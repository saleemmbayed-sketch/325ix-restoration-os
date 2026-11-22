#!/usr/bin/env python3
"""Guarded restore for a BMW 325iX Workbench job-database backup."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import os
import shutil
import sqlite3
import sys

def integrity(path):
    try:
        with sqlite3.connect('file:'+str(path.resolve())+'?mode=ro',uri=True) as db:
            return db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    except sqlite3.DatabaseError:return False

def main():
    p=argparse.ArgumentParser(description='Restore an explicit Workbench SQLite backup after stopping the app')
    p.add_argument('--jobs',type=Path,required=True)
    p.add_argument('--backup',type=Path,required=True)
    p.add_argument('--confirm-replace',action='store_true')
    args=p.parse_args();jobs=args.jobs.resolve();backup=args.backup.resolve()
    if not args.confirm_replace:p.error('Refusing to replace the job database without --confirm-replace')
    if not jobs.is_file():p.error('Current job database not found: '+str(jobs))
    if not backup.is_file() or backup==jobs:p.error('Valid separate backup file required')
    wal=Path(str(jobs)+'-wal')
    if wal.exists() and wal.stat().st_size:p.error('Active/non-empty WAL detected. Stop the Workbench before restoring.')
    if not integrity(backup):p.error('Backup failed SQLite integrity check')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    safety=jobs.with_name(jobs.stem+f'.pre-restore.{stamp}.sqlite3')
    shutil.copy2(jobs,safety)
    if not integrity(safety):p.error('Safety copy of current database failed integrity check')
    staged=jobs.with_name(jobs.name+'.restore-staged')
    shutil.copy2(backup,staged)
    os.replace(staged,jobs)
    for suffix in ('-shm','-wal'):
        sidecar=Path(str(jobs)+suffix)
        if sidecar.exists() and sidecar.stat().st_size==0:sidecar.unlink()
    print(f'Restored {jobs} from {backup}')
    print(f'Previous current database preserved at {safety}')
    return 0

if __name__=='__main__':sys.exit(main())
