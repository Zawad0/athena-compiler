# Athena Compiler

Web app: write C, C++ or Java in the browser, click Run, see output or errors.
Local only: each person runs their own backend on `127.0.0.1`.

## Stack
Flask (Python) backend serving a single plain HTML/JS page. *Docker isolation planned.*

## Prerequisites (Arch)
```bash
sudo pacman -S --needed git gcc jdk-openjdk python docker
sudo systemctl enable --now docker.service
sudo usermod -aG docker $USER   # then log out and back in
```

## Setup and run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python backend/app.py
```
Open http://localhost:5000


## Status
Walking skeleton: returns a fake response. Real execution not implemented yet.
