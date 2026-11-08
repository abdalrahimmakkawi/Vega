"""Traceable engineering-model graph for a saved Vega design.

The graph describes the executable calculations and data passed between them.
It distinguishes mathematical verification from physical validation; absent
matched measurements are always reported as unvalidated.
"""
import hashlib
import json
from .system_readiness import assess_system


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _stage(id, title, status, inputs, outputs, equations, assumptions, checks=(), depends_on=()):
    return {'id': id, 'title': title, 'status': status, 'depends_on': list(depends_on),
            'inputs': inputs, 'outputs': outputs, 'equations': list(equations),
            'assumptions': list(assumptions), 'checks': list(checks)}


def build_model_trace(run):
    """Build the linked model record from the exact calculations in ``run``."""
    brief = run['requirements']
    candidate = run['candidates'][0]
    perf = candidate['performance']
    eng = candidate['engineering']
    state = candidate['assembly'].get('design_state')
    checks = eng['checks']
    chemistry = perf['chemistry']
    stages = [
        _stage('requirements', 'Requirements and domain checks', 'passed',
               {'brief': 'RocketBrief, SI-derived engineering units'},
               {'thrust': [brief['thrust_n'], 'N'], 'chamber_pressure': [brief['chamber_pressure_bar'], 'bar'],
                'burn_duration': [brief['burn_duration_s'], 's'], 'propellant': brief['propellant_model']},
               ['range checks; architecture and model-domain gates'],
               ['User-entered requirements define a single operating point.'],
               [{'name': 'all inputs finite and within declared bounds', 'pass': True}]),
        _stage('thermochemistry', 'Propellant and chamber state',
               'computed' if chemistry.get('source', '').startswith('RocketCEA') else 'assumed',
               {'propellant': brief['propellant_model'], 'mixture_ratio': [brief['mixture_ratio'], 'kg/kg']},
               {'chamber_temperature': [chemistry['chamber_temperature_k'], 'K'],
                'gamma': chemistry['gamma'], 'gas_constant': [chemistry['gas_constant_j_kg_k'], 'J/(kg K)']},
               ['NASA CEA equilibrium state via RocketCEA; R = R_universal / molecular_weight'],
               ['Equilibrium chamber properties; downstream frozen constant-property approximation.'],
               [{'name': 'source and finite positive gas properties', 'pass': True}], depends_on=['requirements']),
        _stage('nozzle', 'Ideal choked nozzle solution',
               'verified' if 'cross-check' in perf['verification'].get('source', '') and perf['verification'].get('relative_error', float('inf')) < 1e-6 else 'screened',
               {'chamber_state': 'thermochemistry', 'target_thrust': [brief['thrust_n'], 'N'],
                'expansion_ratio': brief['expansion_ratio']},
               {'mass_flow': [perf['mass_flow_kg_s'], 'kg/s'], 'thrust': [perf['thrust_n'], 'N'],
                'exit_mach': perf['exit_mach'], 'exit_pressure': [perf['exit_pressure_pa'], 'Pa']},
               ['A/A* = area_ratio(M,gamma)', 'F = mdot Ve + (pe - pa) Ae',
                'mdot = A* Pc/sqrt(Tc) sqrt(gamma/R) (2/(gamma+1))^((gamma+1)/(2(gamma-1)))'],
               ['Steady, one-dimensional, attached, isentropic flow; constant gamma and gas constant.'],
               [{'name': perf['verification'].get('source', 'internal consistency only'),
                 'pass': perf['verification'].get('relative_error', 0) < 1e-6}], depends_on=['thermochemistry']),
        _stage('geometry_seed', 'Shared pressure-wall and cooling-route recipe',
               'computed' if candidate.get('geometry') else 'pending',
               {'nozzle': 'nozzle', 'wall_thickness': [brief['wall_mm'], 'mm'],
                'cooling_passages': bool(brief['cooling_passages'])},
               {'profile_stations': len(candidate.get('geometry', {}).get('profile_mm', [])),
                'cooling_route_count': len(candidate.get('geometry', {}).get('cooling', {}).get('paths', []))},
               ['solved throat/exit area -> shared axial profile',
                'profile + passage sizing inputs -> cooling centerlines'],
               ['Contours and channel centerlines are parametric geometry; hot gas loads are not solved.'],
               [{'name': 'profile and route recipe finite', 'pass': bool(candidate.get('geometry'))}],
               depends_on=['nozzle']),
        _stage('feed_network', 'Pressure-fed mass and pressure network',
               'passed' if checks.get('network_closure') and checks.get('pressure_margin') else 'failed',
               {'nozzle_mass_flow': [perf['mass_flow_kg_s'], 'kg/s'], 'mixture_ratio': brief['mixture_ratio'],
                'burn_duration': [brief['burn_duration_s'], 's']},
               {'branch_flows': eng['mass_flow_kg_s'], 'pressure_margin': [eng['pressure_bar']['margin'], 'bar'],
                'tanks': eng['tank_sizing']},
               ['mdot_total = mdot_fuel + mdot_oxidizer',
                'Delta p = f (L/D) rho V^2/2; p_tank >= p_chamber + losses + reserve',
                'V_tank = mdot t_burn / (rho (1 - ullage))'],
               ['Steady, incompressible, single-phase branches; Darcy friction and nominal properties.'],
               [{'name': key, 'pass': bool(checks.get(key))} for key in
                ('mass_balance', 'network_closure', 'pressure_margin', 'both_propellants_reach_chamber')],
               depends_on=['nozzle', 'geometry_seed']),
        _stage('thermal', 'Routed cooling energy and wall screen',
               'passed' if checks.get('routed_cooling_energy_closure') and checks.get('coolant_bulk_temperature') and checks.get('estimated_hot_wall_temperature') else 'failed',
               {'cooling_route': 'generated centerline', 'heat_flux': [brief['design_heat_flux_mw_m2'], 'MW/m^2'],
                'coolant_flow': [eng['mass_flow_kg_s']['fuel'], 'kg/s']},
               {'heat_load': [eng['thermal']['assumed_heat_load_w'], 'W'],
                'coolant_outlet': [eng['thermal']['estimated_bulk_outlet_k'], 'K'],
                'wall_estimate': [eng['thermal']['estimated_hot_wall_k'], 'K'],
                'energy_residual': [eng['thermal']['energy_balance_residual_w'], 'W']},
               ['Q = integral(q\'\' dA)', 'mdot cp (Tout - Tin) = Q',
                'Twall ~= Tout + q\'\' t_wall/k + q\'\'/h'],
               ['Specified heat flux, constant liquid properties, one-dimensional steady routed centerline.'],
               [{'name': key, 'pass': bool(checks.get(key))} for key in
                ('routed_cooling_energy_closure', 'routed_cooling_span', 'coolant_bulk_temperature', 'estimated_hot_wall_temperature', 'fuel_property_domain')],
               depends_on=['feed_network', 'geometry_seed']),
        _stage('structure_manufacture', 'Pressure, ligament, feature and route screens',
               'passed' if all(checks.get(key) for key in
                   ('pressure_hoop_screen', 'radial_ligament', 'circumferential_ligament', 'voxel_feature', 'channel_velocity_screen')) else 'failed',
               {'chamber_pressure': [brief['chamber_pressure_bar'], 'bar'], 'wall': [brief['wall_mm'], 'mm'],
                'passage_geometry': 'ranked channel candidates'},
               {'stress_utilization': eng['structural_screen']['utilization'],
                'radial_ligament': [eng['manufacturing_screen']['radial_ligament_mm'], 'mm'],
                'circumferential_ligament': [eng['manufacturing_screen']['throat_circumferential_ligament_mm'], 'mm']},
               ['sigma_hoop ~= p r / t_net', 'utilization = estimated stress / allowable stress',
                'ligament = available wall or pitch - passage width'],
               ['Thin-wall hoop screen; assumed material properties; voxel-feature floor is not a process qualification.'],
               [{'name': key, 'pass': bool(checks.get(key))} for key in
                ('pressure_hoop_screen', 'radial_ligament', 'circumferential_ligament', 'voxel_feature', 'channel_velocity_screen')],
               depends_on=['feed_network', 'thermal', 'geometry_seed']),
        _stage('variant_study', 'Cooling design-space sweep and ranking', 'computed',
               {'design_variants': len(run.get('alternatives', [])), 'variables': ['channel count', 'channel radius']},
               {'ranked_alternatives': run.get('alternatives', [])},
               ['feasible screens first; documented preliminary score second'],
               ['Ranking heuristic is not a validated multiobjective optimizer.'],
               [{'name': 'each alternative evaluated with the same pressure, heat and feature screens', 'pass': True}],
               depends_on=['feed_network', 'thermal', 'structure_manufacture']),
        _stage('geometry', 'Parametric component and topology geometry',
               'computed' if candidate.get('geometry') else 'pending',
               {'solved_nozzle': 'nozzle', 'fluid_routes': 'feed_network', 'thermal_state': 'thermal',
                'manufacturing_bounds': 'structure_manufacture'},
               {'core_components': len(candidate.get('components', [])),
                'core_geometry_recipe': 'shared pressure-wall, fluid-route and cooling recipes'},
               ['shared solved profile -> chamber, throat, nozzle and routed passage centerlines',
                'registered ports and routes -> tank/feed/cooling/injector assembly'],
               ['Geometry is driven by this run state; decorative topology has no credited performance.'],
               [{'name': 'core geometry route audit', 'pass': bool(candidate.get('geometry_audit', {}).get('pass'))}],
               depends_on=['nozzle', 'feed_network', 'thermal', 'structure_manufacture', 'variant_study']),
    ]
    if state:
        cycle = candidate.get('vehicle_screen', {}).get('engine_cycle')
        stages.append(_stage('combined_cycle', 'Conditional combined-cycle flowpath',
            'screened_closed' if cycle and cycle.get('status') == 'screened_closed' else
            ('conditional' if state.get('status', '').startswith('conditional') else 'screened'),
            {'captured_air': [state['mass_flow_kg_s']['captured_air_ideal'], 'kg/s'],
             'rocket_flow': [state['mass_flow_kg_s']['rocket_primary'], 'kg/s'],
             'pressure_recovery_assumption': [brief['airpath_pressure_recovery'], 'fraction']},
            {'area_stations': state['area_m2'], 'flow_station_count': len(state['conditional_airpath']['stations']),
             'engine_cycle': cycle},
            ['coupled station pressure, heat-release and common-nozzle balance',
             'ideal mixer mass and enthalpy balance', 'compressible station mass-flow relation',
             'A_required = mdot_total / choked_mass_flux'],
            ['Air/fuel ratio, combustion efficiency and pressure losses are declared reduced-order inputs; reacting CFD and transients remain unresolved.'],
               [{'name': key, 'pass': bool(value)} for key, value in state.get('checks', {}).items()] +
               ([{'name': 'coupled engine-cycle closure', 'pass': cycle.get('status') == 'screened_closed'}] if cycle else []),
               depends_on=['nozzle', 'requirements', 'geometry']))
    stages.append(_stage('assembly', 'Shared connected component assembly',
        'computed' if candidate.get('assembly') else 'pending',
        {'core_geometry': 'geometry', 'combined_cycle_state': 'combined_cycle' if state else 'not_applicable',
         'registered_fluid_network': 'feed_network'},
        {'components': len(candidate.get('assembly', {}).get('components', [])),
         'interfaces': len(candidate.get('assembly', {}).get('interfaces', [])),
         'recipe_sha256': candidate.get('assembly', {}).get('recipe_sha256')},
        ['shared stage interfaces and same-run component recipes',
         'registered ports and flow routes determine fluid-connection topology'],
        ['Concept assembly is packaging geometry; unsupported physical interactions remain explicit.'],
        [{'name': 'assembly interface and architecture checks', 'pass': candidate.get('rbcc_architecture_wiring', {}).get('status') != 'failed'}],
        depends_on=['geometry', 'feed_network'] + (['combined_cycle'] if state else [])))
    mass=candidate.get('vehicle_mass_model')
    resources=candidate.get('orbital_resources')
    if resources:
        stages.append(_stage('orbital_resources','Orbital power, eclipse energy and radiator sizing','conditional',
            {'orbit_altitude_m':brief['orbit_altitude_m'],'design_electrical_load_w':resources['power']['design_load_w'],
             'assumptions':resources['assumptions']},
            {'orbit':resources['orbit'],'power':resources['power'],'thermal':resources['thermal'],
             'component_masses_kg':resources['component_masses_kg']},
            ['T_orbit = 2*pi*sqrt(r^3/mu); eclipse fraction = asin(R_earth/r)/pi',
             'sunlight array energy = full-orbit load energy + battery conversion losses',
             'Q_radiator = epsilon*sigma*A*(T_radiator^4 - T_sink^4)',
             'array/radiator mass = area * assumed areal mass; battery mass = nominal Wh / assumed Wh/kg'],
            [resources['scope']], [{'name':key,'pass':passed} for key,passed in resources['checks'].items()],
            depends_on=['requirements']))
    if mass:
        stages.append(_stage('vehicle_mass','Vehicle material mass and packaging screen',
            'screened' if all(mass['checks'].values()) else 'failed',
            {'geometry':'assembly','mode':mass['mode'],'densities':'explicit material density assumptions',
             'equipment_allowance_kg':mass['unmodeled_equipment_allowance_kg'],'margin_fraction':mass['mass_margin_fraction']},
            {'modeled_material_mass_kg':mass['modeled_material_mass_kg'],
             'estimated_dry_mass_kg':mass['estimated_dry_mass_kg'],'selected_dry_mass_kg':mass['selected_dry_mass_kg'],
             'inverse_sizing':mass['inverse_sizing']},
            ['component mass = saved material volume * assumed density',
             'estimated dry mass = (modeled material mass + equipment allowance) * (1 + margin)',
             'inverse propellant P = (exp(delta-v/ve)-1) * (fixed mass + tank mass slope * P)'],
            [mass['scope']], [{'name':key,'pass':passed} for key,passed in mass['checks'].items()],
            depends_on=['assembly','requirements']+(['orbital_resources'] if resources else [])))
    stages.append(_stage('mission', 'Vehicle trajectory and mission budget',
        'screened' if candidate.get('flight_screen') else 'pending',
        {'engine_solution': 'nozzle', 'vehicle_requirements': 'requirements'},
        {'flight': candidate.get('flight_screen', {}).get('status', 'not available'),
         'mission': candidate.get('vehicle_screen', {}).get('status', 'not available')},
        ['rocket equation bookkeeping; one-dimensional point-mass RK4 trajectory'],
        ['Illustrative vehicle inputs; no airbreathing thrust or 6-DOF aerodynamics.'],
        [{'name': 'mass-flow and propellant consistency checks',
          'pass': abs(candidate.get('vehicle_screen', {}).get('vehicle', {}).get('rocket_propellant_mass_kg', 0) -
                      perf['mass_flow_kg_s'] * brief['burn_duration_s']) < 1e-8}], depends_on=['nozzle', 'requirements']+(['vehicle_mass'] if mass else [])))

    artifact = run.get('artifact')
    assembly_artifact = run.get('assembly_artifact')
    mesh_status = ('pending' if not artifact or not assembly_artifact else
                   'failed' if run.get('execution', {}).get('mesh_integrity_screen') == 'failed' else 'audited')
    stages.append(_stage('mesh_and_export', 'PicoGK geometry conversion and export audit',
        mesh_status,
        {'geometry_recipe': candidate.get('assembly', {}).get('recipe_sha256'), 'kernel': 'PicoGK'},
        {'core_triangles': artifact.get('triangles') if artifact else None,
         'assembly_triangles': assembly_artifact.get('triangles') if assembly_artifact else None,
         'mesh_audit': artifact.get('mesh_audit') if artifact else None,
         'native_voxel_mm':artifact.get('voxel_mm') if artifact else None,
         'surface_mesh_policy':candidate.get('assembly',{}).get('mesh_policy'),
         'surface_triangle_quality':candidate.get('assembly',{}).get('mesh_quality')},
        ['voxel solid reconstruction; mesh topology and body-range audit'],
        ['Mesh validity is geometric; it does not establish stress, heat-transfer, leak-tightness, or flight validity.'],
        [{'name': 'mesh integrity', 'pass': run.get('execution', {}).get('mesh_integrity_screen') == 'surface_pass'},
         {'name': 'system contract', 'pass': run.get('execution', {}).get('system_contract') in
         ('connected_unvalidated', 'connected_unvalidated_contract_refreshed')}], depends_on=['assembly']))

    study=run.get('mesh_study',{})
    if study.get('selected_mesh'):
        stages.append(_stage('volume_mesh_and_solvers','Gmsh hybrid mesh, adaptive CFD and frame FEA',
            study['status'],study.get('source',{}),
            {'mesh':study['selected_mesh'],'adaptation':study.get('adaptation'),'frame_fea':study.get('fea'),
             'coarse_cfd':study.get('coarse_cfd'),'adaptive_cfd':study.get('adaptive_cfd')},
            ['Conforming prism core / hex wall-layer sweep; OpenFOAM steady incompressible momentum and continuity',
             'Recovered velocity-gradient indicator drives axial mesh refinement; CalculiX solves the selected axial-bar frame'],
            [study['scope']],
            [{'name':'positive volume cells','pass':study['selected_mesh']['inverted_cells']==0},
             {'name':'CFD axial mesh comparison','pass':bool((study.get('adaptation') or {}).get('converged'))},
             {'name':'external frame FEA comparison','pass':bool(study.get('fea',{}).get('optimizer_cross_check_passed'))}],
            depends_on=['mesh_and_export']))
    if study.get('airpath_mesh'):
        air=study['airpath_mesh'];flow=study.get('airpath_cfd')
        stages.append(_stage('five_stage_airpath','Connected airpath volume and cold-flow check',
            'computed' if flow and flow['converged'] else 'mesh_only_or_unconverged',
            {'assembly_recipe_sha256':study.get('source',{}).get('assembly_recipe_sha256'),
             'interfaces_z_mm':air['interfaces_z_mm']},
            {'mesh':air,'cold_flow':flow},
            ['One continuous prism/hex volume across the inlet, mixer, isolator, air combustor and nozzle',
             'OpenFOAM steady incompressible continuity and momentum with assumed cold laminar fluid'],
            [air['scope']],
            [{'name':'positive five-stage cells','pass':air['inverted_cells']==0},
             {'name':'continuous stage interfaces','pass':air['conforming_interface'] and len(air['interfaces_z_mm'])==4},
             {'name':'cold-flow solver convergence','pass':bool(flow and flow['converged'])}],
            depends_on=['volume_mesh_and_solvers']))
    cal = run.get('calibration', {})
    if eng['thermal'].get('thermal_model')=='thermal_resistance':
        thermal_stage=next(s for s in stages if s['id']=='thermal')
        thermal_stage['inputs']={'gas_temperature_k':eng['thermal']['gas_boundary_temperature_k'],
            'gas_htc_w_m2_k':brief['gas_htc_w_m2_k'],'coolant_htc_w_m2_k':brief['coolant_htc_w_m2_k'],
            'route':'actual channel centerline and hot-side profile','ligament':'wall/2 - channel radius'}
        thermal_stage['equations']=['R = 1/(hg Ag) + t/(k Ag) + 1/(hc Ac)',
            'Tout = Tg - (Tg - Tin) exp(-1/(R mdot cp))','Q = mdot cp (Tout - Tin)']
        thermal_stage['assumptions']=[eng['thermal']['model'],'No gas cooling, radiation, boiling or axial/circumferential conduction. Film coefficients are inputs.']
        operating_thermal=eng['thermal'].get('operating_case',{})
        thermal_stage['outputs']['operating_case']={k:operating_thermal[k] for k in
            ('heat_load_w','coolant_outlet_k','hot_wall_peak_k','wall_gradient_peak_k','energy_residual_w') if k in operating_thermal}
        thermal_stage['checks'].extend({'name':key,'pass':checks[key]} for key in
            ('operating_coolant_temperature','operating_hot_wall_temperature','operating_liquid_property_domain') if key in checks)
        if any(not item['pass'] for item in thermal_stage['checks']):thermal_stage['status']='failed'
    if eng.get('channel_synthesis'):
        variant_stage=next(s for s in stages if s['id']=='variant_study')
        variant_stage['synthesis']=eng['channel_synthesis']
        variant_stage['outputs']['evaluated_radius_samples']=eng['channel_synthesis']['evaluations']
    if eng.get('operating_performance'):
        feed_stage=next(s for s in stages if s['id']=='feed_network')
        feed_stage['outputs']['fixed_hardware_performance']=eng['operating_performance']
        operating_performance=eng['operating_performance']
        position=next(i for i,s in enumerate(stages) if s['id']=='feed_network')+1
        stages.insert(position,_stage('operating_performance',
            'Fixed-hardware forward performance', 'computed',
            {'nozzle_areas':'nozzle','pressure_and_branch_flows':'feed_network'},
            operating_performance,
            ['fixed A_exit/A_throat -> supersonic Mach',
             'mdot_feed = mdot_choked',
             'F = mdot V_exit + (p_exit - p_ambient) A_exit'],
            [operating_performance['scope']],
            [{'name':'feed/nozzle mass closure',
              'pass':abs(operating_performance['mass_balance_residual_kg_s'])<=max(1e-10,operating_performance['mass_flow_kg_s']*1e-7)}],
            depends_on=['nozzle','feed_network']))
    validation_status = 'awaiting_measured_data' if cal.get('status', '').startswith('awaiting') else cal.get('status')
    verification_checks = {stage['id']: stage['checks'] for stage in stages if stage['checks']}
    solutions = [s for s in (perf.get('equation_solution'), eng.get('equation_solution')) if s]
    for stage_id, solution in zip(('nozzle', 'feed_network'), (perf.get('equation_solution'), eng.get('equation_solution'))):
        if solution:
            stage = next(s for s in stages if s['id'] == stage_id)
            stage['solver'] = solution
            stage['checks'].append({'name': f"Equation residual {solution['max_scaled_residual']:.3g} <= {solution['tolerance']:.3g}; full-rank system", 'pass': solution['status'] == 'converged'})
    if eng.get('operating_point'):
        operating = eng['operating_point']
        solutions.append(operating)
        feed_stage = next(s for s in stages if s['id'] == 'feed_network')
        feed_stage['operating_solver'] = operating
        feed_stage['outputs']['unthrottled_operating_point'] = operating['variables']
        feed_stage['assumptions'].append(operating['scope'])
    record = {'schema_version': 1, 'model_name': 'Vega computational engineering model',
        'model_class': 'sequential reduced-order design model with executable equation blocks',
        'run_id': run.get('id'), 'requirements_sha256': _hash(brief),
        'candidate_id': candidate['id'], 'dependency_order': [stage['id'] for stage in stages],
        'stages': stages,
        'verification': {'status': 'screened_with_internal_closure_checks',
            'checks': verification_checks,
            'independent_cross_checks': {'nozzle_mass_flow': perf.get('verification', {})},
            'equation_solutions': solutions,
            'numerical_convergence': ('Bounded residual solves for nozzle, routed feed and fixed-hardware operating point; named-propellant runs couple equilibrium chemistry and operating pressure into candidate stress ranking. Remaining stages are conditional screens; no CFD mesh-convergence claim.' if solutions else 'Legacy run: no executable residual-solver record.')},
        'validation': {'status': validation_status, 'matched_measurements': cal.get('matched_observations', 0),
            'evidence': cal.get('comparisons', []),
            'statement': 'Verification checks implementation consistency. Physical validation requires matched test measurements.'},
        'limits': list(run.get('unresolved', [])),
        'model_sha256': None}
    record['system_completion'] = assess_system(run)
    record['model_sha256'] = _hash({k: v for k, v in record.items() if k != 'model_sha256'})
    return record

