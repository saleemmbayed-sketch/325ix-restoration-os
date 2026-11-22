#!/usr/bin/env python3
"""BMW 325iX mechanical evidence workbench: offline, read-only catalog, local job records.

No LLM inference, OEM fitment assertion, live web requests or unverified repair specifications.
Works on Python 3.10+ macOS/Linux without third-party dependencies.
"""
import argparse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import json
import re
import sqlite3
import hashlib
import base64
import binascii
import os
import subprocess
import urllib.request
import urllib.error
from urllib.parse import urlsplit as parse_url
from urllib.parse import parse_qs, urlsplit

APP=Path(__file__).resolve().parent
VEHICLE={
    'vin':os.environ.get('BMW_325IX_VIN','VIN_NOT_CONFIGURED'), 'build_date':'1987-12-10',
    'model':'1988 BMW E30 325iX', 'market':'Swiss/ECE owner-reported',
    'body':'4-door LHD sedan', 'transmission':'manual', 'drivetrain':'AWD',
    'engine':'replacement M20B25; owner-confirmed, 2.5 L, 12-valve',
    'engine_number':os.environ.get('BMW_325IX_ENGINE_NUMBER','ENGINE_NUMBER_NOT_CONFIGURED'), 'engine_status':'runs well, owner-reported'
}
CRITICAL_GROUPS={'steering','front_axle','rear_axle','brakes','wheels','drive_shaft',
 'transfer_box_electric_gearbox','fuel_supply','bodywork','manual_transmission','engine'}
GROUP_PROMPTS={
 'steering':{
 'safety':'Steering system: no road-use clearance without qualified inspection if play, binding, leaks or damaged structural/attachment parts are suspected.',
 'questions':['Which corner/side and when does the symptom occur (standing, slow-speed, braking, turning)?',
              'Is the movement originating at a tie-rod joint, rack housing, steering shaft coupling, suspension joint or wheel hub? Record what is directly visible without forcing components.',
              'Were any parts changed or adjusted before the symptom? Photograph part markings and mounts.',
              'What measurements or specialist inspection findings are available?'],
 'reminder':'Do not infer a replacement rack or torque figure from a single symptom.'},
 'front_axle':{
 'safety':'Front axle, hubs and loaded springs are safety-critical. Qualified oversight required for lifting, disassembly, spring compression and final inspection.',
 'questions':['Which corner and what symptom (noise, play, vibration, leak, ride height)?',
              'Take an overview photograph and note any visibly damaged boot, bushing, mount or leaking shock.',
              'Note installed part stamp, dimensions or axle type only if accessible without risk.',
              'Have vehicle ride height, tyre size and condition, and wheel/hub observations been documented?'],
 'reminder':'Do not substitute a standard 325i strut insert or other hardware without iX geometry and specification verification.'},
 'brakes':{
 'safety':'Brake/ABS faults require qualified inspection before driving. Do not infer brake pressure, bleeding steps or torque without the actual BMW procedure.',
 'questions':['Is there a dashboard warning, fluid leak, unusual pedal feel, braking imbalance, or noise?',
              'Is brake-fluid condition and level visible without opening the hydraulic system?',
              'Which wheel/caliper and what work has already been done?',
              'Does the failure appear with engine off/on, and are any test measurements documented?'],
 'reminder':'Use the dedicated 1988 325iX ETM for circuit tests after market applicability is checked.'},
 'transfer_box_electric_gearbox':{
 'safety':'325iX viscous AWD components can be damaged by incorrect on-vehicle tests. Do not perform spin/load tests without the exact BMW procedure.',
 'questions':['Where is the noise/leak/vibration? At what speed, turning condition and load?',
              'Have all four tyre sizes and rolling circumferences been checked?',
              'What transfer case, shaft or flange markings and previous repair history are known?',
              'Is any specialist measurement or differential inspection available?'],
 'reminder':'Avoid improvising viscous coupling tests.'}
}
DEFAULT_PROMPTS={
 'safety':'Record observations first. Safety-critical vehicle systems require competent oversight and appropriate manufacturer procedures.',
 'questions':['What exactly happens and under what conditions?','Where on the car is it located?',
             'What photographs and component identifiers are available?',
             'What previous work or measurements might explain the symptom?'],
 'reminder':'An exploded catalog is for identification, not proof of compatibility or an installation procedure.'
}

CHECK_TEMPLATES={
 'front_axle':[
   ('LOCATION','Identify exact side, location, driving condition and symptom'),
   ('PHOTO','Document visually accessible strut, axle/boot, hub and mounting points'),
   ('IDENTITY','Record markings and compare to iX catalog; not generic E30'),
   ('PHYSICAL','Qualified mechanic identifies source of play/leak/noise; no improvised lifting'),
   ('OEM_PROCEDURE','Acquire appropriate BMW iX procedure and variant-specific values before repair'),
   ('REVIEW','Independent inspection and post-repair validation; road use not approved by software')],
 'steering':[
   ('LOCATION','Locate symptom and identify rack, tie rod, steering shaft, or adjacent suspension components'),
   ('PHOTO','Record steering parts and attachment area photographs'),
   ('IDENTITY','Check installed component/OEM part number and AWD-specific geometry'),
   ('PHYSICAL','Qualified examination to distinguish free play in joints, mounts and rack'),
   ('OEM_PROCEDURE','Consult source-verified steering procedure and applicable values'),
   ('REVIEW','Independent steering alignment/repair sign-off before road use')],
 'brakes':[
   ('SYMPTOM','Record brake/ABS symptoms, dash lamps and operating conditions'),
   ('VISUAL','Photograph accessible lines, fluid reservoir, and wheel area without dismantling'),
   ('ETM','Locate model/market-appropriate 1988 iX ETM wiring page'),
   ('PROCEDURE','Qualified brake inspection with verified hydraulic/bleeding procedures'),
   ('REVIEW','Independent brake test and sign-off before road use')],
 'transfer_box_electric_gearbox':[
   ('SYMPTOM','Describe noises/vibration/leaks and exact driving condition'),
   ('TYRES','Document tyre dimensions and condition at each wheel; do not infer matching circumference'),
   ('PHOTO','Capture safe accessible propshaft/transfer case markings'),
   ('OEM_PROCEDURE','Retrieve correct AWD diagnostic/test procedure before touching driveline'),
   ('REVIEW','Qualified AWD assessment; do not use improvised wheel-spin tests')],
}
DEFAULT_CHECKS=[('OBSERVE','Document symptom, location, and observable evidence'),('PHOTO','Capture relevant photos and markings where safely accessible'),('SOURCE','Find correct BMW procedure and part configuration'),('MEASURE','Use appropriate qualified inspection and documented measurements'),('REVIEW','Verify outcome and retain qualified sign-off where relevant')]

REPAIR_PATHS={
    'REPAIR_EXISTING':1,
    'USED_OEM_REFURBISHED':2,
    'SPEC_VERIFIED_CROSS_FIT':3,
    'NEW_REPLACEMENT':4,
}
OPTION_FITMENT={'UNVERIFIED','CATALOG_ONLY','PHYSICALLY_CHECKED','VERIFIED_PENDING_SIGNOFF'}
OPTION_DECISIONS={'PROPOSED','SELECTED_PENDING_SIGNOFF','REJECTED'}
TWIN_EVENT_TYPES={'CASE_CREATED','PHOTO_CAPTURED','OBSERVATION_RECORDED','MEASUREMENT_RECORDED','PROCEDURE_VERIFIED','COMPONENT_IDENTIFIED','REPAIR_OPTION_RECORDED','QA_RECORDED','QUALIFIED_SIGNOFF_RECORDED','DEVIATION_RECORDED','MILESTONE_RECORDED'}
TWIN_ENTITY_TYPES={'vehicle','case','component','job','part','work_order'}
TWIN_XP={'CASE_CREATED':5,'PHOTO_CAPTURED':10,'OBSERVATION_RECORDED':10,'MEASUREMENT_RECORDED':20,'PROCEDURE_VERIFIED':25,'COMPONENT_IDENTIFIED':20,'REPAIR_OPTION_RECORDED':10,'QA_RECORDED':30,'QUALIFIED_SIGNOFF_RECORDED':50,'DEVIATION_RECORDED':15,'MILESTONE_RECORDED':25}
RESTORATION_DOMAINS={
    'awd_drivetrain':{'label':'AWD & Drivetrain','priority':'P0','groups':['transfer_box_electric_gearbox','drive_shaft'],'default_system':'transfer_box_electric_gearbox','promise':'Restore and verify iX-specific torque transfer, shafts, couplings and interfaces.'},
    'suspension_steering':{'label':'Suspension & Steering','priority':'P0','groups':['front_axle','rear_axle','steering','wheels'],'default_system':'front_axle','promise':'Diagnose, restore and verify chassis control, geometry and wheel interfaces.'},
    'brakes':{'label':'Brakes','priority':'P0','groups':['brakes'],'default_system':'brakes','promise':'Document and restore braking and ABS-related hardware with qualified sign-off.'},
    'engine_support':{'label':'Engine, Cooling & Fuel','priority':'P0','groups':['engine','radiator','fuel_preparation_system','fuel_supply','exhaust_system'],'default_system':'engine','promise':'Maintain the installed M20B25 and its cooling, fuel and exhaust support systems.'},
    'transmission_clutch':{'label':'Transmission & Clutch','priority':'P0','groups':['manual_transmission','clutch','gearshift','pedals'],'default_system':'manual_transmission','promise':'Restore manual power delivery, clutch actuation and shift interfaces.'},
    'electrical':{'label':'Electrical & Controls','priority':'P0','groups':['vehicle_electrical_system','engine_electrical_system','lighting','instruments_measuring_systems'],'default_system':'vehicle_electrical_system','promise':'Trace and restore starting, charging, engine, chassis, lighting and instrument circuits.'},
    'climate_visibility':{'label':'Climate & Visibility','priority':'P1','groups':['heater_and_air_conditioning'],'default_system':'heater_and_air_conditioning','promise':'Restore heating, ventilation and demisting needed for safe operation.'},
}
DEFERRED_CATALOG_GROUPS={'bodywork','vehicle_trim','seats','retrofitting_conversion_accessories','equipment_parts','sliding_roof_folding_top','audio_navigation_electronic_systems','restraint_system_and_accessories','distance_systems_cruise_control'}
DOMAIN_BY_GROUP={group:domain_id for domain_id,domain in RESTORATION_DOMAINS.items() for group in domain['groups']}
DB_SCHEMA_VERSION=2

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def db_connect(path,readonly=False):
    if readonly:
        uri=path.resolve().as_uri()+'?mode=ro&immutable=1'
        connection=sqlite3.connect(uri,uri=True,timeout=8)
    else:
        connection=sqlite3.connect(path,timeout=8)
    connection.row_factory=sqlite3.Row
    return connection

def backup_before_migration(path,target_version=DB_SCHEMA_VERSION):
    """Create an integrity-checked SQLite backup before any schema mutation."""
    if not path.is_file() or path.stat().st_size==0:return None
    source_uri='file:'+str(path.resolve())+'?mode=ro'
    with sqlite3.connect(source_uri,uri=True,timeout=8) as source:
        current=int(source.execute('PRAGMA user_version').fetchone()[0])
        if current>=target_version:return None
        backup_dir=path.parent/'workshop_jobs_backups';backup_dir.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        destination=backup_dir/f'{path.stem}.pre-v{target_version}.{stamp}.sqlite3'
        suffix=1
        while destination.exists():
            destination=backup_dir/f'{path.stem}.pre-v{target_version}.{stamp}.{suffix}.sqlite3';suffix+=1
        with sqlite3.connect(destination) as target:source.backup(target)
    with sqlite3.connect(destination) as check:
        if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            destination.unlink(missing_ok=True);raise RuntimeError('Pre-migration job database backup failed integrity check')
    return destination

def init_jobs(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    backup_before_migration(path)
    with db_connect(path) as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS job(
            id INTEGER PRIMARY KEY AUTOINCREMENT,created_utc TEXT NOT NULL,
            system TEXT NOT NULL,assembly_id TEXT, symptom TEXT NOT NULL,
            context TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',
            risk TEXT NOT NULL, qualified_reviewer TEXT, clearance TEXT NOT NULL DEFAULT 'NOT_APPROVED');
        CREATE TABLE IF NOT EXISTS diagnostic_check(
            id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER NOT NULL,
            code TEXT NOT NULL,label TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'NOT_CHECKED',finding TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',updated_utc TEXT NOT NULL,
            UNIQUE(job_id,code),FOREIGN KEY(job_id) REFERENCES job(id));
        CREATE TABLE IF NOT EXISTS observation(
            id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER NOT NULL,
            created_utc TEXT NOT NULL,type TEXT NOT NULL,value TEXT NOT NULL,
            unit TEXT DEFAULT '',tool TEXT DEFAULT '',source TEXT DEFAULT '',
            FOREIGN KEY(job_id) REFERENCES job(id));
        CREATE TABLE IF NOT EXISTS repair_option(
            id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER NOT NULL,
            created_utc TEXT NOT NULL,path TEXT NOT NULL,description TEXT NOT NULL,
            part_number TEXT NOT NULL DEFAULT '',fitment_status TEXT NOT NULL,
            evidence TEXT NOT NULL,source TEXT NOT NULL,cost_estimate TEXT NOT NULL DEFAULT '',
            availability TEXT NOT NULL DEFAULT '',decision_status TEXT NOT NULL DEFAULT 'PROPOSED',
            FOREIGN KEY(job_id) REFERENCES job(id));
        CREATE TABLE IF NOT EXISTS vehicle_twin(
            id INTEGER PRIMARY KEY CHECK(id=1), vin TEXT NOT NULL, factory_state_json TEXT NOT NULL,
            as_installed_state_json TEXT NOT NULL, confidence_json TEXT NOT NULL, updated_utc TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS twin_event(
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_utc TEXT NOT NULL, event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, payload_json TEXT NOT NULL,
            source TEXT NOT NULL, xp_value INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS component_instance(
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_utc TEXT NOT NULL, updated_utc TEXT NOT NULL,
            component_type TEXT NOT NULL, location TEXT NOT NULL DEFAULT '', side TEXT NOT NULL DEFAULT '',
            oem_part_number TEXT NOT NULL DEFAULT '', marking TEXT NOT NULL DEFAULT '', condition TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'IDENTITY_UNCONFIRMED');
        CREATE TABLE IF NOT EXISTS component_fact(
            id INTEGER PRIMARY KEY AUTOINCREMENT, component_id INTEGER NOT NULL, created_utc TEXT NOT NULL,
            layer TEXT NOT NULL, field TEXT NOT NULL, value TEXT NOT NULL, confidence TEXT NOT NULL,
            source TEXT NOT NULL, FOREIGN KEY(component_id) REFERENCES component_instance(id));
        CREATE TABLE IF NOT EXISTS component_attachment(
            id INTEGER PRIMARY KEY AUTOINCREMENT, component_id INTEGER NOT NULL, created_utc TEXT NOT NULL,
            kind TEXT NOT NULL, title TEXT NOT NULL, source TEXT NOT NULL, source_url TEXT NOT NULL DEFAULT '',
            rights TEXT NOT NULL DEFAULT 'OWNER_SUPPLIED_OR_REVIEW_REQUIRED', variant_scope TEXT NOT NULL DEFAULT '',
            media_path TEXT NOT NULL DEFAULT '', mime TEXT NOT NULL DEFAULT '', sha256 TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '', FOREIGN KEY(component_id) REFERENCES component_instance(id));
        CREATE TABLE IF NOT EXISTS specialist_finding(
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, created_utc TEXT NOT NULL,
            agent_id TEXT NOT NULL, intent TEXT NOT NULL, finding TEXT NOT NULL, evidence_json TEXT NOT NULL,
            uncertainty TEXT NOT NULL, tests_json TEXT NOT NULL, status TEXT NOT NULL, source TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES job(id));
        CREATE TABLE IF NOT EXISTS restoration_mission(
            job_id INTEGER PRIMARY KEY, domain_id TEXT NOT NULL, title TEXT NOT NULL,
            mission_status TEXT NOT NULL DEFAULT 'ACTIVE', current_stage TEXT NOT NULL DEFAULT 'INTAKE',
            created_utc TEXT NOT NULL, updated_utc TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES job(id));
        ''')
        db.execute('''INSERT OR IGNORE INTO vehicle_twin(id,vin,factory_state_json,as_installed_state_json,confidence_json,updated_utc)
            VALUES(1,?,?,?,?,?)''',(
            VEHICLE['vin'],json.dumps({'model':VEHICLE['model'],'build_date':VEHICLE['build_date'],'market':VEHICLE['market'],'body':VEHICLE['body'],'transmission':VEHICLE['transmission'],'drivetrain':VEHICLE['drivetrain']},ensure_ascii=False),
            json.dumps({'engine':VEHICLE['engine'],'engine_number':VEHICLE['engine_number'],'engine_status':VEHICLE['engine_status']},ensure_ascii=False),
            json.dumps({'factory':'CATALOG_APPLICABILITY_REVIEW_REQUIRED','engine':'OWNER_CONFIRMED'},ensure_ascii=False),now()))
        db.execute(f'PRAGMA user_version={DB_SCHEMA_VERSION}')

def insert_twin_event(db,event_type,entity_type,entity_id,payload,source='WORKBENCH'):
    db.execute('INSERT INTO twin_event(created_utc,event_type,entity_type,entity_id,payload_json,source,xp_value) VALUES(?,?,?,?,?,?,?)',
        (now(),event_type,entity_type,str(entity_id),json.dumps(payload,ensure_ascii=False),trim(source,400),TWIN_XP.get(event_type,0)))

def derive_mission_progress(db,job_id):
    """Derive restart-safe mission state from persisted evidence; never from XP."""
    job=db.execute('SELECT status FROM job WHERE id=?',(job_id,)).fetchone()
    if not job:return None
    observation_types={x[0] for x in db.execute('SELECT type FROM observation WHERE job_id=?',(job_id,))}
    findings=int(db.execute('SELECT count(*) FROM specialist_finding WHERE job_id=?',(job_id,)).fetchone()[0])
    checks=int(db.execute("SELECT count(*) FROM diagnostic_check WHERE job_id=? AND status!='NOT_CHECKED'",(job_id,)).fetchone()[0])
    expert_checks=int(db.execute("SELECT count(*) FROM expert_step WHERE job_id=? AND status!='NOT_CHECKED'",(job_id,)).fetchone()[0]) if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='expert_step'").fetchone() else 0
    options=int(db.execute('SELECT count(*) FROM repair_option WHERE job_id=?',(job_id,)).fetchone()[0])
    events={x[0] for x in db.execute("SELECT event_type FROM twin_event WHERE entity_id=? AND entity_type IN ('case','job')",(str(job_id),))}
    event_count=int(db.execute("SELECT count(*) FROM twin_event WHERE entity_id=? AND entity_type IN ('case','job')",(str(job_id),)).fetchone()[0])
    stages=[
        {'id':'INTAKE','label':'Intake','detail':'Symptom and vehicle-system context recorded','complete':True},
        {'id':'IDENTIFY','label':'Identify','detail':'Component identity or specialist finding recorded','complete':findings>0 or 'COMPONENT_IDENTIFIED' in events},
        {'id':'VERIFY','label':'Verify','detail':'Photo, source, inspection or calibrated measurement recorded','complete':bool(observation_types & {'photo_reference','source_reference','measurement','inspection'})},
        {'id':'DIAGNOSE','label':'Diagnose','detail':'Discriminating checks and findings recorded','complete':checks+expert_checks>0 or findings>0},
        {'id':'DECIDE','label':'Decide','detail':'Repair-first comparison and human decision recorded','complete':options>0},
        {'id':'EXECUTE','label':'Execute','detail':'Work performed and as-built deviation recorded','complete':job['status'] in {'WORK_COMPLETED','QA_PENDING','QA_COMPLETE'} or 'DEVIATION_RECORDED' in events},
        {'id':'QA','label':'QA','detail':'Independent checks and qualified sign-off recorded','complete':'QA_RECORDED' in events or 'QUALIFIED_SIGNOFF_RECORDED' in events},
        {'id':'PRESERVE','label':'Preserve','detail':'Evidence written to the vehicle twin','complete':event_count>1},
    ]
    complete=sum(1 for x in stages if x['complete'])
    current=next((x['id'] for x in stages if not x['complete']),'COMPLETE')
    return {'current_stage':current,'completed_stages':complete,'total_stages':len(stages),'percent':round(complete/len(stages)*100),'stages':stages,
        'policy':'Mission progress is derived from persisted evidence and workflow state; it never grants fitment, repair or road-use approval.'}

def sync_mission_progress(db,job_id):
    progress=derive_mission_progress(db,job_id)
    if progress:db.execute('UPDATE restoration_mission SET current_stage=?,updated_utc=? WHERE job_id=?',(progress['current_stage'],now(),job_id))
    return progress

def init_expert_cases(path):
    # Additive tables, never overwrite or migrate owner work-order records.
    with db_connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS expert_case(
            job_id INTEGER PRIMARY KEY, workflow_id TEXT NOT NULL, side TEXT NOT NULL,
            created_utc TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES job(id));
        CREATE TABLE IF NOT EXISTS expert_step(
            job_id INTEGER NOT NULL, code TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'NOT_CHECKED',
            finding TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '',
            updated_utc TEXT NOT NULL, PRIMARY KEY(job_id,code),
            FOREIGN KEY(job_id) REFERENCES job(id));
        ''')

def init_photos(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with db_connect(path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS part_photo(
            id INTEGER PRIMARY KEY AUTOINCREMENT,part_number TEXT NOT NULL,
            kind TEXT NOT NULL,source_label TEXT NOT NULL,source_url TEXT NOT NULL DEFAULT '',
            original_filename TEXT NOT NULL DEFAULT '',image_path TEXT NOT NULL,mime TEXT NOT NULL,
            sha256 TEXT NOT NULL,created_utc TEXT NOT NULL)""")
        db.commit()

def encode(x):return json.dumps(x,ensure_ascii=False,default=str).encode('utf-8')

def trim(value,limit):return str(value or '').strip()[:limit]

def escape_like(s):return s.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')

def sourced_curated(number,record):
    """Conservatively recognize a separately researched exact-number record.

    A URL alone in the catalog's *candidate lead* field is never evidence.
    This only checks the structural provenance and does not independently
    authenticate claims made by a supplier or prove as-installed fitment.
    """
    if not isinstance(record,dict):return False
    if record.get('part_number') != number or not record.get('reviewed_utc') or not record.get('evidence_status'):
        return False
    sources=record.get('sources')
    return bool(isinstance(sources,list) and any(
        isinstance(x,dict) and isinstance(x.get('url'),str) and x['url'].startswith('https://')
        and isinstance(x.get('status'),str) and x['status'].strip()
        for x in sources))

class App(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):print('[workbench]',self.address_string(),fmt%args)
    def local_host_ok(self):
        host=self.headers.get('Host','')
        if not host or '/' in host or '@' in host:return False
        try:
            parsed=urlsplit('http://'+host)
            return (parsed.hostname in {'127.0.0.1','localhost'}
                    and parsed.port==self.server.server_port
                    and parsed.path=='')
        except (ValueError,TypeError):return False
    def require_request_policy(self,write=False):
        if not self.local_host_ok():
            self.send_json(403,{'error':'Local workbench only: invalid Host header'})
            return False
        if write:
            origin=self.headers.get('Origin')
            allowed={'http://127.0.0.1:'+str(self.server.server_port),'http://localhost:'+str(self.server.server_port)}
            if origin and origin not in allowed:
                self.send_json(403,{'error':'Cross-origin writes are not permitted'})
                return False
            if self.headers.get('Sec-Fetch-Site','').lower()=='cross-site':
                self.send_json(403,{'error':'Cross-site requests are not permitted'})
                return False
            if self.headers.get('X-Workbench-Request')!='same-origin':
                self.send_json(403,{'error':'Missing local write-request header'})
                return False
            if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
                self.send_json(415,{'error':'Content-Type must be application/json'})
                return False
        return True
    def send_blob(self,status,raw,mime='application/json; charset=utf-8',filename=None):
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' https://ills.bmwfans.info https://www.bimmerworld.com https://i.ebayimg.com https://www.rageitparts.com https://3a663eb0fef48c6d2d60-a88f8ebfcdb877ad223e888bfcb7f7ec.ssl.cf1.rackcdn.com data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if filename:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
        self.send_header('Content-Length',str(len(raw)));self.end_headers()
        try:self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError):pass
    def send_json(self,status,value):self.send_blob(status,encode(value))
    def get_params(self):return parse_qs(urlsplit(self.path).query)
    def one(self,p,key,default=''):return p.get(key,[default])[0]
    def get_db(self,readonly=True):return db_connect(self.server.catalog if readonly else self.server.jobs,readonly)
    def get_json(self):
        n=int(self.headers.get('Content-Length','0'))
        if n<1 or n>4500000:raise ValueError('Request must contain JSON smaller than 4.5 MB')
        return json.loads(self.rfile.read(n).decode('utf-8'))
    def do_GET(self):
        if not self.require_request_policy():return
        path=urlsplit(self.path).path
        try:
            if path=='/':return self.file('index.html','text/html; charset=utf-8')
            if path=='/site.js':return self.file('site.js','text/javascript; charset=utf-8')
            if path=='/site.css':return self.file('site.css','text/css; charset=utf-8')
            # Only explicitly allowed local 3D files; never expose arbitrary paths or workshop state.
            static_3d = {
                '/viewer3d.js':('viewer3d.js','text/javascript; charset=utf-8'),
                '/models/e30_reference_m3.glb':('models/e30_reference_m3.glb','model/gltf-binary'),
                '/vendor/three/build/three.module.js':('vendor/three/build/three.module.js','text/javascript; charset=utf-8'),
                '/vendor/three/examples/jsm/controls/OrbitControls.js':('vendor/three/examples/jsm/controls/OrbitControls.js','text/javascript; charset=utf-8'),
                '/vendor/three/examples/jsm/loaders/GLTFLoader.js':('vendor/three/examples/jsm/loaders/GLTFLoader.js','text/javascript; charset=utf-8'),
                '/vendor/three/examples/jsm/utils/BufferGeometryUtils.js':('vendor/three/examples/jsm/utils/BufferGeometryUtils.js','text/javascript; charset=utf-8'),
                '/vendor/meshopt_decoder.module.js':('vendor/meshopt_decoder.module.js','text/javascript; charset=utf-8'),
            }
            if path in static_3d:return self.file(*static_3d[path])
            if path=='/api/3d/status':
                required=[n for n,_mime in static_3d.values()]
                missing=[n for n in required if not (APP/n).is_file() or (APP/n).stat().st_size==0]
                return self.send_json(200,{'viewer':'Three.js GLB studio','ready':not missing,'missing':missing,
                  'model_installed':(APP/'models/e30_reference_m3.glb').is_file(),
                  'three_installed':(APP/'vendor/three/build/three.module.js').is_file(),
                  'reference_model':'BMW M3 E30 (not 325iX)', 'source_license':'CC BY 4.0',
                  'source_creator':'Martin Trafas (TinoD2)', 'safety_clearance':'NOT_APPROVED'})
            if path=='/api/vehicle':return self.send_json(200,VEHICLE)
            if path=='/api/restoration/domains':return self.restoration_domains()
            if path=='/api/visual/twin':return self.visual_twin()
            if path=='/api/missions':return self.missions()
            if path=='/api/twin':return self.twin()
            if path=='/api/twin/events':return self.twin_events()
            if path=='/api/twin/components':return self.twin_components()
            if path=='/api/twin/attachment':return self.twin_attachment()
            if path=='/api/expert/front-play':return self.expert_front_play()
            if path=='/api/expert/front-play/cases':return self.expert_cases()
            if path=='/api/sources':return self.send_json(200,self.sources())
            if path=='/api/groups':return self.groups()
            if path=='/api/search':return self.search()
            if path=='/api/assembly':return self.assembly()
            if path=='/api/part-dossier':return self.part_dossier()
            if path=='/api/evidence/coverage':return self.evidence_coverage()
            if path=='/api/catalog/coverage':return self.catalog_coverage()
            if path=='/api/catalog/worklist':return self.catalog_worklist()
            if path=='/api/catalog/entry':return self.catalog_entry()
            if path=='/api/part-photo':return self.part_photo()
            if path=='/api/jobs':return self.jobs()
            if path=='/api/diagram':return self.diagram()
            if path=='/api/diagnostic':return self.diagnostic()
            if path=='/api/manuals/status':return self.manual_status()
            if path=='/api/manuals/search':return self.manual_search()
            if path=='/api/manuals/conflicts':return self.manual_conflicts()
            if path=='/api/job/checks':return self.job_checks()
            if path=='/api/v4/status':return self.v4_status()
            if path=='/api/ai/status':return self.ai_status()
            if path=='/api/ai/route':return self.ai_route()
            if path=='/api/specialists':return self.specialists()
            if path=='/api/workflow/front-axle':return self.workflow_front_axle()
            if path=='/api/integration/health':return self.integration_health()
            m=re.fullmatch(r'/api/job/(\d+)/overview',path)
            if m:return self.job_overview(int(m[1]))
            m=re.fullmatch(r'/api/job/(\d+)/options',path)
            if m:return self.job_options(int(m[1]))
            m=re.fullmatch(r'/api/job/(\d+)\.md',path)
            if m:return self.export_job(int(m[1]))
            self.send_json(404,{'error':'Not found'})
        except (ValueError,KeyError,sqlite3.DatabaseError) as exc:self.send_json(400,{'error':str(exc)[:300]})
    def do_POST(self):
        if not self.require_request_policy(write=True):return
        path=urlsplit(self.path).path
        try:
            data=self.get_json()
            if path=='/api/jobs':return self.new_job(data)
            if path=='/api/missions/start':return self.start_mission(data)
            if path=='/api/twin/event':return self.new_twin_event(data)
            if path=='/api/twin/component':return self.new_component(data)
            if path=='/api/expert/front-play/start':return self.start_expert_case(data)
            if path=='/api/expert/front-play/step':return self.save_expert_step(data)
            if path=='/api/ai/ask':return self.ai_ask(data)
            if path=='/api/ai/route':return self.ai_route(data)
            if path=='/api/job/checks':return self.update_job_check(data)
            if path=='/api/part-photo':return self.upload_part_photo(data)
            match=re.fullmatch(r'/api/job/(\d+)/observation',path)
            if match:return self.new_observation(int(match[1]),data)
            match=re.fullmatch(r'/api/job/(\d+)/options',path)
            if match:return self.new_repair_option(int(match[1]),data)
            match=re.fullmatch(r'/api/twin/component/(\d+)/fact',path)
            if match:return self.new_component_fact(int(match[1]),data)
            match=re.fullmatch(r'/api/twin/component/(\d+)/attachment',path)
            if match:return self.new_component_attachment(int(match[1]),data)
            match=re.fullmatch(r'/api/job/(\d+)/specialist-finding',path)
            if match:return self.new_specialist_finding(int(match[1]),data)
            self.send_json(404,{'error':'Not found'})
        except (ValueError,KeyError,sqlite3.DatabaseError) as exc:self.send_json(400,{'error':str(exc)[:300]})
    def file(self,name,mime):
        f=APP/name
        if not f.is_file():return self.send_json(404,{'error':'Not found'})
        self.send_blob(200,f.read_bytes(),mime)
    def sources(self):return self.server.sources
    def mm_db(self):
        return getattr(self.server,'multimodal',None)
    def groups(self):
        if self.mm_db():
            with db_connect(self.mm_db(),True) as db:
                data=[dict(x) for x in db.execute('SELECT group_name,count(*) assemblies FROM assembly GROUP BY group_name ORDER BY group_name')]
            return self.send_json(200,data)
        with self.get_db() as db:
            data=[dict(x) for x in db.execute('SELECT group_name,count(*) assemblies FROM assembly GROUP BY group_name ORDER BY group_name')]
        return self.send_json(200,data)
    def search(self):
        p=self.get_params();q=trim(self.one(p,'q'),130);group=trim(self.one(p,'group'),70)
        if not q and not group:return self.send_json(200,{'results':[],'message':'Enter a part number, assembly name or technical keyword.'})
        if self.mm_db():
            with db_connect(self.mm_db(),True) as db:
                if not q and group:
                    data=[dict(x) for x in db.execute('''SELECT a.id,a.group_name,a.title AS slug,a.source_url,count(p.id) AS part_count
                        FROM assembly a LEFT JOIN part_record p ON p.assembly_id=a.id WHERE a.group_name=?
                        GROUP BY a.id ORDER BY a.title LIMIT 75''',(group,))]
                    return self.send_json(200,{'kind':'assemblies','results':data,'scope':'V4_MULTIMODAL_SQLITE; UNVERIFIED_FITMENT'})
                like='%'+escape_like(q)+'%'
                rows=db.execute('''SELECT p.id,p.assembly_id,p.part_number,p.callout AS callout_position,
                    p.description,p.quantity AS quantity_raw,p.date_raw AS date_condition_raw,p.supplement,
                    '' AS anchor,'' AS notes,a.title AS slug,a.group_name,a.source_url,
                    ia.id AS image_asset_id,ia.source_url AS figure_url
                    FROM part_record p JOIN assembly a ON a.id=p.assembly_id
                    LEFT JOIN part_figure_link pfl ON pfl.part_id=p.id
                    LEFT JOIN figure_occurrence fo ON fo.id=pfl.figure_id
                    LEFT JOIN image_asset ia ON ia.id=fo.image_asset_id
                    WHERE (p.part_number LIKE ? ESCAPE '\\' OR p.description LIKE ? ESCAPE '\\'
                    OR p.supplement LIKE ? ESCAPE '\\' OR a.title LIKE ? ESCAPE '\\'
                    OR a.group_name LIKE ? ESCAPE '\\') AND (?='' OR a.group_name=?)
                    ORDER BY CASE WHEN p.part_number=? THEN 0 WHEN a.title LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END,
                    a.group_name,a.title,p.callout LIMIT 80''',
                    (like,like,like,like,like,group,group,q,like)).fetchall()
            return self.send_json(200,{'kind':'parts','results':[dict(x) for x in rows],
                'scope':'V4_MULTIMODAL_SQLITE; exact catalog identity, variant and installed fitment remain separate'})
        if not q and group:
            with self.get_db() as db:
                data=[dict(x) for x in db.execute('''SELECT a.id,a.group_name,a.slug,a.source_url,count(p.id) AS part_count
                     FROM assembly a LEFT JOIN part_row p ON p.assembly_id=a.id
                     WHERE a.group_name=? GROUP BY a.id ORDER BY a.slug LIMIT 75''',(group,))]
            return self.send_json(200,{'kind':'assemblies','results':data,'scope':'SECONDARY_ETK_CATALOG; UNVERIFIED_FITMENT'})
        like='%'+escape_like(q)+'%'
        with self.get_db() as db:
            rows=db.execute('''SELECT p.id,p.assembly_id,p.part_number,p.callout_position,p.description,p.quantity_raw,
                        p.date_condition_raw,p.supplement,p.anchor,p.notes,a.slug,a.group_name,a.source_url,
                        f.image_asset_id,f.figure_url
                        FROM part_row p JOIN assembly a ON a.id=p.assembly_id
                        LEFT JOIN figure f ON f.assembly_id=a.id
                        WHERE (p.part_number LIKE ? ESCAPE '\\' OR p.description LIKE ? ESCAPE '\\'
                        OR p.supplement LIKE ? ESCAPE '\\' OR a.slug LIKE ? ESCAPE '\\'
                        OR a.group_name LIKE ? ESCAPE '\\') AND (?='' OR a.group_name=?)
                        ORDER BY CASE WHEN p.part_number=? THEN 0 WHEN a.slug LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END,
                        a.group_name,a.slug,p.callout_position LIMIT 80''',
                        (like,like,like,like,like,group,group,q,like)).fetchall()
        return self.send_json(200,{'kind':'parts','results':[dict(x) for x in rows],
            'scope':'Secondary ETK-derived all-variants catalog; dates/options not individually validated'})
    def assembly(self):
        p=self.get_params();id=trim(self.one(p,'id'),35)
        if self.mm_db():
            with db_connect(self.mm_db(),True) as db:
                a=db.execute('SELECT * FROM assembly WHERE id=?',(id,)).fetchone()
                if not a:return self.send_json(404,{'error':'Assembly not found'})
                f=[dict(x) for x in db.execute('''SELECT fo.id,fo.image_asset_id,fo.source_url AS figure_url,
                    ia.local_file,ia.status FROM figure_occurrence fo JOIN image_asset ia ON ia.id=fo.image_asset_id
                    WHERE fo.assembly_id=?''',(id,))]
                parts=[dict(x) for x in db.execute('''SELECT p.id,p.assembly_id,p.part_number,p.callout AS callout_position,
                    p.description,p.quantity AS quantity_raw,p.date_raw AS date_condition_raw,p.supplement,
                    '' AS anchor,'' AS notes FROM part_record p WHERE p.assembly_id=? ORDER BY CAST(p.callout AS INTEGER),p.description''',(id,))]
            for figure in f:
                asset=self.server.assets.get(figure.get('image_asset_id'),{})
                root=self.server.v4root
                figure['local_available']=bool(root and asset.get('local_file') and (root/asset['local_file']).is_file())
            ad=dict(a);ad['slug']=ad.get('title');ad['downloaded_at']=ad.get('source_status')
            return self.send_json(200,{'assembly':ad,'figures':f,'parts':parts,'scope':'V3/V4 catalog identity only; exact installed fitment and callout pixels require verification'})
        with self.get_db() as db:
            a=db.execute('SELECT * FROM assembly WHERE id=?',(id,)).fetchone()
            if not a:return self.send_json(404,{'error':'Assembly not found'})
            f=[dict(r) for r in db.execute('SELECT * FROM figure WHERE assembly_id=?',(id,))]
            parts=[dict(r) for r in db.execute('SELECT * FROM part_row WHERE assembly_id=? ORDER BY CAST(callout_position AS INTEGER),description',(id,))]
        for figure in f:
            asset=self.server.assets.get(figure.get('image_asset_id'),{})
            root=self.server.v4root
            figure['local_available']=bool(root and asset.get('local_file') and (root/asset['local_file']).is_file())
        return self.send_json(200,{'assembly':dict(a),'figures':f,'parts':parts,'scope':'Identity/fitment requires inspection; exact callout pixel coordinates unavailable'})
    def part_dossier(self):
        pid=trim(self.one(self.get_params(),'id'),45)
        if self.mm_db():
            with db_connect(self.mm_db(),True) as db:
                row=db.execute('''SELECT p.*,a.group_name,a.title AS slug,a.source_url,a.source_status AS downloaded_at
                    FROM part_record p JOIN assembly a ON a.id=p.assembly_id WHERE p.id=?''',(pid,)).fetchone()
                if row is None:return self.send_json(404,{'error':'Part row not found'})
                part=dict(row)
                part.update({'callout_position':part.pop('callout'),'quantity_raw':part.pop('quantity'),
                             'date_condition_raw':part.pop('date_raw'),'anchor':'','notes':''})
                figs=[dict(x) for x in db.execute('''SELECT fo.source_url AS figure_url,fo.image_asset_id,ia.local_file,ia.status
                    FROM figure_occurrence fo JOIN image_asset ia ON ia.id=fo.image_asset_id WHERE fo.assembly_id=?''',(part['assembly_id'],))]
                siblings=[dict(x) for x in db.execute('''SELECT p.id,p.part_number,p.callout AS callout_position,p.description
                    FROM part_record p WHERE p.assembly_id=? AND p.id<>? ORDER BY CAST(p.callout AS INTEGER) LIMIT 25''',(part['assembly_id'],pid))]
            return self._part_dossier_response(part,figs,siblings)
        with self.get_db() as db:
            row=db.execute("""SELECT p.*,a.group_name,a.slug,a.source_url,a.downloaded_at
                        FROM part_row p JOIN assembly a ON a.id=p.assembly_id WHERE p.id=?""",(pid,)).fetchone()
            if row is None:return self.send_json(404,{'error':'Part row not found'})
            part=dict(row)
            figs=[dict(x) for x in db.execute('SELECT figure_url,image_asset_id FROM figure WHERE assembly_id=?',(part['assembly_id'],))]
            siblings=[dict(x) for x in db.execute('SELECT p.id,p.part_number,p.callout_position,p.description FROM part_row p WHERE assembly_id=? AND p.id<>? ORDER BY CAST(p.callout_position AS INTEGER) LIMIT 25',(part['assembly_id'],pid))]
        return self._part_dossier_response(part,figs,siblings)

    def _part_dossier_response(self,part,figs,siblings):
        number=str(part.get('part_number') or '').strip()
        photos=[]
        with db_connect(self.server.photos,False) as db:
            for row in db.execute('SELECT id,part_number,kind,source_label,source_url,original_filename,created_utc FROM part_photo WHERE part_number=? ORDER BY id DESC',(number,)):
                item=dict(row);item['image_url']='/api/part-photo?id='+str(item['id']);photos.append(item)
        curated=self.server.curated.get(number)
        enriched={
          'label':curated.get('label') if curated else None,
          'orientation':curated.get('orientation') if curated else None,
          'reviewed_utc':curated.get('reviewed_utc') if curated else None,
          'evidence_status':curated.get('evidence_status') if curated else 'NOT_RESEARCHED',
          'sources':curated.get('sources',[]) if curated else [],
          'conflicts':curated.get('conflicts',[]) if curated else [],
          'inspection_questions':curated.get('inspection_questions',[]) if curated else [],
          'supplier_photo_refs':curated.get('photos',[]) if curated else [],
        }
        return self.send_json(200,{
          'part':part,'curated':enriched,'figures':figs,'photos':photos,'sibling_parts':siblings,
          'technical_fields':[
             {'name':'BMW part number','value':number or None,'status':'CATALOG_TRANSCRIBED'},
             {'name':'Diagram callout','value':part.get('callout_position'),'status':'TABLE_REFERENCE_ONLY'},
             {'name':'Quantity / assembly','value':part.get('quantity_raw'),'status':'CATALOG_TRANSCRIBED'},
             {'name':'Supplement / variant','value':part.get('supplement'),'status':'CATALOG_TRANSCRIBED'},
             {'name':'Listed date condition','value':part.get('date_condition_raw'),'status':'RAW_TEXT; NOT VIN VERIFIED'},
             {'name':'Catalog notes','value':part.get('notes'),'status':'RAW_TEXT; VERIFY'},
             {'name':'Exact dimensions / tolerances','value':None,'status':'NOT VERIFIED'},
             {'name':'Material / grade','value':None,'status':'NOT VERIFIED'},
             {'name':'Tightening torque / procedure','value':None,'status':'NOT VERIFIED'},
             {'name':'Supersession / replacement','value':None,'status':'NOT VERIFIED'},
             {'name':'Supplier price / availability','value':None,'status':'NOT VERIFIED'},
             {'name':'Fitment for VIN / installed component','value':None,'status':'REQUIRES VERIFICATION'}],
           'researched_fields':curated.get('facts',[]) if curated else [],
           'catalog_research':self.server.research.get(number,{}),
           'evidence_policy':'OEM part number and callout are transcribed from a secondary all-variants catalog. Do not infer BMW manufacturer approval, dimensional interchange, installation torque or VIN-specific fitment.',
           'photo_policy':'Only owner-added local photographs with provenance are displayed. No generic web image is misrepresented as this part.'})
    def catalog_coverage(self):
        stats=dict(self.server.research_stats)
        stats['researched_exact_number_records']=len(self.server.source_reviewed)
        stats['supplier_photo_references']=sum(1 for k in self.server.source_reviewed
            for p in self.server.curated[k].get('photos',[])
            if isinstance(p,dict) and p.get('kind')!='ALTERNATIVE_REFERENCE')
        stats['coverage_basis']='ACTIVE_SOURCE_REVIEWED_OVERLAY; supplier references are not engineering verification'
        stats['status']='DYNAMIC_FROM_CURATED_EVIDENCE'
        return self.send_json(200,stats)
    def catalog_entry(self):
        part=trim(self.one(self.get_params(),'part'),20)
        rec=self.server.research.get(part)
        if not rec:return self.send_json(404,{'error':'Part number not found'})
        return self.send_json(200,{'part_number':part,'record':self.research_record(part,rec)})
    def research_record(self,number,record):
        item=dict(record)
        if number in self.server.source_reviewed:item['evidence_status']='SOURCE_REVIEWED'
        else:item['evidence_status']='NOT_RESEARCHED'
        return item
    def catalog_worklist(self):
        p=self.get_params()
        try:batch=int(self.one(p,'batch','1'))
        except ValueError:return self.send_json(400,{'error':'Batch must be numeric'})
        if batch<1 or batch>self.server.research_stats.get('batches',0):
            return self.send_json(400,{'error':'Batch outside configured range'})
        batch_size=self.server.research_stats.get('batch_size',50)
        start=(batch-1)*batch_size
        partlist=self.server.research_order[start:start+batch_size]
        return self.send_json(200,{'batch':batch,'start_index':start+1,
          'parts':[{'part_number':k,**self.research_record(k,self.server.research[k])} for k in partlist],
          'not_researched_count':sum(k not in self.server.source_reviewed for k in partlist)})
    def evidence_coverage(self):
        n=len(self.server.source_reviewed)
        return self.send_json(200,{'researched_exact_part_numbers':n,
          'physical_photo_reference_count':sum(1 for k in self.server.source_reviewed for p in self.server.curated[k].get('photos',[]) if p.get('kind')!='ALTERNATIVE_REFERENCE'),
          'alternative_photo_reference_count':sum(1 for k in self.server.source_reviewed for p in self.server.curated[k].get('photos',[]) if p.get('kind')=='ALTERNATIVE_REFERENCE'),
          'catalog_distinct_part_numbers':len(self.server.research),
          'policy':'External product images are source-attributed links, not photos of the installed vehicle, OEM certification, or offline assets.',
          'coverage_basis':'ACTIVE_SOURCE_REVIEWED_OVERLAY; no claim of BMW-authorized or fitment-certified data'})
    def part_photo(self):
        raw_id=trim(self.one(self.get_params(),'id'),20)
        if not raw_id.isdecimal():return self.send_json(400,{'error':'Invalid photo id'})
        with db_connect(self.server.photos,False) as db:
            x=db.execute('SELECT image_path,mime FROM part_photo WHERE id=?',(int(raw_id),)).fetchone()
        if not x:return self.send_json(404,{'error':'Photo not found'})
        root=self.server.photo_root.resolve();file=(root/x['image_path']).resolve()
        if root not in file.parents or not file.is_file():return self.send_json(404,{'error':'Photo missing from local photo storage'})
        if file.stat().st_size>3000000:return self.send_json(403,{'error':'Photo too large'})
        self.send_blob(200,file.read_bytes(),x['mime'])
    def upload_part_photo(self,d):
        number=trim(d.get('part_number'),30)
        label=trim(d.get('source_label'),200)
        kind=trim(d.get('kind'),30)
        url=trim(d.get('source_url'),800)
        if not number or not label:return self.send_json(400,{'error':'Part number and provenance/source label required'})
        if not re.fullmatch(r'[0-9A-Za-z-]{5,30}',number):return self.send_json(400,{'error':'Invalid part number'})
        if kind not in ('WORKSHOP_ACTUAL_PART','SUPPLIER_PHOTO','OTHER_DOCUMENTED'):
            return self.send_json(400,{'error':'Invalid photo type'})
        if url and not url.startswith('https://'):return self.send_json(400,{'error':'Use an HTTPS source URL'})
        try: binary=base64.b64decode(str(d.get('image_base64','')),validate=True)
        except (ValueError,binascii.Error):return self.send_json(400,{'error':'Invalid image data'})
        if not 100<len(binary)<=2800000:return self.send_json(400,{'error':'Image size must be 100 bytes to 2.8 MB'})
        if binary.startswith(b'\xff\xd8\xff'):ext='jpg';mime='image/jpeg'
        elif binary.startswith(b'\x89PNG\r\n\x1a\n'):ext='png';mime='image/png'
        elif binary[:4]==b'RIFF' and binary[8:12]==b'WEBP':ext='webp';mime='image/webp'
        else:return self.send_json(400,{'error':'Only genuine JPG/PNG/WebP image files are accepted'})
        if self.mm_db():
            with db_connect(self.mm_db(),True) as db:
                count=db.execute('SELECT count(*) FROM part_record WHERE part_number=?',(number,)).fetchone()[0]
        else:
            with self.get_db() as db:
                count=db.execute('SELECT count(*) FROM part_row WHERE part_number=?',(number,)).fetchone()[0]
        if count<1:return self.send_json(400,{'error':'Part number not found in local catalog'})
        sha=hashlib.sha256(binary).hexdigest()
        self.server.photo_root.mkdir(parents=True,exist_ok=True)
        sub=self.server.photo_root/number;sub.mkdir(parents=True,exist_ok=True)
        filename=sha+'.'+ext
        destination=sub/filename
        if not destination.exists():
            temp=sub/(filename+'.tmp')
            temp.write_bytes(binary);os.replace(temp,destination)
        with db_connect(self.server.photos,False) as db:
            cur=db.execute('INSERT INTO part_photo(part_number,kind,source_label,source_url,original_filename,image_path,mime,sha256,created_utc) VALUES(?,?,?,?,?,?,?,?,?)',(number,kind,label,url,trim(d.get('filename'),200),number+'/'+filename,mime,sha,now()))
            db.commit();new_id=cur.lastrowid
        return self.send_json(201,{'photo_id':new_id,'part_number':number,'stored':'LOCAL; USER_PROVIDED; SOURCE_UNVERIFIED'})
    def restoration_domains(self):
        source=self.mm_db() or self.server.catalog
        with db_connect(source,True) as db:
            if self.mm_db():rows={x['group_name']:x['assemblies'] for x in db.execute('SELECT group_name,count(*) assemblies FROM assembly GROUP BY group_name')}
            else:rows={x['group_name']:x['assemblies'] for x in db.execute('SELECT group_name,count(*) assemblies FROM assembly GROUP BY group_name')}
        with self.get_db(False) as db:
            mission_counts={x['domain_id']:x['n'] for x in db.execute('SELECT domain_id,count(*) n FROM restoration_mission GROUP BY domain_id')}
        domains=[]
        for domain_id,domain in RESTORATION_DOMAINS.items():
            groups=[{'group_name':g,'assemblies':int(rows.get(g,0))} for g in domain['groups']]
            domains.append({'id':domain_id,**domain,'groups':groups,'assembly_count':sum(x['assemblies'] for x in groups),'mission_count':int(mission_counts.get(domain_id,0))})
        deferred=[{'group_name':g,'assemblies':int(rows.get(g,0))} for g in sorted(DEFERRED_CATALOG_GROUPS)]
        return self.send_json(200,{'domains':domains,'deferred':deferred,'scope':'ALL_PRIORITY_IX_MECHANICAL_ELECTRICAL_SYSTEMS','policy':'Body, trim, seats and accessories remain searchable but are deferred from the default restoration journey.'})
    def visual_twin(self):
        """Return a small, stable view model for the interactive orientation twin.

        The SVG scene is intentionally not a CAD model. It is a navigational map
        over the authoritative catalog and mission domains; geometry and fitment
        remain evidence questions in the linked assembly/part views.
        """
        source=self.mm_db() or self.server.catalog
        with db_connect(source,True) as db:
            counts={x['group_name']:int(x['assemblies']) for x in db.execute('SELECT group_name,count(*) assemblies FROM assembly GROUP BY group_name')}
            reps={}
            for group in DOMAIN_BY_GROUP:
                if self.mm_db():
                    row=db.execute('SELECT id,title AS slug,source_url FROM assembly WHERE group_name=? ORDER BY title LIMIT 1',(group,)).fetchone()
                else:
                    row=db.execute('SELECT id,slug,source_url FROM assembly WHERE group_name=? ORDER BY slug LIMIT 1',(group,)).fetchone()
                if row: reps[group]=dict(row)
        with self.get_db(False) as db:
            mission_counts={x['system']:int(x['n']) for x in db.execute('SELECT system,count(*) n FROM job GROUP BY system')}
        systems=[]
        for domain_id,domain in RESTORATION_DOMAINS.items():
            for group in domain['groups']:
                representative=reps.get(group)
                systems.append({'id':group,'domain_id':domain_id,'domain_label':domain['label'],
                    'label':group.replace('_',' ').title(),'priority':domain['priority'],
                    'assembly_count':counts.get(group,0),'mission_count':mission_counts.get(group,0),
                    'representative_assembly':representative,
                    'visual_state':'REFERENCE_3D_ORIENTATION','fallback':'2D_DIAGRAM_CALLOUTS' if representative else 'CATALOG_SEARCH'})
        return self.send_json(200,{'vehicle':VEHICLE,'systems':systems,
            'scope':'PRIORITY_IX_MECHANICAL_ELECTRICAL_SYSTEMS',
            'policy':'The 3D scene is a non-dimensional orientation aid. Use the linked 2D diagram, catalog row, inspection and source evidence for identity, geometry and fitment.'})
    def missions(self):
        with self.get_db(False) as db:
            rows=[dict(x) for x in db.execute('''SELECT m.job_id,m.domain_id,m.title,m.mission_status,m.current_stage,m.created_utc,m.updated_utc,
                j.system,j.symptom,j.status AS job_status,j.risk,j.clearance
                FROM restoration_mission m JOIN job j ON j.id=m.job_id ORDER BY m.updated_utc DESC,m.job_id DESC''')]
            for row in rows:row['progress']=derive_mission_progress(db,row['job_id'])
        for row in rows:
            domain=RESTORATION_DOMAINS.get(row['domain_id'],{});row['domain_label']=domain.get('label',row['domain_id']);row['priority']=domain.get('priority','P2');row['current_stage']=row['progress']['current_stage']
        return self.send_json(200,{'missions':rows,'clearance':'NOT_APPROVED'})
    def start_mission(self,d):
        domain_id=trim(d.get('domain_id'),60);system=trim(d.get('system'),100);symptom=trim(d.get('symptom'),1500);context=trim(d.get('context'),1800);title=trim(d.get('title'),180)
        domain=RESTORATION_DOMAINS.get(domain_id)
        if not domain:raise ValueError('Unknown restoration domain')
        if system not in domain['groups']:raise ValueError('Selected catalog system does not belong to this restoration domain')
        if system not in self.server.groups:raise ValueError('Selected catalog system is unavailable')
        if len(symptom)<4:raise ValueError('Describe the mission symptom or restoration objective')
        risk='SAFETY_CRITICAL_REVIEW_REQUIRED' if system in CRITICAL_GROUPS else 'REVIEW_REQUIRED'
        title=title or domain['label']+' — '+symptom[:90]
        with self.get_db(False) as db:
            cur=db.execute('INSERT INTO job(created_utc,system,assembly_id,symptom,context,risk) VALUES(?,?,?,?,?,?)',(now(),system,None,symptom,context,risk));job_id=cur.lastrowid
            for code,label in CHECK_TEMPLATES.get(system,DEFAULT_CHECKS):db.execute('INSERT INTO diagnostic_check(job_id,code,label,updated_utc) VALUES(?,?,?,?)',(job_id,code,label,now()))
            db.execute('INSERT INTO restoration_mission(job_id,domain_id,title,created_utc,updated_utc) VALUES(?,?,?,?,?)',(job_id,domain_id,title,now(),now()))
            insert_twin_event(db,'CASE_CREATED','case',job_id,{'domain_id':domain_id,'system':system,'title':title,'symptom':symptom,'status':'ACTIVE'},'Restoration Garage mission intake')
            db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),));db.commit()
        return self.send_json(201,{'job_id':job_id,'mission':{'domain_id':domain_id,'domain_label':domain['label'],'title':title,'system':system,'status':'ACTIVE'},'risk':risk,'clearance':'NOT_APPROVED','prompts':GROUP_PROMPTS.get(system,DEFAULT_PROMPTS)})
    def jobs(self):
        with self.get_db(False) as db:
            rows=[dict(x) for x in db.execute('SELECT * FROM job ORDER BY id DESC LIMIT 100')]
        return self.send_json(200,rows)
    def job_overview(self,id):
        with self.get_db(False) as db:
            job=db.execute('SELECT * FROM job WHERE id=?',(id,)).fetchone()
            if not job:return self.send_json(404,{'error':'Job not found'})
            mission=db.execute('SELECT * FROM restoration_mission WHERE job_id=?',(id,)).fetchone()
            checks=[dict(x) for x in db.execute('SELECT * FROM diagnostic_check WHERE job_id=? ORDER BY id',(id,))]
            observations=[dict(x) for x in db.execute('SELECT * FROM observation WHERE job_id=? ORDER BY id',(id,))]
            options=[dict(x) for x in db.execute('''SELECT * FROM repair_option WHERE job_id=?
                ORDER BY CASE path WHEN 'REPAIR_EXISTING' THEN 1 WHEN 'USED_OEM_REFURBISHED' THEN 2
                WHEN 'SPEC_VERIFIED_CROSS_FIT' THEN 3 WHEN 'NEW_REPLACEMENT' THEN 4 ELSE 9 END,id''',(id,))]
            expert=db.execute('SELECT e.job_id,e.workflow_id,e.side,e.created_utc,j.symptom,j.risk,j.clearance FROM expert_case e JOIN job j ON e.job_id=j.id WHERE e.job_id=?',(id,)).fetchone()
            steps=[dict(x) for x in db.execute('SELECT * FROM expert_step WHERE job_id=? ORDER BY rowid',(id,))] if expert else []
            findings=[dict(x) for x in db.execute('SELECT * FROM specialist_finding WHERE job_id=? ORDER BY id DESC',(id,))]
            events=[dict(x) for x in db.execute('''SELECT id,created_utc,event_type,entity_type,entity_id,payload_json,source,xp_value
                FROM twin_event WHERE entity_id=? AND entity_type IN ('case','job') ORDER BY id DESC''',(str(id),))]
            progress=derive_mission_progress(db,id)
        for event in events:event['payload']=json.loads(event.pop('payload_json'))
        for finding in findings:
            finding['evidence']=json.loads(finding.pop('evidence_json'));finding['tests']=json.loads(finding.pop('tests_json'))
        evidence_count=len(observations)+len(options)+len(findings)+sum(1 for x in checks if x['status']!='NOT_CHECKED')+sum(1 for x in steps if x['status']!='NOT_CHECKED')
        blockers=[]
        if not observations:blockers.append('No case observations or measurements recorded')
        if not options:blockers.append('No repair or sourcing comparison recorded')
        if any(x['status']=='NEEDS_SPECIALIST' for x in checks+steps):blockers.append('Specialist review remains required')
        blockers.append('Qualified physical sign-off required; software clearance is never granted')
        return self.send_json(200,{'job':dict(job),'mission':dict(mission) if mission else None,'mission_progress':progress,'checks':checks,'observations':observations,'options':options,'specialist_findings':findings,
            'expert_case':dict(expert) if expert else None,'expert_steps':steps,'twin_events':events,
            'readiness':{'evidence_count':evidence_count,'blockers':blockers,'clearance':'NOT_APPROVED'},
            'policy':'One case overview joins operational evidence, repair choices and vehicle-twin history without changing the safety gate.'})
    def new_specialist_finding(self,id,d):
        agent=trim(d.get('agent_id'),60);intent=trim(d.get('intent'),80);finding=trim(d.get('finding'),2400);uncertainty=trim(d.get('uncertainty'),1200);source=trim(d.get('source'),500)
        evidence=d.get('evidence');tests=d.get('tests');status=trim(d.get('status') or 'NEEDS_EVIDENCE',40).upper()
        if not agent or not intent or not finding or not uncertainty or not source:raise ValueError('Specialist finding requires agent, intent, finding, uncertainty and source')
        if not isinstance(evidence,list) or not evidence:raise ValueError('Specialist finding requires an evidence list')
        if not isinstance(tests,list) or not tests:raise ValueError('Specialist finding requires discriminating tests')
        if status not in {'PROPOSED','NEEDS_EVIDENCE','REQUIRES_HUMAN_REVIEW'}:raise ValueError('Invalid specialist finding status')
        with self.get_db(False) as db:
            if not db.execute('SELECT 1 FROM job WHERE id=?',(id,)).fetchone():return self.send_json(404,{'error':'Job not found'})
            cur=db.execute('''INSERT INTO specialist_finding(job_id,created_utc,agent_id,intent,finding,evidence_json,uncertainty,tests_json,status,source)
                VALUES(?,?,?,?,?,?,?,?,?,?)''',(id,now(),agent,intent,finding,json.dumps(evidence,ensure_ascii=False),uncertainty,json.dumps(tests,ensure_ascii=False),status,source));finding_id=cur.lastrowid
            insert_twin_event(db,'OBSERVATION_RECORDED','case',id,{'specialist_finding_id':finding_id,'agent_id':agent,'intent':intent,'status':status,'uncertainty':uncertainty},source)
            sync_mission_progress(db,id);db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),));db.commit()
        return self.send_json(201,{'finding_id':finding_id,'job_id':id,'status':status,'clearance':'NOT_APPROVED'})
    def twin(self):
        with self.get_db(False) as db:
            twin=db.execute('SELECT * FROM vehicle_twin WHERE id=1').fetchone()
            events=[dict(x) for x in db.execute('SELECT id,created_utc,event_type,entity_type,entity_id,payload_json,source,xp_value FROM twin_event ORDER BY id DESC LIMIT 100')]
        if not twin:return self.send_json(503,{'error':'Vehicle twin is not initialized'})
        data=dict(twin)
        for key in ('factory_state_json','as_installed_state_json','confidence_json'):
            data[key[:-5] if key.endswith('_json') else key]=json.loads(data.pop(key))
        for event in events:
            event['payload']=json.loads(event.pop('payload_json'))
        xp=sum(int(x.get('xp_value',0)) for x in events)
        return self.send_json(200,{'vehicle':VEHICLE,'twin':data,'events':events,
            'gamification':{'xp':xp,'level':1+xp//100,'next_level_xp':((xp//100)+1)*100,
                'policy':'Progress rewards documented evidence, measurements and QA only; never speed, risk or software safety approval.'}})
    def twin_events(self):
        with self.get_db(False) as db:
            events=[dict(x) for x in db.execute('SELECT id,created_utc,event_type,entity_type,entity_id,payload_json,source,xp_value FROM twin_event ORDER BY id DESC LIMIT 100')]
        for event in events:
            event['payload']=json.loads(event.pop('payload_json'))
        return self.send_json(200,{'events':events})
    def twin_components(self):
        with self.get_db(False) as db:
            components=[dict(x) for x in db.execute('SELECT * FROM component_instance ORDER BY id DESC')]
            facts=[dict(x) for x in db.execute('SELECT * FROM component_fact ORDER BY id DESC')]
            attachments=[dict(x) for x in db.execute('SELECT id,component_id,created_utc,kind,title,source,source_url,rights,variant_scope,mime,sha256,notes FROM component_attachment ORDER BY id DESC')]
        by_id={x['id']:[] for x in components}
        for fact in facts:by_id.setdefault(fact['component_id'],[]).append(fact)
        media_by_id={x['id']:[] for x in components}
        for attachment in attachments:
            attachment['media_url']='/api/twin/attachment?id='+str(attachment['id']) if attachment['mime'].startswith('image/') else ''
            media_by_id.setdefault(attachment['component_id'],[]).append(attachment)
        for component in components:
            component['facts']=by_id.get(component['id'],[]);component['attachments']=media_by_id.get(component['id'],[])
        uncertainty={'unknown':0,'owner_reported':0,'source_verified':0,'mechanic_verified':0,'conflicting':0}
        for fact in facts:uncertainty[fact['confidence'].lower()]=uncertainty.get(fact['confidence'].lower(),0)+1
        return self.send_json(200,{'components':components,'uncertainty':uncertainty,
            'policy':'Component identity, installed condition and fitment remain separate facts. Conflicts are retained, not overwritten.'})
    def twin_attachment(self):
        raw=trim(self.one(self.get_params(),'id'),20)
        if not raw.isdecimal():return self.send_json(400,{'error':'Invalid attachment id'})
        with self.get_db(False) as db:x=db.execute('SELECT media_path,mime,sha256 FROM component_attachment WHERE id=?',(int(raw),)).fetchone()
        if not x:return self.send_json(404,{'error':'Attachment not found'})
        if not x['mime'].startswith('image/') or not x['media_path']:return self.send_json(404,{'error':'Attachment is a reference, not a local image'})
        root=self.server.photo_root.resolve();file=(root/x['media_path']).resolve()
        if root not in file.parents or not file.is_file():return self.send_json(404,{'error':'Attachment file missing'})
        if hashlib.sha256(file.read_bytes()).hexdigest()!=x['sha256']:return self.send_json(409,{'error':'Attachment hash mismatch'})
        return self.send_blob(200,file.read_bytes(),x['mime'])
    def new_component(self,d):
        component_type=trim(d.get('component_type'),120);location=trim(d.get('location'),120);side=trim(d.get('side'),20).upper()
        if len(component_type)<2:raise ValueError('Component type is required')
        if side not in {'','LEFT','RIGHT','BOTH','UNKNOWN'}:raise ValueError('Invalid component side')
        with self.get_db(False) as db:
            cur=db.execute('''INSERT INTO component_instance(created_utc,updated_utc,component_type,location,side,oem_part_number,marking,condition,status)
                VALUES(?,?,?,?,?,?,?,?,?)''',(now(),now(),component_type,location,side,trim(d.get('oem_part_number'),80),trim(d.get('marking'),160),trim(d.get('condition'),500),'IDENTITY_UNCONFIRMED'))
            component_id=cur.lastrowid
            insert_twin_event(db,'COMPONENT_IDENTIFIED','component',component_id,{'component_type':component_type,'location':location,'side':side,'oem_part_number':trim(d.get('oem_part_number'),80),'marking':trim(d.get('marking'),160)},trim(d.get('source') or 'Workbench component intake',400))
            db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),));db.commit()
        return self.send_json(201,{'component_id':component_id,'status':'IDENTITY_UNCONFIRMED','safety_clearance':'NOT_APPROVED'})
    def new_component_fact(self,id,d):
        layer=trim(d.get('layer'),40).upper();field=trim(d.get('field'),80);value=trim(d.get('value'),1200);confidence=trim(d.get('confidence'),40).upper();source=trim(d.get('source'),500)
        if layer not in {'FACTORY_CATALOG','OWNER_REPORTED','SOURCE_VERIFIED','MECHANIC_VERIFIED','AS_BUILT'}:raise ValueError('Invalid component fact layer')
        if confidence not in {'UNKNOWN','OWNER_REPORTED','SOURCE_VERIFIED','MECHANIC_VERIFIED','CONFLICTING'}:raise ValueError('Invalid confidence state')
        if not field or not value or not source:raise ValueError('Component fact requires field, value and source')
        with self.get_db(False) as db:
            if not db.execute('SELECT 1 FROM component_instance WHERE id=?',(id,)).fetchone():return self.send_json(404,{'error':'Component not found'})
            db.execute('INSERT INTO component_fact(component_id,created_utc,layer,field,value,confidence,source) VALUES(?,?,?,?,?,?,?)',(id,now(),layer,field,value,confidence,source))
            db.execute('UPDATE component_instance SET updated_utc=?,status=? WHERE id=?',(now(),'FACT_RECORDED',id))
            insert_twin_event(db,'DEVIATION_RECORDED' if layer=='AS_BUILT' else 'OBSERVATION_RECORDED','component',id,{'layer':layer,'field':field,'value':value,'confidence':confidence},source)
            db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),));db.commit()
        return self.send_json(201,{'component_id':id,'saved':True,'confidence':confidence,'safety_clearance':'NOT_APPROVED'})
    def new_component_attachment(self,id,d):
        kind=trim(d.get('kind'),40).upper();title=trim(d.get('title'),160);source=trim(d.get('source'),500);url=trim(d.get('source_url'),800)
        rights=trim(d.get('rights') or 'OWNER_SUPPLIED_OR_REVIEW_REQUIRED',120);variant=trim(d.get('variant_scope'),300);notes=trim(d.get('notes'),1000)
        if kind not in {'PHOTO','SOURCE_REFERENCE','MEASUREMENT_REFERENCE'}:raise ValueError('Invalid attachment kind')
        if not title or not source:raise ValueError('Attachment title and source are required')
        if url and not url.startswith('https://'):raise ValueError('Use an HTTPS source URL')
        media_path='';mime='';sha='';binary=b''
        encoded=str(d.get('image_base64') or '')
        if kind=='PHOTO':
            try:binary=base64.b64decode(encoded,validate=True)
            except (ValueError,binascii.Error):raise ValueError('Photo attachment requires valid base64 image data')
            if not 100<len(binary)<=2800000:raise ValueError('Photo attachment must be 100 bytes to 2.8 MB')
            if binary.startswith(b'\xff\xd8\xff'):ext='jpg';mime='image/jpeg'
            elif binary.startswith(b'\x89PNG\r\n\x1a\n'):ext='png';mime='image/png'
            elif binary[:4]==b'RIFF' and binary[8:12]==b'WEBP':ext='webp';mime='image/webp'
            else:raise ValueError('Only genuine JPG/PNG/WebP photo attachments are accepted')
            sha=hashlib.sha256(binary).hexdigest();sub=self.server.photo_root/'_components'/str(id);sub.mkdir(parents=True,exist_ok=True)
            filename=sha+'.'+ext;destination=sub/filename
            if not destination.exists():
                temp=sub/(filename+'.tmp');temp.write_bytes(binary);os.replace(temp,destination)
            media_path='_components/'+str(id)+'/'+filename
        elif not url:raise ValueError('Non-photo attachments require an HTTPS source URL')
        with self.get_db(False) as db:
            if not db.execute('SELECT 1 FROM component_instance WHERE id=?',(id,)).fetchone():return self.send_json(404,{'error':'Component not found'})
            cur=db.execute('''INSERT INTO component_attachment(component_id,created_utc,kind,title,source,source_url,rights,variant_scope,media_path,mime,sha256,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(id,now(),kind,title,source,url,rights,variant,media_path,mime,sha,notes));attachment_id=cur.lastrowid
            insert_twin_event(db,'PHOTO_CAPTURED' if kind=='PHOTO' else 'OBSERVATION_RECORDED','component',id,{'attachment_id':attachment_id,'kind':kind,'title':title,'variant_scope':variant,'sha256':sha},source)
            db.execute('UPDATE component_instance SET updated_utc=?,status=? WHERE id=?',(now(),'EVIDENCE_ATTACHED',id));db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),));db.commit()
        return self.send_json(201,{'attachment_id':attachment_id,'component_id':id,'kind':kind,'sha256':sha,'safety_clearance':'NOT_APPROVED'})
    def new_twin_event(self,d):
        event_type=trim(d.get('event_type'),40).upper();entity_type=trim(d.get('entity_type'),30).lower();entity_id=trim(d.get('entity_id') or '1',80)
        source=trim(d.get('source'),400);payload=d.get('payload')
        if event_type not in TWIN_EVENT_TYPES:raise ValueError('Invalid twin event type; safety approval cannot be recorded by software')
        if entity_type not in TWIN_ENTITY_TYPES:raise ValueError('Invalid twin entity type')
        if not isinstance(payload,dict) or not payload:raise ValueError('Twin event payload must contain structured evidence')
        if not source:raise ValueError('Twin event source/provenance is required')
        if event_type=='MEASUREMENT_RECORDED' and (not payload.get('value') or not payload.get('unit')):raise ValueError('Measurement events require value and unit')
        if event_type=='QUALIFIED_SIGNOFF_RECORDED' and not payload.get('reviewer'):raise ValueError('Qualified sign-off events require named reviewer')
        with self.get_db(False) as db:
            insert_twin_event(db,event_type,entity_type,entity_id,payload,source)
            if entity_type in {'case','job'} and entity_id.isdigit():sync_mission_progress(db,int(entity_id))
            db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),));db.commit()
            event_id=db.execute('SELECT last_insert_rowid()').fetchone()[0]
        return self.send_json(201,{'event_id':event_id,'event_type':event_type,'xp_value':TWIN_XP.get(event_type,0),'safety_clearance':'NOT_APPROVED'})
    def new_job(self,d):
        symptom=trim(d.get('symptom'),1500);system=trim(d.get('system'),100)
        context=trim(d.get('context'),1800);assembly_id=trim(d.get('assembly_id'),35)
        if len(symptom)<4:raise ValueError('Describe the symptom in at least 4 characters')
        if system not in self.server.groups:raise ValueError('Unknown vehicle system; select a catalogued system')
        if assembly_id:
            source=self.mm_db() or self.server.catalog
            with db_connect(source,True) as db:
                row=db.execute('SELECT group_name FROM assembly WHERE id=?',(assembly_id,)).fetchone()
                if not row:raise ValueError('Unknown assembly')
                if row['group_name']!=system:raise ValueError('Selected assembly does not belong to selected vehicle system')
        risk='SAFETY_CRITICAL_REVIEW_REQUIRED' if system in CRITICAL_GROUPS else 'REVIEW_REQUIRED'
        with self.get_db(False) as db:
            cur=db.execute('INSERT INTO job(created_utc,system,assembly_id,symptom,context,risk) VALUES(?,?,?,?,?,?)',
                (now(),system,assembly_id or None,symptom,context,risk));id=cur.lastrowid
            for code,label in CHECK_TEMPLATES.get(system,DEFAULT_CHECKS):
                db.execute('INSERT INTO diagnostic_check(job_id,code,label,updated_utc) VALUES(?,?,?,?)',(id,code,label,now()))
            domain_id=DOMAIN_BY_GROUP.get(system,'other')
            db.execute('INSERT INTO restoration_mission(job_id,domain_id,title,created_utc,updated_utc) VALUES(?,?,?,?,?)',(id,domain_id,(RESTORATION_DOMAINS.get(domain_id,{}).get('label') or system.replace('_',' ').title())+' — '+symptom[:90],now(),now()))
            insert_twin_event(db,'CASE_CREATED','case',id,{'system':system,'symptom':symptom,'status':'OPEN'},'Workbench case intake')
            db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),))
            db.commit()
        return self.send_json(201,{'job_id':id,'status':'OPEN','risk':risk,'prompts':GROUP_PROMPTS.get(system,DEFAULT_PROMPTS)})
    def expert_front_play(self):
        w=self.server.front_expert
        if self.mm_db():
            with db_connect(self.mm_db(),True) as db:
                arrays=[]
                for item in w['assemblies']:
                    a=db.execute('SELECT id,title AS slug,source_url FROM assembly WHERE id=? AND group_name=?',(item['id'],item['system'])).fetchone()
                    if not a:continue
                    figures=[dict(x) for x in db.execute('''SELECT fo.image_asset_id,fo.source_url AS figure_url,ia.status
                        FROM figure_occurrence fo JOIN image_asset ia ON ia.id=fo.image_asset_id WHERE fo.assembly_id=? LIMIT 4''',(a['id'],))]
                    arrays.append({**item,'slug':a['slug'],'source_url':a['source_url'],'figures':figures})
                parts=[]
                for item in w['parts']:
                    rows=[dict(x) for x in db.execute('''SELECT p.id,p.assembly_id,p.part_number,p.description,p.callout AS callout_position,
                        p.applicability FROM part_record p WHERE p.part_number=? LIMIT 2''',(item['number'],))]
                    parts.append({**item,'rows':rows,'source_reviewed':item['number'] in self.server.source_reviewed})
            v4={'assets_in_manifest':len(self.server.assets),'present':sum(1 for a in self.server.assets.values() if self.server.v4root and a.get('local_file') and (self.server.v4root/a['local_file']).is_file())}
            return self.send_json(200,{**w,'assemblies':arrays,'parts':parts,'v4':v4,'release_gate':'INTERNAL_PILOT; REAL_V4_BINARY_RENDERING_AND_PHYSICAL_SIGNOFF_REMAIN_OPEN'})
        with self.get_db() as db:
            arrays=[]
            for item in w['assemblies']:
                a=db.execute('SELECT id,slug,source_url FROM assembly WHERE id=? AND group_name=?',(item['id'],item['system'])).fetchone()
                if not a:continue
                figures=[dict(x) for x in db.execute('SELECT image_asset_id,figure_url FROM figure WHERE assembly_id=? LIMIT 4',(a['id'],))]
                arrays.append({**item,'slug':a['slug'],'source_url':a['source_url'],'figures':figures})
            parts=[]
            for p in w['parts']:
                rows=[dict(x) for x in db.execute('SELECT id,assembly_id,part_number,description,callout_position FROM part_row WHERE part_number=? LIMIT 2',(p['number'],))]
                parts.append({**p,'rows':rows,'source_reviewed':p['number'] in self.server.source_reviewed})
        v4={'assets_in_manifest':len(self.server.assets),'present':sum(1 for a in self.server.assets.values() if self.server.v4root and (self.server.v4root/a.get('local_file','__missing__')).is_file())}
        return self.send_json(200,{**w,'assemblies':arrays,'parts':parts,'v4':v4,'release_gate':'INTERNAL_PILOT; MAC_VISUAL_TEST_AND_REPAIR_PROCEDURE_NOT_CLEARED'})

    def start_expert_case(self,d):
        w=self.server.front_expert
        side=trim(d.get('side'),16).upper(); symptom=trim(d.get('symptom'),1200); context=trim(d.get('context'),1000)
        if side not in {'LEFT','RIGHT','BOTH','UNKNOWN'}:raise ValueError('Select a valid side')
        if len(symptom)<8:raise ValueError('Describe the front-axle or steering symptom in at least eight characters')
        with self.get_db(False) as db:
            cur=db.execute('INSERT INTO job(created_utc,system,assembly_id,symptom,context,risk) VALUES(?,?,?,?,?,?)',
                (now(),'front_axle',None,symptom,'Side: '+side+' | '+context,'SAFETY_CRITICAL_REVIEW_REQUIRED'))
            job_id=cur.lastrowid
            for code,label in CHECK_TEMPLATES['front_axle']:
                db.execute('INSERT INTO diagnostic_check(job_id,code,label,updated_utc) VALUES(?,?,?,?)',(job_id,code,label,now()))
            db.execute('INSERT INTO expert_case(job_id,workflow_id,side,created_utc) VALUES(?,?,?,?)',(job_id,w['id'],side,now()))
            db.execute('INSERT INTO restoration_mission(job_id,domain_id,title,created_utc,updated_utc) VALUES(?,?,?,?,?)',(job_id,'suspension_steering','Suspension & Steering — '+symptom[:90],now(),now()))
            for step in w['steps']:
                db.execute('INSERT INTO expert_step(job_id,code,updated_utc) VALUES(?,?,?)',(job_id,step['code'],now()))
            insert_twin_event(db,'CASE_CREATED','case',job_id,{'system':'front_axle','side':side,'symptom':symptom,'workflow_id':w['id']},'Front Axle Expert intake')
            db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),))
            db.commit()
        return self.send_json(201,{'job_id':job_id,'workflow_id':w['id'],'clearance':'NOT_APPROVED','stage_count':len(w['steps'])})

    def expert_cases(self):
        p=self.get_params();raw=self.one(p,'job_id','')
        with self.get_db(False) as db:
            if raw:
                if not raw.isdigit():raise ValueError('Invalid job number')
                c=db.execute('SELECT e.job_id,e.workflow_id,e.side,e.created_utc,j.symptom,j.risk,j.clearance FROM expert_case e JOIN job j ON e.job_id=j.id WHERE e.job_id=?',(int(raw),)).fetchone()
                if not c:return self.send_json(404,{'error':'Expert case not found'})
                steps=[dict(s) for s in db.execute('SELECT * FROM expert_step WHERE job_id=?',(int(raw),))]
                observations=[dict(o) for o in db.execute('SELECT created_utc,type,value,unit,tool,source FROM observation WHERE job_id=? ORDER BY id',(int(raw),))]
                return self.send_json(200,{'case':dict(c),'steps':steps,'observations':observations,'clearance':'NOT_APPROVED'})
            cases=[dict(c) for c in db.execute('SELECT e.job_id,e.workflow_id,e.side,e.created_utc,j.symptom,j.clearance FROM expert_case e JOIN job j ON e.job_id=j.id ORDER BY e.job_id DESC LIMIT 50')]
        return self.send_json(200,{'cases':cases,'clearance':'NOT_APPROVED'})

    def save_expert_step(self,d):
        job_id=d.get('job_id')
        if not str(job_id).isdigit():raise ValueError('Invalid job ID')
        job_id=int(job_id)
        code=trim(d.get('code'),40);status=trim(d.get('status'),32)
        finding=trim(d.get('finding'),2000);source=trim(d.get('source'),500)
        if code not in {x['code'] for x in self.server.front_expert['steps']}:raise ValueError('Invalid expert checkpoint')
        if status not in {'NOT_CHECKED','OBSERVED','NOT_APPLICABLE','NEEDS_SPECIALIST'}:raise ValueError('Invalid checkpoint state')
        if status=='OBSERVED' and len(finding)<3:raise ValueError('Observed finding requires evidence notes')
        with self.get_db(False) as db:
            c=db.execute('SELECT 1 FROM expert_case WHERE job_id=?',(job_id,)).fetchone()
            if not c:return self.send_json(404,{'error':'Expert case does not exist'})
            db.execute('UPDATE expert_step SET status=?,finding=?,source=?,updated_utc=? WHERE job_id=? AND code=?',
                (status,finding,source,now(),job_id,code));sync_mission_progress(db,job_id);db.commit()
        return self.send_json(200,{'saved':True,'job_id':job_id,'checkpoint':code,'clearance':'NOT_APPROVED'})

    def new_observation(self,id,d):
        type=trim(d.get('type'),40);value=trim(d.get('value'),2000)
        if type not in {'observation','measurement','photo_reference','inspection','source_reference','test_result','open_issue'}:
            raise ValueError('Invalid observation type')
        if not value:raise ValueError('Observation cannot be blank')
        unit=trim(d.get('unit'),32);tool=trim(d.get('tool'),100);source=trim(d.get('source'),400)
        if type=='measurement' and (not unit or not tool):raise ValueError('Measurements require a unit and tool/method')
        if not source:raise ValueError('Evidence source/person is required')
        with self.get_db(False) as db:
            if not db.execute('SELECT 1 FROM job WHERE id=?',(id,)).fetchone():return self.send_json(404,{'error':'Job not found'})
            db.execute('INSERT INTO observation(job_id,created_utc,type,value,unit,tool,source) VALUES(?,?,?,?,?,?,?)',
                (id,now(),type,value,unit,tool,source))
            event_type='MEASUREMENT_RECORDED' if type=='measurement' else 'OBSERVATION_RECORDED'
            insert_twin_event(db,event_type,'case',id,{'type':type,'value':value,'unit':unit,'tool':tool},source)
            sync_mission_progress(db,id);db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),))
            db.commit()
        return self.send_json(201,{'job_id':id,'saved':True,'status':'OPEN; NO_SAFETY_SIGNOFF'})
    def job_options(self,id):
        with self.get_db(False) as db:
            if not db.execute('SELECT 1 FROM job WHERE id=?',(id,)).fetchone():return self.send_json(404,{'error':'Job not found'})
            rows=[dict(x) for x in db.execute('''SELECT * FROM repair_option WHERE job_id=?
                ORDER BY CASE path WHEN 'REPAIR_EXISTING' THEN 1 WHEN 'USED_OEM_REFURBISHED' THEN 2
                WHEN 'SPEC_VERIFIED_CROSS_FIT' THEN 3 WHEN 'NEW_REPLACEMENT' THEN 4 ELSE 9 END,id''',(id,))]
        return self.send_json(200,{'job_id':id,'options':rows,
            'policy':'Repair existing first, then used/refurbished OEM, then specification-verified cross-fit, then new replacement. No option grants safety or fitment approval.',
            'clearance':'NOT_APPROVED'})
    def new_repair_option(self,id,d):
        path=trim(d.get('path'),40).upper();description=trim(d.get('description'),1200)
        part_number=trim(d.get('part_number'),80);fitment=trim(d.get('fitment_status'),40).upper()
        evidence=trim(d.get('evidence'),1800);source=trim(d.get('source'),700)
        decision=trim(d.get('decision_status') or 'PROPOSED',40).upper()
        if path not in REPAIR_PATHS:raise ValueError('Invalid repair/sourcing path')
        if len(description)<4:raise ValueError('Option description is required')
        if fitment not in OPTION_FITMENT:raise ValueError('Invalid fitment status')
        if len(evidence)<8:raise ValueError('Evidence basis is required; do not record unsupported recommendations')
        if not source:raise ValueError('Source/provenance is required')
        if decision not in OPTION_DECISIONS:raise ValueError('Software cannot approve a repair option; use PROPOSED, SELECTED_PENDING_SIGNOFF or REJECTED')
        with self.get_db(False) as db:
            if not db.execute('SELECT 1 FROM job WHERE id=?',(id,)).fetchone():return self.send_json(404,{'error':'Job not found'})
            cur=db.execute('''INSERT INTO repair_option(job_id,created_utc,path,description,part_number,fitment_status,evidence,source,cost_estimate,availability,decision_status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(id,now(),path,description,part_number,fitment,evidence,source,
                trim(d.get('cost_estimate'),120),trim(d.get('availability'),200),decision))
            option_id=cur.lastrowid
            insert_twin_event(db,'REPAIR_OPTION_RECORDED','case',id,{'path':path,'description':description,'part_number':part_number,'fitment_status':fitment,'decision_status':decision},source)
            sync_mission_progress(db,id);db.execute('UPDATE vehicle_twin SET updated_utc=? WHERE id=1',(now(),));db.commit()
        return self.send_json(201,{'job_id':id,'option_id':option_id,'saved':True,'decision_status':decision,'clearance':'NOT_APPROVED'})
    def export_job(self,id):
        with self.get_db(False) as db:
            j=db.execute('SELECT * FROM job WHERE id=?',(id,)).fetchone()
            if not j:return self.send_json(404,{'error':'Job not found'})
            obs=[dict(o) for o in db.execute('SELECT * FROM observation WHERE job_id=? ORDER BY id',(id,))]
        j=dict(j); system=j['system']; prompts=GROUP_PROMPTS.get(system,DEFAULT_PROMPTS)
        md=[f'# BMW 325iX WORK ORDER — IX-{id:04d}', '',f"VIN: {VEHICLE['vin']} | Production: {VEHICLE['build_date']} | Replacement M20B25 #ENGINE_NUMBER_NOT_CONFIGURED",'',
            f"Opened UTC: {j['created_utc']}",f"System: {system}",f"Assembly ID: {j['assembly_id'] or 'NOT ASSIGNED'}",
            f"Risk: {j['risk']}",f"Status: {j['status']}",f"Qualified sign-off: {j['clearance']}",'',
            '## Symptom',j['symptom'],'','## Context',j['context'] or 'Not recorded','','## Safety and questions',prompts['safety'],'']
        md.extend('- '+x for x in prompts['questions'])
        md+=['','## Workshop evidence log']
        for o in obs:md.append(f"- {o['created_utc']} | **{o['type']}**: {o['value']} {o['unit'] or ''} | tool {o['tool'] or '?'} | source {o['source'] or '?'}")
        if not obs:md.append('*No measurements, observations, photos or tests yet.*')
        with self.get_db(False) as db:
            checks=[dict(r) for r in db.execute('SELECT * FROM diagnostic_check WHERE job_id=? ORDER BY id',(id,))]
        md+=['','## Guided diagnostic checkpoints']
        for c in checks:
            md.append(f"- [{ 'x' if c['status'] in {'OBSERVED','NOT_APPLICABLE'} else ' ' }] {c['label']} | {c['status']} | finding: {c['finding'] or '?'} | source: {c['source'] or '?'}")
        md+=['','## Open verification and safety hold points','- [ ] Compare as-found parts and markings to catalog; check production dates and options.',
              '- [ ] Obtain and check original repair procedure for this vehicle and task.',
              '- [ ] Record correct measurements, tolerances, tool/calibration and sourced torque/fluids when relevant.',
              '- [ ] Document before/after findings and independent inspector where required.',
              '- [ ] No driving or closure of safety-critical repairs without competent physical sign-off.',
              '', '## Sources']
        for s in self.server.sources:
            if s['system'] in {system,'catalog'}:md.append(f"- {s['id']} — {s['title']} — {s['url']} — {s['status']}")
        with self.get_db(False) as db:
            c=db.execute('SELECT * FROM expert_case WHERE job_id=?',(id,)).fetchone()
            options=[dict(o) for o in db.execute('''SELECT * FROM repair_option WHERE job_id=?
                ORDER BY CASE path WHEN 'REPAIR_EXISTING' THEN 1 WHEN 'USED_OEM_REFURBISHED' THEN 2
                WHEN 'SPEC_VERIFIED_CROSS_FIT' THEN 3 WHEN 'NEW_REPLACEMENT' THEN 4 ELSE 9 END,id''',(id,))]
            if c:
                steps={r['code']:dict(r) for r in db.execute('SELECT * FROM expert_step WHERE job_id=?',(id,))}
                md+=['','## Front Axle Expert workflow (internal pilot)',f'Workflow: {c["workflow_id"]}; side: {c["side"]}',
                  'This job has no software-granted road-use approval, even when every checkpoint has notes.','']
                for step in self.server.front_expert['steps']:
                    x=steps.get(step['code'],{})
                    md.append(f'- **{step["title"]}** | {x.get("status","NOT_CHECKED")} | finding: {x.get("finding") or "NOT RECORDED"} | source: {x.get("source") or "NOT SUPPLIED"}')
                md+=['','### Technical references (observational guidance, not repair clearance)']
                for s in self.server.front_expert['sources']:
                    md.append(f'- {s["id"]} | {s["title"]} | source page {s["source_page"]} | {s["url"]} | {s["status"]}')
        if options:
            md+=['','## Repair / sourcing comparison','Policy: repair existing first; then used/refurbished OEM; then specification-verified cross-fit; then new replacement. None of these entries is software approval.']
            for o in options:
                md.append(f'- **{o["path"]}** | {o["description"]} | part {o["part_number"] or "?"} | fitment {o["fitment_status"]} | decision {o["decision_status"]} | evidence {o["evidence"]} | source {o["source"]} | cost {o["cost_estimate"] or "?"} | availability {o["availability"] or "?"}')
        md+=['','*Generated documentation, not a diagnosis or certified repair clearance.*','']
        return self.send_blob(200,'\n'.join(md).encode('utf-8'),'text/markdown; charset=utf-8',f'IX-{id:04d}-work-order.md')
    def diagnostic(self):
        p=self.get_params();system=trim(self.one(p,'system','front_axle'),80)
        if system not in self.server.groups:raise ValueError('Unknown system')
        q=trim(self.one(p,'symptom'),250)
        prompts=GROUP_PROMPTS.get(system,DEFAULT_PROMPTS)
        tokens=re.findall(r'[a-zA-Z0-9]{3,}',q.lower())[:7]
        keywords=[x for x in tokens if x not in {'the','and','that','with','front','rear','when','what','there','from','left','right','have','this','does','wheel','part'}]
        if self.mm_db():
            with db_connect(self.mm_db(),True) as db:
                rows=[dict(x) for x in db.execute('''SELECT a.id,a.title AS slug,a.group_name,a.source_url,count(p.id) as part_count
                    FROM assembly a LEFT JOIN part_record p ON p.assembly_id=a.id WHERE a.group_name=?
                    GROUP BY a.id ORDER BY a.title''',(system,))]
        else:
            with self.get_db() as db:
                rows=[dict(x) for x in db.execute('SELECT a.id,a.slug,a.group_name,a.source_url,count(p.id) as part_count FROM assembly a LEFT JOIN part_row p ON p.assembly_id=a.id WHERE a.group_name=? GROUP BY a.id ORDER BY a.slug',(system,))]
        def score(x):
            words=(x['slug']+' '+x['group_name']).replace('_',' ').lower()
            return (sum(3 for t in keywords if t in words), x['part_count'])
        rows.sort(key=score,reverse=True)
        ref=[x for x in self.server.sources if x['system'] in (system,'catalog')]
        return self.send_json(200,{'system':system,'symptom':q,'safety':prompts['safety'],
            'questions':prompts['questions'],'reminder':prompts['reminder'],
            'candidate_assemblies':rows[:12], 'technical_references':ref[:12], 'manual_excerpts':self.find_manual(q),
            'caution':'Candidate assembly names are not a diagnosis; workshop procedure links are references, not verified extracted instructions. Exact torque and limits are not provided.'})
    def v4_status(self):
        present=0;total=0
        if self.server.v4root:
            root=self.server.v4root.resolve()
            for a in self.server.assets.values():
                total+=1
                rel=a.get('local_file','')
                if not rel:continue
                fn=(root/rel).resolve()
                if root in fn.parents and fn.is_file() and fn.stat().st_size>100:present+=1
        return self.send_json(200,{'connected':bool(self.server.v4root),
            'manifest_assets':total,'images_present_locally':present,
            'note':'Images are read-only. V4 files are never rewritten.'})
    def manual_status(self):
        path=self.server.manual_index
        if not path.is_file():return self.send_json(200,{'indexed_pages':0,'indexed_documents':0,'message':'No local manual text indexed; technical source URLs are pointers only.'})
        with db_connect(path,True) as db:
            n=db.execute('SELECT count(*) FROM manual_page').fetchone()[0]
            d=db.execute('SELECT count(*) FROM manual_doc').fetchone()[0]
            columns={x[1] for x in db.execute('PRAGMA table_info(manual_doc)')}
            verified=0
            if 'verification_status' in columns:
                verified=db.execute("SELECT count(*) FROM manual_doc WHERE verification_status LIKE 'VERIFIED%'").fetchone()[0]
            tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            claims=db.execute('SELECT count(*) FROM manual_claim').fetchone()[0] if 'manual_claim' in tables else 0
        schema_version=2 if {'variant_scope','document_type','source_kind','authority','retrieved_utc'} <= columns else 1
        conflict_data=self.manual_conflict_data()
        return self.send_json(200,{'indexed_pages':n,'indexed_documents':d,'verified_documents':verified,'claim_records':claims,
            'unresolved_conflict_groups':len(conflict_data['conflicts']),
            'schema_version':schema_version,'page_provenance':'HASHED_PAGE_SECTIONS' if schema_version>=2 else 'LEGACY_PAGE_LABELS',
            'message':'Only documents deliberately imported by user are searchable. Source page count is not a claim of OEM authenticity.'})
    def find_manual(self,q,limit=12):
        path=self.server.manual_index
        if not path.is_file() or not q.strip():return []
        terms=[t for t in re.findall(r'[\w-]{3,}',q.lower()) if t not in {'the','and','from','with','what','for','this','that','where','front','rear','vehicle','bmw','325ix'}]
        if not terms:return []
        with db_connect(path,True) as db:
            # LIKE on user-supplied page text, never fabricated manual passages.
            columns={x[1] for x in db.execute('PRAGMA table_info(manual_doc)')}
            optional=('variant_scope','document_type','source_kind','authority','retrieved_utc','original_path','sha256')
            extra=', '.join('d.'+x+' AS doc_'+x for x in optional if x in columns)
            select='SELECT p.doc_id,p.page_label,p.body'
            if 'page_sha256' in {x[1] for x in db.execute('PRAGMA table_info(manual_page)')}:select+=',p.page_sha256'
            select+=',d.title,d.source_url,d.market,d.verification_status'
            if extra:select+=','+extra
            rows=[dict(r) for r in db.execute(select+" FROM manual_page p JOIN manual_doc d ON p.doc_id=d.id WHERE "+' OR '.join(['LOWER(p.body) LIKE ?']*min(len(terms),5))+
                    ' LIMIT 200',tuple('%'+t+'%' for t in terms[:5]))]
        def sc(r):return sum(1 for t in terms if t in r['body'].lower())
        rows.sort(key=sc,reverse=True)
        out=[]
        for r in rows[:limit]:
            item={k:v for k,v in r.items() if k!='body'}
            item['excerpt']=self.excerpt(r['body'],terms)
            item['citation']=r['title']+' — '+r['page_label']+' — document '+r['doc_id']
            item['provenance']={
                'document_id':r['doc_id'],'page_label':r['page_label'],
                'page_sha256':r.get('page_sha256'),'document_sha256':r.get('doc_sha256'),
                'variant_scope':r.get('doc_variant_scope'),'document_type':r.get('doc_document_type'),
                'source_kind':r.get('doc_source_kind'),'authority':r.get('doc_authority'),
                'retrieved_utc':r.get('doc_retrieved_utc'),'original_path':r.get('doc_original_path'),
                'verification_status':r.get('verification_status'),'market':r.get('market'),
            }
            out.append(item)
        return out
    @staticmethod
    def excerpt(body,terms):
        lo=body.lower();hits=[lo.find(t) for t in terms if lo.find(t)>=0]
        i=max(0,min(hits)-130) if hits else 0
        return ('…' if i else '')+body[i:i+500].replace('\x00','')+('…' if len(body)>i+500 else '')
    def manual_search(self):
        q=trim(self.one(self.get_params(),'q'),200)
        return self.send_json(200,{'results':self.find_manual(q),
            'scope':'USER_IMPORTED_TEXT; cite document/page/hash; verify variant, market and diagram visually'})
    def manual_conflict_data(self):
        path=self.server.manual_index
        empty={'conflicts':[],'policy':'Conflicting claims are never silently merged; qualified review must resolve them.'}
        if not path.is_file():return empty
        with db_connect(path,True) as db:
            tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'manual_claim' not in tables:return empty
            groups=[dict(x) for x in db.execute('''SELECT conflict_key,count(DISTINCT value) AS distinct_values
                FROM manual_claim GROUP BY conflict_key HAVING count(DISTINCT value)>1 ORDER BY conflict_key''')]
            out=[]
            for group in groups:
                claims=[dict(x) for x in db.execute('''SELECT c.id,c.doc_id,c.conflict_key,c.claim_text,c.value,c.source_locator,c.status,
                    d.title,d.source_url,d.market,d.verification_status
                    FROM manual_claim c JOIN manual_doc d ON d.id=c.doc_id
                    WHERE c.conflict_key=? ORDER BY c.doc_id,c.id''',(group['conflict_key'],))]
                out.append({'conflict_key':group['conflict_key'],'distinct_values':group['distinct_values'],
                            'status':'UNRESOLVED','claims':claims})
        return {'conflicts':out,'policy':'Conflicting claims are never silently merged; qualified review must resolve them.'}
    def manual_conflicts(self):
        return self.send_json(200,self.manual_conflict_data())
    def job_checks(self):
        p=self.get_params();id=int(self.one(p,'job_id','0'))
        with self.get_db(False) as db:
            exists=db.execute('SELECT id FROM job WHERE id=?',(id,)).fetchone()
            if not exists:return self.send_json(404,{'error':'Job not found'})
            rows=[dict(r) for r in db.execute('SELECT * FROM diagnostic_check WHERE job_id=? ORDER BY id',(id,))]
        return self.send_json(200,{'job_id':id,'checks':rows,'clearance':'NOT_APPROVED'})
    def update_job_check(self,d):
        id=int(d.get('job_id',0));code=trim(d.get('code'),100)
        status=trim(d.get('status'),32);finding=trim(d.get('finding'),1500);source=trim(d.get('source'),400)
        if status not in {'NOT_CHECKED','OBSERVED','NOT_APPLICABLE','NEEDS_SPECIALIST'}:raise ValueError('Invalid check status')
        with self.get_db(False) as db:
            x=db.execute('SELECT id FROM diagnostic_check WHERE job_id=? AND code=?',(id,code)).fetchone()
            if not x:return self.send_json(404,{'error':'Diagnostic check does not exist for job'})
            db.execute('UPDATE diagnostic_check SET status=?,finding=?,source=?,updated_utc=? WHERE job_id=? AND code=?',
                (status,finding,source,now(),id,code));sync_mission_progress(db,id);db.commit()
        return self.send_json(200,{'saved':True,'job_id':id,'clearance':'NOT_APPROVED'})
    def ai_status(self):
        if not self.server.ollama:return self.send_json(200,{'enabled':False,'message':'Optional Ollama is disabled. Guided, source-linked diagnostics work without an LLM.'})
        try:
            with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2) as r:
                tags=json.loads(r.read(250000)).get('models',[])
            return self.send_json(200,{'enabled':True,'available':True,'selected':self.server.ollama,'installed_models':[x.get('name') for x in tags]})
        except Exception as e:return self.send_json(200,{'enabled':True,'available':False,'selected':self.server.ollama,'error':str(e)[:160]})
    def route_payload(self,question,requested_group=''):
        q=question.lower()
        rules=[
            ('part_identity',('photo','pictured','stamped','stamp','number','diagram','identify','part number','part'),['photo or diagram reference','visible marking/OEM number','vehicle-side and location'],['human_review']),
            ('diagnostics',('symptom','noise','clunk','play','leak','vibration','fault','why','diagnos'),['observable symptom and operating condition','inspection findings','calibrated measurements where applicable'],['qualified_inspection']),
            ('repair_rebuild',('rebuild','repair','serviceable','overhaul','restore','refurb'),['component condition','measurements and damage findings','safety classification'],['human_review','qualified_inspection']),
            ('fitment',('fit','compatible','compatibility','dimension','geometry','interface','ix','awd','cross-fit','cross fit'),['exact variant and production applicability','interface/geometry measurements','physical comparison'],['physical_verification']),
            ('sourcing',('buy','source','available','price','supplier','used','replacement','alternative','offer'),['exact part identity','condition and provenance','market and availability'],['human_review']),
            ('qa',('qa','quality','checklist','sign-off','signoff','assemble','torque','procedure','after repair','release'),['verified procedure','completed evidence and test results','as-built record'],['qualified_signoff'])]
        scores=[]
        for agent,terms,evidence,gates in rules:
            score=sum(1 for term in terms if term in q)
            scores.append((score,agent,evidence,gates))
        scores.sort(key=lambda x:(x[0],x[1]=='diagnostics'),reverse=True)
        score,agent,evidence,gates=scores[0]
        if score==0:agent='diagnostics';evidence=rules[1][2];gates=rules[1][3]
        specialist=next((x for x in self.server.specialists.get('agents',[]) if x.get('id')==agent),{'id':agent,'label':agent})
        critical=bool(requested_group in CRITICAL_GROUPS or any(x in q for x in ('steering','suspension','brake','spring','hub','awd','transfer')))
        next_actions=['Capture the minimum evidence listed before making a consequential recommendation','Keep observations, hypotheses and verified procedures separate']
        if critical:next_actions.append('Qualified physical inspection is required; software cannot clear road use')
        return {'intent':agent,'specialist':specialist,'confidence':'HEURISTIC_ROUTING','matched_score':score,
            'required_evidence':evidence,'approval_gates':gates,'safety_class':'SAFETY_CRITICAL' if critical else 'REVIEW_REQUIRED',
            'next_actions':next_actions,'policy':'Routing selects a work path; it is not a diagnosis, fitment decision or safety approval.'}
    def ai_route(self,d=None):
        if d is None:
            p=self.get_params();d={'question':self.one(p,'question'),'system':self.one(p,'system')}
        question=trim(d.get('question'),1200);group=trim(d.get('system',''),80)
        if len(question)<8:raise ValueError('Please enter a specific technical question')
        if group and group not in self.server.groups:raise ValueError('Unknown group')
        return self.send_json(200,self.route_payload(question,group))
    def specialists(self):
        return self.send_json(200, self.server.specialists)
    def workflow_front_axle(self):
        steps=[]
        for item in self.server.front_expert.get('steps',[]):
            steps.append({'code':item['code'],'title':item['title'],'kind':item['kind'],
                          'evidence_required':item['evidence'],'approval_required':item['kind'] in {'MECHANIC','MEASUREMENT','REPAIR_DECISION','QA'}})
        return self.send_json(200, {'workflow_id':self.server.front_expert['id'],
            'vehicle':VEHICLE,'clearance':'NOT_APPROVED','steps':steps,
            'connected_surfaces':['S1_PARTS','S2_MANUALS','S3_PHOTOS','S4_FITMENT','S5_DIAGNOSTICS','S6_WORKBENCH_QA','C0_INTEGRATION']})
    def integration_health(self):
        checks=[]
        def check(name,ok,detail):checks.append({'name':name,'ok':bool(ok),'detail':detail})
        catalog_source=self.mm_db() or self.server.catalog
        check('read_only_catalog',catalog_source.is_file(),str(catalog_source))
        with db_connect(catalog_source,True) as db:
            if self.mm_db():
                assemblies=db.execute('SELECT count(*) FROM assembly').fetchone()[0]
                parts=db.execute('SELECT count(*) FROM part_record').fetchone()[0]
                images=db.execute('SELECT count(*) FROM image_asset').fetchone()[0]
            else:
                assemblies=db.execute('SELECT count(*) FROM assembly').fetchone()[0]
                parts=db.execute('SELECT count(*) FROM part_row').fetchone()[0]
                images=0
        check('full_catalog_identity',assemblies == 805 and parts == 13845, f'{assemblies} assemblies / {parts} rows')
        check('multimodal_graph_index',images == 572 if self.mm_db() else False, f'{images} image assets indexed')
        check('full_catalog_registry_loaded',len(self.server.research) == 7190, f'{len(self.server.research)} registry records')
        check('front_axle_workflow',len(self.server.front_expert.get('steps',[])) == 7,'7 evidence checkpoints')
        check('specialist_registry',len(self.server.specialists.get('agents',[])) >= 6,'6 specialist roles')
        check('persistent_jobs',self.server.jobs.parent.exists(),'SQLite job store available')
        check('v4_assets',bool(self.server.v4root),'optional read-only V4 root connected' if self.server.v4root else 'not connected')
        check('local_ai',bool(self.server.ollama),'Ollama configured' if self.server.ollama else 'optional; guided workflow remains available')
        manual_index=self.server.manual_index
        if manual_index.is_file():
            with sqlite3.connect(manual_index) as db:
                manual_docs=db.execute('SELECT count(*) FROM manual_doc').fetchone()[0]
                manual_pages=db.execute('SELECT count(*) FROM manual_page').fetchone()[0]
            check('manual_evidence_index',manual_docs >= 57 and manual_pages >= 1500,
                  f'{manual_docs} documents / {manual_pages} page sections')
        else:
            check('manual_evidence_index',False,'maintenance manual index not found')
        ready=all(x['ok'] for x in checks[:7])
        return self.send_json(200, {'status':'READY_FOR_INTEGRATION_TEST' if ready else 'DEGRADED','checks':checks,'safety_clearance':'NOT_APPROVED'})
    def ai_ask(self,d):
        question=trim(d.get('question'),1200)
        if len(question)<8:raise ValueError('Please enter a specific technical question')
        requested_language=trim(d.get('language',''),8).lower()
        if requested_language not in {'en','ar'}:
            requested_language='ar' if re.search(r'[\u0600-\u06ff]',question) else 'en'
        requested_group=trim(d.get('system',''),80)
        if requested_group and requested_group not in self.server.groups:raise ValueError('Unknown group')
        routing=self.route_payload(question,requested_group)
        case_context=None
        raw_case=trim(d.get('job_id'),20)
        if raw_case:
            if not raw_case.isdecimal():raise ValueError('Invalid case ID')
            case_id=int(raw_case)
            with self.get_db(False) as db:
                job=db.execute('SELECT id,system,symptom,context,status,risk,clearance FROM job WHERE id=?',(case_id,)).fetchone()
                if not job:raise ValueError('Case not found')
                observations=[dict(x) for x in db.execute('SELECT type,value,unit,tool,source FROM observation WHERE job_id=? ORDER BY id',(case_id,))]
                options=[dict(x) for x in db.execute('SELECT path,description,part_number,fitment_status,evidence,source,decision_status FROM repair_option WHERE job_id=? ORDER BY id',(case_id,))]
                findings=[dict(x) for x in db.execute('SELECT agent_id,intent,finding,uncertainty,tests_json,status,source FROM specialist_finding WHERE job_id=? ORDER BY id DESC',(case_id,))]
            for finding in findings:finding['tests']=json.loads(finding.pop('tests_json'))
            case_context={'job':dict(job),'observations':observations,'options':options,'specialist_findings':findings,'retrieval_scope':'CASE_RECORDS; USER_RECORDED_EVIDENCE'}
        tokens=[t for t in re.findall(r'[a-z0-9]{3,}',question.lower()) if t not in {'the','and','with','from','what','that','this','have','about','when','where','could','would','should','does','325ix','bmw','front','rear'}]
        source=self.mm_db() or self.server.catalog
        with db_connect(source,True) as db:
            groups=[dict(x) for x in db.execute('SELECT group_name FROM assembly GROUP BY group_name')]
            g=next((x['group_name'] for x in groups if x['group_name'] in question.lower().replace(' ','_')),'')
            group=requested_group or g
            searchterms=[]
            for t in tokens[:7]:
                pattern='%'+escape_like(t)+'%'
                if self.mm_db():
                    sql=("SELECT p.part_number,p.description,p.callout AS callout_position,p.date_raw AS date_condition_raw, "
                         "a.id AS assembly_id,a.group_name,a.title AS slug,a.source_url "
                         "FROM part_record p JOIN assembly a ON a.id=p.assembly_id "
                         "WHERE (p.description LIKE ? OR p.part_number LIKE ? OR a.title LIKE ?) "
                         "AND (?='' OR a.group_name=?) LIMIT 5")
                else:
                    sql=("SELECT p.part_number,p.description,p.callout_position,p.date_condition_raw, "
                         "a.id AS assembly_id,a.group_name,a.slug,a.source_url "
                         "FROM part_row p JOIN assembly a ON a.id=p.assembly_id "
                         "WHERE (p.description LIKE ? OR p.part_number LIKE ? OR a.slug LIKE ?) "
                         "AND (?='' OR a.group_name=?) LIMIT 5")
                rr=[dict(x) for x in db.execute(sql,(pattern,pattern,pattern,group,group))]
                searchterms.extend(rr)
        seen=set();retrieved=[]
        for row in searchterms:
            key=(row['part_number'],row['assembly_id'])
            if key not in seen:retrieved.append(row);seen.add(key)
            if len(retrieved)>=15:break
        relevant_refs=[dict(x) for x in self.server.sources if not group or x['system'] in (group,'catalog')][:9]
        manuals=self.find_manual(question,8)
        manual_conflicts=self.manual_conflict_data()['conflicts'][:12]
        system_prompt=(
            'You are a cautious BMW 1987-12 production 325iX workshop research assistant, NOT a certified mechanic. '
            'Current owner-confirmed replacement engine is M20B25 serial ENGINE_NUMBER_NOT_CONFIGURED, manual AWD LHD. '
            'Use retrieved ETK part rows for part identity, and explicitly cited user-imported manual text for procedural claims. Manual URL pointers without excerpts are NOT read procedures. '
            'If evidence is insufficient, explicitly say so and request an observable measurement/photo/test. '
            'Always separate observations, hypotheses, discriminating tests, and verified source-backed procedures. '
            'Never invent a torque, clearance, pressure, dimension, fluid, electrical pinout, interchange fitment or safety clearance. '
            'Do not assume generic RWD E30 parts fit iX. For brakes, suspension, steering, fuel, spring handling, lifting and AWD, require qualified inspection and actual BMW technical procedure before action. '
            f'Respond in {"Arabic" if requested_language == "ar" else "English"} unless the user explicitly asks for another language. Cite catalog rows with their supplied source_url; do not claim external pages have been read. '
            'The indexed ETK-derived catalog covers variants and can have date filters; a row is not confirmed fitment.' )
        content='QUESTION: '+question+'\n\nRETRIEVED PART ROWS: '+json.dumps(retrieved,ensure_ascii=False)[:12000]+'\n\nCASE CONTEXT (only if supplied; cite case records and preserve uncertainty): '+json.dumps(case_context,ensure_ascii=False)[:10000]+'\n\nUSER IMPORTED MANUAL EXCERPTS (cite document/page/hash; market and variant still require validation): '+json.dumps(manuals,ensure_ascii=False)[:7500]+'\n\nUNRESOLVED MANUAL CLAIM CONFLICTS (do not choose between them): '+json.dumps(manual_conflicts,ensure_ascii=False)[:7500]+'\n\nMANUAL POINTERS (unread): '+json.dumps(relevant_refs,ensure_ascii=False)[:4000]
        if not self.server.ollama:
            language=requested_language
            if language=='ar':
                answer=('المساعد المحلي الموثق يستطيع تأكيد هوية صفوف الكتالوج فقط. '
                        'لا توجد هنا أدلة كافية لتشخيص العطل أو اعتماد الإصلاح. '
                        'سجّل صورة/رقم القطعة والقياس وفحص الميكانيكي المؤهل، ثم راجع الإجراء الأصلي المناسب.')
            else:
                answer=('Offline grounded assistant: I can confirm catalog identity and evidence gaps, '
                        'but I cannot diagnose or approve this safety-critical repair from the available evidence. '
                        'Record the exact component marking, calibrated measurement, photo provenance and qualified inspection before acting.')
            return self.send_json(200,{'answer':answer,'model':'OFFLINE_GROUNDED_FALLBACK','language':language,
                'catalog_evidence':retrieved,'manual_pointers':relevant_refs,'manual_excerpts':manuals,'manual_conflicts':manual_conflicts,
                'routing':routing,'case_context':case_context,'policy':'GROUNDED_RULES_ASSISTANCE; NO DIAGNOSIS, FITMENT OR SAFETY APPROVAL'})
        payload=json.dumps({'model':self.server.ollama,'stream':False,'messages':[{'role':'system','content':system_prompt},{'role':'user','content':content}],'options':{'num_predict':420,'temperature':0.15}},ensure_ascii=False).encode()
        try:
            req=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=payload,headers={'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(req,timeout=120) as resp:
                body=json.loads(resp.read(250000))
        except Exception as e:return self.send_json(503,{'error':'Local Ollama request failed: '+str(e)[:250]})
        answer=body.get('message',{}).get('content','')
        return self.send_json(200,{'answer':answer,'model':self.server.ollama,'language':requested_language,'catalog_evidence':retrieved,'manual_pointers':relevant_refs,'manual_excerpts':manuals,'manual_conflicts':manual_conflicts,'routing':routing,'case_context':case_context,'policy':'MODEL_GENERATED_UNVERIFIED; NO FITMENT OR SAFETY APPROVAL'})
    def diagram(self):
        p=self.get_params();asset=trim(self.one(p,'asset'),60)
        if not re.fullmatch('IMG-[a-f0-9]{16}',asset):return self.send_json(400,{'error':'Invalid image asset id'})
        a=self.server.assets.get(asset)
        if not a or not a.get('local_file') or not self.server.v4root:return self.send_json(404,{'error':'Image not available locally'})
        root=self.server.v4root.resolve();f=(root/a['local_file']).resolve()
        if root not in f.parents or not f.is_file():return self.send_json(404,{'error':'Image not found in local V4 folder'})
        if f.stat().st_size>16000000:return self.send_json(403,{'error':'Image too large for preview'})
        mime={'webp':'image/webp','jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png'}.get(f.suffix.lower().strip('.'))
        if not mime:return self.send_json(400,{'error':'Invalid image type'})
        return self.send_blob(200,f.read_bytes(),mime)

def main():
    p=argparse.ArgumentParser(description='Local BMW 325iX parts and inspection workbench')
    p.add_argument('--catalog',type=Path,default=APP/'data'/'325ix_assemblies.sqlite3')
    p.add_argument('--jobs',type=Path,default=APP/'workshop_jobs.sqlite3')
    p.add_argument('--v4-root',type=Path,default=None,help='Optional local 14_MULTIMODAL_MEDIA_AND_GRAPH folder for downloaded images')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--photo-root',type=Path,default=APP/'actual_part_photos')
    default_manual_index=APP/'maintenance_manual_index.sqlite3' if (APP/'maintenance_manual_index.sqlite3').is_file() else APP/'manual_index.sqlite3'
    p.add_argument('--manual-index',type=Path,default=default_manual_index)
    p.add_argument('--ollama-model',default=None,help='Optional installed local Ollama model name (no cloud token required)')
    p.add_argument('--multimodal-db',type=Path,default=APP/'04_SEARCH'/'325ix_multimodal.sqlite3',help='Read-only V3/V4 multimodal catalog index')
    p.add_argument('--demo',action='store_true',help='Allow the bundled five-assembly front-axle fixture; never use for full-catalog claims')
    args=p.parse_args()
    if not args.catalog.is_file():p.error('Catalog missing: '+str(args.catalog))
    multimodal=args.multimodal_db if args.multimodal_db.is_file() else None
    catalog_source=multimodal or args.catalog
    with db_connect(catalog_source,True) as db:
        assembly_count=db.execute('SELECT count(*) FROM assembly').fetchone()[0]
        if multimodal:
            part_count=db.execute('SELECT count(*) FROM part_record').fetchone()[0]
            if assembly_count!=805 or part_count!=13845:p.error('Incomplete multimodal catalog: '+str(assembly_count)+' assemblies / '+str(part_count)+' parts')
        elif assembly_count!=805 and not args.demo:
            p.error('Expected 805 assemblies; received '+str(assembly_count)+' (use --demo only with the bundled fixture)')
    init_jobs(args.jobs)
    init_expert_cases(args.jobs)
    photo_db=APP/'part_photos.sqlite3'
    init_photos(photo_db)
    with (APP/'sources.json').open(encoding='utf-8') as f:sources=json.load(f)
    extra_file=APP/'sources_extra.json'
    if extra_file.exists():
        with extra_file.open(encoding='utf-8') as f:extra=json.load(f)
        existing={e['id'] for e in sources}
        sources.extend(x for x in extra if x.get('id') not in existing)

    curated_file=APP/'curated_evidence.json'
    curated={}
    if curated_file.is_file():
        with curated_file.open(encoding='utf-8') as f:
            curated=json.load(f).get('evidence',{})
    if not isinstance(curated,dict):p.error('Invalid curated evidence file')
    specialist_file=APP/'specialists.json'
    if not specialist_file.is_file():p.error('Specialist registry missing: '+str(specialist_file))
    with specialist_file.open(encoding='utf-8') as f:specialists=json.load(f)
    research_path=APP/'catalog_research_registry.json'
    research={};research_stats={};research_order=[]
    if research_path.is_file():
        with research_path.open(encoding='utf-8') as f:catalog_program=json.load(f)
        research=catalog_program.get('parts',{})
        research_stats=catalog_program.get('catalog_coverage',{})
        research_order=list(research)
        if len(research)!=7190:p.error('Incomplete full-catalog research registry')

    v4root=args.v4_root
    # Detect a separately copied V4 tree without forcing the user to pass a flag.
    if not v4root:
        candidates=[APP/'14_MULTIMODAL_MEDIA_AND_GRAPH',APP,APP.parent/'14_MULTIMODAL_MEDIA_AND_GRAPH',Path.home()/'Desktop'/'14_MULTIMODAL_MEDIA_AND_GRAPH']
        v4root=next((candidate for candidate in candidates if (candidate/'03_MANIFESTS'/'image_assets.jsonl').is_file()),None)
    assets={}
    if v4root:
        local_manifest=v4root/'03_MANIFESTS'/'image_assets_local.jsonl'
        file=local_manifest if local_manifest.is_file() else v4root/'03_MANIFESTS'/'image_assets.jsonl'
        if file.is_file():
            with file.open(encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        d=json.loads(line)
                        if d.get('asset_id'):assets[d['asset_id']]=d
    srv=ThreadingHTTPServer(('127.0.0.1',args.port),App)
    with db_connect(catalog_source,True) as db:groups=set(x[0] for x in db.execute('SELECT DISTINCT group_name FROM assembly'))
    source_reviewed={n for n,r in curated.items() if n in research and sourced_curated(n,r)}
    with (APP/'front_axle_expert_v1.json').open(encoding='utf-8') as f:front_expert=json.load(f)
    if len(front_expert.get('steps',[]))!=7: p.error('Front expert evidence workflow is incomplete')
    srv.front_expert=front_expert
    srv.specialists=specialists
    srv.research=research;srv.research_stats=research_stats;srv.research_order=research_order
    srv.source_reviewed=source_reviewed;srv.curated=curated
    srv.catalog=args.catalog;srv.multimodal=multimodal;srv.jobs=args.jobs;srv.photos=photo_db;srv.photo_root=args.photo_root;srv.sources=sources;srv.v4root=v4root;srv.assets=assets;srv.groups=groups;srv.ollama=args.ollama_model;srv.manual_index=args.manual_index
    print('BMW 325iX Restoration OS MVP-0.9.0 RC12 — system-wide device-acceptance candidate')
    print('Ollama:',args.ollama_model or 'disabled (guide works without AI)')
    print('Read-only catalog:',catalog_source)
    print('Job database:',args.jobs)
    print('Assemblies indexed:',assembly_count)
    print('Source-reviewed exact OEM numbers:',len(source_reviewed))
    print('Full catalog worklist:',len(research),'batches:',research_stats.get('batches'))
    print(f'Open locally: http://127.0.0.1:{args.port}')
    print('Stop with Ctrl+C. Nothing in the V4 downloader is modified.')
    try:srv.serve_forever()
    except KeyboardInterrupt:print('\nStopped.')
    finally:srv.server_close()

if __name__=='__main__':main()
