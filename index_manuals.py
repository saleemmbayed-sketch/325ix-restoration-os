#!/usr/bin/env python3
"""Index user-authorized local .txt/.md manual transcriptions with page IDs.

No web scraping or retrieval. No claim that text is BMW-official or that
market applicability has been checked. Original files remain untouched.

Optional <basename>.metadata.json fields: title, source_url, market,
variant_scope, document_type, source_kind, authority, verification_status,
retrieved_utc. The index stores content and page hashes so retrieval can cite
the exact imported evidence without confusing a URL pointer with read text.
"""
import argparse,hashlib,json,re,sqlite3
from datetime import datetime, timezone
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--input',type=Path,required=True,help='Folder containing user-supplied *.txt / *.md files')
p.add_argument('--output',type=Path,default=Path(__file__).with_name('manual_index.sqlite3'))
a=p.parse_args()
if not a.input.is_dir():p.error('Manual input folder does not exist')
files=sorted(x for x in a.input.rglob('*') if x.is_file() and x.suffix.lower() in ('.txt','.md'))
# Build atomically so interrupted indexing never corrupts existing knowledge.
tmp=a.output.with_name(a.output.name+'.tmp');tmp.parent.mkdir(parents=True,exist_ok=True)
if tmp.exists():tmp.unlink()
con=sqlite3.connect(tmp)
con.executescript('''CREATE TABLE manual_doc(id TEXT PRIMARY KEY,title TEXT NOT NULL,source_url TEXT NOT NULL,
market TEXT NOT NULL,verification_status TEXT NOT NULL,variant_scope TEXT NOT NULL,
document_type TEXT NOT NULL,source_kind TEXT NOT NULL,authority TEXT NOT NULL,
retrieved_utc TEXT NOT NULL,original_path TEXT NOT NULL,sha256 TEXT NOT NULL);
CREATE TABLE manual_page(id INTEGER PRIMARY KEY,doc_id TEXT NOT NULL,page_label TEXT NOT NULL,
body TEXT NOT NULL,page_sha256 TEXT NOT NULL,FOREIGN KEY(doc_id) REFERENCES manual_doc(id));
CREATE TABLE manual_claim(id TEXT PRIMARY KEY,doc_id TEXT NOT NULL,conflict_key TEXT NOT NULL,
claim_text TEXT NOT NULL,value TEXT NOT NULL,source_locator TEXT NOT NULL,status TEXT NOT NULL,
FOREIGN KEY(doc_id) REFERENCES manual_doc(id));
CREATE INDEX page_doc ON manual_page(doc_id);
CREATE INDEX claim_conflict ON manual_claim(conflict_key);
''')
count=0
retrieved_utc=datetime.now(timezone.utc).isoformat(timespec='seconds')
for file in files:
    if file.stat().st_size>15_000_000:print('SKIP >15MB:',file.name);continue
    raw=file.read_bytes()
    txt=raw.decode('utf-8',errors='replace')
    # Sidecar metadata file: <basename>.metadata.json, never indexed.
    meta_path=file.with_name(file.stem+'.metadata.json')
    meta=json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.is_file() else {}
    ident='MNL-'+hashlib.sha256(str(file.relative_to(a.input)).encode()).hexdigest()[:16]
    con.execute('INSERT INTO manual_doc VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(
        ident,str(meta.get('title') or file.name)[:200],str(meta.get('source_url') or '')[:1000],
        str(meta.get('market') or 'UNVERIFIED')[:100],
        str(meta.get('verification_status') or 'USER_IMPORTED; NOT_INDEPENDENTLY_AUTHENTICATED')[:160],
        str(meta.get('variant_scope') or 'UNVERIFIED')[:160],
        str(meta.get('document_type') or 'MANUAL_TRANSCRIPTION')[:100],
        str(meta.get('source_kind') or 'USER_SUPPLIED_TEXT')[:100],
        str(meta.get('authority') or 'UNVERIFIED')[:160],
        str(meta.get('retrieved_utc') or retrieved_utc)[:40],
        str(file.relative_to(a.input)),hashlib.sha256(raw).hexdigest()))
    claims=meta.get('claims',[])
    if isinstance(claims,list):
        for idx,claim in enumerate(claims,1):
            if not isinstance(claim,dict):continue
            conflict_key=str(claim.get('conflict_key') or '').strip()[:160]
            value=str(claim.get('value') or '').strip()[:1000]
            claim_text=str(claim.get('claim_text') or claim.get('claim') or '').strip()[:1200]
            if not conflict_key or not value or not claim_text:continue
            claim_id='CLM-'+hashlib.sha256((ident+'|'+str(idx)+'|'+conflict_key+'|'+value).encode()).hexdigest()[:20]
            con.execute('INSERT INTO manual_claim VALUES(?,?,?,?,?,?,?)',(
                claim_id,ident,conflict_key,claim_text,value,
                str(claim.get('source_locator') or 'not supplied')[:160],
                str(claim.get('status') or 'UNRESOLVED')[:80]))
    # Form feeds from external extractors preserve page boundaries. Otherwise one text block per file.
    pages=txt.split('\f') if '\f' in txt else [txt]
    for n,page in enumerate(pages,1):
        if not page.strip():continue
        # Keep maximum 25k chars per section, preserve each section number.
        for j in range(0,len(page),25000):
            segment=page[j:j+25000]
            label=f'page {n}' + (f' section {j//25000+1}' if j else '')
            con.execute('INSERT INTO manual_page(doc_id,page_label,body,page_sha256) VALUES(?,?,?,?)',
                        (ident,label,segment,hashlib.sha256(segment.encode('utf-8')).hexdigest()))
            count+=1
    print(file.name,'=>',ident,'pages:',len(pages))
con.commit();con.close();tmp.replace(a.output)
print('READY:',a.output,'documents:',len(files),'indexed page sections:',count)
print('Important: page labels are source page numbers only when the input contains form-feed page boundaries.')
