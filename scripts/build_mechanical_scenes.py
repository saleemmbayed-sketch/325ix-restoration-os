#!/usr/bin/env python3
"""Create ORIGINAL illustrative mechanical 3D scenes for the BMW 325iX workshop.

No external 3D assets, no unverified dimensions, no protected imagery. These are
interactive visual orientation models, NOT engineering scans or fitment proof.
"""
from pathlib import Path
import hashlib, json, math
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'models'; OUT.mkdir(exist_ok=True)

def rgb(hex_color):
    h=hex_color.strip('#');return [int(h[i:i+2],16) for i in (0,2,4)]+[255]

palette={
 'body':('#26425a',.72,.28),'panel':('#34546b',.76,.27),'midnight':('#172a38',.3,.7),
 'black':('#1b222b',.26,.75),'rubber':('#21282c',.05,.95),'glass':('#9badb8',.2,.18),
 'steel':('#9eaab1',.88,.29),'aluminum':('#c4cbd0',.8,.32),'silver':('#e3e7e4',.78,.23),
 'bronze':('#a88f67',.64,.42),'cast':('#758189',.68,.66),'gold':('#ceaf67',.8,.25),
 'orange':('#e9a451',.45,.3),'red':('#cf6255',.25,.39),'blue':('#6f9aa7',.35,.29),
 'hose':('#2f4c57',.18,.72),'white':('#e6eef0',.12,.32),
}

class Model:
 def __init__(self,slug,description):
    self.scene=trimesh.Scene();self.slug=slug;self.description=description;self.components={};self.parts=0
 def add(self,id,label,part,kind='steel',system='engine',terms=None,notes=''):
    color,metal,rough=palette[kind]
    part.visual=trimesh.visual.TextureVisuals(material=PBRMaterial(baseColorFactor=rgb(color),metallicFactor=metal,roughnessFactor=rough))
    idx=self.components.get(id,{}).get('segments',0)+1
    name=f'MX:{id}:{idx}'
    self.scene.add_geometry(part,geom_name=name,node_name=name)
    self.components[id]={'id':id,'label':label,'system':system,'search_terms':terms or label.lower(),
       'notes':notes or 'Visual orientation only; use catalog evidence to identify the actual part.', 'segments':idx}
    self.parts+=1
 def box(self,id,label,center,size,kind='steel',**kwargs):
    mesh=trimesh.creation.box(extents=size);mesh.apply_translation(center);self.add(id,label,mesh,kind,**kwargs)
 def cyl(self,id,label,center,radius,height,axis='y',kind='steel',sections=24,**kwargs):
    mesh=trimesh.creation.cylinder(radius=radius,height=height,sections=sections)
    axisv=np.array({'x':[1,0,0],'y':[0,1,0],'z':[0,0,1]}[axis],dtype=float)
    transform=trimesh.geometry.align_vectors([0,0,1],axisv)
    if transform is not None:mesh.apply_transform(transform)
    mesh.apply_translation(center);self.add(id,label,mesh,kind,**kwargs)
 def sphere(self,id,label,center,radius,kind='steel',**kwargs):
    mesh=trimesh.creation.icosphere(subdivisions=2,radius=radius);mesh.apply_translation(center);self.add(id,label,mesh,kind,**kwargs)
 def pipe(self,id,label,points,radius,kind='steel',**kwargs):
    allparts=[]
    for a,b in zip(points[:-1],points[1:]):
     a=np.asarray(a,float);b=np.asarray(b,float);d=b-a;length=np.linalg.norm(d)
     if length<.0001:continue
     m=trimesh.creation.cylinder(radius=radius,height=length,sections=10)
     tr=trimesh.geometry.align_vectors([0,0,1],d/length)
     if tr is not None:m.apply_transform(tr)
     m.apply_translation((a+b)*.5);allparts.append(m)
    if allparts:self.add(id,label,trimesh.util.concatenate(allparts),kind,**kwargs)
 def spring(self,id,label,center,major_r=.16,height=.62,turns=5,kind='steel',**kwargs):
    x,y,z=center;n=110;points=[]
    for i in range(n):
     t=i/(n-1);angle=turns*t*math.tau
     points.append([x+major_r*math.cos(angle),y-height/2+height*t,z+major_r*math.sin(angle)])
    self.pipe(id,label,points,.019,kind,**kwargs)
 def torus(self,id,label,center,radius=.25,tube=.04,kind='steel',axis='z',**kwargs):
    n=42;m=9;verts=[];faces=[]
    for i in range(n):
     a=2*math.pi*i/n
     for j in range(m):
      b=2*math.pi*j/m; rr=radius+tube*math.cos(b)
      if axis=='z':v=(center[0]+rr*math.cos(a),center[1]+rr*math.sin(a),center[2]+tube*math.sin(b))
      elif axis=='y':v=(center[0]+rr*math.cos(a),center[1]+tube*math.sin(b),center[2]+rr*math.sin(a))
      else:v=(center[0]+tube*math.sin(b),center[1]+rr*math.cos(a),center[2]+rr*math.sin(a))
      verts.append(v)
    for i in range(n):
     for j in range(m):
      a=i*m+j;b=((i+1)%n)*m+j;c=((i+1)%n)*m+(j+1)%m;d=i*m+(j+1)%m;faces.extend([(a,b,c),(a,c,d)])
    self.add(id,label,trimesh.Trimesh(vertices=verts,faces=faces,process=False),kind,**kwargs)
 def save(self):
    out=OUT/(self.slug+'.glb');b=self.scene.export(file_type='glb');out.write_bytes(b)
    return {'slug':self.slug,'filename':'models/'+out.name,'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),
      'mesh_segments':self.parts,'components':list(self.components.values()),'description':self.description,
      'geometry_role':'ORIGINAL_INTERACTIVE_ILLUSTRATION_NOT_OEM_CAD'}

def engine():
 m=Model('ix_m20_engine_bay','M20 inline-six engine bay with front-hinged bonnet and inspectable systems')
 # First shell: boxed frame and front-hinged bonnet, a right-hand coordinate approximation.
 m.box('bay_floor','Engine bay lower tray',[0,-.6,0],[2.38,.12,3.65],'midnight')
 for side in (-1,1):
  m.box('engine_bay','Inner wing', [side*1.12,.27,-.1],[.19,1.18,3.38],'panel')
  m.box('engine_bay','Upper wing lip',[side*1.17,.91,.02],[.33,.12,3.7],'body')
  m.box('engine_bay','Chassis rail',[side*.85,-.36,.1],[.19,.17,3.5],'cast')
  m.cyl('strut_mount','Front strut top mount',[side*.91,.7,-.65],.29,.14,'y','steel',system='front_axle',terms='strut mount')
  m.cyl('strut_mount','Top mount bearing',[side*.91,.8,-.65],.12,.08,'y','rubber',system='front_axle',terms='strut mount bearing')
 m.box('bulkhead','Firewall',[0,.45,-1.6],[2.42,1.95,.15],'black',terms='bulkhead')
 m.box('radiator_support','Radiator support panel',[0,.21,1.68],[2.36,.58,.11],'body',terms='radiator')
 m.box('bonnet','Front-hinged bonnet',[0,1.28,0],[2.48,.075,3.7],'body',system='bodywork',terms='hood bonnet')
 for side in (-1,1):m.box('bonnet','Bonnet inner reinforcement',[side*.88,1.225,.0],[.045,.055,3.42],'steel',system='bodywork',terms='hood bonnet')
 m.box('engine_block','Cast iron M20 block',[0,-.17,-.13],[.68,.56,2.38],'cast',terms='engine block')
 m.box('oil_pan','Engine oil sump',[0,-.64,-.08],[.87,.3,1.92],'black',terms='oil pan sump')
 m.box('cylinder_head','Cylinder head',[0,.25,-.16],[.77,.31,2.18],'aluminum',terms='cylinder head')
 m.box('valve_cover','M20 rocker / valve cover',[0,.53,-.14],[.72,.29,2.02],'bronze',terms='valve cover')
 # Distinct M20 cover ribs and oil-cap detail.
 for z in np.linspace(-.95,.67,9):m.box('valve_cover','Cover cooling ribs',[0,.692,float(z)],[.63,.024,.038],'silver',terms='valve cover')
 m.cyl('oil_filler_cap','Oil filler cap',[-.18,.74,-.88],.102,.08,'y','black',terms='oil filler cap')
 for i,z in enumerate(np.linspace(-.9,.75,6)):
  m.cyl('spark_plugs','Spark-plug boot',[-.24,.695,float(z)],.047,.095,'y','black',terms='spark plug',notes='Six visually distinct M20 ignition positions; not engineering geometry')
  m.pipe('ignition_wiring','HT leads',[[-.24,.74,float(z)],[-.53,.83,float(z)-.05],[-.7,.88,-1.03]],.018,'hose',system='engine_electrical_system',terms='ignition lead distributor')
 # Six-bend intake runners from intake plenum into the cylinder head.
 m.box('intake_plenum','Intake manifold plenum',[.63,.54,-.06],[.53,.29,1.9],'aluminum',terms='intake manifold')
 for z in np.linspace(-.94,.78,6):
  m.pipe('intake_runners','Six M20 intake runners',[[.62,.54,float(z)],[.92,.46,float(z)+.09],[.98,.21,float(z)+.10],[.67,.14,float(z)+.12],[.38,.25,float(z)+.12]],.073,'aluminum',terms='intake manifold')
 m.cyl('throttle_body','Throttle body',[.73,.55,1.01],.20,.32,'z','silver',terms='throttle body')
 m.pipe('intake_hose','Intake rubber boot',[[.74,.56,1.03],[.97,.6,1.26],[.84,.57,1.49]],.17,'rubber',terms='air intake rubber boot')
 m.box('airbox','Air filter housing',[.69,.35,1.36],[.5,.38,.6],'black',terms='air filter')
 m.pipe('fuel_rail','Fuel injector rail',[[.29,.48,-1.12],[.3,.49,1.02]],.034,'gold',system='fuel_preparation_system',terms='fuel rail')
 for z in np.linspace(-.94,.78,6):m.cyl('injectors','Fuel injectors',[.35,.42,float(z)],.042,.17,'x','gold',system='fuel_preparation_system',terms='fuel injector')
 # Exhaust manifold on opposite side.
 for z in np.linspace(-.91,.8,6):
  m.pipe('exhaust_manifold','Exhaust manifold tubes',[[-.36,.18,float(z)],[-.58,-.05,float(z)+.04],[-.72,-.30,float(z)+.1],[-.78,-.46,.11]],.053,'cast',system='exhaust_system',terms='exhaust manifold')
 m.box('timing_cover','Front timing-belt cover',[0,.11,1.15],[.67,.72,.22],'black',terms='timing belt cover')
 m.cyl('crank_pulley','Crankshaft pulley',[0,-.34,1.35],.25,.105,'z','steel',terms='crank pulley')
 m.cyl('cam_pulley','Cam pulley / timing',[0,.4,1.34],.21,.085,'z','silver',terms='camshaft pulley')
 m.cyl('alternator','Alternator',[.48,-.28,1.07],.17,.38,'z','steel',system='engine_electrical_system',terms='alternator')
 m.cyl('water_pump','Water pump',[0,.02,1.42],.14,.15,'z','aluminum',system='radiator',terms='water pump')
 m.cyl('fan','Cooling fan hub',[0,.04,1.66],.13,.12,'z','cast',system='radiator',terms='fan clutch')
 for k in range(7):
  a=2*math.pi*k/7
  m.box('fan','Radiator fan blade',[.23*math.cos(a),.04+.23*math.sin(a),1.71],[.32,.085,.03],'silver',system='radiator',terms='cooling fan')
 m.box('radiator','Engine radiator',[0,.07,1.76],[1.64,1.01,.14],'midnight',system='radiator',terms='radiator')
 for x in np.linspace(-.73,.73,18):m.box('radiator','Radiator fins',[float(x),.08,1.85],[.025,.82,.008],'steel',system='radiator',terms='radiator')
 m.pipe('coolant_hoses','Upper coolant hose',[[.37,.4,.91],[.72,.53,1.19],[.54,.57,1.66]],.071,'hose',system='radiator',terms='radiator coolant hose')
 m.pipe('coolant_hoses','Lower coolant hose',[[-.49,-.22,1.04],[-.78,-.1,1.39],[-.45,-.34,1.72]],.061,'hose',system='radiator',terms='radiator coolant hose')
 m.box('battery','12 V battery',[-.9,.24,1.17],[.39,.37,.65],'black',system='vehicle_electrical_system',terms='battery')
 m.box('fuse_box','Fuse/relay box',[.85,.28,-1.16],[.36,.28,.54],'black',system='vehicle_electrical_system',terms='fuse relay box')
 m.cyl('coolant_expansion','Coolant expansion vessel',[-.92,.21,-1.1],.19,.48,'y','white',system='radiator',terms='coolant expansion tank')
 return m.save()

def axle():
 m=Model('ix_front_axle_workshop','Explorable AWD front axle / steering / strut technical illustration')
 m.box('subframe','Front axle carrier',[0,-.34,0],[2.32,.22,.42],'cast',system='front_axle',terms='front axle carrier subframe')
 m.box('steering_rack','Steering rack housing',[0,-.05,-.36],[1.84,.14,.18],'silver',system='steering',terms='steering rack')
 m.cyl('front_differential','325iX front differential casing',[.34,-.43,.35],.39,.56,'x','cast',system='front_axle',terms='front axle differential')
 for side in (-1,1):
  x=side*1.12
  m.cyl('strut_tube','Front strut tube',[x,.24,0],.11,1.45,'y','steel',system='front_axle',terms='strut shock absorber')
  m.spring('coil_spring','MacPherson coil spring',[x,.58,0],.21,.67,5,'blue',system='front_axle',terms='coil spring')
  m.cyl('upper_mount','Front upper strut mount',[x,1.02,0],.22,.11,'y','cast',system='front_axle',terms='strut top mount')
  m.cyl('hub','Front hub / AWD wheel flange',[x,-.29,.16],.27,.28,'x','steel',system='front_axle',terms='wheel hub bearing')
  m.torus('brake_disc','Front brake disc',[x+side*.18,-.29,.16],.31,.055,'silver','x',system='brakes',terms='brake disc')
  m.box('caliper','Brake caliper',[x+side*.20,-.14,-.04],[.23,.28,.24],'red',system='brakes',terms='brake caliper')
  m.pipe('control_arm','Wishbone control arm',[[side*.58,-.53,-.06],[side*.89,-.63,.24],[x,-.38,.2]],.082,'steel',system='front_axle',terms='wishbone control arm')
  m.sphere('ball_joint','Front ball joint',[x,-.38,.2],.095,'gold',system='front_axle',terms='ball joint')
  m.pipe('tie_rod','Steering tie rod',[[side*.69,-.06,-.36],[x,-.25,-.05]],.05,'steel',system='steering',terms='tie rod')
  m.pipe('cv_shaft','Front AWD driveshaft',[[side*.49,-.45,.35],[x,-.28,.18]],.078,'steel',system='front_axle',terms='front axle shaft CV joint')
  for xx in (side*.64,side*.95):m.cyl('cv_boots','CV joint boot',[xx,-.37,.26],.13,.16,'x','rubber',system='front_axle',terms='CV joint axle shaft')
 return m.save()

def transfer():
 m=Model('ix_awd_driveline_workshop','Illustrative 325iX AWD transfer/driveshaft arrangement')
 m.box('transfer_case','AWD transfer housing',[0,0,0],[1.13,.72,1.28],'cast',system='transfer_box_electric_gearbox',terms='transfer case')
 for x in (-.44,.44):
  m.cyl('case_bolt','Transfer housing fastener',[x,.39,.3],.046,.08,'y','steel',system='transfer_box_electric_gearbox',terms='transfer case bolts')
 m.cyl('transfer_output','Transfer output flange',[0,0,.75],.25,.12,'z','silver',system='transfer_box_electric_gearbox',terms='transfer output flange')
 m.cyl('transfer_output','Rear output flange',[0,0,-.77],.21,.12,'z','silver',system='transfer_box_electric_gearbox',terms='transfer output flange')
 m.pipe('front_prop','Front propeller shaft',[[0,0,.79],[0,-.08,2.27]],.10,'steel',system='drive_shaft',terms='front propeller shaft')
 m.pipe('rear_prop','Rear propeller shaft',[[0,0,-.81],[0,.01,-2.38]],.10,'steel',system='drive_shaft',terms='rear propeller shaft')
 m.cyl('front_diff','Front differential shell',[0,-.08,2.67],.42,.61,'z','cast',system='front_axle',terms='front differential')
 m.cyl('rear_diff','Rear differential shell',[0,.01,-2.72],.45,.68,'z','cast',system='rear_axle',terms='rear differential')
 for z in (-2.73,2.67):
  for side in (-1,1):
   m.pipe('axle_halfshafts','Half-shaft to wheel',[[-.35*side,-.09,z],[side*1.43,-.08,z]],.085,'steel',system='front_axle' if z>0 else 'rear_axle',terms='axle half shaft CV')
   m.cyl('cv_joints','CV joint casing',[side*1.34,-.08,z],.17,.19,'x','rubber',system='front_axle' if z>0 else 'rear_axle',terms='CV joint axle')
 m.cyl('case_mount','Transfer case mounting bush',[.58,-.37,.0],.16,.22,'x','rubber',system='transfer_box_electric_gearbox',terms='transfer case mount')
 m.torus('transfer_viscous','Transfer unit conceptual clutch pack',[0,.04,.07],.30,.035,'bronze','z',system='transfer_box_electric_gearbox',terms='viscous coupling')
 return m.save()

if __name__=='__main__':
 info=[engine(),axle(),transfer()]
 data={'title':'Original illustrative 3D mechanic scenes for BMW 325iX POC','revision':'RC19',
 'geometry_notice':'Original stylized mechanical visualizations; not scans, drawings or dimensionally verified OEM geometry.',
 'scenes':info}
 (ROOT/'mechanical_index.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps([{'name':x['slug'],'components':len(x['components']),'segments':x['mesh_segments'],'KB':x['size']//1024} for x in info],indent=2))
