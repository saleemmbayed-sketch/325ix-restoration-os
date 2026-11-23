#!/usr/bin/env python3
"""Isolated safety/rollback contract for the pinned RC13 runtime importer."""
from __future__ import annotations

import errno
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import scripts.import_runtime_from_rc13 as runtime_importer
from scripts.import_runtime_from_rc13 import ImportErrorSafe, import_runtime


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_fixture(root: Path, archive: Path, pins: dict[str, bytes]) -> Path:
    manifest = root / "pins.json"
    manifest.write_text(json.dumps({"sha256_files": {name: sha(raw) for name, raw in pins.items()}}), encoding="utf-8")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for name, raw in pins.items():
            z.writestr(name, raw)
        z.writestr("unlisted/ignored.txt", b"not imported")
    return manifest


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ix-importer-") as temp:
        temp = Path(temp)
        archive = temp / "approved.zip"
        source_bytes = b"immutable source archive"
        pins = {"data/one.txt": b"one", "nested/two.json": b'{"two":2}'}
        manifest = make_fixture(temp, archive, pins)
        archive_digest = sha(archive.read_bytes())
        destination = temp / "checkout"

        installed, existing = import_runtime(archive, destination, manifest)
        assert (installed, existing) == (2, 0)
        for name, raw in pins.items():
            assert (destination / name).read_bytes() == raw
        assert not (destination / "unlisted").exists()
        assert sha(archive.read_bytes()) == archive_digest

        installed, existing = import_runtime(archive, destination, manifest)
        assert (installed, existing) == (0, 2), "identical imports must be idempotent"

        # A local collision blocks the entire import; the other missing file is
        # not installed as a partial side effect.
        clean = temp / "collision"
        (clean / "data").mkdir(parents=True)
        (clean / "data/one.txt").write_bytes(b"owner data; do not replace")
        try:
            import_runtime(archive, clean, manifest)
        except ImportErrorSafe as exc:
            assert "does not match immutable RC13" in str(exc)
        else:
            raise AssertionError("A mismatching existing file must be refused")
        assert not (clean / "nested/two.json").exists()
        assert (clean / "data/one.txt").read_bytes() == b"owner data; do not replace"

        # Exercise the exclusive-create fallback and prove a mid-copy failure
        # removes only its own partial file while leaving no half-imported set.
        failed_copy = temp / "failed-copy"
        with patch.object(runtime_importer.os, "link", side_effect=OSError(errno.EPERM, "hard links disabled")), \
             patch.object(runtime_importer.shutil, "copyfileobj", side_effect=OSError("simulated interrupted copy")):
            try:
                import_runtime(archive, failed_copy, manifest)
            except OSError as exc:
                assert "simulated interrupted copy" in str(exc)
            else:
                raise AssertionError("A simulated partial copy must fail and roll back")
        assert not (failed_copy / "data/one.txt").exists()
        assert not (failed_copy / "nested/two.json").exists()

        # A corrupt archive member must also fail before any destination write.
        bad_archive = temp / "bad.zip"
        with zipfile.ZipFile(bad_archive, "w") as z:
            z.writestr("data/one.txt", b"tampered")
            z.writestr("nested/two.json", pins["nested/two.json"])
        bad_root = temp / "bad-checkout"
        try:
            import_runtime(bad_archive, bad_root, manifest)
        except ImportErrorSafe as exc:
            assert "SHA-256 mismatch" in str(exc)
        else:
            raise AssertionError("A tampered runtime archive must be refused")
        assert not (bad_root / "data/one.txt").exists()

        # Unsafe manifest paths are rejected before archive content is written.
        unsafe_manifest = temp / "unsafe.json"
        unsafe_manifest.write_text(json.dumps({"sha256_files": {"../escape.txt": sha(b"escape")}}), encoding="utf-8")
        unsafe_archive = temp / "unsafe.zip"
        with zipfile.ZipFile(unsafe_archive, "w") as z:
            z.writestr("../escape.txt", b"escape")
        unsafe_root = temp / "unsafe-checkout"
        try:
            import_runtime(unsafe_archive, unsafe_root, unsafe_manifest)
        except ImportErrorSafe as exc:
            assert "Unsafe runtime path" in str(exc)
        else:
            raise AssertionError("Path traversal must be rejected")
        assert not (temp / "escape.txt").exists()

        # A symlinked destination directory must not redirect extracted files.
        outside = temp / "outside"
        outside.mkdir()
        symlink_root = temp / "symlink-checkout"
        symlink_root.mkdir()
        try:
            (symlink_root / "data").symlink_to(outside, target_is_directory=True)
        except OSError:
            pass  # A platform may deny symlink creation; traversal tests still run.
        else:
            try:
                import_runtime(archive, symlink_root, manifest)
            except ImportErrorSafe as exc:
                assert "symlink" in str(exc).lower()
            else:
                raise AssertionError("A symlinked destination must be refused")
            assert not (outside / "one.txt").exists()

    print("PASS: pinned importer verifies all bytes first, is idempotent, refuses collisions/traversal/symlinks, and leaves archives untouched")


if __name__ == "__main__":
    main()
