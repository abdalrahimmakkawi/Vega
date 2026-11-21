"""Add independently audited 0.1 mm architecture components to a checked base.

All hot-section and machinery parts are non-firing representations. Placement
is for an expanded review assembly, not a validated fluid circuit or engine.
"""
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zipfile

from .demonstrator import ROOT
from .print_export import DOTNET,DLL,clean_native,inspect_mesh,append_smooth_normals
from .print_export import export_print_mesh
from .analysis import analyze
from vega_geometry import fingerprint
import numpy as np
import trimesh

BASE_RUN='168a31ccb4ec4a1d80532a3d54228100'


def modules():
    return [
        dict(id='pre-burner',name='Pre-burner',kind='can',center_mm=[-38,0],profile=[[74,6],[86,6]],wall=1.4,port_z=80,outer_radius=6,color=[.79,.38,.22],reference='A13'),
        dict(id='re-heater',name='Re-heater',kind='can',center_mm=[-38,0],profile=[[104,7],[118,7]],wall=1.4,port_z=111,outer_radius=7,color=[.83,.58,.24],reference='A14'),
        dict(id='drive-turbine',name='Drive turbine',kind='rotor',center_mm=[0,0],profile=[[124,5],[132,5]],wall=2,hub_outer=5,tip_radius=15,blade_count=12,z_start=124,z_end=132,color=[.59,.51,.69],reference='A15'),
        dict(id='regenerators',name='Paired regenerators',kind='regenerator',center_mm=[-54,0],profile=[[48,5.2],[74,5.2]],wall=1.4,color=[.45,.64,.46],reference='A16'),
        dict(id='heat-shield',name='Heat shield · open inspection sector',kind='shield',center_mm=[0,0],profile=[[122,25],[148,25],[176,27]],wall=1.4,color=[.37,.42,.47],reference='A17'),
        dict(id='bell-chamber',name='Bell nozzle + thrust chamber representation',kind='bell',center_mm=[0,0],profile=[[138,11],[148,11],[155,5],[158,5]]+[[z,5+15*(3*t*t-2*t*t*t)] for z in range(159,186) for t in [(z-158)/27]],wall=1.6,color=[.73,.48,.33],reference='A18'),
        dict(id='ramjet-burner',name='Spill-duct ramjet burner representation',kind='can',center_mm=[31,18],profile=[[96,6],[113,6],[118,5]],wall=1.4,port_z=104,outer_radius=6,color=[.75,.42,.37],reference='A19'),
        dict(id='lox-pump',name='LOX pump representation',kind='pump',center_mm=[38,-15],profile=[[94,6],[106,6]],wall=1.5,port_z=100,outer_radius=6,color=[.28,.57,.81],reference='A20'),
        dict(id='spill-duct',name='Spill duct',kind='duct',center_mm=[31,18],profile=[[12,7],[20,5],[96,5]],wall=1.4,color=[.46,.67,.66],reference='A21'),
        dict(id='air-compressor',name='Air turbo-compressor · 0.1 mm',kind='rotor',center_mm=[0,0],profile=[[50,12],[60,12]],wall=3,hub_outer=12,tip_radius=21,blade_count=8,z_start=50,z_end=60,color=[.49,.53,.70],reference='A04')]


def profile_mesh(part):
    rows=np.asarray(part['profile'],float)
    if rows.ndim!=2 or rows.shape[1]!=2 or not np.isfinite(rows).all() or not np.all(np.diff(rows[:,0])>0) or part['wall']<=0 or np.any(rows[:,1]<=part['wall']):
        raise ValueError('Invalid annular input profile')
    outline=np.concatenate([rows[:,[1,0]],np.column_stack([rows[::-1,1]-part['wall'],rows[::-1,0]])])
    outline=np.vstack([outline,outline[0]])
    mesh=trimesh.creation.revolve(outline,sections=96)
    if mesh.volume<0:mesh.invert()
    if not mesh.is_volume:raise ValueError('Input profile is not a closed solid: '+part['id'])
    if part['kind']=='regenerator':
        left=mesh.copy();right=mesh.copy();left.apply_translation([part['center_mm'][0],-10,0]);right.apply_translation([part['center_mm'][0],10,0]);return trimesh.util.concatenate([left,right])
    mesh.apply_translation([*part['center_mm'],0])
    return mesh


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def checked_base():
    base=ROOT/'data/prints'/BASE_RUN
    manifest=json.loads((base/'manifest.json').read_text())
    state=json.loads((ROOT/'data/print-jobs'/(BASE_RUN+'.json')).read_text())
    if state['status']!='complete':raise ValueError('The accepted base assembly is unavailable')
    return base,manifest


def display_mesh(mesh,target=50000):
    """Decimate display only; downloads and native audits retain full resolution."""
    if len(mesh.faces)<=target:return mesh.copy(),False
    for budget in sorted({target,min(len(mesh.faces),target*2),min(len(mesh.faces),target*4),min(len(mesh.faces),target*8)}):
        if budget>=len(mesh.faces):break
        candidate=mesh.simplify_quadric_decimation(face_count=budget,aggression=4)
        candidate.update_faces(candidate.area_faces>0)
        candidate.update_faces(candidate.unique_faces())
        candidate.remove_unreferenced_vertices()
        if candidate.is_volume and abs(candidate.volume-mesh.volume)/mesh.volume<=.01:return candidate,True
    return mesh.copy(),False


def generate_architecture(folder,options=None,progress=lambda message:None):
    base,manifest=checked_base();folder.mkdir(parents=True,exist_ok=False)
    design=json.loads((base/'recipe.json').read_text());report=json.loads((base/'report.json').read_text())
    additions=modules();design.update(schema_version=8,revision=8,component_voxel_mm=.1)
    travel=float((options or {}).get('centrebody_mm',design['intake']['centrebody_mm']))
    if not np.isfinite(travel) or not -4<=travel<=4:raise ValueError('Centrebody travel must be between -4 and +4 mm')
    delta=travel-design['intake']['centrebody_mm'];design['intake']['centrebody_mm']=travel
    design['components']=[p for p in design['components'] if p['id']!='air-compressor']+[
        dict(id=p['id'],name=p['name'],color=p['color'],voxel_mm=.1,anatomy_reference=p['reference'],review_anchor_mm=[*p['center_mm'],float(np.mean([r[0] for r in p['profile']]))]) for p in additions]
    design['design_changes']=dict(baseline_run=BASE_RUN,description='Expanded non-firing architecture: ten new or upgraded 0.1 mm modules; inherited casing and original accessories remain 0.2 mm')
    design['architecture_modules']=additions
    design['resolution_policy'].update(component_voxel_mm=.1,display='Decimated component display meshes; full-resolution native component STLs are downloadable')
    design['recipe_sha256']=fingerprint({k:v for k,v in design.items() if k!='recipe_sha256'})
    (folder/'recipe.json').write_text(json.dumps(design,indent=2),encoding='utf-8')
    config=dict(modules=additions,voxel_mm=.1,scope='Non-firing expanded review assembly')
    (folder/'architecture-input.json').write_text(json.dumps(config),encoding='utf-8')
    progress('Building closed triangular input meshes for ten 0.1 mm modules')
    input_evidence={}
    for part in additions:
        mesh=profile_mesh(part);path=folder/(part['id']+'.input.stl');mesh.export(path)
        input_evidence[part['id']]=dict(triangles=len(mesh.faces),sha256=digest(path),closed_shells=2 if part['kind']=='regenerator' else 1)
    (folder/'architecture-input-meshes.json').write_text(json.dumps(input_evidence,indent=2))
    progress('Voxelizing component triangles at 0.1 mm and adding implicit blades, ribs and shield cutaway')
    native_hash=digest(DLL)
    with (folder/'architecture-native.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([str(DOTNET),str(DLL),'architecture',str(folder/'architecture-input.json'),str(folder),'0.1'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    if result.returncode:raise ValueError('0.1 mm module generation failed: '+(folder/'architecture-native.log').read_text()[-1500:])
    native=json.loads((folder/'architecture-native.json').read_text())
    if native['boolean_reference_samples']!=15:raise ValueError('Module Boolean checks failed')
    for record in native['components']:
        if record['voxel_mm']!=.1 or record['triangle_input_count']!=input_evidence[record['id']]['triangles']:raise ValueError('Module mesh-to-voxel evidence mismatch')
    # Only immutable, hash-verified base artifacts are linked. Never rewrite them.
    changed={'recipe.json','report.json','PRINT.txt','vega-one-print-kit.zip','scene.stl','scene-normals.bin','air-compressor.stl','centrebody.stl','analysis.json'}
    for name,expected in manifest.items():
        if name in changed:continue
        source=base/name
        if digest(source)!=expected:raise ValueError('Base artifact changed: '+name)
        os.link(source,folder/name)
    scene_paths=[];bodies=[];components={k:v for k,v in report['components'].items() if k!='air-compressor'};first=0;cleanup={};display_evidence={}
    if digest(base/'centrebody.stl')!=manifest['centrebody.stl']:raise ValueError('Base centrebody changed')
    centrebody=trimesh.load_mesh(base/'centrebody.stl',process=True);centrebody.apply_translation([0,0,delta])
    export_print_mesh(centrebody,folder/'centrebody.stl');del centrebody;gc.collect()
    components['centrebody']=inspect_mesh(folder/'centrebody.stl')[1];gc.collect()
    analysis=analyze(design);(folder/'analysis.json').write_text(json.dumps(analysis,allow_nan=False),encoding='utf-8')
    # Extract the two casing surfaces directly from the verified packed base STL.
    if digest(base/'scene.stl')!=manifest['scene.stl']:raise ValueError('Base viewer mesh changed')
    for body in report['bodies']:
        if body['component_id']=='air-compressor':continue
        name=body['component_id'];target=folder/(name+'.display.stl')
        with (base/'scene.stl').open('rb') as src,target.open('wb') as dst:
            src.seek(84+50*body['first_triangle']);dst.write(b'Vega inherited display'.ljust(80,b'\0'));dst.write(struct.pack('<I',body['triangle_count']))
            remaining=50*body['triangle_count']
            while remaining:
                data=src.read(min(4*1024*1024,remaining));dst.write(data);remaining-=len(data)
        # Inherited display also gets a lighter LOD so the expanded scene fits.
        mesh=trimesh.load_mesh(target,process=True)
        if name=='centrebody':mesh.apply_translation([0,0,delta])
        lod,reduced=(mesh.copy(),False) if name.startswith('half-') else display_mesh(mesh,70000)
        lod.export(target);count=len(lod.faces)
        display_evidence[name]=dict(source_triangles=body['triangle_count'],display_triangles=count,decimated=reduced)
        bodies.append(dict(body,first_triangle=first,triangle_count=count));first+=count;scene_paths.append(target)
        del mesh,lod;gc.collect()
    for part in additions:
        name=part['id'];progress('Checking 0.1 mm '+part['name'])
        path=folder/(name+'.stl');cleanup[name]=clean_native(path,.1);gc.collect()
        mesh,check=inspect_mesh(path);check['voxel_mm']=.1;components[name]=check
        lod,reduced=display_mesh(mesh,70000);target=folder/(name+'.display.stl');lod.export(target)
        count=len(lod.faces);display_evidence[name]=dict(source_triangles=len(mesh.faces),display_triangles=count,decimated=reduced)
        bodies.append(dict(component_id=name,name=part['name'],first_triangle=first,triangle_count=count,color=part['color'],voxel_mm=.1));first+=count;scene_paths.append(target)
        del mesh,lod;gc.collect()
    progress('Packing the expanded review assembly and full-resolution downloads')
    if first>6_000_000:raise ValueError('Expanded display exceeds triangle budget')
    with (folder/'scene.stl').open('wb') as dst,(folder/'scene-normals.bin').open('wb') as normals:
        dst.write(b'Vega review LOD: full resolution in component STL files'.ljust(80,b'\0'));dst.write(struct.pack('<I',first))
        for path in scene_paths:
            mesh=trimesh.load_mesh(path,process=True);append_smooth_normals(mesh,normals)
            with path.open('rb') as src:src.seek(84);shutil.copyfileobj(src,dst)
            del mesh;gc.collect()
    # These are unserved build intermediates, already packed into scene.stl.
    for path in scene_paths:path.unlink()
    report.update(recipe=design,components=components,bodies=bodies,module_native=native,module_native_binary_sha256=native_hash,
        module_input_meshes=input_evidence,module_cleanup=cleanup,display_meshes=display_evidence,scene_sha256=digest(folder/'scene.stl'),
        base_run=BASE_RUN,assembly_scope='Expanded review arrangement; component fits, hot operation and connected engine performance are not validated',
        analysis_summary=dict(status=analysis['status'],cfd_cells=analysis['cfd']['cells'],fea_elements=analysis['fea']['elements']),
        analysis_scope='Inherited intake CFD and centrebody FEA only. The new hot-section and rotating-machine components are not simulated.')
    (folder/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    guide=(base/'PRINT.txt').read_text(encoding='utf-8')+'\nREVISION 8: new module STLs are 0.1 mm voxel exports in assembly coordinates. Review orientation and supports separately. The scene is a decimated visual review assembly. New hot-section components are non-firing representations; inherited CFD/FEA do not analyze them.\n'
    (folder/'PRINT.txt').write_text(guide,encoding='utf-8')
    # Full native modules plus the inherited print kit are separate downloads.
    with zipfile.ZipFile(folder/'vega-one-print-kit.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as kit:
        for name in ['half-a.stl','half-b.stl','recipe.json','report.json','PRINT.txt','analysis.json']+[p['id']+'.stl' for p in design['components']]:kit.write(folder/name,name)
    return report
