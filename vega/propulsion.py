"""Conditional, zero-dimensional bench calculations. No engine qualification.

Gas-phase equilibrium and frozen ideal-gas expansion are deliberate limits.
No cryogenic, reacting-flow, turbomachinery-map or combustion-stability model.
"""
from math import pi, sqrt, isfinite
import cantera as ct
from scipy.optimize import brentq


def positive(**values):
    for name, value in values.items():
        if type(value) not in (int, float) or not isfinite(value) or value <= 0:
            raise ValueError(f'{name} must be finite and positive')


def combust(oxidizer_mass_kg_s, fuel_mass_kg_s, pressure_pa,
            oxidizer_temperature_k, fuel_temperature_k=300., oxidizer='air', heat_removed_w=0.):
    positive(oxidizer_mass_kg_s=oxidizer_mass_kg_s, fuel_mass_kg_s=fuel_mass_kg_s,
             pressure_pa=pressure_pa, oxidizer_temperature_k=oxidizer_temperature_k,
             fuel_temperature_k=fuel_temperature_k)
    if oxidizer not in ('air','oxygen'):
        raise ValueError('Oxidizer must be air or oxygen')
    if min(oxidizer_temperature_k, fuel_temperature_k)<200:
        raise ValueError('Gas-phase model excludes cryogenic liquid reactants')
    gas=ct.Solution('h2o2.yaml')
    gas.TPX=oxidizer_temperature_k,pressure_pa,('O2:1,N2:3.76' if oxidizer=='air' else 'O2:1')
    ox_y=gas.Y.copy(); ox_h=gas.enthalpy_mass
    gas.TPX=fuel_temperature_k,pressure_pa,'H2:1'
    total=oxidizer_mass_kg_s+fuel_mass_kg_s
    mixture=(oxidizer_mass_kg_s*ox_y+fuel_mass_kg_s*gas.Y)/total
    enthalpy=(oxidizer_mass_kg_s*ox_h+fuel_mass_kg_s*gas.enthalpy_mass)/total
    gas.HPY=enthalpy,pressure_pa,mixture
    elements={e:gas.elemental_mass_fraction(e) for e in gas.element_names}
    gas.equilibrate('HP')
    if not isfinite(heat_removed_w) or heat_removed_w<0:
        raise ValueError('Extracted heat must be nonnegative')
    if heat_removed_w:
        gas.HP=enthalpy-heat_removed_w/total,pressure_pa
        gas.equilibrate('HP')
    element_error=max(abs(gas.elemental_mass_fraction(e)-v) for e,v in elements.items())
    energy_error=total*(gas.enthalpy_mass-enthalpy)+heat_removed_w
    return dict(temperature_k=float(gas.T),pressure_pa=pressure_pa,
        mass_flow_kg_s=total,gamma=float(gas.cp_mass/gas.cv_mass),
        gas_constant_j_kgk=float(ct.gas_constant/gas.mean_molecular_weight),
        cp_j_kgk=float(gas.cp_mass), composition={s:float(y) for s,y in zip(gas.species_names,gas.Y) if y>1e-10},
        element_mass_fraction_error=element_error,energy_residual_w=energy_error,
        converged=bool(element_error<1e-8 and abs(energy_error)<1e-4*max(total*abs(enthalpy),1)),
        mechanism='Cantera h2o2.yaml',oxidizer=oxidizer,
        heat_extracted_w=heat_removed_w,
        scope='Adiabatic gas-phase equilibrium; no ignition, kinetics, NOx, atomization or stability prediction')


def nozzle(chamber, expansion_ratio, ambient_pa, intake_mass_kg_s=0., flight_speed_m_s=0.):
    positive(expansion_ratio=expansion_ratio,ambient_pa=ambient_pa)
    if expansion_ratio<1 or min(intake_mass_kg_s,flight_speed_m_s)<0:
        raise ValueError('Invalid nozzle area ratio or inlet momentum')
    g=chamber['gamma']; r=chamber['gas_constant_j_kgk']; t=chamber['temperature_k']; p=chamber['pressure_pa']
    mdot=chamber['mass_flow_kg_s']
    critical=(2/(g+1))**(g/(g-1))
    if ambient_pa/p>=critical:
        return dict(status='unchoked_outside_model',net_thrust_n=None,
                    reason='Supersonic frozen nozzle approximation requires choking')
    def area(m):
        return (2/(g+1)*(1+(g-1)*m*m/2))**((g+1)/(2*(g-1)))/m
    mach=1. if expansion_ratio==1 else brentq(lambda m:area(m)-expansion_ratio,1.00000001,30.)
    throat=mdot*sqrt(t)/(p*sqrt(g/r)*(2/(g+1))**((g+1)/(2*(g-1))))
    exit_area=throat*expansion_ratio
    exit_t=t/(1+(g-1)*mach*mach/2)
    exit_p=p*(exit_t/t)**(g/(g-1))
    speed=mach*sqrt(g*r*exit_t)
    momentum=mdot*speed; pressure=(exit_p-ambient_pa)*exit_area
    ram_drag=intake_mass_kg_s*flight_speed_m_s
    return dict(status='ideal_frozen_estimate',exit_mach=mach,exit_temperature_k=exit_t,
        exit_pressure_pa=exit_p,exit_speed_m_s=speed,throat_area_m2=throat,
        throat_radius_mm=sqrt(throat/pi)*1000,exit_area_m2=exit_area,
        gross_thrust_n=momentum+pressure,ram_drag_n=ram_drag,net_thrust_n=momentum+pressure-ram_drag,
        momentum_thrust_n=momentum,pressure_thrust_n=pressure,
        overexpanded=exit_p<ambient_pa,
        scope='Constant chamber cp/gamma frozen expansion. Separation, friction and installation losses unresolved')


def helium_loop(air_compressor_w, heat_from_air_w, cold_k=150., turbine_inlet_k=900., pressure_ratio=2.):
    """Solve helium circulation and HX3/HX4 duties with constant-cp bookkeeping.

    Includes circulator shaft demand. Fuel sink is NOT infinite: separately
    report the gas-H2 mass needed to absorb HX4 heat under explicit temperatures.
    """
    positive(air_compressor_w=air_compressor_w,heat_from_air_w=heat_from_air_w,
             cold_k=cold_k,turbine_inlet_k=turbine_inlet_k,pressure_ratio=pressure_ratio)
    cp=5193.; gamma=5/3; eta_c=.75; eta_t=.85; mechanical=.95; recovery=.90
    if pressure_ratio*recovery<=1:
        raise ValueError('Helium expansion ratio must exceed one after losses')
    t1=cold_k*(1+(pressure_ratio**((gamma-1)/gamma)-1)/eta_c)
    t4=turbine_inlet_k*(1-eta_t*(1-(pressure_ratio*recovery)**(-(gamma-1)/gamma)))
    specific_t=cp*(turbine_inlet_k-t4)*mechanical
    specific_c=cp*(t1-cold_k)
    if specific_t<=specific_c:
        return dict(status='infeasible',reason='Turbine cannot supply its own circulator plus air compressor')
    flow=air_compressor_w/(specific_t-specific_c)
    t2=t1+heat_from_air_w/(flow*cp)
    hx3=flow*cp*(turbine_inlet_k-t2)
    hx4=flow*cp*(t4-cold_k)
    turbine=flow*specific_t; circulator=flow*specific_c
    shaft=turbine-circulator-air_compressor_w
    # Thermodynamic shaft extracted before mechanical losses enters this balance.
    energy=heat_from_air_w+hx3-hx4-flow*cp*(turbine_inlet_k-t4)+circulator
    sink_in=25.; sink_out=min(t4-20.,600.); sink_pressure=1e6
    hydrogen=ct.Hydrogen()
    hydrogen.TP=sink_in,sink_pressure
    sink_h=hydrogen.enthalpy_mass
    hydrogen.TP=sink_out,sink_pressure
    sink_delta_h=hydrogen.enthalpy_mass-sink_h
    sink_flow=hx4/sink_delta_h if sink_delta_h>0 else None
    feasible=hx3>=0 and hx4>=0 and t2<turbine_inlet_k and sink_flow is not None
    return dict(status='subcycle_balanced' if feasible else 'infeasible',
        helium_mass_flow_kg_s=flow,temperatures_k=dict(cold=cold_k,after_circulator=t1,after_HX1=t2,turbine_in=turbine_inlet_k,turbine_out=t4),
        HX1_w=heat_from_air_w,HX3_required_w=hx3,HX4_rejection_w=hx4,
        turbine_shaft_w=turbine,circulator_shaft_w=circulator,air_compressor_w=air_compressor_w,
        shaft_residual_w=shaft,loop_energy_residual_w=energy,
        required_hydrogen_sink_kg_s=sink_flow,sink_assumptions=dict(inlet_k=sink_in,outlet_k=sink_out,pressure_pa=sink_pressure,enthalpy_rise_j_kg=sink_delta_h,model='Cantera Hydrogen pure-fluid EOS'),
        scope='Constant-cp helium subcycle only; no finite-fuel-loop or preburner closure')


def bench_study(reference_flow_kg_s, expansion_ratio=None):
    """Explicit hypothetical bench case. No aircraft or rated thrust is assumed."""
    ambient=101325.; cooled=305.; cp=1005.; ratio=6.; eta=.78
    compressor_t=cooled*(1+(ratio**(0.4/1.4)-1)/eta)
    power=reference_flow_kg_s*cp*(compressor_t-cooled)
    fuel=reference_flow_kg_s*.029  # Declared illustrative gaseous H2/air ratio.
    chamber=combust(reference_flow_kg_s,fuel,ambient*ratio*.95,compressor_t)
    rocket_chamber=combust(reference_flow_kg_s,reference_flow_kg_s/8,ambient*ratio*.95,300.,oxidizer='oxygen')
    loop=helium_loop(power,reference_flow_kg_s*cp*25)
    sink=loop.get('required_hydrogen_sink_kg_s')
    # Bound the HX3 source against the actual equilibrium gas enthalpy drop.
    pb=ct.Solution('h2o2.yaml')
    pb.TPY=chamber['temperature_k'],chamber['pressure_pa'],chamber['composition']
    hot_h=pb.enthalpy_mass
    pb_exit=loop['temperatures_k']['turbine_in']+30.
    pb.TP=pb_exit,chamber['pressure_pa']
    source_capacity=chamber['mass_flow_kg_s']*(hot_h-pb.enthalpy_mass)*.9
    bleed=loop['HX3_required_w']/source_capacity if source_capacity>0 else None
    preburner_ok=bleed is not None and 0<=bleed<=1
    if preburner_ok:
        chamber=combust(reference_flow_kg_s,fuel,ambient*ratio*.95,compressor_t,
                        heat_removed_w=loop['HX3_required_w']/.9)
    candidates=[]
    for ratio_candidate in (1.2,1.5,2.,3.,4.,(9/3.5)**2):
        air=nozzle(chamber,ratio_candidate,ambient)
        rocket=nozzle(rocket_chamber,ratio_candidate,ambient)
        score=min(air['net_thrust_n'],rocket['net_thrust_n'])
        candidates.append(dict(expansion_ratio=ratio_candidate,air_ideal_thrust_n=air['net_thrust_n'],
            rocket_ideal_thrust_n=rocket['net_thrust_n'],score=score))
    chosen=max(candidates,key=lambda c:c['score'])
    expansion_ratio=chosen['expansion_ratio'] if expansion_ratio is None else expansion_ratio
    air_nozzle=nozzle(chamber,expansion_ratio,ambient)
    rocket_nozzle=nozzle(rocket_chamber,expansion_ratio,ambient)
    checks=dict(combustion_energy_closed=chamber['converged'] and rocket_chamber['converged'],
        helium_subcycle_closed=loop['status']=='subcycle_balanced',
        HX1_cold_end_pinch=loop.get('temperatures_k',{}).get('after_circulator',float('inf'))<cooled,
        finite_fuel_sink_closed=sink is not None and sink<=fuel,
        HX4_temperature_pinch=loop['temperatures_k']['cold']>loop['sink_assumptions']['inlet_k'] and loop['temperatures_k']['turbine_out']>loop['sink_assumptions']['outlet_k'],
        preburner_HX3_capacity_closed=preburner_ok,turbomachinery_maps_available=False,
        chamber_cooling_validated=False,structural_limits_validated=False)
    return dict(status='incomplete_engine_cycle',case='Illustrative gas-phase bench study; no rated engine target',
        inputs=dict(oxidizer_mass_flow_kg_s=reference_flow_kg_s,air_fuel_ratio=fuel/reference_flow_kg_s,
            compressor_pressure_ratio=ratio,compressor_efficiency=eta,combustor_pressure_recovery=.95,
            ambient_pressure_pa=ambient,expansion_ratio=expansion_ratio,flight_speed_m_s=0),
        airbreathing=dict(combustion=chamber,nozzle=air_nozzle,compressor_power_w=power),
        rocket=dict(combustion=rocket_chamber,nozzle=rocket_nozzle),helium=loop,checks=checks,
        preburner=dict(air_and_fuel_bleed_fraction=bleed,gas_exit_k=pb_exit,
            heat_transfer_efficiency=.9,HX3_heat_w=loop['HX3_required_w'],
            gas_heat_extracted_w=loop['HX3_required_w']/.9 if preburner_ok else None,
            scope='Proportional air/fuel bleed with equilibrium enthalpy extraction; pressure losses and actual hardware unresolved'),
        whole_engine_closed=False,flight_capability_verified=False,
        nozzle_search=dict(candidates=candidates,selected_expansion_ratio=expansion_ratio,
            objective='Maximize the smaller ideal nozzle thrust of the two illustrative bench cases',
            geometry_scope='Only area ratio transfers to the enlarged print; physical throat areas are calculated separately'),
        missing_design_inputs=['Rated thrust target','Bench pressure/temperature envelope','Material and manufacturing process','Measured component maps and validation data'],
        sources=['https://www.cantera.org/3.1/examples/python/thermo/equivalenceRatio.html',
                 'https://www.grc.nasa.gov/WWW/BGH/rktthsum.html'])
