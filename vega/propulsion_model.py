"""Reduced-order design-point components consumed by the geometry pipeline.

The nozzle block solves seven simultaneous equations. The routed feed block
solves supply pressure, equivalent injector areas, and coolant energy balance.
Chamber state and wall heat flux remain boundary assumptions, not predictions.
"""
from math import pi, sqrt, isfinite
from .equation_system import Variable as V, Equation as E, solve_system


def nozzle_design(thrust, pc, pa, temperature, gamma, gas_constant, expansion):
    if not (thrust > 0 and pc > pa >= 0 and temperature > 0 and gamma > 1 and gas_constant > 0 and expansion > 1):
        raise ValueError('Outside ideal supersonic nozzle domain')
    if pa/pc >= (2/(gamma+1))**(gamma/(gamma-1)):
        raise ValueError('Back pressure exceeds choked-flow domain')
    def ratio(m):
        return (2/(gamma+1)*(1+(gamma-1)*m*m/2))**((gamma+1)/(2*(gamma-1)))/m
    flux = pc/sqrt(temperature)*sqrt(gamma/gas_constant)*(2/(gamma+1))**((gamma+1)/(2*(gamma-1)))
    area_scale = thrust/pc
    velocity_scale = sqrt(gas_constant*temperature)
    variables = [V('mach', '1', 3., 3., 1., 100.),
                 V('exit_temperature', 'K', temperature/2, temperature, 0., temperature),
                 V('exit_pressure', 'Pa', pc/20, pc, 0., pc),
                 V('exit_velocity', 'm/s', velocity_scale, velocity_scale, 0.),
                 V('throat_area', 'm2', area_scale, area_scale, 0.),
                 V('exit_area', 'm2', expansion*area_scale, expansion*area_scale, 0.),
                 V('mass_flow', 'kg/s', flux*area_scale, flux*area_scale, 0.)]
    equations = [E('supersonic_area_mach', '1', expansion, lambda s: ratio(s['mach'])-expansion),
                 E('stagnation_temperature', 'K', temperature, lambda s: s['exit_temperature']*(1+(gamma-1)*s['mach']**2/2)-temperature),
                 E('isentropic_pressure', 'Pa', pc, lambda s: s['exit_pressure']-pc*(s['exit_temperature']/temperature)**(gamma/(gamma-1))),
                 E('exit_velocity', 'm/s', velocity_scale, lambda s: s['exit_velocity']-s['mach']*sqrt(gamma*gas_constant*s['exit_temperature'])),
                 E('expansion_area', 'm2', expansion*area_scale, lambda s: s['exit_area']-expansion*s['throat_area']),
                 E('choked_mass_flow', 'kg/s', flux*area_scale, lambda s: s['mass_flow']-flux*s['throat_area']),
                 E('momentum_pressure_thrust', 'N', thrust, lambda s: s['mass_flow']*s['exit_velocity']+(s['exit_pressure']-pa)*s['exit_area']-thrust)]
    return solve_system('ideal_nozzle_design', variables, equations)


def close_feed_design(b, engineering):
    """Execute on actual routed losses, before emitting injector geometry.

    Required supply pressures are unknowns; tank pressure is an inequality.
    Do not force an inconsistent tank pressure into a prescribed chamber state.
    """
    p, prop = engineering['pressure_bar'], engineering['properties']
    fuel, oxidizer = (engineering['mass_flow_kg_s'][key] for key in ('fuel', 'oxidizer'))
    pc = b.chamber_pressure_bar*1e5
    dp = pc*b.injector_pressure_drop_fraction
    cd = engineering['injector_screen']['discharge_coefficient_assumed']
    heat = engineering['thermal']['assumed_heat_load_w']
    tin, cp = prop['fuel_inlet_k'], prop['fuel_cp_j_kg_k']
    # Reserve is a design allowance, not an actual friction component.
    base = pc+dp+(b.valve_loss_bar+b.pressure_reserve_bar)*1e5
    variables = [V('fuel_supply_required', 'Pa', base*1.1, pc, 0.),
                 V('oxidizer_supply_required', 'Pa', base*1.1, pc, 0.),
                 V('fuel_orifice_area', 'm2', 1e-5, 1e-5, 0.),
                 V('oxidizer_orifice_area', 'm2', 1e-5, 1e-5, 0.),
                 V('coolant_outlet', 'K', tin+10, tin, 0.)]
    equations = [E('fuel_branch_pressure', 'Pa', pc, lambda s: s['fuel_supply_required']-base-(p['fuel_feed_loss']+p['cooling_loss'])*1e5),
                 E('oxidizer_branch_pressure', 'Pa', pc, lambda s: s['oxidizer_supply_required']-base-p['oxidizer_feed_loss']*1e5),
                 E('fuel_injector_flow', 'kg/s', fuel, lambda s: cd*s['fuel_orifice_area']*sqrt(2*prop['fuel_density_kg_m3']*dp)-fuel),
                 E('oxidizer_injector_flow', 'kg/s', oxidizer, lambda s: cd*s['oxidizer_orifice_area']*sqrt(2*prop['oxidizer_density_kg_m3']*dp)-oxidizer),
                 E('coolant_energy', 'W', max(1., heat, fuel*cp*tin), lambda s: fuel*cp*(s['coolant_outlet']-tin)-heat)]
    state, report = solve_system('routed_feed_design', variables, equations)
    p['fuel_required'] = state['fuel_supply_required']/1e5
    p['oxidizer_required'] = state['oxidizer_supply_required']/1e5
    p['margin'] = b.tank_pressure_bar-max(p['fuel_required'], p['oxidizer_required'])
    for medium in ('fuel', 'oxidizer'):
        engineering['injector_screen']['single_'+medium+'_orifice_radius_mm'] = sqrt(state[medium+'_orifice_area']/pi)*1000
    engineering['thermal']['estimated_bulk_outlet_k'] = state['coolant_outlet']
    engineering['checks']['pressure_margin'] = p['margin'] >= 0
    engineering['analytical_screen_pass'] = all(engineering['checks'].values())
    report['constraints'] = [{'name': 'available_supply_pressure', 'pass': p['margin'] >= 0, 'margin_pa': p['margin']*1e5}]
    report['coupling'] = 'Nozzle mass flow -> route dimensions -> Darcy losses -> pressure and energy closure -> injector geometry'
    engineering['equation_solution'] = report
    return report


def predict_fixed_hardware(b, performance, engineering, tank_pressure_pa=None, chamber_model=None):
    """Predict the unthrottled operating point of the sized hydraulic hardware.

    Unlike sizing, chamber pressure and mixture ratio are outcomes here. This
    A supplied chamber_model updates equilibrium gas properties at every trial.
    Liquid properties remain constant. Regulator dynamics, boiling, combustion
    efficiency and minor losses are omitted.
    """
    from .engineering import darcy_loss_bar
    prop = engineering['properties']
    supply = b.tank_pressure_bar*1e5 if tank_pressure_pa is None else tank_pressure_pa
    ambient = b.ambient_pressure_bar*1e5
    critical = (2/(performance['chemistry']['gamma']+1))**(performance['chemistry']['gamma']/(performance['chemistry']['gamma']-1))
    lower_pc = max(1., ambient/critical)
    if supply <= lower_pc:
        raise ValueError('Supply cannot support the choked operating-point domain')
    design_flow = engineering['mass_flow_kg_s']
    coefficient = performance['mass_flow_kg_s']/(b.chamber_pressure_bar*1e5)
    chemistry_cache = {}
    def chemistry_at(state):
        key = (state['chamber_pressure'],state['oxidizer_flow']/state['fuel_flow'])
        if key not in chemistry_cache:
            chemistry = chamber_model(*key)
            g,t,r = (chemistry[k] for k in ('gamma','chamber_temperature_k','gas_constant_j_kg_k'))
            if not all(isfinite(v) for v in (g,t,r)) or g<=1 or t<=0 or r<=0:
                raise ValueError('Invalid chamber properties in coupled operating solve')
            chemistry_cache[key] = chemistry
        return chemistry_cache[key]
    def nozzle_flow(state):
        if chamber_model is None:
            return coefficient*state['chamber_pressure']
        chemistry = chemistry_at(state)
        g,t,r = (chemistry[k] for k in ('gamma','chamber_temperature_k','gas_constant_j_kg_k'))
        return performance['throat_area_m2']*state['chamber_pressure']/sqrt(t)*sqrt(g/r)*(2/(g+1))**((g+1)/(2*(g-1)))
    cd = engineering['injector_screen']['discharge_coefficient_assumed']
    def loss(medium, flow):
        rho = prop[medium+'_density_kg_m3']; mu = prop[medium+'_viscosity_pa_s']
        radius = engineering['feed_bore_radius_mm'][medium]
        pressure = darcy_loss_bar(flow,rho,mu,radius,engineering['feed_route_lengths_m'][medium])[0]*1e5
        if medium == 'fuel' and b.cooling_passages:
            pressure += darcy_loss_bar(flow/engineering['channel_count'],rho,mu,
                engineering['channel_radius_mm'],engineering['thermal']['route_length_m'])[0]*1e5
        area = pi*(engineering['injector_screen']['single_'+medium+'_orifice_radius_mm']/1000)**2
        pressure += (flow/(cd*area))**2/(2*rho)
        # Interpret prescribed design valve loss as a fixed quadratic resistance.
        pressure += b.valve_loss_bar*1e5*(flow/design_flow[medium])**2
        return pressure
    gap = supply-lower_pc
    initial_pc = min(max(b.chamber_pressure_bar*1e5,lower_pc+.01*gap),supply-.01*gap)
    variables = [V('chamber_pressure','Pa',initial_pc,supply,lower_pc,supply),
                 V('fuel_flow','kg/s',design_flow['fuel'],design_flow['fuel'],0.),
                 V('oxidizer_flow','kg/s',design_flow['oxidizer'],design_flow['oxidizer'],0.)]
    equations = [E('fuel_pressure_balance','Pa',supply,lambda s: supply-s['chamber_pressure']-loss('fuel',s['fuel_flow'])),
                 E('oxidizer_pressure_balance','Pa',supply,lambda s: supply-s['chamber_pressure']-loss('oxidizer',s['oxidizer_flow'])),
                 E('chamber_nozzle_mass_balance','kg/s',performance['mass_flow_kg_s'],lambda s: s['fuel_flow']+s['oxidizer_flow']-nozzle_flow(s))]
    # CEA's formatted input/output has lower resolution than machine epsilon.
    # Perturb far enough to resolve property changes instead of a noisy Jacobian.
    state, report = solve_system('fixed_hardware_unthrottled_operating_point',variables,equations,
                                 difference_step=1e-4 if chamber_model else None)
    if chamber_model is not None:
        chemistry = chemistry_at(state)
        g = chemistry['gamma']
        if ambient/state['chamber_pressure'] >= (2/(g+1))**(g/(g-1)):
            raise ValueError('Converged chemistry is outside the choked-flow domain')
        report['converged_chemistry'] = chemistry
        report['chemistry_evaluations'] = len(chemistry_cache)
    report['boundary_conditions'] = {'tank_pressure_pa':supply,'throat_area_m2':performance['throat_area_m2'],
                                     'gas_state':'recomputed at trial pressure and mixture ratio' if chamber_model else 'frozen at design point','additional_throttling':'none'}
    report['predicted_mixture_ratio'] = state['oxidizer_flow']/state['fuel_flow']
    report['chamber_pressure_deviation_fraction'] = state['chamber_pressure']/(b.chamber_pressure_bar*1e5)-1
    report['scope'] = ('Equilibrium chamber chemistry coupled to steady hydraulics; constant-property ideal nozzle and liquids. No combustion kinetics, stability, or regulation prediction.' if chamber_model else 'Conditional unregulated hydraulic operating point with frozen gas properties; not a reacting-flow or regulated-engine prediction.')
    return report


def apply_operating_load_screen(b, engineering, operating, chamber_radius_mm):
    """Feed solved pressure back into the existing preliminary stress ranking.

    This is still the legacy hoop/thermal screen, not FEA. It must not silently
    use a lower requested pressure when the operating model predicts a higher one.
    """
    structural = engineering['structural_screen']
    previous = structural['utilization']
    predicted_pa = operating['variables']['chamber_pressure']['value']
    pressure_pa = max(b.chamber_pressure_bar*1e5, predicted_pa)
    ligament = b.wall_mm-2*engineering['channel_radius_mm'] if b.cooling_passages else b.wall_mm
    hoop_mpa = pressure_pa/1e6*chamber_radius_mm/ligament
    utilization = max(hoop_mpa+structural['estimated_thermal_stress_mpa'],structural['tank_hoop_mpa'])/b.allowable_stress_mpa
    structural['design_point_shell_hoop_mpa'] = structural['shell_hoop_mpa']
    structural['shell_hoop_mpa'] = hoop_mpa
    structural['utilization'] = utilization
    structural['governing_pressure_pa'] = pressure_pa
    structural['load_basis'] = 'Maximum of requested and predicted unthrottled operating pressure; thermal load remains prescribed.'
    engineering['checks']['pressure_hoop_screen'] = utilization <= 1
    engineering['analytical_screen_pass'] = all(engineering['checks'].values())
    engineering['preliminary_score_lower_is_better'] += 1000*(utilization-previous)
    engineering['operating_point'] = operating


def fixed_nozzle_performance(performance, operating, ambient_pressure_pa):
    """Forward prediction on immutable throat/exit areas at the solved state.

    Uses the same ideal, attached, constant-property equations as nozzle sizing.
    It does not resize a nozzle to recover the requested thrust.
    """
    pc=operating['variables']['chamber_pressure']['value']
    fuel=operating['variables']['fuel_flow']['value']
    oxidizer=operating['variables']['oxidizer_flow']['value']
    chemistry=operating.get('converged_chemistry',performance['chemistry'])
    g,t,r=(chemistry[k] for k in ('gamma','chamber_temperature_k','gas_constant_j_kg_k'))
    at=performance['throat_area_m2'];ae=performance['exit_area_m2']
    pa=ambient_pressure_pa
    if not all(isfinite(v) for v in (pc,fuel,oxidizer,g,t,r,at,ae,pa)):
        raise ValueError('Nonfinite fixed-nozzle state')
    if not (pc>pa>=0 and fuel>0 and oxidizer>0 and g>1 and t>0 and r>0 and ae>at>0):
        raise ValueError('Outside fixed-nozzle domain')
    if pa/pc >= (2/(g+1))**(g/(g-1)):
        raise ValueError('Fixed nozzle is outside choked-flow domain')
    expansion=ae/at
    def area(m):return (2/(g+1)*(1+(g-1)*m*m/2))**((g+1)/(2*(g-1)))/m
    lo,hi=1.,2.
    while area(hi)<expansion:
        hi*=2
        if hi>128:raise ValueError('Supersonic Mach root not bracketed')
    for _ in range(100):
        mid=(lo+hi)/2
        if area(mid)<expansion:lo=mid
        else:hi=mid
    mach=(lo+hi)/2
    te=t/(1+(g-1)*mach*mach/2);pe=pc*(te/t)**(g/(g-1))
    velocity=mach*sqrt(g*r*te)
    nozzle_flow=at*pc/sqrt(t)*sqrt(g/r)*(2/(g+1))**((g+1)/(2*(g-1)))
    mdot=fuel+oxidizer
    residual=mdot-nozzle_flow
    if abs(residual)>max(1e-10,mdot*1e-7):
        raise ValueError('Fixed nozzle does not close the supplied operating mass flow')
    momentum=mdot*velocity;pressure=(pe-pa)*ae;thrust=momentum+pressure
    return {'status':'computed','throat_area_m2':at,'exit_area_m2':ae,
        'chamber_pressure_pa':pc,'mass_flow_kg_s':mdot,'mixture_ratio':oxidizer/fuel,
        'exit_mach':mach,'exit_temperature_k':te,'exit_pressure_pa':pe,
        'exit_velocity_m_s':velocity,'momentum_thrust_n':momentum,
        'pressure_thrust_n':pressure,'thrust_n':thrust,'ideal_isp_s':thrust/(mdot*9.80665),
        'chemistry':chemistry,'mass_balance_residual_kg_s':residual,
        'thrust_deviation_fraction':thrust/performance['thrust_n']-1,
        'overexpanded':pe<pa,'evidence':'ideal_model_prediction',
        'scope':'Fixed geometry at solved unregulated supply conditions; attached isentropic flow, no measured performance validation.'}
