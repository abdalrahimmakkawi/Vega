"""Source-traceable cold-flow reference, not a functioning combined-cycle inlet.

Calorically perfect gas; a normal shock at capture followed by an ideal
subsonic diffuser. This deliberately does NOT stand in for a scramjet inlet.
"""
import math
from .geometry_model import fingerprint  # also locates standalone package
from .airpath_flow import air_viscosity_pa_s, VISCOSITY_SOURCE
from .meshing.cad import cad_duct

SOURCES = [
    'https://www.grc.nasa.gov/www/k-12/airplane/normal.html',
    'https://www.grc.nasa.gov/www/k-12/airplane/isentrop.html',
    'https://www.grc.nasa.gov/www/BGH/ramth.html',
    'https://ntrs.nasa.gov/citations/20100024370',
    VISCOSITY_SOURCE,
]
GAMMA, R = 1.4, 286.9


def normal_shock(mach, gamma=GAMMA):
    if not math.isfinite(mach) or mach<1 or not math.isfinite(gamma) or gamma<=1:
        raise ValueError('Normal shock requires upstream Mach >= 1 and gamma > 1')
    m2=mach*mach
    density=(gamma+1)*m2/((gamma-1)*m2+2)
    pressure=(2*gamma*m2-(gamma-1))/(gamma+1)
    return {'mach':math.sqrt(((gamma-1)*m2+2)/(2*gamma*m2-(gamma-1))),
            'density_ratio':density,'pressure_ratio':pressure,'temperature_ratio':pressure/density,
            'total_pressure_ratio':density**(gamma/(gamma-1))*((gamma+1)/(2*gamma*m2-(gamma-1)))**(1/(gamma-1))}


def mass_flux(mach, total_pressure_pa, total_temperature_k):
    """kg/(m² s); NASA isentropic density × speed relation."""
    if any(not math.isfinite(v) or v<=0 for v in (mach,total_pressure_pa,total_temperature_k)):
        raise ValueError('Mass flux requires positive finite inputs')
    return (total_pressure_pa/math.sqrt(total_temperature_k)*math.sqrt(GAMMA/R)*mach
            *(1+(GAMMA-1)*mach*mach/2)**(-(GAMMA+1)/(2*(GAMMA-1))))


def inlet_reference(b, transition):
    if transition is None:
        return None
    air=transition
    total_temperature=air['temperature_k']*(1+.2*air['mach']**2)
    common={'name':'Cold normal-shock diffuser reference','sources':SOURCES,
            'scope':'Area continuity and ideal station states only. Not a scramjet inlet, installed inlet design, or solved RBCC/TBCC cycle.',
            'net_thrust_n':None,'total_temperature_k':total_temperature,
            'assumptions':['Full capture; no spillage, bleed, friction or boundary-layer displacement.',
                           'Normal shock at the inlet plane; constant gamma=1.4 and R=286.9 J/(kg K).',
                           'Exit Mach is the lesser of 0.3 and 80% of post-shock Mach.',
                           'Length, aspect ratio and wall thickness are geometry inputs, not aerodynamic optimizations.']}
    # Explicit implementation domain, not a universal physical validity cutoff.
    if total_temperature>1000:
        return {**common,'status':'outside_reference_domain',
                'reason':'Total temperature exceeds the chosen 1000 K constant-property screening limit. Variable-cp flow is required.',
                'mesh':None}
    shock=normal_shock(air['mach'])
    pt=air['pressure_pa']*(1+.2*air['mach']**2)**3.5*shock['total_pressure_ratio']
    mdot=air['ideal_capture_mass_flow_kg_s']
    exit_mach=min(.3,.8*shock['mach'])
    stations=[]
    # The geometry is now CAD-based: use analytic area, independent of mesh density.
    coefficient=1 if b.inlet_section=='rectangular' else math.pi/4
    for index in range(17):
        t=index/16
        # Smooth station-Mach interpolation is an explicit geometric choice.
        blend=t*t*(3-2*t)
        mach=shock['mach']+(exit_mach-shock['mach'])*blend
        factor=1+.2*mach*mach
        temperature=total_temperature/factor
        pressure=pt/factor**3.5
        density=pressure/(R*temperature)
        velocity=mach*math.sqrt(GAMMA*R*temperature)
        viscosity=air_viscosity_pa_s(temperature)
        area=mdot/mass_flux(mach,pt,total_temperature)
        width=math.sqrt(area*b.inlet_aspect_ratio/coefficient)
        height=width/b.inlet_aspect_ratio
        hydraulic_diameter=2*width*height/(width+height)
        stations.append({'z_mm':t*b.inlet_length_m*1000,'width_mm':width*1000,'height_mm':height*1000,
                         'area_m2':area,'mach':mach,'temperature_k':temperature,'pressure_pa':pressure,
                         'density_kg_m3':density,'velocity_m_s':velocity,
                         'dynamic_pressure_pa':density*velocity*velocity/2,
                         'air_viscosity_pa_s':viscosity,
                         'hydraulic_diameter_proxy_m':hydraulic_diameter,
                         'reynolds_hydraulic_proxy':density*velocity*hydraulic_diameter/viscosity,
                         'mass_flow_kg_s':density*velocity*area})
    surface=cad_duct([{**s,'wall_mm':b.inlet_wall_mm} for s in stations],
                     b.mesh_surface_edge_mm,b.mesh_chord_tolerance_mm,b.inlet_section)
    dimensions={'length_mm':b.inlet_length_m*1000,
                'diameter_mm':max(math.hypot(s['width_mm']+2*b.inlet_wall_mm,s['height_mm']+2*b.inlet_wall_mm) for s in stations)}
    residual=max(abs(s['mass_flow_kg_s']-mdot)/mdot for s in stations)
    return {**common,'status':'ideal_reference_only','shock':shock,'stations':stations,
            'mass_flow_kg_s':mdot,'relative_mass_residual':residual,'mesh':surface,'dimensions':dimensions,
            'geometry_sha256':fingerprint(surface),'section':b.inlet_section,'backend':'Vega Geometry / Gmsh OpenCASCADE',
            'equations':['Tt/T = 1 + (gamma−1)M²/2','pt/p = (Tt/T)^(gamma/(gamma−1))',
                         'Mass flow = density × speed × area',
                         'Net thrust = exit mass flow × exit speed − capture mass flow × flight speed + pressure thrust (not evaluated)']}
