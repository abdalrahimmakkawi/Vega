# Vega specialized airflow and cooling CEM

This model designs a **non-firing airflow and cooling inspection demonstrator**.
It retains the SABRE-inspired arrangement as a geometric reference. New builds
do not execute the archived combustion, thrust or flight-transition studies.

## Executable chain

1. `vega/demonstrator.py` accepts 3.5, 4.0 or 4.5 g/s reference airflow,
   5–60 mL/s channel-network reference airflow, and 0.7 mm voxel pitch by default (0.4 mm remains available).
2. `vega/sabre.py` sizes the intake and tests reference tube bundles plus a length derived from the required area for each tube count.
   Its 330 → 305 K / 293 K sink case is a hypothetical surface-area screen;
   the actual printed tubes are solid, with no predicted exchanger performance.
3. `vega/cooling.py` searches twelve channel layouts and checks branch/collector/
   access-port junction proximity against the actual polylines.
4. `vega/cem.py` derives resistance from every branch's length and radius, solves
   parallel flow splitting, and checks conservation and laminar applicability.
5. `vega/input_mesh.py` builds closed, consistently wound triangular nacelle and
   core shells. It reloads the written `input-body.stl` to verify both solids.
6. `integrations/Demonstrator.cs` loads that STL into `PicoGK.Mesh` and calls
   `new Voxels(inputMesh)`. Only then are implicit gyroid features, lattice
   supports, unions and channel subtractions applied. Auxiliary features remain
   implicit/lattice constructions; the primary nacelle and core are mesh-first.
7. `vega/print_export.py` checks native conversion counts, input hashes, sampled
   clearance, closed connected outputs and print envelope before publication.

The exported kit includes the input triangular mesh, input audit, recipe,
specialized `cem.json`, final STLs and acceptance report. Analysis and acceptance
have separate content hashes. Native library/binary and STL identities remain in
the report. Older runs are preserved and visibly identified as legacy studies.

## Hydraulic model and limits

Physics uses SI units, geometry millimetres, and the UI mL/s. For each branch,
`R = 8 μ L / (π r⁴)`; for ideal equipressure collectors,
`1/R_eq = Σ 1/R_i`, `Δp = Q_total R_eq`, and `Q_i = Δp/R_i`.
Reference air properties are assumed: density 1.2 kg/m³, viscosity 1.8e-5 Pa·s,
and cp 1005 J/(kg·K). Reynolds number and estimated entrance length are reported.
The [Ansys Poiseuille verification case](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/fbu_vm/Hlp_VMFL005.html)
documents the fully developed circular-pipe analytical benchmark.

Curved channels are replaced by straight pipes of equal length. Entrance,
curvature, port/collector losses, surface roughness and seam leakage are omitted.
An unresolved entrance-length check is retained rather than hidden. The estimate
is not total assembly pressure loss or a solved fan operating point.
Heat-capacity rate `ρ Q cp` is reported in W/K; actual cooling duty is unknown.
The outlet area ratio is fixed at 1.5 for inspection, not selected for thrust.

## Evidence gates

Checks carry `passed`, `failed`, `pending`, or `unresolved` plus an evidence path.
Mesh-dependent checks are pending during analysis and resolved only after the
native build. A failed computational gate blocks publication. Physical airflow,
sealing and thermal validation remain unresolved regardless of mesh success.

Physical validation needs a printed-part inspection, measured flow/pressure loss,
seam-leakage assessment, and a separately specified thermal experiment with
material properties. Room-temperature, unsealed fan exploration remains the
current use. No functional heat exchanger, pressure vessel or engine is claimed.

## Verification

Run `python -m unittest discover -s tests` and
`node --test tests/test_renderer.cjs tests/test_mesh_worker.cjs`.
Tests cover analytical resistance/scaling, unequal branch splitting, invalid
inputs, topology/volume/winding, dependency order and rejection of missing native
conversion evidence. Native build acceptance exercises the entire mesh-first path.

## Boolean operations

- **Add** forms the union: material present in either voxel field.
- **Subtract** retains the first field except material present in the second.
- **Intersect** retains only material present in both fields.

These are fundamental modeling operations. Every native build runs all three on
known overlapping cubes, checks 15 interior/exterior probes, and records model
operation counts. Every production Boolean passes through an audited dispatcher;
a kernel exception aborts the build. Native passage/wall sampling and exported
mesh checks independently inspect the result. Publication requires successful
reference checks and execution of all three operation types.

This is a fail-closed workflow, not a mathematical promise that arbitrary Boolean
inputs or native libraries can never fail. Reference probes and mesh topology do
not prove every voxel correct. Failed runs remain diagnostic artifacts and cannot
be downloaded as accepted parts.

The requested 0.7 mm pitch is coarser than 0.4 mm. All native and exported-part
acceptance checks still run; changing resolution does not waive clearance gates.

At 0.7 mm, nominal channel bores grow from 1.6 to 2.1 mm (three voxels),
with 1.2 mm nominal tube walls and adjusted centerlines. The BCC backing extends to radius 28.8 mm
at the coarse pitch, leaving shallow lattice relief instead of fragile open tips.
These are geometry changes, not cleanup exemptions; detached material still fails.

## Mesh redesign revision 6

Default pitch is now 0.3 mm; 0.4 and 0.7 mm remain selectable. The actual
mesh has a 17 mm flared outlet bore, a tapered aft nacelle (34.4 mm inner
diameter at the exit), a 42 mm exit collar and a centrebody tapering to
3 mm radius. Cooling routes are recomputed on the revised core. These are
inspection geometry choices, not a demonstrated aerodynamic improvement.
The viewer can load the previous checked mesh for a same-angle comparison.

## 0.2 mm resolution

The default voxel pitch is now 0.2 mm; 0.3, 0.4 and 0.7 mm remain available.
The revision 6 shape and nominal 1.6 mm cooling bores are retained at 0.2 mm.
The gyroid backing land extends to 26.2 mm radius to remove enclosed slivers
at its casing connection observed at the finer resolution.
The viewer and export triangle limit is six million, with a 60-second mesh
loading timeout and a 600-second native generation timeout. Geometry, Boolean
and cooling-clearance acceptance gates remain mandatory.
Print orientation exports quantize to STL's float32 precision before removing
exactly zero-area faces; removals are recorded and the saved file is rechecked.
Topology validation counts face-connected components without retaining duplicate
surface meshes, keeping the finer-resolution build within the local memory budget.

## Systems assembly revision 7

The review scene adds separately selectable and downloadable components:
movable two-cone centrebody, precooler bundle with represented He routing,
helium circulator, hydrogen pump and static air turbo-compressor. The two casing
halves remain the print orientations. Other components are exported in assembly
coordinates; their printing, attachment, fits and mechanical operation are not
validated. The pump bodies and represented pipes are solid architecture models.

The centrebody has a 4 mm diameter stem and a 5.2 mm guide bore. Its viewer travel
is -4 to +4 mm; Generate saves a selected position in a new recipe and STL.
Live motion is a visual kinematic preview, not a contact or actuation solution.
The inlet is a two-cone axisymmetric concept; neither two-shock performance nor
shock-on-lip conditions are established.

With the user's selected resolution policy, the full assembly remains at 0.2 mm.
Interpolated normals smooth its display without changing checked STL dimensions.
A separate 2 mm cube at the first/second cone junction is evaluated by PicoGK
at an actual 0.01 mm voxel pitch and exported as intake-detail.stl. Its crop
boundaries are artificial. A full 0.01 mm model is not generated.

analysis.json contains actual numerical solutions tied to the recipe hash:

- CFD: axisymmetric potential flow in the intake meridional passage, finite
  volumes, 1.0/0.5 mm grid comparison, flux conservation and linear residuals.
  Incompressible and inviscid with slip walls; excludes shocks, viscosity,
  turbulence, exchanger tubes, rotating machinery and heat transfer.
- FEA: cubic Hermite Euler-Bernoulli beam elements for a 0.1 N transverse tip
  load, fixed at z=48 mm, using the centrebody's varying circular sections.
  E=2 GPa is an assumption; guide contact, print anisotropy, local stress and
  full-assembly strength are not solved. Two meshes report deflection sensitivity.

The CFD uniform-annulus test checks analytic velocity and mass conservation;
the FEA uniform-cantilever test checks analytic deflection, force and moment.
Run CFD + FEA recomputes the selected travel without claiming that the saved
STL changed. Generate saves the geometry and analysis together.

Primary references: [NASA potential flow/Bernoulli](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/bernoullis-equation-1/),
[TU Delft beam elements](https://teachbooks.tudelft.nl/computational-modelling/structural_linear/euler_bernouilli.html),
[NASA axisymmetric inlet concepts](https://ntrs.nasa.gov/api/citations/20240008586/downloads/TM-20240008586.pdf).

## Expanded architecture revision 8

Ten new or upgraded modules use genuine 0.1 mm PicoGK voxels: pre-burner,
re-heater, drive turbine, paired regenerators, open-sector heat shield, bell
nozzle with thrust-chamber representation, spill-duct ramjet burner, LOX pump,
spill duct and the upgraded air turbo-compressor. Each module begins as closed
triangular annular input meshes before voxelization and implicit/Boolean additions.
The original accepted casing and accessories retain their 0.2 mm resolution.

The arrangement is expanded for inspection. Component attachments, connections,
combustion, cryogenic systems, power transfer, thermal protection and operating
performance are not established. The existing potential-flow CFD and beam FEA
remain limited to the intake and centrebody; they do not analyze the new modules.

Full-resolution component STLs are checked for closed surfaces, winding,
connectivity and positive volume. Display meshes may be simplified; failed
topology checks retain the full mesh. The casing keeps its original detail.
Native and display triangle counts are recorded separately. File hashes preserve
traceability to the accepted base. Unchanged artifacts are linked without
modifying their contents. Native STL export now streams triangles to reduce
memory use at fine resolution.

Anatomy references A13–A21 identify the additions. A04 remains the compressor
reference, now at 0.1 mm. Module resolution, inherited resolution and display
simplification are identified in the viewer and recipe.
