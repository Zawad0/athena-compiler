# =============================================================
#  sandbox.py — Docker-based isolation for compiling & running code
#
#  WHY THIS EXISTS:
#  Without Docker, user code runs directly on your machine with
#  your user's permissions.  This module runs the compiler and
#  the compiled program inside a short-lived Docker container
#  with strict limits:
#    --network none     no internet or local network access
#    --memory 256m      caps RAM usage
#    --cpus 0.5         caps CPU usage
#    --pids-limit 64    stops fork bombs
#    --rm               deletes the container automatically on exit
#
#  IMPORTANT GOTCHA:
#  Killing the `docker run` client process on timeout does NOT
#  stop the container running in the background!  That is why
#  we pass a unique `--name` and explicitly run `docker kill`
#  when a timeout happens.
# =============================================================

import os
import subprocess
from typing import Optional

import config
from languages import LanguageConfig


def _docker_base_cmd(container_name: str, tmp_dir: str, interactive: bool = False) -> list:
    """
    Build the common `docker run` prefix shared by compile and run steps.
    Uses list-style arguments (no shell=True) so user data can never
    become shell syntax.
    """
    cmd = ["docker", "run", "--rm"]
    if interactive:
        # -i keeps stdin open so we can pipe stdin_text into the program
        cmd.append("-i")

    cmd.extend([
        "--name", container_name,
        "--network", "none",
        "--memory", config.DOCKER_MEMORY,
        "--cpus", config.DOCKER_CPUS,
        "--pids-limit", str(config.DOCKER_PIDS_LIMIT),
        "-v", f"{os.path.abspath(tmp_dir)}:/work",
        "-w", "/work",
        config.DOCKER_IMAGE,
    ])
    return cmd


def _kill_container(container_name: str) -> None:
    """Force-stop a timed-out container so it doesn't linger in the background."""
    subprocess.run(
        ["docker", "kill", container_name],
        capture_output=True,
        timeout=5,
    )


def _is_docker_setup_error(returncode: Optional[int], stderr: str) -> bool:
    """
    Docker uses exit code 125 when `docker run` itself fails (e.g. daemon
    not running, image not built yet, permission denied on docker socket).
    """
    if returncode == 125:
        return True
    lowered = (stderr or "").lower()
    return (
        "cannot connect to the docker daemon" in lowered
        or "is the docker daemon running" in lowered
        or "unable to find image" in lowered
        or "permission denied while trying to connect" in lowered
        or "docker.sock" in lowered
    )


def compile_in_docker(cfg: LanguageConfig, tmp_dir: str) -> Optional[dict]:
    """
    Run `cfg.compile_cmd` inside a short-lived Docker container.

    Returns:
        None on success, or an API-shaped failure dict on error.
    """
    job_id = os.path.basename(tmp_dir)
    container_name = f"{job_id}_compile"
    cmd = _docker_base_cmd(container_name, tmp_dir) + cfg.compile_cmd

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=cfg.compile_timeout,
        )
    except subprocess.TimeoutExpired:
        _kill_container(container_name)
        return {
            "status":         "compile_error",
            "compile_output": f"Compiler timed out after {cfg.compile_timeout} s.",
            "stdout":         "",
            "stderr":         "",
            "exit_code":      None,
            "duration_ms":    0,
            "truncated":      False,
        }
    except FileNotFoundError:
        return {
            "status":         "internal_error",
            "message":        "Docker CLI not found. Is Docker installed and on PATH?",
            "compile_output": "",
            "stdout":         "",
            "stderr":         "",
            "exit_code":      None,
            "duration_ms":    0,
            "truncated":      False,
        }

    if _is_docker_setup_error(result.returncode, result.stderr):
        return {
            "status":         "internal_error",
            "message":        (
                f"Docker failed (is Docker running and did you build '{config.DOCKER_IMAGE}'?): "
                f"{result.stderr.strip()}"
            ),
            "compile_output": "",
            "stdout":         "",
            "stderr":         "",
            "exit_code":      None,
            "duration_ms":    0,
            "truncated":      False,
        }

    if result.returncode != 0:
        return {
            "status":         "compile_error",
            "compile_output": result.stderr or result.stdout,
            "stdout":         "",
            "stderr":         "",
            "exit_code":      result.returncode,
            "duration_ms":    0,
            "truncated":      False,
        }

    return None


def run_in_docker(cfg: LanguageConfig, tmp_dir: str, stdin_text: str = "") -> dict:
    """
    Run `cfg.run_cmd` inside a short-lived Docker container, enforcing
    timeout and output caps.

    Returns a plain dict matching `_run_with_cap` in runner.py:
        stdout, stderr, returncode, truncated, timed_out
        (plus optional `docker_error` string if Docker itself failed)
    """
    cap = config.OUTPUT_CAP_BYTES
    job_id = os.path.basename(tmp_dir)
    container_name = f"{job_id}_run"
    cmd = _docker_base_cmd(container_name, tmp_dir, interactive=True) + cfg.run_cmd

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return {
            "stdout":       "",
            "stderr":       "",
            "returncode":   None,
            "truncated":    False,
            "timed_out":    False,
            "docker_error": "Docker CLI not found. Is Docker installed and on PATH?",
        }

    try:
        raw_out, raw_err = proc.communicate(
            input=stdin_text,
            timeout=cfg.run_timeout,
        )
        if _is_docker_setup_error(proc.returncode, raw_err):
            return {
                "stdout":       "",
                "stderr":       "",
                "returncode":   None,
                "truncated":    False,
                "timed_out":    False,
                "docker_error": (
                    f"Docker failed (is Docker running and did you build '{config.DOCKER_IMAGE}'?): "
                    f"{raw_err.strip()}"
                ),
            }

        truncated = len(raw_out) > cap or len(raw_err) > cap
        return {
            "stdout":     raw_out[:cap],
            "stderr":     raw_err[:cap],
            "returncode": proc.returncode,
            "truncated":  truncated,
            "timed_out":  False,
        }

    except subprocess.TimeoutExpired:
        # Must kill the container itself, not just the local `docker run` client
        _kill_container(container_name)
        proc.kill()
        raw_out, raw_err = proc.communicate()
        return {
            "stdout":     (raw_out or "")[:cap],
            "stderr":     (raw_err or "")[:cap],
            "returncode": proc.returncode,
            "truncated":  False,
            "timed_out":  True,
        }
