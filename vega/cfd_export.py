"""Export a solver-ready manifest without pretending the mesh is solved."""
import json
import zipfile
from pathlib import Path


REGION_SOLVERS = {
    'main-air': {'fluid': 'air', 'solver': 'pressure-based steady RANS', 'turbulence': 'kOmegaSST'},
    'bypass-air': {'fluid': 'air', 'solver': 'pressure-based steady RANS', 'turbulence': 'kOmegaSST'},
    'exchanger-cooling': {'fluid': 'air', 'solver': 'pressure-based steady RANS', 'turbulence': 'kOmegaSST'},
    'jacket-cooling': {'fluid': 'air', 'solver': 'pressure-based steady RANS', 'turbulence': 'kOmegaSST'},
}


def _boundary_conditions(model, target):
    point = target['operating_point']
    return {
        'main-air': {'inlet': {'type': 'mass-flow-inlet', 'mass_flow_kg_s': model['circuits'][0].get('boundary_conditions', {}).get('inlet_mass_flow_kg_s'), 'temperature_k': point['ambient_temperature_k']},
                     'outlet': {'type': 'pressure-outlet', 'static_pressure_pa': point['ambient_pressure_pa']}},
        'bypass-air': {'inlet': {'type': 'mass-flow-inlet', 'mass_flow_kg_s': None}, 'outlet': {'type': 'pressure-outlet', 'static_pressure_pa': point['ambient_pressure_pa']}},
        'exchanger-cooling': {'inlet': {'type': 'mass-flow-inlet', 'mass_flow_kg_s': None, 'temperature_k': point['ambient_temperature_k']}, 'outlet': {'type': 'pressure-outlet', 'static_pressure_pa': point['ambient_pressure_pa']}},
        'jacket-cooling': {'inlet': {'type': 'mass-flow-inlet', 'mass_flow_kg_s': None, 'temperature_k': point['ambient_temperature_k']}, 'outlet': {'type': 'pressure-outlet', 'static_pressure_pa': point['ambient_pressure_pa']}},
    }


def export_case(folder, report, network):
    folder = Path(folder)
    target = network['concept_requirement']
    model = network['model']
    validation = network['validation']
    regions = []
    for circuit in model['circuits']:
        spec = REGION_SOLVERS[circuit['id']]
        regions.append(dict(id=circuit['id'], fluid=spec['fluid'], solver=spec['solver'], turbulence=spec['turbulence'], source=circuit['requirement']))
    geometry = []
    for body in report.get('bodies', []):
        identity = body['component_id']
        path = identity + '.stl'
        geometry.append(dict(component_id=identity, file=path, units='mm', role='solid boundary'))
    manifest = {
        'schema_version': 1,
        'source_report_sha256': network['source_recipe_sha256'],
        'source_run': report.get('base_run'),
        'units': {'geometry': 'mm', 'pressure': 'Pa', 'temperature': 'K', 'mass_flow': 'kg/s'},
        'status': 'case-definition-only',
        'solver_ready': False,
        'simulation': {'status': 'not-run', 'result_visible': False,
                       'reason': 'This export contains solid assembly surfaces and a setup skeleton; no OpenFOAM solve has run.'},
        'reason': 'Fluid volumes, wall boundaries, unresolved port data, and pressure-loss inputs are incomplete.',
        'target': target,
        'regions': regions,
        'geometry': geometry,
        'boundary_conditions': _boundary_conditions(model, target),
        'port_ids': [p['id'] for p in model['ports']],
        'validation': {'topology_valid': validation['topology_valid'], 'geometry_verified': validation['geometry_verified'], 'missing_input_count': len(validation['missing_data'])},
        'next_gates': ['Create watertight fluid-domain volumes per region.', 'Name inlet, outlet, wall, interface and symmetry patches.', 'Supply missing mass flows, loss models and thermal properties.', 'Run mesh independence and residual checks.', 'Compare pressure, heat and mass balances against Vega.'],
    }
    (folder/'cfd-case.json').write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding='utf-8')
    (folder/'fluent-case.json').write_text(json.dumps(dict(format='ANSYS Fluent setup manifest', **manifest), indent=2, allow_nan=False), encoding='utf-8')
    openfoam = folder/'openfoam-case'; (openfoam/'system').mkdir(parents=True, exist_ok=True); (openfoam/'constant').mkdir(exist_ok=True)
    (openfoam/'README.md').write_text('# Vega OpenFOAM case\n\nThis case definition awaits fluid-domain extraction and named patch meshing. The STL files are solid assembly surfaces, not a ready fluid mesh.\n\nUse `cfd-case.json` as the source for regions, ports, units, boundary conditions, and acceptance gates.\n', encoding='utf-8')
    (openfoam/'system/controlDict').write_text('application simpleFoam;\nstartFrom latestTime;\nwriteInterval 500;\n', encoding='utf-8')
    (openfoam/'constant/transportProperties').write_text('FoamFile { version 2.0; format ascii; class dictionary; object transportProperties; }\nnu [0 2 -1 0 0 0 0] 1.5e-05;\n', encoding='utf-8')
    archive = folder/'openfoam-case.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in openfoam.rglob('*'):
            if path.is_file(): z.write(path, path.relative_to(folder).as_posix())
        z.write(folder/'cfd-case.json', 'cfd-case.json')
    for path in sorted(openfoam.rglob('*'), reverse=True):
        if path.is_file(): path.unlink()
        elif path.is_dir(): path.rmdir()
    return manifest
