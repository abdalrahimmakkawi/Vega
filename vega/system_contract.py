"""Executable coherence contract for one saved Vega design and its meshes.

This checks that the analysis, registered flow routes, generated parts, native
rocket bodies and assembled viewer/export scene share the same recipe. It does
not claim that unresolved combined-cycle physics has been solved.
"""
import hashlib
import json
import math


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def build_system_contract(run):
    candidate=run['candidates'][0]
    geometry=candidate['geometry']
    model=candidate['geometry_model']
    assembly=candidate['assembly']
    artifact=run.get('artifact')
    assembly_artifact=run.get('assembly_artifact')
    if not artifact:
        raise ValueError('A verified PicoGK artifact is required for the system contract')
    if assembly.get('status')=='concept_assembly' and not assembly_artifact:
        raise ValueError('The connected assembly export is required for the system contract')

    ports={p['id']:p for p in model['ports']}
    route_ids={r['id'] for r in geometry['systems']['manifolds']}
    flow_edges=assembly.get('topology',{}).get('flow',{}).get('edges',[])
    alias={'cooling_channels':'cooling','injector_head':'injector'}
    expected_edges=[]
    for route_id,route in model['routes'].items():
        source=ports.get(route['source'])
        target=ports.get(route['target'])
        if not source or not target:
            raise ValueError('Registered route has a missing port: '+route_id)
        expected_edges.extend([[alias.get(source['component'],source['component']),route_id],
                               [route_id,alias.get(target['component'],target['component'])]])
    core_expected={p['id'] for p in candidate['components']}
    assembly_expected={p['id'] for p in assembly.get('components',[])}
    exported_bodies=assembly_artifact['bodies'] if assembly_artifact else [
        {**body,'component_id':'core_'+body['component_id'],'group':'core'} for body in artifact.get('bodies',[])]
    exported={p['component_id'] for p in exported_bodies}
    scene_bodies=assembly.get('scene',{}).get('bodies',[])
    expected_native_triangles=artifact.get('scene_triangles')
    expected_assembly_triangles=len(assembly.get('scene',{}).get('triangles',[]))
    ranges=[]
    for body in exported_bodies:
        first=body.get('first_triangle');count=body.get('triangle_count')
        ranges.append((first,count))
    contiguous=bool(ranges) and all(isinstance(first,int) and isinstance(count,int) and count>0 and
                                    first==sum(n for _,n in ranges[:i])
                                    for i,(first,count) in enumerate(ranges))
    scene_range_match=(len(scene_bodies)==len(assembly.get('components',[])) and
        all(body.get('component_id')==part.get('id') and body.get('first_triangle')==exported_bodies[i].get('first_triangle') and
            body.get('triangle_count')==exported_bodies[i].get('triangle_count')
            for i,(body,part) in enumerate(zip(scene_bodies,assembly.get('components',[])))) if assembly_artifact else True)
    core_ranges_match=(all(body.get('group')!='core' or body.get('first_triangle')==expected_assembly_triangles+
        sum(p.get('triangle_count',0) for p in exported_bodies[len(scene_bodies):i])
        for i,body in enumerate(exported_bodies)) if assembly_artifact else True)
    transition=candidate['vehicle_screen'].get('transition')
    state=assembly.get('design_state')
    checks={
        'registered_route_ids_match_native_recipe':set(model['routes'])==route_ids,
        'all_registered_ports_coincident':all(c['gap_mm']<=1e-6 for c in model['connections']),
        'all_propellant_edges_from_registered_routes':set(map(tuple,expected_edges)).issubset(set(map(tuple,flow_edges))) if state else True,
        'rocket_mass_flow_matches_shared_state':close(candidate['performance']['mass_flow_kg_s'],state['mass_flow_kg_s']['rocket_primary']) if state else True,
        'captured_air_matches_shared_state':close(transition['ideal_capture_mass_flow_kg_s'],state['mass_flow_kg_s']['captured_air_ideal']) if state else True,
        'mission_propellant_matches_rocket_flow':close(candidate['vehicle_screen']['vehicle']['rocket_propellant_mass_kg'],candidate['performance']['mass_flow_kg_s']*run['requirements']['burn_duration_s']),
        'shared_stage_interfaces_coincident':all(i['gap_mm']<=1e-6 and i['section_mismatch_mm']<=1e-6 for i in assembly.get('interfaces',[])),
        'all_assembly_bodies_exported':assembly_expected.issubset(exported) if assembly_artifact else True,
        'all_native_core_bodies_exported':{'core_'+p for p in core_expected}.issubset(exported) if assembly_artifact else True,
        'assembly_recipe_matches_export':assembly_artifact['recipe_sha256']==assembly['recipe_sha256'] if assembly_artifact else True,
        'native_core_scene_matches_export':assembly_artifact['source_core_scene_sha256']==artifact['scene_sha256'] if assembly_artifact else True,
        'exported_component_triangle_ranges_partition_mesh':contiguous and
              sum(count for _,count in ranges)==(assembly_artifact.get('triangles') if assembly_artifact else expected_native_triangles),
        'assembly_body_ranges_match_scene_manifest':scene_range_match,
        'native_core_triangle_count_matches_export':sum(body.get('triangle_count',0) for body in exported_bodies if body.get('group')=='core')==expected_native_triangles if assembly_artifact else True,
        'native_core_ranges_follow_assembly_scene':core_ranges_match,
    }
    mass=candidate.get('vehicle_mass_model')
    policy=assembly.get('mesh_policy')
    if policy:
        checks['surface_mesh_controls_match_requirements']=(
            close(policy['surface_edge_mm'],run['requirements']['mesh_surface_edge_mm']) and
            close(policy['chord_tolerance_mm'],run['requirements']['mesh_chord_tolerance_mm']))
    if 'voxel_mm' in artifact:
        checks['native_mesh_voxel_matches_request']=close(artifact['voxel_mm'],run['requirements'].get('mesh_voxel_mm',1.0))
    resources=candidate.get('orbital_resources')
    if mass:
        vehicle=candidate['vehicle_screen']['vehicle']
        checks.update({
            'mission_dry_mass_matches_selected_mass_model':close(vehicle['dry_mass_excluding_payload_kg'],mass['selected_dry_mass_kg']),
            'flight_launch_mass_matches_mission_mass':close(candidate['flight_screen']['launch_mass_kg'],vehicle['budget_initial_mass_kg']),
            'mission_reference_area_matches_selected_envelope':close(vehicle['reference_area_m2'],math.pi*(mass['selected_reference_diameter_m']/2)**2),
            'component_mass_estimate_closes':close(mass['estimated_dry_mass_kg'],
                (sum(row['mass_kg'] for row in mass['components'])+mass['unmodeled_equipment_allowance_kg'])*(1+mass['mass_margin_fraction'])),
        })
        if resources:
            rows={row['id']:row['mass_kg'] for row in mass['components']}
            checks['orbital_resource_masses_in_vehicle_budget']=all(
                key in rows and close(rows[key],value) for key,value in resources['component_masses_kg'].items())
    if not all(checks.values()):
        raise ValueError('Vega system connection failed: '+', '.join(k for k,v in checks.items() if not v))

    # Each visible body has explicit provenance. Some parts are intentionally
    # envelopes or support concepts rather than physically solved components.
    core_parts={p['id']:p for p in candidate['components']}
    outer_parts={p['id']:p for p in assembly.get('components',[])}
    components=[]
    for body in exported_bodies:
        identity=body['component_id']
        native=body.get('group')=='core'
        source_id=identity[5:] if native else identity
        part=(core_parts if native else outer_parts).get(source_id)
        if not part:
            raise ValueError('Exported body has no source component: '+identity)
        drivers=next((c['drivers'] for c in model['components'] if c['id']==source_id),None)
        if drivers is None:
            drivers=(['solved rocket mass flow','chamber pressure','nozzle profile','manufacturing screen'] if native else
                     ['shared RBCC design state','stage interface','geometry field','manufacturing feature screen'])
        components.append({'id':identity,'name':part['name'],'group':body.get('group','core' if native else 'assembly'),
                           'triangle_count':body['triangle_count'],'drivers':drivers,'role':part['role'],
                           'evidence_class':'screened_core_geometry' if native else 'conditional_assembly_geometry'})

    identities={
        'requirements_sha256':digest(run['requirements']),
        'rocket_solution_sha256':digest(candidate['performance']),
        'core_geometry_sha256':digest(geometry),
        'registered_routes_sha256':digest(model),
        'shared_state_sha256':digest(state) if state else None,
        'assembly_recipe_sha256':assembly.get('recipe_sha256'),
        'picogk_scene_sha256':artifact['scene_sha256'],
        'connected_stl_sha256':assembly_artifact['stl_sha256'] if assembly_artifact else None,
        'vehicle_mass_model_sha256':digest(mass) if mass else None,
        'orbital_resources_sha256':digest(resources) if resources else None,
    }
    result={'schema_version':4,'status':'connected_unvalidated','run_id':run.get('id'),
            'family':run['requirements']['propulsion_family'],'identities':identities,
            'flow':{'nodes':assembly.get('topology',{}).get('flow',{}).get('nodes',[]),
                    'edges':flow_edges,'registered_routes':model['routes']},
            'components':components,'checks':checks,
            'unresolved':list(dict.fromkeys(run.get('unresolved',[])+state.get('unresolved',[]) if state else run.get('unresolved',[]))),
            'scope':'One traceable run across screens, registered ports, geometry, PicoGK core and exported bodies. Connection does not validate performance or manufacture.'}
    result['contract_sha256']=digest({k:v for k,v in result.items() if k!='contract_sha256'})
    return result
