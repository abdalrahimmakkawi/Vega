# Vega — Specialized airflow and cooling CEM

Vega builds a non-firing airflow and cooling demonstrator with a SABRE-inspired
arrangement. The active model evaluates bounded sizing requirements, routed
channel resistance and geometry acceptance. It does not run combustion, thrust
or flight-transition calculations. Earlier study modules remain available as
historical research, separate from new builds.

**Geometry pipeline: closed triangular meshes → PicoGK voxels → implicit features
and Boolean operations → checked STL parts.** Primary nacelle and core shells are
triangulated and validated before voxelization. Gyroid and lattice features are
then added and cooling passages subtracted. The two print halves are intersections
with half-spaces. Each native build tests Add, Subtract and Intersect against known
occupancy results; any failure prevents publication.

The model produces a 120 × 60 mm, two-part FDM inspection assembly. Start with
[the specialized CEM specification](docs/SPECIALIZED_CEM.md) for equations, units,
assumptions, dependency stages, evidence gates and physical validation limits.
Each new print kit includes `cem.json`, the triangular `input-body.stl`, its audit,
the recipe, final STLs and the acceptance report.

## Computational model

The [component and port requirements](docs/COMPONENT_NETWORK.md) now separate
main air, bypass air and two cooling circuits from the inspection manifold.
Each checked run exposes its proposed port graph, automatic connectivity check,
and missing engineering data in the UI. This is the foundation for whole-system
sizing; it is not evidence of open physical passages or a solved engine cycle.

New builds also emit a solver-neutral [CFD case definition](docs/CFD_EXPORT.md)
for OpenFOAM and Fluent. The exporter carries ports, regions, units, boundary
conditions, hashes and the 11 kN target, then stops at a gated case manifest
until fluid volumes and missing engineering inputs are complete.

`vega/sabre.py` owns the architecture and bounded synthesis. The low-speed
reference case assumes 3.5, 4.0 or 4.5 g/s airflow, 101325 Pa, 330 K inlet air,
305 K cooled air, and an isothermal 293 K coolant sink. U = 1000 W/(m² K),
compressor pressure ratio 1.05, efficiency 0.78, cp = 1005 J/(kg K) and gamma = 1.4
are declared assumptions, not measured performance or SABRE operating data.

- Continuity A = mass_flow/(density × velocity), with ideal-gas density and an
  assumed 3 m/s reference velocity, sizes the annular intake at the 8 mm hub.
- Q = mass_flow × cp × (Tin − Tout) and A = Q/(U × LMTD) set an exchange-area target.
  The LMTD calculation assumes a constant-temperature sink and neglects pressure
  loss, phase change and finite coolant capacity.
- For each tube count, the search tests the original lengths plus the length
  required by the thermal area, rounded up to 0.2 mm. Candidates must meet
  the midspan flow-area requirement and
  a 1.6 mm minimum tube-to-tube gap. The least solid-tube material proxy wins.
- Ideal-gas compressor work with an assumed efficiency is reported independently.
  It does not solve turbine matching or drive a functional compressor blade design.
- The chosen intake radius, tube count and tube length drive the native geometry.
  The native manifest verifies architecture and tube-count identity before release.

The default selects 24 enlarged tubes, each 25.2 mm long. Its tube material proxy
is 16.9% below the declared 28 × 26 mm baseline while meeting the reference area
and clearance gates. This is a bounded geometric improvement, not evidence of
better engine efficiency, thrust, cooling, strength or flight performance.

The tubes are SOLID printable representations, not helium microtubes. The vanes
are stationary. Helium-loop closure, HX3/HX4, turbine and pumps, hydrogen/oxygen
circuits, reacting flow, inlet shocks, compressor maps, pressure losses, structural
and thermal qualification remain unresolved. The conceptual modes are air-breathing,
rocket with isolated inlet, and the user's requested post-reentry air-breathing
restart. No transition or flight capability is claimed by the model.

Primary architecture and equation references:

- [UK Space Agency SABRE evaluation](https://www.gov.uk/government/publications/synergetic-air-breathing-rocket-engine-sabre-programme-evaluation-report-2022/synergetic-air-breathing-rocket-engine-sabre-programme-evaluation-report-2022)
- [NASA compressor thermodynamics](https://www.grc.nasa.gov/www/k-12/airplane/compth.html)
- [NASA mass-flow relations](https://www.grc.nasa.gov/www/k-12/VirtualAero/BottleRocket/airplane/mflchk508.html)

## Run and print

Run `powershell -File start.ps1`, then open [Vega](http://127.0.0.1:8712/).
Use `setup.ps1` on a fresh checkout. The active Python requirements are NumPy,
SciPy and Trimesh. The native bridge uses the pinned PicoGK/LEAP 71 sources.

Choose a reference airflow sizing case and synthesize. The page displays the
actual exported geometry, selected candidate, equations, all rejected candidates,
mode intent and unresolved systems. Old generic demonstrator runs remain on disk
and are not presented as new SABRE studies.

Each print half must be watertight, consistently wound, one connected solid,
positive volume, and within 125 × 65 × 35 mm before download. Native sampling
checks open air corridors and main-wall material. Zero-area triangles are filtered;
only non-positive voxel-artifact shells inside a strict size/volume budget may be
removed, with counts and filled volumes recorded. Open primary shells, detached
material and substantial cavities fail publication. The exact recipe, native binary
hash, print-file hashes and report travel with each downloaded kit.

STLs use millimetres and arrive with the flat mating plane on the bed. Use your
0.4 mm FDM nozzle and PLA/PETG. Start with 0.2 mm layers and 4 perimeters, review
supports in your slicer and remove them from exposed passages before assembly.
Align the rims and hold the smooth collars with two removable rubber bands.
Physical printability and support removal still require testing on your printer.

Use only room-temperature air from an unsealed desk fan. No fuel, ignition,
compressed gas or hot operation. This is an architecture and airflow demonstrator,
not a pressure vessel, functional precooler or operating SABRE engine.

## Verification

```powershell
python -m unittest discover -s tests
node --test tests/test_renderer.cjs tests/test_mesh_worker.cjs
```

Runs are under `data/prints/`. Earlier source was snapshotted in
`tmp/before-print-focus-20261110-213531.zip` before the scope reduction. The
LEAP 71 research notes are retained as historical references. Vendor sources,
licenses and existing runs have not been deleted.
