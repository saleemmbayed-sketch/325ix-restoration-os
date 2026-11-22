#!/usr/bin/env python3
"""V4 BMW E30 325iX privately-used visual catalog indexer.

Consumes existing V3.1 *without changing its files*. Builds normalized image-asset
registry, assembly/figure/callout/part edges, local illustrated browser and SQLite
search. Optionally downloads public diagram image URLs (same site as V3 references),
resumably, with robot policy checks and no access-control circumvention.

Part photos: import owner photos placed in 02_PART_PHOTOS/<11 digit OE number>/.
Otherwise generate a prioritized, unverified photo-acquisition work queue.

References are not a guarantee of vehicle fitment or original BMW certification.
"""
from __future__ import annotations
import argparse, csv, hashlib, html, io, json, re, sqlite3, time
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

USER_AGENT='BMW325iXPrivateWorkshopIndexer/4.0 (private maintenance archive; polite requests)'
DATE_TARGET='1987-12'
ALLOWED_HOST='ills.bmwfans.info'
GROUP_PRIORITY={'front_axle':0,'steering':1,'transfer_box_electric_gearbox':2,'drive_shaft':3,'rear_axle':4,'brakes':5,'engine':6,'engine_electrical_system':7,'bodywork':8}
MTH={m:i for i,m in enumerate(('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'),1)}
MONTH=re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[\'’]?\s*(\d{2})',re.I)
PN=re.compile(r'^\d{11}$')

def utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def hsh(b):return hashlib.sha256(b).hexdigest()
def json_lines(path):
    with path.open('r',encoding='utf-8') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def dump_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_suffix(path.suffix+'.temp')
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');t.replace(path)
def dump_jsonl(path,items):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8') as f:
        for i in items:f.write(json.dumps(i,ensure_ascii=False,sort_keys=True)+'\n')

def applicability(raw,month=DATE_TARGET):
    """Only a conservative *textual date-window* flag, never verified fitment."""
    text=(raw or '').replace('’',"'")
    toks=MONTH.findall(text)
    if not toks:
        return 'DATE_NOT_EXPLICIT'
    months=[f"{(2000+int(y) if int(y)<30 else 1900+int(y)):04d}-{MTH[m.title()]:02d}" for m,y in toks]
    if '—' in text:
        a,b=text.split('—',1)
        am=MONTH.search(a);bm=MONTH.search(b)
        start=(f"{(2000+int(am.group(2)) if int(am.group(2))<30 else 1900+int(am.group(2))):04d}-{MTH[am.group(1).title()]:02d}") if am else None
        end=(f"{(2000+int(bm.group(2)) if int(bm.group(2))<30 else 1900+int(bm.group(2))):04d}-{MTH[bm.group(1).title()]:02d}") if bm else None
        if (start and month<start) or (end and month>end):return 'OUTSIDE_FACTORY_MONTH_DATE_WINDOW'
        return 'WITHIN_TEXTUAL_DATE_WINDOW_NOT_FITMENT_PROOF'
    return 'DATE_EXPRESSION_REVIEW_REQUIRED'

def is_robots_allowed(session,timeout,agent=USER_AGENT):
    # Conservative: missing robots file (404 or 410) means no robots rules;
    # any access/security error prevents automated acquisition.
    u=f'https://{ALLOWED_HOST}/robots.txt'
    try:
        r=session.get(u,timeout=timeout,allow_redirects=False)
        if r.status_code in (404,410):return True,'ROBOTS_NOT_PRESENT'
        if r.status_code!=200:return False,f'ROBOTS_HTTP_{r.status_code}'
        rp=RobotFileParser();rp.parse(r.text.splitlines())
        allowed=rp.can_fetch(agent,f'https://{ALLOWED_HOST}/2pz.webp')
        return allowed,'ROBOTS_ALLOW' if allowed else 'ROBOTS_DISALLOW'
    except Exception as exc:
        return False,'ROBOTS_CHECK_FAILED_'+type(exc).__name__

def fetch_images(assets,state,root,limit,delay,timeout,maxmb,refresh_failures):
    import requests
    from PIL import Image,UnidentifiedImageError
    session=requests.Session();session.headers.update({'User-Agent':USER_AGENT,'Accept':'image/webp,image/png,image/jpeg,image/*;q=0.7'})
    allow,reason=is_robots_allowed(session,timeout)
    if not allow:
        print('Image downloads withheld:',reason,'(metadata/index generation continues)')
        for a in assets:
            if a['status'] not in ('DOWNLOADED','ALREADY_PRESENT'):
                a['status']=reason
        return 0
    target=root/'01_DIAGRAM_IMAGES';target.mkdir(parents=True,exist_ok=True)
    attempted=0
    for a in sorted(assets,key=lambda z:(GROUP_PRIORITY.get(z['priority_group'],100),z['url'])):
        u=urlsplit(a['url']);
        if u.scheme!='https' or u.hostname!=ALLOWED_HOST: a['status']='SKIPPED_UNAPPROVED_HOST';continue
        existing=state.get(a['asset_id'],{})
        if existing.get('status') in ('DOWNLOADED','ALREADY_PRESENT') and existing.get('local_file'):
            p=root/existing['local_file']
            if p.is_file() and p.stat().st_size>0:
                a.update(existing);continue
        if existing.get('status','').startswith(('HTTP_','ROBOTS_','ERROR_')) and not refresh_failures:
            a.update(existing);continue
        if limit and attempted>=limit:break
        attempted+=1
        try:
            with session.get(a['url'],timeout=(10,timeout),allow_redirects=True,stream=True) as r:
                final=urlsplit(r.url)
                if final.scheme!='https' or final.hostname!=ALLOWED_HOST:raise ValueError('redirect to unapproved host')
                if r.status_code!=200:
                    a.update(status=f'HTTP_{r.status_code}',checked_at=utc());state[a['asset_id']]=a.copy();continue
                typ=r.headers.get('Content-Type','').split(';')[0].strip().lower()
                if typ not in ('image/webp','image/jpeg','image/png','application/octet-stream'):
                    raise ValueError('unexpected content type '+typ)
                data=bytearray()
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        data+=chunk
                        if len(data)>maxmb*1024*1024: raise ValueError('image exceeds byte ceiling')
                if len(data)<100:raise ValueError('image unexpectedly small')
            im=Image.open(io.BytesIO(data)); im.verify()
            im=Image.open(io.BytesIO(data))
            typ2=im.format
            if typ2 not in ('WEBP','PNG','JPEG'):raise ValueError('unexpected image format '+str(typ2))
            ext={'WEBP':'webp','PNG':'png','JPEG':'jpg'}[typ2]
            new_digest=hsh(data)
            # Content de-duplication: images with different remote URLs may be byte-identical.
            file=target/(new_digest+'.'+ext)
            if not file.exists():
                tmp=file.with_suffix(file.suffix+'.tmp');tmp.write_bytes(data);tmp.replace(file)
            a.update(status='DOWNLOADED',sha256=new_digest,width_px=im.size[0],height_px=im.size[1],
                     mime='image/'+('jpeg' if ext=='jpg' else ext),bytes=len(data),
                     local_file=str(file.relative_to(root)),checked_at=utc(),http_status=200)
        except (requests.RequestException,ValueError,OSError,UnidentifiedImageError) as exc:
            a.update(status='ERROR_'+type(exc).__name__,error=str(exc)[:300],checked_at=utc())
        state[a['asset_id']]=a.copy()
        dump_json(root/'03_MANIFESTS'/'image_acquisition_state.json',state)
        print(f"{attempted:03} {a['status']:26} {a['asset_id']} {a['url']}",flush=True)
        if delay:time.sleep(delay)
    return attempted

def photos_from_folders(v4):
    from PIL import Image
    root=v4/'02_PART_PHOTOS';root.mkdir(parents=True,exist_ok=True)
    all_photos=[];unknown=[]
    for f in sorted(root.rglob('*')):
        if not f.is_file() or f.suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):continue
        number=f.parent.name;nomatch=not PN.fullmatch(number)
        try:
            with Image.open(f) as im:im.verify()
            with Image.open(f) as im:width,height=im.size;fmt=im.format
            data=f.read_bytes();digest=hsh(data)
            rec={'photo_id':'PHOTO-'+digest[:20], 'part_number':number if not nomatch else None,
                 'file':str(f.relative_to(v4)),'sha256':digest,'width_px':width,
                 'height_px':height,'mime':fmt,'source':'OWNER_OR_WORKSHOP_PROVIDED','identity_verified':False}
            all_photos.append(rec)
            if nomatch:unknown.append(rec)
        except Exception:continue
    return all_photos,unknown

def make_db(path,assemblies,parts,figures,assets,photos):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.building.sqlite3');temp.unlink(missing_ok=True)
    db=sqlite3.connect(temp)
    db.executescript('''PRAGMA foreign_keys=ON;
CREATE TABLE assembly(id TEXT PRIMARY KEY, group_name TEXT, title TEXT, source_url TEXT, source_status TEXT);
CREATE TABLE image_asset(id TEXT PRIMARY KEY, source_url TEXT, local_file TEXT, status TEXT, sha256 TEXT, width INTEGER, height INTEGER);
CREATE TABLE figure_occurrence(id TEXT PRIMARY KEY, assembly_id TEXT REFERENCES assembly(id),image_asset_id TEXT REFERENCES image_asset(id),source_url TEXT);
CREATE TABLE part_record(id TEXT PRIMARY KEY, assembly_id TEXT REFERENCES assembly(id),part_number TEXT, callout TEXT, description TEXT,supplement TEXT,date_raw TEXT,quantity TEXT,source_url TEXT,applicability TEXT);
CREATE INDEX ix_partnum ON part_record(part_number);CREATE INDEX ix_callout ON part_record(assembly_id,callout);
CREATE TABLE part_figure_link(part_id TEXT REFERENCES part_record(id),figure_id TEXT REFERENCES figure_occurrence(id),relation TEXT,PRIMARY KEY(part_id,figure_id));
CREATE TABLE part_photo(photo_id TEXT PRIMARY KEY, part_number TEXT, local_file TEXT,sha256 TEXT,identity_verified INTEGER);
CREATE VIRTUAL TABLE parts_fts USING fts5(part_number,description,supplement,assembly_title,source_url UNINDEXED,tokenize='unicode61');
''')
    a={x['source_id']:x for x in assemblies}; figby=defaultdict(list)
    for fig in figures:figby[fig['assembly_id']].append(fig)
    for x in assemblies:
        db.execute('INSERT INTO assembly VALUES(?,?,?,?,?)',(x['source_id'],x.get('group',''),x.get('title',''),x.get('url',''),x.get('status','')))
    for i in assets:
        db.execute('INSERT INTO image_asset VALUES(?,?,?,?,?,?,?)',(i['asset_id'],i['url'],i.get('local_file',''),i['status'],i.get('sha256',''),i.get('width_px'),i.get('height_px')))
    for fig in figures:
        db.execute('INSERT INTO figure_occurrence VALUES(?,?,?,?)',(fig['figure_id'],fig['assembly_id'],fig['image_asset_id'],fig['figure_url']))
    for p in parts:
        flag=applicability(p.get('date_condition_raw',''))
        db.execute('INSERT INTO part_record VALUES(?,?,?,?,?,?,?,?,?,?)',(p['record_id'],p['assembly_id'],p['part_number'],p.get('callout_position',''),p.get('description',''),p.get('supplement',''),p.get('date_condition_raw',''),p.get('quantity_raw',''),p.get('part_anchor',''),flag))
        for fig in figby[p['assembly_id']]:
            db.execute('INSERT INTO part_figure_link VALUES(?,?,?)',(p['record_id'],fig['figure_id'],'ASSEMBLY_TABLE_CALLOUT_NUMBER_ONLY'))
        db.execute('INSERT INTO parts_fts VALUES(?,?,?,?,?)',(p['part_number'],p.get('description',''),p.get('supplement',''),a[p['assembly_id']].get('title',''),p.get('source_url','')))
    for p in photos:
        db.execute('INSERT OR IGNORE INTO part_photo VALUES(?,?,?,?,?)',(p['photo_id'],p['part_number'],p['file'],p['sha256'],int(p['identity_verified'])))
    db.commit(); db.close();temp.replace(path)

def make_html(out,assemblies,parts,figures,assets,photos):
    ast={x['asset_id']:x for x in assets}; figby=defaultdict(list);partby=defaultdict(list)
    for f in figures:figby[f['assembly_id']].append(f)
    for p in parts:
        partby[p['assembly_id']].append([p.get('callout_position',''),p['part_number'],p.get('description',''),p.get('quantity_raw',''),p.get('date_condition_raw',''),p.get('supplement',''),applicability(p.get('date_condition_raw','')),p.get('part_anchor','')])
    blocks=[]
    for s in assemblies:
        f=figby[s['source_id']][0] if figby[s['source_id']] else None
        asset=ast.get(f['image_asset_id']) if f else None
        blocks.append({'g':s.get('group',''),'t':s.get('title',''),'u':s.get('url',''),'i':asset.get('local_file','') if asset else '',
                       'fu':asset.get('url','') if asset else '', 'st':asset.get('status','') if asset else '',
                       'p':partby[s['source_id']]})
    photos_by=defaultdict(list)
    for p in photos:
        if p.get('part_number'):photos_by[p['part_number']].append(p['file'])
    data=json.dumps({'assemblies':blocks,'photos':photos_by},ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    content=r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BMW 325iX — V4 Visual Workshop Atlas</title>
<style>:root{font-family:system-ui,-apple-system,Arial,sans-serif;color:#17283b;background:#f3f5f9}*{box-sizing:border-box}body{max-width:1400px;margin:auto;padding:16px}header{background:#15324d;color:white;padding:24px;border-radius:14px}header p{color:#c9deec}input,select,button{font:inherit;padding:12px;border-radius:9px;border:1px solid #bbcad8}input{width:100%}.controls{display:grid;grid-template-columns:2fr 1fr;gap:10px;margin:14px 0}.info{padding:12px;background:#fff;border:1px solid #d9e1eb;border-radius:10px;margin:14px 0}#cards{display:grid;gap:14px}.card{background:#fff;border:1px solid #d7e2ec;padding:14px;border-radius:12px}.head{display:flex;justify-content:space-between;gap:15px;align-items:start;flex-wrap:wrap}.head h3{margin:0 0 6px}.muted{font-size:13px;color:#52677a}.picture{display:grid;grid-template-columns:minmax(250px,50%) 1fr;gap:16px}.picture img{width:100%;max-height:435px;object-fit:contain;background:#f8f8f8;border-radius:8px}.none{padding:50px 12px;background:#f7f9fc;border:1px dashed #aab6c3;border-radius:8px;text-align:center}table{width:100%;border-collapse:collapse;table-layout:fixed}td,th{padding:7px 6px;vertical-align:top;border-bottom:1px solid #e3e8ed;overflow-wrap:anywhere;text-align:left;font-size:12px}th:nth-child(1){width:32px}th:nth-child(2){width:135px}a{color:#1661aa;overflow-wrap:anywhere}.tag{padding:3px 7px;border-radius:6px;background:#e9f0fa;font-size:12px}.stats{color:#234f77;font-weight:600}details summary{cursor:pointer;padding:9px 0;font-weight:600}.imgthumb{width:90px;max-height:90px;object-fit:contain}footer{color:#61748b;padding:25px;text-align:center}@media(max-width:800px){.picture{grid-template-columns:1fr}.controls{grid-template-columns:1fr}th:nth-child(2){width:110px}}</style></head>
<body><header><h1>BMW E30 325iX — V4 Visual Workshop Atlas</h1><p>805 European sedan catalog assemblies · parts &amp; drawing references · December 1987 factory context · replacement M20B25 · manual AWD</p></header>
<div class="controls"><input id="query" placeholder="Search BMW number, part name, assembly, group, or callout..."><select id="group"><option value="">All catalog groups</option></select></div>
<div class="info"><div class="stats" id="status">Loading records…</div><div class="muted">This is a secondary BMW ETK-derived catalog, not proof of installed fitment. A date-window match is not a verified part match. Printed callout positions are taken from the assembly parts table; their pixel locations within drawings are not yet annotated.</div></div>
<div id="cards"></div><footer>BMW 325iX restoration research archive · Source links and evidence are preserved.</footer>
<script>const DB=__DATA__;const groups=[...new Set(DB.assemblies.map(x=>x.g))].sort();const g=document.getElementById('group'),q=document.getElementById('query'),cards=document.getElementById('cards'),status=document.getElementById('status');for(const n of groups){let o=document.createElement('option');o.value=n;o.textContent=n.replaceAll('_',' ');g.append(o)}
function el(tag,txt,cls){const x=document.createElement(tag);if(txt!==undefined)x.textContent=txt;if(cls)x.className=cls;return x}function link(label,href){let a=el('a',label);if(href&&(/^https:\/\//.test(href)||/^01_DIAGRAM_IMAGES\//.test(href)||/^02_PART_PHOTOS\//.test(href))){a.href=href;a.target='_blank';a.rel='noopener noreferrer'}return a}
function render(){let query=q.value.trim().toLowerCase(),group=g.value;let result=DB.assemblies.filter(a=>(!group||a.g===group)&&(!query||[a.g,a.t,...a.p.flatMap(p=>p.slice(0,6))].join(' ').toLowerCase().includes(query)));status.textContent=`${result.length} matching assemblies / ${DB.assemblies.length} indexed — ${result.reduce((s,a)=>s+a.p.length,0).toLocaleString()} part table rows`;cards.replaceChildren();for(let a of result.slice(0,75)){let box=el('div',undefined,'card');let head=el('div',undefined,'head'),title=el('div');title.append(el('h3',a.t),el('div',a.g.replaceAll('_',' '),'muted'),link('Original catalog page',a.u));head.append(title,el('span',`${a.p.length} part rows · ${a.st||'no image'}`,'tag'));box.append(head);let pic=el('div',undefined,'picture'),left=el('div');if(a.i){let im=el('img');im.src=a.i;im.alt=a.t+' exploded parts illustration';im.loading='lazy';left.append(im)}else left.append(el('div','Drawing not saved locally; original illustration reference is available online.','none'));if(a.fu)left.append(link('Open source drawing',a.fu));pic.append(left);let right=el('div'),det=el('details');det.open=(result.length<5);det.append(el('summary','Part list and numbered callouts'));let table=el('table'),thead=el('tr');for(let h of ['#','BMW part number','Description / notes'])thead.append(el('th',h));table.append(thead);let rowfilter=query&&!([a.g,a.t].join(' ').toLowerCase().includes(query));for(let p of a.p){if(rowfilter&&!p.slice(0,6).join(' ').toLowerCase().includes(query))continue;let tr=el('tr'),v=el('td',p[0]),pn=el('td');pn.append(link(p[1],p[7]));let detail=el('td');detail.append(el('div',p[2]),el('div',`Qty ${p[3]||'?'} · ${p[4]||'Date unspecified'} · ${p[6]}`,'muted'));if(p[5])detail.append(el('div',p[5],'muted'));if(DB.photos[p[1]])for(let f of DB.photos[p[1]]){let img=el('img');img.src=f;img.className='imgthumb';detail.append(img)}tr.append(v,pn,detail);table.append(tr)}det.append(table);right.append(det);pic.append(right);box.append(pic);cards.append(box)}if(result.length>75)cards.append(el('div',`Showing first 75 of ${result.length} matches. Narrow search to see more.`,'info'))}q.addEventListener('input',render);g.addEventListener('change',render);render();</script></body></html>'''
    file=out/'OFFLINE_VISUAL_ATLAS.html'
    file.write_text(content.replace('__DATA__',data),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(description='V4 visual catalog, preserves original V3.1')
    ap.add_argument('--root',required=True)
    ap.add_argument('--download-images',action='store_true',help='Download accessible original drawings, with robots/HTTP checks')
    ap.add_argument('--max-images',type=int,default=0,help='Maximum new downloads (0 means no limit)')
    ap.add_argument('--delay',type=float,default=1.5)
    ap.add_argument('--timeout',type=float,default=35)
    ap.add_argument('--max-image-mb',type=int,default=15)
    ap.add_argument('--retry-failed',action='store_true')
    args=ap.parse_args()
    root=Path(args.root).expanduser().resolve(); v3=root/'13_EU_FULL_ASSEMBLY_CORPUS_V3'/'09_RAG_DATASETS';v4=root/'14_MULTIMODAL_MEDIA_AND_GRAPH'
    required=[v3/'assemblies.jsonl',v3/'part_rows.jsonl',v3/'figures.jsonl']
    for f in required:
        if not f.is_file():raise SystemExit(f'V3.1 result missing: {f}')
    assemblies=list(json_lines(required[0]));parts=list(json_lines(required[1]));figures=list(json_lines(required[2]))
    assert len(assemblies)==805 and len(parts)>=13000 and len(figures)==805,'V3 final data differs from expected audit; investigate before continuing'
    by_assembly={a['source_id']:a for a in assemblies}
    assets={}
    for f in figures:
        id=f['image_asset_id'];u=f['figure_url']; assert urlsplit(u).hostname==ALLOWED_HOST,'Unexpected figure host'
        if id not in assets:assets[id]={'asset_id':id,'url':u,'priority_group':by_assembly[f['assembly_id']]['group'],'status':'NOT_DOWNLOADED','local_file':''}
        else:
            if GROUP_PRIORITY.get(by_assembly[f['assembly_id']]['group'],100)<GROUP_PRIORITY.get(assets[id]['priority_group'],100):
                assets[id]['priority_group']=by_assembly[f['assembly_id']]['group']
    saved=v4/'03_MANIFESTS'/'image_acquisition_state.json'
    state=json.loads(saved.read_text(encoding='utf-8')) if saved.exists() else {}
    for id,a in assets.items():
        if id in state:
            a.update(state[id]);a['status']=state[id].get('status','NOT_DOWNLOADED')
            p=v4/a.get('local_file','') if a.get('local_file') else None
            if a['status'] in ('DOWNLOADED','ALREADY_PRESENT') and not(p and p.is_file()):a.update(status='MISSING_ON_DISK',local_file='')
    attempted=0
    if args.download_images:
        attempted=fetch_images(list(assets.values()),state,v4,args.max_images,args.delay,args.timeout,args.max_image_mb,args.retry_failed)
    v4.mkdir(parents=True,exist_ok=True)
    dump_json(saved,state)
    photos,unmatched=photos_from_folders(v4)
    figures_out=[{**f,'binary_status':assets[f['image_asset_id']]['status'],'local_file':assets[f['image_asset_id']].get('local_file',''),
                  'callout_relation':'POSITION_FROM_ASSEMBLY_TABLE; IMAGE_COORDINATES_UNANNOTATED'} for f in figures]
    part_out=[]
    figs_by=defaultdict(list)
    for f in figures:figs_by[f['assembly_id']].append(f)
    for p in parts:
        part_out.append({'part_record_id':p['record_id'],'part_number':p['part_number'], 'assembly_id':p['assembly_id'],
                         'callout_position':p['callout_position'], 'figure_ids':[f['figure_id'] for f in figs_by[p['assembly_id']]],
                         'image_asset_ids':[f['image_asset_id'] for f in figs_by[p['assembly_id']]],
                         'drawing_link_status':'ASSEMBLY_TABLE_CALLOUT; PIXEL_COORDINATE_UNVERIFIED',
                         'factory_month_assessment':applicability(p.get('date_condition_raw','')),
                         'source_url':p['part_anchor']})
    out=v4/'03_MANIFESTS'
    dump_jsonl(out/'image_assets.jsonl',sorted(assets.values(),key=lambda x:x['url']))
    dump_jsonl(out/'figure_occurrences.jsonl',figures_out)
    dump_jsonl(out/'parts_to_figures.jsonl',part_out)
    dump_jsonl(out/'part_photos.jsonl',photos)
    dump_jsonl(out/'unmatched_photos.jsonl',unmatched)
    # Prioritize photos needed in known workshop systems. PHOTO_REQUESTED != PHOTO_PRESENT.
    pn_info={}
    for p in parts:
        n=p['part_number'];g=by_assembly[p['assembly_id']]['group']
        e=pn_info.setdefault(n,{'groups':set(),'count':0,'description':p.get('description','')})
        e['count']+=1;e['groups'].add(g)
    photo_by=defaultdict(list)
    for x in photos:photo_by[x['part_number']].append(x)
    with (out/'part_photo_research_queue.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['bmw_part_number','description','catalog_mentions','groups','priority','photo_count','verification_required'])
        for n,e in sorted(pn_info.items(),key=lambda t:(min(GROUP_PRIORITY.get(g,100) for g in t[1]['groups']),-t[1]['count'])):
            pr=min(GROUP_PRIORITY.get(g,100) for g in e['groups'])
            w.writerow([n,e['description'],e['count'],'|'.join(sorted(e['groups'])),pr,len(photo_by[n]),'CONFIRM PHOTO BELONGS TO EXACT PART NUMBER'])
    make_db(v4/'04_SEARCH'/'325ix_multimodal.sqlite3',assemblies,parts,figures,list(assets.values()),photos)
    make_html(v4,assemblies,parts,figures,list(assets.values()),photos)
    st=Counter(x['status'] for x in assets.values()); cov={
        'version':'4.0.0', 'generated_at':utc(),'vehicle_VIN':__import__('os').environ.get('BMW_325IX_VIN','VIN_NOT_CONFIGURED'),
        'factory_month':DATE_TARGET,'installed_engine':'owner-confirmed M20B25',
        'v3_assemblies':len(assemblies),'parts_rows':len(parts),'distinct_part_numbers':len(pn_info),
        'figure_associations':len(figures),'unique_image_assets':len(assets),
        'image_assets_saved':sum(x['status'] in ('DOWNLOADED','ALREADY_PRESENT') for x in assets.values()),
        'unique_binary_contents_saved':len(set(x.get('sha256') for x in assets.values() if x.get('sha256'))),
        'image_status_breakdown':dict(st),'download_attempts_this_run':attempted,
        'workshop_photos_indexed':len(photos),'unmatched_workshop_photos':len(unmatched),
        'date_window_outside':sum(applicability(p.get('date_condition_raw',''))=='OUTSIDE_FACTORY_MONTH_DATE_WINDOW' for p in parts),
        'callout_positions_extracted':sum(bool(p.get('callout_position')) for p in parts),
        'exact_callout_pixel_coordinates_verified':0,
        'warning':'secondary catalog across variants; date window is a textual filter, not VIN-specific fitment; image photos unverified; no safety specs inferred'}
    dump_json(out/'v4_coverage.json',cov)
    print('V4 SUMMARY',json.dumps(cov,indent=2),flush=True)
    print('OFFLINE ATLAS',v4/'OFFLINE_VISUAL_ATLAS.html',flush=True)

if __name__=='__main__':main()
