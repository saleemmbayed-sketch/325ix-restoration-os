#!/usr/bin/env python3
"""Safe in-place staging installer for Workbench RC 0.7.0. No third-party packages."""
import json,os,sys,sqlite3,shutil,hashlib,tempfile,tarfile
from pathlib import Path
from datetime import datetime,timezone

FILES=('app.py','index.html','site.js','site.css','sources_extra.json',
       'index_manuals.py','catalog_research_registry.json','curated_evidence.json',
       'README_RC070.md','front_axle_expert_v1.json','rollback_upgrade.sh','rollback_070.py')

def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def copy_atomic(src,dst):
    with tempfile.NamedTemporaryFile(dir=dst.parent,delete=False) as f:tmp=Path(f.name)
    try:shutil.copyfile(src,tmp);os.replace(tmp,dst)
    finally:tmp.unlink(missing_ok=True)

def main():
    if sys.version_info<(3,10):raise RuntimeError('Python 3.10+ required; use Python 3.11 on Monterey')
    kit=Path(__file__).resolve().parent
    root=Path(sys.argv[1] if len(sys.argv)>1 else Path.home()/'Desktop'/'325ix_workbench').expanduser().resolve()
    if not all((root/p).is_file() for p in ['app.py','sources.json','data/325ix_assemblies.sqlite3']):
        raise RuntimeError('Existing Workbench not found: '+str(root))
    # Force the user to stop the old server; do not write into a live code installation.
    import socket
    with socket.socket() as sock:
        sock.settimeout(.15)
        if sock.connect_ex(('127.0.0.1',8765))==0:
            raise RuntimeError('Port 8765 is active. Stop the Workbench with Ctrl+C before installing')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=root/('upgrade_backup_rc070_'+stamp)
    if backup.exists():raise RuntimeError('Backup collision; retry in one second')
    backup.mkdir(mode=0o700)
    manifest={'created_utc':stamp,'release':'RC0.7.0','before':{},'after':{},'data_snapshots':[],
              'photo_files_untouched':True,'notes':'Restore code with rollback_upgrade.sh; mutable DBs never overwritten by installer or normal rollback.'}
    written=[]
    try:
        for name in FILES:
            dest=root/name
            if dest.exists():
                shutil.copy2(dest,backup/name)
                manifest['before'][name]=digest(backup/name)
            else:manifest['before'][name]=None
        for name in ('workshop_jobs.sqlite3','part_photos.sqlite3'):
            src=root/name
            if src.is_file():
                dst=backup/name
                # sqlite3 backup sees committed records even if source is WAL-backed.
                with sqlite3.connect('file:'+str(src)+'?mode=ro',uri=True) as conn:
                    with sqlite3.connect(dst) as dest:conn.backup(dest)
                manifest['data_snapshots'].append(name)
        photo_dir=root/'actual_part_photos'
        if photo_dir.is_dir():
            with tarfile.open(backup/'actual_part_photos.tar.gz','w:gz') as tf:
                tf.add(photo_dir,arcname='actual_part_photos')
            manifest['data_snapshots'].append('actual_part_photos.tar.gz')
        new=json.loads((kit/'curated_evidence.json').read_text(encoding='utf-8'))
        original_path=root/'curated_evidence.json'
        previous=json.loads(original_path.read_text(encoding='utf-8')) if original_path.is_file() else {'evidence':{}}
        assert isinstance(new.get('evidence'),dict) and isinstance(previous.get('evidence'),dict)
        conflicts=[]
        for number,record in previous['evidence'].items():
            if number in new['evidence'] and new['evidence'][number]!=record:conflicts.append(number)
            new['evidence'][number]=record # Existing local record wins; never silent conflict.
        new['verified_count']=len(new['evidence'])
        temp_cur=backup/'merged_curated.json'
        temp_cur.write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding='utf-8')
        manifest['curated_conflicts_preserved_locally']=conflicts
        manifest['merged_curated_records']=len(new['evidence'])
        for name in FILES:
            src=(temp_cur if name=='curated_evidence.json' else kit/name)
            if not src.is_file():raise RuntimeError('Missing upgrade file '+name)
            copy_atomic(src,root/name);written.append(name)
            manifest['after'][name]=digest(root/name)
        # Manifest and pointer are installed last; failures roll back code.
        (backup/'backup_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        pointer=root/'RC070_BACKUP_POINTER.json'
        pointer.write_text(json.dumps({'backup_path':str(backup),'release':'RC0.7.0'},indent=2))
        print('STAGED: Workbench RC0.7.0 (INTERNAL PILOT ONLY)')
        print('Backups:',backup)
        print('Snapshot databases:',', '.join(manifest['data_snapshots']))
        print('Curated evidence merged:',manifest['merged_curated_records'])
        print('Local conflicts preserved:',len(conflicts))
        print('No workshop jobs, catalog rows or V4 images were modified.')
        print('Start with Python 3.11: cd',root,'&& python3 app.py')
        print('Rollback: bash',root/'rollback_upgrade.sh')
    except Exception:
        for name in reversed(written):
            if manifest['before'][name] is None:(root/name).unlink(missing_ok=True)
            else:copy_atomic(backup/name,root/name)
        raise

if __name__=='__main__':
    try:main()
    except Exception as e:print('Upgrade failed; existing code restored: '+str(e),file=sys.stderr);sys.exit(2)
