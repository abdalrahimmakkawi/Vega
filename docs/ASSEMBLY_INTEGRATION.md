# Revision 9: static assembly integration

The accepted revision 8 geometry is retained in its original coordinates.
Eleven additional 0.1 mm PicoGK parts establish material overlaps between every
fixed component. The centrebody deliberately remains a sliding component.

## Interfaces

- A22: left accessory mounting frame, including precooler, He pod, canister
  and regenerator saddles.
- A30: right mounting frame, including hydrogen and LOX pod saddles and the
  spill-duct/burner coupling.
- A31: aft transition housing, bearing webs and heat-shield supports.
- A32: hollow static shaft, compressor carrier and turbine coupling.
- A23–A26: four hollow inspection links joining the regenerator canisters,
  pre-burner representation and re-heater representation.
- A27–A29: hollow He, hydrogen and LOX service harness representations.
  Their inherited machinery interfaces are **blind**. These are not operating
  fluid circuits, and the arrangement is not a validated thermodynamic cycle.

## Computation and acceptance

Closed triangular annular meshes are voxelized at 0.1 mm. Lattice beams add
supports and rounded conduit exteriors; Boolean subtraction opens their bores.
Bore cuts extend beyond the rounded outer caps into the annular couplings.
Add, Subtract and Intersect reference tests run before native generation.

Each joint has seven material probes: its center and ±0.12 mm on each axis.
The source STL is checked by bounded-memory ray parity. Native connectors
must contain those probes, and the final exported connectors are independently
checked at the same positions. The attachment graph must reach all fixed
parts. This is sampled material-overlap evidence, not a minimum-contact-area
or structural-strength calculation.

Every added STL must be watertight, consistently wound, positive-volume and
one connected surface. A separate enclosed cavity causes rejection. Only the
existing tightly bounded sub-voxel artifact cleanup policy is permitted.
Conduit centerlines and the new shaft's stem-clearance region are sampled.

Native downloads retain the full resolution. The viewer loads the immutable
base scene and a separate simplified integration scene, with audited triangle
ranges and normals for both. Each display reduction must remain a closed solid
and preserve volume within 1%. Open-half viewing sections the aft housing in
the renderer; the native STL remains whole. The heat shield has a visibility
control. The integration ZIP contains additions; the accepted base kit remains
available separately.

## Limits

Overlapping contacts establish a static geometric assembly. They do not provide
fasteners, production fits, sealing, exhaustive collision clearance or strength
qualification. The original precooler tubes and machinery ports remain solid
representations. Existing CFD and FEA cover only the intake and centrebody;
they do not validate the added supports, plumbing, rotating machines or hot
sections. No firing, thrust or cryogenic operation is established.
