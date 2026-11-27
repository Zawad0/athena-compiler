# =============================================================
#  runner.py — Compile and run user code, return a result dict
#
#  IMPORTANT: This file must NEVER import Flask.
#  It is pure Python logic so it can be tested from the
#  command line without starting the web server.
#  Run:  python backend/runner.py   to execute the self-tests.
#
#  FLOW (see project context §7):
#
#    run_code(language, source)
#      │
#      ├─ look up language config in languages.py
#      ├─ create a unique temp directory  (tempfile.mkdtemp)
#      ├─ write source file into it
#      ├─ [compile step, if lang has a compiler]
#      │     non-zero exit → return status="compile_error"
#      ├─ [run step]
#      │     TimeoutExpired → kill process → status="timeout"
#      │     non-zero exit  → status="runtime_error"
#      │     output cap hit → status="output_limit" (future)
#      │     exit 0         → status="success"
#      └─ always: shutil.rmtree(tmp)   ← even on exceptions
#
#  WHY subprocess WITH A LIST (not shell=True)?
#  When you pass a string to shell=True, the OS runs:
#      /bin/sh -c "gcc main.c -o main"
#  If the string was built from user input (e.g. the filename),
#  a user could inject  ; rm -rf /  and the shell would run it.
#  Passing a list bypasses the shell entirely — each element is
#  one argument, so injection is structurally impossible.
# =============================================================

import os
import shutil
import subprocess
import tempfile
import time
from typing import Optional

import config
from languages import LANGUAGES, LanguageConfig
import sandbox


# =============================================================
#  _compile
#  Run the compiler and return a failure-result dict, or None.
#
#  WHY return None on success?
#  Lets the caller write:   err = _compile(...); if err: return err
#  which reads like English and avoids nested ifs.
# =============================================================

def _compile(cfg: LanguageConfig, tmp_dir: str) -> Optional[dict]:
    """
    Invoke the compiler for `cfg` with cwd=tmp_dir.

    Returns:
        None           — compilation succeeded (binary is now in tmp_dir)
        dict           — a complete API-result dict describing the failure
    """
    try:
        result = subprocess.run(
            cfg.compile_cmd,          # e.g. ["gcc", "main.c", "-o", "main"]
            cwd=tmp_dir,              # run inside the temp dir so relative paths work
            capture_output=True,      # safe: compiler output is always small
            text=True,
            encoding="utf-8",
            errors="replace",         # don't crash on weird bytes in error messages
            timeout=cfg.compile_timeout,
        )

    except subprocess.TimeoutExpired:
        return _result(
            status="compile_error",
            compile_output=f"Compiler timed out after {cfg.compile_timeout} s.",
        )

    except FileNotFoundError:
        # gcc / g++ / javac is not installed on this machine.
        name = cfg.compile_cmd[0]
        return _result(
            status="internal_error",
            message=f"Compiler '{name}' not found on PATH. Is it installed?",
        )

    if result.returncode != 0:
        # Non-zero exit = compile error.  Error messages are on stderr
        # for gcc/g++/javac.  We also grab stdout just in case.
        return _result(
            status="compile_error",
            compile_output=result.stderr or result.stdout,
            exit_code=result.returncode,
        )

    return None   # success


# =============================================================
#  _run_with_cap
#  Run the compiled program, capping output to avoid OOM.
#
#  WHY NOT capture_output=True here?
#  subprocess.run(capture_output=True) buffers ALL output in RAM
#  before returning.  A program printing in a tight loop can
#  produce gigabytes.  We read with a cap instead.
#
#  Approach used here:
#    communicate(timeout=N) reads all output then waits for exit.
#    After reading we slice to OUTPUT_CAP_BYTES.
#    This is simple and correct for programs up to a few MB.
#    Limitation: a truly runaway program could still use lots of
#    RAM before we cap it.  The Docker phase fixes this properly.
#    Document this in the report's "isolation limits" section.
# =============================================================

def _run_with_cap(cfg: LanguageConfig, tmp_dir: str, stdin_text: str = "") -> dict:
    """
    Run the program and collect output up to OUTPUT_CAP_BYTES per stream.

    Returns a plain dict (not an API-result dict yet):
        stdout, stderr, returncode, truncated, timed_out
    """
    cap = config.OUTPUT_CAP_BYTES

    proc = subprocess.Popen(
        cfg.run_cmd,
        cwd=tmp_dir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        raw_out, raw_err = proc.communicate(
            input=stdin_text,
            timeout=cfg.run_timeout
        )
        truncated = len(raw_out) > cap or len(raw_err) > cap
        return {
            "stdout":     raw_out[:cap],
            "stderr":     raw_err[:cap],
            "returncode": proc.returncode,
            "truncated":  truncated,
            "timed_out":  False,
        }

    except subprocess.TimeoutExpired:
        # Process is still running.  Kill it, then drain the pipes.
        # Skipping the kill would leave a zombie process consuming
        # CPU and potentially blocking the next request.
        proc.kill()
        raw_out, raw_err = proc.communicate()
        return {
            "stdout":     (raw_out or "")[:cap],
            "stderr":     (raw_err or "")[:cap],
            "returncode": proc.returncode,
            "truncated":  False,
            "timed_out":  True,
        }


# =============================================================
#  _result — tiny helper to build a consistent result dict.
#  Every path in run_code() returns one of these.
# =============================================================

def _result(
    status: str,
    compile_output: str = "",
    stdout: str = "",
    stderr: str = "",
    exit_code=None,
    duration_ms: int = 0,
    truncated: bool = False,
    message: str = "",
) -> dict:
    d = {
        "status":         status,
        "compile_output": compile_output,
        "stdout":         stdout,
        "stderr":         stderr,
        "exit_code":      exit_code,
        "duration_ms":    duration_ms,
        "truncated":      truncated,
    }
    if message:
        d["message"] = message
    return d


# =============================================================
#  run_code — PUBLIC ENTRY POINT
#  Called by app.py with the validated language key and source.
#
#  Returns a dict matching the API contract (§8 of project docs).
#  Never raises — all errors are caught and returned as dicts.
# =============================================================

def run_code(language: str, source: str, stdin_text: str = "") -> dict:
    """
    Compile and run `source` written in `language`.

    Args:
        language  — one of "c", "cpp", "java"
        source    — the user's source code as a plain string

    Returns:
        A dict with at minimum {"status": <string>} and the
        other fields defined in the API contract (§8).
    """

    # 1. Look up language config
    cfg = LANGUAGES.get(language)
    if cfg is None:
        return _result(status="internal_error",
                       message=f"Unknown language: {language!r}")

    # 2. Create a unique temp directory.
    #    mkdtemp returns something like /tmp/athena_a1b2c3.
    #    Two concurrent requests get different directories so
    #    their files can't collide.
    tmp_dir = tempfile.mkdtemp(prefix="athena_")

    try:
        # When running inside Docker as a non-root user, the container's
        # user ID may differ from your host user ID.  Making this single
        # ephemeral temp dir writable lets the container write compiled
        # binaries into /work; it is deleted in `finally` right after.
        if config.USE_DOCKER:
            os.chmod(tmp_dir, 0o777)

        # 3. Write the source file
        source_path = os.path.join(tmp_dir, cfg.source_filename)
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source)

        # 4. Compile (skip for interpreted languages with compile_cmd=None)
        if cfg.compile_cmd is not None:
            compile_err = (
                sandbox.compile_in_docker(cfg, tmp_dir)
                if config.USE_DOCKER
                else _compile(cfg, tmp_dir)
            )
            if compile_err:
                return compile_err   # early return; finally still runs

        # 5. Run the program and time it
        t_start = time.monotonic()
        run = (
            sandbox.run_in_docker(cfg, tmp_dir, stdin_text)
            if config.USE_DOCKER
            else _run_with_cap(cfg, tmp_dir, stdin_text)
        )
        duration_ms = int((time.monotonic() - t_start) * 1000)

        if run.get("docker_error"):
            return _result(
                status="internal_error",
                message=run["docker_error"],
                duration_ms=duration_ms,
            )

        # 6. Classify the outcome
        if run["timed_out"]:
            status = "timeout"
        elif run["returncode"] != 0:
            # Covers: explicit exit(N), segfault (returncode=-11),
            # division by zero crash, unhandled signals, etc.
            status = "runtime_error"
        elif run["truncated"]:
            status = "output_limit"
        else:
            status = "success"

        return _result(
            status=status,
            stdout=run["stdout"],
            stderr=run["stderr"],
            exit_code=run["returncode"],
            duration_ms=duration_ms,
            truncated=run["truncated"],
        )

    except Exception as exc:
        # Catch-all safety net: a bug in runner.py should never
        # crash the Flask server.  Return the error so it's visible
        # during development.
        return _result(
            status="internal_error",
            message=f"Unexpected runner error: {exc}",
        )

    finally:
        # 7. ALWAYS delete the temp directory.
        # `finally` runs even when we returned early (compile error)
        # or an exception was raised.  Without this, /tmp fills up.
        shutil.rmtree(tmp_dir, ignore_errors=True)


# =============================================================
#  Self-test
#  Run from the project root:   python backend/runner.py
#  No web server needed.  Good for quick sanity checks.
#
#  TEAMMATE: add C++ and Java test cases here when you implement
#  those modules.  Just copy the C pattern and change language+source.
# =============================================================

if __name__ == "__main__":
    print("=" * 56)
    print("  Athena runner self-test")
    print("=" * 56)

    tests = [
        # --- C tests (implemented) ---
        {
            "desc":     "C — hello world  →  expect: success",
            "language": "c",
            "source":   '#include <stdio.h>\nint main(){\n    puts("Hello from Athena!");\n    return 0;\n}',
        },
        {
            "desc":     "C — stdout + stderr  →  expect: success, both non-empty",
            "language": "c",
            "source":   '#include <stdio.h>\nint main(){\n    printf("out\\n");\n    fprintf(stderr,"err\\n");\n    return 0;\n}',
        },
        {
            "desc":     "C — syntax error  →  expect: compile_error",
            "language": "c",
            "source":   "int main(){ this is not valid C }",
        },
        {
            "desc":     "C — non-zero exit  →  expect: runtime_error, exit_code=42",
            "language": "c",
            "source":   "int main(){ return 42; }",
        },
        {
            "desc":     "C — infinite loop  →  expect: timeout",
            "language": "c",
            "source":   "int main(){ while(1); }",
        },
        # --- C++ tests (uncomment when teammate implements C++) ---
        # {
        #     "desc":     "C++ — hello world  →  expect: success",
        #     "language": "cpp",
        #     "source":   '#include<iostream>\nint main(){std::cout<<"Hello C++!"<<std::endl;}',
        # },
        # --- Java tests (uncomment when teammate implements Java) ---
        # {
        #     "desc":     "Java — hello world  →  expect: success",
        #     "language": "java",
        #     "source":   'public class Main{\n    public static void main(String[] a){\n        System.out.println("Hello Java!");\n    }\n}',
        # },
    ]

    for t in tests:
        print(f"\n--- {t['desc']} ---")
        r = run_code(t["language"], t["source"])
        print(f"  status      : {r['status']}")
        if r.get("message"):
            print(f"  message     : {r['message']}")
        if r.get("compile_output"):
            print(f"  compile_out : {r['compile_output'][:200]!r}")
        if r.get("stdout"):
            print(f"  stdout      : {r['stdout']!r}")
        if r.get("stderr"):
            print(f"  stderr      : {r['stderr']!r}")
        print(f"  exit_code   : {r.get('exit_code')}   duration: {r.get('duration_ms')} ms")

    print("\n" + "=" * 56)
    print("  Done.  Check each line matches the expected status.")
    print("=" * 56)
