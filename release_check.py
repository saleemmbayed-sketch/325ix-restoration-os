#!/usr/bin/env python3
"""Release gate for the BMW 325iX restoration MVP candidate."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, sqlite3, subprocess, sys

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / 'RELEASE_STATUS.json'
MANIFEST = ROOT / 'RELEASE_MANIFEST_MVP.json'

def check(name, ok, detail):
    return {'name': name, 'ok': bool(ok), 'detail': detail}

def main():
    mm = ROOT / '04_SEARCH' / '325ix_multimodal.sqlite3'
    checks=[]
    with sqlite3.connect(mm) as db:
        counts={t:db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('assembly','part_record','image_asset','figure_occurrence','part_figure_link')}
        checks += [
            check('catalog_assemblies', counts['assembly']==805, counts['assembly']),
            check('catalog_part_occurrences', counts['part_record']==13845, counts['part_record']),
            check('v4_image_assets', counts['image_asset']==572, counts['image_asset']),
            check('figure_occurrences', counts['figure_occurrence']==805, counts['figure_occurrence']),
            check('part_figure_links', counts['part_figure_link']==13845, counts['part_figure_link']),
        ]
        required=['31121701059','31121701060','32211701039','32211701040','31211132284']
        found={x[0] for x in db.execute('SELECT DISTINCT part_number FROM part_record WHERE part_number IN ('+','.join('?'*len(required))+')',required)}
        checks.append(check('front_axle_exact_numbers',len(found)==len(required),sorted(found)))
    registry=json.loads((ROOT/'catalog_research_registry.json').read_text())
    checks.append(check('research_registry',len(registry.get('parts',{}))==7190,len(registry.get('parts',{}))))
    specialists=json.loads((ROOT/'specialists.json').read_text())
    checks.append(check('specialist_roles',len(specialists.get('agents',[]))==6,len(specialists.get('agents',[]))))
    expert=json.loads((ROOT/'front_axle_expert_v1.json').read_text())
    checks.append(check('front_axle_checkpoints',len(expert.get('steps',[]))==7,len(expert.get('steps',[]))))
    local_manifest=ROOT/'03_MANIFESTS'/'image_assets_local.jsonl'
    local_rows=[json.loads(x) for x in local_manifest.read_text().splitlines() if x.strip()] if local_manifest.exists() else []
    materialized=[x for x in local_rows if x.get('status')=='MATERIALIZED_READ_ONLY']
    checks.append(check('front_axle_diagrams_materialized',len(materialized)>=3,len(materialized)))
    site_js=(ROOT/'site.js').read_text(encoding='utf-8')
    site_css=(ROOT/'site.css').read_text(encoding='utf-8')
    checks += [
        check('visual_twin_api_contract','visual_twin' in (ROOT/'app.py').read_text(encoding='utf-8'),'system map endpoint present'),
        check('visual_twin_interaction',all(x in site_js for x in ('loadVisualTwin','selectVisualSystem','loadVisualAssembly')),'3D reference, system selection and 2D fallback present'),
        check('visual_twin_responsive_styles','visual-twin' in site_css,'visual twin styles present'),
    ]
    manual_index=ROOT/'maintenance_manual_index.sqlite3'
    manual_ok=False
    manual_detail='missing'
    if manual_index.is_file():
        with sqlite3.connect(manual_index) as db:
            manual_docs=db.execute('SELECT count(*) FROM manual_doc').fetchone()[0]
            manual_pages=db.execute('SELECT count(*) FROM manual_page').fetchone()[0]
        manual_ok=manual_docs>=57 and manual_pages>=1500
        manual_detail=f'{manual_docs} documents / {manual_pages} page sections'
    checks.append(check('maintenance_manual_index',manual_ok,manual_detail))
    launcher=ROOT/'RUN_RC12_TRIAL.command'
    checks.append(check('rc12_isolated_trial_launcher',launcher.is_file() and os.access(launcher,os.X_OK),'isolated owner-DB copy launcher executable'))
    launcher_test=subprocess.run([sys.executable,str(ROOT/'test_rc12_launcher.py')],cwd=ROOT,capture_output=True,text=True,timeout=10)
    checks.append(check('rc12_port_conflict_recovery',launcher_test.returncode==0,(launcher_test.stdout+launcher_test.stderr).strip()[-300:]))
    test=subprocess.run([sys.executable,str(ROOT/'test_mvp_integration.py')],cwd=ROOT,capture_output=True,text=True,timeout=30)
    checks.append(check('end_to_end_integration_test',test.returncode==0,(test.stdout+test.stderr).strip()[-500:]))
    blockers=[
        'Qualified physical mechanic inspection and safety sign-off are outside software.',
        'No real authorized model-appropriate repair set is included yet; the page-level provenance/index contract is ready for controlled import.',
        'Owner-installed photos and calibrated measurements are not supplied in this environment.',
        'Arabic voice and Ollama model execution are not validated in this environment.',
        'Browser-device visual acceptance remains unobserved because Chromium cannot start in this execution container.',
    ]
    report={'generated_utc':datetime.now(timezone.utc).isoformat(),'release':'MVP-0.9.0-RC13',
            'status':'INTERNAL_RELEASE_CANDIDATE' if all(x['ok'] for x in checks) else 'BLOCKED',
            'checks':checks,'blockers':blockers,'safety_clearance':'NOT_APPROVED',
            'original_v3_v4_policy':'immutable originals remain external/read-only; this package contains a derived local V4 manifest'}
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    release_files=[
        'README_MVP.md','MVP_PROGRESS.md','PRODUCT_BLUEPRINT.md','docs/adr/0001-system-wide-ix-restoration-scope.md','RELEASE_STATUS.json','app.py','index.html','site.js','site.css',
        'specialists.json','sources.json','front_axle_expert_v1.json','catalog_research_registry.json',
        '03_MANIFESTS/image_assets_local.jsonl','04_SEARCH/325ix_multimodal.sqlite3','test_mvp_integration.py',
        'materialize_v4_front_axle.py','ingest_drive_maintenance.py','ingest_web_gap_materials.py',
        'maintenance_ingestion_manifest.json','maintenance_web_gap_input/manifest.json',
        'maintenance_manual_index.sqlite3','release_check.py','restore_jobs_backup.py','launch_rc12_trial.py','test_rc12_launcher.py','RUN_RC12_TRIAL.command','README_RC12.md',
    ]
    hashes={}
    for name in release_files:
        path=ROOT/name
        if path.is_file():
            hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps({
        'release':'MVP-0.9.0-RC13','status':report['status'],
        'generated_utc':report['generated_utc'],'sha256_files':hashes,
        'mutable_files_excluded':['workshop_jobs.sqlite3','part_photos.sqlite3','actual_part_photos','rc12_trial_state','workshop_jobs_backups','__pycache__'],
        'safety_clearance':'NOT_APPROVED'
    },indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':report['status'],'passed':sum(x['ok'] for x in checks),'failed':sum(not x['ok'] for x in checks),'report':str(REPORT)},indent=2))
    return 0 if report['status']=='INTERNAL_RELEASE_CANDIDATE' else 1

if __name__ == '__main__': sys.exit(main())
