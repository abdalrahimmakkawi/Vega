"""Whole-spacecraft requirements assessment, distinct from numerical consistency."""


def assess_system(run):
    candidate=run['candidates'][0];engineering=candidate['engineering']
    vehicle=candidate['vehicle_screen'];family=run['requirements']['propulsion_family']
    failures=[name for name,passed in engineering['checks'].items() if not passed]
    if vehicle['status']=='failed':failures.append('mission_velocity_budget')
    mass=candidate.get('vehicle_mass_model')
    resources=candidate.get('orbital_resources')
    if mass:failures.extend('vehicle_'+key for key,passed in mass['checks'].items() if not passed)
    if run.get('artifact') and run.get('execution',{}).get('mesh_integrity_screen')=='failed':
        failures.append('native_mesh_integrity')
    operating=engineering.get('operating_point',{})
    if abs(operating.get('chamber_pressure_deviation_fraction',0))>.01:
        failures.append('requested_chamber_pressure_requires_regulation')
    obligations=[
        {'id':'vehicle_mass_packaging','depends_on':['payload','propulsion','structure'],
         'status':'component_estimate_incomplete' if mass else 'missing_model','required_output':'Closed subsystem mass budget and collision-checked payload/vehicle packaging'},
        {'id':'aerodynamics_trajectory','depends_on':['vehicle_mass_packaging','propulsion'],
         'status':'conditional_screen','required_output':'Coupled ascent and orbital insertion meeting the mission with declared margins'},
        {'id':'vehicle_structure','depends_on':['aerodynamics_trajectory','vehicle_mass_packaging'],
         'status':'partial_frame_model','required_output':'Vehicle loads, stress, buckling, joints and fatigue closure'},
        {'id':'vehicle_thermal','depends_on':['aerodynamics_trajectory','propulsion'],
         'status':'conditional_orbital_and_engine_screens' if resources else 'partial_engine_screen','required_output':'Vehicle thermal balance and applicable ascent/reentry protection'},
        {'id':'power_avionics_gnc','depends_on':['aerodynamics_trajectory','vehicle_mass_packaging'],
         'status':'power_sizing_only_gnc_missing' if resources else 'missing_model','required_output':'Power/energy, guidance/navigation/control, communications and attitude-control budgets'},
        {'id':'manufacturing_validation','depends_on':['vehicle_structure','vehicle_thermal','propulsion'],
         'status':'unvalidated','required_output':'Process-specific tolerances, inspection access and matched physical evidence'},
    ]
    if family!='rocket_only':
        obligations.append({'id':'combined_cycle','depends_on':['propulsion','aerodynamics_trajectory'],
            'status':'conditional_geometry','required_output':'Airbreathing net thrust, fuel staging and mode-transition operating envelope'})
    return {'scope':'whole_spacecraft_and_propulsion','status':'failed_requirements_and_incomplete_models' if failures else 'incomplete_models',
        'failed_requirements':failures,'obligations':obligations,'complete':False,
        'statement':'Passing equation residuals and mesh checks establishes software consistency, not whole-spacecraft engineering closure.'}
