"""Conditional one-dimensional compressible-flow screen for the RBCC airpath.

The pressure recovery is a design assumption, not a predicted mixing loss.
No combustion, wall friction, stream momentum closure, or installed thrust is
inferred from these station states.
"""
import math

MASS_FLOW_SOURCE = 'https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/mass-flow-rate-equations/'
ISENTROPIC_SOURCE = 'https://www.grc.nasa.gov/www/k-12/airplane/isentrop.html'
VISCOSITY_SOURCE = 'https://ntrs.nasa.gov/api/citations/19990046590/downloads/19990046590.pdf'


def mass_flux(mach, total_pressure_pa, total_temperature_k, gamma, gas_constant):
    if not all(math.isfinite(v) and v > 0 for v in
               (mach, total_pressure_pa, total_temperature_k, gas_constant)) or gamma <= 1:
        raise ValueError('Positive finite perfect-gas flow inputs are required')
    factor = 1 + (gamma - 1) * mach * mach / 2
    return (total_pressure_pa / math.sqrt(total_temperature_k) *
            math.sqrt(gamma / gas_constant) * mach *
            factor ** (-(gamma + 1) / (2 * (gamma - 1))))


def air_viscosity_pa_s(temperature_k):
    """NASA Sutherland reference: 1.796e-5 Pa s at 293 K, S=111 K."""
    if not math.isfinite(temperature_k) or temperature_k <= 0:
        raise ValueError('Positive finite air temperature required')
    return 1.796e-5 * (temperature_k / 293) ** 1.5 * (293 + 111) / (temperature_k + 111)


def subsonic_station(name, area_m2, mass_flow_kg_s, total_pressure_pa,
                     total_temperature_k, gamma, gas_constant):
    critical = mass_flux(1, total_pressure_pa, total_temperature_k, gamma, gas_constant)
    requested = mass_flow_kg_s / area_m2
    if requested > critical * (1 + 1e-10):
        raise ValueError(f'{name} is choked under the assumed pressure recovery')
    lo, hi = 0.0, 1.0
    for _ in range(65):
        mid = (lo + hi) / 2
        if mass_flux(mid, total_pressure_pa, total_temperature_k, gamma, gas_constant) < requested:
            lo = mid
        else:
            hi = mid
    mach = (lo + hi) / 2
    factor = 1 + (gamma - 1) * mach * mach / 2
    temperature = total_temperature_k / factor
    pressure = total_pressure_pa / factor ** (gamma / (gamma - 1))
    density = pressure / (gas_constant * temperature)
    velocity = mach * math.sqrt(gamma * gas_constant * temperature)
    return {'name': name, 'area_m2': area_m2, 'mach': mach,
            'static_pressure_pa': pressure, 'static_temperature_k': temperature,
            'density_kg_m3': density, 'velocity_m_s': velocity,
            'dynamic_pressure_pa': density * velocity * velocity / 2,
            'mass_flow_kg_s': density * velocity * area_m2,
            'critical_mass_flux_kg_m2_s': critical,
            'choking_margin_fraction': 1 - requested / critical}


def conditional_airpath(areas, mixer, pressure_recovery):
    """Solve the subsonic isentropic branch at every generated duct section."""
    if not 0 < pressure_recovery <= 1:
        raise ValueError('Pressure recovery must be in (0, 1]')
    pressure = mixer['air_total_pressure_after_normal_shock_pa'] * pressure_recovery
    props = mixer['mixed_constant_properties']
    mass_flow = mixer['mass_flow_kg_s']['mixed']
    temperature = mixer['stagnation_temperature_k']['mixed_ideal']
    names = ('mixer_throat', 'mixer_exit', 'isolator_exit', 'combustor_exit',
             'common_nozzle_throat', 'common_nozzle_exit')
    stations = [subsonic_station(name, areas[name], mass_flow, pressure,
                temperature, props['gamma'], props['r_j_kg_k']) for name in names]
    return {'status': 'conditional_perfect_gas_subsonic_screen',
            'assumed_mixed_total_pressure_recovery': pressure_recovery,
            'assumed_mixed_total_pressure_pa': pressure,
            'mixed_total_temperature_k': temperature,
            'stations': stations,
            'maximum_relative_mass_residual': max(abs(s['mass_flow_kg_s'] - mass_flow) / mass_flow for s in stations),
            'minimum_choking_margin_fraction': min(s['choking_margin_fraction'] for s in stations),
            'sources': [MASS_FLOW_SOURCE, ISENTROPIC_SOURCE],
            'limits': 'Conditional isentropic subsonic branch at assumed mixed total pressure; pressure loss is an input, not a prediction. No combustion, heat transfer, momentum closure, supersonic nozzle branch, or installed thrust.'}
