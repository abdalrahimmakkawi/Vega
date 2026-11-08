"""One continuous unobstructed CFD domain across Vega's five duct stages."""
from math import isclose
from .hybrid import build_hybrid


def connected_stations(assembly):
    sections = assembly['sections']
    if len(sections) != 5 or any(len(stage) < 2 for stage in sections):
        raise ValueError('Five duct stages with two or more stations are required')
    stations = list(sections[0])
    interfaces = []
    for stage in sections[1:]:
        a, b = stations[-1], stage[0]
        for key in ('z_mm', 'width_mm', 'height_mm', 'wall_mm',
                    'lobe_amplitude', 'twist_rad'):
            if not isclose(a[key], b[key], rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError('Duct stage interface mismatch: ' + key)
        if a['lobe_amplitude'] and a['lobe_count'] != b['lobe_count']:
            raise ValueError('Duct harmonic discontinuity at interface')
        interfaces.append(a['z_mm'])
        stations.extend(stage[1:])
    return stations, interfaces


def build_airpath(assembly, edge_mm=None, max_cells=300000):
    stations, interfaces = connected_stations(assembly)
    span = stations[-1]['z_mm'] - stations[0]['z_mm']
    edge = max(span / 128, edge_mm or 0)
    mesh = build_hybrid(stations, edge, max_cells=max_cells)
    mesh.summary['domain'] = 'five_connected_ducts_unobstructed_cold_flow'
    mesh.summary['interfaces_z_mm'] = interfaces
    mesh.summary['scope'] = ('Five connected analytic duct passages. Embedded PicoGK rocket, '
        'mixer strakes, wall heat transfer, combustion and mode transition are excluded.')
    return mesh, stations
