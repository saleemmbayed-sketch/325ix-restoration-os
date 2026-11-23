#!/usr/bin/env python3
"""Offline contracts for read-only V4 manifest, file and catalog integrity."""
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import hashlib
import json
import sqlite3
import struct
import tempfile
import urllib.error
import urllib.request
import zlib

from app import App, audit_v4_runtime, check_image_mime, inspect_v4_asset, load_v4_asset_manifest


def png_fixture(width=24,height=24):
    def chunk(tag,data):
        return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
    scan=b''.join(bytes((0,))+bytes(v for x in range(width) for v in (
        (x*17+y*5)%256,(x*11+y*19)%256,(x*23+y*7)%256)) for y in range(height))
    signature=bytes((137,80,78,71,13,10,26,10))
    return (signature+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+
            chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))

def write_catalog(path, asset):
    with sqlite3.connect(path) as db:
        db.execute('''CREATE TABLE image_asset(
            id TEXT PRIMARY KEY,source_url TEXT,local_file TEXT,status TEXT,sha256 TEXT,
            width INTEGER,height INTEGER)''')
        db.execute('''CREATE TABLE assembly(
            id TEXT PRIMARY KEY,group_name TEXT,title TEXT,source_url TEXT,source_status TEXT)''')
        db.execute('''CREATE TABLE figure_occurrence(
            id TEXT PRIMARY KEY,assembly_id TEXT,image_asset_id TEXT,source_url TEXT)''')
        db.execute('''CREATE TABLE part_record(
            id TEXT PRIMARY KEY,assembly_id TEXT,part_number TEXT,callout TEXT,description TEXT,
            quantity TEXT,date_raw TEXT,supplement TEXT)''')
        db.execute('INSERT INTO image_asset VALUES(?,?,?,?,?,?,?)',(
            asset['asset_id'],asset['url'],asset['local_file'],asset['status'],asset['sha256'],
            asset.get('width_px'),asset.get('height_px')))
        db.execute('INSERT INTO assembly VALUES(?,?,?,?,?)',(
            'A-fixture','front_axle','Offline test assembly','https://catalog.example/assembly','DOWNLOADED'))
        db.execute('INSERT INTO figure_occurrence VALUES(?,?,?,?)',(
            'FIG-fixture','A-fixture',asset['asset_id'],asset['url']))


def main():
    with tempfile.TemporaryDirectory(prefix='ix-v4-integrity-') as temp:
        root=Path(temp)/'v4';images=root/'01_DIAGRAM_IMAGES';manifest_dir=root/'03_MANIFESTS'
        images.mkdir(parents=True);manifest_dir.mkdir(parents=True)
        raw=png_fixture()
        local_file='01_DIAGRAM_IMAGES/fixture.png'
        (root/local_file).write_bytes(raw)
        asset={'asset_id':'IMG-'+'a'*16,'url':'https://catalog.example/figure.png',
            'local_file':local_file,'status':'DOWNLOADED','sha256':hashlib.sha256(raw).hexdigest(),
            'bytes':len(raw),'mime':'image/png','width_px':24,'height_px':24}
        canonical=manifest_dir/'image_assets.jsonl'
        canonical.write_text(json.dumps(asset)+'\n',encoding='utf-8')
        # An empty reduced local manifest must not shadow a usable canonical manifest.
        (manifest_dir/'image_assets_local.jsonl').write_text('',encoding='utf-8')
        assets,selected=load_v4_asset_manifest(root)
        assert selected=='image_assets.jsonl' and assets[asset['asset_id']]==asset
        catalog=Path(temp)/'catalog.sqlite3';write_catalog(catalog,asset)
        before=hashlib.sha256(catalog.read_bytes()).hexdigest()

        report=audit_v4_runtime(root,assets,catalog)
        assert report['integrity_status']=='VERIFIED',report
        assert report['catalog_integrity']=='VERIFIED' and report['catalog_assets']==1
        assert report['manifest_assets']==1 and report['reported_downloaded_assets']==1
        assert report['images_present_locally']==1 and report['images_hash_verified']==1
        checked=inspect_v4_asset(root,asset,include_bytes=True)
        assert checked['state']=='VERIFIED' and checked['raw']==raw and checked['mime']=='image/png'
        assert check_image_mime(images/'fixture.jpg',asset,raw)==(None,'MIME_MISMATCH')

        bad_mime={**asset,'mime':'image/jpeg'}
        report=audit_v4_runtime(root,{asset['asset_id']:bad_mime},catalog)
        assert report['integrity_status']=='MISMATCH' and report['images_mime_mismatches']==1,report

        no_mime={k:v for k,v in asset.items() if k!='mime'}
        report=audit_v4_runtime(root,{asset['asset_id']:no_mime},catalog)
        assert report['integrity_status']=='INCOMPLETE' and report['images_mime_unverifiable']==1,report

        no_size={k:v for k,v in asset.items() if k!='bytes'}
        report=audit_v4_runtime(root,{asset['asset_id']:no_size},catalog)
        assert report['integrity_status']=='INCOMPLETE' and report['images_size_unverifiable']==1,report
        assert inspect_v4_asset(root,no_size)['state']=='SIZE_UNVERIFIABLE'

        http=ThreadingHTTPServer(('127.0.0.1',0),App);http.catalog=catalog;http.multimodal=catalog
        http.v4root=root;http.assets={asset['asset_id']:asset}
        worker=Thread(target=http.serve_forever,daemon=True);worker.start()
        endpoint=f'http://127.0.0.1:{http.server_port}/api/diagram?asset={asset["asset_id"]}'
        def get_diagram():
            try:
                with urllib.request.urlopen(endpoint,timeout=5) as response:
                    return response.status,response.headers,response.read()
            except urllib.error.HTTPError as exc:
                return exc.code,exc.headers,json.loads(exc.read())
        try:
            code,headers,body=get_diagram()
            assert code==200 and headers.get_content_type()=='image/png' and body==raw
            with urllib.request.urlopen(f'http://127.0.0.1:{http.server_port}/api/assembly?id=A-fixture',timeout=5) as response:
                assembly=json.loads(response.read())
            assert assembly['figures'][0]['local_available'] is True
            assert assembly['figures'][0]['local_integrity_state']=='VERIFIED'
            rejected=(
                ({**asset,'mime':'image/jpeg'},'MIME_MISMATCH'),
                ({k:v for k,v in asset.items() if k!='mime'},'MIME_UNVERIFIABLE'),
                ({k:v for k,v in asset.items() if k!='bytes'},'SIZE_UNVERIFIABLE'),
                ({**asset,'local_file':'../../outside.png'},'INVALID_PATH'),
            )
            for record,state in rejected:
                http.assets[asset['asset_id']]=record
                code,_,body=get_diagram()
                assert code==404 and body['integrity_state']==state,(state,code,body)
            wrong_ext=images/'fixture.jpg';wrong_ext.write_bytes(raw)
            http.assets[asset['asset_id']]={**asset,'local_file':'01_DIAGRAM_IMAGES/fixture.jpg'}
            code,_,body=get_diagram()
            assert code==404 and body['integrity_state']=='MIME_MISMATCH',(code,body)
            http.assets[asset['asset_id']]=asset
            (root/local_file).write_bytes(raw[:-1]+bytes((raw[-1]^1,)))
            code,_,body=get_diagram()
            assert code==404 and body['integrity_state']=='SHA256_MISMATCH',(code,body)
            with urllib.request.urlopen(f'http://127.0.0.1:{http.server_port}/api/assembly?id=A-fixture',timeout=5) as response:
                assembly=json.loads(response.read())
            assert assembly['figures'][0]['local_available'] is False
            assert assembly['figures'][0]['local_integrity_state']=='SHA256_MISMATCH'
            (root/local_file).write_bytes(raw)
        finally:
            http.shutdown();http.server_close();worker.join(timeout=3)

        missing_catalog_field={k:v for k,v in asset.items() if k!='url'}
        report=audit_v4_runtime(root,{asset['asset_id']:missing_catalog_field},catalog)
        assert report['catalog_integrity']=='MISMATCH' and report['catalog_metadata_mismatches']==1,report

        bad_hash={**asset,'sha256':'0'*64}
        report=audit_v4_runtime(root,{asset['asset_id']:bad_hash},catalog)
        assert report['integrity_status']=='MISMATCH' and report['images_sha256_mismatches']==1,report

        bad_size={**asset,'bytes':len(raw)+1}
        report=audit_v4_runtime(root,{asset['asset_id']:bad_size},catalog)
        assert report['integrity_status']=='MISMATCH' and report['images_size_mismatches']==1,report

        (root/local_file).unlink()
        report=audit_v4_runtime(root,assets,catalog)
        assert report['integrity_status']=='INCOMPLETE' and report['images_missing_locally']==1,report
        (root/local_file).write_bytes(raw)

        traversal={**asset,'local_file':'../../outside.webp'}
        report=audit_v4_runtime(root,{asset['asset_id']:traversal},catalog)
        assert report['integrity_status']=='MISMATCH' and report['images_unsafe_paths']==1,report
        assert inspect_v4_asset(root,traversal)['state']=='INVALID_PATH'
        outside=Path(temp)/'outside.png';outside.write_bytes(raw)
        (images/'escape.png').symlink_to(outside)
        escaped_symlink={**asset,'local_file':'01_DIAGRAM_IMAGES/escape.png'}
        assert inspect_v4_asset(root,escaped_symlink)['state']=='INVALID_PATH'

        pending={**asset,'status':'NOT_DOWNLOADED','local_file':''}
        report=audit_v4_runtime(root,{asset['asset_id']:pending})
        assert report['integrity_status']=='INCOMPLETE' and report['not_reported_downloaded_assets']==1
        assert report['images_hash_verified']==0

        changed={**asset,'url':'https://catalog.example/changed.webp'}
        report=audit_v4_runtime(root,{asset['asset_id']:changed},catalog)
        assert report['catalog_integrity']=='MISMATCH' and report['catalog_metadata_mismatches']==1

        report=audit_v4_runtime(root,{},catalog)
        assert report['catalog_asset_ids_missing_from_manifest']==1
        assert report['catalog_integrity']=='MANIFEST_MISSING'
        disconnected=audit_v4_runtime(None,{},catalog)
        assert not disconnected['connected'] and disconnected['integrity_status']=='NOT_CONNECTED'
        assert disconnected['catalog_assets']==1 and disconnected['catalog_integrity']=='NOT_CONNECTED'

        canonical.write_text(json.dumps(asset)+'\n'+json.dumps(asset)+'\n',encoding='utf-8')
        try:load_v4_asset_manifest(root)
        except ValueError as exc:assert 'Duplicate V4 image asset ID' in str(exc)
        else:raise AssertionError('Duplicate manifest asset IDs must be rejected')
        assert hashlib.sha256(catalog.read_bytes()).hexdigest()==before,'The catalog must remain read-only'

    print('PASS: V4 manifest/catalog reconciliation, contained paths, required size/SHA-256/MIME checks, and verified-only diagram serving')


if __name__=='__main__':
    main()
