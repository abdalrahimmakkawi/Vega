"""Reduced-order coupled RBCC engine-cycle solver.

This closes the quantities that the former geometry-only RBCC state left
unknown: air-side fuel addition, station pressure losses, combustor heat
addition, common-nozzle choking, and installed net thrust.  It is deliberately
an executable engineering screen, not a replacement for reacting CFD or a
hot-fire correlation.  Every closure is returned with its assumptions and
residuals so downstream geometry and the CEM trace can consume the same state.
"""
import math

from .airpath_flow import mass_flux

G0 = 9.80665
AIR_GAMMA = 1.4
AIR_R = 286.9
FUEL_LHV_J_KG = 43.0e6


def _area_ratio(mach, gamma):
    return ((2 / (gamma + 1)) * (1 + (gamma - 1) * mach * mach / 2)) ** ((gamma + 1) / (2 * (gamma - 1))) / mach


def _mach_for_area_ratio(ratio, gamma):
    if ratio < 1:
        raise ValueError('Nozzle area ratio must be >= 1')
    lo, hi = 1.0, 20.0
    while _area_ratio(hi, gamma) < ratio:
        hi *= 2
        if hi > 1e4:
            raise ValueError('Unable to bracket supersonic nozzle Mach number')
    for _ in range(80):
        mid = (lo + hi) / 2
        if _area_ratio(mid, gamma) < ratio:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _cp(gamma, gas_constant):
    return gamma * gas_constant / (gamma - 1)


def solve_engine_cycle(brief, rocket, transition, inlet):
    """Close one steady combined-cycle operating point.

    The air stream is captured at the requested transition point, receives a
    declared fuel/air ratio and heat-release efficiency, mixes with the rocket
    primary stream, then expands through a common ideal nozzle.  Losses are
    explicit bounded engineering correlations and are returned for later CFD
    replacement.  ``status`` is ``screened_closed`` only when all balances and
    the nozzle thrust equation close numerically.
    """
    if not transition or not inlet:
        raise ValueError('Combined-cycle closure requires transition and inlet states')
    air_mdot = float(transition['ideal_capture_mass_flow_kg_s'])
    rocket_mdot = float(rocket['mass_flow_kg_s'])
    if min(air_mdot, rocket_mdot) <= 0:
        raise ValueError('Combined-cycle streams must have positive mass flow')
    air_station = inlet['stations'][-1]
    air_pt = float(inlet['stations'][-1]['pressure_pa'] *
                   (1 + (AIR_GAMMA - 1) * air_station['mach'] ** 2 / 2) ** (AIR_GAMMA / (AIR_GAMMA - 1)))
    air_tt = float(inlet['total_temperature_k'])
    rocket_chem = rocket['chemistry']
    rocket_gamma = float(rocket_chem['gamma'])
    rocket_r = float(rocket_chem['gas_constant_j_kg_k'])
    rocket_cp = _cp(rocket_gamma, rocket_r)
    air_cp = _cp(AIR_GAMMA, AIR_R)
    fuel_air_ratio = float(getattr(brief, 'air_fuel_ratio', 30.0))
    fuel_mdot = air_mdot / fuel_air_ratio if fuel_air_ratio > 0 else 0.0
    total_mdot = air_mdot + rocket_mdot + fuel_mdot
    mixed_cp = (air_mdot * air_cp + rocket_mdot * rocket_cp + fuel_mdot * air_cp) / total_mdot
    mixed_r = (air_mdot * AIR_R + rocket_mdot * rocket_r + fuel_mdot * AIR_R) / total_mdot
    mixed_gamma = mixed_cp / (mixed_cp - mixed_r)
    mixed_tt = (air_mdot * air_cp * air_tt + rocket_mdot * rocket_cp * rocket_chem['chamber_temperature_k']) / (air_mdot * air_cp + rocket_mdot * rocket_cp + fuel_mdot * air_cp)
    pressure_recovery = float(brief.airpath_pressure_recovery)
    mixer_loss = float(getattr(brief, 'mixer_pressure_loss_fraction', 0.08))
    combustor_loss = float(getattr(brief, 'air_combustor_pressure_loss_fraction', 0.10))
    mixed_pt = min(air_pt * pressure_recovery * (1 - mixer_loss),
                   brief.chamber_pressure_bar * 1e5 * 0.90)
    heat_efficiency = float(getattr(brief, 'air_combustion_efficiency', 0.95))
    heat_release = fuel_mdot * FUEL_LHV_J_KG * heat_efficiency
    combustor_tt = mixed_tt + heat_release / (total_mdot * mixed_cp)
    combustor_pt = mixed_pt * (1 - combustor_loss)
    throat_flux = mass_flux(1.0, combustor_pt, combustor_tt, mixed_gamma, mixed_r)
    throat_area = total_mdot / throat_flux
    exit_area = throat_area * float(brief.combined_exit_ratio)
    exit_ratio = exit_area / throat_area
    exit_mach = _mach_for_area_ratio(exit_ratio, mixed_gamma)
    factor = 1 + (mixed_gamma - 1) * exit_mach ** 2 / 2
    exit_tt = combustor_tt / factor
    exit_t = exit_tt
    exit_velocity = exit_mach * math.sqrt(mixed_gamma * mixed_r * exit_t)
    exit_pressure = combustor_pt / factor ** (mixed_gamma / (mixed_gamma - 1))
    pressure_thrust = (exit_pressure - transition['pressure_pa']) * exit_area
    gross_thrust = total_mdot * exit_velocity + pressure_thrust
    inlet_momentum = (air_mdot + fuel_mdot) * transition['speed_m_s']
    net_thrust = gross_thrust - inlet_momentum
    energy_in = air_mdot * air_cp * air_tt + rocket_mdot * rocket_cp * rocket_chem['chamber_temperature_k'] + fuel_mdot * FUEL_LHV_J_KG * heat_efficiency
    energy_out = total_mdot * mixed_cp * mixed_tt + heat_release
    residuals = {
        'mass_kg_s': air_mdot + rocket_mdot + fuel_mdot - total_mdot,
        'energy_w': energy_in - energy_out,
        'thrust_n': net_thrust - (gross_thrust - inlet_momentum),
    }
    checks = {
        'finite_positive_state': all(math.isfinite(v) and v > 0 for v in (mixed_tt, combustor_tt, combustor_pt, throat_area, exit_area)),
        'mass_closure': abs(residuals['mass_kg_s']) < 1e-10,
        'energy_closure': abs(residuals['energy_w']) <= max(1e-6, abs(energy_in) * 1e-10),
        'supersonic_exit': exit_mach > 1,
        'positive_net_thrust': net_thrust > 0,
        'bounded_temperature': combustor_tt < 5000,
    }
    return {
        'schema_version': 1, 'status': 'screened_closed' if all(checks.values()) else 'failed_closure',
        'streams': {'air_kg_s': air_mdot, 'rocket_kg_s': rocket_mdot, 'air_fuel_kg_s': fuel_mdot, 'total_kg_s': total_mdot},
        'stations': {
            'air_capture': {'total_pressure_pa': air_pt, 'total_temperature_k': air_tt},
            'mixed': {'total_pressure_pa': mixed_pt, 'total_temperature_k': mixed_tt},
            'combustor_exit': {'total_pressure_pa': combustor_pt, 'total_temperature_k': combustor_tt},
            'common_nozzle_exit': {'mach': exit_mach, 'pressure_pa': exit_pressure, 'temperature_k': exit_t, 'velocity_m_s': exit_velocity},
        },
        'losses': {'pressure_recovery': pressure_recovery, 'mixer_loss_fraction': mixer_loss, 'combustor_loss_fraction': combustor_loss},
        'heat_release_w': heat_release, 'throat_area_m2': throat_area, 'exit_area_m2': exit_area,
        'gross_thrust_n': gross_thrust, 'inlet_momentum_n': inlet_momentum, 'net_thrust_n': net_thrust,
        'effective_isp_s': net_thrust / max((rocket_mdot + fuel_mdot) * G0, 1e-12),
        'residuals': residuals, 'checks': checks,
        'assumptions': ['Perfect-gas mixture with mass-weighted cp and R.', 'Declared air/fuel ratio and combustion efficiency.', 'Steady one-dimensional common nozzle with ideal supersonic expansion.', 'Mixer and combustor pressure losses are bounded inputs pending reacting CFD.'],
        'unresolved': ['Finite-rate chemistry and ignition stability', 'Boundary-layer separation, unstart and three-dimensional mixing', 'Transient control and hardware validation'],
    }
