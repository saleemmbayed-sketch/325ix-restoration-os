#!/usr/bin/env python3
"""Offline contract for the interactive front-wheel-play -> expert-case handoff."""
from pathlib import Path
import json
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from app import App, db_connect, init_expert_cases, init_jobs, resolve_visual_catalog_selection, resolve_visual_reference


def make_catalog(path,multimodal):
    with sqlite3.connect(path) as db:
        if multimodal:
            db.executescript('''
                CREATE TABLE assembly(id TEXT PRIMARY KEY,group_name TEXT,title TEXT,source_url TEXT);
                CREATE TABLE part_record(id TEXT PRIMARY KEY,assembly_id TEXT,part_number TEXT,description TEXT);
                INSERT INTO assembly VALUES('front-1','front_axle','Front support assembly','https://catalog.example/front-1');
                INSERT INTO assembly VALUES('steer-1','steering','Steering linkage','https://catalog.example/steer-1');
                INSERT INTO assembly VALUES('brake-1','brakes','Brake disc','https://catalog.example/brake-1');
                INSERT INTO part_record VALUES('row-1','front-1','31121701059','Left control arm');
                INSERT INTO part_record VALUES('row-2','steer-1','32211701039','Left tie rod');
            ''')
        else:
            db.executescript('''
                CREATE TABLE assembly(id TEXT PRIMARY KEY,group_name TEXT,slug TEXT,source_url TEXT);
                CREATE TABLE part_row(id TEXT PRIMARY KEY,assembly_id TEXT,part_number TEXT,description TEXT);
                INSERT INTO assembly VALUES('front-1','front_axle','Front support assembly','https://catalog.example/front-1');
                INSERT INTO assembly VALUES('steer-1','steering','Steering linkage','https://catalog.example/steer-1');
                INSERT INTO assembly VALUES('brake-1','brakes','Brake disc','https://catalog.example/brake-1');
                INSERT INTO part_row VALUES('row-1','front-1','31121701059','Left control arm');
                INSERT INTO part_row VALUES('row-2','steer-1','32211701039','Left tie rod');
            ''')


def main():
    scene=resolve_visual_reference('ix_front_axle_workshop','tie_rod','steering')
    assert scene['component_label']=='Steering tie rod'
    assert scene['geometry_status']=='ORIENTATION_ONLY_NOT_INSTALLED_PART'
    assert resolve_visual_reference('','','front_axle') is None
    for values in (
        ('ix_front_axle_workshop','brake_disc','brakes'),
        ('ix_m20_engine_bay','tie_rod','steering'),
        ('ix_front_axle_workshop','missing_component','steering'),
        ('ix_front_axle_workshop','tie_rod','front_axle'),
    ):
        try:resolve_visual_reference(*values)
        except ValueError:pass
        else:raise AssertionError('Invalid visual reference was accepted: '+repr(values))

    for multimodal in (False,True):
        with tempfile.TemporaryDirectory() as td:
            db_path=Path(td)/'catalog.sqlite3';make_catalog(db_path,multimodal)
            selected=resolve_visual_catalog_selection(db_path,multimodal,'steer-1','row-2','32211701039')
            assert selected['assembly']['group_name']=='steering'
            assert selected['part']['description']=='Left tie rod'
            assembly_only=resolve_visual_catalog_selection(db_path,multimodal,'front-1')
            assert assembly_only['part'] is None
            for args in (
                ('brake-1','',''),
                ('steer-1','row-1','31121701059'),
                ('steer-1','row-2','99999999999'),
            ):
                try:resolve_visual_catalog_selection(db_path,multimodal,*args)
                except ValueError:pass
                else:raise AssertionError('Invalid catalog candidate was accepted: '+repr(args))
            try:resolve_visual_catalog_selection(db_path,multimodal,'','row-2','32211701039')
            except ValueError:pass
            else:raise AssertionError('Part candidate without parent assembly was accepted')

    with tempfile.TemporaryDirectory() as td:
        td=Path(td);catalog_path=td/'catalog.sqlite3';jobs_path=td/'jobs.sqlite3'
        make_catalog(catalog_path,True);init_jobs(jobs_path);init_expert_cases(jobs_path)
        server=SimpleNamespace(front_expert=json.loads((ROOT/'front_axle_expert_v1.json').read_text(encoding='utf-8')),
            catalog=catalog_path,multimodal=catalog_path,jobs=jobs_path,source_reviewed={'32211701039'},sources=[])
        class HandlerStub:
            def __init__(self):self.server=server
            def mm_db(self):return self.server.multimodal
            def get_db(self,readonly=False):return db_connect(self.server.jobs,readonly)
            def send_json(self,status,value):return status,value
            def send_blob(self,status,raw,mime,filename=None):return status,raw,mime,filename
        handler=HandlerStub()
        payload={'side':'LEFT','system':'steering','symptom':'Observed play near the left steering tie rod; cause unknown',
            'context':'Owner-reported complaint; inspection pending','visual_scene':'ix_front_axle_workshop',
            'visual_component_id':'tie_rod','assembly_id':'steer-1','candidate_id':'row-2','part_number':'32211701039'}
        status,created=App.start_expert_case(handler,payload)
        assert status==201 and created['clearance']=='NOT_APPROVED' and created['stage_count']==7
        assert created['catalog_assembly']['id']=='steer-1'
        assert created['catalog_candidate']['id']=='row-2'
        with db_connect(jobs_path,False) as db:
            job=db.execute('SELECT system,assembly_id,context FROM job WHERE id=?',(created['job_id'],)).fetchone()
            assert job['system']=='steering' and job['assembly_id']=='steer-1'
            assert 'not confirmed as installed' in job['context']
            assert db.execute('SELECT count(*) FROM expert_step WHERE job_id=?',(created['job_id'],)).fetchone()[0]==7
            event=json.loads(db.execute("SELECT payload_json FROM twin_event WHERE event_type='CASE_CREATED' AND entity_id=?",(str(created['job_id']),)).fetchone()[0])
            assert event['visual_reference']['geometry_status']=='ORIENTATION_ONLY_NOT_INSTALLED_PART'
            assert event['catalog_candidate']['source_reviewed_exact_number'] is True
            before=db.execute('SELECT count(*) FROM job').fetchone()[0]
        invalid={**payload,'assembly_id':'brake-1','candidate_id':'','part_number':''}
        try:App.start_expert_case(handler,invalid)
        except ValueError:pass
        else:raise AssertionError('Non-steering catalog assembly was accepted by the front-play workflow')
        with db_connect(jobs_path,False) as db:assert db.execute('SELECT count(*) FROM job').fetchone()[0]==before
        status,raw,mime,filename=App.export_job(handler,created['job_id'])
        work_order=raw.decode('utf-8')
        assert status==200 and mime.startswith('text/markdown') and filename.startswith('IX-')
        assert '3D locator: ix_front_axle_workshop / tie_rod' in work_order
        assert 'Part occurrence candidate: 32211701039 — Left tie rod' in work_order
        assert 'https://catalog.example/steer-1' in work_order
        assert 'Fitment remains unverified' in work_order

    site=(ROOT/'site.js').read_text(encoding='utf-8')
    backend=(ROOT/'app.py').read_text(encoding='utf-8')
    assert "api('/api/expert/front-play/start'" in site
    assert 'visual_scene:mechanicalScene.slug' in site and 'candidate_id:mechanicalCandidate?.id' in site
    assert 'await expertOpen(job.job_id)' in site
    assert 'Open BMW drawing & part evidence' in site
    assert 'Catalog wording:' in site and 'Verify variant, side, installed markings and actual hardware independently' in site
    workflow=json.loads((ROOT/'front_axle_expert_v1.json').read_text(encoding='utf-8'))
    assert all(not any(side in part['label'].lower() for side in ('left','right')) for part in workflow['parts'][:4])
    assert 'source_reviewed_exact_number' in site and 'NOT_CONFIRMED_AS_INSTALLED' in backend
    assert 'ORIENTATION_ONLY_NOT_INSTALLED_PART' in backend
    assert '325ix-visual-context-v1' in site and 'function saveVisualContext' in site
    assert 'async function restoreVisualContext' in site and 'async function restoreMissionContext' in site
    assert 'front_play_job_id:jobId,mission_job_id:jobId' in site
    assert 'history.pushState' in site and "window.addEventListener('popstate'" in site
    assert 'const startupContext=readVisualContext()' in site and 'restoreCatalogContext()' in site
    if subprocess.run(['node','--version'],capture_output=True).returncode==0:
        result=subprocess.run(['node','--check','site.js'],cwd=ROOT,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
    print('PASS: front-axle visual selection links to the seven-step case and exact catalog occurrence without asserting fitment')


if __name__=='__main__':
    main()
