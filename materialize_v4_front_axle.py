#!/usr/bin/env python3
"""Materialize only the front-axle diagrams needed by the MVP acceptance path.

The downloaded source manifest is preserved. A derived local manifest records
the exact source URL, local file, checksum and retrieval time.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, tempfile, urllib.request

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / '03_MANIFESTS' / 'image_assets.jsonl'
OUT_MANIFEST = ROOT / '03_MANIFESTS' / 'image_assets_local.jsonl'
IMAGE_ROOT = ROOT / '01_DIAGRAM_IMAGES'
TARGETS = {
    'IMG-d20b4403da1f7395',  # front axle support / wishbone
    'IMG-6a06213e7f530bf7',  # front wheel bearing
    'IMG-301dd470baa03ce2',  # steering linkage / tie rods
}

def main():
    rows = [json.loads(line) for line in MANIFEST.read_text(encoding='utf-8').splitlines() if line.strip()]
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(timezone.utc).isoformat(timespec='seconds')
    selected = 0
    for row in rows:
        if row.get('asset_id') not in TARGETS:
            continue
        url = row.get('url')
        if not isinstance(url, str) or not url.startswith('https://'):
            raise RuntimeError(f"No HTTPS source for {row.get('asset_id')}")
        dest = IMAGE_ROOT / f"{row['asset_id']}.webp"
        if not dest.exists():
            request = urllib.request.Request(url, headers={'User-Agent': 'BMW325iX-Restoration-Workbench/1.0'})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(4_000_000)
            if not data.startswith(b'RIFF') or data[8:12] != b'WEBP':
                raise RuntimeError(f"Unexpected image type for {row['asset_id']}")
            with tempfile.NamedTemporaryFile(dir=IMAGE_ROOT, delete=False) as tmp:
                tmp.write(data); tmp_path = Path(tmp.name)
            os.replace(tmp_path, dest)
        row['local_file'] = f'01_DIAGRAM_IMAGES/{dest.name}'
        row['status'] = 'MATERIALIZED_READ_ONLY'
        row['sha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
        row['retrieved_utc'] = retrieved
        selected += 1
    OUT_MANIFEST.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    print(f'materialized={selected} output={OUT_MANIFEST}')

if __name__ == '__main__':
    main()
