# Vega — spacecraft mission and rocket-core workbench

Version 0.30 adds a coupled reduced-order combined-cycle closure: captured-air
fuel addition, pressure-loss bookkeeping, combustor heat release, common-nozzle
expansion, and installed net thrust with explicit residual checks. See
[the engine-cycle scope](docs/ENGINE_CYCLE_030.md). The output is an executable
engineering screen and still requires reacting CFD, transient validation, and
hot-fire data before it can be treated as an engine rating.

Version 0.29 adds a single checked CFD volume across all five analytic duct
stages, separate from the adaptive common-nozzle study. It also replaces
stretched support-bar display triangles with segmented, closed surfaces and
caches saved-run summaries for faster workbench startup. See
[the verified five-stage study](docs/MESH_BACKEND_029.md).

Version 0.28 replaces the active bespoke duct mesher with **Gmsh/OpenCASCADE**,
adds **conforming prism/hex CFD volumes**, solution-driven axial adaptation,
OpenFOAM mesh checks and cold-flow solves, and independent CalculiX verification
of the topology-optimized frame. Select **CFD volume · prism + hex** on a newly
generated run to inspect actual cell faces and download solver cases/results.
See [setup, APIs, sources and exact analysis scope](docs/MESH_BACKEND_028.md).
ANSYS Python clients are installed; an ANSYS solver license is still required.

Historical version 0.27 [connected quality-controlled tessellation to actual previews and
exports](docs/LIVE_MESH_027.md), adds native voxel resolution controls, and displays
actual triangle edges and radius-quality heatmaps. **Mesh generation quality
controls** are under the rocket/core settings. Select a newly generated study to
inspect the updated surfaces; older saved studies keep their original geometry.

Version 0.26 adds [geometry-derived vehicle mass, orbital power/battery/radiator
sizing, and conditional inverse propellant sizing](docs/VEHICLE_CEM_026.md).
Under **Vehicle material mass and sizing**, select **Component estimate → mission
mass and size**, then solve a preview or generate a study. The new orbital resource
and vehicle-mass stages expose their assumptions in the model trace. Resource mass,
selected dry mass, diameter proxy and mission/flight inputs are connection-checked.

Version 0.25 fixes a mismatch between analyzed straight frame members and exported
curved wraps, adds a fast solved geometry preview, makes exact-input generation
the default, and adds engineering inspection views and physical-scale locking.
See [repair details and native sensitivity evidence](docs/MESH_REPAIR_025.md).
Whole-spacecraft completion is now reported separately from numerical verification.

Runtime repair (0.24.1): run `powershell -File setup.ps1 -CheckOnly` to check the
active numerical, isolated CAD and native export dependencies. Use
`powershell -File setup.ps1` to install the active Python requirements and rebuild
the bridge. `start.ps1` checks readiness before starting, and `/api/health` now
reports missing dependencies instead of always returning healthy. Restart a running
server after repairing dependencies because readiness is cached per process.
The setup uses existing vendored PicoGK/ShapeKernel sources and initializes the
pinned lattice submodules; it does not replace upstream source trees.

Native component scenes and assembled STL exports now share a validator that
rejects truncated files, nonfinite normals/vertices and incomplete or overlapping
component ranges before publication. The surface acceptance screen also requires
consistent winding and positive signed volume. The viewer rejects empty meshes
and invalid display scales. These repairs improve pipeline integrity; they do
not supply the missing physical models listed in [the CEM scope](docs/EXECUTABLE_CEM.md).

Version 0.20 adds a run-bound [computational engineering model trace](docs/COMPUTATIONAL_ENGINEERING_MODEL.md). The saved run now carries a dependency-ordered record of requirements, equations, units, model assumptions, upstream links, solution outputs, verification checks, PicoGK export audits, and physical-validation status. The studio leads with this model trace and the active run identity; changing geometry-driving inputs marks the displayed result as stale until a new run is generated. A compatibility view builds the same trace from saved result fields when opening earlier runs.

Version 0.19 adds a [ground-structure frame optimizer](docs/FRAME_TOPOLOGY_OPTIMIZATION.md). It uses axial-bar finite elements and a member-volume constraint to size the external support-frame members under stated representative loads. The optimized radii drive the actual Vega Geometry frame mesh and appear in the studio. The gas path and fluid routes remain protected; bending, buckling, thermal stress, joints and real load cases are not solved.

Version 0.18 adds a conditional one-dimensional fluid-dynamics station screen to the connected RBCC/ejector geometry. An explicit mixed total-pressure recovery assumption sizes the mixer and common-nozzle throat; the saved studio run reports subsonic Mach, static pressure and temperature, speed, dynamic pressure, and choking margin at six generated sections. The cold inlet reports air viscosity and a Reynolds-number proxy. Changing recovery changes the exported assembly mesh. The [flow model and its limits](docs/AIRPATH_FLUID_DYNAMICS.md) are documented separately; the recovery is an input, not a solved mixing loss or CFD result.

Version 0.17 makes geometry changes inspectable in the studio. The viewer now opens in solid cutaway mode, fits the visible component bounds, and compares exact exported body triangles with the previously selected study. Changed bodies can be isolated and zoomed. A banner distinguishes unsaved geometry-driving inputs from mission-only inputs such as payload; the latter change calculations but correctly leave the engine mesh unchanged. This fixes a visibility and feedback problem. It does not add new combustion physics or new engine shapes.

The [studio geometry diagnosis](docs/STUDIO_GEOMETRY_DIAGNOSIS.md) records the traced pipeline, sensitivity checks, exact saved-mesh comparisons and remaining physics limitations.

Version 0.16 derives the assembly's propellant-flow edges from the registered ports and routes that also define the PicoGK feed geometry. Each new run saves a system contract checking requirement, rocket-flow, mission-propellant, mixer, route, component and exported-mesh identities. The viewer shows the actual route graph and each selected body's drivers. This verifies software connection across stages; it does not solve the remaining combined-cycle physics or validate an engine.

The [public LEAP 71 geometry reverse study](docs/LEAP71_GEOMETRY_REVERSE_STUDY.md) maps PicoGK, ShapeKernel, lattice and quasi-crystal interfaces to a concrete development sequence for Vega's independent material-and-void geometry layer.

Run `python server.py` and open [the local workbench](http://127.0.0.1:8711/). Version 0.15 added the conditional ideal mixer mass and energy balance above the shared RBCC design state. The calculated mixed stagnation temperature drives the wall and reinforcement fields. Version 0.18 sizes the throats using an assumed recovered mixed pressure with a 5% area margin. This is a geometry constraint, not a solution for mixing pressure loss, combustion or installed thrust. The viewer opens in **Solid assembly** with a cutaway; **Geometry study** remains an orbitable sampled-point view of the saved native assembly. Use **Solid assembly** for opaque STL surfaces and **Interior hardware** to hide duct walls and the support frame. The cutaway control applies to solid view. RBCC, TBCC with a separate orbital rocket, and ejector-rocket selections still contain unresolved atmospheric-cycle physics. Vega does **not** certify a working, safe or manufacturable engine.

The [public-source LEAP 71/Noyron design study](docs/NOYRON_PUBLIC_REVERSE_ENGINEERING.md) compares the published computational-engineering workflow with Vega's current physics, geometry and manufacturing paths, explains why added reference data did not change the mesh, and records the next CEM milestones.

Vega now has a standalone [Vega Geometry library](packages/vega-geometry/README.md): registered component interfaces, deterministic connected route recipes, and an original rectangular duct mesher. A **cold inlet reference** uses NASA normal-shock and isentropic station equations to set internal areas, then creates its mesh directly in Vega Geometry. Changing capture area, aspect ratio or reference length changes that mesh. This cold diffuser is not a solved high-speed inlet or complete spaceplane. Its assumptions, domain limits and primary sources are recorded in [GEOMETRY_SOURCES.md](docs/GEOMETRY_SOURCES.md).

Rocket-core tank placement now supports paired and staggered layouts. Ports move with their components, feed routes regenerate, and the actual route lengths enter the pressure screen before passage ranking. A new feed/return clearance check rejects an obvious cooling bypass. PicoGK remains the backend for those solid assemblies, with upstream attribution intact. Neither the geometry layer nor its new NASA reference establishes physical validation.

The mission panel exposes payload, dry mass excluding payload, target orbit, requested handover Mach/altitude and inlet capture area. **Recalculate mission budget** calls `/api/mission/preview` without meshing; the panel labels this an unsaved calculation and keeps the displayed mesh associated with its saved study. **Generate Vega assembly** saves the mission budget, inputs, engine geometry and execution evidence together. Changing mission inputs can change the budget without changing engine geometry; a different architectural label does not imply a solved different engine.

The budget uses the actual engine mass flow and commanded burn duration for propellant mass, and includes payload in both the rocket-equation calculation and the separate vertical diagnostic. At handover, all rocket propellant is optimistically assumed to remain. It compares ideal vacuum delta-v against a circular-speed gap, with no altitude transfer, gravity/drag/steering losses or Earth rotation. This is a conditional speed comparison, not an ascent trajectory. A positive margin remains **incomplete**, never mission-pass. Unknown airbreathing thrust, mode transition, vehicle mass closure and thermal protection remain explicitly unknown. The default 1 kN, two-second engine with a 1,000 kg payload fails this comparison.

Atmospheric density, pressure and temperature follow the [NASA Glenn educational curve fit](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/earth-atmosphere-equation-metric/), limited here to 0–32 km. Inlet capture is only density × area × speed; it is not net thrust or pressure recovery. The [ideal rocket equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/) supplies the ideal delta-v bookkeeping. Historical fields `airbreathing_isp_s`, `airbreathing_thrust_fraction` and `vehicle_lift_to_drag` are retained for request compatibility but do not drive these calculations.

The native core mesh represents the rocket core and its modeled feed components. A separate combined assembly STL now includes that actual core, five shared duct stages, core mounts, mixer strakes, thermal reinforcement and a branching support frame, with 22 selectable components in the verified example. The fixed-radius tube added as a “lifting body” in the initial spacecraft prototype has been removed: it was not derived from packaging, lift, loads or inlet geometry. The current assembly export is a packaging concept with multiple solids, not a fabrication-qualified vehicle. The interactive subsystem map shows this missing work explicitly. Measured calibration data are still unavailable.

The assembly stage now gives the mixer a convergent and divergent area profile, contracts the isolator slightly, expands the combustor envelope, and shapes a common nozzle throat and exit. Each stage shares its interface with the next. Area ratios remain declared geometry inputs, not a solved combined-cycle prediction. The stage controls show those areas. The assembly stage connects the reference inlet to a core bay, mixer,
isolator, air-combustor envelope and common nozzle. Core positions retain physical
scale; export checks actual core vertices against the bay. Shared interfaces,
flow reachability, frame cycles and surface topology are saved with the mesh.
Use **Connected assembly** for overall placement and **Rocket core detail** for
tanks, feed lines, injector and cooling hardware. Cutaway, group visibility,
component highlighting and isolation use that same saved component scene.

This is still an unvalidated RBCC/ejector packaging model. TBCC assembly
requests explicitly report unsupported until a turbine flowpath and maps exist.
Air-mode fuel staging, mixing, combustion, heat transfer, unstart, installed
net thrust, structural sizing and manufacturing joints remain unresolved.
See [geometry sources and limitations](docs/GEOMETRY_SOURCES.md).

The core analysis chain is: requirements → RocketCEA chamber equilibrium → a documented constant-property nozzle approximation and proptools mass-flow cross-check → pressure-fed mass and pressure network → tank, feed and cooling sizing → a steady thermal and friction balance integrated on the same cooling centerlines passed to PicoGK → structural and manufacturing screens → ranking of three passage variants → one shared component recipe → geometric endpoint and cross-propellant feed-clearance checks → ShapeKernel and PicoGK voxel geometry → sparse native wall-ligament sampling and Trimesh mesh audit → interactive component inspection and STL download. A separate vehicle mission screen integrates the same engine's ideal thrust and mass flow through a one-dimensional vertical flight model. CadQuery and Build123d independently revolve that same recipe's **uncut pressure-shell envelope** and compare volumes; a reference STEP is available. This STEP omits passages and hardware. The combined STL contains the PicoGK bodies with boolean operations applied; the viewer's separate scene retains component colors and selection.

Available geometry includes chamber, convergent, nozzle, ranked swept fuel-wall channels and collectors, external fuel ports, a rib layout, capped pressure-fed tanks sized for the requested burn, sized hollow fuel/oxidizer feed and fuel-return tubes, and a closed injector face with two distinct equivalent outlets. The nozzle can use either a straight cone or a shorter cubic bell generated from the same solved throat and exit areas. The bell is a geometric concept: the ideal performance model does not predict contour losses or a performance gain. Experimental BCC, quasi and Penrose jackets use the corresponding LEAP71 libraries. The default selects a bell contour and Penrose jacket and recuts fluid passages after the bounded jacket union: direct PicoGK testing of the default 1.00 kN brief yielded one watertight outer shell, zero enclosed void shells, clear route endpoints, and 480 sampled radial ligament positions with zero failures. BCC remains selectable; its tested 1.10 kN conical mesh had one watertight outer shell and one enclosed void, while its 1.00 kN conical mesh had tiny detached fragments. The tested conical quasicrystal mesh had 20 enclosed void shells. Both voids and detached shells now fail the mesh-integrity screen. The no-jacket baseline remains available. These are geometric outcomes for specific briefs, not validated topology optimizations or stiffness claims. Tank capacity, pressure budget, ideal-gas pressurant supply, assumed heat-flux wall temperature, combined hoop/thermal stress, channel ligaments and voxel feature size are preliminary screens. The sampled feed/cooling centerlines are unobstructed in the tested studies. These checks do not prove leak-tightness, internal wall thickness throughout or separated propellant circuits before injection. Regulators, valves, atomization, combustion stability, tank end caps, fatigue and manufacture remain unsolved. Do not treat it as fabrication-ready.

The default chemistry is LOX/RP-1 at a user-selected mixture ratio. LOX/LH2 and manual gas-property mode are also available. RocketCEA supplies chamber temperature, molecular weight and gamma when a propellant pair is selected. The nozzle calculation still assumes one-dimensional attached, isentropic flow with those chamber properties held constant. Its ideal thrust and specific impulse exclude viscous, divergence and combustion-efficiency losses. [NASA's rocket thrust relations](https://www.grc.nasa.gov/WWW/K-12/BGP/rktthsum.html) explain the ideal model.

The mission screen is informed by [OpenRocket's technical documentation](https://openrocket.info/documentation.html) and [flight-simulation guidance](https://github.com/openrocket/openrocket/blob/unstable/docs/source/user_guide/basic_flight_simulation.rst). It is Vega's own small model, not an OpenRocket installation or execution. Enter dry vehicle mass including engine, diameter, assumed drag coefficient, launch altitude and optional target apogee. Vega combines those inputs with the selected engine's mass flow and burn duration, integrates vertical motion with gravity and drag, and reports pad thrust-to-weight, vacuum ideal delta-v, burnout state, maximum dynamic pressure and estimated apogee. Its pressure thrust changes with the assumed local ambient pressure, while chamber state and mass flow remain fixed. With a target apogee, Vega also solves for a suggested minimum ideal thrust between 100 and 10,000 N by repeated flight integration; that vehicle-only suggestion must be re-run through the full engine screens and geometry. It uses an exponential atmosphere and a point-mass RK4 integrator. It does not assess 6-DOF stability, winds, thrust transients, nozzle separation or recovery. Without measured vehicle mass, drag and a thrust curve, it cannot predict an actual flight accurately; [OpenRocket's guide](https://github.com/openrocket/openrocket/blob/unstable/docs/source/user_guide/basic_flight_simulation.rst) likewise stresses matching physical component mass and drag.

The native builder uses `vendor/PicoGK`, `vendor/ShapeKernel`, and the pinned LatticeLibrary and QuasiCrystals submodules in `vendor/modules`. Initialize submodules with `git submodule update --init --recursive` and build with `./.tools/dotnet/dotnet.exe build integrations/Vega.Native.csproj -c Release`. The local Python packages live under `.tools/python`; CadQuery and Build123d are isolated in `.tools/cadquery` and `.tools/build123d` because they use different OpenCASCADE bindings. `integrations/reference_cad.py` invokes them in separate processes.

To recreate the local Python setup, install `requirements-physics.txt` and `requirements-engineering.txt` with `python -m pip install --target .tools/python -r <file>`. Install the two reference CAD stacks with `python -m pip install --target .tools/cadquery cadquery==2.8.0` and `python -m pip install --target .tools/build123d build123d==0.13.0`. Keep those target directories separate.

NASA CEA's Python package is installed alongside RocketCEA. RocketCEA is the active chemistry interface. OpenMDAO and Cantera are installed but have no active stage. PyOpenVDB has no matching package for this Windows Python environment, and the research PyMesh project requires a separate native C++ build; PicoGK and Trimesh cover their intended voxel and mesh roles in the current workflow. Installing an alternative kernel alone would not improve the component design.

The feed model uses NASA reference liquid densities and explicitly assumed viscosity, heat capacity, heat flux, wall conductivity, coolant film coefficient, material constants and regulator behavior. Its routed Darcy losses omit fittings, valve flow curves, two-phase flow and real transients; the valve loss is an input. The LOX/LH2 mode now fails its analytical screen when the estimated coolant outlet reaches hydrogen's 32.976 K critical temperature, because its fixed liquid density and heat capacity model no longer covers that state ([NIST hydrogen properties](https://nvlpubs.nist.gov/nistpubs/Legacy/MONO/nbsmonograph168.pdf)). This is a model-domain gate, not a full phase or real-fluid solution. The three alternatives are ranked by a documented heuristic after analytical gates, not by validated engine performance. Independent CEA/proptools comparison verifies part of the software calculation; it does not calibrate the engine. Vega reports `awaiting_measured_data` until exact-design measurements are provided using [the evidence schema](data/evidence/README.md). It will report residuals without changing model parameters from a single test point. [NASA's fluid-cooled chamber monograph](https://ntrs.nasa.gov/citations/19730022965) and [injector design research](https://ntrs.nasa.gov/citations/20150016316) describe why cooling and injector validation require much more than these screens.

Run `python -m unittest discover -s tests`, run the same command from `packages/vega-geometry` for the standalone library, and `node --test tests/test_mesh_worker.cjs` for targeted checks. Generated studies, revision fingerprints, STL and STEP exports are under `data/`. Recipe, requirement or native-binary changes invalidate cached native artifacts. A saved study retains its original calculated recipe; regenerate after Python model changes.
