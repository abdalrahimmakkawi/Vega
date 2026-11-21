"""Static assembly integration, with material-contact evidence from actual STLs.

Hollow canister links are inspection passages. Existing machinery ports remain
blind representations; these additions do not establish an operating engine.
"""
import gc
import json
import os
import struct
import subprocess
import zipfile
import shutil
import numpy as np
import trimesh
from .demonstrator import ROOT
from .architecture import digest, display_mesh
from .print_export import DOTNET, DLL, clean_native, inspect_mesh, append_smooth_normals
from vega_geometry import fingerprint

BASE_RUN='35ba46279d35462bb86514ce3f19b73f'
PART_IDS=('mount-frame','mount-frame-right','aft-coupling','static-drive','regenerator-link','thermal-supply','heater-link','thermal-return','helium-link','hydrogen-line','oxygen-line')
STL_DTYPE=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])


def interior_probes(point,margin=.12):
    p=np.asarray(point,float)
    return np.vstack([p,p+np.eye(3)*margin,p-np.eye(3)*margin]).tolist()


def inside_stl(path,points,first=0,count=None):
    """Bounded-memory oblique ray parity, used away from surface boundaries."""
    with open(path,'rb') as f:
        f.seek(80);total=struct.unpack('<I',f.read(4))[0]
    count=total-first if count is None else count
    if first<0 or count<1 or first+count>total:raise ValueError('Invalid STL range')
    triangles=np.memmap(path,dtype=STL_DTYPE,mode='r',offset=84+first*50,shape=(count,))
    direction=np.array([.813719,.337129,.473921]);direction/=np.linalg.norm(direction)
    hits=np.zeros(len(points),dtype=np.int64)
    for start in range(0,count,16384):
        tri=np.asarray(triangles[start:start+16384]['vertices'],dtype=float)
        a=tri[:,0];e1=tri[:,1]-a;e2=tri[:,2]-a
        h=np.cross(direction,e2);det=np.einsum('ij,ij->i',e1,h)
        valid=np.abs(det)>1e-12;inv=np.divide(1.,det,out=np.zeros_like(det),where=valid)
        for i,p in enumerate(points):
            s=np.asarray(p)-a;u=np.einsum('ij,ij->i',s,h)*inv
            q=np.cross(s,e1);v=q@direction*inv;t=np.einsum('ij,ij->i',e2,q)*inv
            hits[i]+=np.count_nonzero(valid&(u>=0)&(v>=0)&(u+v<=1)&(t>1e-8))
    del triangles
    return (hits%2==1).tolist()


def annulus(center,rows):
    # Each row is z, outer radius, inner radius; different tapers on each wall.
    rows=np.asarray(rows,float)
    polygon=np.vstack([rows[:,[1,0]],rows[::-1][:,[2,0]],rows[0,[1,0]]])
    mesh=trimesh.creation.revolve(polygon,sections=64)
    if mesh.volume<0:mesh.invert()
    if not mesh.is_volume:raise ValueError('Open integration input')
    mesh.apply_translation([*center,0]);return mesh


def rounded_route(points,radius=3):
    points=np.asarray(points,float);result=[points[0]]
    for i in range(1,len(points)-1):
        a,b,c=points[i-1:i+2];u=a-b;v=c-b
        d=min(radius,np.linalg.norm(u)*.3,np.linalg.norm(v)*.3)
        entry=b+u/np.linalg.norm(u)*d;end=b+v/np.linalg.norm(v)*d
        result.append(entry)
        result.extend((1-t)**2*entry+2*(1-t)*t*b+t*t*end for t in np.linspace(0,1,13)[1:])
    result.append(points[-1]);return np.asarray(result).tolist()


def sample_route(points,step=.6,trim=0):
    result=[]
    for a,b in zip(np.asarray(points)[:-1],np.asarray(points)[1:]):
        result.extend(a+(b-a)*t for t in np.linspace(0,1,max(2,int(np.linalg.norm(b-a)/step)+1)))
    return np.asarray(result)[trim:len(result)-trim if trim else None].tolist()


def specification():
    parts=[];joints=[]
    def part(identity,name,meshes,color,reference,anchor):
        value=dict(id=identity,name=name,seeds=meshes,color=color,anatomy_reference=reference,
            review_anchor_mm=anchor,voxel_mm=.1,beams=[],routes=[],contact_probes=[],open_probes=[])
        parts.append(value);return value
    def beam(p,a,b,r=1.4,end=None):p['beams'].append([list(map(float,a)),list(map(float,b)),r,end or r])
    def contact(p,source,point,label):
        probes=interior_probes(point);p['contact_probes']+=probes
        joints.append(dict(part=p['id'],source=source,point_mm=point,probes=probes,name=label))
    frame=part('mount-frame','Mounting frame + aft cartridge',[
        annulus([0,0],[[119.4,19.5,16.2],[133,19.5,16.2],[139.2,11,8.8]]),
        annulus([0,0],[[59.4,11.5,9.3],[65.4,11.5,9.3]]),
        annulus([0,0],[[63,3.2,2.5],[136,3.2,2.5]]),
        annulus([0,0],[[126,4.3,2.5],[130,4.3,2.5]]),
        annulus([31,18],[[94.5,5.3,3.5],[98,6.3,4.5]])
    ],[.37,.43,.49],'A22',[0,-30,64])
    for x in [-30,30]:
        beam(frame,[x,-7,22],[x,-7,124],1.8)
        beam(frame,[x,-7,64],[x,-31,64],1.6)
        beam(frame,[x,-31,64],[0,-31,64],1.6)
        beam(frame,[x,-7,24],[np.sign(x)*24.5,0,24],1.7)
        beam(frame,[x,-7,123],[np.sign(x)*18,0,123],1.6)
    # Radial bearing webs and a hollow static shaft; the moving stem remains clear.
    for z,end in [(64.5,10.5),(121,18),(135,15.2)]:
        for a in [0,2*np.pi/3,4*np.pi/3]:
            beam(frame,[3*np.cos(a),3*np.sin(a),z],[end*np.cos(a),end*np.sin(a),z],.8)
    for z,r in [(125,18.5),(145,10.3)]:
        for a in [-np.pi/4,-3*np.pi/4]:
            beam(frame,[r*np.cos(a),r*np.sin(a),z],[24.3*np.cos(a),24.3*np.sin(a),z],1.1)
    # Long shield supports attach to the aft housing, not just to the bell.
    for a in [-np.pi/4,-3*np.pi/4]:
        beam(frame,[24.3*np.cos(a),24.3*np.sin(a),125],[24.3*np.cos(a),24.3*np.sin(a),145],1.1)
    mounts=[
        ('helium-circulator',[-32.2,0,38],[-30,-7,38]),
        ('hydrogen-pump',[43.5,0,66],[30,-7,66]),
        ('pre-burner',[-32.7,0,76],[-30,-7,76]),
        ('re-heater',[-31.7,0,108],[-30,-7,108]),
        ('regenerators',[-49.5,-10,54],[-30,-7,54]),
        ('lox-pump',[43.3,-15,98],[30,-7,98]),
        ('precooler',[-22,0,24],[-30,-7,24])]
    for source,p,start in mounts:
        beam(frame,start,p,1.4,.45 if source in ('pre-burner','re-heater','regenerators','lox-pump') else 1.)
        contact(frame,source,p,'Accessory saddle')
    for z,r,source in [(35,4.3,'spill-duct'),(100,5.3,'ramjet-burner')]:
        beam(frame,[30,-7,z],[42,18,z],1.4)
        beam(frame,[42,18,z],[31+r,18,z],1.4,.4)
        contact(frame,source,[31+r,18,z],'Spill assembly saddle')
    beam(frame,[30,-7,96],[42,18,96],1.4)
    beam(frame,[42,18,96],[36.4,18,96],1.4,.5)
    for source,p in [('half-a',[-24.5, .7,24]),('half-b',[-24.5,-.7,24]),
                     ('air-compressor',[10.5,0,59.7]),('drive-turbine',[4,0,128]),
                     ('bell-chamber',[10.2,0,138.6]),('heat-shield',[-17.2,-17.2,125])]:
        contact(frame,source,p,'Structural joint')
    # Open central stem bore over its full possible travel; check 0.3 mm margin.
    frame['open_probes']=[[x,y,z] for z in np.arange(62.8,69,.2) for x,y in [(0,0),(2.2,0),(-2.2,0),(0,2.2),(0,-2.2)]]

    def link(identity,name,end1,end2,via,reference,color):
        # end=(source,center x/y, face z, outer, inner, extension direction)
        seeds=[];terminals=[];probes=[]
        for source,c,z,outer,inner,d in [end1,end2]:
            rows=sorted([[z-d*.5,outer,inner],[z,outer,inner],[z+d*4,1.6,.8]])
            seeds.append(annulus(c,rows));terminals.append([*c,z+d*4])
            probes.append((source,[c[0]+(outer+inner)/2,c[1],z-d*.25]))
        points=rounded_route([terminals[0],*via,terminals[1]])
        value=part(identity,name,seeds,color,reference,points[len(points)//2])
        value['routes']=[dict(points=points,outer=1.6,bore=.8)]
        value['open_probes']=sample_route(points)
        for source,p in probes:contact(value,source,p,'Tapered annular coupling')
        return value
    regen1=lambda z,d:('regenerators',[-54,-10],z,5.2,3.8,d)
    regen2=lambda z,d:('regenerators',[-54,10],z,5.2,3.8,d)
    pre=lambda z,d:('pre-burner',[-38,0],z,6,4.6,d)
    heater=lambda z,d:('re-heater',[-38,0],z,7,5.6,d)
    link('regenerator-link','Regenerator crossover',regen1(74,1),regen2(74,1),[[-54,-10,83],[-54,10,83]],'A23',[.44,.68,.53])
    link('thermal-supply','Regenerator → pre-burner inspection link',regen1(48,-1),pre(74,-1),[[-54,-10,39],[-65,-10,39],[-65,-20,66],[-38,-20,66],[-38,0,66]],'A24',[.35,.65,.65])
    link('heater-link','Pre-burner → re-heater coupling',pre(86,1),heater(104,-1),[],'A25',[.77,.49,.26])
    link('thermal-return','Re-heater → regenerator inspection return',heater(118,1),regen2(48,-1),[[-38,0,127],[-68,15,127],[-68,15,39],[-54,10,39]],'A26',[.35,.65,.65])
    # These harnesses mate to the existing blind pump stubs. Explicitly record
    # blind terminations instead of pretending that these are flow connections.
    def harness(identity,name,points,ends,reference,color):
        points=rounded_route(points)
        seed=trimesh.creation.icosphere(subdivisions=2,radius=1.6);seed.apply_translation(points[0])
        p=part(identity,name,[seed],color,reference,points[len(points)//2])
        p['routes']=[dict(points=points,outer=1.6,bore=.8)]
        p['open_probes']=sample_route(points)
        # Contact at radial offset lies in both tube wall and the blind stub.
        for source,point in ends:contact(p,source,point,'Blind interface / static harness')
    harness('helium-link','He service harness · blind interfaces',
        [[-27,0,40],[-30,-10,40],[-30,-22,80],[-28,0,80]],
        [('helium-circulator',[-27.6,0,41.05]),('pre-burner',[-28.6,0,81.05])],'A27',[.73,.64,.30])
    harness('hydrogen-line','Hydrogen service harness · blind interfaces',
        [[48,0,68],[51,-8,68],[51,-38,80],[-24,-38,80],[-28,0,80]],
        [('hydrogen-pump',[48,0,69.05]),('pre-burner',[-28.6,0,81.05])],'A28',[.73,.46,.31])
    harness('oxygen-line','LOX service harness · blind interfaces',
        [[47.5,-15,100],[52,-15,100],[52,-36,111],[-24,-36,111],[-27,0,111]],
        [('lox-pump',[47.4,-15,101.05]),('re-heater',[-27.6,0,112.05])],'A29',[.28,.55,.79])
    # Separate connected manufacturing subassemblies keep native mesh audits
    # within memory bounds. Their mating overlaps are audited like other joints.
    seeds=frame['seeds'];beams=frame['beams'];opens=frame['open_probes']
    seed=trimesh.creation.icosphere(subdivisions=2,radius=1.8);seed.apply_translation([-30,-7,24])
    frame.update(name='Left accessory mounting frame',seeds=[seed],beams=[],contact_probes=[],open_probes=[])
    right=part('mount-frame-right','Right accessory mounting frame',[seeds[4]],[.37,.43,.49],'A30',[30,-7,80])
    aft=part('aft-coupling','Aft housing + hollow static drive carrier',seeds[:4],[.48,.49,.53],'A31',[0,-16,131])
    aft['open_probes']=opens
    for b in beams:
        a=b[0]
        destination=(frame if a[0]<0 else right) if abs(a[0])>=29.9 and a[2]<125 else aft
        destination['beams'].append(b)
    for j in joints:
        if j['part']!='mount-frame':continue
        target=aft if j['source'] in ('air-compressor','drive-turbine','bell-chamber','heat-shield') else right if j['point_mm'][0]>0 else frame
        j['part']=target['id'];target['contact_probes']+=j['probes']
    contact(right,'half-a',[24.5,.7,24],'Right frame casing mount')
    for p,x in [(frame,-18),(right,18)]:
        contact(p,'aft-coupling',[x,0,123],'Frame to aft housing')
        aft['contact_probes']+=interior_probes([x,0,123])
    drive=part('static-drive','Hollow static drive carrier',aft['seeds'][1:],[.54,.52,.60],'A32',[3,0,91])
    aft['seeds']=aft['seeds'][:1];aft['name']='Aft transition housing + shield supports'
    drive['beams']=[b for b in aft['beams'] if b[0][2]==64.5]
    aft['beams']=[b for b in aft['beams'] if b[0][2]!=64.5]
    drive['open_probes']=aft['open_probes'];aft['open_probes']=[]
    aft['contact_probes']=[]
    for j in joints:
        if j['part']=='aft-coupling':
            destination=drive if j['source'] in ('air-compressor','drive-turbine') else aft
            j['part']=destination['id'];destination['contact_probes']+=j['probes']
        elif j['source']=='aft-coupling':aft['contact_probes']+=j['probes']
    contact(drive,'aft-coupling',[2.9,0,121],'Static drive to housing web')
    aft['contact_probes']+=interior_probes([2.9,0,121])
    for p in parts:
        if p['routes']:p['bore_end_extension_mm']=3.2
    return parts,joints


def generate_integration(folder,options=None,progress=lambda message:None):
    base=ROOT/'data/prints'/BASE_RUN
    manifest=json.loads((base/'manifest.json').read_text())
    if json.loads((ROOT/'data/print-jobs'/(BASE_RUN+'.json')).read_text())['status']!='complete':raise ValueError('Accepted assembly unavailable')
    folder.mkdir(parents=True,exist_ok=False)
    report=json.loads((base/'report.json').read_text());design=report['recipe']
    travel=float((options or {}).get('centrebody_mm',0))
    if travel!=design['intake']['centrebody_mm']:raise ValueError('This integrated build uses the accepted centrebody position; ±4 mm remains a preview')
    parts,joints=specification()
    progress('Checking actual source-mesh contact points for every fixed component')
    for joint in joints:
        source=joint['source']
        if source in PART_IDS:continue
        if source.startswith('half-'):
            body=next(b for b in report['bodies'] if b['component_id']==source)
            path=base/'scene.stl';first=body['first_triangle'];count=body['triangle_count']
        else:path=base/(source+'.stl');first=0;count=None
        if not all(inside_stl(path,joint['probes'],first,count)):raise ValueError('Source contact failed: '+source+' '+str(joint['point_mm']))
        joint['source_mesh_contact']='passed'
    config=[];input_evidence={}
    for p in parts:
        meshes=p.pop('seeds');mesh=trimesh.util.concatenate(meshes);path=folder/(p['id']+'.input.stl');mesh.export(path)
        input_evidence[p['id']]=dict(triangles=len(mesh.faces),sha256=digest(path))
        config.append(p)
    (folder/'integration-input.json').write_text(json.dumps(dict(parts=config)))
    progress('Voxelizing mounting frame, transitions and hollow routes at 0.1 mm')
    with (folder/'integration-native.log').open('w') as log:
        result=subprocess.run([str(DOTNET),str(DLL),'integrate',str(folder/'integration-input.json'),str(folder),'0.1'],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,timeout=900)
    if result.returncode:raise ValueError((folder/'integration-native.log').read_text()[-1800:])
    native=json.loads((folder/'integration-native.json').read_text())
    if native['boolean_reference_samples']!=15:raise ValueError('Boolean acceptance failed')
    for record in native['components']:
        if record['voxel_mm']!=.1 or record['triangle_input_count']!=input_evidence[record['id']]['triangles']:
            raise ValueError('Integration mesh-to-voxel evidence mismatch')
    changed={'recipe.json','report.json','PRINT.txt','vega-one-print-kit.zip'}
    for name,expected in manifest.items():
        if name in changed:continue
        if digest(base/name)!=expected:raise ValueError('Accepted artifact changed: '+name)
        os.link(base/name,folder/name)
    first=sum(b['triangle_count'] for b in report['bodies']);extension_count=0;cleanup={};display_paths=[]
    for p in parts:
        identity=p['id'];progress('Checking integrated '+p['name'])
        path=folder/(identity+'.stl')
        cleanup[identity]=clean_native(path,.1);gc.collect()
        mesh,check=inspect_mesh(path);check['voxel_mm']=.1;report['components'][identity]=check
        lod,reduced=display_mesh(mesh,120000 if identity in ('mount-frame','mount-frame-right','aft-coupling','static-drive') else 18000)
        target=folder/(identity+'.display.stl');lod.export(target);display_paths.append(target)
        count=len(lod.faces);report['display_meshes'][identity]=dict(source_triangles=len(mesh.faces),display_triangles=count,decimated=reduced)
        report['bodies'].append(dict(component_id=identity,name=p['name'],first_triangle=first+extension_count,triangle_count=count,color=p['color'],voxel_mm=.1))
        design['components'].append({k:p[k] for k in ['id','name','color','anatomy_reference','review_anchor_mm','voxel_mm']})
        extension_count+=count;del mesh,lod;gc.collect()
    for j in joints:
        if j['source'] in PART_IDS:
            if not all(inside_stl(folder/(j['source']+'.stl'),j['probes'])):raise ValueError('Integration joint missed: '+j['source'])
            j['source_mesh_contact']='passed'
    for p in parts:
        if not all(inside_stl(folder/(p['id']+'.stl'),p['contact_probes'])):
            raise ValueError('Exported connector lost material contact: '+p['id'])
    if first+extension_count>6_000_000:raise ValueError('Display triangle budget exceeded')
    with (folder/'integration-scene.stl').open('wb') as dst,(folder/'integration-normals.bin').open('wb') as normals:
        dst.write(b'Vega assembly integration display'.ljust(80,b'\0'));dst.write(struct.pack('<I',extension_count))
        for path in display_paths:
            mesh=trimesh.load_mesh(path,process=True);append_smooth_normals(mesh,normals)
            with path.open('rb') as src:src.seek(84);shutil.copyfileobj(src,dst)
            del mesh;gc.collect();path.unlink()
    # Every fixed original surface has an audited material-overlap path to frame.
    fixed={b['component_id'] for b in report['bodies']} - {'centrebody'}
    edges=[(j['part'],j['source']) for j in joints];seen={'mount-frame'}
    while True:
        expanded=seen|{b for a,b in edges if a in seen}|{a for a,b in edges if b in seen}
        if expanded==seen:break
        seen=expanded
    if seen!=fixed:raise ValueError('Detached assembly nodes: '+str(fixed-seen))
    design.update(revision=9,schema_version=9)
    design['design_changes']=dict(baseline_run=BASE_RUN,description='Integrated static assembly: common mounting frame, aft transition, hollow drive carrier, spill coupling and routed service connections at 0.1 mm.')
    design['recipe_sha256']=fingerprint({k:v for k,v in design.items() if k!='recipe_sha256'})
    report.update(base_run=BASE_RUN,scene_extension='integration-scene.stl',scene_extension_sha256=digest(folder/'integration-scene.stl'),
        integration_native=native,integration_native_binary_sha256=digest(DLL),integration_input_meshes=input_evidence,integration_cleanup=cleanup,
        integration=dict(status='static_material_connections_passed',joints=joints,fixed_parts_connected=len(seen),
            source_contact_probes=sum(len(j['probes']) for j in joints),probe_offset_mm=.12,
            moving_joint=dict(part='centrebody',type='sliding guide',shaft_nominal_radial_gap_mm=.5,web_nominal_radial_gap_mm=.2,sampled_stem_envelope_radius_mm=2.2,travel_mm=[-4,4],scope='New shaft and carrier were sampled around the stem travel. Manufactured clearance and guide contact remain unverified.'),
            fluid_scope='Four hollow canister links form an inspection loop. He, hydrogen and LOX harnesses terminate at inherited blind machinery ports. No complete working-fluid circuit or pump operation is established.',
            validation_scope='Sampled material overlap, individual mesh topology and route-centerline openness. Sealing, assembly tolerances, full clearance and structural strength remain unverified.'),
        assembly_scope='Mechanically connected static review assembly with an intentional sliding centrebody joint. No operating engine performance is established.')
    (folder/'recipe.json').write_text(json.dumps(design,indent=2))
    (folder/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    guide='REVISION 9 — STATIC ASSEMBLY INTEGRATION\n\nUse the revision 8 base kit ('+BASE_RUN+') plus these eleven integration STLs, in their shared assembly coordinates. This is a review overlay with intentional overlapping contact regions, not a fastened or toleranced production assembly. New geometry uses 0.1 mm PicoGK voxels. The original movable centrebody retains a sliding joint.\n\nFour tapered annular canister links have sampled open bores. The He, hydrogen and LOX harnesses end at BLIND original machinery stubs. Their presence does not establish a working fluid circuit. No firing, pressure, cryogenic, leakage or structural qualification is implied. Existing CFD/FEA only cover the intake and centrebody.\n\nThe browser combines the immutable base scene.stl with integration-scene.stl. Component STL downloads retain native resolution. The integration kit contains additions only; base parts are available from the previous run and individual downloads.\n'
    (folder/'PRINT.txt').write_text(guide,encoding='utf-8')
    progress('Packing the integration additions and contact report')
    with zipfile.ZipFile(folder/'vega-one-print-kit.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as kit:
        for name in [p+'.stl' for p in PART_IDS]+['recipe.json','report.json','PRINT.txt']:kit.write(folder/name,name)
    return report
