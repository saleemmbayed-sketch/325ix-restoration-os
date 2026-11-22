#!/usr/bin/env python3
"""Restore only app code from the RC 0.7.0 backup; leave all mutable workshop records alone."""
import json,sys,shutil,os,tempfile
from pathlib import Path
from datetime import datetime,timezone

def cp(src,dest):
    with tempfile.NamedTemporaryFile(dir=dest.parent,delete=False) as t:tmp=Path(t.name)
    try:shutil.copyfile(src,tmp);os.replace(tmp,dest)
    finally:tmp.unlink(missing_ok=True)

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else Path.home()/'Desktop'/'325ix_workbench').resolve()
    pointer=root/'RC070_BACKUP_POINTER.json'
    if not pointer.is_file():raise RuntimeError('RC0.7.0 backup pointer not found')
    backup=Path(json.loads(pointer.read_text())['backup_path']).resolve()
    if backup.parent!=root or not backup.name.startswith('upgrade_backup_rc070_'):
        raise RuntimeError('Backup path is not an approved local RC0.7.0 backup')
    manifest=json.loads((backup/'backup_manifest.json').read_text())
    preserve=root/('rollback_preserved_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    preserve.mkdir(mode=0o700)
    files=list(manifest['before'])
    for name in files:
        target=root/name
        if target.exists():shutil.copy2(target,preserve/name)
    for name,digest in manifest['before'].items():
        target=root/name
        if digest is None:target.unlink(missing_ok=True)
        else:cp(backup/name,target)
    pointer.unlink(missing_ok=True)
    print('ROLLED BACK app files to state before RC0.7.0.')
    print('Pre-rollback versions preserved:',preserve)
    print('Workshop job/photo databases and physical photo files left untouched.')
    print('Install-time SQLite snapshots remain available in:',backup)

if __name__=='__main__':
    try:main()
    except Exception as e:print('Rollback failed: '+str(e),file=sys.stderr);sys.exit(2)
