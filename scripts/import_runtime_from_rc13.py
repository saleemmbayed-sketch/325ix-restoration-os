#!/usr/bin/env python3
"""Restore only checksum-pinned RC13 runtime data without overwriting local files.

The original archive, Drive, workshop databases and owner photographs are never
modified. All archive members and destinations are validated before publishing
any file; files are created without replacing an existing path.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "runtime_rc13_sha256.json"


class ImportErrorSafe(ValueError):
    """Invalid archive or a destination that must be investigated manually."""


def _safe_relative(name: str) -> PurePosixPath:
    if (
        not isinstance(name, str)
        or not name
        or "\\" in name
        or "\x00" in name
        or ":" in name
        or any(ord(ch) < 32 for ch in name)
    ):
        raise ImportErrorSafe(f"Unsafe runtime path: {name!r}")
    rel = PurePosixPath(name)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise ImportErrorSafe(f"Unsafe runtime path: {name!r}")
    if rel.as_posix() != name:
        raise ImportErrorSafe(f"Runtime path is not canonical POSIX form: {name!r}")
    return rel


def _destination(root: Path, name: str) -> Path:
    rel = _safe_relative(name)
    root_real = root.resolve()
    target = root.joinpath(*rel.parts)
    # Reject symlinks anywhere below the selected root, including a dangling
    # symlink that Path.exists() alone would not report.
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ImportErrorSafe(f"Refusing symlink in runtime destination: {cursor}")
    try:
        target.resolve(strict=False).relative_to(root_real)
    except (OSError, ValueError) as exc:
        raise ImportErrorSafe(f"Runtime destination escapes selected root: {name}") from exc
    return target


def import_runtime(archive: Path, root: Path = ROOT, manifest_path: Path = MANIFEST) -> tuple[int, int]:
    """Validate then install the pinned files. Returns (installed, already present)."""
    archive = Path(archive).expanduser().resolve()
    root = Path(root).expanduser().resolve()
    manifest_path = Path(manifest_path).expanduser().resolve()
    if not archive.is_file():
        raise ImportErrorSafe(f"RC13 source ZIP not found: {archive}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportErrorSafe(f"Cannot read runtime pin manifest: {exc}") from exc
    pins = document.get("sha256_files")
    if not isinstance(pins, dict) or not pins:
        raise ImportErrorSafe("Runtime pin manifest has no sha256_files mapping")

    safe_names = {name: _safe_relative(name) for name in pins}
    for name, wanted in pins.items():
        if not isinstance(wanted, str) or len(wanted) != 64 or any(c not in "0123456789abcdefABCDEF" for c in wanted):
            raise ImportErrorSafe(f"Invalid SHA-256 pin for {name!r}")

    root.mkdir(parents=True, exist_ok=True)
    root_real = root.resolve()
    staged_payloads: dict[str, bytes] = {}
    already_present = 0

    try:
        with zipfile.ZipFile(archive) as source:
            members: dict[str, list[zipfile.ZipInfo]] = {}
            for info in source.infolist():
                members.setdefault(info.filename, []).append(info)
            for name in safe_names:
                matches = members.get(name, [])
                if len(matches) != 1:
                    raise ImportErrorSafe(f"Expected one archive entry for {name!r}; found {len(matches)}")
                mode = matches[0].external_attr >> 16
                if stat.S_ISLNK(mode) or matches[0].is_dir():
                    raise ImportErrorSafe(f"Archive member is not a regular file: {name}")

            # Verify every source byte and every existing target before creating
            # anything in the destination tree.
            for name, wanted in pins.items():
                target = _destination(root, name)
                payload = source.read(members[name][0])
                actual = hashlib.sha256(payload).hexdigest()
                if actual.lower() != wanted.lower():
                    raise ImportErrorSafe(f"RC13 SHA-256 mismatch: {name}")
                if target.exists():
                    if not target.is_file():
                        raise ImportErrorSafe(f"Existing runtime destination is not a regular file: {target}")
                    if hashlib.sha256(target.read_bytes()).hexdigest().lower() != wanted.lower():
                        raise ImportErrorSafe(
                            f"Existing file does not match immutable RC13: {name}. "
                            "Leave it unchanged and investigate separately."
                        )
                    already_present += 1
                else:
                    staged_payloads[name] = payload

        if not staged_payloads:
            return 0, already_present

        # Stage on the same filesystem. Publish with exclusive hard links so an
        # existing file can never be replaced by a race or an accidental retry.
        stage_dir = Path(tempfile.mkdtemp(prefix=".rc13-import-", dir=root_real))
        created: list[tuple[Path, int, int]] = []
        try:
            staged_paths: dict[str, Path] = {}
            for name, payload in staged_payloads.items():
                rel = safe_names[name]
                staged = stage_dir.joinpath(*rel.parts)
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_bytes(payload)
                staged_paths[name] = staged

            for name, staged in staged_paths.items():
                target = _destination(root, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    os.link(staged, target)
                    staged_stat = staged.stat()
                    created.append((target, staged_stat.st_dev, staged_stat.st_ino))
                    published_stat = target.lstat()
                    if (published_stat.st_dev, published_stat.st_ino) != (staged_stat.st_dev, staged_stat.st_ino):
                        raise ImportErrorSafe(f"Published destination changed during import: {target}")
                except FileExistsError as exc:
                    raise ImportErrorSafe(f"Destination appeared during import; refusing to overwrite: {target}") from exc
                except OSError as exc:
                    # Some filesystems disallow hard links; retain no-overwrite
                    # semantics by using O_EXCL for a direct copy instead.
                    unsupported = {errno.EXDEV, errno.EPERM, errno.ENOTSUP}
                    if hasattr(errno, "EOPNOTSUPP"):
                        unsupported.add(errno.EOPNOTSUPP)
                    if exc.errno not in unsupported:
                        raise
                    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
                    st = os.fstat(fd)
                    created.append((target, st.st_dev, st.st_ino))
                    with os.fdopen(fd, "wb") as out, staged.open("rb") as inp:
                        shutil.copyfileobj(inp, out)
                        out.flush()
                        os.fsync(out.fileno())
        except Exception:
            # Track the exact inode created by this call so even a failed
            # fallback copy rolls back, while a concurrent/user replacement is
            # never unlinked.
            for target, device, inode in reversed(created):
                try:
                    st = target.lstat()
                    if (st.st_dev, st.st_ino) == (device, inode):
                        target.unlink()
                except OSError:
                    pass
            raise
        finally:
            shutil.rmtree(stage_dir, ignore_errors=True)

        return len(created), already_present
    except zipfile.BadZipFile as exc:
        raise ImportErrorSafe(f"Invalid RC13 ZIP archive: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore only SHA-256-pinned derived runtime data from the approved RC13 ZIP"
    )
    parser.add_argument("archive", type=Path, help="Path to the approved RC13 ZIP; the archive is read-only")
    parser.add_argument(
        "--root", type=Path, default=ROOT,
        help="Source checkout to restore into (default: this repository; useful for isolated verification)",
    )
    parser.add_argument("--manifest", type=Path, default=MANIFEST, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        installed, existing = import_runtime(args.archive, args.root, args.manifest)
    except (ImportErrorSafe, OSError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(f"Imported {installed} pinned runtime data files; already present: {existing}")
    print("Original ZIP, source-of-truth data and existing workshop records were not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
