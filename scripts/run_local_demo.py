#!/usr/bin/env python3
"""Run an isolated, loopback-only synthetic demo without Google Drive data."""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
BUILDER = ROOT / "scripts" / "build_demo_catalog.py"
sys.path.insert(0, str(ROOT / "scripts"))
from build_demo_catalog import build as build_demo_catalog, is_demo_catalog


def default_state_dir() -> Path:
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "325ix-restoration-os-demo"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / "325ix-restoration-os-demo"
    return Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / "325ix-restoration-os-demo"


def port_available(port: int) -> bool:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def choose_port(preferred: int) -> int:
    for port in range(preferred, min(preferred + 100, 65536)):
        if port_available(port):
            return port
    raise RuntimeError("No free loopback port found starting at " + str(preferred))


def wait_for_app(port: int, process: subprocess.Popen, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/api/3d/status"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Workbench exited during startup with code {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise TimeoutError("Local demo did not become healthy within 20 seconds")


def verify_or_build_catalog(catalog: Path) -> None:
    if catalog.exists():
        if not is_demo_catalog(catalog):
            raise RuntimeError("Existing catalog is not a valid synthetic demo; refusing to use or overwrite it")
        return
    build_demo_catalog(catalog)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765, help="Preferred loopback port (tries the next 99 if busy)")
    parser.add_argument("--state-dir", type=Path, default=default_state_dir(),
                        help="Directory for this demo's persistent test jobs/photos/catalog")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically")
    args = parser.parse_args()

    if not APP.is_file() or not BUILDER.is_file():
        parser.error("Run this script from an extracted local-test package containing app.py and scripts/build_demo_catalog.py")
    if not 1024 <= args.port <= 65535:
        parser.error("Port must be in the range 1024–65535")

    state = args.state_dir.expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True)
    catalog = state / "demo_catalog.sqlite3"
    jobs = state / "workshop_jobs.sqlite3"
    photos = state / "part_photos.sqlite3"
    photo_root = state / "actual_part_photos"
    manual_index = state / "manual_index.sqlite3"
    try:
        verify_or_build_catalog(catalog)
        port = choose_port(args.port)
    except (OSError, RuntimeError) as exc:
        parser.error(str(exc))

    env = os.environ.copy()
    # Prevent machine-specific identifiers from appearing in a synthetic demo.
    env.pop("BMW_325IX_VIN", None)
    env.pop("BMW_325IX_ENGINE_NUMBER", None)
    command = [
        sys.executable, "-u", str(APP),
        "--catalog", str(catalog), "--demo", "--port", str(port),
        "--jobs", str(jobs), "--photo-db", str(photos), "--photo-root", str(photo_root),
        "--manual-index", str(manual_index),
    ]
    process = subprocess.Popen(command, cwd=ROOT, env=env)
    url = f"http://127.0.0.1:{port}/#twin"
    try:
        wait_for_app(port, process)
        print("\nLOCAL SYNTHETIC DEMO — no Drive data or external services are required.", flush=True)
        print("URL:", url, flush=True)
        print("State directory:", state, flush=True)
        print("Test catalog: five synthetic assemblies; all part numbers begin DEMO-.", flush=True)
        print("No OEM drawings, real fitment, repair instructions, or safety clearance are included.", flush=True)
        print("Keep this process running; press Ctrl+C to stop.", flush=True)
        if not args.no_browser:
            webbrowser.open(url, new=2)
        return process.wait()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print("Local demo failed:", exc, file=sys.stderr)
        return 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
