"""Specialized non-firing airflow CEM. SI physics, millimetre geometry.

The channel network is a screening model, not CFD: collectors are equipressure,
and curved passages are replaced by straight circular pipes of equal length.
"""
from math import pi, isfinite
from vega_geometry import centerline_length, fingerprint


def channel_network(routes, total_flow_ml_s):
    if type(total_flow_ml_s) not in (float, int) or not isfinite(total_flow_ml_s) or not 5 <= total_flow_ml_s <= 60:
        raise ValueError('Cooling inspection airflow must be between 5 and 60 mL/s')
    if not routes:
        raise ValueError('At least one channel is required')
    rho, mu, cp = 1.2, 1.8e-5, 1005.
    branches=[]
    for route in routes:
        length=centerline_length(route['points'])/1000
        radius=route['bore_radius_mm']/1000
        if not isfinite(radius) or radius<=0:raise ValueError('Invalid channel radius')
        resistance=8*mu*length/(pi*radius**4)
        branches.append(dict(id=route['id'],length_mm=length*1000,
            diameter_mm=radius*2000,resistance_pa_s_m3=resistance))
    flow=total_flow_ml_s*1e-6
    resistance=1/sum(1/b['resistance_pa_s_m3'] for b in branches)
    drop=flow*resistance
    for b in branches:
        q=drop/b['resistance_pa_s_m3']; diameter=b['diameter_mm']/1000
        velocity=q/(pi*diameter**2/4); re=rho*velocity*diameter/mu
        b.update(flow_ml_s=q*1e6,velocity_m_s=velocity,reynolds=re,
            pressure_drop_pa=drop,entrance_length_mm=.05*re*b['diameter_mm'],
            laminar_screen_passed=re<2300)
    return dict(total_flow_ml_s=total_flow_ml_s,branches=branches,
        branch_only_pressure_drop_pa=drop,equivalent_resistance_pa_s_m3=resistance,
        mass_residual_kg_s=rho*(sum(b['flow_ml_s'] for b in branches)*1e-6-flow),
        heat_capacity_rate_w_k=rho*flow*cp,
        assumptions=dict(density_kg_m3=rho,dynamic_viscosity_pa_s=mu,cp_j_kgk=cp,
            fluid='room-temperature air',collector_model='equipressure'),
        equations=['R = 8*mu*L/(pi*r^4)', '1/R_eq = sum(1/R_i)',
                   'delta_p = Q_total*R_eq; Q_i = delta_p/R_i', 'Re = rho*v*D/mu'],
        scope='Fully developed straight-pipe equivalent only; entrance, bends, port/collector losses, roughness and split-seam leakage omitted. Heat-capacity rate is not achieved cooling duty.')


def evaluate(synthesis, cooling, nozzle_geometry, cooling_flow_ml_s=40.,voxel_mm=.2):
    network=channel_network(cooling['routes'],cooling_flow_ml_s)
    selected=synthesis['search']['selected']; thermal=synthesis['equations'][1]['outputs']
    checks=[
        dict(id='surface_screen',status='passed' if selected['surface_area_mm2']>=thermal['required_surface_mm2'] else 'failed',
             evidence='synthesis.search.selected.surface_area_mm2',scope='Hypothetical exchanger sizing only; printed tubes are solid'),
        dict(id='tube_clearance',status='passed' if selected['tube_gap_mm']>=1.6 else 'failed',evidence='synthesis.search.selected.tube_gap_mm'),
        dict(id='channel_junctions',status='passed' if cooling['network']['maximum_junction_gap_mm']<=.05 else 'failed',evidence='cooling.network.maximum_junction_gap_mm'),
        dict(id='network_mass_balance',status='passed' if abs(network['mass_residual_kg_s'])<1e-12 else 'failed',evidence='cem.channel_network.mass_residual_kg_s'),
        dict(id='laminar_regime',status='passed' if all(b['laminar_screen_passed'] for b in network['branches']) else 'failed',evidence='cem.channel_network.branches.reynolds'),
        dict(id='fully_developed_flow',status='passed' if all(b['entrance_length_mm']<b['length_mm'] for b in network['branches']) else 'unresolved',evidence='cem.channel_network.branches.entrance_length_mm',scope='Entrance effects still omitted even if estimated entrance length fits'),
        dict(id='mesh_to_voxel_conversion',status='pending',evidence='native.geometry_pipeline'),
        dict(id='boolean_operations',status='pending',evidence='native.boolean_reference_samples and native.boolean_operations'),
        dict(id='export_integrity',status='pending',evidence='report.assembly and report.parts'),
        dict(id='native_channel_clearance',status='pending',evidence='native.cooling_clearance_samples'),
        dict(id='physical_flow_validation',status='unresolved',evidence='Measured flow, pressure loss and leakage required'),
        dict(id='thermal_validation',status='unresolved',evidence='Measured heat transfer and material properties required')]
    result=dict(schema_version=1,specialization='non_firing_airflow_cooling_demonstrator',
        status='screened_pending_geometry',
        requirements=dict(length_mm=120,maximum_diameter_mm=60,wall_mm=2.4,
            voxel_mm=voxel_mm,minimum_tube_gap_mm=1.6,nominal_channel_diameter_mm=cooling['network']['nominal_bore_diameter_mm'],
            reference_airflow_g_s=synthesis['reference']['mass_flow_kg_s']*1000,
            cooling_inspection_flow_ml_s=cooling_flow_ml_s,operation='Unsealed room-temperature air inspection'),
        stages=[
            dict(id='requirements',depends_on=[],method='Bounded dimensional and airflow inputs'),
            dict(id='intake_and_bundle',depends_on=['requirements'],method='Continuity + hypothetical LMTD area screen + nine-candidate search'),
            dict(id='channels',depends_on=['intake_and_bundle'],method='Twelve-route search + junction proximity checks'),
            dict(id='hydraulics',depends_on=['channels'],method='Parallel laminar resistance network from actual route lengths'),
            dict(id='triangle_mesh',depends_on=['intake_and_bundle','channels'],method='Closed, wound triangular shells from sampled sections'),
            dict(id='voxel_geometry',depends_on=['triangle_mesh'],method='PicoGK mesh voxelization + implicit TPMS + lattice + Boolean passage cuts'),
            dict(id='acceptance',depends_on=['voxel_geometry','hydraulics'],method='Clearance samples + closed connected export checks')],
        channel_network=network,checks=checks,
        geometry_drivers=dict(intake_radius_mm=synthesis['geometry']['intake_inner_radius_mm'],
            tube_count=selected['tube_count'],tube_length_mm=selected['length_mm'],
            outlet_area_ratio=nozzle_geometry['expansion_ratio'],
            outlet_basis='Fixed inspection contour; not sized for thrust'),
        excluded_capabilities=['combustion','thrust prediction','compressor operation','flight transitions'],
        physical_validation_passed=False,
        sources=['https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/fbu_vm/Hlp_VMFL005.html'])
    result['analysis_sha256']=fingerprint(result)
    return result


def acceptance(cem,native,assembly,parts,input_mesh):
    from copy import deepcopy
    result=deepcopy(cem)
    evidence=dict(mesh_to_voxel_conversion=native.get('geometry_pipeline')=='triangle_mesh_to_voxels_then_implicit_booleans'
        and native.get('input_triangle_count')==input_mesh['triangles'] and input_mesh['passed'],
        boolean_operations=native.get('boolean_reference_samples')==15 and
            all(native.get('boolean_operations',{}).get(op,0)>0 for op in ('Add','Subtract','Intersect')),
        export_integrity=assembly['passed'] and len(parts)==2 and all(p['passed'] for p in parts.values()),
        native_channel_clearance=native.get('cooling_clearance_samples',0)>0)
    for check in result['checks']:
        if check['id'] in evidence:check['status']='passed' if evidence[check['id']] else 'failed'
    if any(c['status']=='failed' for c in result['checks']):raise ValueError('CEM acceptance gate failed')
    result['status']='geometry_checked_physical_validation_pending'
    result['acceptance_sha256']=fingerprint(result)
    return result
