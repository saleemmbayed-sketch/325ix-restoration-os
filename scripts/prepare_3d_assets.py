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
import json,os,sys,zipfile,io,argparse
import ssl


def verified_ssl_context():
    """Use a normal verified TLS context, including macOS Python CA bundles.

    Python.org's macOS builds may ship without the system CA bundle linked into
    the interpreter. Prefer certifi when it is already installed, then common
    system bundles. Never disable certificate verification.
    """
    candidates=[]
    try:
        import certifi
        candidates.append(certifi.where())
    except ImportError:
        pass
    candidates.extend(('/etc/ssl/cert.pem','/etc/ssl/certs/ca-certificates.crt'))
    for cafile in candidates:
        if cafile and Path(cafile).is_file():
            try:
                return ssl.create_default_context(cafile=cafile)
            except (OSError,ssl.SSLError):
                continue
    return ssl.create_default_context()


TLS_CONTEXT=verified_ssl_context()

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
KIT_URL='https://github.com/saleemmbayed-sketch/325ix-restoration-os/releases/download/rc15-3d-runtime/325ix_3d_assets_v1.zip'
REQUIRED_KIT=(
  'models/e30_reference_m3.glb',
  'vendor/three/build/three.module.js',
  'vendor/three/examples/jsm/controls/OrbitControls.js',
  'vendor/three/examples/jsm/loaders/GLTFLoader.js',
  'vendor/three/examples/jsm/utils/BufferGeometryUtils.js',
  'vendor/three/LICENSE',
  'vendor/meshopt_decoder.module.js',
  'vendor/meshoptimizer_LICENSE.md',
)

def install_kit(zip_bytes):
    """Extract only pinned expected runtime files after hashing each archive member.

    Existing owner files, workshop data and any source ZIP are untouched.
    """
    zf=zipfile.ZipFile(io.BytesIO(zip_bytes))
    manifest=json.loads(zf.read('ASSET_KIT_MANIFEST.json'))
    assert manifest['version']=='rc15-3d-runtime-v1','Unexpected asset kit'
    assert manifest['model']['git_blob_sha']==MODEL_GIT_BLOB,'Unexpected model source'
    for name in REQUIRED_KIT:
        if name not in manifest['files']:raise ValueError('Missing manifest entry: '+name)
        raw=zf.read(name)
        if sha256(raw).hexdigest()!=manifest['files'][name]['sha256']:
            raise ValueError('Asset hash mismatch: '+name)
        if name.startswith('models/'):
            blob=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if blob!=MODEL_GIT_BLOB or raw[:4]!=b'glTF':
                raise ValueError('Unexpected GLB identity: '+blob)
    # Only install manifest-checked files; no path traversal or arbitrary extraction.
    for name in REQUIRED_KIT:
        dst=ROOT/name
        dst.parent.mkdir(parents=True,exist_ok=True)
        tmp=dst.with_suffix(dst.suffix+'.tmp')
        tmp.write_bytes(zf.read(name))
        os.replace(tmp,dst)
        print('OK (verified kit):',name,flush=True)
    report={'status':'ready','source':'GitHub release '+KIT_URL,'model_git_blob':MODEL_GIT_BLOB,
        'files':manifest['files'],'installed_utc':datetime.now(timezone.utc).isoformat()}
    (ROOT/'models'/'asset-install-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0

JS_SUFFIX='.js'

def get(url):
    """Try two pinned source mirrors; never accept an unverified replacement model."""
    mirrors=[url]
    if url.startswith('https://cdn.jsdelivr.net/npm/'):
        mirrors.append(url.replace('https://cdn.jsdelivr.net/npm/','https://unpkg.com/',1))
    elif url.startswith('https://raw.githubusercontent.com/ahnuchen/auto-atlas/master/'):
        mirrors.append(url.replace('https://raw.githubusercontent.com/ahnuchen/auto-atlas/master/',
                       'https://github.com/ahnuchen/auto-atlas/raw/refs/heads/master/',1))
    last=None
    for candidate in mirrors:
        try:
            req=Request(candidate,headers={'User-Agent':'BMW-325iX-Local-Viewer/0.2 (licensed reference asset installer)'})
            with urlopen(req,timeout=22,context=TLS_CONTEXT) as res:return res.read()
        except (HTTPError,URLError,TimeoutError,OSError) as exc:
            last=exc
            print('  Source failed:',candidate,':',str(exc)[:120],flush=True)
    raise URLError('No pinned source mirror reachable: '+str(last))

def install(local_kit=None):
    if local_kit:
        try:return install_kit(Path(local_kit).expanduser().read_bytes())
        except (OSError,ValueError,AssertionError,KeyError,zipfile.BadZipFile) as e:
            print('FAILED: local asset kit:',e,file=sys.stderr)
            return 1
    if all((ROOT/n).is_file() and (ROOT/n).stat().st_size for n in REQUIRED_KIT):
        try:
            raw=(ROOT/'models/e30_reference_m3.glb').read_bytes()
            blob=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if blob==MODEL_GIT_BLOB:
                print('3D asset status: ready (verified cached kit)')
                return 0
        except OSError:pass
    print('Downloading one verified 3D asset kit from GitHub release…',flush=True)
    try:
        req=Request(KIT_URL,headers={'User-Agent':'BMW-325iX-Local-Viewer/0.3'})
        with urlopen(req,timeout=75,context=TLS_CONTEXT) as res:
            size=res.headers.get('Content-Length')
            if size and int(size)>12500000:raise ValueError('Kit exceeds 12.5 MB budget')
            zip_bytes=res.read(12500001)
        if len(zip_bytes)>12500000:raise ValueError('Kit exceeds 12.5 MB budget')
        return install_kit(zip_bytes)
    except (HTTPError,URLError,TimeoutError,ValueError,AssertionError,KeyError,OSError,zipfile.BadZipFile) as e:
        print('Kit download unavailable:',str(e)[:220],file=sys.stderr)
        print('Fallback: retrieving individually pinned public sources.',flush=True)
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

if __name__=='__main__':
    args=argparse.ArgumentParser(description='Install approved E30 3D model and renderer (one-time)')
    args.add_argument('--kit',help='Path to downloaded 325ix_3d_assets_v1.zip; avoids network')
    opt=args.parse_args()
    sys.exit(install(opt.kit))

