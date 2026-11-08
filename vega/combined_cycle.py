"""Architecture roadmap and conditional mission budget, not a cycle solver."""
import math
from .inlet import inlet_reference
from .rbcc_knowledge import evaluate_reference_cases
from .engine_cycle import solve_engine_cycle

G0 = 9.80665
MU = 3.986004418e14
EARTH_RADIUS_M = 6371000.0
SOURCES = [
    'https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/earth-atmosphere-equation-metric/',
    'https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/',
    'https://www.grc.nasa.gov/WWW/BGH/hmission.html',
    'https://ntrs.nasa.gov/citations/20110012002',
]
FAMILIES = {
    'rocket_only': ('Rocket-only baseline', ['Rocket ascent', 'Orbital insertion'],
                    ['rocket_core', 'vehicle', 'trajectory']),
    'rbcc': ('Rocket-based combined cycle',
             ['Rocket / ejector acceleration', 'Ramjet / scramjet', 'Rocket ascent', 'Orbital insertion'],
             ['inlet', 'ejector', 'air_combustor', 'mode_control', 'rocket_core', 'vehicle', 'trajectory']),
    'tbcc': ('Turbine-based combined cycle + separate orbital rocket',
             ['Turbine acceleration', 'Ramjet / scramjet', 'Separate rocket ascent', 'Orbital insertion'],
             ['inlet', 'turbine', 'air_combustor', 'mode_control', 'rocket_core', 'vehicle', 'trajectory']),
    'ejector_rocket': ('Ejector-augmented rocket',
                      ['Rocket with air entrainment', 'Rocket ascent', 'Orbital insertion'],
                      ['inlet', 'ejector', 'mode_control', 'rocket_core', 'vehicle', 'trajectory']),
}
SYSTEMS = {
    'inlet': ('Air inlet', 'A cold normal-shock diffuser reference has station continuity and a Vega Geometry loft. Installed compression, spillage, unstart and high-speed operation remain unsolved.'),
    'ejector': ('Ejector / mixer', 'Entrainment, mixing losses and starting behavior are not modeled.'),
    'turbine': ('Turbine flow path', 'Compressor and turbine maps, shaft balance and cooling are not modeled.'),
    'air_combustor': ('Airbreathing combustor', 'Net thrust remains unknown until fuel flow, combustion and nozzle states close.'),
    'mode_control': ('Mode transition', 'Requested handover conditions are not demonstrated transitions.'),
    'rocket_core': ('Pressure-fed rocket core', 'Existing nozzle, propellant network and native geometry screens; unvalidated hardware.'),
    'vehicle': ('Airframe and thermal protection', 'Structural mass, lift, drag, packaging, reentry and thermal protection remain unsolved.'),
    'trajectory': ('Ascent and orbit', 'Conditional ideal speed budget only. Coupled ascent and orbital insertion remain unsolved.'),
}

def atmosphere(altitude_m):
    """NASA Glenn educational curve fit, limited here to 0–32 km."""
    if not math.isfinite(altitude_m) or not 0 <= altitude_m <= 32000:
        raise ValueError('Atmosphere screen supports 0–32,000 m only')
    if altitude_m < 11000:
        tc = 15.04 - .00649 * altitude_m
        pkpa = 101.29 * ((tc + 273.1) / 288.08) ** 5.256
    elif altitude_m < 25000:
        tc = -56.46
        pkpa = 22.65 * math.exp(1.73 - .000157 * altitude_m)
    else:
        tc = -131.21 + .00299 * altitude_m
        pkpa = 2.488 * ((tc + 273.1) / 216.6) ** -11.388
    tk = tc + 273.1
    return {'temperature_k': tk, 'pressure_pa': pkpa * 1000,
            'density_kg_m3': pkpa / (.2869 * tk),
            'speed_of_sound_m_s': math.sqrt(1.4 * 286.9 * tk)}

def screen_combined_cycle(b, rocket):
    family_name, mode_names, system_ids = FAMILIES[b.propulsion_family]
    combined = b.propulsion_family != 'rocket_only'
    transition = None
    transition_speed = 0.0
    if combined:
        air = atmosphere(b.transition_altitude_m)
        transition_speed = b.transition_mach * air['speed_of_sound_m_s']
        transition = {
            **air, 'mach': b.transition_mach, 'altitude_m': b.transition_altitude_m,
            'speed_m_s': transition_speed,
            'ideal_capture_mass_flow_kg_s': air['density_kg_m3'] * b.inlet_capture_area_m2 * transition_speed,
            'dynamic_pressure_pa': .5 * air['density_kg_m3'] * transition_speed ** 2,
            'capture_area_m2': b.inlet_capture_area_m2,
            'net_thrust_n': None, 'status': 'requested_not_demonstrated',
        }
    # Same propellant inventory as the engine/tank model. Optimistically reserve
    # ALL of it for handover; atmospheric-mode fuel consumption is unresolved.
    propellant = rocket['mass_flow_kg_s'] * b.burn_duration_s
    final_mass = b.vehicle_dry_mass_kg + b.payload_mass_kg
    initial_mass = final_mass + propellant
    vacuum_thrust = rocket['momentum_thrust_n'] + rocket['exit_pressure_pa'] * rocket['exit_area_m2']
    exhaust_velocity = vacuum_thrust / rocket['mass_flow_kg_s']
    available_dv = exhaust_velocity * math.log1p(propellant / final_mass)
    circular_speed = math.sqrt(MU / (EARTH_RADIUS_M + b.orbit_altitude_m))
    # Speed comparison only. This is NOT an orbital transfer solution: climbing,
    # gravity/drag/steering losses and Earth rotation are omitted.
    speed_gap = max(0.0, circular_speed - transition_speed)+b.mission_delta_v_allowance_m_s
    margin = available_dv - speed_gap
    budget_pass = margin >= 0
    inlet = inlet_reference(b,transition)
    engine_cycle = None
    if combined and transition and inlet and inlet.get('status') == 'ideal_reference_only':
        engine_cycle = solve_engine_cycle(b, rocket, transition, inlet)
    systems = [
        {'id': sid, 'name': SYSTEMS[sid][0], 'detail': SYSTEMS[sid][1],
         'status': 'screened_unvalidated' if sid == 'rocket_core' else inlet['status'] if sid == 'inlet' else 'unmodeled',
         'depends_on': (['rocket_core', 'vehicle'] if sid == 'trajectory' else
                        ['inlet'] if sid in ('ejector', 'turbine') else
                        ['inlet', 'mode_control'] if sid == 'air_combustor' else [])}
        for sid in system_ids
    ]
    warnings = [
        'Airframe geometry and airbreathing performance are not generated by the current engine solver.',
        'Transition is assumed, with all rocket propellant reserved for it; atmospheric fuel and hardware mass are not closed.',
    ] if combined else []
    if not budget_pass:
        warnings.append('The rocket propellant budget fails even the simplified remaining-speed comparison.')
    return {
        'schema_version': 2, 'family': b.propulsion_family, 'family_name': family_name,
        'architecture': b.vehicle_architecture, 'status': 'incomplete' if budget_pass else 'failed',
        'screen_pass': None if budget_pass else False,
        'checks': {'ideal_velocity_budget': budget_pass, 'coupled_trajectory': None,
                   'vehicle_mass_and_packaging': None, 'aerothermal_constraints': None,
                   **({'airbreathing_performance': None, 'mode_transition': None} if combined else {})},
        'transition': transition, 'inlet_reference': inlet, 'engine_cycle': engine_cycle, 'systems': systems,
        'rbcc_reference': (evaluate_reference_cases(b,air) if b.propulsion_family in ('rbcc','ejector_rocket') else None),
        'mode_schedule': [{'mode': name, 'status': 'planned'} for name in mode_names],
        'vehicle': {
            'dry_mass_excluding_payload_kg': b.vehicle_dry_mass_kg,
            'payload_mass_kg': b.payload_mass_kg, 'rocket_propellant_mass_kg': propellant,
            'budget_initial_mass_kg': initial_mass, 'budget_final_mass_kg': final_mass,
            'orbit_altitude_m': b.orbit_altitude_m, 'circular_speed_m_s': circular_speed,
            'reference_area_m2': math.pi * (b.vehicle_diameter_m / 2) ** 2,
        },
        'budget': {
            'vacuum_effective_exhaust_velocity_m_s': exhaust_velocity,
            'available_ideal_delta_v_m_s': available_dv,
            'remaining_speed_gap_m_s': speed_gap, 'velocity_margin_m_s': margin,
            'assumed_delta_v_allowance_m_s':b.mission_delta_v_allowance_m_s,
            'ideal_propellant_for_speed_gap_kg': final_mass * math.expm1(speed_gap / exhaust_velocity),
            'scope': 'Conditional speed comparison with a user-declared delta-v allowance; ascent loss mechanisms, altitude transfer and Earth rotation are not solved. A positive margin is not mission feasibility.',
        },
        'equations': ['Propellant mass = engine mass flow × burn duration',
                      'Ideal delta-v = (vacuum thrust / mass flow) × ln(initial mass / final mass)',
                      'Circular speed = sqrt(Earth mu / orbital radius)',
                      'Ideal inlet capture = density × area × Mach × speed of sound'],
        'warnings': warnings, 'sources': SOURCES,
        'model': 'Coupled reduced-order combined-cycle closure with declared loss and combustion assumptions; reacting CFD and transient validation remain required.' if engine_cycle else 'Architecture roadmap and conditional mission budget.',
    }
