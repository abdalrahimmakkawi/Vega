# Vega 0.28: CAD meshing, hybrid volumes and adaptive solver studies

The active bespoke duct strip mesher and standalone midpoint-refinement module
have been retired. Their source and tests are recoverable under
`.tools/retired-meshing/0.27/`, with a SHA-256 manifest of the original files.
Old saved studies retain their original geometry. Generate a new study to use
the replacement; opening a saved STL does not silently regenerate it.

## Implemented pipeline

1. Vega's mission/propulsion equations generate the saved section geometry.
2. `vega_geometry.sections` supplies validated analytic elliptical/lobed and
   rectangular boundaries. Elliptical area uses the analytic coefficient π/4,
   independent of display mesh resolution. Lobe amplitudes preserve section area.
3. `vega.meshing.cad` builds closed OpenCASCADE wall solids. Gmsh generates
   unstructured surface triangles using curvature, throat/area-gradient and port
   sizing. Adjacency-based orientation repair changes winding, not coordinates.
   Closed-manifold, winding, positive volume and measured triangle-quality checks
   gate assembly export. This applies to the cold-reference inlet and all five
   connected duct walls; there is no fallback to the retired mesher.
4. PicoGK still generates the unioned rocket core and cooling/feed geometry.
   The actual core mesh is placed at physical scale in the combined assembly.
5. The selected common-nozzle passage receives a **conforming hybrid volume**:
   an unstructured Gmsh triangular section sweeps into prisms, while graded
   quadrilateral wall layers sweep into hexahedra. Shared indices and complete
   faces join the two regions. It is a swept hybrid, not a tet/prism mixture.
6. OpenFOAM imports the SI-unit mesh, runs `checkMesh -allTopology -allGeometry`,
   then solves an explicitly assumed low-Re, steady incompressible laminar case.
   Its recovered axial velocity gradient drives a second mesh and solve.
   Pressure-drop change, residuals and flow imbalance are recorded. The 5%
   two-mesh criterion concerns axial discretization only, not radial or model
   independence. Nonconvergence is recorded rather than reported as success.
7. CalculiX solves the **same selected topology-optimized frame**, using its
   actual nodes, radii, supports and two representative load cases. Its axial-bar
   compliance is compared with Vega's independent internal truss solution.
8. The saved run binds the mesh report to the assembly recipe, PicoGK STL hash,
   inputs and exported artifacts. The UI offers an actual half-domain cell-face
   inspector and a ZIP containing meshes, solver inputs, logs and results.
9. A separate continuous, conforming volume spans all five analytic duct stages.
   The four shared section interfaces are checked before meshing. This cold-flow
   case excludes the embedded PicoGK rocket and mixer strakes, so it does not
   establish installed propulsion performance. Its mesh, scene, OpenFOAM case
   and convergence state are recorded separately from the nozzle refinement.

## Installed tools and repeatable setup

| Tool | Runtime | Status on this machine |
|---|---|---|
| Gmsh 4.15.2 | `.tools/meshing` | Installed; native DLL and mesher executed |
| OpenFOAM 1912.200626 | Ubuntu 22.04 WSL package | Installed; conversion, mesh checks and CFD executed |
| CalculiX 2.17 | Ubuntu 22.04 WSL package | Installed; selected frame FEA executed |
| PyMAPDL 0.74.1 / PyFluent 0.43.0 | `.tools/ansys` | Isolated client APIs installed |
| ANSYS solver | Licensed local/remote installation | Unavailable; user confirmed no license yet |

The Ubuntu repository versions were selected for the existing distribution;
they are not claimed to be the latest upstream releases. The Ansys clients are
not solver executables. No ANSYS result is claimed. The study writes a MAPDL
frame deck and, after a successful OpenFOAM solve, a Fluent mesh export.

```powershell
python integrations/install_meshing.py
powershell -File integrations/setup-solvers.ps1 -InstallAnsysClients
python -m vega.meshing.solvers --probe
python -m unittest tests.test_meshing_backend tests.test_mesh_validation -v
node --test tests/test_renderer.cjs tests/test_mesh_worker.cjs
```

`setup-solvers.ps1` uses the existing `Ubuntu-22.04` WSL installation; it does not
enable virtualization or reboot Windows. Gmsh, Ansys and the two pre-existing
OpenCASCADE Python distributions are isolated to avoid dependency collisions.
`install_meshing.py` repairs the Windows Gmsh wheel's DLL location when pip's
`--target` mode omits it.

When a licensed local MAPDL solver is available, configure
`VEGA_MAPDL_EXECUTABLE`, then run:

```powershell
python integrations/run_ansys.py data/analysis/RUN_ID/fea/frame.mapdl
```

## APIs and scope

```python
from vega.meshing.cad import cad_duct
from vega.meshing.hybrid import build_hybrid, write_msh
from vega.meshing.imported import mesh_solid

# Stations use mm; required: z_mm, width_mm, height_mm, wall_mm.
# Optional fields: lobe_amplitude, lobe_count, twist_rad.
surface = cad_duct(stations, edge_mm=12, chord_mm=.5)
volume = build_hybrid(stations, edge_mm=20, sectors=48, layers=6)
write_msh(volume, "flow.msh")  # SI coordinates, named inlet/outlet/wall/fluid
solid = mesh_solid("component.step", "solid.msh", edge_mm=4)
```

`mesh_solid` accepts STEP/BREP/IGES solids and a single closed oriented STL
(including a suitable PicoGK union). It rejects an overlapping multi-body STL
instead of guessing a repair. Its output remains in mm. This generic solid
adapter is separate from the automatic common-nozzle CFD study.

The current hybrid sweep supports single, star-shaped elliptical/lobed passages.
The CFD domain excludes the upstream embedded rocket, mixer strakes, combustion,
cooling manifolds and whole-airframe external flow. Wall-layer thickness is
reported; no target y+ or turbulent-wall resolution is claimed for the laminar
verification case. Axial spacing growth is capped at 1.3 and radial wall growth
at 1.25; isotropic quality is not demanded of deliberately anisotropic layers.
CAD chord sizing is a target, not an independently certified Hausdorff bound.
Frame FEA excludes pressure-wall stress, bending, joints, buckling and fatigue.
These executable analyses do not complete or qualify a whole-spacecraft CEM.

## Sources used

- [SimScale: five tips for high-quality meshes](https://www.simscale.com/blog/tips-high-quality-mesh/): clean closed geometry, local sizing, boundary layers and convergence checks.
- [Asmaa Hadane: meshing strategies for complex geometries](https://www.linkedin.com/pulse/meshing-strategies-complex-geometries-best-practices-asmaa-hadane/): hybrid/conformal meshes, smoothing and adaptation.
- [Gmsh reference manual](https://gmsh.info/doc/texinfo/): CAD construction, meshing API, element definitions and quality measures.
- [OpenFOAM Windows guidance](https://openfoam.org/download/windows/): Linux solver runtime through WSL.
- [CalculiX manual](https://www.dhondt.de/ccx_2.15.pdf): truss elements and input deck conventions.
- [PyMAPDL installation requirements](https://mapdl.docs.pyansys.com/version/stable/getting_started/install_pymapdl.html): separate solver requirement.

The two supplied articles guide the workflow; they do not specify Vega's physics,
material constants, boundary conditions or numerical acceptance thresholds.
# Verified saved run

Run `0595368cf75a4269b73b1bdd06ede2c2` contains 126,882 conforming prism/hex cells
(80,878 before adaptation), no inverted cells, and minimum sampled scaled
Jacobian 0.95125. Both OpenFOAM cases passed checkMesh and converged after
continuation from saved fields. Pressure drop changed by 2.259% across the
single axial refinement pass. The adaptive mesh used the initial coarse
velocity-gradient estimate; its exact source is retained in `adaptation_source`.
This is not a radial refinement study or a hot propulsion validation.

The selected 150-member frame passed its independent CalculiX compliance
comparison. Full numerical records are in `MESH_028_VERIFICATION.json`.
For an interrupted iterative solve, use
`python integrations/resume_mesh_study.py RUN_ID --end-time 1600` to continue
checked cases and refresh the bound report and downloadable archive.

