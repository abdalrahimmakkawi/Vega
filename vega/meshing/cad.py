"""Gmsh/OpenCASCADE loft meshing, replacing the bespoke triangle-strip mesher.

The CAD boundary uses interpolating splines around each analytic section and
ruled patches between stations. A local size callback refines high lobe curvature,
throats and ports. Gmsh's frontal-Delaunay algorithm supplies unstructured surface
triangles; its tetrahedral mesher is available separately for solid FEA.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import uuid
import numpy as np
from vega_geometry.sections import contour, validate_stations
from . import ROOT
from .kernel import model
from .quality import audit_triangle_quality

_CODE_ID=hashlib.sha256(b''.join(p.read_bytes() for p in
    (Path(__file__),Path(__file__).with_name('kernel.py'),Path(__file__).with_name('quality.py'),
     ROOT/'packages/vega-geometry/vega_geometry/sections.py'))).hexdigest()


def _build(g, stations, section, chord):
    o = g.model.occ
    # Geometry interpolation resolution is independent of the analysis mesh.
    max_lobes = max(s['lobe_count'] for s in stations)
    radius = max(max(s['width_mm'], s['height_mm'])/2+s['wall_mm'] for s in stations)
    samples = min(512, 4*math.ceil(max(48, 12*max_lobes, math.pi*math.sqrt(radius/(2*chord)))/4))
    angles = 2*math.pi*np.arange(samples)/samples
    def wire(s, outer):
        if section == 'rectangular':
            w, h = s['width_mm']/2, s['height_mm']/2
            if outer: w += s['wall_mm']; h += s['wall_mm']
            pts = [o.addPoint(x, y, s['z_mm']) for x, y in ((w,h),(-w,h),(-w,-h),(w,-h))]
            curves = [o.addLine(pts[i], pts[(i+1)%4]) for i in range(4)]
        else:
            xyz = contour(s, angles, s['wall_mm'] if outer else 0.)
            pts = [o.addPoint(*p) for p in xyz]
            quarter = samples//4
            curves = [o.addSpline([pts[(j+i)%samples] for i in range(quarter+1)]) for j in range(0, samples, quarter)]
        return o.addWire(curves)
    outer = o.addThruSections([wire(s, True) for s in stations], makeSolid=True, makeRuled=True)
    inner = o.addThruSections([wire(s, False) for s in stations], makeSolid=True, makeRuled=True)
    solids, _ = o.cut(outer, inner)
    o.synchronize()
    if len(solids) != 1 or solids[0][0] != 3 or o.getMass(*solids[0]) <= 0:
        raise ValueError('CAD wall must be one positive-volume solid')
    boundaries = g.model.getBoundary(solids, oriented=True)
    needed = {abs(tag) for dim, tag in boundaries if dim == 2}
    unused = [(2,t) for _,t in g.model.getEntities(2) if t not in needed]
    if unused:
        o.remove(unused, recursive=True); o.synchronize()
    return solids, boundaries, samples


def _sizing(g, stations, edge, chord, volume=False):
    levels = np.array([s['z_mm'] for s in stations])
    radii = np.array([min(s['width_mm'],s['height_mm'])/2 for s in stations])
    amps = np.array([s['lobe_amplitude'] for s in stations])
    modes = np.array([s['lobe_count'] for s in stations])
    curvature = (1+amps*(modes+1)**2)/radii
    sizes = np.minimum(edge, np.sqrt(8*chord/curvature))
    # Throat area gradients and nearby sharp end rims receive finer elements.
    area = np.array([s['width_mm']*s['height_mm'] for s in stations])
    gradient = abs(np.gradient(np.log(area), levels))*radii
    sizes /= np.sqrt(1+gradient)
    if volume:
        sizes = np.minimum(sizes, np.array([s['wall_mm'] for s in stations])*1.5)
    hmin = max(float(sizes.min())*.5, edge/100)
    def size(dim, tag, x, y, z, lc):
        local = float(np.interp(z, levels, sizes))
        distance = min(abs(z-levels[0]), abs(z-levels[-1]))
        # Lipschitz target-size field: dh/dd <= 0.25 at each port.
        return min(local, .65*float(sizes[0])+.25*distance) if distance < 2*edge else local
    g.model.mesh.setSizeCallback(size)
    g.option.setNumber('Mesh.MeshSizeMin', hmin)
    g.option.setNumber('Mesh.MeshSizeMax', edge)
    g.option.setNumber('Mesh.MeshSizeFromPoints', 0)
    g.option.setNumber('Mesh.MeshSizeExtendFromBoundary', 0)
    g.option.setNumber('Mesh.Algorithm', 6)
    g.option.setNumber('Mesh.Smoothing', 10)
    return {'minimum_target_mm': float(sizes.min()), 'maximum_target_mm': float(sizes.max()),
            'curvature_chord_target_mm': chord, 'port_size_slope': .25,
            'gradation_scope': 'Target size slope; actual cell growth is audited separately in volume meshes.'}


def _surface(g, boundaries):
    tags, coords, _ = g.model.mesh.getNodes()
    order = np.argsort(tags); tags = tags[order]; xyz = coords.reshape(-1,3)[order]
    faces = []
    for dim, signed in boundaries:
        types, _, blocks = g.model.mesh.getElements(2, abs(signed))
        for typ, block in zip(types, blocks):
            if typ != 2: raise ValueError('Expected first-order surface triangles')
            f = np.searchsorted(tags, block).reshape(-1,3)
            if signed < 0: f = f[:,[0,2,1]]
            faces.append(f)
    faces = np.concatenate(faces)
    used, inverse = np.unique(faces, return_inverse=True)
    # OCC boundary signs and generated face parametrizations need not agree.
    # Orient the closed connected shell by adjacency, without moving a node.
    import trimesh
    surface=trimesh.Trimesh(xyz[used],inverse.reshape(-1,3),process=False)
    surface.fix_normals(multibody=True)
    if not surface.is_watertight or not surface.is_winding_consistent or surface.volume<=0:
        raise ValueError('CAD boundary failed closed oriented surface checks')
    return np.asarray(surface.vertices), np.asarray(surface.faces)


@lru_cache(maxsize=12)
def _cached_surface(station_json, edge, chord, section):
    stations = validate_stations(json.loads(station_json))
    if not all(math.isfinite(v) and v > 0 for v in (edge,chord)):
        raise ValueError('Mesh edge and chord controls must be positive')
    with model('vega-cad-wall') as g:
        solids, boundary, samples = _build(g, stations, section, chord)
        sizing = _sizing(g, stations, edge, chord)
        g.model.mesh.generate(2)
        xyz, faces = _surface(g, boundary)
        if len(faces) > 600000: raise ValueError('CAD surface exceeds the 600,000 triangle budget')
        result = {'vertices': xyz.tolist(), 'triangles': faces.tolist(), 'units': 'mm',
                  'generator': 'Gmsh 4.15 / OpenCASCADE frontal-Delaunay',
                  'tessellation': {'backend': 'Gmsh/OpenCASCADE', 'cad_section_samples': samples,
                      'cad_volume_mm3': float(g.model.occ.getMass(*solids[0])),
                      'target_edge_mm': edge, 'chord_tolerance_mm': chord, 'sizing': sizing,
                      'scope': 'CAD boundary triangulation; solver volumes have separate quality reports.'}}
        result['tessellation']['triangle_quality'] = audit_triangle_quality(xyz, faces)
        return result


def cad_duct(stations, edge_mm, chord_mm, section='elliptical'):
    """Closed CAD wall boundary; content caching cannot reuse a changed recipe.

    Cache identity includes all geometric fields, controls, backend code and
    Gmsh version. Thermodynamic annotations that do not change coordinates are
    deliberately excluded. Stored arrays are checked and never unpickled.
    """
    stations=validate_stations(stations)
    keys=('z_mm','width_mm','height_mm','wall_mm','lobe_amplitude','lobe_count','twist_rad')
    canonical=json.dumps([{k:s[k] for k in keys} for s in stations],sort_keys=True)
    edge,chord=float(edge_mm),float(chord_mm)
    identity=hashlib.sha256(json.dumps([_CODE_ID,'gmsh-4.15.2',canonical,edge,chord,section]).encode()).hexdigest()
    cache=ROOT/'.tools/mesh-cache';path=cache/(identity+'.npz')
    if path.is_file():
        try:
            with np.load(path,allow_pickle=False) as data:
                xyz=data['vertices'];faces=data['triangles'];metadata=json.loads(str(data['metadata']))
            checksum=hashlib.sha256(xyz.tobytes()+faces.tobytes()).hexdigest()
            if metadata.pop('array_sha256')!=checksum or metadata.pop('cache_identity')!=identity:
                raise ValueError('Mesh cache checksum mismatch')
            if xyz.ndim!=2 or xyz.shape[1]!=3 or faces.ndim!=2 or faces.shape[1]!=3 or not np.isfinite(xyz).all():
                raise ValueError('Invalid cached mesh arrays')
            if len(faces)==0 or faces.min()<0 or faces.max()>=len(xyz):raise ValueError('Invalid cached connectivity')
            return {**metadata,'vertices':xyz.tolist(),'triangles':faces.tolist()}
        except (OSError,ValueError,KeyError):
            pass  # Recompute only; never silently use corrupt cache data.
    result=deepcopy(_cached_surface(canonical,edge,chord,section))
    xyz=np.asarray(result['vertices'],dtype='<f8');faces=np.asarray(result['triangles'],dtype='<i8')
    metadata={k:v for k,v in result.items() if k not in ('vertices','triangles')}
    metadata.update(cache_identity=identity,array_sha256=hashlib.sha256(xyz.tobytes()+faces.tobytes()).hexdigest())
    cache.mkdir(parents=True,exist_ok=True)
    temp=cache/(identity+'.'+uuid.uuid4().hex+'.npz')
    np.savez_compressed(temp,vertices=xyz,triangles=faces,metadata=json.dumps(metadata));temp.replace(path)
    return result
