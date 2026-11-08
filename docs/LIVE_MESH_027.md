# Mesh changes connected to the workbench

The adaptive surface module introduced previously was opt-in. The studio and its
exports continued to use the earlier lofts; adding that module did not alter them.
Version 0.27 changes the generator that `rocket.design`, preview, saved studies
and assembly exports actually execute.

## Generated surfaces

Elliptical/lobed ducts now use a shared angular resolution across all five stages.
The resolution follows bounds on angular first and second derivatives, constrained
by target surface edge length and chord tolerance. Radius/amplitude variation
between saved stations is included in the bound. The default uses 352 angular
segments rather than separate 96/128-segment stage contours.

Axial sampling evaluates the saved parametric fields between stations. It balances
axial length against actual circumferential edge scales and tests midpoint chord
deviation. This avoids long strips when angular refinement alone increases the
number of circumferential nodes. Annular rims subdivide when required by thickness.
Shared stage endpoints retain identical inner and outer rings. The rectangular
reference path is retained and is explicitly identified as legacy in mesh policy.

`mesh_surface_edge_mm`, `mesh_chord_tolerance_mm` and `mesh_voxel_mm` are real
generation inputs. Native export now passes the requested voxel pitch to PicoGK,
records it and uses it in the feature-resolution screens. New defaults are 12 mm
surface target, 0.5 mm chord tolerance and 0.75 mm core voxels. Legacy saved runs
without a pitch field retain their original 1 mm artifact identity.

Surface topology/quality validation is content-addressed and bounded in memory.
Repeated identical geometry reuses audit results, while mutations produce another
key. Returned diagnostics are copied so caller mutations cannot poison the cache.
Assembly surfaces and combined exports have explicit allocation/triangle budgets;
exceeding them reports an error requiring coarser controls.

## Visible inspection

The renderer now draws the actual exported triangle edges and computes each
triangle's normalized radius quality `2r/R`. A separate quality view colors those
triangles red/amber/green. These modes use the same native triangle ranges as
solid view. Whole-scene statistics and per-body saved metrics remain distinct.
New generated studies open in solid view with cutaway off; switch to triangle
inspection, isolate a component and zoom to inspect the cells. Camera labels now distinguish a custom orbit from
an orthographic preset.

## Actual old/new export comparison

Old run: `6f695b5862d14c9487372a09ae842be9`.
New displayed run: `7c13cc1b1eb44a25918583a059c0d3dd`.

| Duct body | Old mean 2r/R | New mean 2r/R |
|---|---:|---:|
| Inlet / core bay | 0.584 | 0.761 |
| Mixer | 0.581 | 0.768 |
| Isolator | 0.729 | 0.781 |
| Air combustor | 0.535 | 0.767 |
| Common nozzle | 0.502 | 0.763 |

The new combined export contains 2,831,371 triangles. Its 0.75 mm native core is
watertight with consistent winding, one outer shell and no enclosed void shells.
Exact fingerprints and quality distributions are in `LIVE_MESH_027_VERIFICATION.json`.
The source physics requirements were retained; the new meshing controls and
tessellation change the exported surface discretization, not the engine architecture.

Slender frame members, sharp features and voxel-intersection triangles can still
score poorly under an isotropic triangle metric. The quality view deliberately
exposes those cases. No whole-assembly isotropic-quality acceptance, tetrahedral
volume mesh, solver error estimate, physical validation or manufacturing approval
is claimed. Engine and whole-spacecraft model limitations still apply.
