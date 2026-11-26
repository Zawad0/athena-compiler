# =============================================================
#  languages.py — Per-language configuration
#
#  HOW TO ADD A NEW LANGUAGE (read this, teammate!):
#  -------------------------------------------------------
#  1. Add a new key to LANGUAGES below (e.g. "rust", "python").
#  2. Fill in the five fields described in the LanguageConfig
#     dataclass below.  That's it. runner.py reads this dict
#     and needs NO changes at all.
#
#  The only exception: if the new language has a quirk that
#  doesn't fit the compile→run model (e.g. interpreted langs
#  skip compilation), set compile_cmd to None and runner.py
#  will skip the compile step automatically.
#
#  WHY A DATACLASS?
#  A plain dict works too, but a dataclass gives you
#  auto-complete in editors and a clear "schema" for what every
#  language entry must supply.  It costs zero extra complexity.
# =============================================================

from dataclasses import dataclass
from typing import Optional

import config  # our own config.py for timeout values


@dataclass
class LanguageConfig:
    """Describes everything runner.py needs to compile and run one language."""

    # The filename to write source code into inside the temp dir.
    # Java REQUIRES the filename to match the public class name,
    # so it must be "Main.java" when the class is named Main.
    source_filename: str

    # List of command tokens for the compiler step.
    # We use a list (not a string) so subprocess never passes this
    # through a shell — user source code can't inject shell syntax.
    # Set to None for interpreted languages that need no compilation.
    compile_cmd: Optional[list]

    # List of command tokens to *run* the program after compilation.
    # For native binaries this is just ["./main"]; for Java it's
    # ["java", "-cp", ".", "Main"] because the JVM takes a class name,
    # not a file path.
    run_cmd: list

    # How long (seconds) we allow the compiler to run.
    compile_timeout: int

    # How long (seconds) we allow the program itself to run.
    run_timeout: int


# =============================================================
#  The registry.  runner.py does:  LANGUAGES[language_key]
#
#  Keys must match the values the frontend sends as "language":
#  "c", "cpp", "java"  (lowercase, no spaces).
# =============================================================

LANGUAGES: dict[str, LanguageConfig] = {

    # ----------------------------------------------------------
    #  C  (implemented by Zawad — fully working)
    #  Source → gcc → ./main → stdout/stderr
    # ----------------------------------------------------------
    "c": LanguageConfig(
        source_filename="main.c",

        # gcc flags:
        #   main.c   — input file (relative, inside the temp dir)
        #   -o main  — name of the output binary
        # No extra flags: keep it simple, same as a lecture example.
        compile_cmd=["gcc", "main.c", "-o", "main"],

        # On Linux the binary is "./main".
        # On Windows it would be "main.exe" — see README note.
        run_cmd=["./main"],

        compile_timeout=config.COMPILE_TIMEOUT_SECONDS,
        run_timeout=config.RUN_TIMEOUT_SECONDS,
    ),

    # ----------------------------------------------------------
    #  C++  (TEAMMATE: implement and test this)
    #  Nearly identical to C; only the compiler and filename differ.
    #  Steps:
    #   1. Verify g++ is installed:  g++ --version
    #   2. Test manually:  echo '#include<iostream>
    #      int main(){std::cout<<"hi";}' | g++ -o /tmp/t -xc++ -
    #   3. Run the self-test:  python backend/runner.py
    #      and check the C++ cases pass.
    # ----------------------------------------------------------
    "cpp": LanguageConfig(
        source_filename="main.cpp",
        compile_cmd=["g++", "main.cpp", "-o", "main"],
        run_cmd=["./main"],
        compile_timeout=config.COMPILE_TIMEOUT_SECONDS,
        run_timeout=config.RUN_TIMEOUT_SECONDS,
    ),

    # ----------------------------------------------------------
    #  Java  (TEAMMATE: implement and test this)
    #  Quirks you must know:
    #   1. The public class MUST be named "Main" and saved in
    #      "Main.java" — javac enforces this hard.
    #      The frontend shows a warning about this to the user.
    #   2. After javac, .class files live in the temp dir.
    #      We run  `java -cp . Main`  to execute them.
    #      (-cp . means "look for .class files in current dir")
    #   3. JVM startup is slower; we use the longer timeout.
    #  Steps:
    #   1. Verify javac/java are installed:  java -version
    #   2. Run the self-test:  python backend/runner.py
    #      and check the Java cases pass.
    # ----------------------------------------------------------
    "java": LanguageConfig(
        source_filename="Main.java",
        compile_cmd=["javac", "Main.java"],
        run_cmd=["java", "-cp", ".", "Main"],
        compile_timeout=config.COMPILE_TIMEOUT_SECONDS,
        run_timeout=config.JAVA_RUN_TIMEOUT_SECONDS,
    ),
}
