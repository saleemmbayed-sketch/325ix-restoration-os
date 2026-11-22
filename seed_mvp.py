#!/usr/bin/env python3
"""Create the small reproducible front-axle demo catalog; never touches Drive data."""
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "325ix_assemblies.sqlite3"
DB.parent.mkdir(parents=True, exist_ok=True)
if DB.exists():
    DB.unlink()

assemblies = [
    ("A-776c8e5f755bc176", "front_axle", "front support control arms", "LOCAL_DRIVE_SOURCE_NOT_PUBLIC"),
    ("A-26eb660e7170ed83", "front_axle", "front wheel bearing", "LOCAL_DRIVE_SOURCE_NOT_PUBLIC"),
    ("A-d9c1652de5fb8cfa", "front_axle", "front strut shock absorber", "LOCAL_DRIVE_SOURCE_NOT_PUBLIC"),
    ("A-6746b0e5032fcf50", "steering", "steering linkage tie rods", "LOCAL_DRIVE_SOURCE_NOT_PUBLIC"),
    ("A-b6733a082f6080e2", "steering", "mechanical steering", "LOCAL_DRIVE_SOURCE_NOT_PUBLIC"),
]
parts = [
    ("A-776c8e5f755bc176", "31121701059", "1", "left control arm", "1", "1987-12", "", "", ""),
    ("A-776c8e5f755bc176", "31121701060", "2", "right control arm", "1", "1987-12", "", "", ""),
    ("A-6746b0e5032fcf50", "32211701039", "1", "left tie rod", "1", "1987-12", "", "", ""),
    ("A-6746b0e5032fcf50", "32211701040", "2", "right tie rod", "1", "1987-12", "", "", ""),
    ("A-26eb660e7170ed83", "31211132284", "1", "front wheel bearing candidate; check catalog conditions", "2", "1987-12", "", "", ""),
]
with sqlite3.connect(DB) as db:
    db.executescript("""
      CREATE TABLE assembly(id TEXT PRIMARY KEY, group_name TEXT, slug TEXT, source_url TEXT, downloaded_at TEXT DEFAULT '2026-11-22');
      CREATE TABLE figure(id INTEGER PRIMARY KEY AUTOINCREMENT, assembly_id TEXT, image_asset_id TEXT, figure_url TEXT);
      CREATE TABLE part_row(id INTEGER PRIMARY KEY AUTOINCREMENT, assembly_id TEXT, part_number TEXT, callout_position TEXT, description TEXT, quantity_raw TEXT, date_condition_raw TEXT, supplement TEXT, anchor TEXT, notes TEXT);
    """)
    db.executemany("INSERT INTO assembly(id,group_name,slug,source_url) VALUES(?,?,?,?)", assemblies)
    db.executemany("INSERT INTO part_row(assembly_id,part_number,callout_position,description,quantity_raw,date_condition_raw,supplement,anchor,notes) VALUES(?,?,?,?,?,?,?,?,?)", parts)
    db.commit()
print(f"seeded {DB} with {len(assemblies)} assemblies and {len(parts)} exact-number rows")
