"""Shared reduced-order design state for Vega's RBCC geometry.

This module intentionally separates source equations, bounded heuristics and
unresolved physics.  Geometry consumes this state instead of repeating area
ratios and styling constants in the mesher.
"""
import math

from .inlet import GAMMA as AIR_GAMMA, R as AIR_R
from .airpath_flow import conditional_airpath


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def ideal_mixer_balance(air_mdot, rocket_mdot, inlet, rocket):
    """Conditional adiabatic mass/enthalpy balance and choking area screen.

    Perfect mixing and full ideal air capture are assumed.  No mixed pressure,
    momentum exchange, heat release or installed thrust is predicted here.
    """
    chemistry=rocket['chemistry']
    gas_gamma=chemistry['gamma'];gas_r=chemistry['gas_constant_j_kg_k']
    air_cp=AIR_GAMMA*AIR_R/(AIR_GAMMA-1)
    rocket_cp=gas_gamma*gas_r/(gas_gamma-1)
    total=air_mdot+rocket_mdot
    capacity=air_mdot*air_cp+rocket_mdot*rocket_cp
    inlet_enthalpy=air_mdot*air_cp*inlet['total_temperature_k']
    rocket_enthalpy=rocket_mdot*rocket_cp*chemistry['chamber_temperature_k']
    mixed_temperature=(inlet_enthalpy+rocket_enthalpy)/capacity
    mixed_cp=capacity/total
    mixed_r=(air_mdot*AIR_R+rocket_mdot*gas_r)/total
    mixed_gamma=mixed_cp/(mixed_cp-mixed_r)
    exit=inlet['stations'][-1]
    air_total_pressure=exit['pressure_pa']*(1+(AIR_GAMMA-1)*exit['mach']**2/2)**(AIR_GAMMA/(AIR_GAMMA-1))
    critical_mass_flux=(air_total_pressure/math.sqrt(mixed_temperature)*math.sqrt(mixed_gamma/mixed_r)*
        (2/(mixed_gamma+1))**((mixed_gamma+1)/(2*(mixed_gamma-1))))
    minimum_area=total/critical_mass_flux
    energy_residual=inlet_enthalpy+rocket_enthalpy-total*mixed_cp*mixed_temperature
    return {
        'status':'conditional_ideal_adiabatic_mixing',
        'mass_flow_kg_s':{'air_ideal_capture':air_mdot,'rocket':rocket_mdot,'mixed':total},
        'stagnation_temperature_k':{'air':inlet['total_temperature_k'],
                                    'rocket':chemistry['chamber_temperature_k'],
                                    'mixed_ideal':mixed_temperature},
        'mixed_constant_properties':{'cp_j_kg_k':mixed_cp,'r_j_kg_k':mixed_r,'gamma':mixed_gamma},
        'air_total_pressure_after_normal_shock_pa':air_total_pressure,
        'critical_mass_flux_at_air_pressure_kg_m2_s':critical_mass_flux,
        'minimum_ideal_choked_area_m2':minimum_area,
        'energy_residual_w':energy_residual,
        'mass_residual_kg_s':air_mdot+rocket_mdot-total,
        'sources':['https://www.grc.nasa.gov/www/k-12/airplane/isentrop.html',
                   'https://www.grc.nasa.gov/www/k-12/airplane/normal.html',
                   'https://ntrs.nasa.gov/citations/20010036882'],
        'limits':'Calorically perfect gases, full ideal air capture, adiabatic complete mixing. Air total pressure is a reference bound, not solved mixed pressure. Momentum, combustion and installed thrust are unknown.'
    }


def rbcc_design_state(b, candidate, inlet_area_m2, hydraulic_diameter_mm):
    """Create the single state used by the RBCC flowpath and its geometry.

    Air and rocket mass flows are solved upstream.  Downstream recovery,
    combustion and installed thrust are not solved, so the contour relations
    below remain explicitly identified bounded heuristics.
    """
    transition=candidate['vehicle_screen']['transition']
    air_mdot=transition['ideal_capture_mass_flow_kg_s']
    rocket_mdot=candidate['performance']['mass_flow_kg_s']
    total_mdot=air_mdot+rocket_mdot
    air_fraction=air_mdot/total_mdot
    entrainment_ratio=air_mdot/rocket_mdot
    rocket_exit_area=candidate['performance']['exit_area_m2']
    rocket_exit_momentum=candidate['performance']['momentum_thrust_n']
    capture_momentum=air_mdot*transition['speed_m_s']
    momentum_fraction=rocket_exit_momentum/max(rocket_exit_momentum+capture_momentum,1e-9)
    mixing=ideal_mixer_balance(air_mdot,rocket_mdot,candidate['vehicle_screen']['inlet_reference'],candidate['performance'])
    # A bounded geometry index, now driven by the mixed-stream energy balance.
    thermal_index=clamp((mixing['stagnation_temperature_k']['mixed_ideal']-transition['temperature_k'])/1800,0,1)

    # Bounded reduced-order contour rules.  Each term depends on a solved
    # upstream state so influential requirement changes propagate into mesh.
    mixer_contraction=clamp(.72-.16*air_fraction+.05*momentum_fraction,.56,.76)
    # The 5% margin is above the choked area at an explicitly assumed mixed
    # total-pressure recovery. Recovery is not a computed mixing loss.
    minimum_throat=mixing['minimum_ideal_choked_area_m2']/b.airpath_pressure_recovery*1.05
    mixer_throat=max(inlet_area_m2*mixer_contraction,rocket_exit_area*1.5,minimum_throat)
    mixing['required_ideal_stagnation_pressure_at_mixer_throat_pa']=(
        mixing['air_total_pressure_after_normal_shock_pa']*
        mixing['minimum_ideal_choked_area_m2']/mixer_throat)
    mixing['reference_pressure_headroom_fraction']=(
        1-mixing['required_ideal_stagnation_pressure_at_mixer_throat_pa']/
        mixing['air_total_pressure_after_normal_shock_pa'])
    mixing['assumed_pressure_headroom_fraction']=(
        1-mixing['required_ideal_stagnation_pressure_at_mixer_throat_pa']/
        (mixing['air_total_pressure_after_normal_shock_pa']*b.airpath_pressure_recovery))
    mixer_exit=max(inlet_area_m2*clamp(.82+.08*air_fraction,.82,.90),minimum_throat)
    isolator_exit=max(mixer_exit*clamp(.97-.05*thermal_index,.92,.97),minimum_throat)
    combustor_exit=max(isolator_exit*(1.07+.11*air_fraction),minimum_throat)
    nozzle_throat=max(inlet_area_m2*b.combined_throat_ratio,rocket_exit_area*1.5,minimum_throat)
    nozzle_exit=max(inlet_area_m2*b.combined_exit_ratio,minimum_throat)
    areas={'mixer_inlet':inlet_area_m2,'mixer_throat':mixer_throat,
           'mixer_exit':mixer_exit,'isolator_exit':isolator_exit,
           'combustor_exit':combustor_exit,'common_nozzle_throat':nozzle_throat,
           'common_nozzle_exit':nozzle_exit,'minimum_ideal_choked':minimum_throat}
    flow=conditional_airpath(areas,mixing,b.airpath_pressure_recovery)

    lobe_count=int(b.frame_sectors)
    lobe_amplitude=clamp(.035+.10*air_fraction+.025*thermal_index,.04,.15)
    twist_rad=math.pi*clamp(.35+.35*air_fraction,.35,.70)
    hot_wall_factor=1+.25*thermal_index+.12*air_fraction
    rib_radius_mm=clamp(b.inlet_wall_mm*(.24+.16*thermal_index),2.0,8.0)
    rib_turns=clamp(.65+1.1*air_fraction+.35*thermal_index,.75,2.0)
    strake_radius_mm=clamp(rib_radius_mm*.75,1.8,5.0)
    manufacturable_feature_mm=max(2.0,b.minimum_ligament_mm)

    checks={
        'finite_positive_mass_flows':all(math.isfinite(v) and v>0 for v in (air_mdot,rocket_mdot,total_mdot)),
        'rocket_exit_below_mixer_throat':rocket_exit_area*1.5<=mixer_throat+1e-12,
        'nozzle_throat_contains_rocket_exit':rocket_exit_area*1.5<=nozzle_throat+1e-12,
        'positive_stage_areas':all(v>0 for v in (mixer_throat,mixer_exit,isolator_exit,combustor_exit,nozzle_throat,nozzle_exit)),
        'generated_features_above_screen':min(rib_radius_mm*2,strake_radius_mm*2)>=manufacturable_feature_mm,
        'ideal_mixing_energy_closed':abs(mixing['energy_residual_w'])<=max(1e-6,(air_mdot+rocket_mdot)*mixing['mixed_constant_properties']['cp_j_kg_k']*mixing['stagnation_temperature_k']['mixed_ideal']*1e-10),
        'ideal_mixing_mass_closed':abs(mixing['mass_residual_kg_s'])<1e-10,
        'minimum_choked_area_respected':mixer_throat>=minimum_throat and nozzle_throat>=minimum_throat,
        'ideal_reference_pressure_headroom':mixing['reference_pressure_headroom_fraction']>=0,
        'assumed_pressure_headroom':mixing['assumed_pressure_headroom_fraction']>=-1e-10,
        'positive_mixed_properties':all(math.isfinite(v) and v>0 for v in (mixing['stagnation_temperature_k']['mixed_ideal'],mixing['mixed_constant_properties']['cp_j_kg_k'],mixing['mixed_constant_properties']['r_j_kg_k'],mixing['critical_mass_flux_at_air_pressure_kg_m2_s'])),
        'station_mass_conservation':flow['maximum_relative_mass_residual']<1e-10,
        'conditional_stations_not_choked':flow['minimum_choking_margin_fraction']>=-1e-10,
    }
    if not all(checks.values()):
        raise ValueError('RBCC shared design state failed: '+', '.join(k for k,v in checks.items() if not v))
    return {
        'schema_version':3,'status':'conditional_ideal_mixing_and_flow_geometry_driver',
        'ideal_mixer':mixing,
        'conditional_airpath':flow,
        'mass_flow_kg_s':{'captured_air_ideal':air_mdot,'rocket_primary':rocket_mdot,'combined':total_mdot},
        'ratios':{'air_to_rocket_mass':entrainment_ratio,'air_mass_fraction':air_fraction,
                  'rocket_momentum_fraction':momentum_fraction,'thermal_index':thermal_index},
        'area_m2':areas,
        'geometry_fields':{'lobe_count':lobe_count,'peak_lobe_amplitude':lobe_amplitude,
                           'total_twist_rad':twist_rad,'hot_wall_factor':hot_wall_factor,
                           'rib_radius_mm':rib_radius_mm,'rib_turns':rib_turns,
                           'strake_radius_mm':strake_radius_mm,
                           'hydraulic_diameter_mm':hydraulic_diameter_mm},
        'checks':checks,
        'causality':[
            'Transition altitude, Mach and capture area set ideal captured-air mass flow.',
            'Rocket solution sets primary mass flow, exit area and ideal momentum thrust.',
            'Ideal complete-mixing mass and enthalpy balance sets mixed stagnation temperature.',
            'Air total-pressure reference, assumed mixed pressure recovery and mixed gas state set a minimum choked mixer area with a stated 5% margin.',
            'The compressible mass-flow equation solves subsonic Mach, static pressure, temperature and velocity at generated sections.',
            'Air/rocket mass and momentum fractions drive mixer contraction and lobe amplitude.',
            'Mixed stagnation-temperature index drives local wall and reinforcement fields.',
            'Manufacturing screen bounds rib and strake feature diameters.'
        ],
        'equations':['air mass flow = density * capture area * Mach * speed of sound',
                     'air mass fraction = air mass flow / (air + rocket mass flow)',
                     'mixed total enthalpy = air mass flow * air cp * air Tt + rocket mass flow * rocket cp * rocket Tt',
                     'ideal choked area = total mass flow / maximum isentropic mass flux at the assumed mixed pressure',
                     'mass flux = pt/sqrt(Tt) * sqrt(gamma/R) * M * [1+(gamma-1)M²/2]^[-(gamma+1)/(2(gamma-1))]'],
        'heuristics':['The mixer and common-nozzle throats exceed the conditional choked-area floor by 5%.',
                      'Mixed total-pressure recovery is a user-specified assumption, not a solved loss.',
                      'Mixer/isolator/combustor area relations beyond that floor are bounded reduced-order geometry rules.',
                      'Lobe, twist and reinforcement fields are physics-responsive geometry heuristics, not CFD or structural optimization.'],
        'unresolved':['Actual captured air and stream mixing efficiency','Mixed-stream momentum and total-pressure loss','Airbreathing fuel addition and heat release','Installed combined thrust','Unstart and mode transition','Conjugate heat transfer and structural loads']
    }
