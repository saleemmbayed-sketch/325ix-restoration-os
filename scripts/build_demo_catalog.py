#!/usr/bin/env python3
"""Build a small synthetic catalog for safe, offline UI testing.

This fixture contains no BMW source data and makes no claims about real part
numbers, drawings, fitment, repair procedures, or any real vehicle. It only
uses Python's standard library.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "local_demo_catalog.json"
DEMO_MARKER = "325IX_SYNTHETIC_LOCAL_DEMO_V1"
ALLOWED_GROUPS = {
    "front_axle", "steering", "brakes", "transfer_box_electric_gearbox",
    "vehicle_electrical_system",
}


def load_fixture(path: Path = FIXTURE) -> dict:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if fixture.get("fixture_version") != 1:
        raise ValueError("Unsupported demo fixture version")
    assemblies = fixture.get("assemblies")
    parts = fixture.get("parts")
    figures = fixture.get("figures")
    if not isinstance(assemblies, list) or len(assemblies) != 5:
        raise ValueError("The local demo fixture must contain exactly five synthetic assemblies")
    if not isinstance(parts, list) or not parts:
        raise ValueError("The local demo fixture has no synthetic catalog rows")
    if figures != []:
        raise ValueError("Local demo fixture must not bundle or imply OEM drawings")
    assembly_ids = set()
    for assembly in assemblies:
        if assembly.get("group_name") not in ALLOWED_GROUPS:
            raise ValueError("Unexpected system in demo assembly: " + str(assembly.get("group_name")))
        if not assembly.get("id", "").startswith("demo-") or not assembly.get("slug", "").startswith("demo_"):
            raise ValueError("Demo assembly IDs and slugs must be visibly synthetic")
        if assembly["id"] in assembly_ids:
            raise ValueError("Duplicate demo assembly ID")
        assembly_ids.add(assembly["id"])
    part_ids = set()
    for part in parts:
        if not part.get("id", "").startswith("demo-") or not part.get("part_number", "").startswith("DEMO-"):
            raise ValueError("Demo part IDs and numbers must be visibly synthetic")
        if part.get("assembly_id") not in assembly_ids:
            raise ValueError("Demo part refers to an unknown assembly")
        if part["id"] in part_ids:
            raise ValueError("Duplicate demo part ID")
        part_ids.add(part["id"])
    return fixture


def is_demo_catalog(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True) as db:
            marker = db.execute(
                "SELECT value FROM demo_metadata WHERE key='marker'"
            ).fetchone()
            integrity = db.execute("PRAGMA quick_check").fetchone()
            return bool(marker and marker[0] == DEMO_MARKER and integrity and integrity[0] == "ok")
    except sqlite3.Error:
        return False


def build(output: Path, *, force: bool = False, fixture_path: Path = FIXTURE) -> Path:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if not force:
            raise FileExistsError(f"Refusing to overwrite existing file: {output}; pass --force only for a verified demo catalog")
        if not is_demo_catalog(output):
            raise ValueError("Refusing to replace an existing file that is not marked as this synthetic demo catalog")

    fixture = load_fixture(fixture_path)
    fd, temp_name = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        with sqlite3.connect(temp) as db:
            db.executescript("""
                PRAGMA foreign_keys = ON;
                CREATE TABLE demo_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE assembly (
                    id TEXT PRIMARY KEY,
                    group_name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    downloaded_at TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE part_row (
                    id TEXT PRIMARY KEY,
                    assembly_id TEXT NOT NULL REFERENCES assembly(id),
                    part_number TEXT NOT NULL,
                    description TEXT NOT NULL,
                    callout_position TEXT NOT NULL DEFAULT '',
                    quantity_raw TEXT NOT NULL DEFAULT '',
                    date_condition_raw TEXT NOT NULL DEFAULT '',
                    supplement TEXT NOT NULL DEFAULT '',
                    anchor TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE figure (
                    assembly_id TEXT NOT NULL REFERENCES assembly(id),
                    image_asset_id TEXT NOT NULL DEFAULT '',
                    figure_url TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX idx_demo_assembly_group ON assembly(group_name);
                CREATE INDEX idx_demo_part_assembly ON part_row(assembly_id);
                CREATE INDEX idx_demo_part_number ON part_row(part_number);
            """)
            db.executemany(
                "INSERT INTO demo_metadata(key,value) VALUES(?,?)",
                [
                    ("marker", DEMO_MARKER),
                    ("fixture_version", str(fixture["fixture_version"])),
                    ("notice", fixture["notice"]),
                    ("assembly_count", str(len(fixture["assemblies"]))),
                    ("part_count", str(len(fixture["parts"]))),
                ],
            )
            db.executemany(
                "INSERT INTO assembly(id,group_name,slug,source_url,downloaded_at) VALUES(?,?,?,?,?)",
                [
                    (row["id"], row["group_name"], row["slug"], "", "SYNTHETIC_DEMO_ONLY")
                    for row in fixture["assemblies"]
                ],
            )
            db.executemany(
                """INSERT INTO part_row(
                    id,assembly_id,part_number,description,callout_position,quantity_raw,
                    date_condition_raw,supplement,anchor,notes
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        row["id"], row["assembly_id"], row["part_number"], row["description"],
                        row.get("callout_position", ""), row.get("quantity_raw", ""),
                        row.get("date_condition_raw", "DEMO ONLY"), row.get("supplement", ""),
                        row.get("anchor", ""), row.get("notes", ""),
                    )
                    for row in fixture["parts"]
                ],
            )
            db.execute("PRAGMA user_version = 32501")
            db.commit()
            integrity = db.execute("PRAGMA quick_check").fetchone()[0]
            if integrity != "ok":
                raise sqlite3.DatabaseError("Generated demo catalog failed quick_check: " + str(integrity))
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    if not is_demo_catalog(output):
        output.unlink(missing_ok=True)
        raise sqlite3.DatabaseError("Generated catalog did not retain its demo marker")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Output SQLite path; existing files are protected")
    parser.add_argument("--fixture", type=Path, default=FIXTURE, help="Synthetic JSON fixture (defaults to the bundled fixture)")
    parser.add_argument("--force", action="store_true", help="Replace only an existing catalog with this demo's marker")
    args = parser.parse_args()
    try:
        output = build(args.output, force=args.force, fixture_path=args.fixture.expanduser())
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    with sqlite3.connect(f"file:{output}?mode=ro", uri=True) as db:
        assemblies = db.execute("SELECT count(*) FROM assembly").fetchone()[0]
        parts = db.execute("SELECT count(*) FROM part_row").fetchone()[0]
    print(f"Built {DEMO_MARKER}: {assemblies} synthetic assemblies, {parts} synthetic rows")
    print(f"Catalog: {output}")
    print("No OEM data, photos, drawings, fitment, or repair instructions are included.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
