# Geometry and cold-flow reference

Sources inspected on 2026-10-20. Equations are implemented in `vega/inlet.py`;
the geometry primitive is original code in `packages/vega-geometry`.

| Source | Implementation | Limits |
|---|---|---|
| [NASA Glenn: isentropic flow](https://www.grc.nasa.gov/www/k-12/airplane/isentrop.html) | Static/total pressure and temperature, speed, mass flux and station area | Constant gamma, one-dimensional ideal flow between stations |
| [NASA Glenn: normal shocks](https://www.grc.nasa.gov/www/k-12/airplane/normal.html) | Downstream Mach, static jumps and total-pressure loss | Normal shock at the capture plane; not oblique-shock inlet design |
| [NASA Glenn: ramjet/scramjet thrust](https://www.grc.nasa.gov/www/BGH/ramth.html) | Records the required gross momentum, ram drag and pressure terms | No thrust value until combustor and exhaust states are solved |
| [NASA/TM-2010-216362](https://ntrs.nasa.gov/citations/20100024370) | Defines unresolved inlet-mode-transition validation work | Report describes a specific TBCC study; not calibration data for Vega |

The inlet reference starts from the existing atmospheric handover condition.
It imposes a normal shock, then an ideal subsonic diffuser. Captured mass flow
is held constant; the model computes each station's area from mass flux.
Width/height follows an explicit aspect-ratio input. Axial length and wall
thickness are user inputs, not solved structural or aerodynamic dimensions.

The exit Mach rule, smooth Mach interpolation, 17 stations, and 1000 K maximum
total-temperature screening limit are **Vega implementation assumptions**.
They are not recommendations or universal bounds from NASA. Above that limit
the reference returns an unsupported-domain result and no mesh. The limit
does not prove accuracy below it.

The mesher joins rectangular or 96-segment elliptical stations linearly,
producing a closed material surface with open flow ends. Ellipse sizing uses
the exact polygon area to preserve the required station area. Elliptical outer
semi-axes expand by the wall input, which is not a constant normal offset.
The geometry does not prove that the depicted
contour creates the assumed flow. Boundary layers, separation, bleed, shock
placement, starting, heat transfer, combustion and transition remain unresolved.
This is not a supersonic-combustion inlet. The full RBCC/TBCC spaceplane remains
unclosed. Version 0.12 uses the cold reference as an input to a connected
assembly; packaging then enlarges the bay to contain the actual core. The
unobstructed cold-flow solution does not describe this installed geometry.

For the rocket reference, shared ports determine route endpoints. Actual feed
and return lengths now enter the existing Darcy friction screen before passage
variants are ranked. Feed/return overlap is rejected by a centerline clearance
screen, preventing an obvious geometric cooling bypass. Bend losses, global
fluid isolation and actual leak-tightness still require additional modeling.

Software checks include independent normal-shock conservation of mass,
momentum and total enthalpy; Mach-2 reference ratios; station continuity;
mesh edge incidence/winding and a known rectangular-duct material volume;
parameter-to-geometry sensitivity; and actual native recipe runs. None of
these substitutes for measured engine or inlet validation data.


## Connected assembly and topology (2026-10-22)

The [NASA RBCC analysis](https://ntrs.nasa.gov/citations/19980237203) and
[NASA mixing study](https://ntrs.nasa.gov/citations/20000038202) inform the
component architecture and the need to resolve mixing. Their experimental
performance is not assigned to Vega. Downstream stage lengths, area ratios,
mount positions and frame sectors are explicitly Vega geometry inputs.

`vega/assembly.py` builds inlet/core bay, mixer, isolator, air-combustor envelope,
common nozzle, mounting supports and frame from one shared set of sections.
`vega/assembly_export.py` combines these with the actual generated PicoGK core
mesh using a translation only. Export rejects a core whose native vertices lie
outside its bay (2 mm tolerance for the 1 mm voxel boundary). Component ranges
and colors accompany the same STL in the saved engineering bundle.

Graph cycle rank is E - V + C. For closed orientable indexed surfaces,
Euler characteristic is V - E + F and the sum of genera is (2C - chi) / 2.
Tests include a capped cylinder (genus 0), annular duct (genus 1), open face,
reversed winding and pinched vertex. These checks do not establish global
collision freedom, structural load paths, leak-tightness or manufacture.
The frame is overlapping beam solids. Core mounts need cooling-interference,
aerodynamic and stress analyses. No topology-optimized performance is claimed.


### Area-profile generation

The saved assembly now exposes a piecewise area schedule for its air path. If
`A` is the installed inlet/core-bay reference area and `Ae,r` is the solved
rocket-core exit area, the geometry inputs are: mixer throat `max(0.68 A,
1.5 Ae,r)`, mixer exit `0.88 A`, isolator exit `0.85 A`, combustor-envelope
exit `1.10 A`, common-nozzle throat `r_t A` (editable, default 0.68), and
common-nozzle exit `r_e A` (editable, default 2.0). Each transition samples a
cubic smoothstep area blend across 24 axial intervals; the mesh shares the
exact end station between adjacent sections. The mixer and common nozzle each
have separate convergent and divergent portions. If the rocket-core exit is
too large for the selected common-nozzle throat, Vega rejects the geometry
rather than silently overlapping the throat areas.

These equations are packaging geometry rules. They do not compute captured
mass-flow compatibility, fuel addition, combustor heat release, pressure loss,
thermal state, choking, or installed thrust. No solved combined-cycle claim is
made from the area schedule.

### RBCC evidence wiring (2026-10-22)

`vega/rbcc_reference.json` is loaded by `vega/rbcc_knowledge.py` during every
RBCC/ejector design. NASA's [A5 integrated flowpath record](https://ntrs.nasa.gov/citations/20020016608)
supplies the required stage sequence (inlet, rocket primary/mixer, isolator,
airbreathing combustor, common nozzle) and the documented mode transitions.
The generator checks stage presence/order, shared interfaces, the two mixer
inflows, the combustor-to-nozzle connection and a connected core mount network;
the saved candidate carries the pass/fail checks and the UI exposes them.

The [NASA RBCC cycle-code comparison](https://ntrs.nasa.gov/citations/20020073110)
supplies five Mach anchors (0, 1, 2.5, 4 and 8). At the brief's selected
altitude, Vega recalculates ideal free-stream speed, dynamic pressure, capture
mass-flow, total temperature/pressure and ideal normal-shock total-pressure
recovery. These are operating-condition screens only; they are not the original
NASA test values, a thrust solution or a measured calibration. Mach 8's total
temperature screen is deliberately flagged rather than treated as a usable
cold inlet state.

The [NASA THRSTER three-stream ejector description](https://ntrs.nasa.gov/search.jsp?R=20010036882)
identifies a rocket primary stream, captured-air secondary stream and mixed
stream marched through mixer, combustor and nozzle. Its abstract does not
provide quantitative mixing rates, so Vega stores the model as a provenance
anchor and does not invent coefficients. [NASA direct-connect instrumentation](https://ntrs.nasa.gov/citations/19990064401)
informs the required validation fields: matched inlet conditions, primary and
secondary flow, mixer/combustor wall pressures, injection state, measured net
thrust, uncertainty and facility corrections. Vega has no such matched test
dataset yet; the reference pack is not calibration data.
