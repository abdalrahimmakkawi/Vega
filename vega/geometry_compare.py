"""Compare saved component geometry, not request IDs or mesh triangle counts."""
import hashlib
from pathlib import Path


MISSION_ONLY_INPUTS=frozenset({
    'vehicle_architecture','vehicle_dry_mass_kg','vehicle_drag_coefficient',
    'vehicle_diameter_m','launch_altitude_m','target_apogee_m','payload_mass_kg',
    'orbit_altitude_m',
    'vehicle_mass_mode','core_material_density_kg_m3','tank_material_density_kg_m3',
    'assembly_material_density_kg_m3','vehicle_unmodeled_dry_mass_kg',
    'vehicle_mass_margin_fraction','mission_delta_v_allowance_m_s',
    'orbital_electrical_load_w','solar_array_efficiency','solar_eol_factor','battery_specific_energy_wh_kg',
    'battery_depth_of_discharge','power_margin_fraction','radiator_temperature_k','radiator_sink_temperature_k','radiator_emissivity',
})


def compare_runs(before, after, root):
    """Use each exported body's exact binary-STL triangle span as its identity."""
    old=before.get('assembly_artifact')
    new=after.get('assembly_artifact')
    if not old or not new:
        raise ValueError('Both studies need current connected assembly exports')
    def spans(run, artifact):
        data=(Path(root)/'data'/'native'/f'{run["id"]}.assembly.stl').read_bytes()
        result={}
        for body in artifact['bodies']:
            first=body['first_triangle'];count=body['triangle_count']
            chunk=data[84+50*first:84+50*(first+count)]
            if len(chunk)!=50*count:raise ValueError('Component span exceeds assembly STL')
            result[body['component_id']]={'sha256':hashlib.sha256(chunk).hexdigest(),
                'triangle_count':count,'group':body.get('group','unknown')}
        return result
    a=spans(before,old);b=spans(after,new)
    names={c['id']:c['name'] for c in new['components']}
    components=[]
    for identity in sorted(a.keys()|b.keys()):
        left=a.get(identity);right=b.get(identity)
        status=('added' if not left else 'removed' if not right else
                'unchanged' if left['sha256']==right['sha256'] else 'changed')
        components.append({'id':identity,'name':names.get(identity,identity),
            'group':(right or left)['group'],'status':status,
            'before_triangles':left['triangle_count'] if left else 0,
            'after_triangles':right['triangle_count'] if right else 0})
    inputs=[]
    for key in sorted(before['requirements'].keys()|after['requirements'].keys()):
        old_value=before['requirements'].get(key);new_value=after['requirements'].get(key)
        if old_value!=new_value:
            inputs.append({'name':key,'before':old_value,'after':new_value,
                           'geometry_dependency':'mission_only' if key in MISSION_ONLY_INPUTS else 'geometry_or_engine_state'})
    old_size=before['candidates'][0]['assembly']['dimensions'] if before.get('candidates') else None
    new_size=after['candidates'][0]['assembly']['dimensions'] if after.get('candidates') else None
    dimension_change={key:{'before_mm':old_size[key],'after_mm':new_size[key],
        'change_percent':100*(new_size[key]/old_size[key]-1)} for key in ('length_mm','diameter_mm')} if old_size and new_size else None
    return {'before_run':before['id'],'after_run':after['id'],
        'status':'unchanged' if old['stl_sha256']==new['stl_sha256'] else 'changed',
        'before_sha256':old['stl_sha256'],'after_sha256':new['stl_sha256'],
        'changed_component_count':sum(c['status']!='unchanged' for c in components),
        'components':components,'changed_inputs':inputs,'dimension_change':dimension_change,
        'scope':'Exact exported component triangle bytes. A changed body fingerprint proves a mesh difference, not a physically meaningful performance change.'}
