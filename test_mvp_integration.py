#!/usr/bin/env python3
"""Reproducible local integration check for the front-axle MVP demo."""
import base64, json, pathlib, sqlite3, subprocess, sys, tempfile, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent

def call(base, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {} if body is None else {'Content-Type':'application/json','X-Workbench-Request':'same-origin'}
    req = urllib.request.Request(base+path, data=data, headers=headers, method='POST' if body else 'GET')
    with urllib.request.urlopen(req, timeout=4) as response:
        raw = response.read()
        return response.status, (json.loads(raw) if 'json' in response.headers.get('content-type','') else raw.decode())

def main():
    assert 'id="mission"' in (ROOT/'index.html').read_text(encoding='utf-8')
    assert 'loadLivingMission' in (ROOT/'site.js').read_text(encoding='utf-8')
    assert 'id="missionevidenceform"' in (ROOT/'index.html').read_text(encoding='utf-8')
    assert 'id="missionoptionform"' in (ROOT/'index.html').read_text(encoding='utf-8')
    assert 'id="missionaiform"' in (ROOT/'index.html').read_text(encoding='utf-8')
    assert 'loadVisualTwin' in (ROOT/'site.js').read_text(encoding='utf-8')
    assert 'visual-twin' in (ROOT/'site.css').read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory() as td:
        jobs = pathlib.Path(td) / 'jobs.sqlite3'
        with sqlite3.connect(jobs) as legacy:
            legacy.execute('CREATE TABLE legacy_marker(value TEXT NOT NULL)')
            legacy.execute("INSERT INTO legacy_marker VALUES('preserve-me')")
            legacy.execute('PRAGMA user_version=0')
        manual_input = pathlib.Path(td) / 'authorized_manuals'
        manual_input.mkdir()
        manual_text = 'STEERING INSPECTION\nCheck the steering linkage for observable free play.\fWHEEL ALIGNMENT\nRecord the applicable vehicle variant before using any limit.'
        (manual_input / 'e30_ix_steering.txt').write_text(manual_text, encoding='utf-8')
        (manual_input / 'e30_ix_steering.metadata.json').write_text(json.dumps({
            'title':'Authorized 325iX steering extract',
            'source_url':'https://example.invalid/authorized-manual-extract',
            'market':'Swiss/ECE',
            'variant_scope':'E30 325iX; verify production date and market',
            'document_type':'BMW_REPAIR_PROCEDURE_EXTRACT',
            'source_kind':'OWNER_AUTHORIZED_TEXT',
            'authority':'OWNER_SUPPLIED; MECHANIC_REVIEW_PENDING',
            'verification_status':'VERIFIED_SOURCE; PAGE_CAPTURED',
            'claims':[
                {'conflict_key':'steering_inspection_scope','claim_text':'Inspection scope for this extract','value':'visual only','source_locator':'page 1','status':'UNRESOLVED'},
                {'conflict_key':'steering_inspection_scope','claim_text':'Inspection scope for this extract','value':'qualified physical inspection','source_locator':'page 2','status':'UNRESOLVED'}
            ]
        }), encoding='utf-8')
        manual_index = pathlib.Path(td) / 'manual_index.sqlite3'
        indexed = subprocess.run([sys.executable, 'index_manuals.py', '--input', str(manual_input), '--output', str(manual_index)], cwd=ROOT, capture_output=True, text=True)
        assert indexed.returncode == 0, indexed.stderr
        proc = subprocess.Popen([sys.executable, 'app.py', '--port', '8878', '--jobs', str(jobs), '--manual-index', str(manual_index)], cwd=ROOT)
        base = 'http://127.0.0.1:8878'
        try:
            for _ in range(40):
                try:
                    call(base, '/api/vehicle'); break
                except Exception: time.sleep(.1)
            _, health = call(base, '/api/integration/health')
            assert health['status'] == 'READY_FOR_INTEGRATION_TEST'
            assert all(x['ok'] for x in health['checks'][:8])
            with sqlite3.connect(jobs) as migrated:
                assert migrated.execute('PRAGMA user_version').fetchone()[0] == 2
                assert migrated.execute('SELECT value FROM legacy_marker').fetchone()[0] == 'preserve-me'
            backups=list((pathlib.Path(td)/'workshop_jobs_backups').glob('jobs.pre-v2.*.sqlite3'))
            assert len(backups)==1
            with sqlite3.connect(backups[0]) as backup_db:
                assert backup_db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert backup_db.execute('SELECT value FROM legacy_marker').fetchone()[0]=='preserve-me'
            _, domains = call(base, '/api/restoration/domains')
            assert {x['id'] for x in domains['domains']} >= {'awd_drivetrain','suspension_steering','brakes','engine_support','transmission_clutch','electrical'}
            assert all(x['assembly_count'] > 0 for x in domains['domains'])
            assert any(x['group_name']=='bodywork' for x in domains['deferred'])
            _, visual = call(base, '/api/visual/twin')
            assert visual['vehicle']['vin'] == 'VIN_NOT_CONFIGURED'
            assert len(visual['systems']) >= 20
            assert all(x['assembly_count'] > 0 for x in visual['systems'])
            assert all(x['visual_state']=='REFERENCE_3D_ORIENTATION' for x in visual['systems'])
            assert all('2D_DIAGRAM_CALLOUTS' in (x['fallback'], 'CATALOG_SEARCH') for x in visual['systems'])
            status, awd_mission = call(base, '/api/missions/start', {'domain_id':'awd_drivetrain','system':'transfer_box_electric_gearbox','symptom':'Document transfer-case leak and driveline condition','context':'No measurements yet'})
            assert status == 201 and awd_mission['mission']['domain_id'] == 'awd_drivetrain'
            _, awd_overview = call(base, f"/api/job/{awd_mission['job_id']}/overview")
            assert awd_overview['job']['system'] == 'transfer_box_electric_gearbox' and awd_overview['readiness']['clearance'] == 'NOT_APPROVED'
            assert awd_overview['mission_progress']['current_stage'] == 'IDENTIFY'
            try:
                call(base, f"/api/job/{awd_mission['job_id']}/observation", {'type':'measurement','value':'0.10','unit':'','tool':'','source':'Invalid fixture'})
                raise AssertionError('Measurement without unit/method was accepted')
            except urllib.error.HTTPError as e:
                assert e.code == 400
            call(base, f"/api/job/{awd_mission['job_id']}/observation", {'type':'source_reference','value':'AWD procedure applicability remains under review','unit':'','tool':'document review','source':'Integration source fixture'})
            call(base, f"/api/job/{awd_mission['job_id']}/specialist-finding", {'agent_id':'diagnostics','intent':'diagnostics','finding':'Transfer-case condition is unresolved; inspect before selecting repair.','evidence':['Recorded driveline symptom','Source applicability remains under review'],'uncertainty':'Leak origin and internal condition are not established.','tests':['Qualified leak-source inspection','Verify tyre rolling circumference evidence'],'status':'REQUIRES_HUMAN_REVIEW','source':'Integration specialist fixture'})
            _, awd_progressed = call(base, f"/api/job/{awd_mission['job_id']}/overview")
            assert awd_progressed['mission_progress']['current_stage'] == 'DECIDE'
            _, progressed_missions = call(base, '/api/missions')
            progressed_awd=next(x for x in progressed_missions['missions'] if x['job_id']==awd_mission['job_id'])
            assert progressed_awd['current_stage']=='DECIDE' and progressed_awd['progress']['percent']>0
            status, electrical_mission = call(base, '/api/missions/start', {'domain_id':'electrical','system':'vehicle_electrical_system','symptom':'Inspect intermittent chassis electrical fault','context':'Circuit not identified yet'})
            assert status == 201 and electrical_mission['mission']['domain_id'] == 'electrical'
            _, mission_list = call(base, '/api/missions')
            assert {x['domain_id'] for x in mission_list['missions']} >= {'awd_drivetrain','electrical'}
            _, twin_before = call(base, '/api/twin')
            assert twin_before['vehicle']['vin'] == 'VIN_NOT_CONFIGURED'
            before_xp = twin_before['gamification']['xp']
            status, twin_event = call(base, '/api/twin/event', {
                'event_type':'MEASUREMENT_RECORDED',
                'entity_type':'component',
                'payload':{'value':'0.10','unit':'mm','description':'QA fixture measurement'},
                'source':'Integration test fixture'
            })
            assert status == 201 and twin_event['xp_value'] == 20
            _, twin_after_event = call(base, '/api/twin')
            assert twin_after_event['gamification']['xp'] == before_xp + 20
            assert any(x['event_type']=='MEASUREMENT_RECORDED' for x in twin_after_event['events'])
            status, component = call(base, '/api/twin/component', {'component_type':'Steering tie rod','location':'Front axle','side':'LEFT','marking':'owner-photo-marking','source':'QA component fixture'})
            assert status == 201 and component['status'] == 'IDENTITY_UNCONFIRMED'
            component_id = component['component_id']
            status, fact = call(base, f'/api/twin/component/{component_id}/fact', {'layer':'OWNER_REPORTED','field':'condition','value':'Visible boot damage; inspection pending','confidence':'OWNER_REPORTED','source':'Owner photo P-001'})
            assert status == 201 and fact['confidence'] == 'OWNER_REPORTED'
            _, components = call(base, '/api/twin/components')
            assert components['components'][0]['id'] == component_id and components['uncertainty']['owner_reported'] == 1
            _, isolated_job_overview = call(base, f"/api/job/{awd_mission['job_id']}/overview")
            assert all(x['entity_type'] in {'case','job'} for x in isolated_job_overview['twin_events'])
            fake_png=base64.b64encode(b'\x89PNG\r\n\x1a\n'+b'fixture-image-bytes-'*8).decode()
            status, attachment = call(base, f'/api/twin/component/{component_id}/attachment', {'kind':'PHOTO','title':'As-found tie-rod fixture photo','source':'Integration fixture','variant_scope':'Swiss/ECE 325iX','image_base64':fake_png})
            assert status == 201 and len(attachment['sha256']) == 64
            _, components_with_photo = call(base, '/api/twin/components')
            assert components_with_photo['components'][0]['attachments'][0]['kind'] == 'PHOTO'
            with urllib.request.urlopen(base+'/api/twin/attachment?id='+str(attachment['attachment_id']), timeout=4) as photo_response:
                assert photo_response.status == 200 and photo_response.read(8) == b'\x89PNG\r\n\x1a\n'
            _, specialists = call(base, '/api/specialists')
            assert len(specialists['agents']) == 6
            _, workflow = call(base, '/api/workflow/front-axle')
            assert len(workflow['steps']) == 7 and workflow['clearance'] == 'NOT_APPROVED'
            _, manual_status = call(base, '/api/manuals/status')
            assert manual_status['indexed_documents'] == 1 and manual_status['indexed_pages'] == 2
            assert manual_status['verified_documents'] == 1 and manual_status['schema_version'] == 2
            assert manual_status['claim_records'] == 2 and manual_status['unresolved_conflict_groups'] == 1
            _, conflicts = call(base, '/api/manuals/conflicts')
            assert conflicts['conflicts'][0]['conflict_key'] == 'steering_inspection_scope'
            assert conflicts['conflicts'][0]['status'] == 'UNRESOLVED'
            _, manual_search = call(base, '/api/manuals/search?q=steering')
            assert manual_search['results'][0]['citation'].startswith('Authorized 325iX steering extract — page 1')
            assert manual_search['results'][0]['provenance']['variant_scope'].startswith('E30 325iX')
            assert len(manual_search['results'][0]['provenance']['page_sha256']) == 64
            _, assistant = call(base, '/api/ai/ask', {'question':'What do I know about the steering part 31121701059 and what is still missing?','system':'front_axle'})
            assert assistant['model'] == 'OFFLINE_GROUNDED_FALLBACK' and assistant['policy'].startswith('GROUNDED_RULES')
            assert assistant['routing']['intent'] == 'part_identity' and assistant['routing']['safety_class'] == 'SAFETY_CRITICAL'
            _, routed = call(base, '/api/ai/route', {'question':'Can this AWD steering component fit and what measurements are needed?','system':'front_axle'})
            assert routed['intent'] == 'fitment' and 'physical_verification' in routed['approval_gates']
            assert assistant['manual_excerpts'][0]['provenance']['document_id'].startswith('MNL-')
            assert assistant['manual_conflicts'][0]['status'] == 'UNRESOLVED'
            _, arabic_assistant = call(base, '/api/ai/ask', {'question':'ما الذي نعرفه عن القطعة 31121701059 وما الدليل الناقص؟','system':'front_axle'})
            assert arabic_assistant['language'] == 'ar' and arabic_assistant['model'] == 'OFFLINE_GROUNDED_FALLBACK'
            _, requested_arabic = call(base, '/api/ai/ask', {'question':'What evidence is missing for this steering part?','system':'front_axle','language':'ar'})
            assert requested_arabic['language'] == 'ar'
            _, search = call(base, '/api/search?q=31121701059')
            assert search['results'][0]['part_number'] == '31121701059'
            _, assembly = call(base, '/api/assembly?id=A-776c8e5f755bc176')
            assert assembly['assembly']['id'] == 'A-776c8e5f755bc176' and len(assembly['parts']) > 0
            _, dossier = call(base, '/api/part-dossier?id='+search['results'][0]['id'])
            assert dossier['part']['part_number'] == '31121701059' and dossier['figures'][0]['image_asset_id'].startswith('IMG-')
            _, expert = call(base, '/api/expert/front-play')
            assert len(expert['assemblies']) == 5 and all(x['rows'] for x in expert['parts'])
            with urllib.request.urlopen(base+'/api/diagram?asset=IMG-d20b4403da1f7395', timeout=4) as image_response:
                assert image_response.status == 200 and image_response.read(12).startswith(b'RIFF')
            status, case = call(base, '/api/expert/front-play/start', {'side':'LEFT','symptom':'Clunk near left wheel','context':'No measurements yet'})
            assert status == 201 and case['clearance'] == 'NOT_APPROVED'
            jid = case['job_id']
            call(base, '/api/expert/front-play/step', {'job_id':jid,'code':'SYMPTOM','status':'OBSERVED','finding':'Clunk on slow left turn','source':'Owner statement'})
            call(base, '/api/expert/front-play/step', {'job_id':jid,'code':'TRIAGE','status':'NEEDS_SPECIALIST','finding':'Awaiting qualified inspection','source':'BMW_TIS_STEER_7'})
            try:
                call(base, '/api/expert/front-play/step', {'job_id':jid,'code':'TRIAGE','status':'CLEARED','finding':'Unsafe attempted clearance','source':'Invalid test'})
                raise AssertionError('Safety-critical checkpoint accepted invalid CLEARED state')
            except urllib.error.HTTPError as e:
                assert e.code == 400
            call(base, f'/api/job/{jid}/observation', {'type':'measurement','value':'0.10','unit':'mm','tool':'Dial indicator fixture','source':'Integration measurement fixture'})
            call(base, f'/api/job/{jid}/options', {'path':'NEW_REPLACEMENT','description':'New replacement candidate; exact iX fitment not established','part_number':'CANDIDATE-NEW','fitment_status':'UNVERIFIED','decision_status':'PROPOSED','evidence':'Candidate listing only; no dimensional verification','source':'Supplier listing pointer','cost_estimate':'EUR unknown','availability':'Source required'})
            call(base, f'/api/job/{jid}/options', {'path':'REPAIR_EXISTING','description':'Inspect and rebuild installed component if serviceable','part_number':'31121701059','fitment_status':'CATALOG_ONLY','decision_status':'SELECTED_PENDING_SIGNOFF','evidence':'Existing component must be inspected before replacement decision','source':'Owner observation; qualified inspection pending','cost_estimate':'Inspection first','availability':'Component on vehicle'})
            try:
                call(base, f'/api/job/{jid}/options', {'path':'REPAIR_EXISTING','description':'Invalid software approval attempt','part_number':'31121701059','fitment_status':'VERIFIED_PENDING_SIGNOFF','decision_status':'APPROVED_BY_SOFTWARE','evidence':'Invalid test','source':'Invalid test'})
                raise AssertionError('Software accepted prohibited repair approval state')
            except urllib.error.HTTPError as e:
                assert e.code == 400
            _, options = call(base, f'/api/job/{jid}/options')
            assert [x['path'] for x in options['options']] == ['REPAIR_EXISTING','NEW_REPLACEMENT']
            assert options['clearance'] == 'NOT_APPROVED'
            status, finding = call(base, f'/api/job/{jid}/specialist-finding', {'agent_id':'diagnostics','intent':'diagnostic_triage','finding':'Wheel play source is unresolved; do not identify the failed component yet.','evidence':['Owner symptom: clunk on slow left turn','No calibrated measurement recorded'],'uncertainty':'Joint, rack, hub and mounting source are not distinguished.','tests':['Qualified inspection with loaded wheel and safe lift','Record calibrated play measurement by component'],'status':'REQUIRES_HUMAN_REVIEW','source':'Diagnostics specialist; integration fixture'})
            assert status == 201 and finding['status'] == 'REQUIRES_HUMAN_REVIEW'
            _, case_assistant = call(base, '/api/ai/ask', {'question':'What evidence is still missing for this case?','system':'front_axle','job_id':jid})
            assert case_assistant['case_context']['job']['id'] == jid
            assert case_assistant['case_context']['specialist_findings'][0]['agent_id'] == 'diagnostics'
            try:
                _, overview = call(base, f'/api/job/{jid}/overview')
            except urllib.error.HTTPError as exc:
                raise AssertionError('case overview failed: '+exc.read().decode()) from exc
            assert overview['job']['id'] == jid and overview['readiness']['clearance'] == 'NOT_APPROVED'
            assert overview['readiness']['evidence_count'] >= 4
            assert overview['specialist_findings'][0]['agent_id'] == 'diagnostics'
            assert any('Qualified physical sign-off' in x for x in overview['readiness']['blockers'])
            _, reopened = call(base, f'/api/expert/front-play/cases?job_id={jid}')
            _, export = call(base, f'/api/job/{jid}.md')
            assert any(x['code']=='SYMPTOM' and x['status']=='OBSERVED' for x in reopened['steps'])
            assert any(x['code']=='TRIAGE' and x['status']=='NEEDS_SPECIALIST' for x in reopened['steps'])
            assert any(x['type']=='measurement' for x in reopened['observations'])
            assert 'NOT_APPROVED' in export and 'REPAIR_EXISTING' in export
            proc.terminate(); proc.wait(timeout=5)
            proc=subprocess.Popen([sys.executable, 'app.py', '--port', '8878', '--jobs', str(jobs)], cwd=ROOT)
            for _ in range(40):
                try: call(base, '/api/vehicle'); break
                except Exception: time.sleep(.1)
            _, after_restart = call(base, f'/api/expert/front-play/cases?job_id={jid}')
            assert after_restart['case']['job_id'] == jid and len(after_restart['observations']) == 1
            _, options_after_restart = call(base, f'/api/job/{jid}/options')
            assert len(options_after_restart['options']) == 2 and options_after_restart['options'][0]['path'] == 'REPAIR_EXISTING'
            _, twin_after_restart = call(base, '/api/twin')
            assert any(x['event_type']=='MEASUREMENT_RECORDED' for x in twin_after_restart['events'])
            assert twin_after_restart['gamification']['xp'] >= before_xp + 20
            _, missions_after_restart = call(base, '/api/missions')
            assert {x['domain_id'] for x in missions_after_restart['missions']} >= {'awd_drivetrain','electrical','suspension_steering'}
            print('PASS: real catalog/graph, manual provenance/citations/conflicts, digital twin events/gamification, repair-first options, specialist registry, workflow, persistence, measurement ledger, restart recovery, export')
        finally:
            proc.terminate(); proc.wait(timeout=5)

if __name__ == '__main__': main()
