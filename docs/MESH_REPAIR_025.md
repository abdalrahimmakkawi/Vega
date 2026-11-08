# Geometry and model consistency repair, 0.25

The frame optimizer analyzed straight axial bars, but the assembly mesher wrapped
their centerlines around the duct. A negative sector offset was reduced modulo
the sector count, turning a neighboring clockwise diagonal into a nearly complete
positive revolution. The exported member lengths, volumes and load paths did not
match the FE model. Passing surface-manifold checks could not detect this error.

The exporter now meshes each analyzed node pair as one straight, 32-sided member,
using the optimized radius. Saved `frame_members` records contain node identities,
endpoints, radii and lengths. A regression verifies the exact member-to-mesh count
and FE endpoints/radii. A stronger sampled clearance screen includes wall thickness
and each member's radius. Radial wall attachments remain separate, unanalyzed
members; overlapping joints still need manufacturing design. The circular FE area
has a 0.64% polygonal-area discretization difference at 32 sides.

`/api/geometry/preview` runs the actual design calculation through the shared
single-worker chemistry queue and constructs recipe surfaces, tank exteriors and
feed envelopes. It neither supplies native passage booleans nor claims an audited
manufacturing solid. The UI labels it as unsaved, removes export links and disables
the saved component inspector until the saved native mesh is restored. Exact-design
generation is now the default; design-space exploration is an explicit option.

The viewer has isometric, side, top and end presets, a coordinate triad, a
millimetre scale bar, physical-scale locking, expanded inspection, and accurate
preview body bounds. Auto-fit can make two differently sized geometries look
similar; physical-scale locking makes dimensional comparisons possible.

## Native export verification

Baseline: `fa61007608a843029bfbf6521a893637`, inlet aspect ratio 3.
Variant: `5bf71b2faa2c4b9a93f5bd47fe43aa5f`, inlet aspect ratio 5.
Only that input changed. Nine of 22 exported bodies changed; core bodies remained
byte-identical. Length changed 3682.265 to 3253.767 mm and envelope diameter
1238.926 to 1499.839 mm. Both native core surface audits passed with one connected
component. Exact component fingerprints are in `FRAME_REPAIR_SENSITIVITY.json`.

The default frame has 25,344 triangles, versus 126,464 in the earlier curved-member
export. The reduction comes from removing unintended wrapping and duplicate segment
caps, not from hiding frame members.

## Whole spacecraft scope

The target is the whole spacecraft and propulsion system. The model record now
separately assesses failed engineering requirements and incomplete subsystem models.
Numerical consistency does not close vehicle mass, payload packaging, aerodynamics,
coupled ascent, vehicle structures, thermal protection, power, avionics, GNC,
communications, manufacturing or physical validation. Current outputs remain a
reduced-order propulsion and packaging model, not a complete spacecraft CEM.

LEAP 71 describes Noyron as proprietary domain knowledge, physics, manufacturing
rules and a feedback process using simulation and physical observations. Using
PicoGK alone does not provide those models:
[Noyron](https://leap71.com/Noyron/),
[Noyron RP](https://leap71.com/rp/).
