"""One-dimensional mission screen using Vega's own ideal engine duty point.

OpenRocket motivates the vehicle-level quantities (mass, drag and trajectory),
but no OpenRocket source code is copied or executed here. This intentionally
omits stability, winds, launch rail, thrust transient and recovery dynamics.
"""
from math import exp, pi, sqrt, log

G0 = 9.80665
EARTH_RADIUS_M = 6371000.0
SEA_LEVEL_DENSITY_KG_M3 = 1.225
SEA_LEVEL_PRESSURE_PA = 101325.0
SCALE_HEIGHT_M = 8500.0


def screen_flight(brief, performance, suggest=True):
    """Integrate a vertical point-mass flight to apogee with RK4.

    Dry mass includes engine and vehicle. Propellant mass is mdot times burn.
    Constant thrust and mdot are assumed throughout the commanded burn.
    """
    mdot = performance['mass_flow_kg_s']
    burn = brief.burn_duration_s
    dry = brief.vehicle_dry_mass_kg + getattr(brief, 'payload_mass_kg', 0)
    propellant = mdot * burn
    initial_mass = dry + propellant
    area = pi * (brief.vehicle_diameter_m / 2) ** 2
    cd = brief.vehicle_drag_coefficient
    h0 = brief.launch_altitude_m
    exit_area = performance['exit_area_m2']
    momentum_thrust = performance['momentum_thrust_n']
    exit_pressure = performance['exit_pressure_pa']

    def local_thrust(altitude):
        ambient = SEA_LEVEL_PRESSURE_PA * exp(-altitude / SCALE_HEIGHT_M)
        return momentum_thrust + (exit_pressure - ambient) * exit_area

    def acceleration(t, h, v, running):
        mass = dry + mdot * max(0.0, burn - t)
        altitude = max(0.0, h0 + h)
        density = SEA_LEVEL_DENSITY_KG_M3 * exp(-altitude / SCALE_HEIGHT_M)
        drag = 0.5 * density * cd * area * v * abs(v)
        gravity = G0 * (EARTH_RADIUS_M / (EARTH_RADIUS_M + altitude)) ** 2
        net_acceleration = ((local_thrust(altitude) if running else 0.0) - drag) / mass - gravity
        if h <= 0 and v <= 0 and net_acceleration <= 0:
            net_acceleration = 0.0  # Remain supported at the launch point until thrust exceeds weight.
        return net_acceleration, 0.5 * density * v * v

    h = v = t = max_q = 0.0
    burnout_h = burnout_v = None
    dt = min(0.02, burn / 100)
    while t < min(900.0, burn + 890.0):
        powered = t < burn - 1e-10
        step = min(dt, burn - t) if powered else dt
        a1, q1 = acceleration(t, h, v, powered)
        a2, q2 = acceleration(t + step / 2, h + step * v / 2, v + step * a1 / 2, powered)
        a3, q3 = acceleration(t + step / 2, h + step * (v + step * a1 / 2) / 2, v + step * a2 / 2, powered)
        a4, q4 = acceleration(t + step, h + step * (v + step * a2 / 2), v + step * a3, powered)
        h_next = h + step * (v + 2 * (v + step * a1 / 2) + 2 * (v + step * a2 / 2) + (v + step * a3)) / 6
        v_next = v + step * (a1 + 2 * a2 + 2 * a3 + a4) / 6
        max_q = max(max_q, q1, q2, q3, q4)
        t += step
        if burnout_h is None and t >= burn - 1e-9:
            burnout_h, burnout_v = h_next, v_next
        if t > burn and v > 0 >= v_next:
            fraction = v / (v - v_next)
            t -= step * (1 - fraction)
            h = h + fraction * (h_next - h)
            v = 0.0
            break
        h, v = h_next, v_next
        if h <= 0 and v <= 0 and not powered:
            h = v = 0.0
            break
        if t > burn and h < 0:
            break

    apogee = max(h0, h0 + h)
    target = brief.target_apogee_m
    result = {
        'model': 'vertical one-dimensional point mass, fixed mdot and chamber state, altitude-varying nozzle pressure thrust, exponential atmosphere, RK4',
        'source': 'https://openrocket.info/documentation.html',
        'vehicle_dry_mass_kg_including_engine': dry,
        'payload_mass_kg': getattr(brief, 'payload_mass_kg', 0),
        'propellant_mass_kg': propellant,
        'launch_mass_kg': initial_mass,
        'reference_area_m2': area,
        'drag_coefficient_assumed': cd,
        'pad_thrust_n': local_thrust(h0),
        'vacuum_thrust_n': momentum_thrust + exit_pressure * exit_area,
        'pad_thrust_to_weight': local_thrust(h0) / (initial_mass * G0),
        'vacuum_ideal_delta_v_m_s': ((momentum_thrust + exit_pressure * exit_area) / mdot) * log(initial_mass / dry),
        'burnout_altitude_m': h0 + (burnout_h or 0.0),
        'burnout_speed_m_s': burnout_v or 0.0,
        'predicted_apogee_m': apogee,
        'time_to_apogee_s': t,
        'maximum_dynamic_pressure_pa': max_q,
        'target_apogee_m': target,
        'target_screen_pass': None if target == 0 else apogee >= target,
        'limitations': 'Illustrative flight screen only: no 6-DOF stability, wind, chamber-pressure transient, launch rail, nozzle separation or measured drag.'
    }
    if suggest and target > 0:
        def at_thrust(requested_thrust):
            factor = requested_thrust / performance['thrust_n']
            scaled = dict(performance)
            for key in ('thrust_n', 'momentum_thrust_n', 'pressure_thrust_n', 'exit_area_m2', 'throat_area_m2', 'mass_flow_kg_s'):
                scaled[key] = performance[key] * factor
            return screen_flight(brief, scaled, suggest=False)['predicted_apogee_m']
        lower, upper = 100.0, 10000.0
        if at_thrust(upper) < target:
            result['suggested_minimum_ideal_thrust_n'] = None
        else:
            for _ in range(20):
                middle = (lower + upper) / 2
                if at_thrust(middle) < target:
                    lower = middle
                else:
                    upper = middle
            result['suggested_minimum_ideal_thrust_n'] = round(upper, 1)
        result['thrust_suggestion_scope'] = 'Vehicle-only solve over 100–10,000 N at fixed nozzle state and dry mass. Re-run Vega to check engine pressure, thermal, structure and mesh at the suggested thrust.'
    return result
