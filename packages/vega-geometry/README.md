# Vega Geometry 0.2.0

An original, dependency-free Python library for component interfaces, connected
route recipes, content fingerprints, and indexed hollow rectangular/elliptical lofts.
It is the beginning of Vega's geometry layer, **not a replacement for a general
solid-modeling kernel**. It contains no copied PicoGK source.

The application uses it in one generation pipeline:

* The pressure-fed reference builds tank/feed/cooling/injector interfaces in an
  `Assembly`. The emitted route and placement data drive the existing PicoGK
  adapter. Feed friction uses those same route centerlines.
* The cold inlet reference supplies flow-station widths and heights to
  `rectangular_duct` or `elliptical_duct`. These produce vertices and triangles directly in Vega
  Geometry, without PicoGK.

* The connected RBCC/ejector assembly uses shared station interfaces for five
  duct stages, embeds the actual PicoGK core at scale 1, and adds core mounting
  struts plus a graph-generated support frame. `beam` produces oriented capped
  solids. `graph_topology` reports components and independent cycles;
  `mesh_topology` checks incidence, winding, vertex links, Euler characteristic
  and genus. These are mathematical checks, not structural optimization.

Mesh topology uses indexed connectivity; it does not weld coincident vertices,
boolean-union overlapping beams or detect geometric self-intersections. Genus
is reported only for closed consistently oriented components. Multi-body exports
are explicitly distinguished from fused manufacturing solids.

Coordinates are right-handed, millimetres, with +Z downstream. Ports carry an
explicit medium, radius and position. A connection requires matching media and
coincident positions within 1e-6 mm; different bore radii are allowed. Routes
reference ports by stable ID, and reject zero-length segments. These checks
establish geometric intent, not fluid isolation or material continuity.

```python
from vega_geometry import Assembly, Port
from vega_geometry.loft import rectangular_duct

assembly = Assembly()
assembly.component("reservoir", "vessel")
assembly.component("sink", "vessel")
assembly.port(Port("supply", "reservoir", "water", (0, 0, 0), 2))
assembly.port(Port("receive", "sink", "water", (20, 0, 10), 2))
recipe = assembly.route("line", "Water line", "water",
                        "supply", "receive", [(20, 0, 0)], 2)
graph = assembly.export()

mesh = rectangular_duct([
    {"z_mm": 0, "width_mm": 100, "height_mm": 50},
    {"z_mm": 200, "width_mm": 120, "height_mm": 60},
], wall_mm=3)
```

`rectangular_duct` takes strictly increasing axial stations with positive inner
dimensions. It connects corresponding corners with triangles and closes the
material at the end rims while leaving the central flow opening clear. It
supports neither arbitrary cross sections nor booleans, fillets, adaptive
voxels, toleranced CAD or manufacturing qualification.

`elliptical_duct` accepts the same station format and an optional `segments`
resolution (default 96). It expands the outer semi-axes by the wall input;
this is not a constant normal offset. Its cross section is a polygonal ellipse.
The application accounts for the polygon area when sizing fluid stations.

Run tests from this directory with `python -m unittest discover -s tests`.
Install locally with `python -m pip install .`. Only `vega_geometry` is packaged;
the app, generated hardware, native binaries and third-party libraries are not.

See [PUBLICATION.md](PUBLICATION.md) before publishing.
