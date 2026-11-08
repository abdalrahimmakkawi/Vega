"""Geometric passage layout, not a thermal or hydraulic design solver."""
import math
import json
from pathlib import Path

def knowledge():
    return json.loads((Path(__file__).parent/'rocket_knowledge.json').read_text(encoding='utf-8'))

def cooling_layout(profile, wall, channel_count=12, radius=2.0):
    if wall<2*radius+4:
        raise ValueError('Passage layout needs at least 2 mm radial ligament on each side at 1 mm voxels.')
    def r(z):
        for (a,ra),(b,rb) in zip(profile,profile[1:]):
            if a<=z<=b:return ra+(rb-ra)*(z-a)/(b-a)+wall/2
        raise ValueError('Route outside profile')
    start,end=8,profile[-1][0]-8
    def point(z,angle):return [r(z)*math.cos(angle),r(z)*math.sin(angle),z]
    paths=[]
    for name,z in [('inlet_collector',end),('outlet_collector',start)]:
        paths.append({'id':name,'points':[point(z,2*math.pi*k/96) for k in range(97)]})
    station_count=max(16,math.ceil((end-start)/8))
    stations=[start+(end-start)*i/station_count for i in range(station_count+1)]
    # The phase varies continuously, keeping constant circumferential spacing.
    # Both ends meet the collector rings; the route drives subtraction and inspection.
    for k in range(channel_count):
        paths.append({'id':f'channel_{k+1:02}','points':[point(z,2*math.pi*k/channel_count+0.42*(z-start)/(end-start)) for z in stations]})
    ports=[]
    for name,z in [('fuel_inlet',end),('fuel_outlet',start)]:
        a=point(z,0);b=[a[0]+wall/2+12,0,z]
        ports.append({'id':name,'name':name.replace('_',' ').title()+' interface','points':[a,b]})
    return {'radius_mm':radius,'paths':paths,'ports':ports,'tube_wall_mm':3,
            'channel_count':channel_count,'status':'sized_by_reduced_order_pressure_fed_screen',
            'helix_phase_rad':0.42,
            'flow_order':['fuel inlet interface','downstream collector',f'{channel_count} parallel wall passages','upstream collector','fuel outlet / injector interface'],
            'unresolved':['Fuel properties and mass split','Pressure drop and tank pressure','Heat flux, wall temperature and boiling','Injector connection and metering','Seals, tolerances and manufacturing access']}
