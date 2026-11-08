"""Rocket-core concept geometry connected to an explicit vehicle mission budget."""
from dataclasses import dataclass, asdict, fields, replace
import math
import hashlib
import json
from pathlib import Path
import sys
from .circuits import cooling_layout, knowledge
from .manufacturing import constrain, screen as manufacturing_screen, validate_selection
from .engineering import evaluate, apply_operating_thermal
from .evidence import compare
from .flight import screen_flight
from .geometry_audit import inspect as inspect_geometry
from .combined_cycle import screen_combined_cycle
from .rbcc_knowledge import check_architecture_wiring
from .geometry_model import build_feed_system, apply_routed_feed_losses
from .assembly import build_assembly
from .computational_model import build_model_trace
from .propulsion_model import nozzle_design, close_feed_design, predict_fixed_hardware, apply_operating_load_screen, fixed_nozzle_performance
from .equation_system import EquationConvergenceError
from .vehicle_mass import estimate_vehicle_mass
from .orbital_resources import size_orbital_resources
from .channel_synthesis import size_channels

SOURCE='https://www.grc.nasa.gov/WWW/K-12/BGP/rktthsum.html'

@dataclass(frozen=True)
class RocketBrief:
    material_id: str='custom'
    print_process: str='unspecified'
    test_purpose: str='concept'
    print_min_wall_mm: float=0
    print_min_ligament_mm: float=0
    print_build_x_mm: float=0
    print_build_y_mm: float=0
    print_build_z_mm: float=0
    architecture: str='pressure_fed'
    propellant_model: str='lox_rp1'
    mixture_ratio: float=2.6
    jacket_pattern: str='penrose'
    cell_size_mm: float=12
    beam_radius_mm: float=2.5
    jacket_depth_mm: float=10
    thrust_n: float=1000
    chamber_pressure_bar: float=20
    chamber_temperature_k: float=3000
    ambient_pressure_bar: float=0
    expansion_ratio: float=8
    gamma: float=1.22
    gas_constant_j_kg_k: float=350
    chamber_area_ratio: float=4
    chamber_length_mm: float=120
    wall_mm: float=10
    cooling_passages: float=1
    channel_variant: float=0
    nozzle_half_angle_deg: float=15
    nozzle_contour: str='bell'
    burn_duration_s: float=2
    tank_pressure_bar: float=35
    tank_layout: str='staggered'
    tank_clearance_mm: float=22
    pressure_reserve_bar: float=2
    injector_pressure_drop_fraction: float=0.2
    design_heat_flux_mw_m2: float=0.5
    thermal_model: str='prescribed_flux'
    gas_htc_w_m2_k: float=1000
    max_coolant_outlet_k: float=425
    allowable_stress_mpa: float=80
    minimum_ligament_mm: float=2
    pressurant_storage_bar: float=200
    pressurant_temperature_k: float=293
    regulator_reserve_bar: float=20
    valve_loss_bar: float=0.5
    wall_conductivity_w_m_k: float=200
    coolant_htc_w_m2_k: float=10000
    max_wall_temperature_k: float=650
    vehicle_dry_mass_kg: float=25
    vehicle_mass_mode: str='specified'
    core_material_density_kg_m3: float=8900
    tank_material_density_kg_m3: float=2700
    assembly_material_density_kg_m3: float=2700
    vehicle_unmodeled_dry_mass_kg: float=100
    vehicle_mass_margin_fraction: float=.2
    mission_delta_v_allowance_m_s: float=0
    orbital_electrical_load_w: float=1000
    solar_array_efficiency: float=.28
    solar_eol_factor: float=.8
    battery_specific_energy_wh_kg: float=150
    battery_depth_of_discharge: float=.7
    power_margin_fraction: float=.2
    radiator_temperature_k: float=320
    radiator_sink_temperature_k: float=250
    radiator_emissivity: float=.85
    vehicle_drag_coefficient: float=0.5
    vehicle_diameter_m: float=0.15
    launch_altitude_m: float=0
    target_apogee_m: float=0
    vehicle_architecture: str='spaceplane'
    propulsion_family: str='rbcc'
    transition_mach: float=4
    transition_altitude_m: float=25000
    orbit_altitude_m: float=200000
    payload_mass_kg: float=1000
    inlet_capture_area_m2: float=0.08
    inlet_aspect_ratio: float=3
    inlet_section: str='elliptical'
    inlet_length_m: float=0.6
    inlet_wall_mm: float=10
    mixer_length_dh: float=2
    combustor_length_dh: float=2.5
    combined_exit_ratio: float=2
    combined_throat_ratio: float=.68
    airpath_pressure_recovery: float=.8
    air_fuel_ratio: float=30.0
    air_combustion_efficiency: float=.95
    mixer_pressure_loss_fraction: float=.08
    air_combustor_pressure_loss_fraction: float=.10
    frame_sectors: float=8
    frame_topology: str='optimized'
    frame_volume_fraction: float=.65
    mesh_surface_edge_mm: float=12
    mesh_chord_tolerance_mm: float=.5
    mesh_voxel_mm: float=.75
    search_evaluations: float=64
    search_mesh_limit: float=12
    search_seed: int=0
    mesh_run_solvers: float=1
    airbreathing_isp_s: float=1200
    vehicle_lift_to_drag: float=6
    airbreathing_thrust_fraction: float=0.35

    @classmethod
    def parse(cls, data):
        if data.get('material_id','custom')!='custom':
            required={'core_material_density_kg_m3','wall_conductivity_w_m_k','allowable_stress_mpa','max_wall_temperature_k'}
            if required-set(data):raise ValueError('Selected material requires explicit engineering properties: '+', '.join(sorted(required-set(data))))
        allowed={f.name for f in fields(cls)}
        if set(data)-allowed:raise ValueError('Unsupported rocket requirement: '+', '.join(sorted(set(data)-allowed)))
        limits={'print_min_wall_mm':(0,15),'print_min_ligament_mm':(0,5),'print_build_x_mm':(0,100000),'print_build_y_mm':(0,100000),'print_build_z_mm':(0,100000),'search_evaluations':(8,512),'search_mesh_limit':(2,64),'mixture_ratio':(1,8),'cooling_passages':(0,1),'channel_variant':(0,16),'cell_size_mm':(8,25),'beam_radius_mm':(1,3),'jacket_depth_mm':(6,20),'thrust_n':(100,10000),'chamber_pressure_bar':(2,100),'chamber_temperature_k':(300,4500),
            'ambient_pressure_bar':(0,2),'expansion_ratio':(1.1,30),'gamma':(1.05,1.67),
            'gas_constant_j_kg_k':(100,1000),'chamber_area_ratio':(2,10),'chamber_length_mm':(40,500),
            'wall_mm':(2,15),'nozzle_half_angle_deg':(8,25),'burn_duration_s':(0.5,20),
            'tank_pressure_bar':(5,150),'tank_clearance_mm':(10,50),'pressure_reserve_bar':(0,20),
            'injector_pressure_drop_fraction':(0.05,0.5),'design_heat_flux_mw_m2':(0.1,5),
            'max_coolant_outlet_k':(50,900),'allowable_stress_mpa':(.1,2000),
            'minimum_ligament_mm':(1,5),'pressurant_storage_bar':(40,350),
            'pressurant_temperature_k':(100,500),'regulator_reserve_bar':(5,80),
            'valve_loss_bar':(0,5),'wall_conductivity_w_m_k':(.01,1000),
            'gas_htc_w_m2_k':(10,100000),'coolant_htc_w_m2_k':(100,100000),'max_wall_temperature_k':(100,1500),
            'vehicle_dry_mass_kg':(1,100000),'vehicle_drag_coefficient':(0,3),
            'vehicle_diameter_m':(0.02,10),'launch_altitude_m':(0,100000),
            'target_apogee_m':(0,1000000),'transition_mach':(1,15),'transition_altitude_m':(1000,32000),
            'orbit_altitude_m':(80000,2000000),'payload_mass_kg':(0,1000000),'inlet_capture_area_m2':(0.01,1000),
            'inlet_aspect_ratio':(1,10),'inlet_length_m':(0.5,20),'inlet_wall_mm':(1,50),
            'mixer_length_dh':(1,5),'combustor_length_dh':(1,6),'combined_exit_ratio':(1.2,4),'combined_throat_ratio':(.55,.85),'airpath_pressure_recovery':(.5,1),'air_fuel_ratio':(5,200),'air_combustion_efficiency':(.1,1),'mixer_pressure_loss_fraction':(0,.4),'air_combustor_pressure_loss_fraction':(0,.4),'frame_volume_fraction':(.35,1),'frame_sectors':(6,12),
            'airbreathing_isp_s':(100,5000),'vehicle_lift_to_drag':(1,20),'airbreathing_thrust_fraction':(0,1)}
        values={}
        limits['search_seed']=(0,4294967295)
        limits.update({'core_material_density_kg_m3':(100,22000),'tank_material_density_kg_m3':(100,22000),
            'assembly_material_density_kg_m3':(100,22000),'vehicle_unmodeled_dry_mass_kg':(0,100000),
            'vehicle_mass_margin_fraction':(0,1),'mission_delta_v_allowance_m_s':(0,10000)})
        limits.update({'mesh_surface_edge_mm':(4,40),'mesh_chord_tolerance_mm':(.1,2),'mesh_voxel_mm':(.5,2),'mesh_run_solvers':(0,1)})
        limits.update({'orbital_electrical_load_w':(0,1000000),'solar_array_efficiency':(.01,.5),
            'solar_eol_factor':(.1,1),'battery_specific_energy_wh_kg':(10,500),
            'battery_depth_of_discharge':(.1,.9),'power_margin_fraction':(0,1),
            'radiator_temperature_k':(200,600),'radiator_sink_temperature_k':(3,500),
            'radiator_emissivity':(.05,1)})
        for key,value in data.items():
            if key in ('material_id','print_process','test_purpose'):
                if not isinstance(value,str):raise ValueError(key+' must be text')
                values[key]=value;continue
            if key=='vehicle_mass_mode':
                if value not in ('specified','component_estimate'):raise ValueError('Unknown vehicle mass mode')
                values[key]=value;continue
            if key=='thermal_model':
                if value not in ('prescribed_flux','thermal_resistance'):raise ValueError('Unknown thermal model')
                values[key]=value;continue
            if key=='frame_topology':
                if value not in ('rails','braced','optimized'):raise ValueError('Unknown frame topology')
                values[key]=value;continue
            if key=='inlet_section':
                if value not in ('rectangular','elliptical'):raise ValueError('Unknown inlet section')
                values[key]=value;continue
            if key=='tank_layout':
                if value not in ('paired','staggered'):raise ValueError('Unknown tank layout')
                values[key]=value;continue
            if key=='architecture':
                if value is None or (isinstance(value,float) and math.isnan(value)):
                    values[key]='pressure_fed';continue
                if value not in ('pressure_fed','expander','gas_generator','staged_combustion'):
                    raise ValueError('Unknown rocket architecture')
                values[key]=value;continue
            if key=='jacket_pattern':
                if value not in ('none','bcc','quasi','penrose'):raise ValueError('Unknown jacket pattern')
                values[key]=value;continue
            if key=='nozzle_contour':
                if value not in ('bell','conical'):raise ValueError('Unknown nozzle contour')
                values[key]=value;continue
            if key=='propellant_model':
                if value not in ('lox_rp1','lox_lh2','assumed'):raise ValueError('Unknown propellant model')
                values[key]=value;continue
            if key=='vehicle_architecture':
                if value not in ('spaceplane','vertical','air_launch'): raise ValueError('Unknown vehicle architecture')
                values[key]=value;continue
            if key=='propulsion_family':
                if value not in ('rocket_only','rbcc','tbcc','ejector_rocket'): raise ValueError('Unknown propulsion family')
                values[key]=value;continue
            if isinstance(value,bool):raise ValueError(key+' must be numeric')
            try:value=float(value)
            except (TypeError,ValueError):raise ValueError(key+' must be numeric')
            lo,hi=limits[key]
            if not math.isfinite(value) or not lo<=value<=hi:raise ValueError(f'{key} must be between {lo} and {hi}')
            if key in ('search_evaluations','search_mesh_limit','search_seed') and not value.is_integer():raise ValueError(key+' must be a whole number')
            values[key]=int(value) if key=='search_seed' else value
        b=cls(**values)
        if b.radiator_temperature_k<=b.radiator_sink_temperature_k:raise ValueError('Radiator temperature must exceed the effective sink temperature')
        if b.frame_sectors not in (6,8,12):raise ValueError('Frame sectors must be 6, 8 or 12')
        if b.propulsion_family!='rocket_only' and b.launch_altitude_m>=b.transition_altitude_m:
            raise ValueError('Launch altitude must be below the requested atmospheric handover altitude')
        if b.orbit_altitude_m<=b.launch_altitude_m:
            raise ValueError('Target orbit altitude must exceed launch altitude')
        if b.architecture!='pressure_fed':
            raise ValueError('The rocket core currently uses pressure-fed sizing; choose pressure_fed while pump maps are unavailable.')
        if b.cooling_passages not in (0,1):raise ValueError('Cooling passages must be 0 or 1')
        if b.mesh_run_solvers not in (0,1):raise ValueError('Solver verification must be 0 or 1')
        if b.channel_variant not in (0,8,12,16):raise ValueError('Channel variant must be automatic, 8, 12 or 16')
        if b.cooling_passages and b.wall_mm<10:raise ValueError('Passage layout requires wall thickness >= 10 mm; or disable passages for a shell study')
        if b.beam_radius_mm*4>b.cell_size_mm:raise ValueError('Cell size must be at least four beam radii')
        if b.ambient_pressure_bar/b.chamber_pressure_bar >= (2/(b.gamma+1))**(b.gamma/(b.gamma-1)):
            raise ValueError('Back pressure is too high for the choked-flow model')
        if b.pressurant_storage_bar<=b.tank_pressure_bar+b.regulator_reserve_bar:
            raise ValueError('Pressurant storage pressure must exceed tank setpoint plus regulator reserve')
        validate_selection(b)
        return constrain(b)

def area_ratio(m,g):
    return ((2/(g+1))*(1+(g-1)*m*m/2))**((g+1)/(2*(g-1)))/m

def chamber_properties(b, pressure_pa, mixture_ratio):
    g=b.gamma; R=b.gas_constant_j_kg_k; T=b.chamber_temperature_k; pc=pressure_pa
    chemistry={'source':'user assumed gas properties','chamber_temperature_k':T,
               'gamma':g,'gas_constant_j_kg_k':R}
    if b.propellant_model!='assumed':
        dependencies=Path(__file__).resolve().parents[1]/'.tools'/'python'
        if str(dependencies) not in sys.path:sys.path.insert(0,str(dependencies))
        import rocketcea.cea_obj as cea
        cea.ROCKETCEA_DATA_DIR=str(Path(__file__).resolve().parents[1]/'data'/'cea')
        fuel={'lox_rp1':'RP-1','lox_lh2':'LH2'}[b.propellant_model]
        solver=cea.CEA_Obj(oxName='LOX',fuelName=fuel)
        pressure_psi=pressure_pa/1e5*14.5037738
        molwt,g=map(float,solver.get_Chamber_MolWt_gamma(Pc=pressure_psi,MR=mixture_ratio,eps=b.expansion_ratio))
        T=float(solver.get_Tcomb(Pc=pressure_psi,MR=mixture_ratio))/1.8
        R=8314.0/molwt
        chemistry={'source':'RocketCEA / NASA CEA equilibrium chamber state','oxidizer':'LOX','fuel':fuel,'mixture_ratio':mixture_ratio,'molecular_weight_kg_per_kmol':molwt,'chamber_temperature_k':T,'gamma':g,'gas_constant_j_kg_k':R}
    return chemistry


def solve(b):
    pc=b.chamber_pressure_bar*1e5;pa=b.ambient_pressure_bar*1e5
    chemistry=chamber_properties(b,pc,b.mixture_ratio)
    g=chemistry['gamma'];R=chemistry['gas_constant_j_kg_k'];T=chemistry['chamber_temperature_k']
    state, equation_solution = nozzle_design(b.thrust_n,pc,pa,T,g,R,b.expansion_ratio)
    me=state['mach'];te=state['exit_temperature'];pe=state['exit_pressure'];ve=state['exit_velocity']
    at=state['throat_area'];ae=state['exit_area'];mdot=state['mass_flow']
    verification={'source':'internal ideal nozzle model'}
    if b.propellant_model!='assumed':
        from proptools.nozzle import mass_flow
        reference=float(mass_flow(at,pc,T,g,chemistry['molecular_weight_kg_per_kmol']/1000))
        relative=abs(reference-mdot)/mdot
        if relative>1e-6:raise ValueError('Proptools mass-flow cross-check failed')
        verification={'source':'proptools choked mass-flow cross-check','relative_error':relative}
    return {'throat_area_m2':at,'exit_area_m2':ae,'exit_mach':me,'exit_pressure_pa':pe,
        'exit_temperature_k':te,'exit_velocity_m_s':ve,'mass_flow_kg_s':mdot,
        'momentum_thrust_n':mdot*ve,'pressure_thrust_n':(pe-pa)*ae,
        'thrust_n':mdot*ve+(pe-pa)*ae,'ideal_isp_s':b.thrust_n/(mdot*9.80665),
        'overexpanded':pe<pa,'model':'Constant-property, one-dimensional, isentropic choked nozzle','chemistry':chemistry,'verification':verification,'equation_solution':equation_solution}

def design(b, *, screening=False):
    b=constrain(b)
    c=solve(b);flight=screen_flight(b,c);rt=math.sqrt(c['throat_area_m2']/math.pi)*1000;re=rt*math.sqrt(b.expansion_ratio);rc=rt*math.sqrt(b.chamber_area_ratio)
    z1=b.chamber_length_mm;z2=z1+(rc-rt)/math.tan(math.radians(35))
    cone_length=(re-rt)/math.tan(math.radians(b.nozzle_half_angle_deg))
    z3=z2+(.75 if b.nozzle_contour=='bell' else 1.0)*cone_length
    profile=[[0,rc],[z1,rc],[z2,rt]]
    if b.nozzle_contour=='bell':
        length=z3-z2;rise=re-rt
        control1=rt+min(math.tan(math.radians(30))*length/3,.6*rise)
        control2=re-min(math.tan(math.radians(8))*length/3,.2*rise)
        for i in range(1,17):
            t=i/16;u=1-t
            radius=u**3*rt+3*u*u*t*control1+3*u*t*t*control2+t**3*re
            profile.append([z2+length*t,radius])
    else:profile.append([z3,re])
    def evaluate_variant(channel_count,radius):
        variant=evaluate(b,c,profile,channel_count,radius)
        recipe={'profile_mm':profile,'wall_mm':b.wall_mm}
        if b.cooling_passages:
            recipe['cooling']=cooling_layout(profile,b.wall_mm,variant['channel_count'],variant['channel_radius_mm'])
        systems,_=build_feed_system(b,variant,recipe)
        apply_routed_feed_losses(b,variant,systems)
        close_feed_design(b,variant)
        try:
            operating=predict_fixed_hardware(b,c,variant,
                chamber_model=(lambda pressure,ratio: chamber_properties(b,pressure,ratio)) if b.propellant_model!='assumed' else None)
            variant['operating_performance']=fixed_nozzle_performance(c,operating,b.ambient_pressure_bar*1e5)
            variant['checks']['operating_point_convergence']=True
            apply_operating_load_screen(b,variant,operating,rc)
            apply_operating_thermal(b,c,profile,variant)
        except EquationConvergenceError as error:
            variant['checks']['operating_point_convergence']=False
            variant['analytical_screen_pass']=False
            variant['operating_point']={'status':'failed','error':str(error)}
        return variant
    synthesis=None
    if b.cooling_passages and not b.channel_variant:
        variants,synthesis=size_channels(b,rt,evaluate_variant)
    else:
        variants=[evaluate_variant(n,r) for n,r in ((8,1.5),(12,1.7),(16,1.5))]
    variants.sort(key=lambda v:(not v['checks']['operating_point_convergence'],not v['analytical_screen_pass'],v['preliminary_score_lower_is_better']))
    engineering=next((v for v in variants if v['channel_count']==b.channel_variant),variants[0])
    if not engineering['checks']['operating_point_convergence']:
        raise EquationConvergenceError('Selected channel variant has no converged operating point: '+engineering['operating_point']['error'])
    if synthesis:engineering['channel_synthesis']=synthesis
    parts=[{'id':'chamber','name':'Chamber envelope','axial_mm':[0,z1],'profile_indices':[0,1],'role':'User-set residence length and contraction area. Combustion and injector are not solved.'},
        {'id':'convergent','name':'Convergent / throat','axial_mm':[z1,z2],'profile_indices':[1,2],'role':'Throat area follows choked mass flow and requested ideal thrust. Contraction angle is an explicit 35° assumption.'},
        {'id':'nozzle','name':'Expansion nozzle','axial_mm':[z2,z3],'profile_indices':[2,len(profile)-1],'role':('Cubic bell contour uses the solved throat and exit areas and 75% of the reference cone length; viscous and divergence losses are not predicted.' if b.nozzle_contour=='bell' else 'Conical contour uses the requested half-angle; divergence loss is not included in ideal thrust.')}]
    jacket={'pattern':b.jacket_pattern,'cell_size_mm':b.cell_size_mm,'beam_radius_mm':b.beam_radius_mm,
            'inner_radius_mm':rc+b.wall_mm-2,'outer_radius_mm':rc+b.wall_mm+b.jacket_depth_mm,'start_mm':8,'end_mm':z1-8}
    geometry={'profile_mm':profile,'wall_mm':b.wall_mm,'minimum_ligament_mm':b.minimum_ligament_mm,
              'length_mm':z3,'components':parts[:],'jacket':jacket}
    if b.cooling_passages:geometry['cooling']=cooling_layout(profile,b.wall_mm,engineering['channel_count'],engineering['channel_radius_mm'])
    geometry['systems'],geometry_model=build_feed_system(b,engineering,geometry)
    if b.cooling_passages:
        for port in geometry['cooling']['ports']:
            z=port['points'][0][2]
            parts.append({'id':port['id'],'name':port['name'],'axial_mm':[z-5,z+5],'role':'Hollow port connected to the sized fuel feed, cooling passage, and return network.'})
    for tank in geometry['systems']['tanks']:
        parts.append({'id':tank['id'],'name':tank['name'],'axial_mm':[tank['center'][2]-tank['length_mm']/2,tank['center'][2]+tank['length_mm']/2],'role':'Tank capacity follows mass flow, burn duration, density, and 15% ullage. Hoop stress has a preliminary screen; end caps and regulation remain unresolved.'})
    for manifold in geometry['systems']['manifolds']:
        zz=[p[2] for p in manifold['points']]
        parts.append({'id':manifold['id'],'name':manifold['name'],'axial_mm':[min(zz),max(zz)],'role':'PicoGK swept feed path with bore sized from liquid mass flow and nominal velocity; pressure drop is screened.'})
    parts.append({'id':'injector_head','name':'Injector face and outlets','axial_mm':[-8,1],'role':'Two distinct equivalent orifices are sized for the specified pressure loss; spray pattern, mixing and stability are unresolved.'})
    parts.append({'id':'thermal_lattice','name':'Integrated thermal lattice','axial_mm':[8,z1-8],'role':'PicoGK swept ribs and annular collectors integrated around the chamber. It is a geometric load path; thermal stress and manufacturing qualification remain unresolved.'})
    if b.jacket_pattern!='none':parts.append({'id':'jacket','name':'Experimental '+b.jacket_pattern+' jacket','axial_mm':[8,z1-8],'role':'Library-generated outer structure clipped to the chamber envelope. No stiffness, thermal or cooling benefit is established.'})
    tanks=geometry['systems']['tanks'];routes=geometry['systems']['manifolds']
    zmin=min(t['center'][2]-t['length_mm']/2 for t in tanks)
    system_radius=max([abs(t['center'][0])+t['radius_mm']+t['wall_mm'] for t in tanks]+
                      [math.hypot(*p[:2])+r['outer_radius_mm'] for r in routes for p in r['points']])
    layout_alternatives=[]
    for layout in ('paired','staggered'):
        systems,model=build_feed_system(b,engineering,geometry,layout)
        audit=inspect_geometry({**geometry,'systems':systems})
        layout_alternatives.append({'layout':layout,'selected':layout==b.tank_layout,
            'feed_length_mm':model['total_feed_centerline_mm'],'recipe_sha256':model['recipe_sha256'],
            'route_screen_pass':audit['pass'] and all(model['checks'].values())})
    layout_alternatives.sort(key=lambda a:(not a['route_screen_pass'],a['feed_length_mm']))
    geometry_audit=inspect_geometry(geometry)
    vehicle_screen=screen_combined_cycle(b,c)
    # Vehicle plans live beside the engine recipe. Do not fuse an arbitrary
    # decorative hull into pressure hardware and call it a solved airframe.
    candidate={'id':hashlib.sha256(json.dumps([asdict(b),engineering['channel_count'],engineering['channel_radius_mm']],sort_keys=True).encode()).hexdigest()[:12],
        'geometry':geometry,'geometry_model':geometry_model,'layout_alternatives':layout_alternatives,'geometry_audit':geometry_audit,'components':parts,'dimensions':{'length_mm':z3-zmin,'diameter_mm':2*max(max(rc,re)+b.wall_mm+(17 if b.cooling_passages else 0),jacket['outer_radius_mm'] if b.jacket_pattern!='none' else 0,system_radius)},'performance':c,'engineering':engineering,'flight_screen':flight,'vehicle_screen':vehicle_screen}
    if candidate['dimensions']['diameter_mm']**2*z3>45000000:raise ValueError('Geometry exceeds the interactive meshing budget; reduce thrust, expansion or length')
    calibration=compare(candidate['id'],engineering)
    candidate['assembly']=build_assembly(b,candidate,screening=screening)
    candidate['manufacturing']=manufacturing_screen(b,candidate)
    candidate['orbital_resources']=size_orbital_resources(b)
    mass_model=estimate_vehicle_mass(b,candidate)
    candidate['vehicle_mass_model']=mass_model
    if b.vehicle_mass_mode=='component_estimate':
        effective=replace(b,vehicle_dry_mass_kg=mass_model['selected_dry_mass_kg'],
                          vehicle_diameter_m=mass_model['selected_reference_diameter_m'])
        flight=screen_flight(effective,c)
        vehicle_screen=screen_combined_cycle(effective,c)
        candidate['flight_screen']=flight
        candidate['vehicle_screen']=vehicle_screen
    vehicle_screen['mass_budget']=mass_model
    vehicle_screen['orbital_resources']=candidate['orbital_resources']
    candidate['rbcc_architecture_wiring']=check_architecture_wiring(candidate['assembly'])
    if candidate['rbcc_architecture_wiring']['status']=='failed':
        raise ValueError('Source-informed RBCC architecture wiring failed: '+', '.join(k for k,v in candidate['rbcc_architecture_wiring']['checks'].items() if not v))
    warnings=[]
    if not all(mass_model['checks'].values()):
        warnings.append('Vehicle mass/packaging screen fails: '+', '.join(k for k,passed in mass_model['checks'].items() if not passed)+'. '+mass_model['scope'])
    operating=engineering['operating_point']
    if abs(operating['chamber_pressure_deviation_fraction'])>0.01:
        warnings.append('Fixed-hardware unthrottled pressure differs from the requested design point by '
            +format(100*operating['chamber_pressure_deviation_fraction'],'.1f')
            +'%; regulation/throttling must be designed. '+operating['scope'])
    if c['overexpanded']:warnings.append('Overexpanded nozzle: separated flow is possible and is not modeled.')
    if not engineering['analytical_screen_pass']:
        warnings.append('The selected variant fails preliminary analytical checks: '+', '.join(k for k,ok in engineering['checks'].items() if not ok)+'.')
    if not geometry_audit['pass']:
        warnings.append('The geometry route audit fails: '+', '.join(k for k,ok in geometry_audit['checks'].items() if not ok)+'.')
    if b.jacket_pattern!='none':warnings.append('The experimental jacket needs mechanical and manufacturing validation; the mesh audit checks surface continuity only.')
    if flight['target_screen_pass'] is False:warnings.append('The illustrative vertical-flight estimate does not reach the requested apogee.')
    warnings.extend(vehicle_screen.get('warnings',[]))
    result={'kind':'spacecraft' if b.propulsion_family!='rocket_only' else 'rocket','requirements':asdict(b),'candidates':[candidate],
        'alternatives':[{'rank':i+1,'channel_count':v['channel_count'],'channel_radius_mm':v['channel_radius_mm'],'score':v['preliminary_score_lower_is_better'],'screen_pass':v['analytical_screen_pass'],'selected':v is engineering,'failed_checks':[k for k,ok in v['checks'].items() if not ok]} for i,v in enumerate(variants)],
        'assumptions':[('Gas temperature, gamma and gas constant are user assumptions.' if b.propellant_model=='assumed' else 'RocketCEA calculates chamber temperature, gamma and molecular weight for the selected propellants; nozzle flow still assumes constant properties.'),
            'Ideal attached flow; no viscous, divergence or combustion-efficiency losses.',
            'Tank and line sizing, friction loss, bulk coolant temperature, and hoop stress are preliminary steady screens using stated assumptions.',
            'Vehicle flight uses assumed dry mass, diameter and drag coefficient; nozzle pressure thrust varies with the assumed atmosphere while chamber state and mass flow stay fixed. No OpenRocket executable or vehicle file is imported.'],
        'unresolved':['Airbreathing installed performance, unstart and mode-transition operability','Vehicle mass closure, coupled ascent, reentry and thermal protection','Injector atomization, finite-rate mixing and combustion stability','Regulator and valve hardware, cavitation and real-gas transients','Conjugate heat transfer, boiling and verified wall temperature','Tank end caps, joints, fatigue and proof testing','CFD and hot-fire calibration'],
        'warnings':warnings,
        'knowledge':knowledge(),'architecture':'Pressure-fed core + '+b.propulsion_family,'propulsion_family':b.propulsion_family,'vehicle_screen':vehicle_screen,'sources':vehicle_screen['sources']+[SOURCE,engineering['property_source'],
            'https://ntrs.nasa.gov/citations/19730022965','https://ntrs.nasa.gov/citations/20150016316',
            'https://openrocket.info/documentation.html'],
        'calibration':calibration,
        'execution':{'geometry_generator':'vega_geometry_0.5.0_coupled_channel_sizing','requirements':'computed','cea_chemistry':'computed' if b.propellant_model!='assumed' else 'manual_inputs','proptools_cross_check':'computed' if b.propellant_model!='assumed' else 'not_run','ideal_nozzle':'computed','mass_and_pressure_network':'screened','tank_and_feed_sizing':'screened','pressurant_supply':'screened','structural_manufacturing':'screened','variant_ranking':'computed','vehicle_flight':'illustrative_screen','component_scene':'computed','geometry_route_audit':'screen_pass' if geometry_audit['pass'] else 'failed','fuel_passage_layout':'computed' if b.cooling_passages else 'disabled','feed_system_layout':'computed','injector_layout':'two_orifice_screen','rbcc_shared_design_state':'computed' if b.propulsion_family in ('rbcc','ejector_rocket') else 'not_applicable','ideal_mixer_mass_energy':'conditional_closed' if b.propulsion_family in ('rbcc','ejector_rocket') else 'not_applicable','airpath_fluid_stations':'conditional_subsonic_screen' if b.propulsion_family in ('rbcc','ejector_rocket') else 'not_applicable','field_driven_airpath_geometry':'computed' if b.propulsion_family in ('rbcc','ejector_rocket') else 'not_applicable','cycle_architecture':b.propulsion_family,'combined_cycle':'screened_closed_reduced_order' if (vehicle_screen.get('engine_cycle') or {}).get('status')=='screened_closed' else 'conditional_mixer_and_flow_geometry_driver','rbcc_reference_cases':'free_stream_screen' if vehicle_screen.get('rbcc_reference') else 'not_applicable','mission_budget':vehicle_screen['status'],'airframe_envelope':'not_modeled','thermal_hydraulics':b.thermal_model,'calibration':calibration['status'],'picogk':'pending','validation':'not_run'}}
    result['computational_model']=build_model_trace(result)
    return result

def mesh(candidate):
    g=candidate['geometry'];vertices=[];triangles=[];bodies=[];n=96
    # Shared axial stations give each component exactly matching mating faces.
    for index,part in enumerate(g['components']):
        start=len(triangles);base=len(vertices)
        first,last=part.get('profile_indices',[index,index+1])
        stations=g['profile_mm'][first:last+1]
        for z,r in stations:
            for radius in (r,r+g['wall_mm']):
                for j in range(n):
                    a=2*math.pi*j/n;vertices.append([radius*math.cos(a),radius*math.sin(a),z])
        def quad(a,b,c,d):triangles.extend([[base+a,base+b,base+c],[base+a,base+c,base+d]])
        for j in range(n):
            q=(j+1)%n
            quad(j,q,n+q,n+j)
            far=2*n*(len(stations)-1)
            quad(far+j,far+n+j,far+n+q,far+q)
            for k in range(len(stations)-1):
                left=2*n*k;right=left+2*n
                quad(left+j,right+j,right+q,left+q)
                quad(left+n+j,left+n+q,right+n+q,right+n+j)
        bodies.append({'name':part['name'],'component_id':part['id'],'first_triangle':start,'triangle_count':len(triangles)-start,'minimum_feature_mm':g['wall_mm']})
    return {'vertices':vertices,'triangles':triangles,'bodies':bodies,'units':'mm'}
