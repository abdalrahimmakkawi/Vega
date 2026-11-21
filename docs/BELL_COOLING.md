# Bell cooling and whole-system assessment

Revision 10 adds six hollow passages following the existing bell contour,
two ring manifolds and two inspection halves (A33/A34). A35 connects the
existing core cooling outlet to the bell inlet. A36 provides an open return
and a casing support. Hydrogen and oxygen service representations are routed
behind the casing; their machinery interfaces remain blind.

The additions use 0.1 mm PicoGK voxels. The separate cooling-wall crop uses
0.009 mm voxels in a 1 mm cube. It is exported about a local origin, with its
source location recorded in the report. It does not increase the full assembly
resolution. Closed triangular seeds precede voxelization and implicit Boolean
features. Fine-grid Boolean reference tests use geometrically scaled fixtures
to avoid allocating a full-size test volume at the detail pitch.

The Python hydraulic calculation solves nodal mass balance for the original
core branches, connecting lines, six bell branches and finite-resistance ring
manifolds. It assumes room-temperature air and laminar straight-pipe resistance.
Bend, entrance, roughness and leakage losses are omitted. The assumed flow is
an input; it is not a predicted fan operating point or achieved cooling duty.

The whole-system assessment remains **operation not established**. It records
the outstanding whole-airpath viscous CFD, fan/circulator curves, thermal
boundary conditions, material properties, sealing, fit, fastening and physical
validation. The existing intake CFD and centrebody FEA remain local models.
No whole-engine CFD or thermal simulation is represented as having run.

Native STL files may be stored losslessly compressed. Artifact hashes and HTTP
downloads refer to the original uncompressed STL bytes. The viewer combines
three checked display layers and hides the two superseded service-line meshes.
Download the revision 10 additions together with the linked earlier base kits.
