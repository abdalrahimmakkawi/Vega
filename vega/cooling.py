"""Original bounded channel routing for the non-firing inspection geometry."""
from math import sin,cos,pi,sqrt,dist
import numpy as np
from vega_geometry import Assembly, Port, centerline_length
from vega_geometry.sections import interpolate, contour


def validate_network(routes, collectors, ports):
    """Check actual polyline junctions, including the external access tubes."""
    if len(collectors) != 2 or len(ports) != 2 or not routes:
        raise ValueError('Cooling network requires two collectors, two ports and branches')
    def gap(point, collector):
        p=np.asarray(point); ps=np.asarray(collector['points'])
        a,b=ps[:-1],ps[1:]; delta=b-a
        lengths=np.sum(delta*delta,axis=1)
        if np.any(lengths<=0):raise ValueError('Degenerate collector segment')
        t=np.clip(np.sum((p-a)*delta,axis=1)/lengths,0,1)
        return float(np.min(np.linalg.norm(p-a-t[:,None]*delta,axis=1)))
    gaps=[]
    for index,collector in enumerate(collectors):
        if dist(collector['points'][0],collector['points'][-1])>1e-6:
            raise ValueError('Cooling collector is not closed')
        for route in routes:
            gaps.append(gap(route['points'][0 if index==0 else -1],collector))
        gaps.append(gap(ports[index]['points'][0],collector))
    if max(gaps)>.05:
        raise ValueError('Disconnected cooling branch or access port')
    return dict(status='polyline_junctions_checked',branch_count=len(routes),
        collector_count=2,external_port_count=2,maximum_junction_gap_mm=max(gaps),
        nominal_bore_diameter_mm=2*routes[0]['bore_radius_mm'],
        scope='Polyline junction proximity only. Native clearance samples are checked separately; no leak or thermal qualification.')


def cooling_routes(core_sections, voxel_mm=.4):
    bore_radius=max(.8,1.5*voxel_mm)
    outer_radius=bore_radius+1.2
    offset=3.4+(outer_radius-2.)
    def radius(z):
        return float(np.linalg.norm(contour(interpolate(core_sections,z),np.array([0.]))[0,:2]))
    trials=[]
    # Discrete new route families, evaluated against actual radial support
    # segments at z=70..74 and the four inspection air corridors.
    for angle_deg in (20,25,30,35):
        for twist_deg in (-8,0,8):
            paths=[]; minimum=float('inf')
            for branch in range(4):
                points=[]
                for z in np.linspace(76,112,73):
                    t=(z-76)/36
                    angle=(angle_deg+90*branch+twist_deg*sin(pi*t))*pi/180
                    r=radius(float(z))+offset
                    point=[r*cos(angle),r*sin(angle),float(z)]
                    # 2 mm outer tube radius + 0.6 mm sampled air corridor.
                    for axis in range(4):
                        q=[14.8*cos(axis*pi/2),14.8*sin(axis*pi/2),float(z)]
                        minimum=min(minimum,dist(point,q)-(outer_radius+.6))
                    points.append(point)
                paths.append(points)
            length=sum(centerline_length(p) for p in paths)
            feasible=minimum>=.8
            trials.append(dict(angle_deg=angle_deg,twist_deg=twist_deg,length_mm=length,
                air_corridor_clearance_mm=minimum,feasible=feasible,paths=paths))
    feasible=[t for t in trials if t['feasible']]
    if not feasible:raise ValueError('No cooling route clears the inspection airflow corridors')
    selected=min(feasible,key=lambda t:(t['length_mm'],-t['air_corridor_clearance_mm']))
    graph=Assembly(); graph.component('inlet_collector','coolant_manifold');graph.component('outlet_collector','coolant_manifold')
    routes=[]
    for i,points in enumerate(selected['paths']):
        for end,component,p in [('in','inlet_collector',points[0]),('out','outlet_collector',points[-1])]:
            graph.port(Port(f'{i}.{end}',component,'inspection_air',tuple(p),bore_radius))
        routes.append(graph.route(f'cooling_{i}','Cooling inspection channel','inspection_air',f'{i}.in',f'{i}.out',points[1:-1],bore_radius,1.2))
    collectors=[]
    for z in (76.,112.):
        r=radius(z)+offset
        points=[[r*cos(2*pi*i/144),r*sin(2*pi*i/144),z] for i in range(145)]
        collectors.append(dict(points=points,bore_radius_mm=bore_radius,outer_radius_mm=outer_radius))
    ports=[]
    for z,angle in [(76.,pi/4),(112.,3*pi/4)]:
        r=radius(z)+offset
        points=[[r*cos(angle),r*sin(angle),z],[29*cos(angle),29*sin(angle),z]]
        bore_points=[points[0],[33*cos(angle),33*sin(angle),z]]
        ports.append(dict(points=points,bore_points=bore_points,bore_radius_mm=bore_radius,outer_radius_mm=outer_radius))
    # Low-speed air reference for inspectable passages, not liquid hydrogen cooling.
    density=1.2; viscosity=1.8e-5; velocity=5.; diameter=2*bore_radius/1000
    reynolds=density*velocity*diameter/viscosity
    friction=64/reynolds
    channel_length=selected['length_mm']/4/1000
    drop=friction*channel_length/diameter*density*velocity**2/2
    return dict(routes=routes,collectors=collectors,ports=ports,graph=graph.export(),
        network=validate_network(routes,collectors,ports),
        selection={k:v for k,v in selected.items() if k!='paths'},
        candidates=[{k:v for k,v in t.items() if k!='paths'} for t in trials],
        hydraulic_reference=dict(fluid='room-temperature air',velocity_m_s=velocity,
            reynolds=reynolds,channel_friction_drop_pa=drop,
            scope='Fully developed laminar straight-pipe approximation; bends, collectors and ports omitted'),
        thermal_status='unresolved: hot-wall flux, material, real coolant state and allowable temperatures required',
        scope='Open inspection channels. Split FDM halves are not sealed or pressure rated.')
