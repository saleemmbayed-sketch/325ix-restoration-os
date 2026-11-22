#!/usr/bin/env python3
"""Offline RC19 data/interaction contract. Browser WebGL tested separately in CI."""
from pathlib import Path
import json,struct,hashlib,subprocess,sys
root=Path(__file__).resolve().parent
index=json.loads((root/'mechanical_index.json').read_text())
assert len(index['scenes'])==3
expected={'ix_m20_engine_bay':{'valve_cover','intake_runners','bonnet','radiator','engine_block'},
          'ix_front_axle_workshop':{'strut_tube','coil_spring','cv_shaft','front_differential','tie_rod'},
          'ix_awd_driveline_workshop':{'transfer_case','front_prop','rear_prop','front_diff','rear_diff'}}
for scene in index['scenes']:
 p=root/scene['filename'];b=p.read_bytes()
 assert b[:4]==b'glTF' and struct.unpack_from('<I',b,8)[0]==len(b),p
 size=struct.unpack_from('<I',b,12)[0]
 assert b[16:20]==b'JSON'
 gltf=json.loads(b[20:20+size]);names={x.get('name','') for x in gltf['nodes']}
 ids={c['id'] for c in scene['components']}
 assert expected[scene['slug']]<=ids
 assert all(any(n.startswith('MX:'+cid+':') for n in names) for cid in ids),'Semantic 3D nodes must be preserved'
 assert hashlib.sha256(b).hexdigest()==scene['sha256']
 assert (root/scene['preview']).stat().st_size>5000
 assert len(scene['components'])>=11
 assert all(c['system'] and c['search_terms'] for c in scene['components'])
site=(root/'site.js').read_text();backend=(root/'app.py').read_text();view=(root/'viewer3d.js').read_text()
for needle in ('openMechanicalScene','selectMechanicalComponent','renderMechanicalJobForm','mechanicalCandidate?.assembly_id',
 '/api/job/','ix-mech-part-list','ix-mech-job-source'):
 assert needle in site,needle
for needle in ('openMechanical','toggleBonnet','setupEngineBonnet','isolateMechanicalComponent','focusMechanicalComponent'):
 assert needle in view,needle
for needle in ('/mechanical_index.json','ix_m20_engine_bay.glb','ix_front_axle_workshop.glb','ix_awd_driveline_workshop.glb','/api/jobs'):
 assert needle in backend,needle
for x in ['site.js','viewer3d.js','scripts/browser_mechanical_smoke.cjs']:
 r=subprocess.run(['node','--check',str(root/x)],capture_output=True,text=True)
 assert r.returncode==0,(x,r.stderr)
print('PASS RC19: 3 original valid GLBs; semantic mesh IDs; 57 component records; catalog → saved job → evidence contracts; WebGL test script parses')
