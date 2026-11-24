#!/usr/bin/env python3
"""Run the complete RC21 V4 workbench with isolated, persistent trial jobs."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from launch_rc12_trial import choose_port, healthy


def find_v4(explicit: Path | None) -> Path:
    home = Path.home()
    candidates = ([explicit] if explicit else [
        ROOT / 'google_drive' / '14_MULTIMODAL_MEDIA_AND_GRAPH',
        ROOT.parent / '14_MULTIMODAL_MEDIA_AND_GRAPH',
        home / 'Desktop' / '14_MULTIMODAL_MEDIA_AND_GRAPH',
        home / 'Google Drive' / '325IX DATA' / '14_MULTIMODAL_MEDIA_AND_GRAPH',
        home / 'Library' / 'CloudStorage' / 'GoogleDrive-saleemmbayed' / 'My Drive' / '325IX DATA' / '14_MULTIMODAL_MEDIA_AND_GRAPH',
    ])
    for candidate in candidates:
        root = candidate.expanduser().resolve()
        if (root / '04_SEARCH' / '325ix_multimodal.sqlite3').is_file():
            return root
    raise FileNotFoundError('V4 catalog not found. Pass --v4-root with the local 14_MULTIMODAL_MEDIA_AND_GRAPH folder.')


def check_v4(root: Path) -> tuple[int, int]:
    catalog = root / '04_SEARCH' / '325ix_multimodal.sqlite3'
    uri = catalog.as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('V4 catalog failed SQLite quick_check')
        assemblies = db.execute('SELECT count(*) FROM assembly').fetchone()[0]
        parts = db.execute('SELECT count(*) FROM part_record').fetchone()[0]
    if (assemblies, parts) != (805, 13845):
        raise ValueError(f'V4 catalog incomplete: {assemblies} assemblies / {parts} parts')
    return assemblies, parts


def copy_once(source: Path, destination: Path, allow_empty: bool = False) -> None:
    if destination.exists():
        if not healthy(destination):
            raise ValueError(f'Existing trial database failed integrity check: {destination}')
        return
    if not source.is_file():
        if allow_empty:
            return
        raise FileNotFoundError(f'Original job database not found: {source}. Pass --source-jobs or --fresh-trial explicitly.')
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=10) as original:
        with sqlite3.connect(destination) as trial:
            original.backup(trial)
    if not healthy(destination):
        destination.unlink(missing_ok=True)
        raise ValueError(f'Trial copy failed integrity check: {destination}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v4-root', type=Path, help='Local V4 folder containing 03_MANIFESTS and 04_SEARCH')
    parser.add_argument('--source-jobs', type=Path, default=Path.home() / 'Desktop' / '325ix_workbench' / 'workshop_jobs.sqlite3')
    parser.add_argument('--trial-dir', type=Path, default=ROOT / 'rc21_full_trial_state')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--ollama-model', help='Optional installed local model')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--fresh-trial', action='store_true', help='Explicitly start with empty trial jobs if the source DB is absent')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Port must be between 1024 and 65535')
    try:
        v4 = find_v4(args.v4_root)
        assemblies, parts = check_v4(v4)
        trial = args.trial_dir.expanduser().resolve()
        if trial == v4 or v4 in trial.parents:
            raise ValueError('Trial state must be outside the read-only V4 folder')
        trial.mkdir(parents=True, exist_ok=True)
        jobs = trial / 'workshop_jobs.sqlite3'
        source = args.source_jobs.expanduser().resolve()
        if source != jobs:
            copy_once(source, jobs, allow_empty=args.fresh_trial)
        port = choose_port(args.port)
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.error(str(exc))
    command = [sys.executable, str(ROOT / 'app.py'), '--v4-root', str(v4),
               '--jobs', str(jobs), '--photo-db', str(trial / 'part_photos.sqlite3'),
               '--photo-root', str(trial / 'actual_part_photos'), '--port', str(port)]
    manual = ROOT / 'maintenance_manual_index.sqlite3'
    if manual.is_file():
        command.extend(['--manual-index', str(manual)])
    if args.ollama_model:
        command.extend(['--ollama-model', args.ollama_model])
    missing = [p for p in ('vendor/three/build/three.module.js',
              'vendor/three/examples/jsm/controls/OrbitControls.js',
              'vendor/three/examples/jsm/loaders/GLTFLoader.js',
              'vendor/meshopt_decoder.module.js') if not (ROOT / p).is_file()]
    print(f'RC21 full V4: {assemblies} assemblies / {parts} catalog rows', flush=True)
    print('Read-only V4:', v4, flush=True)
    print('Trial jobs:', jobs, '(existing trial reused, owner DB copied, or explicit fresh trial)', flush=True)
    print('3D runtime:', 'ready' if not missing else 'missing ' + ', '.join(missing), flush=True)
    print('AI model:', args.ollama_model or 'disabled', flush=True)
    url = f'http://127.0.0.1:{port}/#twin'
    process = subprocess.Popen(command, cwd=ROOT)
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError(f'Workbench stopped during startup (exit {process.returncode})')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/vehicle', timeout=.5):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('Workbench did not become ready')
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v4/status', timeout=60) as response:
            v4_status = json.load(response)
        print('V4 image integrity:', v4_status.get('integrity_status', 'UNKNOWN'),
              '·', v4_status.get('images_hash_verified', 0), '/',
              v4_status.get('manifest_assets', 0), 'local images verified', flush=True)
        if v4_status.get('integrity_status') != 'VERIFIED':
            print('Inspect /api/v4/status for missing images or manifest/catalog differences.', flush=True)
        print('Open:', url, flush=True)
        print('Keep this window open; Ctrl+C stops the server.', flush=True)
        if not args.no_browser:
            webbrowser.open(url, new=2)
        return process.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    sys.exit(main())
