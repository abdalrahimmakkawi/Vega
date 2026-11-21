"""Specialized airflow CEM: requirements -> triangles -> voxels -> checked parts.

This model has no propellant, combustion, thrust or flight-performance solver.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
sys.path.insert(0, str(ROOT / 'packages/vega-geometry'))
from vega_geometry import fingerprint
from vega_geometry.sections import validate_stations, interpolate, contour
from .sabre import BUNDLE_CASING_RADIUS_MM, synthesize
from .cooling import cooling_routes
from .cem import evaluate


def recipe(options=None):
    options = {} if options is None else options
    if not isinstance(options, dict) or set(options) - {'voxel_mm', 'reference_flow_g_s', 'cooling_flow_ml_s', 'centrebody_mm'}:
        raise ValueError('Only the bounded reference airflow sizing case is adjustable')
    pitch = options.get('voxel_mm', 0.2)
    if type(pitch) not in (int, float) or pitch not in (0.2,0.3,0.4,0.7):
        raise ValueError('Supported voxel pitches are 0.2, 0.3, 0.4 and 0.7 mm')
    travel = options.get('centrebody_mm', 0.)
    if type(travel) not in (int, float) or not -4 <= travel <= 4:
        raise ValueError('Centrebody travel must be between -4 and +4 mm')

    def sections(rows):
        return validate_stations([
            dict(z_mm=z, width_mm=2*r, height_mm=2*r, wall_mm=2.4,
                 lobe_amplitude=a, lobe_count=6, twist_rad=0.) for z, r, a in rows])

    flow = options.get('reference_flow_g_s', 4.)
    if type(flow) not in (int, float) or flow not in (3.5, 4., 4.5):
        raise ValueError('Choose a reference airflow of 3.5, 4.0 or 4.5 g/s')
    synthesis = synthesize(flow/1000)
    intake = synthesis['geometry']['intake_inner_radius_mm']
    outer = sections([(0, 23, 0), (14, intake, 0), (20, BUNDLE_CASING_RADIUS_MM, 0), (60, BUNDLE_CASING_RADIUS_MM, 0),
                      (78, 23, .10), (96, 19, .06), (110,17.3,.02), (120,17.2,0)])
    exit_radius=8.5  # Flared non-firing inspection outlet; no thrust optimization.
    # Sample a tangent-continuous contour at the native table spacing. Keep the
    # fixed inspection throat and outlet ratio independent of propulsion studies.
    def smooth(t):
        return t*t*(3-2*t)
    core = sections([(z, 8 if z <= 82 else
        8+(3.5-8)*smooth((z-82)/16) if z <= 98 else
        3.5+(exit_radius-3.5)*smooth((z-98)/22), 0) for z in range(66,121)])
    synthesis['geometry']['nozzle_exit_radius_mm']=exit_radius
    cooling = cooling_routes(core,pitch)
    # Sample the existing Vega section evaluator into the actual native recipe.
    # The native implicit interpolates these identical angular radius tables.
    import numpy as np
    angles = np.arange(120) * 2*np.pi/120

    def sample(stations):
        return [dict(z_mm=float(z), radii_mm=np.linalg.norm(
            contour(interpolate(stations, float(z)), angles)[:, :2], axis=1).tolist())
            for z in np.arange(stations[0]['z_mm'], stations[-1]['z_mm'] + .5, 1.)]

    result = dict(schema_version=7, model='Vega Airflow and Cooling CEM', revision=7, units='mm',
                  architecture=synthesis['architecture'], synthesis=synthesis,
                  cooling=cooling,
                  purpose='SABRE-inspired non-firing architecture and geometry demonstrator',
                  length_mm=120., wall_mm=2.4, voxel_mm=float(pitch),
                  printer=dict(process='FDM', nozzle_mm=.4, materials=['PLA', 'PETG']),
                  outer_sections=outer, core_sections=core,
                  outer=sample(outer), core=sample(core),
                  gyroid_cell_mm=16., gyroid_min_band_mm=1.6,
                  bcc_cell_mm=10., bcc_beam_diameter_mm=2.4)
    result['intake'] = dict(centrebody_mm=float(travel), travel_limits_mm=[-4.,4.],
        profile_z_radius_mm=[[-22,.8],[-6,4.8],[6,8.],[16,8.],[20,2.],[64,2.]],
        guide_inner_radius_mm=2.6, guide_outer_radius_mm=6., guide_z_mm=[48.,62.],
        interpretation='Axisymmetric two-cone intake concept; two shocks are not established by the low-speed CFD case.')
    result['components'] = [
        dict(id='centrebody',name='Movable two-cone centrebody',color=[.66,.70,.76]),
        dict(id='precooler',name='Precooler bundle + He routing',color=[.17,.68,.78]),
        dict(id='air-compressor',name='Air turbo-compressor representation',color=[.49,.53,.70]),
        dict(id='helium-circulator',name='He circulator representation',color=[.75,.57,.22]),
        dict(id='hydrogen-pump',name='Hydrogen pump representation',color=[.72,.36,.27])]
    result['resolution_policy']=dict(full_assembly_voxel_mm=float(pitch),detail_voxel_mm=.01,
        detail_scope='2 mm cube from the first/second cone junction',
        display='Interpolated vertex normals; STL dimensions and voxel pitch unchanged',
        estimated_full_001_triangles=4492676*(.2/.01)**2)
    result['design_changes']=dict(baseline_run='296686f8cc96480db0c46eb695edc896',
        description='Sliding two-cone intake, separate precooler, air compressor, helium circulator and hydrogen pump representations',
        exit_bore_diameter_mm=17.,aft_nacelle_inner_diameter_mm=34.4,
        centrebody_tail_radius_mm=3.,exit_collar_outer_diameter_mm=42.)
    result['nozzle_geometry'] = dict(contour='Sampled cubic smoothstep, tangent-continuous analytic profile',
        throat_z_mm=98., throat_radius_mm=3.5, exit_radius_mm=exit_radius,
        expansion_ratio=(exit_radius/3.5)**2,
        scope='Fixed non-firing inspection geometry; no thrust sizing or performance prediction.')
    result['cem']=evaluate(synthesis,cooling,result['nozzle_geometry'],options.get('cooling_flow_ml_s',40.),pitch)
    result['recipe_sha256'] = fingerprint(result)
    return result


PRINT_GUIDE = '''Vega SABRE Study | non-firing architecture demonstrator | STL units: millimetres

PRINT: half-a.stl and half-b.stl, once each. They are already oriented with
their longitudinal mating planes on the bed. Keep scale at 100%.
FDM starting settings: 0.4 mm nozzle, 0.2 mm layers, PLA or PETG, 4 perimeters,
15-20% infill. Review your slicer's layer preview. Internal curved roofs and
lattice overhangs may need removable supports; support-free printing is NOT
validated. Inspect the accessible channels and remove supports before joining.
Each part fits within 125 x 65 x 35 mm. Nominal main walls are 2.4 mm.

ASSEMBLE: align the flat faces and matching inlet/outlet rims. Use two removable
rubber bands around the smooth collars near the inlet and outlet. There are no
blind fasteners, captive parts, or tolerance-dependent press fits. Leave one half
off for inspection. assembled.stl is an inspection reference, NOT a third part.

TRY: with halves together, use a small unsealed desk fan at the inlet and paper
streamers at the outlet to observe airflow. Inspect the blunted intake centrebody,
enlarged precooler tube bundle, static compressor/support vanes, aft chamber and
nozzle, and surrounding bypass passage. The tubes are solid representations;
they carry no helium. The static vanes do not compress air. The equations describe
an assumed sizing case, not operating conditions of this plastic print.
There is no turbine, fuel system, ignition, heat source or predicted thrust. Do not attach
compressed gas, fuel or combustion hardware. This plastic model is not a
pressure vessel or an operating rocket/jet engine.

CHECKS: report.json records the exact recipe and exported-file hashes, surface
closure, connected bodies, positive volume, dimensions, and sampled open paths.
Those checks do not establish print success, strength, leakage or flow performance.
Next acceptance step: slice, print and inspect this exact model on your printer.
'''


if __name__ == '__main__':
    print(json.dumps(recipe(), indent=2))
