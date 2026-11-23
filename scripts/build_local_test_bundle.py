#!/usr/bin/env python3
"""Build a source-only, offline local-test ZIP with synthetic data support.

The archive is assembled from an explicit allowlist plus safe project source
files. Private Drive mirrors, SQLite state, owner photos, local registries,
third-party M3 geometry, caches, and Git internals are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "out" / "325ix-restoration-os-local-test.zip"
BUNDLE_NAME = "325ix-restoration-os-local-test"
EXCLUDED_DIRS = {
    ".git", ".arena", ".cache", ".local", ".venv", "node_modules", "__pycache__",
    "google_drive", "out", "data", "actual_part_photos", "local_models",
    "rc12_trial_state", "workshop_jobs_backups", "coverage", "dist", "build",
}
EXCLUDED_FILES = {
    "catalog_research_registry.json", "maintenance_manual_index.sqlite3",
    "part_photos.sqlite3", "3D_RELEASE_STATUS.json", "models/asset-install-report.json",
    "models/e30_reference_m3.glb",
}
EXCLUDED_SUFFIXES = (".sqlite3", ".sqlite3-wal", ".sqlite3-shm", ".zip", ".log", ".tmp", ".pyc")
ALLOWED_MODEL_FILES = {
    "models/ix_m20_engine_bay.glb",
    "models/ix_front_axle_workshop.glb",
    "models/ix_awd_driveline_workshop.glb",
    "models/previews/ix_m20_engine_bay.webp",
    "models/previews/ix_front_axle_workshop.webp",
    "models/previews/ix_awd_driveline_workshop.webp",
}
ALLOWED_VENDOR_FILES = {
    "vendor/three/LICENSE",
    "vendor/three/build/three.module.js",
    "vendor/three/examples/jsm/controls/OrbitControls.js",
    "vendor/three/examples/jsm/loaders/GLTFLoader.js",
    "vendor/three/examples/jsm/utils/BufferGeometryUtils.js",
    "vendor/meshopt_decoder.module.js",
    "vendor/meshoptimizer_LICENSE.md",
}
REQUIRED_FILES = {
    "README.md", "app.py", "index.html", "site.css", "site.js", "viewer3d.js",
    "explosion-rig.js", "mechanical_index.json", "front_axle_expert_v1.json",
    "sources.json", "sources_extra.json", "specialists.json", "curated_evidence.json",
    "fixtures/local_demo_catalog.json", "RUN_LOCAL_DEMO.command",
    "scripts/build_demo_catalog.py", "scripts/run_local_demo.py",
    "scripts/build_local_test_bundle.py", "scripts/browser_local_demo_smoke.cjs",
    "scripts/browser_visual_handoff.cjs", "scripts/preview_server.py",
    "scripts/import_curated_evidence_snapshot.py", "release_check_rc14.py",
    "test_release_check_rc14.py", "test_local_demo.py", "test_front_play_visual_handoff.py",
    "test_mvp_integration.py",
    "test_runtime_catalog_paths.py", "test_runtime_importer.py", "test_viewer3d_contract.py",
    "docs/LOCAL_TEST_GUIDE.md", "docs/EVIDENCE_RECONCILIATION.md",
    *ALLOWED_MODEL_FILES, *ALLOWED_VENDOR_FILES,
}


def excluded(rel: str, path: Path, output: Path | None = None) -> bool:
    if output is not None and path.resolve() == output:
        return True
    if rel in ALLOWED_VENDOR_FILES or rel in ALLOWED_MODEL_FILES:
        return False
    parts = Path(rel).parts
    if any(part in EXCLUDED_DIRS for part in parts):
        return True
    if rel in EXCLUDED_FILES:
        return True
    if rel.startswith("models/") and rel not in ALLOWED_MODEL_FILES:
        return True
    if rel.startswith("vendor/") and rel not in ALLOWED_VENDOR_FILES:
        return True
    if path.name == ".DS_Store" or path.name == ".env" or path.name.endswith(".env"):
        return True
    if path.name.startswith("workshop_jobs"):
        return True
    if path.suffix.lower().endswith(EXCLUDED_SUFFIXES):
        return True
    return False


def collect_files(output: Path | None = None) -> list[tuple[str, Path]]:
    collected: list[tuple[str, Path]] = []
    for current, dirnames, filenames in os.walk(ROOT, topdown=True, followlinks=False):
        current_path = Path(current)
        dirnames[:] = sorted(
            name for name in dirnames
            if (name not in EXCLUDED_DIRS or (current_path / name).relative_to(ROOT).as_posix() == "vendor/three/build")
            and not (current_path / name).is_symlink()
        )
        for name in sorted(filenames):
            path = current_path / name
            rel = path.relative_to(ROOT).as_posix()
            if path.is_symlink() or excluded(rel, path, output):
                continue
            collected.append((rel, path))
    collected.sort(key=lambda pair: pair[0])
    found = {rel for rel, _ in collected}
    missing = sorted(REQUIRED_FILES - found)
    if missing:
        raise FileNotFoundError("Local-test bundle is incomplete; required files missing: " + ", ".join(missing))
    return collected


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_commit() -> str | None:
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        return value or None
    except (OSError, subprocess.CalledProcessError):
        return None


def source_worktree_dirty() -> bool | None:
    try:
        value = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=ROOT, stderr=subprocess.DEVNULL, text=True,
        )
        return bool(value.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def validate_archive(path: Path) -> tuple[int, int]:
    with zipfile.ZipFile(path, "r") as archive:
        names = set(archive.namelist())
        prefix = BUNDLE_NAME + "/"
        manifest_name = prefix + "LOCAL_TEST_PACKAGE_MANIFEST.json"
        if manifest_name not in names:
            raise ValueError("Package manifest is missing")
        manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
        payload = manifest.get("files", [])
        for record in payload:
            member = prefix + record["path"]
            raw = archive.read(member)
            if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
                raise ValueError("Packaged file failed integrity check: " + record["path"])
        forbidden = []
        for name in names:
            rel = name[len(prefix):] if name.startswith(prefix) else name
            if rel.startswith(("google_drive/", ".git/", "actual_part_photos/", "local_models/", "data/")):
                forbidden.append(name)
            if rel.endswith((".sqlite3", ".sqlite3-wal", ".sqlite3-shm", ".pyc", ".zip")):
                forbidden.append(name)
            if rel in EXCLUDED_FILES:
                forbidden.append(name)
        if forbidden:
            raise ValueError("Private or local-only files entered the archive: " + ", ".join(sorted(forbidden)[:12]))
        required = {prefix + item for item in REQUIRED_FILES}
        if not required.issubset(names):
            raise ValueError("Required local-test files are missing from the ZIP")
        return len(payload), path.stat().st_size


def build(output: Path) -> Path:
    output = output.expanduser().resolve()
    if output == ROOT or output.is_dir():
        raise ValueError("Output must be a ZIP file path")
    if output.suffix.lower() != ".zip":
        raise ValueError("Output filename must end with .zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    files = collect_files(output)
    records = [
        {"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for rel, path in files
    ]
    manifest = {
        "package": BUNDLE_NAME,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit(),
        "source_worktree_dirty": source_worktree_dirty(),
        "file_hashes_describe_built_snapshot": True,
        "fixture": "Synthetic-only; generated locally by scripts/build_demo_catalog.py",
        "private_data_included": False,
        "safety_clearance": "NOT_APPROVED",
        "exclusions": [
            "Google Drive/local runtime mirrors", "SQLite/workshop job and photo state",
            "owner photographs", "private research registry", "third-party M3 reference GLB",
            "Git metadata and caches",
        ],
        "files": records,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for rel, path in files:
                archive.write(path, arcname=f"{BUNDLE_NAME}/{rel}")
            archive.writestr(f"{BUNDLE_NAME}/LOCAL_TEST_PACKAGE_MANIFEST.json", manifest_bytes)
        validate_archive(temp)
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)
    checksum = sha256_file(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{checksum}  {output.name}\n", encoding="ascii",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Destination ZIP (default: out/325ix-restoration-os-local-test.zip)")
    args = parser.parse_args()
    try:
        result = build(args.output)
        file_count, size = validate_archive(result)
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(f"Built and verified {result}")
    print(f"Files: {file_count} · ZIP bytes: {size}")
    print(f"SHA-256: {sha256_file(result)}")
    print(f"Checksum sidecar: {result.with_suffix(result.suffix + '.sha256')}")
    print("Private runtime/Drive data, owner state/photos, and the unverified M3 GLB were excluded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
