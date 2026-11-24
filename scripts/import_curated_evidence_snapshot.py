#!/usr/bin/env python3
"""Conservatively import row-level source reviews from a Drive evidence snapshot.

The snapshot is never modified. Only records with an explicit matching
part_number, a row-level source-review status, a parseable reviewed_utc or
reviewed_at field, and a status-bearing HTTPS source enter the active overlay.
The source record is preserved verbatim: identity and timestamp fields are
never synthesized or promoted. This does not validate supplier claims, VIN
fitment, specifications, or safety approval.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PART_NUMBER = re.compile(r"\d{11}\Z")
REVIEW_TIME_FIELDS = ("reviewed_utc", "reviewed_at")


def read_json(path: Path):
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_review_timestamp(value) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return True


def has_status_bearing_https_source(record) -> bool:
    sources = record.get("sources")
    if not isinstance(sources, list):
        return False
    for source in sources:
        if not isinstance(source, dict):
            continue
        url = source.get("url")
        status = source.get("status")
        if not isinstance(url, str) or not isinstance(status, str) or not status.strip():
            continue
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        if parsed.scheme == "https" and parsed.netloc:
            return True
    return False


def source_review_record(number: str, record) -> tuple[dict | None, str | None]:
    """Return a minimally normalized record or a conservative exclusion reason."""
    if not PART_NUMBER.fullmatch(number):
        return None, "invalid_part_number_key"
    if not isinstance(record, dict):
        return None, "record_not_object"
    evidence_status = record.get("evidence_status")
    if not isinstance(evidence_status, str) or not evidence_status.strip():
        return None, "missing_record_evidence_status"

    # Require the row's explicit identity field to agree with its exact-number
    # key. Do not populate identity from the dictionary key.
    has_matching_identity = record.get("part_number") == number
    review_time = next(
        (record.get(field) for field in REVIEW_TIME_FIELDS if valid_review_timestamp(record.get(field))),
        None,
    )
    if not has_matching_identity and review_time is None:
        return None, "missing_record_part_number_and_review_timestamp"
    if not has_matching_identity:
        return None, "missing_or_mismatched_record_part_number"
    if review_time is None:
        return None, "missing_record_review_timestamp"

    if not has_status_bearing_https_source(record):
        return None, "missing_status_bearing_https_source"

    # Keep the source record's original fields verbatim. In particular, do not
    # synthesize part_number or promote reviewed_at to reviewed_utc.
    return copy.deepcopy(record), None


def registry_part_numbers(path: Path) -> set[str]:
    registry = read_json(path)
    parts = registry.get("parts") if isinstance(registry, dict) else None
    if not isinstance(parts, dict):
        raise ValueError("Research registry must contain a parts object")
    return set(parts)


def catalog_part_numbers(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    uri = path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "part_record" not in tables:
            raise ValueError("Multimodal catalog has no part_record table")
        return {row[0] for row in db.execute("SELECT DISTINCT part_number FROM part_record WHERE part_number IS NOT NULL")}


def atomic_json_write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        mode = 0o644
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def import_snapshot(snapshot_path: Path, base_path: Path, registry_path: Path,
                    output_path: Path, multimodal_db: Path | None = None) -> dict:
    snapshot_path = snapshot_path.expanduser().resolve()
    base_path = base_path.expanduser().resolve()
    registry_path = registry_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if base_path == snapshot_path:
        raise ValueError("The source snapshot cannot also be the local base overlay")
    if output_path == snapshot_path:
        raise ValueError("Output cannot overwrite the source snapshot")

    snapshot = read_json(snapshot_path)
    source_records = snapshot.get("evidence") if isinstance(snapshot, dict) else None
    if not isinstance(source_records, dict):
        raise ValueError("Evidence snapshot must contain an evidence object")

    registry_numbers = registry_part_numbers(registry_path)
    catalog_numbers = catalog_part_numbers(multimodal_db)
    for number in source_records:
        if not PART_NUMBER.fullmatch(number):
            raise ValueError(f"Snapshot key is not an 11-digit part number: {number!r}")
        if number not in registry_numbers:
            raise ValueError(f"Snapshot part number is absent from the active registry: {number}")
        if catalog_numbers is not None and number not in catalog_numbers:
            raise ValueError(f"Snapshot part number is absent from the V4 catalog: {number}")

    if base_path.is_file():
        base = read_json(base_path)
        base_records = base.get("evidence") if isinstance(base, dict) else None
        if not isinstance(base_records, dict):
            raise ValueError("Base overlay must contain an evidence object")
    else:
        base = {}
        base_records = {}

    accepted = {}
    excluded = Counter()
    for number, record in source_records.items():
        normalized, reason = source_review_record(number, record)
        if reason:
            excluded[reason] += 1
            continue
        accepted[number] = normalized

    # Local records win only when they are absent from the snapshot. A collision
    # is a hard error, not a silent replacement or a guessed reconciliation.
    for number, local_record in base_records.items():
        if not PART_NUMBER.fullmatch(number) or number not in registry_numbers:
            raise ValueError(f"Base overlay key is invalid or absent from the registry: {number!r}")
        if catalog_numbers is not None and number not in catalog_numbers:
            raise ValueError(f"Base overlay part number is absent from the V4 catalog: {number}")
        if number in accepted and accepted[number] != local_record:
            raise ValueError(f"Conflicting local and snapshot evidence for part {number}")

    merged = dict(base_records)
    for number, record in accepted.items():
        merged.setdefault(number, record)

    source_reviewed_count = sum(
        source_review_record(number, record)[1] is None for number, record in merged.items()
    )
    payload = {
        "schema_version": str(snapshot.get("schema_version") or base.get("schema_version") or "1"),
        "scope": str(snapshot.get("scope") or base.get("scope") or "Exact-number source-reviewed records; not fitment certification"),
        # Retained as a compatibility alias; this is a source-review count,
        # never a VIN-fitment, engineering-specification, or safety count.
        "verified_count": source_reviewed_count,
        "source_reviewed_count": source_reviewed_count,
        "count_semantics": "Source-provenance screen only; no VIN-specific fitment, engineering-specification, condition, or safety approval.",
        "source_snapshot": {
            "file_name": snapshot_path.name,
            "sha256": sha256_file(snapshot_path),
            "as_of": snapshot.get("as_of"),
            "prior_snapshot": snapshot.get("prior_overlay"),
            "input_record_count": len(source_records),
            "eligible_record_count": len(accepted),
            "excluded_by_reason": dict(sorted(excluded.items())),
            "import_policy": "Exact 11-digit registry/catalog key + explicit matching record part_number + explicit record evidence_status + parseable reviewed_utc or reviewed_at + status-bearing HTTPS source; original fields preserved, no fitment/specification approval inferred.",
        },
        "evidence": merged,
    }
    atomic_json_write(output_path, payload)
    return {
        "input_record_count": len(source_records),
        "eligible_record_count": len(accepted),
        "merged_record_count": len(merged),
        "source_reviewed_count": source_reviewed_count,
        "excluded_by_reason": dict(sorted(excluded.items())),
        "output": str(output_path),
        "snapshot_sha256": payload["source_snapshot"]["sha256"],
        "registry_part_count": len(registry_numbers),
        "catalog_part_count": len(catalog_numbers) if catalog_numbers is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Downloaded Drive CURATED_EVIDENCE JSON snapshot")
    parser.add_argument("--base", type=Path, default=ROOT / "curated_evidence.json", help="Existing local overlay to preserve")
    parser.add_argument("--registry", type=Path, default=ROOT / "catalog_research_registry.json")
    parser.add_argument("--multimodal-db", type=Path, default=None, help="Optional V4 SQLite DB; every snapshot key must exist there")
    parser.add_argument("--output", type=Path, default=ROOT / "curated_evidence.json")
    args = parser.parse_args()
    try:
        result = import_snapshot(args.snapshot, args.base, args.registry, args.output, args.multimodal_db)
    except (OSError, json.JSONDecodeError, sqlite3.Error, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
