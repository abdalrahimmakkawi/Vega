"""Independent arithmetic and assembly-consistency review of saved geometry.

Route screening is bounded to the supplied service routes. It does not replace
global solid interference detection, manufacturing fit, CFD or thermal analysis.
"""
import argparse
import json
from itertools import combinations, product
from math import log, pi, sin, sqrt
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from .demonstrator import ROOT
from .integration import sample_route, inside_stl, specification
from .artifacts import artifact_digest, materialized_stl
from .cooling_simulation import assembly_network


def route_conflicts(parts,step=.25):
    routes=[dict(id=p['id'],route_index=i,**r) for p in parts for i,r in enumerate(p.get('routes',[]))]
    samples=[np.asarray(sample_route(r['points'],step=step)) for r in routes]
    conflicts=[]
    for i,j in combinations(range(len(routes)),2):
        a,b=routes[i],routes[j]
        if a['id']==b['id']:continue
        distances,indices=cKDTree(samples[j]).query(samples[i]);k=int(np.argmin(distances))
        gap=float(distances[k]-a['outer']-b['outer'])
        if gap>=0:continue
        pa,pb=samples[i][k],samples[j][indices[k]]
        shared=any(np.linalg.norm(np.array(x)-y)<1e-6 for x in (a['points'][0],a['points'][-1]) for y in (b['points'][0],b['points'][-1]))
        conflicts.append(dict(parts=[a['id'],b['id']],route_indices=[a['route_index'],b['route_index']],
            kind='shared_terminal' if shared else 'route_crossing',sampled_surface_gap_mm=gap,
            centerline_points_mm=[pa.tolist(),pb.tolist()],status='nominal_envelope_overlap',
            scope='Negative sampled gap proves overlap of nominal swept outer envelopes; native wall witnesses checked separately. This is not an exact minimum clearance.'))
    return conflicts


def point_distances(points,route):
    path=np.asarray(route['points']);delta=np.diff(path,axis=0);length2=np.sum(delta**2,axis=1)
    vectors=np.asarray(points)[:,None,:]-path[:-1]
    t=np.clip(np.sum(vectors*delta,axis=2)/length2,0,1)
    return np.linalg.norm(vectors-t[:,:,None]*delta,axis=2).min(axis=1)


def require_route_clearance(parts):
    conflicts=route_conflicts(parts)
    if conflicts:
        pairs=[' / '.join(c['parts']) for c in conflicts]
        raise ValueError('Service-route interference must be resolved before rebuilding: '+'; '.join(pairs))


def native_witnesses(folder,report,parts,conflict):
    routes=[next(p for p in parts if p['id']==identity)['routes'][index]
            for identity,index in zip(conflict['parts'],conflict['route_indices'])]
    center=np.mean(conflict['centerline_points_mm'],axis=0)
    candidates=center+np.asarray(list(product(np.arange(-1.5,1.51,.3),repeat=3)))
    valid=np.ones(len(candidates),dtype=bool)
    for route in routes:
        distances=point_distances(candidates,route)
        valid&=(distances>route['bore']+.15)&(distances<route['outer']-.15)
    points=candidates[valid][:5]
    if not len(points):return dict(status='no_interior_witness_candidates',points_mm=[])
    valid=np.ones(len(points),dtype=bool);hashes={};blocked=[]
    for index,identity in enumerate(conflict['parts']):
        path=folder/(identity+'.stl');expected=report['components'][identity]['sha256']
        hashes[identity]=artifact_digest(path)
        if hashes[identity]!=expected:raise ValueError('Changed native collision source: '+identity)
        other_point=conflict['centerline_points_mm'][1-index]
        with materialized_stl(path) as work:
            valid&=inside_stl(work,points)
            if inside_stl(work,[other_point])[0]:
                blocked.append(dict(route=conflict['parts'][1-index],obstruction=identity,point_mm=other_point))
    return dict(status='confirmed_shared_material' if any(valid) else 'not_confirmed',
                points_mm=points[valid].tolist(),native_stl_sha256=hashes,foreign_material_at_route_centerline=blocked,
                method='Oblique ray parity at interior points in both full-resolution exported STLs')


def arithmetic_checks(design):
    s=design['synthesis'];r=s['reference'];selected=s['search']['selected']
    density=r['pressure_pa']/(287.05*r['inlet_temperature_k'])
    area=r['mass_flow_kg_s']/(density*r['intake_speed_m_s'])*1e6
    hot=r['inlet_temperature_k']-r['assumed_coolant_temperature_k']
    cold=r['cooled_temperature_k']-r['assumed_coolant_temperature_k']
    lmtd=(hot-cold)/log(hot/cold)
    duty=r['mass_flow_kg_s']*r['cp_j_kgk']*(hot-cold)
    power=r['mass_flow_kg_s']*r['cp_j_kgk']*r['cooled_temperature_k']*(r['compressor_pressure_ratio']**(2/7)-1)/r['assumed_compressor_efficiency']
    values=[('intake_area_mm2',area,s['equations'][0]['outputs']['intake_area_mm2']),
            ('intake_radius_mm',sqrt(area/pi+8**2),s['geometry']['intake_inner_radius_mm']),
            ('hypothetical_heat_duty_w',duty,s['equations'][1]['outputs']['heat_duty_w']),
            ('required_surface_mm2',duty/(r['assumed_U_w_m2k']*lmtd)*1e6,s['equations'][1]['outputs']['required_surface_mm2']),
            ('selected_surface_mm2',selected['tube_count']*pi*selected['tube_diameter_mm']*selected['length_mm'],selected['surface_area_mm2']),
            ('tube_gap_mm',2*selected['ring_radius_mm']*sin(pi/selected['tube_count'])-selected['tube_diameter_mm'],selected['tube_gap_mm']),
            ('reference_compressor_power_w',power,s['equations'][2]['outputs']['shaft_power_w'])]
    return [dict(quantity=k,recomputed=v,saved=saved,passed=bool(np.isclose(v,saved,rtol=1e-10,atol=1e-10))) for k,v,saved in values]


def audit(folder,verify_native=True):
    folder=Path(folder);report=json.loads((folder/'report.json').read_text());design=report['recipe']
    if 'bell_cooling' not in design:raise ValueError('This audit requires a saved bell-cooling assembly')
    source=ROOT/'data/prints'/report['base_run']/'integration-input.json'
    archived=json.loads(source.read_text())['parts']
    archived_ids={p['id'] for p in archived}
    # An earlier partial rebuild overwrote the legacy input with only two parts.
    # Label reconstruction explicitly and confirm any findings on actual STLs.
    reconstructed,_=specification()
    recovered=[p for p in reconstructed if p['id'] not in archived_ids]
    inherited=archived+recovered
    replacements=json.loads((folder/'routes-input.json').read_text())['parts']
    stages=json.loads((folder/'native-stages.json').read_text())
    if artifact_digest(folder/'routes-input.json')!=stages['integrate']['inputs']['routes-input.json']:
        raise ValueError('Changed native route input')
    replacement_ids={p['id'] for p in replacements}
    parts=[p for p in inherited if p['id'] not in replacement_ids]+replacements
    conflicts=route_conflicts(parts)
    for conflict in conflicts:
        if verify_native:conflict['native_evidence']=native_witnesses(folder,report,parts,conflict)
    bounds=np.asarray([report['assembly']['bounds_mm']]+[c['bounds_mm'] for c in report['components'].values()])
    extent=np.max(bounds[:,1],axis=0)-np.min(bounds[:,0],axis=0)
    network=assembly_network(design,design['bell_cooling'],report['cooling_network']['total_flow_ml_s'])
    network['assembly_applicability']='Assumes unobstructed independent pipes. Confirmed assembly interference invalidates treating this estimate as the assembled circuit pressure requirement.'
    saved_pressure=report['cooling_network']['required_pressure_difference_pa']
    arithmetic=arithmetic_checks(design)
    checks=[dict(id='reference_arithmetic',status='passed' if all(c['passed'] for c in arithmetic) else 'failed',
                 evidence='Independent recomputation of continuity, energy, LMTD, tube area/gap and reference compressor work.'),
        dict(id='service_route_interference',status='failed' if conflicts else 'screened',
             evidence=f'{len(conflicts)} nominal route overlaps; native witness evidence below. Other components are outside this route-pair screen.'),
        dict(id='assembly_envelope_scope',status='stale' if extent[2]>design['length_mm']+.5 else 'consistent',
             evidence=f"Saved CEM length {design['length_mm']:.1f} mm describes the original casing. Full current bounds: {extent[0]:.1f} × {extent[1]:.1f} × {extent[2]:.1f} mm."),
        dict(id='hydraulic_geometry_dependencies',status='corrected',
             evidence=f'Now uses saved branch/port bores, junctions and all four collector polylines. {saved_pressure:.2f} Pa saved → {network["required_pressure_difference_pa"]:.2f} Pa revised at the same assumed flow.'),
        dict(id='flow_model_applicability',status='limited',
             evidence=f'{len(network["developing_flow_edges"])} edges shorter than estimated entrance length. Bends, developing flow, leakage and thermal effects still omitted.'),
        dict(id='whole_assembly_synthesis',status='incomplete',
             evidence='Intake/bundle and core routing have bounded selection logic. Expanded machinery dimensions, placement, frames and service waypoints are fixed; there is no assembly-wide constraint solver or operating-point match.'),
        dict(id='functional_fluid_connectivity',status='unresolved',
             evidence='He/H2/LOX harness terminals are blind; material contact does not establish a fluid circuit. Precooler tubes and machinery are static representations.'),
        dict(id='legacy_input_provenance',status='incomplete' if recovered else 'available',
             evidence=f'{len(recovered)} inherited component inputs reconstructed from current specification because the saved legacy input contains only {len(archived)} components. Collision witnesses are checked against hash-verified native STLs.')]
    return dict(schema_version=1,run_id=folder.name,source_report_sha256=artifact_digest(folder/'report.json'),
        scope='Non-firing airflow/cooling demonstrator; arithmetic and targeted assembly audit',
        conclusion='Assembly review failed: routing conflicts and incomplete engineering dependencies' if conflicts else 'Targeted route screen clear; whole-assembly design remains unverified',
        whole_engine_operability_established=False,checks=checks,arithmetic=arithmetic,
        assembly_bounds_mm=[np.min(bounds[:,0],axis=0).tolist(),np.max(bounds[:,1],axis=0).tolist()],assembly_size_mm=extent.tolist(),
        route_conflicts=conflicts,route_screen=dict(route_count=sum(len(p.get('routes',[])) for p in parts),sample_spacing_mm=.25,
            coverage='Pairwise external service-route envelopes only. Excludes ring/branch jackets, fittings, supports, casing and other solids; no global collision-free claim.'),
        cooling_network=network,previous_cooling_pressure_pa=saved_pressure,
        source_inputs={str(source.relative_to(ROOT)):artifact_digest(source),'routes-input.json':artifact_digest(folder/'routes-input.json'),
                       'vega/integration.py':artifact_digest(ROOT/'vega/integration.py')},
        reconstructed_legacy_component_ids=[p['id'] for p in recovered if p['id'] not in replacement_ids],
        logic=[dict(system='Intake and precooler',method='Continuity + hypothetical heat-transfer-area constraint + nine-candidate search',coupling='Drives intake radius, tube count and length'),
               dict(system='Original cooling routes',method='Twelve candidates screened against four sampled air corridors',coupling='Selected centerlines drive geometry and resistance'),
               dict(system='Bell cooling',method='Follows saved bell profile with prescribed offsets and six branches',coupling='Network now reads all saved bores, lengths and collector junctions'),
               dict(system='Expanded machinery and frame',method='Fixed profiles, coordinates, beam anchors and contact probes',coupling='No sizing feedback from flow, heat load, power or whole-assembly fit')],
        sources=['https://www.grc.nasa.gov/www/k-12/airplane/compth.html',
                 'https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/fbu_vm/Hlp_VMFL005.html'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run');args=parser.parse_args()
    if len(args.run)!=32 or any(c not in '0123456789abcdef' for c in args.run):raise ValueError('Invalid run ID')
    result=audit(ROOT/'data/prints'/args.run)
    target=ROOT/'data/design-audits';target.mkdir(exist_ok=True)
    (target/(args.run+'.json')).write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('conclusion','assembly_size_mm','route_conflicts')},indent=2))
    print('Revised pressure Pa:',result['cooling_network']['required_pressure_difference_pa'])


if __name__=='__main__':main()
