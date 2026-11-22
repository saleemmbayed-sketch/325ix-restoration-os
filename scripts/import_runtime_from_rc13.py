#!/usr/bin/env python3
"""Import only pinned RC13 derived runtime data without overwriting any existing file.
Never touches the original ZIP, Drive, or any jobs/photos; no third-party dependencies.
"""
import json,sys,zipfile,hashlib,argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs'/'runtime_rc13_sha256.json'

def main():
  parser=argparse.ArgumentParser(description='Copy runtime-only data from the exact approved RC13 ZIP into a GitHub source checkout')
  parser.add_argument('archive',type=Path)
  args=parser.parse_args()
  pins=json.loads(MANIFEST.read_text())['sha256_files']
  if not args.archive.is_file():parser.error('RC13 source ZIP not found')
  with zipfile.ZipFile(args.archive) as z:
    entries=set(z.namelist())
    absent=[name for name in pins if name not in entries]
    if absent:parser.error('Archive missing '+str(absent[:4]))
    installed=0;existing=0
    for name,wanted in pins.items():
      if not name or Path(name).is_absolute() or '..' in Path(name).parts:parser.error('Unsafe archive entry '+name)
      target=ROOT/name
      if target.is_file():
        if hashlib.sha256(target.read_bytes()).hexdigest()!=wanted:parser.error('Existing file does not match immutable RC13: '+name+'. Leave unchanged and investigate separately.')
        existing+=1;continue
      source=z.read(name)
      if hashlib.sha256(source).hexdigest()!=wanted:parser.error('RC13 hash mismatch: '+name)
      target.parent.mkdir(parents=True,exist_ok=True)
      tmp=target.with_suffix(target.suffix+'.importing');tmp.write_bytes(source);tmp.replace(target);installed+=1
    print('Imported',installed,'pinned runtime data files; already present:',existing)
    print('Original ZIP and any existing jobs/photos were not changed.')
  return 0
if __name__=='__main__':sys.exit(main())
