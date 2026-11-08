"""Reduced-order pressure-fed concept model with explicit assumptions and gates.

This module closes mass and steady pressure budgets for one selected family. It
does not predict combustion stability, transient operation, phase change, or
hardware qualification.
"""
from math import ceil, hypot, isfinite, pi, sqrt
from .circuits import cooling_layout
from .thermal_model import thermal_segment

PROPERTY_ASSUMPTIONS={
    'lox_rp1':{'fuel':'RP-1','fuel_density_kg_m3':807.0,'oxidizer_density_kg_m3':1142.0,
               'fuel_cp_j_kg_k':2100.0,'fuel_viscosity_pa_s':0.0016,
               'oxidizer_viscosity_pa_s':0.0002,'fuel_inlet_k':293.0,
               'source':'NASA propellant density references; heat capacity and viscosity are screening assumptions'},
    'lox_lh2':{'fuel':'LH2','fuel_density_kg_m3':70.5,'oxidizer_density_kg_m3':1142.0,
               'fuel_cp_j_kg_k':9700.0,'fuel_viscosity_pa_s':0.000013,
               'oxidizer_viscosity_pa_s':0.0002,'fuel_inlet_k':20.0,
               'constant_liquid_model_limit_k':32.976,
               'property_limit_source':'NIST Selected Properties of Hydrogen, NBS Monograph 168; hydrogen critical temperature 32.976 K',
               'source':'NASA propellant density references; single-phase heat capacity and viscosity are screening assumptions'},
}
PROPERTY_SOURCE='https://ntrs.nasa.gov/api/citations/20140002709/downloads/20140002709.pdf'

def wetted_area_m2(profile,z_start=None,z_end=None):
    """Internal surface area of the profile, clipped to the actual cooled span."""
    z_start=profile[0][0] if z_start is None else z_start
    z_end=profile[-1][0] if z_end is None else z_end
    area=0.0
    for (za,ra),(zb,rb) in zip(profile,profile[1:]):
        lo=max(za,z_start);hi=min(zb,z_end)
        if hi<=lo:continue
        rlo=ra+(rb-ra)*(lo-za)/(zb-za)
        rhi=ra+(rb-ra)*(hi-za)/(zb-za)
        area+=pi*(rlo+rhi)*hypot(hi-lo,rhi-rlo)*1e-6
    return area

def routed_cooling_screen(b,profile,fuel,prop,channel_count,channel_radius_mm,gas_temperature_k=None):
    """Steady single-phase energy and friction balances on the meshed centerline."""
    layout=cooling_layout(profile,b.wall_mm,channel_count,channel_radius_mm)
    points=layout['paths'][2]['points']  # all parallel channels share this length
    coolant_k=prop['fuel_inlet_k'];loss_bar=0.0;length_m=0.0;segments=[]
    for p,q in zip(reversed(points[1:]),reversed(points[:-1])):
        segment_m=sqrt(sum((a-bb)**2 for a,bb in zip(p,q)))/1000
        mid=(p[2]+q[2])/2
        r=next(ra+(rb-ra)*(mid-za)/(zb-za) for (za,ra),(zb,rb) in zip(profile,profile[1:]) if za<=mid<=zb)
        slope=next((rb-ra)/(zb-za) for (za,ra),(zb,rb) in zip(profile,profile[1:]) if za<=mid<=zb)
        surface_m2=2*pi*r*hypot(q[2]-p[2],slope*(q[2]-p[2]))*1e-6
        heat_w=b.design_heat_flux_mw_m2*1e6*surface_m2
        delta_bar,velocity,reynolds=darcy_loss_bar(fuel/channel_count,prop['fuel_density_kg_m3'],prop['fuel_viscosity_pa_s'],channel_radius_mm,segment_m)
        outlet_k=coolant_k+heat_w/(fuel*prop['fuel_cp_j_kg_k'])
        thermal={}
        if b.thermal_model=='thermal_resistance':
            if gas_temperature_k is None:raise ValueError('Thermal resistance model requires a gas temperature boundary')
            thermal=thermal_segment(coolant_k,gas_temperature_k,fuel*prop['fuel_cp_j_kg_k'],surface_m2,
                channel_count*2*pi*channel_radius_mm/1000*segment_m,
                (b.wall_mm/2-channel_radius_mm)/1000,b.wall_conductivity_w_m_k,b.gas_htc_w_m2_k,b.coolant_htc_w_m2_k)
            heat_w=thermal['heat_w'];outlet_k=thermal['bulk_outlet_k']
        segments.append({'z_from_mm':p[2],'z_to_mm':q[2],'route_length_m':segment_m,
                         'wetted_area_m2':surface_m2,'heat_w':heat_w,'bulk_inlet_k':coolant_k,
                         'bulk_outlet_k':outlet_k,'friction_loss_bar':delta_bar,**thermal})
        coolant_k=outlet_k;loss_bar+=delta_bar;length_m+=segment_m
    return {'route_length_m':length_m,'wetted_area_m2':sum(s['wetted_area_m2'] for s in segments),
            'heat_load_w':sum(s['heat_w'] for s in segments),'coolant_outlet_k':coolant_k,
            'cooling_loss_bar':loss_bar,'channel_velocity_m_s':velocity,
            'channel_reynolds':reynolds,'axial_segments':segments}

def darcy_loss_bar(mdot,density,viscosity,bore_radius_mm,length_m):
    radius=bore_radius_mm/1000
    area=pi*radius*radius
    velocity=mdot/(density*area)
    reynolds=2*radius*velocity*density/viscosity
    friction=64/reynolds if reynolds<2300 else 0.3164/reynolds**0.25
    pressure=friction*length_m/(2*radius)*density*velocity**2/2
    return pressure/1e5,velocity,reynolds

def tank_size(mdot,duration_s,density,inner_radius_mm,wall_mm,ullage_fraction):
    propellant_mass=mdot*duration_s
    required_volume=propellant_mass/density/(1-ullage_fraction)
    inner_length_mm=ceil(required_volume/(pi*(inner_radius_mm/1000)**2)*1000)
    return {'required_propellant_kg':propellant_mass,'capacity_m3':required_volume,
            'inner_radius_mm':inner_radius_mm,'length_mm':inner_length_mm+2*wall_mm,
            'ullage_fraction':ullage_fraction}


def apply_operating_thermal(b,performance,profile,engineering):
    if not b.cooling_passages:return
    operating=engineering['operating_point']
    gas=operating.get('converged_chemistry',performance['chemistry'])
    flow=operating['variables']['fuel_flow']['value']
    routed=routed_cooling_screen(b,profile,flow,engineering['properties'],engineering['channel_count'],
        engineering['channel_radius_mm'],gas['chamber_temperature_k'])
    if b.thermal_model=='thermal_resistance':
        wall=max(s['hot_wall_peak_k'] for s in routed['axial_segments'])
        gradient=max(s['wall_gradient_peak_k'] for s in routed['axial_segments'])
    else:
        # Prescribed heat flux stays a boundary condition, but the coolant
        # temperature must use the solved branch flow rather than design flow.
        net_wall_mm=b.wall_mm-2*engineering['channel_radius_mm']
        flux=b.design_heat_flux_mw_m2*1e6
        gradient=flux*(net_wall_mm/1000)/b.wall_conductivity_w_m_k
        wall=routed['coolant_outlet_k']+gradient+flux/b.coolant_htc_w_m2_k
    engineering['thermal']['operating_case']={**routed,'hot_wall_peak_k':wall,
        'wall_gradient_peak_k':gradient,'fuel_flow_kg_s':flow,'gas_boundary_temperature_k':gas['chamber_temperature_k'],
        'energy_residual_w':routed['heat_load_w']-flow*engineering['properties']['fuel_cp_j_kg_k']*(routed['coolant_outlet_k']-engineering['properties']['fuel_inlet_k'])}
    structural=engineering['structural_screen'];previous=structural['utilization']
    structural['estimated_thermal_stress_mpa']=max(structural['estimated_thermal_stress_mpa'],110000*17e-6*gradient/(1-.3))
    structural['utilization']=max(structural['shell_hoop_mpa']+structural['estimated_thermal_stress_mpa'],structural['tank_hoop_mpa'])/b.allowable_stress_mpa
    checks=engineering['checks']
    checks['operating_coolant_temperature']=routed['coolant_outlet_k']<=b.max_coolant_outlet_k
    checks['operating_hot_wall_temperature']=wall<=b.max_wall_temperature_k
    checks['operating_liquid_property_domain']=routed['coolant_outlet_k']<engineering['properties'].get('constant_liquid_model_limit_k',float('inf'))
    checks['pressure_hoop_screen']=structural['utilization']<=1
    engineering['analytical_screen_pass']=all(checks.values())
    engineering['preliminary_score_lower_is_better']+=1000*(structural['utilization']-previous)+max(0,routed['coolant_outlet_k']-b.max_coolant_outlet_k)

def evaluate(b,performance,profile,channel_count,channel_radius_mm):
    if b.propellant_model not in PROPERTY_ASSUMPTIONS and b.propellant_model!='assumed':
        raise ValueError('The pressure-fed family requires a supported propellant property set')
    prop=PROPERTY_ASSUMPTIONS['lox_rp1' if b.propellant_model=='assumed' else b.propellant_model]
    total=performance['mass_flow_kg_s']
    fuel=total/(1+b.mixture_ratio);oxidizer=total-fuel
    chamber_radius=profile[0][1];throat_radius=min(r for _,r in profile)
    tank_radius=max(25.0,1.3*chamber_radius)
    fuel_tank=tank_size(fuel,b.burn_duration_s,prop['fuel_density_kg_m3'],tank_radius,b.wall_mm,0.15)
    ox_tank=tank_size(oxidizer,b.burn_duration_s,prop['oxidizer_density_kg_m3'],tank_radius,b.wall_mm,0.15)
    fuel_feed_bore=max(3.0,sqrt(fuel/(pi*prop['fuel_density_kg_m3']*3.0))*1000)
    ox_feed_bore=max(3.0,sqrt(oxidizer/(pi*prop['oxidizer_density_kg_m3']*3.0))*1000)
    feed_length_m=(profile[-1][0]+tank_radius+100)/1000
    fuel_feed_loss,fuel_feed_velocity,_=darcy_loss_bar(fuel,prop['fuel_density_kg_m3'],prop['fuel_viscosity_pa_s'],fuel_feed_bore,feed_length_m)
    ox_feed_loss,ox_feed_velocity,_=darcy_loss_bar(oxidizer,prop['oxidizer_density_kg_m3'],prop['oxidizer_viscosity_pa_s'],ox_feed_bore,feed_length_m)
    routed=routed_cooling_screen(b,profile,fuel,prop,channel_count,channel_radius_mm,performance['chemistry']['chamber_temperature_k']) if b.cooling_passages else None
    cooling_loss=routed['cooling_loss_bar'] if routed else 0.0
    cooling_velocity=routed['channel_velocity_m_s'] if routed else 0.0
    heat_load_w=routed['heat_load_w'] if routed else 0.0
    coolant_outlet_k=routed['coolant_outlet_k'] if routed else prop['fuel_inlet_k']
    injector_loss_bar=b.chamber_pressure_bar*b.injector_pressure_drop_fraction
    injector_cd=0.7
    def injector_orifice_radius(mdot,density):
        return sqrt(mdot/(pi*injector_cd*sqrt(2*density*injector_loss_bar*1e5)))*1000
    injector_fuel_radius=injector_orifice_radius(fuel,prop['fuel_density_kg_m3'])
    injector_ox_radius=injector_orifice_radius(oxidizer,prop['oxidizer_density_kg_m3'])
    required_fuel_tank_bar=b.chamber_pressure_bar+injector_loss_bar+fuel_feed_loss+cooling_loss+b.valve_loss_bar+b.pressure_reserve_bar
    required_ox_tank_bar=b.chamber_pressure_bar+injector_loss_bar+ox_feed_loss+b.valve_loss_bar+b.pressure_reserve_bar
    pressure_margin_bar=b.tank_pressure_bar-max(required_fuel_tank_bar,required_ox_tank_bar)
    throat_pitch_mm=2*pi*(throat_radius+b.wall_mm/2)/channel_count
    circumferential_ligament_mm=throat_pitch_mm-2*channel_radius_mm
    radial_ligament_mm=b.wall_mm-2*channel_radius_mm
    net_shell_mm=radial_ligament_mm if b.cooling_passages else b.wall_mm
    shell_hoop_mpa=b.chamber_pressure_bar*0.1*chamber_radius/net_shell_mm
    tank_hoop_mpa=b.tank_pressure_bar*0.1*tank_radius/b.wall_mm
    wall_heat_flux=b.design_heat_flux_mw_m2*1e6
    wall_gradient_k=wall_heat_flux*(net_shell_mm/1000)/b.wall_conductivity_w_m_k
    estimated_hot_wall_k=coolant_outlet_k+wall_gradient_k+wall_heat_flux/b.coolant_htc_w_m2_k
    if routed and b.thermal_model=='thermal_resistance':
        wall_gradient_k=max(s['wall_gradient_peak_k'] for s in routed['axial_segments'])
        estimated_hot_wall_k=max(s['hot_wall_peak_k'] for s in routed['axial_segments'])
    thermal_stress_mpa=110000*17e-6*wall_gradient_k/(1-0.3)
    stress_utilization=max(shell_hoop_mpa+thermal_stress_mpa,tank_hoop_mpa)/b.allowable_stress_mpa
    pressurant_r=2077.0  # helium screening assumption
    liquid_volume_m3=b.burn_duration_s*(fuel/prop['fuel_density_kg_m3']+oxidizer/prop['oxidizer_density_kg_m3'])
    pressurant_delivered_kg=b.tank_pressure_bar*1e5*liquid_volume_m3/(pressurant_r*b.pressurant_temperature_k)
    storage_final_bar=b.tank_pressure_bar+b.regulator_reserve_bar
    bottle_volume_m3=pressurant_delivered_kg*pressurant_r*b.pressurant_temperature_k/((b.pressurant_storage_bar-storage_final_bar)*1e5)
    pressure_schedule=[{'time_s':b.burn_duration_s*f,'source_pressure_bar':b.pressurant_storage_bar-(b.pressurant_storage_bar-storage_final_bar)*f,
                        'regulated_tank_pressure_bar':b.tank_pressure_bar} for f in (0,0.25,0.5,0.75,1)]
    checks={
        'mass_balance':abs(total-fuel-oxidizer)<1e-10,
        'pressure_margin':pressure_margin_bar>=0,
        'coolant_bulk_temperature':not b.cooling_passages or coolant_outlet_k<=b.max_coolant_outlet_k,
        'pressure_hoop_screen':stress_utilization<=1,
        'estimated_hot_wall_temperature':not b.cooling_passages or estimated_hot_wall_k<=b.max_wall_temperature_k,
        'pressurant_supply_margin':storage_final_bar>b.tank_pressure_bar,
        'radial_ligament':not b.cooling_passages or radial_ligament_mm>=b.minimum_ligament_mm,
        'circumferential_ligament':not b.cooling_passages or circumferential_ligament_mm>=b.minimum_ligament_mm,
        'voxel_feature':not b.cooling_passages or min(radial_ligament_mm,circumferential_ligament_mm)>=2*b.mesh_voxel_mm,
        'channel_velocity_screen':not b.cooling_passages or cooling_velocity<=12.0,
        'routed_cooling_energy_closure':not b.cooling_passages or abs(heat_load_w-fuel*prop['fuel_cp_j_kg_k']*(coolant_outlet_k-prop['fuel_inlet_k']))<=max(1e-6,heat_load_w*1e-10),
        'routed_cooling_span':not b.cooling_passages or (routed['route_length_m']>0 and routed['wetted_area_m2']>0),
        'fuel_property_domain':not b.cooling_passages or coolant_outlet_k<prop.get('constant_liquid_model_limit_k',float('inf')),
        'injector_voxel_resolution':min(injector_fuel_radius,injector_ox_radius)>=b.mesh_voxel_mm,
    }
    if not all(isfinite(v) for v in [pressure_margin_bar,coolant_outlet_k,stress_utilization,bottle_volume_m3]):
        raise ValueError('Nonfinite system solution')
    edges=[
        {'from':'fuel_tank','to':'fuel_feed','flow_kg_s':fuel},
        {'from':'fuel_feed','to':'fuel_inlet','flow_kg_s':fuel},
        {'from':'fuel_inlet','to':'cooling_channels','flow_kg_s':fuel},
        {'from':'cooling_channels','to':'fuel_outlet','flow_kg_s':fuel},
        {'from':'fuel_outlet','to':'fuel_return','flow_kg_s':fuel},
        {'from':'fuel_return','to':'injector_fuel','flow_kg_s':fuel},
        {'from':'injector_fuel','to':'chamber','flow_kg_s':fuel},
        {'from':'oxidizer_tank','to':'oxidizer_feed','flow_kg_s':oxidizer},
        {'from':'oxidizer_feed','to':'injector_oxidizer','flow_kg_s':oxidizer},
        {'from':'injector_oxidizer','to':'chamber','flow_kg_s':oxidizer},
    ]
    if not b.cooling_passages:
        bypass={'fuel_inlet','cooling_channels','fuel_outlet','fuel_return'}
        edges=[e for e in edges if e['from'] not in bypass and e['to'] not in bypass]
        edges += [{'from':'fuel_feed','to':'injector_fuel','flow_kg_s':fuel}]
    mass_at_chamber=sum(e['flow_kg_s'] for e in edges if e['to']=='chamber')
    nodes={e['from'] for e in edges}|{e['to'] for e in edges}
    internal=nodes-{'fuel_tank','oxidizer_tank','chamber'}
    def reaches_chamber(start):
        seen={start};front=[start]
        while front:
            node=front.pop()
            for edge in edges:
                if edge['from']==node and edge['to'] not in seen:
                    seen.add(edge['to']);front.append(edge['to'])
        return 'chamber' in seen
    checks['network_closure']=abs(mass_at_chamber-total)<1e-10 and all(
        abs(sum(e['flow_kg_s'] for e in edges if e['to']==node)-
            sum(e['flow_kg_s'] for e in edges if e['from']==node))<1e-10 for node in internal)
    checks['both_propellants_reach_chamber']=reaches_chamber('fuel_tank') and reaches_chamber('oxidizer_tank')
    score=1000*stress_utilization+3*(cooling_loss+fuel_feed_loss+ox_feed_loss)+max(0,coolant_outlet_k-b.max_coolant_outlet_k)
    score+=channel_count*channel_radius_mm**2*0.02
    return {'channel_count':channel_count,'channel_radius_mm':channel_radius_mm,
        'mass_flow_kg_s':{'fuel':fuel,'oxidizer':oxidizer,'chamber':total},
        'tank_sizing':{'fuel':fuel_tank,'oxidizer':ox_tank},
        'feed_bore_radius_mm':{'fuel':fuel_feed_bore,'oxidizer':ox_feed_bore},
        'injector_screen':{'discharge_coefficient_assumed':injector_cd,'pressure_drop_bar':injector_loss_bar,
                           'single_fuel_orifice_radius_mm':injector_fuel_radius,
                           'single_oxidizer_orifice_radius_mm':injector_ox_radius,
                           'note':'One equivalent orifice per propellant sizes area only; spray, mixing and stability are not predicted.'},
        'pressure_bar':{'tank_available':b.tank_pressure_bar,'fuel_required':required_fuel_tank_bar,
                        'oxidizer_required':required_ox_tank_bar,'margin':pressure_margin_bar,
                        'injector_loss':injector_loss_bar,'valve_loss_each_branch':b.valve_loss_bar,'fuel_feed_loss':fuel_feed_loss,
                        'oxidizer_feed_loss':ox_feed_loss,'cooling_loss':cooling_loss},
        'thermal':{'assumed_heat_flux_mw_m2':b.design_heat_flux_mw_m2 if b.thermal_model=='prescribed_flux' else None,'assumed_heat_load_w':heat_load_w,
                   'heat_load_w':heat_load_w,'thermal_model':b.thermal_model,
                   'gas_boundary_temperature_k':performance['chemistry']['chamber_temperature_k'],
                   'gas_htc_w_m2_k':b.gas_htc_w_m2_k if b.thermal_model=='thermal_resistance' else None,
                   'wall_gradient_peak_k':wall_gradient_k,
                   'fuel_inlet_k':prop['fuel_inlet_k'],'estimated_bulk_outlet_k':coolant_outlet_k,
                   'estimated_hot_wall_k':estimated_hot_wall_k,'assumed_wall_conductivity_w_m_k':b.wall_conductivity_w_m_k,
                   'assumed_coolant_htc_w_m2_k':b.coolant_htc_w_m2_k,
                   'single_phase_property_assumption':True,
                   'model':('distributed gas convection / planar ligament conduction / coolant convection; fixed gas reservoir and film coefficients' if b.thermal_model=='thermal_resistance' else 'steady one-dimensional routed centerline, constant properties and user-specified heat flux') if routed else 'cooling disabled',
                   'route_length_m':routed['route_length_m'] if routed else 0.0,
                   'wetted_area_m2':routed['wetted_area_m2'] if routed else 0.0,
                   'axial_segments':routed['axial_segments'] if routed else [],
                   'constant_liquid_property_domain_pass':checks['fuel_property_domain'],
                   'energy_balance_residual_w':heat_load_w-fuel*prop['fuel_cp_j_kg_k']*(coolant_outlet_k-prop['fuel_inlet_k'])},
        'structural_screen':{'shell_hoop_mpa':shell_hoop_mpa,'tank_hoop_mpa':tank_hoop_mpa,
                             'estimated_thermal_stress_mpa':thermal_stress_mpa,
                             'allowable_stress_mpa':b.allowable_stress_mpa,'utilization':stress_utilization,
                             'assumed_elastic_modulus_mpa':110000,'assumed_expansion_per_k':17e-6,'assumed_poisson_ratio':0.3},
        'pressurization_screen':{'model':'isothermal regulated helium ideal-gas mass balance','helium_r_j_kg_k':pressurant_r,
                                'delivered_mass_kg':pressurant_delivered_kg,'minimum_bottle_volume_m3':bottle_volume_m3,
                                'pressure_schedule':pressure_schedule,
                                'limitations':'No regulator flow curve, valve Cv, thermal transient, real-gas correction or bottle structural design.'},
        'manufacturing_screen':{'radial_ligament_mm':radial_ligament_mm,
                                 'throat_circumferential_ligament_mm':circumferential_ligament_mm,
                                 'minimum_ligament_mm':b.minimum_ligament_mm},
        'flow_network':edges,'checks':checks,'analytical_screen_pass':all(checks.values()),
        'preliminary_score_lower_is_better':score,
        'ranking_basis':'Screen-pass first, then 1000×hoop utilization + 3×feed/cooling pressure loss (bar) + bulk-temperature exceedance (K) + 0.02×channel count×radius² (mm²). This is a configurable heuristic, not validated optimization.',
        'properties':prop,'property_source':PROPERTY_SOURCE,
        'limitations':['Steady incompressible feed and single-phase fuel properties are assumptions.',
                       ('Heat transfer uses a fixed chamber-temperature reservoir, assumed film coefficients and a planar ligament approximation; no axial conduction, spreading, radiation or gas cooling.' if b.thermal_model=='thermal_resistance' else 'Heat flux is a specified scenario, not a combustion or conjugate-heat-transfer prediction.'),
                       'Hot-wall temperature and thermal stress use assumed heat transfer and material constants; no FEA or fatigue certification.',
                       'Pressurant supply is an isothermal ideal-gas screen; regulator and valve hardware are not designed.',
                       'Hoop stress is a thin-wall screening formula, not pressure-vessel or thermal-fatigue certification.',
                       'Injector loss fraction is an input; atomization and combustion stability are unsolved.']+
            (['The LH2 constant-liquid-property model is invalid when the predicted coolant temperature reaches the NIST critical temperature; a pressure-dependent property model is required.'] if b.propellant_model=='lox_lh2' and not checks['fuel_property_domain'] else [])+
            (['Manual gas mode still uses LOX/RP-1 liquid property assumptions for the feed network.'] if b.propellant_model=='assumed' else [])}
