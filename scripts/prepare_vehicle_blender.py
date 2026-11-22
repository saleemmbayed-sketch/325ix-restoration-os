#!/usr/bin/env python3
"""Blender 4.x background import -> named vehicle hierarchy -> assembled GLB.

Run using Blender's Python (not system Python):
  blender -b --python scripts/prepare_vehicle_blender.py -- --input car.fbx --output models/e30_source_prepared.glb --mapping models/assembly_map.json

Only splits loose parts with --split-loose; authored mesh names always take precedence.
Never infers exact BMW OEM numbers, suspension geometry, dimensions or fitment.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROLE_PATTERNS = (
    ('Hood', r'hood|bonnet|motorhaube'),
    ('Roof', r'roof|dach'),
    ('Doors_Left', r'left.?door|door.?l|tuer.?l'),
    ('Doors_Right', r'right.?door|door.?r|tuer.?r'),
    ('Wheels_Left', r'left.?wheel|wheel.?l|left.?tire|left.?tyre'),
    ('Wheels_Right', r'right.?wheel|wheel.?r|right.?tire|right.?tyre'),
    ('Front_Bumper', r'front.?bumper|bumper.?front'),
    ('Rear_Bumper', r'rear.?bumper|bumper.?rear'),
    ('Engine_Assembly', r'engine|motor|piston|intake|radiator.?fan|head.?cover|throttle'),
    ('Suspension', r'strut|suspension|spring|knuckle|arm|shock|brake|axle'),
    ('Steering', r'steering|tie.?rod|rack'),
    ('Drivetrain', r'differential|transfer|prop.?shaft|gearbox|transmission|driveshaft'),
    ('Interior', r'dashboard|cockpit|seat|console|steering.?wheel|pedal'),
    ('Chassis', r'subframe|frame|chassis|floor.?pan|underbody'),
    ('Electrical', r'battery|wiring|headlight|taillight|alternator'),
)

def arguments():
    cli=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--mapping',help='Optional JSON object: mesh name -> assembly group')
    parser.add_argument('--split-loose',action='store_true',help='Split disconnected geometry; may create many fragments')
    return parser.parse_args(cli)

def choose_role(name,explicit):
    if name in explicit:return explicit[name]
    for role,pattern in ROLE_PATTERNS:
        if re.search(pattern,name,re.I):return role
    return 'Body_Exterior'  # Unknown means visually unclassified, not OEM approved.

def move_without_jumping(obj,parent):
    world=obj.matrix_world.copy()
    obj.parent=parent
    obj.matrix_world=world

def make_empty(name,parent=None,location=None):
    ob=bpy.data.objects.new(name,None)
    bpy.context.scene.collection.objects.link(ob)
    if parent:ob.parent=parent
    if location is not None:ob.matrix_world.translation=location
    return ob

def center_world(ob):
    # Closed geometry uses Blender's origin-of-mass operator; open body panels use surface median.
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    try:bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS',center='MEDIAN')
    except RuntimeError:bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY',center='MEDIAN')
    return ob.matrix_world.translation.copy()

def main():
    args=arguments();src=Path(args.input).expanduser().resolve();out=Path(args.output).expanduser().resolve()
    if src.suffix.lower() not in ('.glb','.gltf','.fbx','.usd','.usdc','.usda'):
        raise ValueError('Supported Blender imports: GLB, glTF, FBX, USD')
    if not src.is_file():raise FileNotFoundError(src)
    explicit=json.loads(Path(args.mapping).read_text()) if args.mapping else {}
    if not isinstance(explicit,dict):raise ValueError('mapping must be a JSON object')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    if src.suffix.lower() in ('.glb','.gltf'):bpy.ops.import_scene.gltf(filepath=str(src))
    elif src.suffix.lower()=='.fbx':bpy.ops.import_scene.fbx(filepath=str(src))
    else:bpy.ops.wm.usd_import(filepath=str(src))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    if not meshes:raise ValueError('No mesh objects in source model')
    if args.split_loose:
        for mesh in list(meshes):
            bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);bpy.context.view_layer.objects.active=mesh
            bpy.ops.mesh.separate(type='LOOSE')
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    group_for={o.name:choose_role(o.name,explicit) for o in meshes}
    group_centers={}
    for ob in meshes:center_world(ob)
    for role in set(group_for.values()):
        group_objects=[o for o in meshes if group_for[o.name]==role]
        # Volume/density data is unavailable: use geometric centroid for an assembly pivot.
        group_centers[role]=sum((o.matrix_world.translation for o in group_objects),Vector())/len(group_objects)
    root=make_empty('E30_Vehicle_Root',location=Vector((0,0,0)))
    for role in sorted(group_centers):
        group=make_empty('Assembly:'+role,parent=root,location=group_centers[role])
        for ob in [o for o in meshes if group_for[o.name]==role]:
            component=make_empty('Component:'+ob.name,parent=group,location=ob.matrix_world.translation.copy())
            move_without_jumping(ob,component)
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for ob in root.children_recursive:ob.select_set(True)
    bpy.context.view_layer.objects.active=root
    out.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_yup=True)
    report={'source':str(src),'output':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
            'mesh_count':len(meshes),'assembly_counts':{r:sum(v==r for v in group_for.values()) for r in sorted(set(group_for.values()))},
            'unclassified':[n for n,g in group_for.items() if g=='Body_Exterior'],
            'caution':'Pivot = mesh mass center where Blender can compute it; mixed assembly centroid otherwise. Geometry, identity, dimensions and fitment not automatically verified.'}
    (out.with_suffix('.manifest.json')).write_text(json.dumps(report,indent=2))
    print('PREPARED 3D HIERARCHY',json.dumps(report,indent=2))

if __name__=='__main__':main()
