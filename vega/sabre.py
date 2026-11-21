"""Bounded geometry synthesis for a SABRE-inspired, non-firing study model.

The low-speed reference is an assumed sizing case, not a solved SABRE cycle.
Search selects geometry by surface demand, tube clearance and material proxy.
"""
from math import ceil, exp, pi, log, sin, sqrt, isfinite

ARCHITECTURE = 'sabre_inspired_precooled_combined_cycle'
SOURCES = [
    'https://www.gov.uk/government/publications/synergetic-air-breathing-rocket-engine-sabre-programme-evaluation-report-2022/synergetic-air-breathing-rocket-engine-sabre-programme-evaluation-report-2022',
    'https://www.grc.nasa.gov/www/k-12/airplane/compth.html',
    'https://www.grc.nasa.gov/www/k-12/VirtualAero/BottleRocket/airplane/mflchk508.html',
]


def bundle_screen(reference, bundle, casing_radius_mm):
    """Straight tube midspan, after the centrebody tapers to its 2 mm stem."""
    count = bundle['tube_count']
    diameter = bundle['tube_diameter_mm']
    ring = bundle['ring_radius_mm']
    stem = 2.
    density = reference['pressure_pa'] / (287.05 * reference['inlet_temperature_k'])
    flow = reference['mass_flow_kg_s']
    speed_limit = reference['intake_speed_m_s']
    open_area = pi * (casing_radius_mm**2 - stem**2 - count * (diameter / 2)**2)
    required_area = 1e6 * flow / (density * speed_limit)
    bulk_speed = flow / (density * open_area * 1e-6) if open_area > 0 else None
    heat_capacity_rate = flow * reference['cp_j_kgk']
    hot = reference['inlet_temperature_k']
    sink = reference['assumed_coolant_temperature_k']
    ntu = reference['assumed_U_w_m2k'] * bundle['surface_area_mm2'] * 1e-6 / heat_capacity_rate
    return dict(open_area_mm2=open_area, required_area_mm2=required_area,
                midspan_velocity_m_s=bulk_speed, ntu=ntu,
                isothermal_sink_outlet_k=sink + (hot-sink)*exp(-ntu),
                flow_area_passed=open_area >= required_area and
                    ring + diameter/2 <= casing_radius_mm and ring - diameter/2 >= stem,
                scope='Uniform axial flow at tube midspan. End rings, supports and local losses require separate checks.')


BUNDLE_CASING_RADIUS_MM = 23.


def synthesize(mass_flow_kg_s=.004):
    if type(mass_flow_kg_s) not in (float, int) or not isfinite(mass_flow_kg_s) or not .002 <= mass_flow_kg_s <= .006:
        raise ValueError('Reference mass flow must be between 0.002 and 0.006 kg/s')
    cp, gamma, gas_r = 1005., 1.4, 287.05
    inlet_k, cooled_k, sink_k = 330., 305., 293.
    pressure_pa, efficiency, pressure_ratio = 101325., .78, 1.05
    assumed_u = 1000.  # Assumed overall heat-transfer coefficient, not measured.
    hot_delta, cold_delta = inlet_k-sink_k, cooled_k-sink_k
    lmtd = (hot_delta-cold_delta)/log(hot_delta/cold_delta)
    duty = mass_flow_kg_s*cp*(inlet_k-cooled_k)
    area_required = duty/(assumed_u*lmtd)*1e6
    density = pressure_pa/(gas_r*inlet_k)
    intake_speed = 3.
    intake_area = mass_flow_kg_s/(density*intake_speed)*1e6
    # The fixed 8 mm centrebody blocks the reference inlet section.
    intake_radius = sqrt(intake_area/pi+8**2)
    if intake_radius > 25:
        raise ValueError('The reference flow exceeds the 60 mm print envelope')

    candidates = []
    reference = dict(mass_flow_kg_s=mass_flow_kg_s, pressure_pa=pressure_pa,
                     inlet_temperature_k=inlet_k, intake_speed_m_s=intake_speed,
                     assumed_coolant_temperature_k=sink_k, assumed_U_w_m2k=assumed_u, cp_j_kgk=cp)
    for count in (20, 24, 28):
        diameter, ring_radius = 2.4, 18.
        required_length = area_required / (count*pi*diameter)
        fitted_length = max(18., ceil(required_length*5)/5)
        lengths = {18., 22., 26.}
        if fitted_length <= 26.:
            lengths.add(fitted_length)
        for length in sorted(lengths):
            area = count*pi*diameter*length
            clearance = 2*ring_radius*sin(pi/count)-diameter
            volume = count*pi*(diameter/2)**2*length
            screen = bundle_screen(reference, dict(tube_count=count, tube_diameter_mm=diameter,
                ring_radius_mm=ring_radius, surface_area_mm2=area), BUNDLE_CASING_RADIUS_MM)
            passed = area >= area_required and clearance >= 1.6 and screen['flow_area_passed']
            candidates.append(dict(id=f't{count}-l{length:g}', tube_count=count,
                length_mm=length, tube_diameter_mm=diameter, ring_radius_mm=ring_radius,
                surface_area_mm2=area, tube_gap_mm=clearance, material_proxy_mm3=volume,
                feasible=passed, score=volume if passed else None, bundle_screen=screen,
                rejection=None if passed else ('insufficient exchange area' if area<area_required else
                    'tube gap below 1.6 mm' if clearance<1.6 else 'insufficient midspan flow area or radial fit')))
    feasible = [c for c in candidates if c['feasible']]
    if not feasible:
        raise ValueError('No printable precooler candidate meets the assumed reference duty')
    chosen = min(feasible, key=lambda c: (c['score'], c['id']))
    compressor_out = cooled_k*(1+(pressure_ratio**((gamma-1)/gamma)-1)/efficiency)
    compressor_power = mass_flow_kg_s*cp*(compressor_out-cooled_k)
    baseline = candidates[-1]
    return dict(architecture=ARCHITECTURE,
        reference=dict(mass_flow_kg_s=mass_flow_kg_s, inlet_temperature_k=inlet_k,
            cooled_temperature_k=cooled_k, assumed_coolant_temperature_k=sink_k,
            pressure_pa=pressure_pa, assumed_U_w_m2k=assumed_u, cp_j_kgk=cp,
            intake_speed_m_s=intake_speed, compressor_pressure_ratio=pressure_ratio,
            assumed_compressor_efficiency=efficiency),
        equations=[
            dict(name='Intake continuity', equation='A = mass_flow / (rho * velocity); R = sqrt(A/pi + hub_radius^2)',
                 outputs=dict(intake_area_mm2=intake_area, intake_inner_radius_mm=intake_radius)),
            dict(name='Precooler energy and surface screen', equation='Q = mass_flow*cp*(Tin-Tout); A = Q/(U*LMTD)',
                 outputs=dict(heat_duty_w=duty, lmtd_k=lmtd, required_surface_mm2=area_required)),
            dict(name='Compressor reference work', equation='Tout = Tin*(1+(PR^((gamma-1)/gamma)-1)/eta); P = mass_flow*cp*(Tout-Tin)',
                 outputs=dict(outlet_temperature_k=compressor_out, shaft_power_w=compressor_power)),
            dict(name='Printable tube representation', equation='A = N*pi*d*L; gap = 2*r*sin(pi/N)-d; V = N*pi*d^2*L/4',
                 outputs=dict(surface_mm2=chosen['surface_area_mm2'], gap_mm=chosen['tube_gap_mm']))],
        search=dict(objective='Minimum tube material meeting thermal area, spacing, radial fit and midspan flow area',
            evaluated=len(candidates), feasible=len(feasible), selected=chosen, candidates=candidates,
            baseline=baseline['id'], material_proxy_reduction_percent=100*(1-chosen['score']/baseline['material_proxy_mm3'])),
        geometry=dict(intake_inner_radius_mm=intake_radius, precooler=chosen,
            compressor_vane_count=4, compressor_hub_radius_mm=8., nozzle_exit_radius_mm=9.),
        modes=[
            dict(name='Air-breathing', route='Intake → HX1 precooler → compressor → core chamber → nozzle', status='architecture represented'),
            dict(name='Rocket', route='Onboard oxidizer supply → core chamber → nozzle; atmospheric intake isolated', status='conceptual routing only'),
            dict(name='Return to air-breathing', route='Restart atmospheric intake and compressor after reentry', status='requested capability; restart and transition not solved')],
        unresolved=['Helium-loop heat/work closure, HX3/HX4 and turbine/pump matching',
            'Real-fluid hydrogen/oxygen properties, combustion, thrust and flight trajectory',
            'Compressor maps, inlet shocks, icing, pressure losses and transient mode switching',
            'Structural and thermal qualification, physical print and measured airflow'],
        scope='Low-speed assumed sizing case. Enlarged solid tube and static vane representations; no working heat exchanger or compressor.',
        sources=SOURCES)
