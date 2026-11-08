# Public-source reverse study: LEAP 71 geometry stack and Vega Geometry

This study inspects the public LEAP 71 repositories already present under
`vendor/` and their published documentation. It derives an architecture for
Vega's own geometry system. It cannot recover Noyron's private engineering
rules from photos or infer performance from visual complexity.

## What the public code establishes

| Layer | Observable implementation | What it actually supplies |
|---|---|---|
| PicoGK | `vendor/PicoGK/Base/Voxels.cs` exposes signed-distance implicits, voxel rendering, Boolean add/subtract/intersect, offsets and smoothing; `Base/Lattice.cs` accumulates nodes and tapered beams. | A small set of geometry operations and a sampled-material representation. It does not decide engine topology or dimensions. |
| ShapeKernel | `vendor/ShapeKernel/ShapeKernel/BaseShapes/BasePipe.cs`, `BaseCylinder.cs`, frames and modulations construct reusable shapes, then render them to PicoGK voxels. | A higher-level shape vocabulary with local coordinates and spatially varying dimensions. |
| LatticeLibrary | `ICellArray`, `ILatticeType` and `IBeamThickness` are separate interfaces in `vendor/modules/LatticeLibrary/LatticeLibrary/`. | Cell placement, beam connectivity and local thickness can vary independently. A pattern still needs a load/thermal/flow reason. |
| QuasiCrystals | `PenrosePattern.cs` and `QuasiCrystal.cs` repeatedly inflate/subdivide typed tiles and deduplicate matches. | Deterministic aperiodic topology generation. It does not establish an engine benefit or validated vibration behavior. |
| Application CEM | LEAP 71 describes Noyron as its proprietary application-specific engineering layer. Its source is not in these repositories. | Physics, requirements, manufacturing and test knowledge must be supplied by Vega's own models. |

Primary sources: [PicoGK](https://github.com/leap71/PicoGK),
[ShapeKernel](https://github.com/leap71/LEAP71_ShapeKernel),
[ShapeKernel technical guide](https://github.com/leap71/LEAP71_ShapeKernel/blob/main/Documentation/README-ReadingDetails.md),
[LatticeLibrary](https://github.com/leap71/LEAP71_LatticeLibrary),
[QuasiCrystals](https://github.com/leap71/LEAP71_QuasiCrystals), and
[LEAP 71's stack description](https://leap71.com/tech/).

## Geometry logic inferred from those interfaces

1. An application model chooses physical components, interfaces and spatial
   fields before it creates a final surface. A chamber wall is therefore a
   function of axial station, local load, cooling and process limits, rather
   than a static tube followed by decorative detail.
2. A shape generator evaluates local frames and modulation functions along a
   path or surface. Examples include a variable-radius pipe, a conformal
   support and a changing channel section. The coordinates and modulation
   fields are independent of final voxel resolution.
3. Solids, voids and structures are combined through material-field
   operations, then discretized and meshed. For negative-inside signed fields,
   the basic constructive forms are `union=min(a,b)`,
   `intersection=max(a,b)`, `subtract=max(a,-b)`, and an outward offset
   `a-d`. These expressions preserve inside/outside classification, but
   Boolean combinations need not remain exact Euclidean distance fields;
   careful sampling or re-distancing may be required.
4. Libraries can generate candidate topology: cell arrays, beam rules and
   inflation rules. The CEM must still decide where a lattice belongs, how
   thick it is, whether it interrupts a fluid path, and whether a process can
   build and inspect it.
5. The material model is tested after meshing: components, channels, minimum
   walls, trapped volumes, connected boundaries and intersections. A clean
   rendering alone is no evidence of those properties.

These are architectural inferences from public code, **not** claims that
Noyron uses exactly this sequence internally or that any pictured engine has
the specific hidden features guessed from its silhouette.

## Where Vega stands after the system-connection milestone

`packages/vega-geometry` has registered ports, deterministic routes, lofted
rectangular/elliptical ducts, field-driven lobed ducts, beams and topology
audits. The application now derives its propellant flow graph from those
registered routes. A saved system contract checks that requirements, physics,
geometry, PicoGK core and exported assembly identities agree. The native
rocket core still uses PicoGK for solid Boolean and voxel operations.

The largest geometry gap is **one material-and-void field representation**
owned by Vega. Today the airpath uses direct triangle lofts, the core uses
PicoGK voxels, and the final assembly is a collection of overlapping closed
bodies. A shared recipe and matching export hashes establish coherence, but
they do not resolve body intersections, channel-wall thickness everywhere,
fluid isolation, material continuity or manufacturable joints. Changing the
mesher alone will not solve the missing physical loads.

## Vega Geometry development contract

The following build order keeps each new geometry capability connected to an
actual engine feature, instead of creating another unused library:

| Order | Vega-owned capability | First engine use | Acceptance evidence |
|---|---|---|---|
| 1 | Typed feature graph for material, void, fluid, heat and load paths; dimensions carry units, bounds and provenance. | One regenerative rocket core with pressure shell, cooling channels, injector and feed routes. | Changing a requirement changes the expected state and geometry fingerprint; every visible body and internal void has a source feature. |
| 2 | Bounded scalar-field primitives, local frames, path sweeps, Boolean operations and offsets. | Recreate one actual cooling circuit and surrounding pressure wall from the same solved centerlines. | Compare bore area, endpoint positions and wall clearance against the current PicoGK result on identical recipes. |
| 3 | Resolution-controlled sparse sampling and surface extraction with deterministic component IDs. | Produce a closed chamber/cooling material mesh without stitching independent overlapping STLs. | Stable hash, convergence with voxel size, manifold/winding checks, connected material and channel volumes. |
| 4 | Conformal cell placement + topology rule + thickness field as separately replaceable interfaces. | Local reinforcement only where a thermal or structural screen requests it. | Variant changes local material and margin; no isolated beams or blocked coolant passage. |
| 5 | Exact route and interface audits, process constraints and field-to-mesh provenance. | Validate a printable core candidate at stated process resolution. | Minimum ligament, powder access, unsupported features, trapped volumes and inspection openings are reported or explicitly unknown. |
| 6 | Backend parity and measured evidence loop. | Run the same recipe through Vega Geometry and PicoGK, then compare against a measured core. | Report dimensions, topology, volume and performance residuals separately; never promote software parity to physical validation. |

The next implementation should be a **single vertical slice**: a bounded,
variable-section cooling passage and its surrounding wall driven by the
existing `vega/engineering.py` thermal/friction state and
`vega/geometry_model.py` registered route. It should export both a material
body and an inspectable fluid-domain body. PicoGK remains the reference backend
until Vega's replacement passes geometry and physical-domain comparisons.

## Design rules for Vega's own implementation

- Keep the original Vega geometry package independent of vendor source and
  record any upstream inspiration or copied code explicitly. The included
  LEAP 71 repositories have Apache-2.0 licenses; attribution and notices stay
  with them. Vega's own package still needs a license selected before public
  release.
- Use millimetres for geometry and SI units for physics at an explicit
  adapter boundary. Reject missing units and nonfinite values before sampling.
- Make media and material/void types explicit. A fuel route must never join an
  oxidizer route upstream of the injector because two contours touch in a mesh.
- Give every field finite bounds, a resolution budget and a stable identity.
  Apply hard feature-size and wall-clearance checks before expensive meshing.
- Treat topology as a requirement: connected fluid paths, sealed material,
  reachable inspection ports and acceptable genus/components must be checked
  after every Boolean or meshing step.
- Track three distinct results: mathematically constructed shape, numerically
  acceptable mesh, and physically supported engine prediction. None implies
  the next.
