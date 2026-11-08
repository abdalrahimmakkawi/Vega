"""Combine the saved Vega components and actual PicoGK core into one scene.

The STL preserves multiple component solids. No implicit boolean union or
physical coupling is claimed. Coordinates remain millimetres at scale 1.
"""
from pathlib import Path
import hashlib
import struct
import sys
from .stl import validate_binary_stl


def export_assembly(run, root):
    assembly=run['candidates'][0].get('assembly',{})
    if assembly.get('status')!='concept_assembly':return None
    sys.path.insert(0,str(root/'.tools/python'))
    import numpy as np
    import json
    path=root/'data/native'/f'{run["id"]}.stl'
    raw=Path(str(path)+'.scene.stl').read_bytes()
    checks=json.loads(Path(str(path)+'.checks.json').read_text())
    validate_binary_stl(raw, checks['bodies'])
    core_hash=hashlib.sha256(raw).hexdigest()
    if core_hash!=run['artifact']['scene_sha256']:raise ValueError('Core scene identity mismatch')
    dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
    core=np.frombuffer(raw[84:],dtype=dtype).copy()
    core['vertices']+=np.array(assembly['core_placement']['translation_mm'],dtype='float32')
    points=core['vertices'].reshape(-1,3)
    sections=assembly['sections'][0]
    zs=[s['z_mm'] for s in sections]
    widths=np.interp(points[:,2],zs,[s['width_mm']/2 for s in sections])
    heights=np.interp(points[:,2],zs,[s['height_mm']/2 for s in sections])
    # Two millimetres accommodates the native core's one-mm voxel boundary.
    if run['requirements']['inlet_section']=='elliptical':
        radial=(points[:,0]/(widths+2))**2+(points[:,1]/(heights+2))**2
    else:
        radial=np.maximum(abs(points[:,0])/(widths+2),abs(points[:,1])/(heights+2))
    contained=bool(np.all(radial<=1) and points[:,2].min()>=zs[0]-2 and points[:,2].max()<=zs[-1]+2)
    if not contained:raise ValueError('Actual native core exceeds assembly bay; export rejected')
    shape=assembly['scene'];vertices=np.array(shape['vertices'],dtype='float32');indices=np.array(shape['triangles'],dtype='int32')
    extra=np.zeros(len(indices),dtype=dtype);extra['vertices']=vertices[indices]
    normals=np.cross(extra['vertices'][:,1]-extra['vertices'][:,0],extra['vertices'][:,2]-extra['vertices'][:,0])
    magnitudes=np.linalg.norm(normals,axis=1)
    if np.any(magnitudes<=0) or not np.all(np.isfinite(magnitudes)):raise ValueError('Invalid Vega assembly triangle')
    extra['normal']=normals/magnitudes[:,None]
    output=root/'data/native'/f'{run["id"]}.assembly.stl'
    if len(extra)+len(core)>4000000:
        raise ValueError('Combined mesh exceeds the four-million-triangle workbench budget; increase surface edge/chord tolerances or native voxel pitch')
    content=b'Vega connected multi-body concept assembly; NOT a fused solid'.ljust(80,b'\0')+struct.pack('<I',len(extra)+len(core))+extra.tobytes()+core.tobytes()
    original={part['id']:part for part in run['candidates'][0]['components']}
    components=list(assembly['components']);bodies=list(shape['bodies'])
    offset=assembly['core_placement']['translation_mm'][2]
    for body in checks['bodies']:
        identity=body['component_id'];part=original.get(identity,{'axial_mm':[0,run['candidates'][0]['geometry']['length_mm']],'role':'PicoGK core component'})
        bodies.append({**body,'component_id':'core_'+identity,'first_triangle':body['first_triangle']+len(extra),
                       'group':'core','color':[.74,.49,.29] if identity not in ('fuel_tank','oxidizer_tank') else [.53,.60,.64]})
        components.append({'id':'core_'+identity,'name':'Core / '+body['name'],
                           'axial_mm':[z+offset for z in part['axial_mm']],'role':part['role'],'group':'core'})
    validate_binary_stl(content, bodies)
    output.write_bytes(content)
    return {'backend':'Vega Geometry + PicoGK core','recipe_sha256':assembly['recipe_sha256'],
            'source_core_scene_sha256':core_hash,'stl_sha256':hashlib.sha256(content).hexdigest(),
            'triangles':len(extra)+len(core),'bodies':bodies,'components':components,
            'placement_check':{'native_core_vertices_inside_bay':contained,'tolerance_mm':2,'vertices_checked':len(points)},
            'scope':'One scene with multiple component solids and shared placement; not a boolean-unioned manufacturing export.'}


def assembly_artifact_valid(run,root):
    artifact=run.get('assembly_artifact')
    if not artifact or not run.get('artifact'):return False
    assembly=run['candidates'][0].get('assembly',{})
    path=root/'data/native'/f'{run["id"]}.assembly.stl'
    return (artifact['recipe_sha256']==assembly.get('recipe_sha256') and
            artifact['source_core_scene_sha256']==run['artifact']['scene_sha256'] and path.exists() and
            hashlib.sha256(path.read_bytes()).hexdigest()==artifact['stl_sha256'])
