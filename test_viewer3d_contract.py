#!/usr/bin/env python3
"""Offline 3D integration contract smoke checks; not a WebGL browser test."""
from pathlib import Path
import re,subprocess,sys,json,hashlib,zipfile,tempfile,shutil
ROOT=Path(__file__).resolve().parent

def main():
  app=(ROOT/'app.py').read_text()
  site=(ROOT/'site.js').read_text()
  view=(ROOT/'viewer3d.js').read_text()
  prep=(ROOT/'scripts/prepare_3d_assets.py').read_text()
  assert "'/viewer3d.js':" in app and "'/models/e30_reference_m3.glb':" in app
  assert 'import(\'/viewer3d.js\')' in site and 'ixSelectVisualSystemById' in site
  assert 'activate2DFallback' in site and 'local_available===true' in site
  assert 'if(!status.ready)' in site and "'/api/3d/status'" in site
  assert 'missing=[n for n in required' in app
  assert "loadVisualAssemblies(system)" in site and "loadVisualAssembly" in site and "selectVisualPart" in site
  assert "MeshoptDecoder" in view and "GLTFLoader" in view and "OrbitControls" in view
  assert "setExplosion" in view and "selectMesh" in view and "positionView" in view
  # Ponytail RC16: no fake SVG vehicle map or serial probes for cached OEM diagrams.
  assert 'VISUAL_LAYOUT' not in site and 'twinNode(' not in site
  assert 'has_local_drawing' in app and 'has_local_drawing' in site
  assert 'ix-system-finder' in site and 'visualSearchToken' in site
  assert 'ix3d-marker' in view and 'REGIONS' in view
  assert "MODEL_GIT_BLOB='8aaa3daafd53158b63ced92c4c65d520ebce561f'" in prep
  assert 'NOT_APPROVED' in app and 'NOT 325iX CAD' in view
  assert "'/explosion-rig.js':" in app and "from '/explosion-rig.js'" in view
  assert 'setExplodeFactor' in view and 'triggerTelemetryAlert' in view
  assert 'ix-explode-scope' in site and (ROOT/'explosion-rig.js').is_file()
  assert (ROOT/'scripts/prepare_vehicle_blender.py').is_file()
  # RC17: one external four-door preview and private, catalog-bound local GLB/STL imports.
  assert 'ix-preview-sedan' in site and 'bd0925e21c934a9cbfdb30ccf5584e86' in site
  assert 'PERSONAL_MODELS' in app and "if path=='/api/3d/models'" in app
  assert 'def personal_model_save' in app and 'def personal_slot_valid' in app
  assert 'frame-src https://sketchfab.com' in app
  assert 'async function openPersonal' in view and 'loadBinarySTL' in view
  assert 'local_models/' in (ROOT/'.gitignore').read_text()
  if shutil.which('node'):
    for path in ('viewer3d.js','site.js'):
      result=subprocess.run(['node','--check',path],cwd=ROOT,capture_output=True,text=True)
      if result.returncode:raise AssertionError(path+': '+result.stderr)
  result=subprocess.run([sys.executable,'-m','py_compile','app.py','launch_rc12_trial.py','scripts/prepare_3d_assets.py'],cwd=ROOT,capture_output=True,text=True)
  assert result.returncode==0,result.stderr
  assert json.loads((ROOT/'docs/runtime_rc13_sha256.json').read_text())['sha256_files']['04_SEARCH/325ix_multimodal.sqlite3']
  print('PASS: JS/Python parse; local asset routes; source pin; 3D/2D integration contract; no safety clearance')
  print('LIMIT: no installed real GLB/Three.js in this offline execution environment; device visual test still pending.')
  return 0
if __name__=='__main__':sys.exit(main())
