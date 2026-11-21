"""Geometry-derived cold-air resistance network; explicitly not 3-D CFD."""
from math import pi
import numpy as np


def length_mm(points):
    return float(np.linalg.norm(np.diff(np.asarray(points),axis=0),axis=1).sum())


def solve_network(edges,source,sink,total_flow_ml_s=10.):
    if type(total_flow_ml_s) not in (int,float) or not np.isfinite(total_flow_ml_s) or not 0<total_flow_ml_s<=30:
        raise ValueError('Cold-air screening flow must be above 0 and at most 30 mL/s')
    nodes=sorted({e[k] for e in edges for k in ('from','to')})
    if source not in nodes or sink not in nodes or source==sink:raise ValueError('Invalid terminals')
    if len({e['id'] for e in edges})!=len(edges):raise ValueError('Duplicate hydraulic edge IDs')
    seen={source}
    while True:
        expanded=seen|{e['to'] for e in edges if e['from'] in seen}|{e['from'] for e in edges if e['to'] in seen}
        if expanded==seen:break
        seen=expanded
    if seen!=set(nodes):raise ValueError('Disconnected hydraulic network')
    unknown=[n for n in nodes if n!=sink];index={n:i for i,n in enumerate(unknown)}
    matrix=np.zeros((len(unknown),len(unknown)));rhs=np.zeros(len(unknown));rhs[index[source]]=total_flow_ml_s*1e-6
    records=[];mu=1.8e-5;rho=1.2
    for edge in edges:
        length=float(edge['length_mm'])*.001;radius=float(edge['radius_mm'])*.001
        if not np.isfinite(length+radius) or min(length,radius)<=0:raise ValueError('Invalid hydraulic dimensions')
        resistance=8*mu*length/(pi*radius**4);g=1/resistance
        a,b=edge['from'],edge['to']
        if a==b:raise ValueError('Self-connected hydraulic edge')
        for n,other in ((a,b),(b,a)):
            if n!=sink:
                matrix[index[n],index[n]]+=g
                if other!=sink:matrix[index[n],index[other]]-=g
        records.append(dict(edge,resistance_pa_s_m3=resistance))
    pressure=np.linalg.solve(matrix,rhs);pressures={sink:0.,**{n:float(pressure[i]) for n,i in index.items()}}
    balance={n:0. for n in nodes}
    for edge in records:
        a,b=edge['from'],edge['to'];q=(pressures[a]-pressures[b])/edge['resistance_pa_s_m3']
        radius=edge['radius_mm']*.001;re=rho*abs(q)/(pi*radius**2)*2*radius/mu
        entrance=.05*re*2*edge['radius_mm']
        edge.update(flow_ml_s=q*1e6,pressure_drop_pa=pressures[a]-pressures[b],reynolds=re,laminar_screen_passed=re<2300,
                    entrance_length_mm=entrance,fully_developed_length_screen=entrance<edge['length_mm'])
        balance[a]+=q;balance[b]-=q
    balance[source]-=total_flow_ml_s*1e-6;balance[sink]+=total_flow_ml_s*1e-6
    residual=max(abs(v) for v in balance.values())/(total_flow_ml_s*1e-6)
    if residual>1e-9:raise ValueError('Cooling network mass balance failed')
    power=pressures[source]*total_flow_ml_s*1e-6
    dissipation=sum(e['resistance_pa_s_m3']*(e['flow_ml_s']*1e-6)**2 for e in records)
    energy_residual=abs(power-dissipation)/power
    if energy_residual>1e-9:raise ValueError('Cooling network energy balance failed')
    return dict(method='Linear laminar hydraulic network',fluid='room-temperature air',total_flow_ml_s=total_flow_ml_s,
        required_pressure_difference_pa=pressures[source],node_pressures_pa=pressures,edges=records,
        relative_mass_balance_residual=residual,relative_energy_balance_residual=energy_residual,
        all_edges_laminar=all(e['laminar_screen_passed'] for e in records),
        developing_flow_edges=[e['id'] for e in records if not e['fully_developed_length_screen']],
        assumptions=dict(density_kg_m3=rho,dynamic_viscosity_pa_s=mu),
        scope='Steady straight-pipe equivalents with finite ring-manifold resistance. Omits bends, entrances, roughness, leakage, heat transfer and rotating machinery. This is not 3-D CFD or measured cooling performance.')


def collector_edges(prefix,collector,attachments):
    """Split the saved collector polyline at its actual branch/port junctions.

    Project within the geometry junction tolerance, then retain every intervening
    segment length. No assumed branch count, angular spacing or ring radius.
    """
    points=np.asarray(collector['points'],dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)<4 or not np.isfinite(points).all():
        raise ValueError('Invalid collector points')
    if np.linalg.norm(points[0]-points[-1])>1e-6:raise ValueError('Collector is not closed')
    delta=np.diff(points,axis=0);lengths=np.linalg.norm(delta,axis=1)
    if np.any(lengths<=0):raise ValueError('Degenerate collector segment')
    cumulative=np.r_[0,np.cumsum(lengths)];total=cumulative[-1]
    positions=[]
    for name,point in attachments.items():
        t=np.clip(np.sum((np.asarray(point)-points[:-1])*delta,axis=1)/lengths**2,0,1)
        gaps=np.linalg.norm(points[:-1]+t[:,None]*delta-point,axis=1);i=int(np.argmin(gaps))
        if gaps[i]>.05:raise ValueError('Disconnected collector junction: '+name)
        s=float(cumulative[i]+t[i]*lengths[i])
        positions.append((0. if total-s<1e-6 else s,name))
    nodes=[];mapping={}
    for position,name in sorted(positions):
        if not nodes or position-nodes[-1][0]>1e-6:nodes.append((position,prefix+'-node-'+str(len(nodes))))
        mapping[name]=nodes[-1][1]
    if len(nodes)<2:raise ValueError('Collector needs distinct junctions')
    edges=[]
    for i,(position,node) in enumerate(nodes):
        next_position,next_node=nodes[(i+1)%len(nodes)]
        edges.append(dict(id=prefix+'-ring-'+str(i),**{'from':node,'to':next_node},
            length_mm=float((next_position-position)%total),radius_mm=collector['bore_radius_mm'],group='ring manifold'))
    return edges,mapping


def assembly_network(design,cooling,flow=10.):
    edges=[]
    def add(identity,a,b,route,group):
        edges.append(dict(id=identity,**{'from':a,'to':b},length_mm=length_mm(route['points']),radius_mm=route['bore_radius_mm'],group=group))
    def rings(prefix,collectors,branches,ports):
        maps=[]
        if len(collectors)!=2 or len(ports)!=2 or not branches:raise ValueError('Expected two collectors, two ports and branches')
        if len({r['id'] for r in branches})!=len(branches):raise ValueError('Duplicate branch IDs')
        for i,collector in enumerate(collectors):
            attachments={r['id']:r['points'][0 if i==0 else -1] for r in branches}
            attachments['port']=ports[i]['points'][0]
            ring,mapping=collector_edges(prefix+str(i),collector,attachments);edges.extend(ring);maps.append(mapping)
        return maps
    core=design['cooling']
    core_maps=rings('core',core['collectors'],core['routes'],core['ports'])
    bell_maps=rings('bell',cooling['rings'],cooling['branches'],cooling['ports'])
    add('core-inlet','inlet',core_maps[0]['port'],core['ports'][0],'core port')
    for route in core['routes']:add(route['id'],core_maps[0][route['id']],core_maps[1][route['id']],route,'core channel')
    add('core-outlet',core_maps[1]['port'],'core-port',core['ports'][1],'core port')
    for a,b in [(core['ports'][1]['points'][-1],cooling['supply'][0]),
                (cooling['supply'][-1],cooling['ports'][0]['points'][-1]),
                (cooling['ports'][1]['points'][-1],cooling['return'][0])]:
        if np.linalg.norm(np.asarray(a)-b)>.05:raise ValueError('Disconnected external cooling route')
    add('cooling-supply','core-port','front-port',dict(points=cooling['supply'],bore_radius_mm=cooling.get('supply_bore_radius_mm',.8)),'external line')
    add('jacket-inlet','front-port',bell_maps[0]['port'],cooling['ports'][0],'jacket port')
    for route in cooling['branches']:add(route['id'],bell_maps[0][route['id']],bell_maps[1][route['id']],route,'bell channel')
    add('jacket-outlet',bell_maps[1]['port'],'rear-port',cooling['ports'][1],'jacket port')
    add('cooling-return','rear-port','outlet',dict(points=cooling['return'],bore_radius_mm=cooling.get('return_bore_radius_mm',.8)),'external line')
    result=solve_network(edges,'inlet','outlet',flow)
    result['model_version']=2
    result['core_collectors']='Finite resistance from saved collector polylines and actual junction positions.'
    result['legacy_defaults']=[k+' = 0.8 mm (revision 10 native route specification)' for k in ('supply_bore_radius_mm','return_bore_radius_mm') if k not in cooling]
    return result
