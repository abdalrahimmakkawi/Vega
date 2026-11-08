"""Geometry-derived mass bookkeeping and a conditional tank-growth sizing model.

Material densities and equipment allowances are explicit assumptions. The mass
estimate is not a whole-vehicle structural design or a fused-solid mass property.
"""
import math

ROCKET_EQUATION_SOURCE='https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/'


def capped_tank_volume_mm3(radius, wall, length):
    if not all(math.isfinite(v) for v in (radius,wall,length)) or min(radius,wall)<=0 or length<=2*wall:
        raise ValueError('Tank mass model requires a positive cavity')
    return math.pi*((radius+wall)**2*length-radius**2*(length-2*wall))


def inverse_tank_growth(delta_v, exhaust_velocity, fixed_mass, tank_mass_per_propellant):
    """Solve P = (exp(dv/ve)-1) * (fixed_mass + k*P).

    Fixed mass includes payload and all non-scaling dry mass. k is an explicitly
    frozen local tank mass slope, not an empirical whole-spacecraft mass law.
    """
    if not all(math.isfinite(v) for v in (delta_v,exhaust_velocity,fixed_mass,tank_mass_per_propellant)) or delta_v<0 or exhaust_velocity<=0 or fixed_mass<=0 or tank_mass_per_propellant<0:
        raise ValueError('Invalid inverse mass sizing boundary')
    exponent=delta_v/exhaust_velocity
    if exponent>700:return {'status':'outside_numerical_domain','propellant_mass_kg':None}
    ratio=math.expm1(exponent);denominator=1-ratio*tank_mass_per_propellant
    if denominator<=0:return {'status':'no_finite_single_stage_solution','propellant_mass_kg':None,
        'structural_feedback_factor':ratio*tank_mass_per_propellant}
    propellant=ratio*fixed_mass/denominator
    dry=fixed_mass+tank_mass_per_propellant*propellant
    if not math.isfinite(propellant+dry):return {'status':'outside_numerical_domain','propellant_mass_kg':None}
    achieved=exhaust_velocity*math.log1p(propellant/dry)
    return {'status':'conditional_solution','propellant_mass_kg':propellant,'final_mass_kg':dry,
        'initial_mass_kg':dry+propellant,'delta_v_residual_m_s':achieved-delta_v,
        'structural_feedback_factor':ratio*tank_mass_per_propellant,
        'maximum_ideal_delta_v_m_s':exhaust_velocity*math.log1p(1/tank_mass_per_propellant) if tank_mass_per_propellant else None}


def estimate_vehicle_mass(brief,candidate):
    geometry=candidate['geometry'];assembly=candidate.get('assembly',{});engineering=candidate['engineering']
    core_density=brief.core_material_density_kg_m3;tank_density=brief.tank_material_density_kg_m3
    structure_density=brief.assembly_material_density_kg_m3
    rows=[]
    def add(identity,volume,density,method):
        if not math.isfinite(volume) or volume<0:raise ValueError('Invalid material volume: '+identity)
        rows.append({'id':identity,'material_volume_mm3':volume,'assumed_density_kg_m3':density,
                     'mass_kg':volume*1e-9*density,'method':method})
    shell_volume=0
    wall=geometry['wall_mm']
    for (za,ra),(zb,rb) in zip(geometry['profile_mm'],geometry['profile_mm'][1:]):
        inner=ra*ra+ra*rb+rb*rb
        outer=(ra+wall)**2+(ra+wall)*(rb+wall)+(rb+wall)**2
        shell_volume+=math.pi*(zb-za)*(outer-inner)/3
    add('pressure_shell_uncut',shell_volume,core_density,'Exact frustum integration of the saved piecewise-linear inner and outer profiles; passages not subtracted')
    tank_variable_mass=0;tank_fixed_mass=0;propellant=engineering['mass_flow_kg_s']['chamber']*brief.burn_duration_s
    for tank in geometry['systems']['tanks']:
        r,w,length=tank['radius_mm'],tank['wall_mm'],tank['length_mm']
        add(tank['id'],capped_tank_volume_mm3(r,w,length),tank_density,'Capped cylindrical shell, matching recipe dimensions; ports not subtracted')
        tank_fixed_mass+=2*math.pi*w*(r+w)**2*1e-9*tank_density
        # Separate cap mass from a continuous cavity-length model. Round-up in
        # tank_size is represented in the current estimate, not in the slope.
        medium='fuel' if tank['id']=='fuel_tank' else 'oxidizer'
        sizing=engineering['tank_sizing'][medium]
        continuous_length=sizing['capacity_m3']*1e9/(math.pi*r*r)
        tank_variable_mass+=math.pi*((r+w)**2-r*r)*continuous_length*1e-9*tank_density
    for tube in geometry['systems']['manifolds']:
        length=sum(math.dist(a,b) for a,b in zip(tube['points'],tube['points'][1:]))
        add(tube['id'],math.pi*(tube['outer_radius_mm']**2-tube['bore_radius_mm']**2)*length,
            core_density,'Annular area times routed centerline length; bend/junction overlap not removed')
    injector=geometry['systems']['injector']
    add('injector_uncut',math.pi*injector['radius_mm']**2*injector['length_mm'],core_density,
        'Uncut injector cylinder; outlet holes not subtracted')
    for identity,audit in assembly.get('topology',{}).get('surfaces',{}).items():
        add(identity,audit['signed_volume_mm3'],structure_density,
            'Signed volume of saved closed component triangles; overlapping members/joints counted separately')
    for identity,mass in candidate.get('orbital_resources',{}).get('component_masses_kg',{}).items():
        rows.append({'id':identity,'material_volume_mm3':None,'assumed_density_kg_m3':None,
            'mass_kg':mass,'method':'Orbital power/thermal sizing with declared assumed areal mass or battery specific energy'})
    modeled=sum(row['mass_kg'] for row in rows)
    allowance=brief.vehicle_unmodeled_dry_mass_kg
    estimate=(modeled+allowance)*(1+brief.vehicle_mass_margin_fraction)
    selected=estimate if brief.vehicle_mass_mode=='component_estimate' else brief.vehicle_dry_mass_kg
    margin=selected-estimate
    tank_mass=sum(row['mass_kg'] for row in rows if row['id'] in ('fuel_tank','oxidizer_tank'))
    fixed=(modeled-tank_mass+allowance+tank_fixed_mass)*(1+brief.vehicle_mass_margin_fraction)+brief.payload_mass_kg
    slope=tank_variable_mass/propellant*(1+brief.vehicle_mass_margin_fraction)
    screen=candidate['vehicle_screen'];budget=screen['budget']
    requested_dv=budget['remaining_speed_gap_m_s']
    inverse=inverse_tank_growth(requested_dv,budget['vacuum_effective_exhaust_velocity_m_s'],fixed,slope)
    if inverse['propellant_mass_kg'] is not None:
        inverse['burn_duration_s']=inverse['propellant_mass_kg']/engineering['mass_flow_kg_s']['chamber']
        inverse['within_burn_duration_domain']=.5<=inverse['burn_duration_s']<=20
    inverse.update({'required_delta_v_m_s':requested_dv,'tank_mass_slope_kg_per_kg':slope,
        'fixed_mass_including_payload_kg':fixed,
        'scope':'Conditional inverse rocket equation with fixed tank radii, wall thickness, materials and all non-tank masses. It does not resize the enclosing assembly, predict flight losses, or qualify a single-stage vehicle.',
        'source':ROCKET_EQUATION_SOURCE})
    envelope=assembly.get('dimensions',candidate['dimensions'])
    required_diameter=envelope['diameter_mm']/1000
    selected_diameter=max(brief.vehicle_diameter_m,required_diameter) if brief.vehicle_mass_mode=='component_estimate' else brief.vehicle_diameter_m
    return {'status':'geometry_derived_estimate','mode':brief.vehicle_mass_mode,'components':rows,
        'modeled_material_mass_kg':modeled,'unmodeled_equipment_allowance_kg':allowance,
        'mass_margin_fraction':brief.vehicle_mass_margin_fraction,'estimated_dry_mass_kg':estimate,
        'selected_dry_mass_kg':selected,'specified_dry_mass_kg':brief.vehicle_dry_mass_kg,
        'assembly_envelope_diameter_m':required_diameter,'selected_reference_diameter_m':selected_diameter,
        'specified_budget_margin_kg':brief.vehicle_dry_mass_kg-estimate,
        'checks':{'selected_dry_mass_covers_estimate':margin>=-1e-8,
                  'vehicle_reference_diameter_contains_assembly_envelope':selected_diameter+1e-12>=required_diameter},
        'inverse_sizing':inverse,
        'scope':'Gross component mass estimate with explicit equipment allowance and margin. Orbital array, battery and radiator masses use declared sizing assumptions. Uncut core envelopes overcount some material; cooling ports, core ribs/jacket, pressurant bottle, valves, vehicle skin, payload bay, wings, power distribution hardware, avionics and TPS are not independently modeled. Overlaps are not unioned. No upper/lower mass bound or manufactured material assignment is claimed.'}
