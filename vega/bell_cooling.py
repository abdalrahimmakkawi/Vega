"""Visible cold-flow bell jacket, routed plumbing and a genuine 9 micron crop."""
import gc
import json
import os
import shutil
import struct
import subprocess
import zipfile
import numpy as np
import trimesh
from .demonstrator import ROOT
from .architecture import digest,display_mesh
from .integration import specification,rounded_route,interior_probes,inside_stl
from .print_export import DOTNET,DLL,clean_native,inspect_mesh,append_smooth_normals
from .cooling_simulation import assembly_network
from .artifacts import physical,artifact_digest,compact_stl,materialized_stl,open_artifact
from vega_geometry import fingerprint

BASE_RUN='1b08ae2d995142b7b6a17949cba321a3'
COOLING_IDS=('bell-cooling-a','bell-cooling-b','cooling-supply','cooling-return','hydrogen-line','oxygen-line')


def geometry(design):
    profile=np.asarray(next(p for p in design['architecture_modules'] if p['id']=='bell-chamber')['profile'])
    radius=lambda z:float(np.interp(z,profile[:,0],profile[:,1]))+1.5
    front,rear=142.,182.;rf,rr=radius(front),radius(rear)
    branches=[]
    for i in range(6):
        points=[]
        for z in np.linspace(front,rear,101):
            t=(z-front)/(rear-front);a=np.pi/6+i*np.pi/3+.1*np.sin(np.pi*t)
            points.append([radius(z)*np.cos(a),radius(z)*np.sin(a),float(z)])
        branches.append(dict(id='bell-'+str(i+1),points=points,outer_radius_mm=1.8,bore_radius_mm=.7))
    rings=[dict(id=name,points=[[r*np.cos(a),r*np.sin(a),z] for a in np.linspace(0,2*np.pi,193)],outer_radius_mm=1.8,bore_radius_mm=.9)
           for name,r,z in [('front-ring',rf,front),('rear-ring',rr,rear)]]
    direction=np.array([-1.,1.,0.])/np.sqrt(2)
    terminals=[];ports=[]
    for name,r,z in [('jacket-inlet',rf,front),('jacket-outlet',rr,rear)]:
        start=direction*r+[0,0,z];end=direction*(r+5)+[0,0,z];terminals.append(end)
        ports.append(dict(id=name,points=[start.tolist(),end.tolist()],outer_radius_mm=1.8,bore_radius_mm=.8,open_end=True))
    source=design['cooling']['ports'][1]['points'][-1]
    supply=rounded_route([source,[-26,26,112],[-26,26,136],(terminals[0]+direction*5).tolist(),terminals[0].tolist()],4)
    ret=rounded_route([terminals[1].tolist(),(terminals[1]+direction*6).tolist(),[-31,30,174],[-31,30,119],[-35,30,114],[-39,30,114]],4)
    return dict(branches=branches,rings=rings,ports=ports,front_radius_mm=rf,rear_radius_mm=rr,supply=supply,
                supply_bore_radius_mm=.8,return_bore_radius_mm=.8,**{'return':ret})


def cross_section_probes(routes):
    probes=[]
    for route in routes:
        points=np.asarray(route['points'])
        for i,p in enumerate(points):
            tangent=points[min(i+1,len(points)-1)]-points[max(0,i-1)]
            tangent/=np.linalg.norm(tangent);axis=np.eye(3)[np.argmin(abs(tangent))]
            u=np.cross(tangent,axis);u/=np.linalg.norm(u);v=np.cross(tangent,u)
            probes.extend([p,p+.4*u,p-.4*u,p+.4*v,p-.4*v])
    return np.asarray(probes).tolist()


def input_parts(design,cooling):
    previous,_=specification();parts=[];joints=[]
    def joint(part,source,point,name,margin=.1):
        probes=interior_probes(point,margin);part['contact_probes']+=probes
        joints.append(dict(part=part['id'],source=source,point_mm=point,probes=probes,name=name))
    for identity,points in [
        ('hydrogen-line',[[48,0,68],[51,10,68],[46,32,76],[-38,32,80],[-38,5.5,80]]),
        ('oxygen-line',[[47.5,-15,100],[51,10,100],[46,36,101],[-24,36,103],[-27,0,111]])]:
        p=next(p for p in previous if p['id']==identity)
        p['routes'][0]['points']=rounded_route(points,5)
        p['open_probes']=cross_section_probes([p['routes'][0]])
        if identity=='hydrogen-line':
            p['contact_probes']=[]
            joint(p,'hydrogen-pump',[48,0,69.05],'Static pump interface')
            joint(p,'pre-burner',[-38,5.5,81.05],'Separate static housing interface; not an open fluid port')
        parts.append(p)
    for identity,name,points,reference,color in [
        ('cooling-supply','Core collector → bell cooling supply',cooling['supply'],'A35',[.22,.61,.73]),
        ('cooling-return','Bell cooling return + support',cooling['return'],'A36',[.35,.64,.67])]:
        seed=trimesh.creation.icosphere(subdivisions=2,radius=1.8);seed.apply_translation(points[0])
        p=dict(id=identity,name=name,seeds=[seed],color=color,anatomy_reference=reference,review_anchor_mm=points[len(points)//2],voxel_mm=.1,
               beams=[],routes=[dict(points=points,outer=1.8,bore=cooling[('supply' if identity=='cooling-supply' else 'return')+'_bore_radius_mm'])],contact_probes=[],open_probes=cross_section_probes([dict(points=points)]))
        if identity=='cooling-supply':
            source=design['cooling']['ports'][1]['points'][-1]
            joint(p,'half-a',[source[0],source[1],source[2]+1.2],'Open core collector coupling')
            end=np.array(points[-1]);end+=np.array([.35,-.35,1.2])
            joint(p,'bell-cooling-a',end.tolist(),'Open jacket inlet coupling')
        else:
            start=np.array(points[0])+np.array([.35,-.35,1.2])
            joint(p,'bell-cooling-a',start.tolist(),'Open jacket outlet coupling')
            p['beams'].append([[-14,14,118],[-31,30,124],1.1,1.1])
            p['beams'].append([[-36,30,114],[-39,30,114],2.2,2.2])
            joint(p,'half-a',[-14,14,118],'Return-line casing saddle')
        parts.append(p)
    for identity,y,ref in [('bell-cooling-a',.5,'A33'),('bell-cooling-b',-.5,'A34')]:
        p=dict(id=identity,name='Bell cooling jacket · '+('upper' if y>0 else 'lower')+' half',color=[.69,.43,.25] if y>0 else [.79,.54,.31],
               anatomy_reference=ref,review_anchor_mm=[0,12*np.sign(y),170],voxel_mm=.1,contact_probes=[])
        joint(p,'bell-chamber',[10.85,y,142],'Jacket to bell material overlap',.05)
        parts.append(p)
    a=next(p for p in parts if p['id']=='bell-cooling-a');b=next(p for p in parts if p['id']=='bell-cooling-b')
    joint(a,'bell-cooling-b',[cooling['front_radius_mm'],0,143.2],'Split jacket mating overlap',.05)
    b['contact_probes']+=interior_probes([cooling['front_radius_mm'],0,143.2],.05)
    return parts,joints


def assessment(report,network):
    return dict(goal='Whole non-firing demonstrator: airflow, circulation, cooling and mechanical fit',
        conclusion='Operation not established; model and validation gaps remain',whole_engine_operability_established=False,
        checks=[
            dict(id='static_connectivity',status='passed',evidence='Native material probes and exported-STL contact graph; moving centrebody intentionally separate'),
            dict(id='cold_cooling_route',status='geometry_checked',evidence='Core collector, supply, split bell jacket and open return; split seams require sealing'),
            dict(id='cold_network_mass_balance',status='passed',evidence=f"Relative mass residual {network['relative_mass_balance_residual']:.3g}; calculated at assumed flow"),
            dict(id='whole_main_airpath_CFD',status='not_run',evidence='Existing CFD covers intake only; full viscous fluid domain, fan boundary and mesh convergence are required'),
            dict(id='circulator_and_pumps',status='blocked',evidence='Machinery is static; inherited He, hydrogen and LOX interfaces remain blind. No operating pump/fan curves'),
            dict(id='thermal_performance',status='not_run',evidence='No specified heat load, wall conductivity/contact resistance or measured coolant boundary conditions'),
            dict(id='mechanical_fit_and_strength',status='unverified',evidence='Sampled contacts are not a global interference, tolerance, fastening or load assessment'),
            dict(id='physical_leakage_and_flow',status='unverified',evidence='No measured fan operating point, leakage, flow distribution or pressure drop')],
        simulation_boundary='The Python network is a submodel, not a simulation of the whole engine. No engine-level pass is inferred from it.',
        next_inputs=['Fan or circulator pressure-flow curve','Solid material properties and intended heat load','Sealing and assembly tolerances','Defined airflow, temperature and deflection acceptance limits'])


def generate_cooling(folder,options=None,progress=lambda m:None,*,resume=False):
    base=ROOT/'data/prints'/BASE_RUN;manifest=json.loads((base/'manifest.json').read_text())
    if json.loads((ROOT/'data/print-jobs'/(BASE_RUN+'.json')).read_text())['status']!='complete':raise ValueError('Accepted connected assembly unavailable')
    if resume and ((folder/'manifest.json').exists() or json.loads((ROOT/'data/print-jobs'/(folder.name+'.json')).read_text())['status']!='failed'):
        raise ValueError('Only an unpublished failed cooling build can be resumed')
    folder.mkdir(parents=True,exist_ok=resume)
    stages=json.loads((folder/'native-stages.json').read_text()) if resume and (folder/'native-stages.json').exists() else {}
    report=json.loads((base/'report.json').read_text());design=report['recipe'];cooling=geometry(design)
    parts,joints=input_parts(design,cooling);evidence={}
    from .design_audit import require_route_clearance
    inherited,_=specification();replaced={p['id'] for p in parts}
    require_route_clearance([p for p in inherited if p['id'] not in replaced]+parts)
    progress('Checking cooling attachments against the accepted source meshes')
    for j in joints:
        if j['source'] in COOLING_IDS:continue
        if j['source'].startswith('half-'):
            body=next(b for b in report['bodies'] if b['component_id']==j['source'])
            passed=inside_stl(base/'scene.stl',j['probes'],body['first_triangle'],body['triangle_count'])
        else:passed=inside_stl(base/(j['source']+'.stl'),j['probes'])
        if not all(passed):raise ValueError('Cooling source interface misses '+j['source'])
        j['source_mesh_contact']='passed'
    progress('Creating triangular manifolds, smooth channels and routed service lines')
    seeds=[]
    for r,z in [(cooling['front_radius_mm'],142),(cooling['rear_radius_mm'],182)]:
        mesh=trimesh.creation.torus(major_radius=r,minor_radius=1.8,major_sections=128,minor_sections=24);mesh.apply_translation([0,0,z]);seeds.append(mesh)
    path=folder/'cooling-manifolds.input.stl';mesh=trimesh.util.concatenate(seeds);mesh.export(path)
    evidence['manifolds']=dict(triangles=len(mesh.faces),sha256=digest(path))
    routes=cooling['branches']+cooling['rings']+cooling['ports']
    config=dict(routes=routes,open_probes=cross_section_probes(routes),**{p['id']+'_contacts':p['contact_probes'] for p in parts if p['id'].startswith('bell-cooling-')})
    (folder/'cooling-input.json').write_text(json.dumps(config))
    route_parts=[p for p in parts if 'seeds' in p]
    for p in route_parts:
        mesh=trimesh.util.concatenate(p.pop('seeds'));path=folder/(p['id']+'.input.stl');mesh.export(path)
        evidence[p['id']]=dict(triangles=len(mesh.faces),sha256=digest(path))
    (folder/'routes-input.json').write_text(json.dumps(dict(parts=route_parts)))
    points=np.asarray(cooling['branches'][0]['points']);index=55;center=points[index]+1.25*np.array([np.cos(np.arctan2(points[index,1],points[index,0])),np.sin(np.arctan2(points[index,1],points[index,0])),0])
    detail_config=dict(center_mm=[0,0,0],source_center_mm=center.tolist(),points=(points[index-12:index+13]-center).tolist(),crop_size_mm=1.)
    (folder/'cooling-detail-input.json').write_text(json.dumps(detail_config))
    mesh=trimesh.creation.box(extents=[1,1,1]);mesh.export(folder/'cooling-detail.input.stl')
    def native(command,config,pitch):
        inputs=[config]+(['cooling-manifolds.input.stl'] if command=='bell-cooling' else [p['id']+'.input.stl' for p in route_parts] if command=='integrate' else ['cooling-detail.input.stl'])
        outputs=['cooling-native.json','bell-cooling-a.stl','bell-cooling-b.stl'] if command=='bell-cooling' else ['integration-native.json']+[p['id']+'.stl' for p in route_parts] if command=='integrate' else ['cooling-detail-native.json','cooling-detail.stl']
        hashes={n:digest(folder/n) for n in inputs};previous=stages.get(command)
        if previous and previous['inputs']==hashes and all(physical(folder/n).exists() and artifact_digest(folder/n)==h for n,h in previous['outputs'].items()):
            progress('Reusing hash-verified native '+command+' geometry');return
        with (folder/(command+'.log')).open('w') as log:
            run=subprocess.run([str(DOTNET),str(DLL),command,str(folder/config),str(folder),pitch],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=900)
        if run.returncode:raise ValueError((folder/(command+'.log')).read_text()[-1800:])
        stages[command]=dict(inputs=hashes,outputs={n:digest(folder/n) for n in outputs},native_binary_sha256=digest(DLL))
        (folder/'native-stages.json').write_text(json.dumps(stages,indent=2))
        for name in outputs:
            if name.endswith('.stl'):compact_stl(folder/name)
    progress('Voxelizing the six-channel bell jacket at 0.1 mm')
    native('bell-cooling','cooling-input.json','0.1')
    progress('Voxelizing the reorganized supply, return and service harnesses')
    native('integrate','routes-input.json','0.1')
    progress('Building the genuine 0.009 mm cooling-wall detail')
    native('cooling-detail','cooling-detail-input.json','0.009')
    cooling_native=json.loads((folder/'cooling-native.json').read_text());route_native=json.loads((folder/'integration-native.json').read_text());detail_native=json.loads((folder/'cooling-detail-native.json').read_text())
    if any(n['boolean_reference_samples']!=15 for n in [cooling_native,route_native,detail_native]):raise ValueError('Cooling Boolean reference gate failed')
    if cooling_native['triangle_input_count']!=evidence['manifolds']['triangles']:raise ValueError('Manifold input evidence mismatch')
    for record in route_native['components']:
        if record['triangle_input_count']!=evidence[record['id']]['triangles']:raise ValueError('Route input evidence mismatch')
    changed={'recipe.json','report.json','PRINT.txt','vega-one-print-kit.zip'}|{p+'.stl' for p in COOLING_IDS}
    for name,expected in manifest.items():
        if name in changed:continue
        if digest(base/name)!=expected:raise ValueError('Base artifact changed: '+name)
        if (folder/name).exists():
            if digest(folder/name)!=expected:raise ValueError('Resumed base artifact changed: '+name)
        else:os.link(base/name,folder/name)
    hidden=[]
    for body in report['bodies']:
        if body['component_id'] in ('hydrogen-line','oxygen-line'):
            body['component_id']='superseded-'+body['component_id'];hidden.append(body['component_id'])
    first=sum(b['triangle_count'] for b in report['bodies']);scene_paths=[];display_count=0;cleanup={}
    for p in parts:
        identity=p['id'];progress('Auditing '+p['name']);path=folder/(identity+'.stl')
        with materialized_stl(path,writeback=True) as work:
            cleanup[identity]=clean_native(work,.1);gc.collect();mesh,check=inspect_mesh(work);check['voxel_mm']=.1
            report['components'][identity]=check
            lod,reduced=display_mesh(mesh,60000 if identity.startswith('bell-cooling-') else 18000)
            target=folder/(identity+'.display.stl');lod.export(target);scene_paths.append(target);count=len(lod.faces)
            report['bodies'].append(dict(component_id=identity,name=p['name'],color=p['color'],voxel_mm=.1,first_triangle=first+display_count,triangle_count=count));display_count+=count
            report['display_meshes'][identity]=dict(source_triangles=len(mesh.faces),display_triangles=count,decimated=reduced)
            design['components']=[c for c in design['components'] if c['id']!=identity]
            design['components'].append({k:p[k] for k in ['id','name','color','voxel_mm','anatomy_reference','review_anchor_mm']})
            del mesh,lod;gc.collect()
            if not all(inside_stl(work,p['contact_probes'])):raise ValueError('Exported contact failed: '+identity)
    for j in joints:
        if j['source'] in COOLING_IDS:
            with materialized_stl(folder/(j['source']+'.stl')) as work:
                if not all(inside_stl(work,j['probes'])):raise ValueError('Cooling joint failed: '+j['source'])
            j['source_mesh_contact']='passed'
    if first+display_count>6_000_000:raise ValueError('Combined display exceeds browser budget')
    with (folder/'cooling-scene.stl').open('wb') as dst,(folder/'cooling-normals.bin').open('wb') as normals:
        dst.write(b'Vega bell cooling overlay'.ljust(80,b'\0'));dst.write(struct.pack('<I',display_count))
        for path in scene_paths:
            mesh=trimesh.load_mesh(path,process=True);append_smooth_normals(mesh,normals)
            with path.open('rb') as src:src.seek(84);shutil.copyfileobj(src,dst)
            del mesh;gc.collect();path.unlink()
    with materialized_stl(folder/'cooling-detail.stl',writeback=True) as work:
        detail_cleanup=clean_native(work,.009);gc.collect()
        mesh,detail=inspect_mesh(work);del mesh;gc.collect()
    detail.update(voxel_mm=.009,file='cooling-detail.stl',crop_size_mm=1.,scope='1 mm cube through a bell cooling-channel wall; crop boundaries are artificial',center_mm=center.tolist(),cleanup=detail_cleanup)
    design.update(revision=10,schema_version=10)
    design['bell_cooling']=cooling
    design['resolution_policy'].update(detail_voxel_mm=.009,detail_scope=detail['scope'])
    design['design_changes']=dict(baseline_run=BASE_RUN,description='Six hollow bell-cooling channels, paired manifolds and open collector/return connections; service harnesses routed behind the casing. Genuine 0.009 mm local wall detail, with 0.1 mm additions.')
    design['recipe_sha256']=fingerprint({k:v for k,v in design.items() if k!='recipe_sha256'})
    network=assembly_network(design,cooling)
    report['integration']['joints']=[j for j in report['integration']['joints'] if j['part']!='hydrogen-line']+joints
    fixed={b['component_id'] for b in report['bodies']}-{*hidden,'centrebody'};seen={'mount-frame'}
    edges=[(j['part'],j['source']) for j in report['integration']['joints']]
    while True:
        new=seen|{b for a,b in edges if a in seen}|{a for a,b in edges if b in seen}
        if new==seen:break
        seen=new
    if seen!=fixed:raise ValueError('Cooling assembly has detached components: '+str(fixed-seen))
    report['integration'].update(fixed_parts_connected=len(seen),source_contact_probes=sum(len(j['probes']) for j in report['integration']['joints']),
        fluid_scope='Core cooling collector → supply → six bell channels with ring manifolds → open return. Split seams require sealing. Machinery harnesses remain blind and static.')
    report.update(base_run=BASE_RUN,detail=detail,hidden_component_ids=hidden,
        scene_layers=[dict(mesh='integration-scene.stl',normals='integration-normals.bin'),dict(mesh='cooling-scene.stl',normals='cooling-normals.bin')],
        cooling_scene_sha256=digest(folder/'cooling-scene.stl'),cooling_native=cooling_native,cooling_routes_native=route_native,
        cooling_detail_native=detail_native,cooling_input_meshes=evidence,cooling_cleanup=cleanup,cooling_native_binaries={k:v['native_binary_sha256'] for k,v in stages.items()},
        whole_engine_assessment=assessment(report,network),cooling_network=network)
    for name,value in [('recipe.json',design),('report.json',report),('cooling-network.json',network),('whole-engine-assessment.json',report['whole_engine_assessment'])]:
        (folder/name).write_text(json.dumps(value,indent=2,allow_nan=False))
    (folder/'PRINT.txt').write_text('REVISION 10 — NON-FIRING BELL COOLING\nUse the revision 9 base kit and its revision 8 base, plus these additions. Replace the hydrogen-line and oxygen-line files with this revision. The browser hides superseded surfaces retained in its immutable base overlay. New geometry is 0.1 mm; cooling-detail.stl alone is 0.009 mm.\n\nThe bell jacket has two inspection halves with 0.4 mm nominal overlap at their mating region. Sealing, manufacturing fit and global collision clearance are not validated. The circuit connects the existing core outlet to the bell manifolds and an open return. No pump is operational. The hydraulic network is not whole-engine CFD or a thermal solution. Read whole-engine-assessment.json for outstanding validation.\n',encoding='utf-8')
    progress('Packing checked cooling geometry and whole-system assessment')
    with zipfile.ZipFile(folder/'vega-one-print-kit.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as kit:
        for name in [p+'.stl' for p in COOLING_IDS]+['cooling-detail.stl','recipe.json','report.json','PRINT.txt','cooling-network.json','whole-engine-assessment.json']:
            with open_artifact(folder/name) as src,kit.open(name,'w') as dst:shutil.copyfileobj(src,dst,1024*1024)
    return report
