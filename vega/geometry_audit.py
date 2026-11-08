"""Deterministic checks that the analytical network maps to one geometry recipe.

These tests establish route intent and clearance in the centerline model. They
cannot replace a voxel connectivity, leak, wall-thickness or pressure test.
"""
from math import dist, sqrt

def _segment_distance(a,b,c,d):
    u=[b[i]-a[i] for i in range(3)];v=[d[i]-c[i] for i in range(3)]
    w=[a[i]-c[i] for i in range(3)]
    dot=lambda x,y:sum(q*r for q,r in zip(x,y))
    aa=dot(u,u);bb=dot(u,v);cc=dot(v,v);dd=dot(u,w);ee=dot(v,w)
    den=aa*cc-bb*bb
    s=0.0 if den<1e-12 else max(0.0,min(1.0,(bb*ee-cc*dd)/den))
    t=max(0.0,min(1.0,(bb*s+ee)/cc)) if cc else 0.0
    s=max(0.0,min(1.0,(bb*t-dd)/aa)) if aa else 0.0
    t=max(0.0,min(1.0,(bb*s+ee)/cc)) if cc else 0.0
    return sqrt(sum((w[i]+s*u[i]-t*v[i])**2 for i in range(3)))

def _path_distance(first,second):
    return min(_segment_distance(a,b,c,d) for a,b in zip(first,first[1:])
               for c,d in zip(second,second[1:]))

def inspect(geometry):
    cooling=geometry.get('cooling')
    systems=geometry['systems']
    tanks={t['id']:t for t in systems['tanks']}
    tubes={t['id']:t for t in systems['manifolds']}
    orifices={o['id']:o for o in systems['injector']['orifices']}
    checks={}
    def joined(a,b,tolerance=1.5):return dist(a,b)<=tolerance
    for tank_id,tube_id in (('fuel_tank','fuel_feed'),('oxidizer_tank','oxidizer_feed')):
        tank=tanks[tank_id];start=tubes[tube_id]['bore_points'][0];center=tank['center']
        checks[tank_id+'_feed_origin_inside']=dist(start[:2],center[:2])<tank['radius_mm'] and abs(start[2]-center[2])<tank['length_mm']/2-tank['wall_mm']
    checks['oxidizer_feed_to_injector']=joined(tubes['oxidizer_feed']['bore_points'][-1],orifices['oxidizer_orifice']['points'][0])
    if cooling:
        ports={p['id']:p for p in cooling['ports']}
        checks['fuel_feed_to_cooling_inlet']=joined(tubes['fuel_feed']['bore_points'][-1],ports['fuel_inlet']['points'][-1])
        checks['cooling_outlet_to_fuel_return']=joined(ports['fuel_outlet']['points'][-1],tubes['fuel_return']['bore_points'][0])
        checks['fuel_return_to_injector']=joined(tubes['fuel_return']['bore_points'][-1],orifices['fuel_orifice']['points'][0])
        feed,returned=tubes['fuel_feed'],tubes['fuel_return']
        checks['no_feed_return_short_circuit']=(
            _path_distance(feed['bore_points'],returned['bore_points'])
            -feed['bore_radius_mm']-returned['bore_radius_mm']>geometry['minimum_ligament_mm'])
        channels=[p for p in cooling['paths'] if p['id'].startswith('channel_')]
        collectors=[p for p in cooling['paths'] if p['id'].endswith('_collector')]
        checks['all_channels_touch_both_collectors']=bool(channels) and len(collectors)==2 and all(
            any(abs(endpoint[2]-collector['points'][0][2])<1e-6 and
                abs(dist(endpoint[:2],[0,0])-dist(collector['points'][0][:2],[0,0]))<1e-6
                for collector in collectors)
            for channel in channels for endpoint in (channel['points'][0],channel['points'][-1]))
    else:
        checks['fuel_feed_to_injector']=joined(tubes['fuel_feed']['bore_points'][-1],orifices['fuel_orifice']['points'][0])
    fuel_tubes=[tubes[name] for name in ('fuel_feed','fuel_return') if name in tubes]
    oxidizer=tubes['oxidizer_feed']
    clearances=[_path_distance(f['bore_points'],oxidizer['bore_points'])-f['bore_radius_mm']-oxidizer['bore_radius_mm']
                for f in fuel_tubes]
    checks['fuel_oxidizer_feed_separation']=min(clearances)>geometry['minimum_ligament_mm']
    return {'checks':checks,'pass':all(checks.values()),
            'minimum_cross_propellant_clearance_mm':min(clearances),
            'scope':'Centerline endpoint and feed-bore clearance checks on the recipe; not voxel leak isolation or global minimum wall.'}
