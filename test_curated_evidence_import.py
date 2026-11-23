#!/usr/bin/env python3
"""Regression tests for conservative, resumable curated-evidence snapshot imports."""
import json
import tempfile
from pathlib import Path

from app import sourced_curated
from scripts.import_curated_evidence_snapshot import import_snapshot


def record(number, **overrides):
    value = {
        "part_number": number,
        "evidence_status": "EXACT_NUMBER_SOURCE_REVIEWED; VIN_FITMENT_NOT_APPROVED",
        "reviewed_utc": "2026-11-22T12:00:00+00:00",
        "sources": [{"url": "https://parts.example/item", "status": "EXACT_NUMBER_LISTING; FITMENT_UNVERIFIED"}],
        "conflicts": [],
    }
    value.update(overrides)
    return value


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory(prefix="ix-curated-import-") as temp:
        root = Path(temp)
        nums = [f"1234567890{i}" for i in range(1, 8)]
        registry = root / "registry.json"
        write_json(registry, {"parts": {number: {} for number in nums}})

        existing = record(nums[0])
        local_only = record(nums[6], reviewed_utc="2026-11-20")
        # Keep the last number's independent local dossier even though it does
        # not appear in the incoming Drive snapshot.
        base = root / "base.json"
        write_json(base, {"schema_version": "0.6", "scope": "local overlay", "verified_count": 2,
                          "evidence": {nums[0]: existing, nums[6]: local_only}})

        snapshot = root / "CURATED_EVIDENCE_V40.json"
        rows = {
            nums[0]: record(nums[0]),
            # reviewed_at is an explicit source timestamp. It stays in that
            # field; the importer must not promote it to reviewed_utc.
            nums[1]: {
                "part_number": nums[1],
                "evidence_status": "SOURCE_REVIEWED_NOT_FITMENT_APPROVED",
                "reviewed_at": "2026-11-22T10:00:00+01:00",
                "sources": [{"url": "https://parts.example/second", "status": "EXACT_NUMBER; VERIFY_VARIANT"}],
            },
            # No row-level status: remain a source lead, not active evidence.
            nums[2]: {"part_number": nums[2], "reviewed_at": "2026-11-22T10:00:00+01:00",
                      "sources": [{"url": "https://parts.example/third", "status": "LISTING"}]},
            # Status without an explicit record review timestamp is not promoted.
            nums[3]: record(nums[3], reviewed_utc="", reviewed_at="", source_reviewed_at=""),
            # A URL without an explicit source status is not promoted.
            nums[4]: record(nums[4], sources=[{"url": "https://parts.example/fifth"}]),
            # Never infer row identity from the dictionary key, even when other
            # evidence fields look complete.
            nums[5]: {"evidence_status": "SOURCE_REVIEWED_NOT_FITMENT_APPROVED",
                      "reviewed_at": "2026-11-22T10:00:00+01:00",
                      "sources": [{"url": "https://parts.example/sixth", "status": "EXACT_NUMBER"}]},
        }
        write_json(snapshot, {"schema_version": "0.40", "scope": "Exact-number reviews; not VIN fitment",
                              "as_of": "2026-11-23T08:25:00Z", "prior_overlay": "V39", "verified_count": 6,
                              "evidence": rows})
        output = root / "output.json"
        snapshot_before = snapshot.read_bytes()
        report = import_snapshot(snapshot, base, registry, output)
        imported = json.loads(output.read_text(encoding="utf-8"))
        assert report["input_record_count"] == 6
        assert report["eligible_record_count"] == 2
        assert report["merged_record_count"] == 3
        assert report["source_reviewed_count"] == 3
        assert report["excluded_by_reason"] == {
            "missing_or_mismatched_record_part_number": 1,
            "missing_record_evidence_status": 1,
            "missing_record_review_timestamp": 1,
            "missing_status_bearing_https_source": 1,
        }, report
        assert imported["evidence"][nums[0]] == existing
        preserved = imported["evidence"][nums[1]]
        assert preserved["part_number"] == nums[1]
        assert preserved["reviewed_at"] == "2026-11-22T10:00:00+01:00"
        assert "reviewed_utc" not in preserved
        assert sourced_curated(nums[1], preserved)
        assert not sourced_curated(nums[5], rows[nums[5]])
        assert imported["evidence"][nums[6]] == local_only
        assert imported["source_snapshot"]["input_record_count"] == 6
        assert len(imported["source_snapshot"]["sha256"]) == 64
        assert "no VIN-specific fitment" in imported["count_semantics"]
        assert snapshot.read_bytes() == snapshot_before
        try:
            import_snapshot(snapshot, base, registry, snapshot)
        except ValueError as exc:
            assert "Output cannot overwrite" in str(exc)
        else:
            raise AssertionError("The source snapshot must never be overwritten")

        # A disagreement with an existing local dossier is a hard stop; the
        # prior output must stay byte-identical after the failed import.
        before = output.read_bytes()
        conflicting_base = root / "conflicting_base.json"
        write_json(conflicting_base, {"evidence": {nums[0]: record(nums[0], evidence_status="LOCAL_CONFLICT")}})
        try:
            import_snapshot(snapshot, conflicting_base, registry, output)
        except ValueError as exc:
            assert "Conflicting local and snapshot evidence" in str(exc)
        else:
            raise AssertionError("A conflicting local evidence record must not be overwritten")
        assert output.read_bytes() == before

    print("PASS: explicit exact keys/status/timestamps/sources, verbatim records, local preservation, and collision refusal")


if __name__ == "__main__":
    main()
