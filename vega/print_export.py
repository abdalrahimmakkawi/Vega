"""Publish only checked, traceable print parts from the single native recipe."""
from pathlib import Path
import hashlib
import gc
import json
import subprocess
import zipfile
import shutil

from .demonstrator import ROOT, recipe, PRINT_GUIDE
from .stl import validate_binary_stl
import numpy as np
import trimesh
from .input_mesh import write_input_mesh
from .cem import acceptance
from .analysis import analyze

DLL = ROOT / 'integrations/bin/Release/net9.0/Vega.Native.dll'
DOTNET = ROOT / '.tools/dotnet/dotnet.exe'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def clean_native(path, pitch):
    """Fill only isolated sub-voxel cavities and discard zero-volume facets.

    Never discard positive-volume detached parts or repair the primary shell.
    Record every change and recheck the final exported file independently.
    """
    validate_binary_stl(path.read_bytes())
    raw_hash = digest(path)
    mesh = trimesh.load_mesh(path, process=True)
    shells = sorted(mesh.split(only_watertight=False, repair=False), key=lambda s: s.volume, reverse=True)
    if not shells or not shells[0].is_volume:
        raise ValueError('The main native surface is not a closed positive solid')
    tiny = shells[1:]
    if any(s.volume > 1e-8 or np.max(s.extents) > 3*pitch for s in tiny):
        raise ValueError('Detached material or a substantial enclosed cavity requires a geometry change')
    filled = sum(abs(float(s.volume)) for s in tiny)
    if filled > 16*pitch**3:
        raise ValueError('Native cavity cleanup exceeds the small voxel-artifact budget')
    shells[0].export(path)
    return dict(raw_sha256=raw_hash, removed_shells=len(tiny),
                filled_cavity_mm3=filled, removed_triangles=sum(len(s.faces) for s in tiny),
                policy='Only non-positive shells within 3 voxels; total volume <= 16 voxels cubed')


def inspect_mesh(path, *, print_part=False):
    count = validate_binary_stl(path.read_bytes())
    if count > 6_000_000:
        raise ValueError('Mesh exceeds the viewer triangle budget')
    mesh = trimesh.load_mesh(path, process=True)
    # Count face-connected components without copying each multi-million-face
    # surface into a second mesh just to count it.
    component_count = len(trimesh.graph.connected_components(
        mesh.face_adjacency, nodes=np.arange(len(mesh.faces))))
    check = dict(triangles=count, watertight=bool(mesh.is_watertight),
                 winding_consistent=bool(mesh.is_winding_consistent),
                 connected_bodies=component_count, volume_mm3=float(mesh.volume),
                 size_mm=mesh.extents.tolist(), bounds_mm=mesh.bounds.tolist(),
                 sha256=digest(path))
    check['passed'] = bool(check['watertight'] and check['winding_consistent']
                           and component_count == 1 and mesh.volume > 0)
    if print_part:
        check['fits_build_envelope'] = bool(np.all(mesh.extents <= [125, 65, 35]))
        check['on_bed'] = abs(float(mesh.bounds[0, 2])) < .001
        check['passed'] &= check['fits_build_envelope'] and check['on_bed']
    if not check['passed']:
        raise ValueError(f'{path.name} failed mesh checks: {json.dumps(check)}')
    return mesh, check


def export_print_mesh(mesh, path):
    # Binary STL stores float32 coordinates. Translation can collapse tiny
    # facets that were distinct in the native coordinate frame. Quantize first
    # and remove only exactly zero-area faces; the exported topology must still
    # pass inspect_mesh independently, without hole filling or surface repair.
    mesh.vertices = mesh.vertices.astype(np.float32).astype(np.float64)
    mesh.merge_vertices()
    keep = mesh.area_faces > 0
    removed = int(np.count_nonzero(~keep))
    mesh.update_faces(keep)
    mesh.remove_unreferenced_vertices()
    mesh.export(path)
    return removed


def append_smooth_normals(mesh, stream):
    """Compact display normals only; the checked STL vertex positions stay exact."""
    normals=np.zeros((len(mesh.vertices),3))
    for corner in range(3):np.add.at(normals,mesh.faces[:,corner],mesh.face_normals)
    normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-30)
    for start in range(0,len(mesh.faces),65536):
        stream.write(np.rint(normals[mesh.faces[start:start+65536]]*127).astype(np.int8).tobytes())


def finish_export(folder, design, progress=lambda message: None, native_binary_sha256=None):
    progress('Checking closed surfaces and preparing two print orientations')
    native = json.loads((folder / 'native.json').read_text())
    cleanup = {'assembled': clean_native(folder / 'assembled.stl', design['voxel_mm'])}
    gc.collect()
    assembly = inspect_mesh(folder / 'assembled.stl')[1]
    gc.collect()
    parts = {}
    scene = []
    bodies = []
    first = 0
    for index, side in enumerate((1, -1)):
        name = ('half-a', 'half-b')[index]
        progress(f'Assembly passed. Checking print half {"AB"[index]} and its exported orientation')
        cleanup[name] = clean_native(folder / (name + '.raw.stl'), design['voxel_mm'])
        gc.collect()
        mesh, _ = inspect_mesh(folder / (name + '.raw.stl'))
        # Native half-space meshing lands exactly on y=0 apart from float noise.
        seam_error = abs(float(mesh.bounds[0 if side > 0 else 1, 1]))
        if seam_error > design['voxel_mm'] * .1:
            raise ValueError('Split plane is not flat at the intended mating face')
        body = mesh.copy()
        bodies.append(dict(component_id=name, name=f'Print half {"AB"[index]}',
                           first_triangle=first, triangle_count=len(body.faces),
                           color=([.19, .60, .60] if index == 0 else [.85, .52, .25])))
        first += len(body.faces)
        scene.append(body)
        # Rotate, never mirror, so the split face lies on the print bed.
        matrix = np.eye(4)
        matrix[:3, :3] = [[0, 0, 1], [side, 0, 0], [0, side, 0]]
        mesh.apply_transform(matrix)
        mesh.apply_translation(-mesh.bounds[0])
        cleanup[name]['print_zero_area_triangles_removed'] = export_print_mesh(mesh, folder / (name + '.stl'))
        del mesh
        gc.collect()
        parts[name] = inspect_mesh(folder / (name + '.stl'), print_part=True)[1]
        gc.collect()
    progress('Both casing halves passed. Checking the five system components')
    components={}
    for component in design.get('components',[]):
        name=component['id']; raw=folder/(name+'.raw.stl')
        cleanup[name]=clean_native(raw,design['voxel_mm']); gc.collect()
        mesh,check=inspect_mesh(raw)
        components[name]=check
        shutil.copyfile(raw,folder/(name+'.stl'))
        bodies.append(dict(component_id=name,name=component['name'],first_triangle=first,
            triangle_count=len(mesh.faces),color=component['color']))
        first+=len(mesh.faces);scene.append(mesh.copy())
        del mesh;gc.collect()
    if first>6_000_000:raise ValueError('Combined review assembly exceeds the viewer triangle budget')
    progress('Checking 0.01 mm intake detail and solving CFD + FEA review cases')
    detail_cleanup=clean_native(folder/'intake-detail.stl',.01);gc.collect()
    detail=inspect_mesh(folder/'intake-detail.stl')[1];gc.collect()
    detail.update(json.loads((folder/'detail.json').read_text()),cleanup=detail_cleanup)
    analysis=analyze(design)
    (folder/'analysis.json').write_text(json.dumps(analysis,allow_nan=False),encoding='utf-8')
    progress('Components and analyses passed. Preparing smooth display and download kit')
    with (folder/'scene-normals.bin').open('wb') as stream:
        for mesh in scene:append_smooth_normals(mesh,stream)
    del mesh;gc.collect()
    trimesh.util.concatenate(scene).export(folder / 'scene.stl')
    validate_binary_stl((folder / 'scene.stl').read_bytes(), bodies)
    if native.get('architecture') != design['architecture'] or native.get('precooler_tube_count') != design['synthesis']['geometry']['precooler']['tube_count']:
        raise ValueError('Native geometry does not match the synthesized SABRE architecture')
    if not np.isclose(native.get('precooler_length_mm', 0), design['synthesis']['geometry']['precooler']['length_mm'], atol=.001, rtol=0):
        raise ValueError('Native precooler length differs from the sized bundle')
    if native.get('cooling_route_count') != len(design['cooling']['routes']) or native.get('cooling_centerline_samples',0)<=0:
        raise ValueError('Native cooling channels were not constructed and checked')
    if design.get('revision',0)>=4 and native.get('cooling_clearance_samples',0)<=0:
        raise ValueError('Native cooling cross-section clearance was not checked')
    input_mesh=json.loads((folder/'input-mesh.json').read_text())
    if input_mesh['sha256']!=digest(folder/'input-body.stl'):
        raise ValueError('Triangular input changed during generation')
    cem=acceptance(design['cem'],native,assembly,parts,input_mesh)
    report = dict(model=design['model'], status='mesh_checked', recipe=design,
                  cem=cem,input_mesh=input_mesh,
                  native_binary_sha256=native_binary_sha256 or digest(DLL),
                  native=native, assembly=assembly, parts=parts, bodies=bodies, voxel_cleanup=cleanup,
                  components=components,detail=detail,analysis_summary={
                      'status':analysis['status'],'cfd_cells':analysis['cfd']['cells'],'fea_elements':analysis['fea']['elements']},
                  smooth_normals=True,
                  scene_sha256=digest(folder / 'scene.stl'),
                  physical_print_verified=False, flow_performance_verified=False,
                  acceptance='Mesh checks passed. Slicer review and a physical print remain required.')
    (folder / 'PRINT.txt').write_text(PRINT_GUIDE, encoding='utf-8')
    (folder / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    (folder / 'cem.json').write_text(json.dumps(cem,indent=2,allow_nan=False),encoding='utf-8')
    with zipfile.ZipFile(folder / 'vega-one-print-kit.zip', 'w', zipfile.ZIP_DEFLATED) as kit:
        for name in ('half-a.stl', 'half-b.stl', 'assembled.stl', 'input-body.stl','input-mesh.json','cem.json','recipe.json', 'report.json', 'PRINT.txt','analysis.json','intake-detail.stl')+tuple(c['id']+'.stl' for c in design.get('components',[])):
            kit.write(folder / name, name)
    return report


def generate(folder, options=None, progress=lambda message: None):
    design = recipe(options)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'recipe.json').write_text(json.dumps(design, indent=2), encoding='utf-8')
    progress('Building closed triangular nacelle and core meshes')
    input_mesh=write_input_mesh(design,folder/'input-body.stl')
    input_mesh['sha256']=digest(folder/'input-body.stl')
    (folder/'input-mesh.json').write_text(json.dumps(input_mesh,indent=2),encoding='utf-8')
    if not DLL.is_file() or not DOTNET.is_file():
        raise ValueError('Build the native bridge with setup.ps1 first')
    progress('Converting triangular meshes to PicoGK voxels, then adding implicit features and channels')
    native_binary_sha256 = digest(DLL)
    with (folder / 'native.log').open('w', encoding='utf-8') as log:
        result = subprocess.run([str(DOTNET), str(DLL), 'demonstrator',
                                 str(folder / 'recipe.json'), str(folder), str(design['voxel_mm'])],
                                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    if result.returncode:
        raise ValueError('PicoGK generation failed: ' + (folder / 'native.log').read_text()[-1200:])
    progress('Voxelizing a bounded intake detail at a genuine 0.01 mm pitch')
    with (folder/'detail.log').open('w',encoding='utf-8') as log:
        detail_result=subprocess.run([str(DOTNET),str(DLL),'detail',str(folder/'recipe.json'),str(folder),'0.01'],
            cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    if detail_result.returncode:raise ValueError('0.01 mm detail generation failed: '+(folder/'detail.log').read_text()[-1000:])
    return finish_export(folder, design, progress, native_binary_sha256)
