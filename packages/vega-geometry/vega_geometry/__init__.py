"""Vega Geometry: original component-graph and recipe utilities.

Pure Python, millimetres, right-handed coordinates. Does not construct a solid
or certify manufacturability; a separate backend executes the emitted recipe.
"""
from dataclasses import dataclass, asdict
from math import dist, isfinite
import hashlib
import json

__version__ = '0.2.0'


def point(value):
    if len(value) != 3 or any(isinstance(x, bool) or not isfinite(x) for x in value):
        raise ValueError('A point must contain three finite coordinates')
    return tuple(float(x) for x in value)


def centerline_length(points):
    points = [point(p) for p in points]
    if len(points) < 2:
        raise ValueError('A route requires at least two points')
    if any(dist(a, b) < 1e-9 for a, b in zip(points, points[1:])):
        raise ValueError('A route contains a zero-length segment')
    return sum(dist(a, b) for a, b in zip(points, points[1:]))


def fingerprint(recipe):
    """Content identity; independent of timestamps and dictionary insertion order."""
    data = json.dumps(recipe, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Port:
    id: str
    component: str
    medium: str
    position_mm: tuple
    radius_mm: float

    def __post_init__(self):
        object.__setattr__(self, 'position_mm', point(self.position_mm))
        if not self.id or not self.component or not self.medium:
            raise ValueError('Ports need an id, component and medium')
        if isinstance(self.radius_mm, bool) or not isfinite(self.radius_mm) or self.radius_mm <= 0:
            raise ValueError('Port radius must be positive and finite')


class Assembly:
    """Explicit attachment graph; connection checks do not imply solid continuity."""
    def __init__(self):
        self.components = {}
        self.ports = {}
        self.connections = []
        self.routes = {}

    def component(self, identity, kind, drivers=()):
        if identity in self.components:
            raise ValueError('Duplicate component: ' + identity)
        self.components[identity] = {'id': identity, 'kind': kind, 'drivers': list(drivers)}

    def port(self, port):
        if port.component not in self.components or port.id in self.ports:
            raise ValueError('Missing component or duplicate port: ' + port.id)
        self.ports[port.id] = port
        return list(port.position_mm)

    def connect(self, first, second):
        a, b = self.ports[first], self.ports[second]
        if a.component == b.component:
            raise ValueError('Connections join different components')
        if a.medium != b.medium:
            raise ValueError('Connection mixes incompatible media')
        if dist(a.position_mm, b.position_mm) > 1e-6:
            raise ValueError('Disconnected interface: ' + first + ' / ' + second)
        # Bore transitions can have different radii; recording both is intentional.
        self.connections.append({'from': first, 'to': second, 'gap_mm': dist(a.position_mm, b.position_mm)})

    def route(self, identity, name, medium, source, target, waypoints, bore_radius_mm, wall_mm=3):
        a, b = self.ports[source], self.ports[target]
        if a.medium != medium or b.medium != medium:
            raise ValueError('Route medium does not match its interfaces')
        if not isfinite(wall_mm) or wall_mm <= 0:
            raise ValueError('Route wall must be positive')
        incoming = Port(identity+'.in', identity, medium, a.position_mm, bore_radius_mm)
        outgoing = Port(identity+'.out', identity, medium, b.position_mm, bore_radius_mm)
        points = [list(a.position_mm)] + [list(point(p)) for p in waypoints] + [list(b.position_mm)]
        length = centerline_length(points)
        self.component(identity, 'hollow_sweep', ['source_port', 'target_port', 'layout', 'bore_radius'])
        self.port(incoming)
        self.port(outgoing)
        self.connect(source, identity+'.in')
        self.connect(identity+'.out', target)
        recipe = {'id': identity, 'name': name, 'points': points, 'bore_points': points,
                  'bore_radius_mm': bore_radius_mm, 'outer_radius_mm': bore_radius_mm+wall_mm}
        self.routes[identity] = {'centerline_length_mm': length, 'source': source, 'target': target}
        return recipe

    def export(self):
        return {'schema_version': 1, 'generator': 'Vega Geometry', 'version': __version__,
                'units': 'mm', 'components': list(self.components.values()),
                'ports': [asdict(p) for p in self.ports.values()],
                'connections': self.connections, 'routes': self.routes,
                'scope': 'Exact interface coincidence and route construction; not a solid intersection or leak test.'}
