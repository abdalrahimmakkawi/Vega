"""Loopback workbench for one printable, non-firing Vega demonstrator."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
import re
import secrets
import shutil
import threading
import time
import uuid

from vega.demonstrator import ROOT, recipe
from vega.print_export import generate, digest
from vega.runtime import readiness
from vega.analysis import analyze
from vega.architecture import generate_architecture, modules
from vega.integration import generate_integration, PART_IDS
from vega.bell_cooling import generate_cooling, COOLING_IDS
from vega.artifacts import physical, artifact_digest, artifact_size, open_artifact
from vega.cooling_simulation import assembly_network
from vega.concept_systems import modules as concept_modules
from vega.component_network import assessment, input_ledger
from vega.cfd_export import export_case
from vega import expanded_inlet

PORT = int(os.environ.get('VEGA_PORT', '8712'))
DATA = ROOT / 'data/prints'
STATES = ROOT / 'data/print-jobs'
DATA.mkdir(parents=True, exist_ok=True)
STATES.mkdir(parents=True, exist_ok=True)
POOL = ThreadPoolExecutor(max_workers=1)
LOCK = threading.Lock()
STATE_LOCK = threading.RLock()
JOBS = {}
TOKEN = secrets.token_urlsafe(32)
ACTIVE = None
ASSETS = {'/', '/rocket.html', '/rocket.css', '/rocket.js', '/renderer.js', '/mesh-worker.js'}
ARTIFACTS = {'half-a.stl', 'half-b.stl', 'assembled.stl', 'scene.stl',
             'recipe.json', 'report.json', 'PRINT.txt', 'vega-one-print-kit.zip',
             'input-body.stl','input-mesh.json','cem.json','scene-normals.bin','intake-detail.stl','analysis.json',
             'centrebody.stl','precooler.stl','air-compressor.stl','helium-circulator.stl','hydrogen-pump.stl'}
ARTIFACTS.update(part['id']+'.stl' for part in modules())
ARTIFACTS.update(part+'.stl' for part in PART_IDS)
ARTIFACTS.update({'integration-scene.stl','integration-normals.bin'})
ARTIFACTS.update(p+'.stl' for p in COOLING_IDS)
ARTIFACTS.update({'cooling-scene.stl','cooling-normals.bin','cooling-detail.stl','cooling-network.json','whole-engine-assessment.json'})
ARTIFACTS.update({'test-interface-scene.stl','test-interface-normals.bin','cooling-inlet-test-port.stl','cooling-return-test-port.stl','spill-outlet-nozzle.stl'})
ARTIFACTS.update(p['id']+'.stl' for p in concept_modules())
ARTIFACTS.update({'concept-frame-left.stl','concept-frame-right.stl'})
ARTIFACTS.update({'joint-scene.stl','joint-normals.bin','lh2-valve-coupling.stl','lox-valve-coupling.stl','compressor-hub-coupling.stl'})
ARTIFACTS.update({'core-service-carrier.stl','cold-air-supply.stl','cold-air-return.stl','cold-connection-checks.json'})
ARTIFACTS.add('connection-validation.json')
ARTIFACTS.add('component-network.json')
ARTIFACTS.add('engineering-inputs.json')
ARTIFACTS.update({'cfd-case.json','fluent-case.json','openfoam-case.zip'})
ARTIFACTS.update({'main-air-inlet.stl','inlet-normals.bin'})
ARTIFACTS.update({'cold-air-'+h+'-'+part+'.stl' for h in ['supply','return'] for part in ['left','right','bridge']})
ARTIFACTS.update({'cold-air-'+h+'-'+side+'-'+part+'.stl' for h in ['supply','return'] for side in ['left','right'] for part in ['lower','upper']})


def write_json(path, value):
    with STATE_LOCK:
        # Keep terminal status observable even if OneDrive/Windows keeps the
        # persisted file locked. Unique temporaries avoid competing writers.
        if path.parent == STATES:
            JOBS[path.stem] = dict(value)
        temporary = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')
        for attempt in range(10):
            try:
                temporary.replace(path)
                return
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(min(.025 * 2**attempt, .25))


def job(identity):
    with STATE_LOCK:
        if identity in JOBS:
            return dict(JOBS[identity])
        path = STATES / (identity + '.json')
        return json.loads(path.read_text()) if path.is_file() else None


def build(identity, options):
    global ACTIVE
    def progress(message):
        write_json(STATES / (identity + '.json'), dict(id=identity, status='running', message=message))
    try:
        folder = DATA / identity
        if options.get('expanded_inlet'):
            expanded_inlet.generate(folder,options['reference_flow_g_s'])
        elif options.get('bell_cooling'):
            generate_cooling(folder,options,progress)
        elif options.get('assembly_integration'):
            generate_integration(folder,options,progress)
        elif options.get('architecture_expansion'):
            generate_architecture(folder,options,progress)
        else:
            generate(folder, options, progress)
        network = assessment(json.loads((folder / 'report.json').read_text(encoding='utf-8')))
        if not network['validation']['topology_valid']:
            raise ValueError('Component topology failed: ' + '; '.join(network['validation']['errors']))
        write_json(folder / 'component-network.json', network)
        write_json(folder / 'engineering-inputs.json', input_ledger(network))
        export_case(folder, json.loads((folder / 'report.json').read_text(encoding='utf-8')), network)
        hashes = {name: artifact_digest(folder / name) for name in ARTIFACTS if physical(folder/name).is_file()}
        write_json(folder / 'manifest.json', hashes)
        write_json(DATA / 'latest.json', {'id': identity})
        write_json(STATES / (identity + '.json'), dict(id=identity, status='complete',
                   message='Mesh checks passed. Review the print guide and slicer preview.'))
    except Exception as error:
        write_json(STATES / (identity + '.json'), dict(id=identity, status='failed', message=str(error) or type(error).__name__))
    finally:
        with LOCK:
            ACTIVE = None


def verified_file(identity, name):
    folder = DATA / identity
    manifest = folder / 'manifest.json'
    state = job(identity)
    if not state or state['status'] != 'complete' or not manifest.is_file():
        return None
    path = folder / name
    hashes = json.loads(manifest.read_text())
    try:
        return path if physical(path).is_file() and hashes.get(name) == artifact_digest(path) else None
    except (OSError,EOFError,ValueError):
        return None


class Handler(BaseHTTPRequestHandler):
    def local_request(self):
        hosts = {f'127.0.0.1:{PORT}', f'localhost:{PORT}'}
        return self.headers.get('Host') in hosts and (
            self.headers.get('Origin') is None or self.headers['Origin'] in {'http://' + h for h in hosts})

    def send(self, value, status=200):
        self.respond(json.dumps(value, allow_nan=False).encode(), 'application/json', status)

    def respond(self, data, content_type, status=200, filename=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.local_request():
            return self.send({'error': 'Local workbench only'}, 403)
        path = self.path.split('?', 1)[0]
        if path in ASSETS:
            file = ROOT / 'web' / ('rocket.html' if path == '/' else path[1:])
            return self.respond(file.read_bytes(), mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        if path == '/api/health':
            return self.send(readiness())
        if path == '/api/state':
            latest = DATA / 'latest.json'
            identity=json.loads(latest.read_text())['id'] if latest.exists() else None
            if identity:
                report=DATA / identity / 'report.json'
                if not report.exists() or json.loads(report.read_text()).get('recipe',{}).get('architecture')!='sabre_inspired_precooled_combined_cycle':
                    identity=None
            return self.send(dict(token=TOKEN, active=ACTIVE,
                                  latest=identity))
        match = re.fullmatch(r'/api/jobs/([a-f0-9]{32})', path)
        if match:
            state = job(match[1])
            return self.send(state or {'error': 'Unknown job'}, 200 if state else 404)
        match = re.fullmatch(r'/api/component-network/([a-f0-9]{32})', path)
        if match:
            checked = verified_file(match[1], 'report.json')
            if checked is None:
                return self.send({'error': 'Checked model unavailable'}, 404)
            return self.send(assessment(json.loads(checked.read_text(encoding='utf-8'))))
        match = re.fullmatch(r'/api/engineering-inputs/([a-f0-9]{32})', path)
        if match:
            checked = verified_file(match[1], 'report.json')
            if checked is None:
                return self.send({'error': 'Checked model unavailable'}, 404)
            return self.send(input_ledger(assessment(json.loads(checked.read_text(encoding='utf-8')))))
        match = re.fullmatch(r'/api/design-audits/([a-f0-9]{32})', path)
        if match:
            checked=verified_file(match[1],'report.json')
            audit_path=ROOT/'data/design-audits'/(match[1]+'.json')
            if checked is None:return self.send({'error':'Checked model unavailable'},404)
            if not audit_path.exists():return self.send({'available':False})
            audit=json.loads(audit_path.read_text(encoding='utf-8'))
            if audit.get('source_report_sha256')!=artifact_digest(checked):
                return self.send({'error':'Audit belongs to a different report'},409)
            return self.send(dict(available=True,**audit))
        match = re.fullmatch(r'/api/prints/([a-f0-9]{32})/([a-zA-Z0-9.-]+)', path)
        if match and match[2] in ARTIFACTS:
            file = verified_file(match[1], match[2])
            if file:
                kind = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
                self.send_response(200)
                self.send_header('Content-Type',kind)
                self.send_header('Content-Length',str(artifact_size(file)))
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('X-Frame-Options','DENY')
                if file.suffix in ('.zip','.stl'):
                    self.send_header('Content-Disposition',f'attachment; filename="{file.name}"')
                self.end_headers()
                with open_artifact(file) as stream:shutil.copyfileobj(stream,self.wfile,1024*1024)
                return
            return self.send({'error': 'Artifact missing, changed or not accepted'}, 404)
        self.send({'error': 'Not found'}, 404)

    def do_POST(self):
        global ACTIVE
        if not self.local_request() or self.headers.get('X-Vega-Token') != TOKEN:
            return self.send({'error': 'Reload the local page before generating'}, 403)
        if self.path not in ('/api/build','/api/analyze','/api/cooling-screen'):
            return self.send({'error': 'Not found'}, 404)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048 or self.headers.get_content_type() != 'application/json':
                raise ValueError('Expected a small JSON request')
            options = json.loads(self.rfile.read(length))
            if self.path=='/api/cooling-screen':
                if not isinstance(options,dict) or set(options)!={'id','flow_ml_s'} or not re.fullmatch('[a-f0-9]{32}',str(options['id'])):raise ValueError('Expected a checked run and screening flow')
                checked=verified_file(options['id'],'report.json')
                if checked is None:raise ValueError('Checked model unavailable')
                loaded=json.loads(checked.read_text());design=loaded['recipe']
                return self.send(assembly_network(design,design['bell_cooling'],float(options['flow_ml_s'])))
            if isinstance(options,dict) and options.get('expanded_inlet') is True:
                if self.path!='/api/build' or set(options)!={'expanded_inlet','reference_flow_g_s'}:
                    raise ValueError('Expected expanded inlet and reference flow')
                recipe({'reference_flow_g_s':options['reference_flow_g_s']})
            elif isinstance(options,dict) and any(options.get(k) is True for k in ('architecture_expansion','assembly_integration','bell_cooling')):
                mode=next(k for k in ('bell_cooling','assembly_integration','architecture_expansion') if options.get(k) is True)
                if set(options)-{mode,'centrebody_mm'} or self.path!='/api/build':raise ValueError('Expanded assembly uses its checked base recipe')
                recipe({'centrebody_mm':options.get('centrebody_mm',0)})
            else:recipe(options)
        except (ValueError, TypeError) as error:
            return self.send({'error': str(error)}, 400)
        if self.path=='/api/analyze':
            try:return self.send(analyze(recipe(options)))
            except Exception as error:return self.send({'error':str(error) or type(error).__name__},400)
        with LOCK:
            if ACTIVE:
                return self.send({'error': 'A model is already being generated', 'id': ACTIVE}, 409)
            identity = uuid.uuid4().hex
            ACTIVE = identity
            write_json(STATES / (identity + '.json'), dict(id=identity, status='queued', message='Starting PicoGK'))
            POOL.submit(build, identity, options)
        self.send({'id': identity}, 202)


if __name__ == '__main__':
    for path in STATES.glob('*.json'):
        state = json.loads(path.read_text())
        if state['status'] in ('queued', 'running'):
            state.update(status='interrupted', message='Server stopped during generation. Generate again.')
            write_json(path, state)
    print(f'Vega One: http://127.0.0.1:{PORT}/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
