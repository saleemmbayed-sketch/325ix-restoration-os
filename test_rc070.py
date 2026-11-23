#!/usr/bin/env python3
"""Disposable regression suite; never point at the user's live Mac workshop folder."""
import argparse,base64,hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,tempfile,time,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone

KIT=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,required=True,help='Working V0.6 test fixture with data/325ix_assemblies.sqlite3, not live Mac folder')
    args=p.parse_args()
    if 'Desktop' in str(args.baseline):p.error('Refusing user Desktop workspace')
    results=[]
    def check(name,cond,detail=None):
        results.append({'name':name,'ok':bool(cond),'detail':detail})
        print(('PASS' if cond else 'FAIL'),name, str(detail or '')[:140])
    with tempfile.TemporaryDirectory(prefix='325ix-qa-') as td:
        root=Path(td)/'325ix_workbench'
        # copy baseline, preserving SQLite in isolated test setup only
        shutil.copytree(args.baseline,root,ignore=shutil.ignore_patterns('__pycache__','upgrade_backup_*','*.sqlite3-shm','*.sqlite3-wal'))
        # Record pre-install application and mutable DB fingerprints.
        old_app=sha(root/'app.py')
        initial_db=sha(root/'workshop_jobs.sqlite3')
        src_cat=sha(root/'data'/'325ix_assemblies.sqlite3')
        # install into temp; source kit deliberately outside root
        installer=subprocess.run(['bash',str(KIT/'install_upgrade.sh'),str(root)],capture_output=True,text=True,timeout=50)
        check('Installer success',installer.returncode==0,installer.stdout[-1000:] or installer.stderr)
        if installer.returncode!=0:raise RuntimeError('Installer failed; cannot proceed')
        check('Original catalog unchanged',sha(root/'data'/'325ix_assemblies.sqlite3')==src_cat)
        check('Original mutable jobs unchanged by installation',sha(root/'workshop_jobs.sqlite3')==initial_db)
        installed_overlay=json.loads((root/'curated_evidence.json').read_text())
        check('Installed source-review count excludes unqualified keys',installed_overlay.get('source_reviewed_count')==85 and installed_overlay.get('verified_count')==85 and len(installed_overlay.get('evidence',{}))==85,installed_overlay.get('source_reviewed_count'))
        check('Application changed',sha(root/'app.py')!=old_app)
        pointers=json.loads((root/'RC070_BACKUP_POINTER.json').read_text());backup=Path(pointers['backup_path'])
        check('Code backup and SQLite snapshot exist',(backup/'app.py').is_file() and (backup/'workshop_jobs.sqlite3').is_file())
        check('Backup manifest includes curated collision state', 'curated_conflicts_preserved_locally' in json.loads((backup/'backup_manifest.json').read_text()))
        manual_db=sqlite3.connect(root/'workshop_jobs.sqlite3');existing=manual_db.execute('SELECT count(*) FROM job').fetchone()[0];manual_db.close()
        # Generate one tiny synthetic diagram fixture. It is NOT BMW evidence.
        from base64 import b64decode
        asset='IMG-90941fe6cc813e29'
        v4=Path(td)/'14_MULTIMODAL_MEDIA_AND_GRAPH';(v4/'03_MANIFESTS').mkdir(parents=True);(v4/'01_DIAGRAM_IMAGES').mkdir()
        import zlib,struct
        def chunk(tag,data):return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
        n=24
        scan=b''.join(b'\x00'+bytes(v for x in range(n) for v in ((x*17+y*5)%256,(x*11+y*19)%256,(x*23+y*7)%256)) for y in range(n))
        binimg=(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',n,n,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))
        (v4/'01_DIAGRAM_IMAGES'/'synthetic.png').write_bytes(binimg)
        (v4/'03_MANIFESTS'/'image_assets.jsonl').write_text(json.dumps({'asset_id':asset,'local_file':'01_DIAGRAM_IMAGES/synthetic.png','status':'DOWNLOADED','bytes':len(binimg),'sha256':hashlib.sha256(binimg).hexdigest(),'mime':'image/png'})+'\n')
        # ephemeral port
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        logfile=Path(td)/'server.log'
        with logfile.open('wb') as logs:
            proc=subprocess.Popen([sys.executable,'-u','app.py','--port',str(port),'--v4-root',str(v4)],cwd=root,stdout=logs,stderr=subprocess.STDOUT)
            try:
                base=f'http://127.0.0.1:{port}'
                for i in range(90):
                    try:
                        with urllib.request.urlopen(base+'/api/vehicle',timeout=.5) as r:break
                    except Exception:time.sleep(.15)
                else:raise RuntimeError('Server not responding: '+logfile.read_text()[-2500:])
                def request(path,body=None,extra_headers=None,override_host=None):
                    headers={'Accept':'application/json'}
                    if body is not None:headers['Content-Type']='application/json'
                    if extra_headers:headers.update(extra_headers)
                    data=None if body is None else json.dumps(body).encode()
                    req=urllib.request.Request(base+path,data=data,headers=headers,method='POST' if body is not None else 'GET')
                    if override_host:req.add_unredirected_header('Host',override_host)
                    try:
                        with urllib.request.urlopen(req,timeout=10) as r:
                            raw=r.read();code=r.status
                    except urllib.error.HTTPError as e:raw=e.read();code=e.code
                    try:payload=json.loads(raw)
                    except Exception:payload=raw
                    return code,payload
                code,stats=request('/api/catalog/coverage')
                check('Catalog counts dynamic after V07 overlay',code==200 and stats.get('researched_exact_number_records')==85 and stats.get('unique_part_numbers')==7190,stats.get('researched_exact_number_records'))
                code,stats2=request('/api/evidence/coverage')
                check('Independent evidence count reconciled',code==200 and stats2.get('researched_exact_part_numbers')==85)
                check('Supplier image references distinct from local actual-part photos',code==200 and stats2.get('supplier_image_reference_count')==6 and stats2.get('owner_uploaded_workshop_actual_part_photo_count')==0 and stats2.get('physical_photo_reference_count')==6,stats2)
                code,work=request('/api/catalog/worklist?batch=1')
                check('Worklist includes sourced first-part state',code==200 and work.get('parts') and work['parts'][0].get('evidence_status')=='SOURCE_REVIEWED',work['parts'][0]['part_number'] if work.get('parts') else None)
                code,entry=request('/api/catalog/entry?part=31331125341')
                check('Exact-number endpoint reflects current overlay',code==200 and entry.get('record',{}).get('evidence_status')=='SOURCE_REVIEWED')
                code,d=request('/api/part-dossier?id=PR-INVALID')
                check('Invalid part id rejected',code==404)
                code,status=request('/api/v4/status')
                check('Synthetic V4 fixture recognized',code==200 and status.get('images_present_locally',0)>=1,status)
                code,img=request('/api/diagram?asset='+asset)
                check('Synthetic diagram served inline through localhost route',code==200 and img==binimg)
                (v4/'01_DIAGRAM_IMAGES'/'synthetic.png').write_bytes(binimg+b'corruption')
                code,broken=request('/api/diagram?asset='+asset)
                check('Corrupt local diagram is rejected before serving',code==404 and broken.get('integrity_state')=='SIZE_MISMATCH',broken)
                code,j=request('/api/jobs',{'system':'invented_critical_bypass','symptom':'Front wheel play'}, {'X-Workbench-Request':'same-origin'})
                check('Unknown vehicle system blocked',code==400)
                code,j=request('/api/jobs',{'system':'steering','symptom':'Front wheel play'}, {'X-Workbench-Request':'same-origin','Origin':'https://untrusted.example'})
                check('Untrusted Origin blocked',code==403)
                code,j=request('/api/jobs',{'system':'steering','symptom':'Front wheel play'})
                check('Missing local write-header blocked',code==403)
                code,j=request('/api/jobs',{'system':'steering','symptom':'Front wheel play'}, {'X-Workbench-Request':'same-origin','Sec-Fetch-Site':'cross-site'})
                check('Cross-site fetch blocked',code==403)
                code,j=request('/api/groups',override_host='attacker.example')
                check('Non-loopback Host blocked',code==403)
                code,diag=request('/api/diagnostic?system=steering&symptom=play')
                check('Diagnostic read still works',code==200 and diag.get('system')=='steering')
                # identify valid front axle assembly to test mismatch
                with sqlite3.connect(root/'data'/'325ix_assemblies.sqlite3') as db:
                    aid=db.execute("SELECT id FROM assembly WHERE group_name='front_axle' LIMIT 1").fetchone()[0]
                code,j=request('/api/jobs',{'system':'steering','symptom':'Front wheel play','assembly_id':aid},{'X-Workbench-Request':'same-origin','Origin':base})
                check('Assembly/system mismatch blocked',code==400)
                code,j=request('/api/jobs',{'system':'front_axle','symptom':'Front wheel play','assembly_id':aid},{'X-Workbench-Request':'same-origin','Origin':base})
                check('Valid local job write works',code==201 and j.get('risk')=='SAFETY_CRITICAL_REVIEW_REQUIRED',j)
                id=j.get('job_id')
                code,jobs=request('/api/jobs')
                check('New inspection job persisted without clearance',code==200 and any(x['id']==id and x['clearance']=='NOT_APPROVED' for x in jobs))
                code,cards=request('/api/job/'+str(id)+'.md')
                check('Job card export still available',code==200 and b'NOT_APPROVED' in cards)
                check('Manual status clearly reported',request('/api/manuals/status')[0]==200)
                code,expert=request('/api/expert/front-play')
                check('Front Axle Expert exposes seven sourced checkpoints',code==200 and len(expert.get('steps',[]))==7 and len(expert.get('sources',[]))==2 and all(x.get('source_page') for x in expert['sources']))
                check('Front Axle Expert resolves iX-specific assemblies',len(expert.get('assemblies',[]))>=5 and all(a.get('source_url','').startswith('https://') for a in expert['assemblies']))
                check('Front Axle Expert resolves part catalog rows',len(expert.get('parts',[]))==5 and all(x['rows'] for x in expert['parts']))
                check('Expert drawing absence is honestly reported',expert['v4'].get('present',99)==1 and expert.get('release_gate','').startswith('INTERNAL_PILOT'))
                code,bad=request('/api/expert/front-play/start',{'side':'FRONT_UNKNOWN','symptom':'front wheel play observed'}, {'X-Workbench-Request':'same-origin'})
                check('Unknown inspection side rejected',code==400)
                code,bad=request('/api/expert/front-play/start',{'side':'LEFT','symptom':'front wheel play observed'}, {'X-Workbench-Request':'same-origin','Origin':'https://untrusted.example'})
                check('Cross-origin expert creation rejected',code==403)
                code,c=request('/api/expert/front-play/start',{'side':'LEFT','symptom':'Clunk near left wheel when turning slowly; exact source unknown','context':'No measurements yet'}, {'X-Workbench-Request':'same-origin'})
                check('Expert start creates persistent safety-critical case',code==201 and c.get('job_id') and c.get('clearance')=='NOT_APPROVED' and c.get('stage_count')==7,c)
                eid=c.get('job_id')
                code,summary=request('/api/expert/front-play/cases')
                check('Expert case appears in case list',code==200 and any(x['job_id']==eid for x in summary.get('cases',[])))
                code,details=request('/api/expert/front-play/cases?job_id='+str(eid))
                check('Seven checkpoints reopen from disk',code==200 and len(details.get('steps',[]))==7 and details['case']['side']=='LEFT')
                code,bad=request('/api/expert/front-play/step',{'job_id':eid,'code':'TRIAGE','status':'CLEARED','finding':'No issue'}, {'X-Workbench-Request':'same-origin'})
                check('False safety-clearance status blocked',code==400)
                code,bad=request('/api/expert/front-play/step',{'job_id':eid,'code':'TRIAGE','status':'OBSERVED','finding':''}, {'X-Workbench-Request':'same-origin'})
                check('Observed checkpoint requires evidence notes',code==400)
                code,ok=request('/api/expert/front-play/step',{'job_id':eid,'code':'SYMPTOM','status':'OBSERVED','finding':'Owner notices clunk on left corner during slow turn','source':'Owner statement'}, {'X-Workbench-Request':'same-origin'})
                check('Observed checkpoint saved',code==200 and ok.get('clearance')=='NOT_APPROVED')
                code,ok=request('/api/expert/front-play/step',{'job_id':eid,'code':'TRIAGE','status':'NEEDS_SPECIALIST','finding':'Awaiting lift and inspection at workshop','source':'BMW TIS source page 7'}, {'X-Workbench-Request':'same-origin'})
                check('Specialist checkpoint can remain blocked',code==200)
                code,details=request('/api/expert/front-play/cases?job_id='+str(eid))
                check('Checkpoint statuses persist after reread',code==200 and any(x['code']=='SYMPTOM' and x['status']=='OBSERVED' for x in details['steps']) and any(x['code']=='TRIAGE' and x['status']=='NEEDS_SPECIALIST' for x in details['steps']))
                code,export=request('/api/job/'+str(eid)+'.md')
                check('Export includes expert steps and source page links',code==200 and b'Front Axle Expert workflow' in export and b'NOT_APPROVED' in export and b'BMW_TIS_SI_STEER_7' in export and b'Awaiting lift' in export)
                code,bad=request('/api/expert/front-play/cases?job_id=9999999')
                check('Unknown case read returns 404',code==404)

            finally:
                proc.terminate();proc.wait(timeout=10)
        # add a valid later job directly into disposable SQLite: rollback cannot erase it
        with sqlite3.connect(root/'workshop_jobs.sqlite3') as db:
            db.execute("INSERT INTO job(created_utc,system,symptom,context,risk) VALUES(?,?,?,?,?)",('test','front_axle','test later job','test','SAFETY_CRITICAL_REVIEW_REQUIRED'))
            db.commit()
        with sqlite3.connect(root/'workshop_jobs.sqlite3') as db:after_install=db.execute('SELECT count(*) FROM job').fetchone()[0]
        rb=subprocess.run(['bash',str(root/'rollback_upgrade.sh'),str(root)],capture_output=True,text=True,timeout=25)
        check('Rollback successful',rb.returncode==0,rb.stdout[-800:] or rb.stderr)
        check('Original app restored byte-for-byte',sha(root/'app.py')==old_app)
        check('Catalog unchanged after rollback',sha(root/'data'/'325ix_assemblies.sqlite3')==src_cat)
        with sqlite3.connect(root/'workshop_jobs.sqlite3') as db:after_rb=db.execute('SELECT count(*) FROM job').fetchone()[0]
        check('Rollback does not erase later jobs',after_install==after_rb and after_rb>=existing+2,(existing,after_install,after_rb))
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'candidate':'RC0.7.0','tests':results,'passed':sum(x['ok'] for x in results),'failed':sum(not x['ok'] for x in results),'policy':'This is an isolated code/API test. Synthetic PNG image is NOT a BMW diagram. Monterey browser CX, manuals, and real photos remain outside this test.'}
    outfile=KIT.parent/'QA_REPORT_RC070.json';outfile.write_text(json.dumps(report,indent=2))
    print(f"TESTS: {report['passed']} PASS / {report['failed']} FAIL. {outfile}")
    return 0 if not report['failed'] else 1

if __name__=='__main__':sys.exit(main())
