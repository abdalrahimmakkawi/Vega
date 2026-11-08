"""Vega rocket workbench: loopback and fixed native commands only."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, re, subprocess, threading, uuid, sys, socket, tempfile, time, secrets
from dataclasses import asdict
from vega.rocket import RocketBrief, design, mesh, solve
from vega.combined_cycle import screen_combined_cycle
from vega.assembly_export import export_assembly, assembly_artifact_valid
from vega.meshing.study import build_study, artifact_path
from vega.run_index import run_summaries
from vega.system_contract import build_system_contract
from vega.geometry_compare import compare_runs
from vega.computational_model import build_model_trace
from vega.design_search import explore, VARIABLES
from vega.runtime import readiness
from vega.manufacturing import catalog
from vega.stl import validate_binary_stl, surface_acceptable
from vega.preview import geometry_preview
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
PORT=int(os.environ.get('VEGA_PORT','8711'))
DLL=ROOT/'integrations/bin/Release/net9.0/Vega.Native.dll'
POOL=ThreadPoolExecutor(max_workers=1)
JOBS={};LOCK=threading.Lock()


def save_job(identity, state):
    folder=DATA/'jobs';folder.mkdir(exist_ok=True)
    target=folder/(identity+'.json')
    temporary=folder/(identity+'.'+uuid.uuid4().hex+'.tmp')
    with temporary.open('w',encoding='utf-8') as stream:
        json.dump({'schema_version':1, **state},stream,allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(target)


def job_state(identity):
    if not re.fullmatch('[a-f0-9]{32}',identity):return {'status':'unknown'}
    with LOCK:
        if identity in JOBS:return dict(JOBS[identity])
        try:
            state=json.loads((DATA/'jobs'/(identity+'.json')).read_text(encoding='utf-8'))
        except (OSError,ValueError):return {'status':'unknown'}
        if state.get('status') in ('queued','running'):
            for stage in state.get('stages',{}).values():
                if stage.get('status') in ('pending','running'):stage['status']='interrupted'
            state['status']='interrupted'
            state['message']='Server restarted; unfinished work was interrupted.'
            save_job(identity,state)
        JOBS[identity]=state
        return dict(state)



class JobCancelled(Exception):
    pass


def check_cancelled(identity):
    with LOCK:
        if JOBS.get(identity,{}).get('status')=='cancelled':
            raise JobCancelled('Generation cancelled; published artifacts retained.')


def cancel_job(identity):
    state=job_state(identity)
    if state.get('status')=='unknown':raise ValueError('Unknown job')
    with LOCK:
        state=JOBS[identity]
        if state.get('status') in ('queued','running'):
            state={**state,'status':'cancelled','cancelled_at':datetime.now(timezone.utc).isoformat(),
                'message':'Cancelled; a running native stage stops at its deadline or next stage boundary.'}
            JOBS[identity]=state
            save_job(identity,state)
        return dict(state)


def context(run):
    payload={'scene':mesh(run['candidates'][0]),'geometry_recipe':run['candidates'][0]['geometry'],'requirements':run['requirements'],'backend':hashlib.sha256(DLL.read_bytes()).hexdigest(),'voxel_mm':run['requirements'].get('mesh_voxel_mm',1.0)}
    identity=hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return payload,identity,DATA/'native'/f'{run["id"]}.stl'

def artifact(run):
    if not DLL.exists():return None
    _,identity,path=context(run);manifest=path.with_suffix('.manifest.json')
    if not manifest.exists() or not path.exists():return None
    try:m=json.loads(manifest.read_text())
    except (ValueError,OSError):return None
    scene=Path(str(path)+'.scene.stl')
    step=path.with_suffix('.envelope.step')
    return m if (m.get('input_sha256')==identity and
                 m.get('stl_sha256')==hashlib.sha256(path.read_bytes()).hexdigest() and
                 scene.exists() and m.get('scene_sha256')==hashlib.sha256(scene.read_bytes()).hexdigest() and
                 (not m.get('cad_reference') or
                  (step.exists() and m['cad_reference']['step_sha256']==hashlib.sha256(step.read_bytes()).hexdigest()))) else None

def native_export(run):
    if not DLL.exists():raise ValueError('Build the PicoGK bridge before generating a rocket concept.')
    payload,identity,path=context(run);path.parent.mkdir(exist_ok=True)
    bundle=path.with_suffix('.input.json');bundle.write_text(json.dumps({'geometry_scene':payload['scene'],'geometry_recipe':payload['geometry_recipe'],'native_export':{'input_sha256':identity}}))
    runtime=ROOT/'.tools/dotnet/dotnet.exe'
    result=subprocess.run([str(runtime),str(DLL),'rocket',str(bundle),str(path),str(payload['voxel_mm'])],cwd=ROOT,capture_output=True,text=True,timeout=240)
    if result.returncode:raise ValueError('PicoGK failed: '+result.stderr[-1500:])
    data=path.read_bytes()
    count=validate_binary_stl(data)
    m={'backend':'PicoGK','input_sha256':identity,'stl_sha256':hashlib.sha256(data).hexdigest(),'triangles':count,'voxel_mm':payload['voxel_mm'],'engineering_validated':False}
    scene=Path(str(path)+'.scene.stl')
    if not scene.exists():raise ValueError('PicoGK did not return a component inspection scene')
    scene_data=scene.read_bytes()
    checks=json.loads(Path(str(path)+'.checks.json').read_text())
    scene_count=validate_binary_stl(scene_data, checks['bodies'])
    if scene_count>4000000:raise ValueError('Native component mesh exceeds four million triangles; increase native voxel pitch')
    m['scene_sha256']=hashlib.sha256(scene_data).hexdigest()
    m['scene_triangles']=scene_count
    m['bodies']=checks['bodies']
    m['library_execution']=checks['library_execution']
    m['route_audit']={'feed_centerline_samples':checks.get('feed_centerline_samples',0),
                      'cooling_centerline_samples':checks.get('passage_centerline_samples',0),
                      'radial_ligament_samples':checks.get('radial_ligament_samples',0),
                      'radial_ligament_failures':checks.get('radial_ligament_failures',0),
                      'sampled_ligaments_clear':checks.get('radial_ligament_failures',0)==0 and checks.get('radial_ligament_samples',0)>0,
                      'sampled_paths_clear':True,
                      'scope':'Centerline obstruction and sparse radial ligament sampling only; neither proves leak-tightness or global minimum wall thickness.'}
    flow=Path(str(path)+'.flow.stl')
    if flow.exists():m['flow_sha256']=hashlib.sha256(flow.read_bytes()).hexdigest()
    m['library_revisions']=json.loads((ROOT/'vendor/libraries.lock.json').read_text())
    executed=' '.join(str(call.get('library','')) for call in m['library_execution'])
    m['library_status']={name:('executed' if name in executed else 'installed_not_selected')
                         for name in ('PicoGK','ShapeKernel','LatticeLibrary','QuasiCrystals')}
    sys.path.insert(0,str(ROOT/'.tools/python'))
    import trimesh
    audited=trimesh.load_mesh(str(path),process=True)
    shells=audited.split(only_watertight=False)
    m['mesh_audit']={'library':'Trimesh','watertight':bool(audited.is_watertight),
        'winding_consistent':bool(audited.is_winding_consistent),
        'connected_components':len(shells),'outer_shells':int(sum(s.volume>0 for s in shells)),
        'internal_void_shells':int(sum(s.volume<0 for s in shells)),
        'shell_signed_volumes_mm3':[float(s.volume) for s in shells],
        'signed_volume_mm3':float(audited.volume)}
    recipe_file=path.with_suffix('.profile.json')
    recipe_file.write_text(json.dumps(payload['geometry_recipe']))
    cad_results=[]
    step_file=path.with_suffix('.envelope.step')
    for backend in ('cadquery','build123d'):
        cad=subprocess.run([sys.executable,str(ROOT/'integrations/reference_cad.py'),backend,
                            str(recipe_file),str(step_file)],cwd=ROOT,capture_output=True,text=True,timeout=90)
        if cad.returncode:raise ValueError(backend+' reference profile failed: '+cad.stderr[-600:])
        cad_results.append(json.loads(cad.stdout.strip().splitlines()[-1]))
    volumes=[r['pressure_shell_envelope_volume_mm3'] for r in cad_results]
    discrepancy=abs(volumes[0]-volumes[1])/max(volumes)
    if discrepancy>1e-6:raise ValueError('CAD backends disagree on pressure-shell envelope volume')
    m['cad_reference']={'checks':cad_results,'relative_volume_discrepancy':discrepancy,
                        'scope':'Profile-only reference, not the full PicoGK component model',
                        'step_sha256':hashlib.sha256(step_file.read_bytes()).hexdigest()}
    path.with_suffix('.manifest.json').write_text(json.dumps(m));return m

def evaluate_design(brief,screening=False):
    with tempfile.TemporaryDirectory(prefix='vega-eval-') as folder:
        request=Path(folder)/'brief.json';output=Path(folder)/'run.json'
        request.write_text(json.dumps(asdict(brief)))
        try:
            result=subprocess.run([sys.executable,str(ROOT/'integrations/evaluate_design.py'),str(request),str(output)]+(['--screening'] if screening else []),
                                  cwd=ROOT,capture_output=True,text=True,timeout=120)
        except subprocess.TimeoutExpired:
            raise ValueError('Design evaluation exceeded 120 seconds; candidate rejected')
        if result.returncode:raise ValueError('Design evaluation failed: '+result.stderr[-1800:])
        return json.loads(output.read_text())

def run_job(identity,brief,computed=None,on_progress=None,on_ready=None):
    timings={}
    def stage(name,operation):
        check_cancelled(identity)
        started=time.monotonic()
        with LOCK:
            state=JOBS.setdefault(identity,{})
            state.setdefault('stages',{})[name]={'status':'running','started_at':datetime.now(timezone.utc).isoformat()}
            state['current_stage']=name
            state['heartbeat_at']=datetime.now(timezone.utc).isoformat()
            save_job(identity,state)
        outcome='failed';error=None
        try:
            result=operation()
            outcome='succeeded'
            return result
        except Exception as failure:
            error=str(failure)
            raise
        finally:
            timings[name]={'wall_seconds':time.monotonic()-started}
            with LOCK:
                state=JOBS.setdefault(identity,{})
                state['stages'][name].update(status='cancelled' if state.get('status')=='cancelled' else outcome,finished_at=datetime.now(timezone.utc).isoformat(),error=error)
                state['timings']=dict(timings)
                save_job(identity,state)
    def update(message):
        check_cancelled(identity)
        with LOCK:
            JOBS[identity]={**JOBS.get(identity,{}),'status':'running','message':message}
            save_job(identity,JOBS[identity])
        if on_progress:on_progress(message)
    try:
        update('Solving rocket nozzle and component geometry…')
        run=computed if computed is not None else stage('evaluation',lambda:evaluate_design(brief));run['id']=identity;run['created_at']=datetime.now(timezone.utc).isoformat()
        update('PicoGK is voxelizing the rocket component scene…')
        run['artifact']=stage('native_export_and_audit',lambda:native_export(run));run['execution']['picogk']='computed'
        update('Building the connected Vega assembly and topology report…')
        if run['candidates'][0].get('assembly',{}).get('screening_only'):
            # Publish the exact native core before spending time on CAD walls.
            run['assembly_artifact']=None
            run['mesh_study']={'status':'pending','reason':'Core mesh ready; selected assembly CAD is building.'}
            run['execution']['connected_assembly']='pending'
            run['computational_model']=build_model_trace(run)
            tmp=DATA/f'{identity}.tmp';tmp.write_text(json.dumps(run));tmp.replace(DATA/f'{identity}.json')
            if on_ready:on_ready(identity)
            update('Core mesh ready; building selected assembly CAD (120 second limit)…')
            try:
                full=stage('assembly_construction',lambda:evaluate_design(brief))
                for key in ('id','created_at','artifact'):full[key]=run[key]
                run=full
            except Exception as error:
                run['warnings'].append('Selected assembly CAD failed: '+str(error))
                run['candidates'][0]['assembly']={'status':'failed','reason':str(error)}
        run['assembly_artifact']=stage('assembly_export',lambda:export_assembly(run,ROOT))
        run['execution']['connected_assembly']='computed' if run['assembly_artifact'] else run['candidates'][0]['assembly']['status']
        run['mesh_study']={'status':'pending','reason':'Hardware mesh available; analysis has not completed.'}
        run['execution']['hybrid_mesh_study']='pending'
        audit=run['artifact']['mesh_audit']
        run['execution']['trimesh_audit']='passed' if audit['watertight'] else 'open_mesh'
        run['execution']['geometry_connectivity']='one_outer_shell' if audit['outer_shells']==1 else f"{audit['outer_shells']}_outer_shells"
        run['execution']['mesh_integrity_screen']='surface_pass' if surface_acceptable(audit) else 'failed'
        run['execution']['sampled_flow_routes']='clear' if run['artifact']['route_audit']['sampled_paths_clear'] else 'blocked'
        has_cooling=bool(run['requirements']['cooling_passages'])
        run['execution']['sampled_wall_ligaments']=('screen_pass' if run['artifact']['route_audit']['sampled_ligaments_clear'] else 'screen_failed') if has_cooling else 'not_requested'
        if has_cooling and not run['artifact']['route_audit']['sampled_ligaments_clear']:
            run['warnings'].append('The sparse PicoGK cooling-channel ligament screen failed or did not run; inspect the actual wall before fabrication.')
        if not audit['watertight']:run['warnings'].append('The combined PicoGK STL has open edges; do not fabricate or simulate it as a closed solid.')
        if not audit['winding_consistent']:run['warnings'].append('The PicoGK mesh has inconsistent face winding; the surface integrity screen failed.')
        if audit['outer_shells']>1:run['warnings'].append(f"The PicoGK mesh has {audit['outer_shells']} separate outer shells; material continuity is not established.")
        if audit['internal_void_shells']>0:run['warnings'].append(f"The mesh has {audit['internal_void_shells']} enclosed void shell(s); inspect trapped volumes and powder-removal access before manufacture.")
        run['execution']['cadquery_reference']='computed';run['execution']['build123d_cross_check']='computed'
        run['system_contract']=build_system_contract(run)
        run['execution']['system_contract']='connected_unvalidated'
        run['computational_model']=build_model_trace(run)
        tmp=DATA/f'{identity}.tmp';tmp.write_text(json.dumps(run));tmp.replace(DATA/f'{identity}.json')
        if on_ready:on_ready(identity)
        try:run['mesh_study']=stage('analysis',lambda:build_study(run,ROOT,update))
        except Exception as error:run['mesh_study']={'status':'failed','reason':str(error)}
        run['execution']['hybrid_mesh_study']=run['mesh_study']['status']
        run['computational_model']=build_model_trace(run)
        tmp=DATA/f'{identity}.tmp';tmp.write_text(json.dumps(run));tmp.replace(DATA/f'{identity}.json')
        check_cancelled(identity)
        failed_assembly=run['execution']['connected_assembly'] != 'computed'
        failed_analysis=run['mesh_study'].get('status') in ('failed','solver_failed','unsupported_section','computed_not_converged')
        with LOCK:
            JOBS[identity]={**JOBS.get(identity,{}),'status':'partial' if failed_assembly or failed_analysis else 'complete','run_id':identity}
            save_job(identity,JOBS[identity])
    except JobCancelled:
        return
    except Exception as error:
        with LOCK:
            if JOBS.get(identity,{}).get('status')=='cancelled':return
            JOBS[identity]={**JOBS.get(identity,{}),'status':'failed','error':str(error)}
            save_job(identity,JOBS[identity])

def search_job(identity,brief):
    ready=[];early={};started=time.monotonic()
    def progress(message):
        check_cancelled(identity)
        print(f'[{identity[:8]}] {message}',flush=True)
        with LOCK:
            JOBS[identity]={**JOBS.get(identity,{}),'status':'running','message':message,'available_run_ids':list(ready),'elapsed_seconds':round(time.monotonic()-started)}
            save_job(identity,JOBS[identity])
    ledger={}
    def record_attempt(record):
        check_cancelled(identity)
        index=record['proposal_index']
        ledger[index]={**ledger.get(index,{}),**record}
        with LOCK:
            JOBS[identity]={**JOBS.get(identity,{}),'attempts':[ledger[k] for k in sorted(ledger)]}
            save_job(identity,JOBS[identity])
    def available(child):
        if child not in ready:ready.append(child)
        progress('Hardware mesh available; continuing study')
    def first(item):
        child=uuid.uuid4().hex
        run_job(child,item['proposal'],item['run'],progress,available)
        with LOCK:result=dict(JOBS[child])
        if result['status']=='complete':early[item['geometry_sha256']]=child;return True
        progress('Candidate export failed: '+result.get('error','Unknown error'))
        return False
    try:
        selected,study=explore(brief,progress,evaluator=lambda b:evaluate_design(b,screening=True),compact=False,on_attempt=record_attempt)
        study['id']=identity;study['candidates']=[]
        folder=DATA/'studies';folder.mkdir(exist_ok=True)
        def persist_study():
            target=folder/(identity+'.json')
            temporary=folder/(identity+'.tmp')
            with temporary.open('w',encoding='utf-8') as stream:
                json.dump(study,stream,allow_nan=False)
                stream.flush();os.fsync(stream.fileno())
            temporary.replace(target)
        persist_study()
        for index,item in enumerate(selected):
            progress(f'Meshing distinct candidate {index+1}/{len(selected)} with PicoGK')
            child=early.get(item['geometry_sha256'])
            if not child:
                child=uuid.uuid4().hex
                try:
                    run_job(child,item['proposal'],item['run'],progress,available)
                except Exception as error:
                    with LOCK:
                        JOBS[child]={'status':'failed','error':str(error)}
                        save_job(child,JOBS[child])
            with LOCK:result=dict(JOBS[child])
            row={'run_id':child,'name':f"Candidate {index+1}",'parameters':{key:vars(item['proposal'])[key] for key in VARIABLES},
                 'failed_checks':item['failed_checks'],'unresolved_checks':item.get('unresolved_checks',[]),
                 'feasibility':item.get('feasibility','unresolved'),'score':item['score'],'geometry_sha256':item['geometry_sha256'],
                 'status':result['status'],'error':result.get('error')}
            if result['status'] in ('complete','partial'):
                saved=json.loads((DATA/f'{child}.json').read_text())
                row['mesh_sha256']=saved['artifact']['scene_sha256']
                row['mesh_status']=saved['execution']['mesh_integrity_screen']
                row['ligament_status']=saved['execution']['sampled_wall_ligaments']
                candidate=saved['candidates'][0]
                row['dimensions_mm']=candidate['dimensions']
                row['hot_wall_k']=candidate['engineering']['thermal']['estimated_hot_wall_k']
                row['stress_utilization']=candidate['engineering']['structural_screen']['utilization']
            study['candidates'].append(row)
            persist_study()
        complete=[row for row in study['candidates'] if row['status'] in ('complete','partial')]
        study['feasible_count']=sum(a.get('feasibility')=='screen_pass' for a in study.get('attempts',[]))
        study['exported_count']=len(complete)
        study['distinct_native_meshes']=len({row['mesh_sha256'] for row in complete})
        for row in complete:
            path=DATA/(row['run_id']+'.json');saved=json.loads(path.read_text());saved['design_study']=study
            tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(saved));tmp.replace(path)
        folder=DATA/'studies';folder.mkdir(exist_ok=True)
        tmp=folder/(identity+'.tmp');tmp.write_text(json.dumps(study));tmp.replace(folder/(identity+'.json'))
        diversity_incomplete=study['distinct_native_meshes']<2
        with LOCK:
            JOBS[identity]={**JOBS.get(identity,{}),'status':'partial' if diversity_incomplete or any(row['status']!='complete' for row in study['candidates']) else 'complete','run_id':complete[0]['run_id'] if complete else None,'study_id':identity,'candidate_count':len(complete),'available_run_ids':ready}
            if diversity_incomplete:JOBS[identity]['message']='Fewer than two distinct native meshes succeeded; inspect the saved results.'
            save_job(identity,JOBS[identity])
    except JobCancelled:
        return
    except Exception as error:
        with LOCK:
            if JOBS.get(identity,{}).get('status')=='cancelled':return
            JOBS[identity]={**JOBS.get(identity,{}),'status':'failed','error':str(error),'available_run_ids':ready}
            report=getattr(error,'report',None)
            if report is not None:JOBS[identity]['search_report']=report
            save_job(identity,JOBS[identity])


def read_run(identity):
    if not re.fullmatch('[a-f0-9]{32}',identity):raise ValueError('Invalid run id')
    r=json.loads((DATA/f'{identity}.json').read_text())
    if r.get('kind') not in ('rocket','spacecraft'):raise ValueError('Unsupported study kind')
    r['artifact']=artifact(r);r['execution']['picogk']='computed' if r['artifact'] else 'stale'
    if r['artifact'] and 'mesh_audit' in r['artifact']:
        if 'library_status' not in r['artifact']:
            executed=' '.join(str(call.get('library','')) for call in r['artifact'].get('library_execution',[]))
            r['artifact']['library_status']={name:('executed' if name in executed else 'installed_not_selected')
                                              for name in ('PicoGK','ShapeKernel','LatticeLibrary','QuasiCrystals')}
        audit=r['artifact']['mesh_audit']
        r['execution']['trimesh_audit']='passed' if audit['watertight'] else 'open_mesh'
        r['execution']['geometry_connectivity']='one_outer_shell' if audit.get('outer_shells')==1 else f"{audit.get('outer_shells','unknown')}_outer_shells"
        r['execution']['mesh_integrity_screen']='surface_pass' if surface_acceptable(audit) else 'failed'
        r['execution']['sampled_flow_routes']='clear' if r['artifact'].get('route_audit',{}).get('sampled_paths_clear') else 'not_recorded'
        route=r['artifact'].get('route_audit',{})
        r['execution']['sampled_wall_ligaments']=('screen_pass' if route.get('sampled_ligaments_clear') else 'not_recorded') if r['requirements'].get('cooling_passages') else 'not_requested'
        if not audit['watertight'] and not any('open edges' in w for w in r['warnings']):
            r['warnings'].append('The combined PicoGK STL has open edges; do not fabricate or simulate it as a closed solid.')
        if audit.get('outer_shells',0)>1 and not any('separate outer shells' in w for w in r['warnings']):
            r['warnings'].append(f"The PicoGK mesh has {audit['outer_shells']} separate outer shells; material continuity is not established.")
        if audit.get('internal_void_shells',0)>0 and not any('enclosed void shell' in w for w in r['warnings']):
            r['warnings'].append(f"The mesh has {audit['internal_void_shells']} enclosed void shell(s); inspect trapped volumes and powder-removal access before manufacture.")
    if r.get('assembly_artifact') and not assembly_artifact_valid(r,ROOT):
        r['assembly_artifact']=None;r['execution']['connected_assembly']='stale'
    if r.get('system_contract'):
        try:
            current=build_system_contract(r)
            if r['system_contract'].get('schema_version')!=current['schema_version']:
                r['system_contract']=current
                r['execution']['system_contract']='connected_unvalidated_contract_refreshed'
            elif current['contract_sha256']!=r['system_contract']['contract_sha256']:
                raise ValueError('Saved system identity changed')
            else:
                r['execution']['system_contract']='connected_unvalidated'
        except (ValueError,KeyError,TypeError):
            r['system_contract']['status']='stale'
            r['execution']['system_contract']='stale'
    r['computational_model']=build_model_trace(r)
    return r

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def allowed(self):return self.headers.get('Host') in (f'127.0.0.1:{PORT}',f'localhost:{PORT}')
    def send(self,data,status=200,mime='application/json'):
        body=json.dumps(data).encode() if mime=='application/json' else data
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; worker-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if not self.allowed():return self.send({'error':'Invalid host'},403)
        try:
            if self.path=='/api/materials':return self.send(catalog())
            if self.path=='/api/health':return self.send(readiness())
            if self.path=='/api/runs':
                return self.send(run_summaries(DATA))
            if re.fullmatch(r'/api/design-studies/[a-f0-9]{32}',self.path):
                return self.send(json.loads((DATA/'studies'/(self.path.rsplit('/',1)[1]+'.json')).read_text()))
            if self.path.startswith('/api/jobs/'):
                return self.send(job_state(self.path.rsplit('/',1)[1]))
            if self.path.startswith('/api/runs/'):
                parts=self.path.strip('/').split('/');run=read_run(parts[2])
                if len(parts)==3:return self.send(run)
                if len(parts)==5 and parts[3]=='compare':
                    return self.send(compare_runs(read_run(parts[4]),run,ROOT))
                if len(parts)!=4:raise ValueError('Unknown route')
                if parts[3]=='mesh':return self.send(mesh(run['candidates'][0]))
                if parts[3]=='bundle':return self.send({**run,'geometry_scene':mesh(run['candidates'][0])})
                if parts[3] in ('analysis-mesh','volume-mesh','airpath-analysis-mesh','airpath-volume-mesh','mesh-study-download'):
                    name={'analysis-mesh':'scene.json','volume-mesh':'selected.msh',
                          'airpath-analysis-mesh':'airpath-scene.json','airpath-volume-mesh':'airpath.msh',
                          'mesh-study-download':'engineering-mesh.zip'}[parts[3]]
                    p=artifact_path(run,ROOT,name)
                    if name.endswith('scene.json'):return self.send(json.loads(p.read_text()))
                    return self.send(p.read_bytes(),mime='application/zip' if name.endswith('.zip') else 'application/octet-stream')
                if parts[3]=='assembly-native':
                    if not run.get('assembly_artifact'):return self.send({'error':'No current connected assembly; generate a study.'},409)
                    return self.send((DATA/'native'/f'{run["id"]}.assembly.stl').read_bytes(),mime='model/stl')
                if parts[3] in ('native','solid','checks','flow','envelope'):
                    if not run['artifact']:return self.send({'error':'Native artifact is stale. Generate a new run.'},409)
                    path=DATA/'native'/f'{run["id"]}.stl'
                    if parts[3]=='flow':
                        flow=Path(str(path)+'.flow.stl')
                        if not flow.exists() or hashlib.sha256(flow.read_bytes()).hexdigest()!=run['artifact'].get('flow_sha256'):return self.send({'error':'No verified passage volume for this run'},404)
                        return self.send(flow.read_bytes(),mime='model/stl')
                    if parts[3]=='native':return self.send(Path(str(path)+'.scene.stl').read_bytes(),mime='model/stl')
                    if parts[3]=='solid':return self.send(path.read_bytes(),mime='model/stl')
                    if parts[3]=='envelope':return self.send(path.with_suffix('.envelope.step').read_bytes(),mime='application/step')
                    return self.send(json.loads(Path(str(path)+'.checks.json').read_text()))
                raise ValueError('Unknown route')
            files={'/':'rocket.html','/rocket.js':'rocket.js','/rocket.css':'rocket.css','/renderer.js':'renderer.js','/mesh-worker.js':'mesh-worker.js'}
            if self.path not in files:return self.send({'error':'Not found'},404)
            file=ROOT/'web'/files[self.path]
            return self.send(file.read_bytes(),mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}[file.suffix])
        except (ValueError,OSError,IndexError) as e:return self.send({'error':str(e)},400)
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=10000:return self.send({'error':'Invalid payload size'},400)
            self.connection.settimeout(10);raw=self.rfile.read(length)
            if not self.allowed():return self.send({'error':'Invalid host'},403)
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):return self.send({'error':'Cross-origin writes disabled'},403)
            if re.fullmatch(r'/api/jobs/[a-f0-9]{32}/cancel',self.path):
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send({'error':'JSON required'},415)
                json.loads(raw)
                return self.send(cancel_job(self.path.split('/')[3]))
            if self.path not in ('/api/rocket/runs','/api/mission/preview','/api/geometry/preview','/api/design-studies'):return self.send({'error':'Not found'},404)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send({'error':'JSON required'},415)
            request=json.loads(raw)
            if self.path=='/api/design-studies' and isinstance(request,dict) and 'search_seed' not in request:
                request['search_seed']=secrets.randbits(32)
            b=RocketBrief.parse(request)
            if self.path=='/api/geometry/preview':
                with LOCK:
                    if any(j['status'] in ('queued','running') for j in JOBS.values()):return self.send({'error':'Wait for the current mesh generation before previewing.'},409)
                return self.send(POOL.submit(geometry_preview,b).result())
            if self.path=='/api/mission/preview':
                # CEA uses shared files. Preview through the same single-worker
                # queue as generation, keeping native jobs and chemistry serial.
                def preview():
                    return design(b)['candidates'][0]['vehicle_screen']
                return self.send(POOL.submit(preview).result())
            identity=uuid.uuid4().hex
            with LOCK:
                if any(j['status'] in ('queued','running') for j in JOBS.values()):return self.send({'error':'A generation is running'},409)
                JOBS[identity]={'status':'queued','requirements':asdict(b),'kind':'search' if self.path=='/api/design-studies' else 'single','created_at':datetime.now(timezone.utc).isoformat()}
                save_job(identity,JOBS[identity])
            POOL.submit(search_job if self.path=='/api/design-studies' else run_job,identity,b);return self.send({'id':identity},202)
        except (ValueError,TypeError,AttributeError) as e:return self.send({'error':str(e)},400)

class VegaServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can allow several processes to bind the same port,
    # leaving users connected to an older build even after a new server starts.
    allow_reuse_address = False

    def server_bind(self):
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


if __name__=='__main__':
    with VegaServer(('127.0.0.1',PORT),Handler) as httpd:
        print(f'Vega computational engineering workbench 0.30: http://127.0.0.1:{PORT}',flush=True)
        httpd.serve_forever()

