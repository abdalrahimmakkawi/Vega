"""Vega's domain adapter. Geometry ownership is separate from the PicoGK backend."""
from pathlib import Path
import sys
from math import pi

# Use the in-repository source package during local development. The package can
# also be installed independently; it has no Vega app or third-party dependency.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'packages'/'vega-geometry'))
from vega_geometry import Assembly, Port, centerline_length, fingerprint


def build_feed_system(b, engineering, geometry, layout=None):
    layout = layout or b.tank_layout
    if layout not in ('paired', 'staggered'):
        raise ValueError('Unknown tank layout')
    profile, wall = geometry['profile_mm'], b.wall_mm
    chamber_radius, nozzle_end = profile[0][1], profile[-1][0]
    fuel, ox = engineering['tank_sizing']['fuel'], engineering['tank_sizing']['oxidizer']
    radius = fuel['inner_radius_mm']
    offset = chamber_radius + wall + radius + b.tank_clearance_mm
    # Both layouts preserve each tank's solved volume. Staggering translates the
    # fuel tank upstream, and its attached route regenerates from its outlet.
    fuel_top = -18 - (0.6*fuel['length_mm'] if layout == 'staggered' else 0)
    tanks = [
        {'id':'fuel_tank','name':'Fuel tank','center':[offset,0,fuel_top-fuel['length_mm']/2],
         'length_mm':fuel['length_mm'],'radius_mm':radius,'wall_mm':wall},
        {'id':'oxidizer_tank','name':'Oxidizer tank','center':[-offset,0,-18-ox['length_mm']/2],
         'length_mm':ox['length_mm'],'radius_mm':radius,'wall_mm':wall},
    ]
    graph = Assembly()
    for tank in tanks:
        graph.component(tank['id'], 'capped_cylinder', ['burn_duration_s','mass_flow','density','tank_layout','tank_clearance_mm'])
    graph.component('injector_head','injector_interface',['chamber_radius','injector_pressure_drop'])
    bore = engineering['feed_bore_radius_mm']
    origins = {}
    for tank, medium in zip(tanks, ('fuel','oxidizer')):
        top = tank['center'][2] + tank['length_mm']/2
        inner_length = tank['length_mm']-2*wall
        z = top-wall-min(17, inner_length/2)
        origins[medium] = graph.port(Port(tank['id']+'.out',tank['id'],medium,
                                         (tank['center'][0],0,z),bore[medium]))
    injector_ports = {}
    for medium, sign in (('fuel',1),('oxidizer',-1)):
        injector_ports[medium] = graph.port(Port('injector.'+medium,'injector_head',medium,
            (sign*(chamber_radius-4),0,-5),bore[medium]))
    cooling = geometry.get('cooling')
    if cooling:
        graph.component('cooling_channels','parallel_channel_network',['channel_count','channel_radius','pressure_shell_profile'])
        inlet, outlet = cooling['ports'][0]['points'][-1], cooling['ports'][1]['points'][-1]
        graph.port(Port('cooling.in','cooling_channels','fuel',inlet,bore['fuel']))
        graph.port(Port('cooling.out','cooling_channels','fuel',outlet,bore['fuel']))
        target = 'cooling.in'
    else:
        inlet, outlet = injector_ports['fuel'], None
        target = 'injector.fuel'
    clearance = max(offset+radius+wall+8, inlet[0]+14)
    fz, oz = origins['fuel'][2], origins['oxidizer'][2]
    manifolds = [
        graph.route('fuel_feed','Fuel feed tube','fuel','fuel_tank.out',target,
                    [[clearance,0,fz],[clearance,0,inlet[2]]],bore['fuel']),
        graph.route('oxidizer_feed','Oxidizer feed tube','oxidizer','oxidizer_tank.out','injector.oxidizer',
                    [[-offset-radius-wall-8,0,-5]],bore['oxidizer']),
    ]
    if cooling:
        # Keep the return away from the feed trunk: joining them would bypass
        # the cooling circuit even though every sampled centerline is open.
        return_clearance = outlet[0]+8
        manifolds.append(graph.route('fuel_return','Fuel return to injector','fuel','cooling.out','injector.fuel',
                         [[return_clearance,0,outlet[2]],[return_clearance,0,-12]],bore['fuel']))
    # Keep the displayed outer sweep outside tank cavities. Bore sweeps extend
    # to the registered tank outlet inside the cavity to cut the wall reliably.
    manifolds[0]['points'] = [[offset+radius+wall/2,0,fz]]+manifolds[0]['points'][1:]
    manifolds[1]['points'] = [[-offset-radius-wall/2,0,oz]]+manifolds[1]['points'][1:]
    injector = {
        'id':'injector_head','name':'Injector face with two screened outlets',
        'z_mm':-8,'radius_mm':chamber_radius+wall,'length_mm':9,
        'orifices':[
            {'id':medium+'_orifice','points':[injector_ports[medium],[injector_ports[medium][0],0,2]],
             'radius_mm':engineering['injector_screen']['single_'+medium+'_orifice_radius_mm']}
            for medium in ('fuel','oxidizer')],
    }
    systems = {'architecture':'pressure_fed','tanks':tanks,'manifolds':manifolds,'injector':injector,
               'flow_network':engineering['flow_network'],
               'unresolved':['Regulator and valve sizing','Injector stability','Tank end-cap and port stress']}
    model = graph.export()
    model['layout'] = layout
    model['tank_clearance_input_mm'] = b.tank_clearance_mm
    model['recipe_sha256'] = fingerprint(systems)
    model['trace'] = [
        'Burn duration and solved mass flow determine tank volumes and lengths.',
        'Tank clearance determines radial placement; layout determines axial placement.',
        'Feed sweeps terminate at registered tank, cooling and injector interfaces.',
        'PicoGK consumes these tank positions and route points without a second layout template.',
    ]
    model['total_feed_centerline_mm'] = sum(v['centerline_length_mm'] for v in model['routes'].values())
    # Analytical capacity checks independent of body placement.
    model['checks'] = {
        'tank_capacities_preserved': all(pi*(t['radius_mm']/1000)**2*(t['length_mm']-2*wall)/1000
                                       >= size['capacity_m3']
                                       for t,size in zip(tanks,(fuel,ox))),
        'tank_outer_envelopes_separated': 2*offset > 2*(radius+wall),
        'exact_registered_interfaces': all(c['gap_mm']<=1e-6 for c in model['connections']),
    }
    return systems, model


def apply_routed_feed_losses(b, engineering, systems):
    """Re-evaluate the existing Darcy screen on the actual emitted route lengths."""
    from .engineering import darcy_loss_bar
    prop, flows = engineering['properties'], engineering['mass_flow_kg_s']
    lengths = {'fuel':0.0,'oxidizer':0.0}
    for route in systems['manifolds']:
        medium = 'oxidizer' if route['id']=='oxidizer_feed' else 'fuel'
        lengths[medium] += centerline_length(route['bore_points'])/1000
    p = engineering['pressure_bar']
    previous = p['fuel_feed_loss']+p['oxidizer_feed_loss']
    for medium in lengths:
        loss, _, _ = darcy_loss_bar(flows[medium],prop[medium+'_density_kg_m3'],
            prop[medium+'_viscosity_pa_s'],engineering['feed_bore_radius_mm'][medium],lengths[medium])
        p[medium+'_feed_loss'] = loss
        p[medium+'_required'] = b.chamber_pressure_bar+p['injector_loss']+loss+b.valve_loss_bar+b.pressure_reserve_bar
    p['fuel_required'] += p['cooling_loss']
    p['margin'] = p['tank_available']-max(p['fuel_required'],p['oxidizer_required'])
    engineering['checks']['pressure_margin'] = p['margin']>=0
    engineering['analytical_screen_pass'] = all(engineering['checks'].values())
    engineering['preliminary_score_lower_is_better'] += 3*(p['fuel_feed_loss']+p['oxidizer_feed_loss']-previous)
    engineering['feed_route_lengths_m'] = lengths
    engineering['feed_route_scope'] = 'Emitted centerlines including fuel return; friction only, no bend or fitting losses.'
