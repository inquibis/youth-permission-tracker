#!/usr/bin/env python3
"""
Local dev launcher for youth-permission-tracker.

- Installs api_base/requirements.txt
- Starts FastAPI (api_base/main.py) via uvicorn on port 8000
- Serves new_site/ via a simple HTTP server

Usage examples:
  python run_local.py
  python run_local.py --web-port 8080 --api-port 8000
  python run_local.py --bind 0.0.0.0
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def run_cmd(cmd: list[str], cwd: Path, env: Optional[dict[str, str]] = None) -> int:
    """Run a command and return its exit code."""
    print(f"\n$ {' '.join(cmd)}\n(cwd: {cwd})")
    p = subprocess.run(cmd, cwd=str(cwd), env=env)
    return p.returncode


def popen_cmd(cmd: list[str], cwd: Path, env: Optional[dict[str, str]] = None) -> subprocess.Popen:
    """Start a long-running process."""
    print(f"\n$ {' '.join(cmd)}\n(cwd: {cwd})")
    return subprocess.Popen(cmd, cwd=str(cwd), env=env)


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    api_dir = repo_root / "api_base"
    site_dir = repo_root / "new_site"
    requirements = api_dir / "requirements.txt"

    parser = argparse.ArgumentParser(description="Run local dev servers.")
    parser.add_argument("--api-port", type=int, default=8000, help="FastAPI port (default: 8000)")
    parser.add_argument("--web-port", type=int, default=8080, help="Web server port (default: 8080)")
    parser.add_argument("--bind", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--no-install", action="store_true", help="Skip pip install step")
    args = parser.parse_args()

    # Basic structure checks
    if not api_dir.is_dir():
        print(f"ERROR: Missing folder: {api_dir}")
        return 2
    if not site_dir.is_dir():
        print(f"ERROR: Missing folder: {site_dir}")
        return 2
    if not requirements.is_file():
        print(f"ERROR: Missing requirements file: {requirements}")
        return 2

    # Install requirements (in the current Python environment)
    if not args.no_install:
        code = run_cmd(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
            cwd=repo_root,
        )
        if code != 0:
            print("ERROR: pip install failed.")
            return code

    # Start API via uvicorn (reload enabled for dev)
    # Assumes FastAPI app is defined as `app` inside api_base/main.py
    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--reload",
        "--host",
        args.bind,
        "--port",
        str(args.api_port),
    ]

    # Start web server to host new_site/
    web_cmd = [
        sys.executable,
        "-m",
        "http.server",
        str(args.web_port),
        "--bind",
        args.bind,
        "--directory",
        str(site_dir),
    ]

    env = os.environ.copy()

    api_proc = popen_cmd(api_cmd, cwd=repo_root, env=env)
    web_proc = popen_cmd(web_cmd, cwd=repo_root, env=env)

    print("\nServers starting...")
    print(f"  Web: http://{args.bind}:{args.web_port}/  (serving {site_dir})")
    print(f"  API: http://{args.bind}:{args.api_port}/  (uvicorn reload)")
    print("\nPress Ctrl+C to stop both.\n")

    def shutdown():
        for p in (web_proc, api_proc):
            if p.poll() is None:
                try:
                    if os.name == "nt":
                        p.terminate()
                    else:
                        p.send_signal(signal.SIGTERM)
                except Exception:
                    pass

        # give them a moment, then force-kill if needed
        deadline = time.time() + 3
        for p in (web_proc, api_proc):
            while p.poll() is None and time.time() < deadline:
                time.sleep(0.1)
        for p in (web_proc, api_proc):
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass

    try:
        while True:
            # If either exits unexpectedly, stop the other too.
            api_code = api_proc.poll()
            web_code = web_proc.poll()
            if api_code is not None:
                print(f"\nAPI process exited with code {api_code}. Shutting down web server...")
                shutdown()
                return api_code
            if web_code is not None:
                print(f"\nWeb server exited with code {web_code}. Shutting down API...")
                shutdown()
                return web_code
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nStopping...")
        shutdown()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
