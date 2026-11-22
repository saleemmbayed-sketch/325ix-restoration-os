#!/usr/bin/env python3
"""Truthful RC14 source, runtime, model-rights, and device-acceptance receipt.
Never calls unverified geometry 'exact 325iX' and never grants road clearance.
"""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,sys,hashlib,importlib.util
ROOT=Path(__file__).resolve().parent

def run(cmd):
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=45)
  return p.returncode==0,(p.stdout+p.stderr).strip()[-320:]

def main():
  source_ok,source_note=run([sys.executable,'test_viewer3d_contract.py'])
  core_ok,core_note=run([sys.executable,'test_mvp_integration.py']) if (ROOT/'04_SEARCH/325ix_multimodal.sqlite3').exists() else (False,'Runtime data not yet imported from pinned RC13')
  model=ROOT/'models/e30_reference_m3.glb'
  try:
    git_blob=hashlib.sha1(b'blob '+str(model.stat().st_size).encode()+b'\0'+model.read_bytes()).hexdigest() if model.is_file() else None
  except OSError:git_blob=None
  model_ok=git_blob=='8aaa3daafd53158b63ced92c4c65d520ebce561f'
  vendors=[ROOT/x for x in ('vendor/three/build/three.module.js','vendor/three/examples/jsm/controls/OrbitControls.js','vendor/three/examples/jsm/loaders/GLTFLoader.js','vendor/three/examples/jsm/utils/BufferGeometryUtils.js','vendor/meshopt_decoder.module.js')]
  vendors_ok=all(p.is_file() for p in vendors)
  checks=[
    {'gate':'source_parse_and_interface_contract','status':'PASS' if source_ok else 'FAIL','detail':source_note},
    {'gate':'existing_missions_catalog_integration','status':'PASS' if core_ok else 'NOT_RUN_OR_FAIL','detail':core_note},
    {'gate':'pinned_CC_BY_E30_reference_model','status':'PASS' if model_ok else 'PENDING','detail':git_blob or 'Model not cached in this environment'},
    {'gate':'locally_cached_MIT_renderer','status':'PASS' if vendors_ok else 'PENDING','detail':'Three.js + meshopt modules'},
    {'gate':'actual_browser_WebGL_and_owner_Mac_Monterey','status':'NOT_OBSERVED','detail':'Actual GUI/GLB/scene picking/explosion not validated in this sandbox'},
    {'gate':'mechanical_fitment_and_roadworthiness','status':'NOT_APPROVED','detail':'Qualified owner/mechanic evidence and sign-off required; reference model is not iX-specific'},
  ]
  result={'release':'BMW_325IX_3D_STUDIO_RC14_SOURCE_PREVIEW','generated_utc':datetime.now(timezone.utc).isoformat(),'status':'SOURCE_INTEGRATED_NOT_DEVICE_ACCEPTED' if source_ok and core_ok else 'NOT_READY','checks':checks,'source_of_truth':'Drive 325IX DATA + local owner evidence; no automatic changes','license':'CC BY 4.0 model; MIT JS libraries','repository_publication':'NOT_PUSHED'}
  (ROOT/'3D_RELEASE_STATUS.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({'release':result['release'],'status':result['status'],'checks':checks},indent=2))
  return 0 if source_ok and core_ok else 1
if __name__=='__main__':sys.exit(main())
