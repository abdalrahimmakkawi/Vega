"""Source-traceable RBCC reference cases and free-stream screening."""
from pathlib import Path
import json
import math
from .inlet import normal_shock


_PACK=json.loads((Path(__file__).with_name('rbcc_reference.json')).read_text(encoding='utf-8'))


def reference_pack():
    return _PACK


def evaluate_reference_cases(b, atmosphere_state):
    """Evaluate NASA code-comparison Mach points at one stated Vega altitude.

    This supplies consistent free-stream and ideal normal-shock inputs. It does
    not calculate an airbreathing combustor state, cycle thrust, or test match.
    """
    cases=[]
    for ref in _PACK['cycle_code_cases']:
        mach=ref['mach'];T=atmosphere_state['temperature_k'];p=atmosphere_state['pressure_pa'];rho=atmosphere_state['density_kg_m3']
        velocity=mach*atmosphere_state['speed_of_sound_m_s']
        q=.5*rho*velocity**2
        total_temperature=T*(1+.2*mach**2)
        total_pressure=p*(1+.2*mach**2)**3.5
        shock=normal_shock(mach) if mach>1 else None
        recovery=shock['total_pressure_ratio'] if shock else 1.0
        cases.append({**ref,'evaluation_altitude_m':b.transition_altitude_m,
            'altitude_interpretation':'same user-selected altitude for comparison; not the NASA case altitude',
            'static_temperature_k':T,'static_pressure_pa':p,'density_kg_m3':rho,
            'flight_speed_m_s':velocity,'dynamic_pressure_pa':q,
            'ideal_capture_mass_flow_kg_s':rho*b.inlet_capture_area_m2*velocity,
            'total_temperature_k':total_temperature,'ideal_normal_shock_total_pressure_recovery':recovery,
            'cold_normal_shock_inlet_supported':mach>=1 and total_temperature<=1000,
            'net_thrust_n':None,'status':'free_stream_reference_only'})
    return {'pack':_PACK['name'],'pack_version':_PACK['schema_version'],
        'source_cases':cases,'case_source':_PACK['cycle_case_source'],
        'architecture_source':_PACK['architecture']['source'],
        'mixing_source':_PACK['mixing_model']['source'],
        'validation_source':_PACK['validation_source'],
        'validation_requirements':_PACK['validation_requirements'],
        'limits':_PACK['limits'],
        'status':'reference_data_applied_to_free_stream_screen_only'}


def check_architecture_wiring(assembly):
    """Use the referenced RBCC component sequence as a generation gate."""
    if assembly.get('status')!='concept_assembly':
        return {'status':'not_applicable','reason':assembly.get('reason',assembly.get('status'))}
    expected=_PACK['architecture']['required_geometry']
    present={part['id'] for part in assembly.get('components',[])}
    order=[part['id'] for part in assembly.get('components',[]) if part.get('group')=='shell']
    edges=assembly.get('topology',{}).get('flow',{}).get('edges',[])
    paths={source:any(e[0]=='air_inlet' and e[1]=='mixer' for e in edges) for source in ('air_inlet',)}
    paths['rocket_primary']=any(e==['rocket_core','mixer'] for e in edges)
    paths['common_nozzle']=any(e==['air_combustor','common_nozzle'] for e in edges)
    interfaces=assembly.get('interfaces',[])
    checks={
        'all_reference_stages_present':all(identity in present for identity in expected),
        'reference_stage_order':order[:len(expected)]==expected,
        'all_stage_interfaces_shared':len(interfaces)==len(expected)-1 and all(i['gap_mm']<1e-6 and i['section_mismatch_mm']<1e-6 for i in interfaces),
        'air_path_enters_mixer':paths['air_inlet'],
        'rocket_primary_enters_mixer':paths['rocket_primary'],
        'combustor_connects_to_nozzle':paths['common_nozzle'],
        'core_mount_network_connected':assembly.get('topology',{}).get('mounts',{}).get('connected_components')==1,
    }
    return {'status':'passed' if all(checks.values()) else 'failed',
            'source':_PACK['architecture']['source'],'expected_sequence':expected,
            'generated_sequence':order,'checks':checks,
            'scope':'Source-informed architecture wiring only; no cycle performance or operability validation.'}
