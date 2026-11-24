#!/usr/bin/env python3
"""Run the Workbench in an isolated Arena/browser preview.

The application keeps its loopback-only Host and Origin checks. This small
reverse proxy is the only listener on 0.0.0.0; it translates same-origin
preview requests to the local backend and stores all mutable jobs/photos in a
TemporaryDirectory. A private/manual index and user VIN environment variables
are deliberately not exposed.
"""
from __future__ import annotations

import argparse
import http.client
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
V4_ROOT = ROOT / "google_drive" / "14_MULTIMODAL_MEDIA_AND_GRAPH"
PORT = int(os.environ.get("PORT", "8080"))
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
}


def unused_loopback_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class PreviewProxy(BaseHTTPRequestHandler):
    backend_port = 0
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):
        print("[preview]", self.address_string(), fmt % args, flush=True)

    def do_GET(self):
        self.forward()

    def do_POST(self):
        self.forward()

    def do_HEAD(self):
        self.send_error(405, "HEAD is not exposed by the local Workbench")

    def do_OPTIONS(self):
        # Cross-origin callers cannot use the preview proxy as a write bypass.
        self.send_error(403, "Cross-origin requests are not enabled")

    def forward(self):
        if not self.path.startswith("/") or self.path.startswith("//"):
            self.send_error(400, "Only same-origin relative paths are accepted")
            return

        browser_origin = self.headers.get("Origin")
        browser_host = self.headers.get("Host", "")
        if browser_origin:
            parsed_origin = urlsplit(browser_origin)
            if parsed_origin.scheme not in {"http", "https"} or parsed_origin.netloc.lower() != browser_host.lower():
                self.send_error(403, "Cross-origin request blocked by preview proxy")
                return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 5_000_000:
                self.send_error(413, "Preview request body too large")
                return
            body = self.rfile.read(length) if length else None
            headers = {
                name: value for name, value in self.headers.items()
                if name.lower() not in HOP_BY_HOP and name.lower() != "origin"
            }
            headers["Host"] = f"127.0.0.1:{self.backend_port}"
            # The backend only permits loopback origins. The proxy accepts this
            # rewrite only after confirming the browser Origin matched its Host.
            if browser_origin:
                headers["Origin"] = f"http://127.0.0.1:{self.backend_port}"

            conn = http.client.HTTPConnection("127.0.0.1", self.backend_port, timeout=90)
            conn.request(self.command, self.path, body=body, headers=headers)
            response = conn.getresponse()
            payload = response.read()
            self.send_response(response.status)
            content_length_sent = False
            for name, value in response.getheaders():
                lowered = name.lower()
                if lowered in HOP_BY_HOP or lowered in {"server", "date"}:
                    continue
                if lowered == "content-security-policy":
                    value = re.sub(
                        r"frame-ancestors\s+'none'",
                        "frame-ancestors 'self' https://*.e2b.app",
                        value,
                        flags=re.IGNORECASE,
                    )
                if lowered == "content-length":
                    value = str(len(payload))
                    content_length_sent = True
                self.send_header(name, value)
            if not content_length_sent:
                self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            if payload:
                self.wfile.write(payload)
            conn.close()
        except (BrokenPipeError, ConnectionResetError):
            return
        except (OSError, http.client.HTTPException, ValueError) as exc:
            self.send_error(502, f"Local Workbench backend unavailable: {str(exc)[:160]}")


def wait_for_backend(port: int, process: subprocess.Popen, timeout: float = 25.0) -> None:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/api/vehicle"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Workbench exited during startup with code {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise TimeoutError("Workbench did not become healthy within 25 seconds")


def stop_on_term(_signum, _frame):
    raise KeyboardInterrupt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v4-root", type=Path, default=V4_ROOT,
                        help="Synced 14_MULTIMODAL_MEDIA_AND_GRAPH folder")
    parser.add_argument("--port", type=int, default=PORT,
                        help="Preview proxy port (default: 8080 or PORT environment variable)")
    args = parser.parse_args()
    v4_root = args.v4_root.expanduser().resolve()
    if not v4_root.is_dir() or not (v4_root / "04_SEARCH" / "325ix_multimodal.sqlite3").is_file():
        raise SystemExit("Local V4 data is missing; sync 14_MULTIMODAL_MEDIA_AND_GRAPH before starting the preview.")
    backend_port = unused_loopback_port()
    runtime = tempfile.TemporaryDirectory(prefix="325ix-workbench-preview-")
    state = Path(runtime.name)
    env = os.environ.copy()
    # Do not expose machine-specific identifiers through the shared preview.
    env.pop("BMW_325IX_VIN", None)
    env.pop("BMW_325IX_ENGINE_NUMBER", None)
    command = [
        sys.executable, "-u", str(ROOT / "app.py"),
        "--port", str(backend_port),
        "--v4-root", str(v4_root),
        "--jobs", str(state / "workshop_jobs.sqlite3"),
        "--photo-db", str(state / "part_photos.sqlite3"),
        "--photo-root", str(state / "actual_part_photos"),
        # Keep privately held/licensed manual text out of the browser preview.
        "--manual-index", str(state / "manual_index.sqlite3"),
    ]
    backend = subprocess.Popen(command, cwd=ROOT, env=env)
    server = None
    try:
        wait_for_backend(backend_port, backend)
        PreviewProxy.backend_port = backend_port
        server = ThreadingHTTPServer(("0.0.0.0", args.port), PreviewProxy)
        server.daemon_threads = True
        print(f"Workbench preview proxy listening on 0.0.0.0:{args.port}", flush=True)
        print("Backend: loopback-only; job/photo state: disposable temporary directory", flush=True)
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        backend.terminate()
        try:
            backend.wait(timeout=10)
        except subprocess.TimeoutExpired:
            backend.kill()
            backend.wait()
        runtime.cleanup()
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop_on_term)
    raise SystemExit(main())
