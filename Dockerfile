# =============================================================
#  Dockerfile — Isolated runner environment for Athena Compiler
#
#  Builds a lightweight Linux image containing gcc, g++, and JDK
#  plus a non-root user ("runner") so untrusted user code never
#  runs as root inside the container.
#
#  Build once from the repo root:
#      docker build -t athena-runner .
# =============================================================

FROM ubuntu:24.04

# Avoid interactive prompts during apt-get install
ENV DEBIAN_FRONTEND=noninteractive

# Install C (gcc), C++ (g++), and Java (headless JDK = javac + java without GUI libs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libc6-dev \
        openjdk-21-jdk-headless && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user so code inside the container runs unprivileged
RUN useradd -m -s /bin/sh runner
USER runner

# runner.py mounts each request's temp directory at /work
WORKDIR /work
