# Third-party sources

LEAP 71 develops and owns PicoGK, ShapeKernel, LatticeLibrary (including
ImplicitLibrary), and QuasiCrystals. Their upstream sources, per-file notices,
licenses and examples are preserved under `vendor/`. Exact revisions are in
`vendor/libraries.lock.json` and the pinned Git submodules. They have not been
removed or replaced during the Vega One scope reduction.

The active native bridge executes PicoGK voxel construction, ShapeKernel BasePipe,
LatticeLibrary ImplicitModular/RawGyroidTPMSPattern/FullWallLogic, and
RegularCellArray/BodyCentreLattice. QuasiCrystals remains available for future
geometry work; it is not executed by the first printable demonstrator.

`packages/vega-geometry` is Vega's original geometry library. Its section evaluator
supplies the sampled lobed contours used by the native implicit material field.
Vega is independent and is not affiliated with or endorsed by LEAP 71. No Noyron
proprietary model or code is included.

NumPy, SciPy and Trimesh supply arrays and exported-mesh inspection. Their notices
remain in the installed packages. The local .NET SDK, native PicoGK binaries and
NuGet dependencies retain their upstream notices and licenses. Older installed
optional dependencies under `.tools/` are not required by the active application.
