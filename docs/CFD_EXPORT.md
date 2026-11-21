# CFD case export

Each new checked Vega build now emits three files. `cfd-case.json` is the
solver-neutral manifest. `fluent-case.json` is the same manifest labeled for
ANSYS Fluent. `openfoam-case.zip` contains a minimal case skeleton and the
manifest.

The exporter carries the exact recipe hash, component STL inventory, four
declared air regions, port IDs, units, sea-level static target conditions, and
the 11,000 N full-size concept requirement. It also preserves the unresolved
input count and names the gates needed before a solver run.

The package is deliberately marked `case-definition-only` until Vega can create
watertight fluid volumes and name the inlet, outlet, wall, interface, and
symmetry patches. Assembly STLs describe solid boundaries. They are not a CFD
fluid mesh. Fluent and OpenFOAM setup must reject the package if
`solver_ready` is false.

Exporting a case does not modify the CAD/STL design. A visible flow field only
appears after a solver has a watertight fluid domain, named patches and valid
boundary data. The manifest reports this explicitly as `simulation.status:
not-run`; solved fields must be checked before feeding any sizing change back
into the geometry recipe.

The OpenFOAM skeleton uses a steady pressure-based RANS placeholder with
k-omega SST and room-temperature air transport properties. These are setup
defaults for later review, not validated physics. The Fluent file is a
structured input manifest rather than a Fluent journal or solver result.

The CATIA exchange layer remains separate. It should be added after port and
mating interfaces stabilize, with a B-rep or STEP/AP242 writer. Exporting the
current STL as STEP would preserve tessellation rather than parametric design
intent.
