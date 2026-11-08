# Why Vega appeared not to change geometry

The traced path is `requirements form → RocketBrief → rocket/core and inlet
calculations → shared RBCC state → core/assembly recipes → PicoGK and Vega
Geometry mesh exports → saved run → mesh worker → WebGL studio`. The live API
was serving the saved native STL for the selected run; it was not silently
reusing the previous mesh. The problem had three distinct causes.

1. Some controls are mission-only. With the same engine brief, doubling
   `payload_mass_kg` changed neither the core geometry fingerprint nor the
   outer assembly scene. That is correct: payload enters the mission budget,
   not the present engine sizing calculation. In contrast, changing handover
   Mach, inlet aspect ratio or chamber pressure changed the generated assembly
   scene; changing jacket pattern changed the PicoGK core while leaving the
   external duct scene alone.
2. The studio opened in an all-surface point cloud, including hidden back
   surfaces and the large duct. This made local contour changes difficult to
   see. The default is now a solid cutaway; the point study remains optional.
3. The camera fitted the full multi-metre assembly even in interior mode, so
   the embedded small rocket hardware looked almost static. The mesh worker
   now calculates each body's bounds, and the renderer fits visible or
   isolated bodies. Selecting a changed component focuses its actual mesh.

Vega 0.17 adds `/api/runs/{new}/compare/{old}`. It hashes each saved binary-STL
component triangle span, classifies it as changed/unchanged/added/removed and
reports changed requirements. The studio shows the exact changed-body list,
lets the user isolate any changed body, and labels the current mesh as stale
when form inputs are edited. Mission-only edits explicitly say the engine
geometry will stay the same.

As a real-file check, comparing runs `644d4805…` and `b8ff8710…` gives zero
changed bodies, because their same-input assembly STLs are byte-identical.
Comparing `644d4805…` against the earlier `8f1b47ab…` identifies seven changed
assembly bodies: mixer, isolator, air-combustor envelope, common nozzle, frame,
mixer strakes and thermal reinforcement. The UI, API and file comparison agree.

A new full PicoGK run `62370a74…` changed only inlet aspect ratio from 3 to 5
relative to `644d4805…`. Its assembly STL hash changed from `22c18d17…` to
`1a8551e8…`; nine of 22 exported bodies changed. The assembly envelope changed
from 3,682.3 to 3,253.8 mm long and from 1,238.9 to 1,499.8 mm in diameter.
Its saved system contract passed all 11 connection checks. This confirms the
form → physics/recipe → native mesh → studio path, while showing that visual
complexity is still limited by the current component model.

This repair makes geometry changes visible and attributable. It does not make
every input a geometry input. If a geometry control is clamped or dominated by
another constraint, a new run may correctly report an unchanged body. It also
does not add unresolved mixing, combustion, thermal, structural or
manufacturing physics; those remain the next CEM work.
