#!/usr/bin/env python3
"""Launch RC12 against an isolated SQLite copy of the owner's workshop jobs."""
import argparse
from pathlib import Path
import socket
import sqlite3
import subprocess
import signal
import sys
import time
import webbrowser

ROOT=Path(__file__).resolve().parent

def healthy(path):
    with sqlite3.connect(path) as db:return db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

def port_available(port):
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try:probe.bind(('127.0.0.1',port));return True
        except OSError:return False

def choose_port(preferred):
    for port in range(preferred,preferred+100):
        if port_available(port):return port
    raise RuntimeError(f'No free local port found from {preferred} to {preferred+99}')

def main():
    p=argparse.ArgumentParser(description='Run RC12 without modifying the current Workbench job database')
    p.add_argument('--source-jobs',type=Path,default=Path.home()/'Desktop'/'325ix_workbench'/'workshop_jobs.sqlite3')
    p.add_argument('--trial-dir',type=Path,default=ROOT/'rc12_trial_state')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--no-browser',action='store_true',help='Do not open the selected URL automatically')
    p.add_argument('--retry-3d',action='store_true',help='Reattempt licensed viewer asset preparation')
    p.add_argument('--skip-3d',action='store_true',help='Start with 2D fallback without downloading 3D assets')
    args=p.parse_args();source=args.source_jobs.expanduser().resolve();trial=args.trial_dir.expanduser().resolve()
    if not source.is_file():print('No existing owner job database was found; a NEW isolated trial database will be created. No live owner records touched.')
    trial.mkdir(parents=True,exist_ok=True);jobs=trial/'workshop_jobs_rc12_trial.sqlite3';photos=trial/'actual_part_photos'
    if not jobs.exists() and source.is_file():
        with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True,timeout=8) as current:
            with sqlite3.connect(jobs) as copy:current.backup(copy)
        if not healthy(jobs):jobs.unlink(missing_ok=True);p.error('Trial copy failed SQLite integrity check')
        print('Created isolated trial copy:',jobs)
    elif not jobs.exists():print('Starting with a NEW trial database:',jobs)
    elif not healthy(jobs):p.error('Existing RC12 trial database failed integrity check: '+str(jobs))
    port=choose_port(args.port)
    if port!=args.port:print(f'Port {args.port} is already in use; RC12 will use port {port} instead.')
    if source.is_file():print('Original job database remains unchanged:',source)
    if not args.skip_3d:
        installed=(ROOT/'models/e30_reference_m3.glb').is_file() and (ROOT/'vendor/three/build/three.module.js').is_file()
        attempted=(ROOT/'models/asset-install-report.json').exists()
        if (not installed) and (not attempted or args.retry_3d):
            print('One-time 3D asset preparation (network needed); 2D remains available if unavailable.',flush=True)
            try:
                prep=subprocess.run([sys.executable,str(ROOT/'scripts/prepare_3d_assets.py')],cwd=ROOT,timeout=150,check=False)
                if prep.returncode:print('3D sources incomplete; 2D catalog and other features still work.')
            except (OSError,subprocess.TimeoutExpired) as e:print('3D setup unavailable:',e)
    print('Isolated trial database:',jobs)
    url='http://127.0.0.1:'+str(port);print('RC12 address:',url)
    process=subprocess.Popen([sys.executable,str(ROOT/'app.py'),'--jobs',str(jobs),'--photo-root',str(photos),'--port',str(port)])
    def stop_launcher(_signal,_frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop_launcher)
    if hasattr(signal,'SIGHUP'):signal.signal(signal.SIGHUP,stop_launcher)
    try:
        ready=False
        for _ in range(80):
            if process.poll() is not None:raise RuntimeError('RC12 server exited before becoming ready')
            if not port_available(port):ready=True;break
            time.sleep(.1)
        if not ready:raise RuntimeError('RC12 server did not become ready in time')
        if not args.no_browser:webbrowser.open(url,new=2)
        print('RC12 is running. Keep this window open; press Ctrl+C to stop.')
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        print('\nRC12 stopped.')
        return 0
    finally:
        if process.poll() is None:process.terminate()

if __name__=='__main__':sys.exit(main())
