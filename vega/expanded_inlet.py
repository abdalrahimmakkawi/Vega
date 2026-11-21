"""Add a room-air inlet upstream of the existing split casing."""
import json
import math
import os
import zipfile
from itertools import combinations

import numpy as np
import trimesh
from vega_geometry import fingerprint
from .architecture import digest
from .artifacts import physical, artifact_digest
from .demonstrator import ROOT
from .print_export import append_smooth_normals
from .sabre import bundle_screen

BASE = '3461d8170a874f7ca296defca47973bf'
PART = 'main-air-inlet'


def optimize_ribs(mesh, z, inner, wall):
    """Select four of twelve external ribs by minimum worst tip compliance."""
    # Axial cantilever strips, uncoupled circumferentially. All candidates
    # contain equal added material; the original shell is a protected region.
    angles = np.arange(12)*math.tau/12
    load = np.array([np.cos(angles)**2, np.sin(angles)**2])
    load /= load.sum(axis=1, keepdims=True)  # Two orthogonal 1 N handling cases.
    modulus = 2000.  # N/mm2, provisional isotropic printed polymer
    amp = 1.6
    # Match the 128-facet mesh with a periodic angular quadrature per sector.
    theta = np.linspace(-math.pi/12, math.pi/12, 129)
    rib = amp*np.maximum(0, 1-np.abs(theta)/.12)
    tip_compliance = []
    for thickness in (np.full_like(theta, wall), wall+rib):
        # Integral of thickness^3/12 over strip width about local midsurface.
        inertia = (inner+wall/2)*np.trapezoid(thickness**3/12,theta)
        tip_compliance.append(np.trapezoid((z-z[0])**2/(modulus*inertia),z))
    def objective(active):
        values = np.full(12,tip_compliance[0])
        values[list(active)] = tip_compliance[1]
        return float(max((load**2) @ values))
    choices = list(combinations(range(12),4))
    active = min(choices,key=objective)
    vertices = mesh.vertices.copy()
    radius = np.linalg.norm(vertices[:,:2],axis=1)
    exterior = radius > np.interp(vertices[:,2],z,inner)+wall/2
    azimuth = np.arctan2(vertices[:,1],vertices[:,0])
    max_rib = np.zeros(len(vertices))
    for sector in active:
        distance = abs((azimuth-angles[sector]+math.pi)%math.tau-math.pi)
        max_rib = np.maximum(max_rib,amp*np.maximum(0,1-distance/.12))
    vertices[exterior,:2] *= (1+max_rib[exterior]/radius[exterior])[:,None]
    original_volume = mesh.volume
    mesh.vertices = vertices
    if not mesh.is_volume or mesh.volume <= original_volume:
        raise ValueError('Invalid reinforced inlet mesh')
    return dict(method='Discrete member selection with worst-case bending compliance',
                candidates=len(choices), selected_angles_deg=[i*30 for i in active],
                handling_load_n=1., modulus_mpa=modulus, original_mm_per_n=objective(()),
                reinforced_mm_per_n=objective(active), added_volume_mm3=mesh.volume-original_volume,
                scope='Independent axial beam strips with fixed casing seat and radial tip loads. Mount restraint, shell coupling and material properties require validation.')


def generate(folder, flow_g_s):
    base = ROOT / 'data/prints' / BASE
    manifest = json.loads((base/'manifest.json').read_text())
    if artifact_digest(base/'report.json') != manifest['report.json']:
        raise ValueError('Expanded baseline report changed')
    report = json.loads((base/'report.json').read_text())
    design = report['recipe']
    synthesis = design['synthesis']
    reference = dict(synthesis['reference'], mass_flow_kg_s=flow_g_s/1000)
    rho = reference['pressure_pa']/(287.05*reference['inlet_temperature_k'])
    # Design assumption: allow half the nominal intake velocity at the mouth.
    mouth = math.sqrt(8**2 + 1e6*reference['mass_flow_kg_s'] /
                      (math.pi*rho*reference['intake_speed_m_s']*.5))
    throat = min(design['outer'][0]['radii_mm'])
    wall = design['wall_mm']
    z = np.linspace(-14, 0, 29)
    fraction = -z/14
    r = throat + (mouth-throat)*fraction**2*(3-2*fraction)
    profile = np.vstack([np.column_stack((r+wall,z)),np.column_stack((r[::-1],z[::-1])),[r[0]+wall,z[0]]])
    mesh = trimesh.creation.revolve(profile, sections=128)
    if mesh.volume < 0: mesh.invert()
    optimization = optimize_ribs(mesh,z,r,wall)
    if not mesh.is_volume: raise ValueError('Open inlet wall')
    folder.mkdir(exist_ok=False)
    changed = {'recipe.json','report.json','vega-one-print-kit.zip','component-network.json'}
    for name, expected in manifest.items():
        if name in changed: continue
        src = physical(base/name)
        if artifact_digest(base/name) != expected: raise ValueError('Baseline changed: '+name)
        os.link(src, folder/src.name)
    mesh.export(folder/(PART+'.stl'))
    with (folder/'inlet-normals.bin').open('wb') as out: append_smooth_normals(mesh,out)
    name = 'Main airflow inlet bellmouth'
    part = dict(id=PART,name=name,color=[.14,.66,.62],review_anchor_mm=[mouth,0,-14])
    design['components'].append(part)
    report['bodies'].append(dict(component_id=PART,name=name,color=part['color'],
        first_triangle=sum(b['triangle_count'] for b in report['bodies']),triangle_count=len(mesh.faces)))
    report.setdefault('scene_layers',[]).append(dict(mesh=PART+'.stl',normals='inlet-normals.bin'))
    design['inlet_revision']=dict(flow_g_s=flow_g_s,mouth_radius_mm=mouth,throat_radius_mm=throat,
        topology_optimization=optimization,
        assumed_mouth_velocity_m_s=.5*reference['intake_speed_m_s'],hub_envelope_radius_mm=8,
        downstream='precooler.main-air.in',interface='Flush casing seat at z=0 mm',
        bundle_screen=bundle_screen(reference,synthesis['search']['selected'],min(design['outer'][30]['radii_mm'])))
    if not design['inlet_revision']['bundle_screen']['flow_area_passed']: raise ValueError('Bundle flow area insufficient')
    design['design_changes']=dict(baseline_run=BASE,description='Flow-sized removable inlet feeding the main-air path')
    design['recipe_sha256']=fingerprint({k:v for k,v in design.items() if k!='recipe_sha256'})
    for file,value in [('report.json',report),('recipe.json',design)]:
        (folder/file).write_text(json.dumps(value,allow_nan=False),encoding='utf-8')
    if digest(base/'vega-one-print-kit.zip') != manifest['vega-one-print-kit.zip']: raise ValueError('Baseline kit changed')
    with zipfile.ZipFile(base/'vega-one-print-kit.zip') as old, zipfile.ZipFile(folder/'vega-one-print-kit.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as new:
        for entry in old.infolist():
            if entry.filename not in changed: new.writestr(entry,old.read(entry))
        for file in ['report.json','recipe.json',PART+'.stl']: new.write(folder/file,file)
