#!/usr/bin/env python3
"""Install pinned MIT Three.js modules and licensed E30 reference geometry.

Only writes to this extracted release copy; independent of Drive and live jobs.
Python standard library only. Internet is needed once, then the viewer works offline.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from hashlib import sha1,sha256
from datetime import datetime,timezone
import json,os,sys

ROOT=Path(__file__).resolve().parents[1]
URLS={
  'vendor/three/build/three.module.js':'https://cdn.jsdelivr.net/npm/three@0.159.0/build/three.module.js',
  'vendor/three/examples/jsm/controls/OrbitControls.js':'https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/controls/OrbitControls.js',
  'vendor/three/examples/jsm/loaders/GLTFLoader.js':'https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/loaders/GLTFLoader.js',
  'vendor/three/examples/jsm/utils/BufferGeometryUtils.js':'https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/utils/BufferGeometryUtils.js',
  'vendor/three/LICENSE':'https://cdn.jsdelivr.net/npm/three@0.159.0/LICENSE',
  'vendor/meshopt_decoder.module.js':'https://cdn.jsdelivr.net/npm/meshoptimizer@0.22.0/meshopt_decoder.module.js',
  'vendor/meshoptimizer_LICENSE.md':'https://cdn.jsdelivr.net/npm/meshoptimizer@0.22.0/LICENSE.md',
  'models/e30_reference_m3.glb':'https://raw.githubusercontent.com/ahnuchen/auto-atlas/master/public/models/free_bmw_m3_e30.glb',
}
MODEL_GIT_BLOB='8aaa3daafd53158b63ced92c4c65d520ebce561f'
JS_SUFFIX='.js'

def get(url):
    req=Request(url,headers={'User-Agent':'BMW-325iX-Local-Viewer/0.1 (rights-preserving reference download)'})
    with urlopen(req,timeout=45) as res:
        return res.read()

def install():
    report={'installed_utc':datetime.now(timezone.utc).isoformat(),'files':{},'source':'ahnuchen/auto-atlas; Martin Trafas CC BY 4.0','status':'partial'}
    failed=[]
    for name,url in URLS.items():
        dst=ROOT/name
        try:
            if dst.exists() and dst.stat().st_size>0:
                raw=dst.read_bytes()
                if name.startswith('models/'):
                    blob=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                    if blob!=MODEL_GIT_BLOB:raise ValueError('Existing model does not match expected Git blob SHA')
                report['files'][name]={'sha256':sha256(raw).hexdigest(),'bytes':len(raw),'url':url,'status':'existing'}
                print('OK (cached):',name)
                continue
            print('Downloading:',name,flush=True)
            raw=get(url)
            if name.startswith('models/'):
                blob=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                if blob!=MODEL_GIT_BLOB:
                    raise ValueError('Model changed upstream (Git blob '+blob+'). Refusing unreviewed asset; expected '+MODEL_GIT_BLOB)
                if raw[:4]!=b'glTF':raise ValueError('Not a GLB')
            if name.endswith(JS_SUFFIX) and name.startswith('vendor/three/examples/'):
                # Eliminate bare-specifier import map requirement; all dependencies are local.
                raw=raw.replace(b"from 'three'",b"from '/vendor/three/build/three.module.js'")
                raw=raw.replace(b'from "three"',b'from "/vendor/three/build/three.module.js"')
            dst.parent.mkdir(parents=True,exist_ok=True)
            temp=dst.with_suffix(dst.suffix+'.tmp')
            temp.write_bytes(raw);os.replace(temp,dst)
            report['files'][name]={'sha256':sha256(raw).hexdigest(),'bytes':len(raw),'url':url,'status':'downloaded'}
            print('OK:',name, len(raw),'bytes')
        except (HTTPError,URLError,TimeoutError,ValueError,OSError) as exc:
            failed.append(name)
            report['files'][name]={'status':'failed','error':str(exc)[:220],'url':url}
            print('FAILED:',name,exc,file=sys.stderr)
    report['status']='ready' if not failed else 'partial'
    out=ROOT/'models'/'asset-install-report.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('3D asset status:',report['status'],'(2D fallback remains available)')
    return 0 if not failed else 1

if __name__=='__main__':sys.exit(install())
