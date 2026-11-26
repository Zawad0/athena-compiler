# Athena Compiler

Web app: write C, C++ or Java in the browser, click Run, see output or errors.
Local only: each person runs their own backend on `127.0.0.1`.

## Stack
Flask (Python) backend serving a single plain HTML/JS page, managed with [uv](https://docs.astral.sh/uv/).
Docker isolation planned.

## Prerequisites

### Arch / CachyOS
```bash
sudo pacman -S --needed git gcc jdk-openjdk uv docker
sudo systemctl enable --now docker.service
sudo usermod -aG docker $USER   # then log out and back in
```

### Windows

1. **Git**: download and run the installer from https://git-scm.com/download/win. The default options are fine.
2. **uv**: follow the installation instructions at https://docs.astral.sh/uv/getting-started/installation/
3. **Docker Desktop**: download it from https://www.docker.com/products/docker-desktop/ and run the installer. Keep the "Use WSL 2" option ticked, restart if asked, then open Docker Desktop once and wait until it says it is running. The app needs Docker running in the background whenever you use it.
4. **JDK and gcc (only needed until the Docker runner is in place):**
   - JDK: download Temurin 21 from https://adoptium.net/ and tick "Add to PATH" in the installer.
   - gcc/g++: install MSYS2 from https://www.msys2.org/, open the "MSYS2 UCRT64" program, run `pacman -S mingw-w64-ucrt-x86_64-gcc`, then add `C:\msys64\ucrt64\bin` to your PATH (Start menu, search "Edit the system environment variables", Environment Variables, select Path, Edit, New).
5. **Check the installs:** close and reopen your terminal, then run `git --version`, `uv --version`, `docker --version`, `gcc --version` and `javac -version`. Each should print a version rather than an error.

## Setup and run (all platforms)
```bash
git clone git@github.com:Zawad0/athena-compiler.git
cd athena-compiler
uv sync         # creates .venv and installs locked dependencies
uv run backend/app.py  # runs flask locally
```
Open http://localhost:5000

## Docker runner image
*WILL BE ADDED SOON*

## Status
Walking skeleton: returns a fake response. Real execution not implemented yet.
