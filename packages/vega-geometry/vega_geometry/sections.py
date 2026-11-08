"""Analytic cross-sections shared by CAD, surface meshing and CFD volumes.

Coordinates are mm. Elliptic lobes use sqrt(1+A^2/2) normalization to preserve
the section's reference area. Wall offsets expand the semi-axes; they are not
constant-normal-distance offsets. Rectangular corners remain explicit features.
"""
import math
import numpy as np


def validate_stations(stations):
    stations = [dict(s) for s in stations]
    if len(stations) < 2:
        raise ValueError('At least two cross-sections are required')
    previous = -math.inf
    for s in stations:
        for key, default in (('lobe_amplitude', 0.), ('lobe_count', 1), ('twist_rad', 0.)):
            s.setdefault(key, default)
        values = [s[k] for k in ('z_mm', 'width_mm', 'height_mm', 'wall_mm',
                                'lobe_amplitude', 'lobe_count', 'twist_rad')]
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Nonfinite section data')
        if s['z_mm'] <= previous or min(s['width_mm'], s['height_mm'], s['wall_mm']) <= 0:
            raise ValueError('Sections must have positive dimensions and increasing axial positions')
        if not 0 <= s['lobe_amplitude'] <= .25 or not 1 <= s['lobe_count'] <= 24 or int(s['lobe_count']) != s['lobe_count']:
            raise ValueError('Unsupported lobe field')
        previous = s['z_mm']
    return stations


def contour(station, angles, extra_mm=0., section='elliptical'):
    a = np.asarray(angles, float)
    c, s = np.cos(a), np.sin(a)
    w, h = station['width_mm']/2+extra_mm, station['height_mm']/2+extra_mm
    if section == 'rectangular':
        radius = 1/np.maximum(abs(c), abs(s))
    elif section == 'elliptical':
        amp = station.get('lobe_amplitude', 0.)
        radius = (1+amp*np.cos(station.get('lobe_count', 1)*a+station.get('twist_rad', 0.)))/math.sqrt(1+amp*amp/2)
    else:
        raise ValueError('Unsupported cross-section')
    return np.column_stack((w*radius*c, h*radius*s, np.full(a.shape, station['z_mm'])))


def interpolate(stations, z):
    """Piecewise-linear parameter interpolation, preserving supplied stations."""
    levels = [s['z_mm'] for s in stations]
    i = min(max(int(np.searchsorted(levels, z, side='right'))-1, 0), len(stations)-2)
    a, b = stations[i:i+2]
    t = (z-a['z_mm'])/(b['z_mm']-a['z_mm'])
    if not -1e-10 <= t <= 1+1e-10:
        raise ValueError('Axial coordinate outside geometry')
    if a['lobe_amplitude'] and b['lobe_amplitude'] and a['lobe_count'] != b['lobe_count']:
        raise ValueError('Nonzero lobe harmonic changes are not continuous')
    count = b['lobe_count'] if not a['lobe_amplitude'] else a['lobe_count']
    return {**a, 'lobe_count': count, **{k: (1-t)*a[k]+t*b[k] for k in
            ('z_mm', 'width_mm', 'height_mm', 'wall_mm', 'lobe_amplitude', 'twist_rad')}}
