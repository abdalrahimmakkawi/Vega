# Calculation and assembly review — revision 10

Audited run: `f281579382794eff858c909b974fa72f`.
Reproduce with `python -m vega.design_audit f281579382794eff858c909b974fa72f`.
The resulting JSON is separate from the immutable accepted geometry artifacts.

## Findings

- A29 (LOX-labelled service line) crosses A35 (cooling supply). Both native
  exported STLs contain shared material at five tested interior locations.
  The nominal swept-envelope gap at the sampled crossing is -2.328 mm.
- A27 (helium service line) and A28 (hydrogen-labelled service line) occupy
  the same blind terminal. Five points confirm shared native material.
  These labels do not represent operating fluid systems.
- Current native component bounds span 121.820 × 70.198 × 207.000 mm.
  The inherited 120 mm length and 60 mm diameter requirements describe the
  original casing, not the expanded assembly.
- The legacy integration input was overwritten by a partial rebuild and
  contains only two components. Missing route inputs are explicitly marked as
  reconstructed from the current specification. The collision confirmations
  use hash-verified native meshes, independently of that reconstruction.

## Arithmetic and model coupling

Seven independently recalculated reference quantities match the saved values:
intake area 1246.504 mm², intake radius 21.466 mm, hypothetical exchanger duty
100.5 W, required area 4526.565 mm², selected area 4644.531 mm², tube gap
1.631 mm, and reference compressor work rate 22.066 W. These remain assumed
sizing cases, not achieved performance of the static demonstrator.

The earlier cooling network used ideal core collectors and hard-coded several
bores, branch locations and port lengths. The revised network splits each of
the four saved collector polylines at its actual branch/port junctions and reads
the saved dimensions. At the same assumed 10 mL/s air flow its estimate changes
from 238.732 to 250.436 Pa. Mass and hydraulic-power balance are checked.
Entrance-length screening exposes developing-flow limitations. Bends, thermal
effects and leakage are still omitted. The estimate assumes unobstructed pipes;
the assembly interference prevents using it as the actual assembly requirement.

Vega has bounded logic for intake/bundle selection and original cooling routes.
The later machinery and frames still use prescribed geometry and coordinates.
There is no complete assembly constraint solver, pump/fan operating point,
working thermal model or whole-engine feasibility result.

## Changes to the workbench

The design-audit panel shows these findings and can isolate each conflicting
pair in the mesh viewer. Older linked revisions show a link to the latest run.
Future bell-cooling builds reject detected external service-route overlaps
before spending resources on voxelization. This targeted guard does not claim
global collision freedom: jacket channels, fittings, support beams and other
solids still need a broader fit audit and explicit interface tolerances.

Equation references: [NASA compressor thermodynamics](https://www.grc.nasa.gov/www/k-12/airplane/compth.html)
and [Ansys laminar-pipe verification](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/fbu_vm/Hlp_VMFL005.html).
