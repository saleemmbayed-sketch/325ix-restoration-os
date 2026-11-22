#!/usr/bin/env python3
"""Render labeled 2D previews of the original mechanical GLBs for offline fallback."""
from pathlib import Path
import trimesh,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import json
root=Path(__file__).resolve().parents[1]
index_path=root/'mechanical_index.json';data=json.loads(index_path.read_text())
(root/'models'/'previews').mkdir(exist_ok=True)
for item in data['scenes']:
 scene=trimesh.load(root/item['filename']);fig=plt.figure(figsize=(11.8,6.2),dpi=115,facecolor='#0a1d2d');ax=fig.add_axes((.02,.015,.96,.97),projection='3d',facecolor='#0a1d2d')
 filtered=[g for n,g in scene.geometry.items() if n.split(':')[1] not in ('bonnet','engine_bay','bay_floor','bulkhead','radiator_support')];all_verts=np.vstack([g.vertices for g in filtered]);mins=all_verts.min(0);maxs=all_verts.max(0);center=(mins+maxs)/2
 radius=max(maxs-mins)*.58
 light=np.array([.46,.84,.5]);light/=np.linalg.norm(light)
 for name,geom in scene.geometry.items():
  if name.split(':')[1] in ('bonnet','engine_bay','bay_floor','bulkhead','radiator_support'):continue  # Expose engine components in preview; shell exists in interactive model.
  vertices=geom.vertices;faces=geom.faces
  normals=geom.face_normals
  col=geom.visual.material.baseColorFactor[:3] if geom.visual.material else (140,175,190)
  if max(col)<=1:col=np.array(col)*255
  col=np.array(col)/255
  shades=np.clip(.38+.64*np.maximum(0,normals@light),.22,1.0)
  colors=np.column_stack((np.clip(col[None,:]*shades[:,None]+.035,0,1),np.ones(len(faces))))
  poly=Poly3DCollection(vertices[faces][:,:,[0,2,1]],facecolors=colors,edgecolors='none',linewidths=0,zsort='average')
  ax.add_collection3d(poly)
 ax.set(xlim=(center[0]-radius,center[0]+radius),ylim=(center[2]-radius,center[2]+radius),zlim=(center[1]-radius*.66,center[1]+radius*.66));ax.set_axis_off();ax.view_init(elev=39,azim=-58)
 ax.set_box_aspect([1,1,.67],zoom=1.25)
 output=root/'models'/'previews'/(item['slug']+'.webp');fig.savefig(output,format='webp',dpi=115,facecolor=fig.get_facecolor(),pil_kwargs={'quality':90});plt.close(fig)
 item['preview']='models/previews/'+output.name
 print(item['slug'],output.stat().st_size)
index_path.write_text(json.dumps(data,indent=2)+'\n')
