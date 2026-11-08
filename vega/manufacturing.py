"""Small cached material index and explicit manufacturing constraints."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import json
from dataclasses import replace

@lru_cache(maxsize=1)
def _catalog():
    return json.loads(Path(__file__).with_name('material_catalog.json').read_text())

def catalog():
    return deepcopy(_catalog())

def validate_selection(b):
    if b.material_id != 'custom' and b.material_id not in {m['id'] for m in _catalog()['materials']}:
        raise ValueError('Unknown material')
    if b.print_process not in _catalog()['processes']:raise ValueError('Unknown printing process')
    if b.test_purpose not in ('concept','fit','cold_flow','hot_fire'):raise ValueError('Unknown test purpose')

def constrain(b):
    validate_selection(b)
    # User-declared process limits drive the geometry before it is solved.
    if b.print_min_wall_mm > 15 or b.print_min_ligament_mm > 5:
        raise ValueError('Requested print limits exceed the supported geometry domain')
    return replace(b,wall_mm=max(b.wall_mm,b.print_min_wall_mm),
                   inlet_wall_mm=max(b.inlet_wall_mm,b.print_min_wall_mm),
                   minimum_ligament_mm=max(b.minimum_ligament_mm,b.print_min_ligament_mm))

def screen(b,c):
    material=next((m for m in _catalog()['materials'] if m['id']==b.material_id),None)
    unresolved=['Printed material allowables versus temperature and orientation',
                'Support removal, internal access and process qualification',
                'Actual part intersections, minimum walls and leak testing']
    if b.print_process=='unspecified':unresolved.append('Printing process not selected')
    if not b.print_min_wall_mm or not b.print_min_ligament_mm:unresolved.append('Process feature limits not specified')
    dims=c.get('assembly',{}).get('dimensions') or c['dimensions']
    bounds=sorted([dims['diameter_mm'],dims['diameter_mm'],dims['length_mm']])
    bed=sorted([b.print_build_x_mm,b.print_build_y_mm,b.print_build_z_mm])
    checks={}
    if all(bed):checks['conservative_build_envelope']=all(a<=z for a,z in zip(bounds,bed))
    else:unresolved.append('Printer build envelope not specified')
    if b.print_min_wall_mm:checks['nominal_wall']=min(b.wall_mm,b.inlet_wall_mm)>=b.print_min_wall_mm
    if b.print_min_ligament_mm:checks['nominal_ligament']=b.minimum_ligament_mm>=b.print_min_ligament_mm
    if b.test_purpose=='hot_fire':unresolved.append('Hot-fire thermal, pressure, fatigue, compatibility and test qualification')
    return {'material_id':b.material_id,'material_name':material['name'] if material else 'Custom material',
            'process':b.print_process,'test_purpose':b.test_purpose,'checks':checks,
            'status':'failed_constraints' if not all(checks.values()) else 'incomplete',
            'print_ready':False,'unresolved':unresolved,
            'property_basis':'User inputs; material name alone does not establish material properties',
            'effective_properties':{k:getattr(b,k) for k in ('core_material_density_kg_m3','wall_conductivity_w_m_k','allowable_stress_mpa','max_wall_temperature_k')},
            'scope':'Core material selection; tanks and frame retain their separately entered properties. Envelope is conservative, axis-permutation only; part splitting and nesting are not solved.'}
