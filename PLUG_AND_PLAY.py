#!/usr/bin/env python3
"""Shakthi_OS v3.2.0 -- plug-and-play launcher.

Run: `python3 PLUG_AND_PLAY.py` (macOS/Linux) or `python PLUG_AND_PLAY.py`
(Windows), from this folder. Requires Python 3.10+ and Node.js 18+ (npm)
already installed on the host -- neither is bundled on this drive.

Deliberately stdlib-only (venv/subprocess/webbrowser/pathlib) instead of
three hand-written shell dialects: those modules already do the right
thing per-OS, which is a stronger correctness bar than an untested .bat
guess. First run creates a local .venv and runs `npm install` -- a few
minutes. Every run after that starts in seconds.
"""
import platform
import shutil
import socket
import subprocess
import sys
import time
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
DASHBOARD_DIR = ROOT / "dashboard"


def venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python3"


def port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def ensure_venv():
    if venv_python().exists():
        return
    print("First run: creating a local Python environment (.venv)...")
    venv.create(VENV_DIR, with_pip=True)
    subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")],
        check=True,
    )


def ensure_npm_installed(npm: str):
    if (DASHBOARD_DIR / "node_modules").exists():
        return
    print("First run: installing dashboard dependencies (npm install)...")
    subprocess.run([npm, "install"], cwd=str(DASHBOARD_DIR), check=True)


def main():
    if sys.version_info < (3, 10):
        sys.exit(f"Python 3.10+ required, found {platform.python_version()}.")
    npm = shutil.which("npm")
    if not npm:
        sys.exit("npm not found on PATH. Install Node.js 18+ from https://nodejs.org, then re-run this script.")

    ensure_venv()
    ensure_npm_installed(npm)

    if not port_open("127.0.0.1", 8787):
        print("Starting API server (127.0.0.1:8787)...")
        subprocess.Popen([str(venv_python()), "-m", "orchestrator.api"], cwd=str(ROOT))
    else:
        print("API server already running.")

    if not port_open("127.0.0.1", 3000):
        print("Starting dashboard (127.0.0.1:3000)...")
        subprocess.Popen([npm, "run", "dev"], cwd=str(DASHBOARD_DIR))
    else:
        print("Dashboard already running.")

    print("Waiting for both to come up...")
    for _ in range(60):
        if port_open("127.0.0.1", 8787) and port_open("127.0.0.1", 3000):
            break
        time.sleep(1)
    else:
        print("Still starting -- check back in a moment, or see any error output above.")
        return

    print("Shakthi_OS is running: http://localhost:3000")
    webbrowser.open("http://localhost:3000")


if __name__ == "__main__":
    main()
