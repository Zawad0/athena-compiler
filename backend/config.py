
# Timeouts (seconds)

# How long the *compiler* runs.
# gcc/g++ are fast; javac is slower. 10 s is generous but safe.
COMPILE_TIMEOUT_SECONDS = 10

# How long the *compiled program* runs before killing it.
# This is the main guard against infinite loops.
# After this many seconds, subprocess raises TimeoutExpired
# and runner.py kills the process and returns status="timeout".
RUN_TIMEOUT_SECONDS = 5

# Java's JVM takes longer to start than a native binary,
# so we give it extra time. runner.py picks this up per-language.
JAVA_RUN_TIMEOUT_SECONDS = 10

# Output caps (bytes)

# Maximum bytes we read from stdout or stderr.
# Without this, a program like `while(1) puts("hi");` would
# fill RAM in seconds.  64 KB is plenty for a demo program.
OUTPUT_CAP_BYTES = 64 * 1024   # 64 KB

# Source size limit (bytes)

# Maximum size of the submitted source code.
# 100 KB is way more than any lecture-exercise program needs.
# This is enforced in app.py *before* touching the filesystem.
MAX_SOURCE_BYTES = 100_000

# Server binding

# Bind to loopback only. If this were 0.0.0.0 the server would
# be reachable from other machines on the network
HOST = "127.0.0.1"
PORT = 5000
