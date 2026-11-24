#!/usr/bin/env python3
"""End-to-end API smoke test for the self-contained synthetic local demo."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_demo_catalog import build, is_demo_catalog


def reserve_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(base: str, path: str, body: dict | None = None):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {} if body is None else {
        "Content-Type": "application/json",
        "X-Workbench-Request": "same-origin",
    }
    req = urllib.request.Request(
        base + path, data=payload, headers=headers,
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        raw = response.read()
        if "json" in response.headers.get("content-type", ""):
            return response.status, json.loads(raw)
        return response.status, raw


def wait_for_server(base: str, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"App exited during start with code {process.returncode}")
        try:
            request(base, "/api/3d/status")
            return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise AssertionError("Local demo did not start in 15 seconds")


def start_app(state: Path, catalog: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env.pop("BMW_325IX_VIN", None)
    env.pop("BMW_325IX_ENGINE_NUMBER", None)
    return subprocess.Popen(
        [
            sys.executable, "-u", "app.py", "--catalog", str(catalog), "--demo",
            "--port", str(port), "--jobs", str(state / "workshop_jobs.sqlite3"),
            "--photo-db", str(state / "part_photos.sqlite3"),
            "--photo-root", str(state / "photos"),
            "--manual-index", str(state / "manual_index.sqlite3"),
        ],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="325ix-local-demo-test-") as temp:
        state = Path(temp)
        catalog = build(state / "demo_catalog.sqlite3")
        assert is_demo_catalog(catalog)
        try:
            build(catalog)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Fixture builder must refuse overwriting an existing catalog by default")

        port = reserve_port()
        base = f"http://127.0.0.1:{port}"
        process = start_app(state, catalog, port)
        try:
            wait_for_server(base, process)
            _, viewer = request(base, "/api/3d/status")
            assert viewer["demo_mode"] is True
            assert viewer["ready"] is True, viewer["missing"]
            assert viewer["original_mechanical_assets"] is True
            _, twin_before = request(base, "/api/twin")
            _, instance = request(base, "/api/twin/component", {
                "component_type": "Tie rod", "location": "Front axle", "side": "LEFT",
                "source": "Synthetic QA intake",
            })
            assert instance["status"] == "IDENTITY_UNCONFIRMED"
            _, twin_after = request(base, "/api/twin")
            assert twin_after["events"][0]["event_type"] == "COMPONENT_INSTANCE_CREATED"
            assert twin_after["gamification"]["xp"] == twin_before["gamification"]["xp"]
            with sqlite3.connect(state / "workshop_jobs.sqlite3") as ledger:
                ledger.executemany(
                    "INSERT INTO twin_event(created_utc,event_type,entity_type,entity_id,payload_json,source,xp_value) VALUES('fixture','QA_RECORDED','component','1','{}','QA fixture',1)",
                    [() for _ in range(101)],
                )
            _, long_history = request(base, "/api/twin")
            assert len(long_history["events"]) == 100
            assert long_history["gamification"]["xp"] == twin_after["gamification"]["xp"] + 101
            _, vehicle = request(base, "/api/vehicle")
            assert vehicle["vin"] == "VIN_NOT_CONFIGURED"
            _, workflow = request(base, "/api/workflow/front-axle")
            assert "S7_INTEGRATION" in workflow["connected_surfaces"]
            assert "C0_COORDINATOR" in workflow["connected_surfaces"]
            assert "C0_INTEGRATION" not in workflow["connected_surfaces"]

            _, twin = request(base, "/api/visual/twin")
            systems = {row["id"]: row for row in twin["systems"]}
            assert systems["front_axle"]["assembly_count"] == 1
            assert systems["steering"]["assembly_count"] == 1
            _, group = request(base, "/api/search?group=steering")
            assert len(group["results"]) == 1 and group["results"][0]["part_count"] == 2

            query = urllib.parse.quote("tie rod")
            _, search = request(base, "/api/search?group=steering&q=" + query)
            candidate = next(row for row in search["results"] if row["part_number"] == "DEMO-STEER-001")
            assert candidate["assembly_id"] == "demo-steering-linkage"
            _, assembly = request(base, "/api/assembly?id=demo-steering-linkage")
            assert assembly["assembly"]["slug"] == "demo_steering_linkage"
            assert {row["part_number"] for row in assembly["parts"]} == {"DEMO-STEER-001", "DEMO-STEER-002"}
            _, dossier = request(base, "/api/part-dossier?id=demo-steer-tie-left")
            assert dossier["part"]["part_number"] == "DEMO-STEER-001"

            status, case = request(base, "/api/expert/front-play/start", {
                "side": "LEFT", "system": "steering",
                "symptom": "Synthetic demo symptom for persistence testing only",
                "context": "Fixture data; do not use as vehicle evidence.",
                "visual_scene": "ix_front_axle_workshop", "visual_component_id": "tie_rod",
                "assembly_id": "demo-steering-linkage", "candidate_id": "demo-steer-tie-left",
                "part_number": "DEMO-STEER-001",
            })
            assert status == 201 and case["clearance"] == "NOT_APPROVED"
            assert case["catalog_candidate"]["part_number"] == "DEMO-STEER-001"
            _, saved = request(base, f"/api/expert/front-play/cases?job_id={case['job_id']}")
            assert saved["case"]["job_id"] == case["job_id"]
            assert saved["case"]["clearance"] == "NOT_APPROVED"
            _, overview = request(base, f"/api/job/{case['job_id']}/overview")
            assert overview["readiness"]["clearance"] == "NOT_APPROVED"
            created = next(event for event in overview["twin_events"] if event["event_type"] == "CASE_CREATED")
            payload = created["payload"]
            assert payload["catalog_candidate"]["source_reviewed_exact_number"] is False
            assert payload["catalog_candidate"]["status"] == "NOT_CONFIRMED_AS_INSTALLED"

            process.terminate()
            process.wait(timeout=5)
            process = start_app(state, catalog, port)
            wait_for_server(base, process)
            _, reopened = request(base, f"/api/expert/front-play/cases?job_id={case['job_id']}")
            assert reopened["case"]["job_id"] == case["job_id"]
            assert reopened["case"]["clearance"] == "NOT_APPROVED"
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stderr:
                process.stderr.close()

    print("PASS local synthetic demo: fixture build, search/dossier, 3D runtime readiness, seven-step case, persistence/restart, and NOT_APPROVED safety hold")


if __name__ == "__main__":
    main()
