# Public-source study of LEAP 71 / Noyron design logic

**Purpose.** Reverse-engineer the observable design method from public descriptions,
published engine examples, and LEAP 71's open-source libraries, then compare it
with Vega's implementation. This is an engineering analysis, not a claim to know
Noyron's proprietary source code. Several different algorithms can produce a
similar final shape, so photographs alone cannot uniquely reveal the original
design rules.

## Findings from public evidence

LEAP 71 describes Noyron as a proprietary computational engineering model that
combines domain logic, physics, manufacturing rules and accumulated design and
test knowledge. It describes PicoGK as the geometry foundation and Noyron RP as
the propulsion-specific model above it. Noyron RP is said to use analytical
thermal and thrust models, heuristics and condensed aerospace logic; its inputs
include specifications such as propellant, thrust and chamber pressure. Its
outputs extend beyond a mesh to predicted performance, process information and
data for simulation. Those are company descriptions, not independently audited
details of its internal implementation. ([Noyron](https://leap71.com/Noyron/),
[Noyron RP](https://leap71.com/rp/), [LEAP 71 technology stack](https://leap71.com/tech/))

A technical article by LEAP 71's co-founder gives the clearest public account
of the method: evaluate physics while constructing a feature. It gives cooling
channels as an example where fluid properties, chemistry, pressure and thermal
loads influence channel cross-section, curvature and wall thickness during
generation. The article argues for a deterministic, traceable computational
model rather than a black-box image-to-CAD generator. ([Computational
Engineering article](https://www.metal-am.com/articles/leap-71-why-engineering-must-move-beyond-cad-to-realise-the-promise-of-ai-and-additive-manufacturing/))

The engine examples show what that coupling buys. LEAP 71 reports a 5 kN
LOX/kerosene engine with regenerative kerosene cooling, a coaxial swirl
injector, film-cooling holes, and temperature/pressure measurement ports. Its
post-test analysis found more cooling-channel pressure loss than predicted due
to printed surface roughness; the company says it updated the cooling-channel
logic for later designs. That is a concrete public example of the loop
`prediction → manufacture → measurement → model correction`, including a
specific miss rather than just a successful render. ([TKL-5 test report](https://leap71.com/2024/06/18/leap-71-hot-fires-3d-printed-liquid-fuel-rocket-engine-designed-through-noyron-computational-model/))

The aerospike is not a bell nozzle with decorative geometry. It changes the
engine's flowpath topology: a toroidal chamber surrounds a central spike, with
separate cooling obligations for the spike and chamber. LEAP 71 reports LOX
cooling the spike and kerosene cooling the outside of the chamber. The later
20 kN bell and aerospike examples show that one underlying model family can
support different architectural phenotypes, but the aerospike test also
encountered startup-transient issues. ([5 kN aerospike report](https://leap71.com/2024/12/23/leap-71-hot-fires-advanced-aerospike-rocket-engine-designed-by-computational-ai/),
[20 kN engine test report](https://leap71.com/2025/12/11/leap-71-hot-fires-two-orbital-class-methalox-engines-designed-autonomously-by-noyron/))

The open-source repositories reveal the intended software layering. PicoGK is
the low-level geometry kernel. ShapeKernel turns kernel operations into reusable
base shapes; its README describes combining those shapes with Boolean and offset
operations. LatticeLibrary offers independent cell-array, lattice-rule and
beam-thickness fields. QuasiCrystals supplies inflation/substitution rules for
Penrose and 3D quasi-tiles. Those are useful construction tools, but none of
them contains rocket-cycle, injector, cooling, strength or manufacturing
knowledge by itself. ([PicoGK](https://github.com/leap71/PicoGK),
[ShapeKernel](https://github.com/leap71/LEAP71_ShapeKernel),
[LatticeLibrary](https://github.com/leap71/LEAP71_LatticeLibrary),
[QuasiCrystals](https://github.com/leap71/LEAP71_QuasiCrystals))

The practical conclusion is that the visual complexity is a consequence of
functional integration. The engine silhouette, chamber, nozzle, cooling
passages, manifolds, injector and build constraints must all derive from a
consistent design state. Adding more lattice patterns or a higher-resolution
mesh cannot substitute for that design model.

## What the current Vega code actually does

Vega has a useful foundation, but the combined-cycle geometry and physics are
not one closed CEM yet:

| Area | Current Vega implementation | Gap that explains the result |
|---|---|---|
| Rocket core | `vega/rocket.py` and `vega/engineering.py` calculate an idealized rocket nozzle and screen feed, tank, injector, cooling and structure. `integrations/Program.cs` sends the core recipe through PicoGK. | Several property and heat-transfer inputs are assumed; steady screens do not close combustion, transients or conjugate heat transfer. |
| Combined-cycle analysis | `vega/combined_cycle.py` computes a cold inlet reference and mission bookkeeping. The new RBCC pack adds Mach-condition screens and an architecture gate. | Airbreathing combustor state, fuel addition, pressure losses, mixing, net thrust, start/unstart and mode transition are unresolved. |
| Outer flowpath geometry | `vega/assembly.py` makes inlet, mixer, isolator, combustor-envelope and nozzle shells from lofted area sections. The downstream stage ratios are declared packaging inputs and several parts are explicitly `geometry_only`. | The shells are not generated from a solved coupled flow/heat/structure state. A pass through the architecture gate establishes connections, not physical correctness. |
| Assembly/export | `vega/assembly_export.py` translates and combines the PicoGK core scene with the separate Vega Geometry shell scene. It exports a multi-body scene after a containment check. | This is not one boolean-integrated, functionally optimized manufacturing body. The shared scene does not make its component models physically coupled. |
| Open-source geometry libraries | PicoGK, ShapeKernel, LatticeLibrary and QuasiCrystals are present. `integrations/Jacket.cs` executes lattice and quasi-crystal branches; the native core builder uses PicoGK operations. | The libraries are geometry primitives and pattern generators. They cannot supply the missing CEM rules or make an unchanged recipe more engine-like. |
| Evidence loop | Vega stores assumptions, sources, software checks and calibration records. | No matched test dataset has been supplied, and the current reference Mach points are not test measurements. No measured performance is used to correct model parameters. |

The most direct explanation for the unchanged mesh is verifiable: the latest
run used the same brief and produced the same assembly STL fingerprint as the
previous run. The RBCC reference pack currently changes the mission evidence
panel and architecture checks; it does not feed solved airpath states into
`vega/assembly.py` dimensions or component contours. Generating it again could
not change the shape. This is the specific connection Vega must gain before a
new data source can alter the geometry.

## Reverse-engineering the public designs responsibly

The useful reverse-engineering target is the design logic visible in public
outputs, not a guessed reconstruction of Noyron's private implementation.
For every reference image or published engine, record the architecture,
propellant, thrust class, nozzle phenotype, cooling strategy, injector type,
visible interfaces, material/process and any explicitly published dimensions.
Mark measurements taken from a scaled photograph as uncertain; do not turn
visual guesses into engineering facts. Keep a separate list of facts,
inferences and unknowns for each example.

Then construct a functional graph before drawing surfaces. Nodes represent
physical domains and parts; typed edges represent hot gas, propellant, coolant,
heat, loads, interfaces and manufacturing operations. The graph must balance
mass and energy, expose pressure drops and heat pickup, and identify each
boundary condition. Geometry should be generated from those solved states and
the graph's connection endpoints. Changing a chamber pressure, propellant,
thrust, material or cooling allocation must change its dependent dimensions,
channels and margins, or Vega must report that the requested design lies
outside the model's domain.

## What Vega needs to build next

1. **Replace geometry-only stage assumptions with one architecture model.**
   Represent each supported phenotype explicitly. Start with a tractable,
   well-documented regenerative rocket core as a calibration case, while
   preserving the user's larger combined-cycle spaceplane objective as a
   separate architecture program. A rocket-only CEM cannot stand in for RBCC,
   TBCC, precooled airbreathing or an orbital vehicle.
2. **Create a single traceable design state.** A versioned recipe should hold
   requirements, fluid states, component interfaces, governing equations,
   assumptions, solved values, geometry fields and manufacturing limits. The
   same state must drive calculations, parts, channels, CAD export, UI
   inspection and the saved run. Remove duplicate geometry constants from the
   assembly layer when physics should determine them.
3. **Solve before shaping.** Close the mass, energy, momentum and pressure
   balances for the chosen engine family. For a regenerative core, couple
   chamber/nozzle gas conditions to coolant enthalpy rise, pressure drop,
   channel geometry and wall conduction. Use a validated property source or
   real-fluid solver inside its documented range. Add structural and thermal
   stress screens with material/process-specific limits. Every approximation
   needs an explicit validity range.
4. **Generate geometry as a response to local physics.** Build the chamber,
   throat, nozzle phenotype, injector, manifolds and cooling channels from the
   same solved flow path. Let channel section, pitch, curvature, wall thickness
   and routing vary in response to local heat flux, coolant state, pressure,
   allowable stress, minimum feature size and powder-removal access. Use
   ShapeKernel/PicoGK for the Boolean, sweep, offset and implicit operations;
   use lattice/quasi-crystal patterns only when a stated structural or thermal
   objective justifies them.
5. **Make manufacturing a constraint in generation.** Model the chosen process,
   alloy and machine: minimum channel and wall features, overhangs, roughness,
   supports, build orientation, powder evacuation, post-processing and
   inspection. The reported channel-roughness pressure-drop miss shows why
   nominal CAD dimensions alone are not enough.
6. **Rank only feasible alternatives.** First reject candidates that violate
   hard physics, topology, structural or process gates. Then report a Pareto
   set for performance, mass, pressure loss, temperature margin, build risk
   and inspection burden. Show why each candidate scored as it did.
7. **Close the evidence loop.** Give every prediction a recorded source and
   uncertainty. Compare measured pressure, temperature, flow and thrust against
   the exact generated recipe, preserve residuals, then update only justified
   model terms. Keep calibration points separate from validation points. A
   render, a watertight mesh or an external reference case is not a physical
   validation result.
8. **Expose causality in the UI.** Selecting a feature should show the
   requirement and equation that sized it, upstream dependencies, its current
   state, margins, validity range and unresolved checks. A channel should be
   inspectable as a connected flow circuit, not only as colored surface detail.

For Vega's combined-cycle spaceplane goal, the second architecture program must
later close inlet capture and recovery, rocket/air stream mixing, airbreathing
combustion, common-nozzle expansion, mode transitions and installed thrust over
the trajectory. The current RBCC Mach table is useful for scenario screening,
but it does not contain the data to solve those parts. Those need a real
cycle/flow model, geometry driven by its states, and eventually matched
simulation or test evidence.

## Proposed acceptance criteria for Vega's next CEM milestone

- A named engine phenotype produces a complete, connected component and flow
  graph with no decorative/unclassified bodies.
- Every critical dimension and local geometry field traces back to a solved
  equation, an explicit manufacturing rule or a clearly labeled assumption.
- Parameter changes propagate end-to-end into analysis, geometry fingerprint,
  mesh and saved UI evidence. A same-input regeneration may remain identical;
  changing an influential input must create a documented, explainable change.
- Geometry checks cover shared interfaces, channel connectivity, collisions,
  minimum wall/ligament, open/closed flow volumes, build limits and inspection
  access at the stated resolution.
- Reported performance is separated into ideal, reduced-order, simulation,
  measured and validated evidence classes.
- The first reference design is compared against independent, published values
  and then against a physical test dataset before Vega labels its model
  calibrated.

## Implemented first slice: Vega 0.14

Vega 0.14 begins this conversion. `vega/cem_state.py` creates one saved RBCC
design state from captured-air mass flow, rocket mass flow and exit state,
momentum proxies, transition total temperature and manufacturing feature limits.
`vega/assembly.py` consumes that state to generate stage areas, an area-normalized
lobed and twisted flowpath, varying wall fields, helical mixer strakes and a
counter-wound conformal reinforcement network. `vega_geometry/field_loft.py`
is the new reusable field-driven geometry primitive.

The same requirement set that produced run `0f4117b446e54c84be6e17df1ae374f4`
now produces verified run `8f1b47abf71f4a34a834ba3435d55ea1`. The assembly recipe and STL
hashes changed, its named components increased from 20 to 22, and the exported
assembly increased from 1,175,198 to 1,202,078 triangles. All saved connection,
surface, field-generation and design-state gates pass. A sensitivity check also
confirmed that changing transition Mach from 4 to 2.5 changes the field values
and geometry fingerprint.

This first slice makes geometry causally responsive, but the area relations,
lobe field and reinforcement field remain bounded heuristics. The next slice
must replace those relations with closed mixing, heat-release, pressure-loss,
thermal and structural solutions before Vega can claim a physically predictive
combined-cycle design.

## Implemented second slice: Vega 0.15

Vega now combines the ideal captured air stream and the solved rocket stream
in one **conditional ideal adiabatic mixer balance**. The saved state carries
their mass flows and total temperatures, constant-property heat capacities,
the mixed total temperature, mass and energy residuals, the cold inlet's
normal-shock total-pressure reference, and the ideal choked mass flux. The
mixer throat is generated above the resulting minimum area with an explicit
5% area margin. The mixed temperature also drives wall and reinforcement
fields, so changed transition or rocket conditions change the connected mesh.
The topology panel reports the calculated values and the pressure needed at
the generated throat.

The same default brief previously saved as `8f1b47abf71f4a34a834ba3435d55ea1`
was regenerated as `b8ff87109abd44549ddd3350fe0e8f00`. The mixer throat
increased from 0.075112 to 0.079620 m². The connected STL fingerprint changed
from `c568b68c…` to `22c18d17…`. Direct comparison of corresponding exported
STL vertices found a 2.55 mm mean and 8.07 mm maximum shift in the mixer;
the frame also moved outward to pass its sampled flow-clearance gate at twice
the default capture area. The native assembly still has 22 named bodies and
1,202,078 triangles; mesh count by itself does not measure shape change.

This closes an ideal mass and enthalpy ledger, **not** the physical ejector or
airbreathing cycle. Full air capture, calorically perfect gases and complete
adiabatic mixing are assumptions. Mixed pressure, momentum transfer, actual
mixing efficiency, air-mode fuel flow, heat release, wall heat flux and
installed thrust remain unknown. NASA's [isentropic flow](https://www.grc.nasa.gov/www/k-12/airplane/isentrop.html)
and [normal-shock](https://www.grc.nasa.gov/www/k-12/airplane/normal.html)
relations support the reference mass-flux and pressure equations; the
[THRSTER research record](https://ntrs.nasa.gov/citations/20010036882)
shows why measured wall pressures and stream mixing are needed to validate
an ejector model. No model coefficient has been calibrated from a test.

## Source record

## Implemented third slice: Vega 0.16 system connection

The assembly's propellant-flow graph is now assembled from the registered
tank, feed, cooling and injector ports in the same geometry recipe that is
sent to PicoGK. It no longer uses a second hand-written propellant diagram.
After the native core and connected assembly export, `vega/system_contract.py`
checks route identity, coincident registered ports, mission inventory, rocket
and captured-air mass-flow agreement, shared interfaces, native core provenance,
and coverage of every exported component. A failed connection stops run saving.
The saved contract includes recipe/export fingerprints, the generated flow
edges, each body's drivers and evidence class. The viewer exposes these facts
in the one-run system panel and on component selection.

The live same-brief run `644d4805df3c4b238109a6a6f2d19d10` passed all 11
connection checks and traced 22 exported bodies and three fluid routes. Its
assembly STL hash remains `22c18d17…`, equal to the preceding version because
this slice connected and checked the existing geometry without changing its
inputs or contour generation.

The contract is a software and geometry coherence gate. It does not turn an
air-combustor envelope into a combusting airpath or establish cooling,
structural, control, trajectory or manufacturing validity. Those need their
own physical models and eventually matching measurements.

- LEAP 71, [Noyron](https://leap71.com/Noyron/), [Noyron RP](https://leap71.com/rp/),
  and [technology stack](https://leap71.com/tech/).
- Lin Kayser, LEAP 71 co-founder, [Why engineering must move beyond CAD](https://www.metal-am.com/articles/leap-71-why-engineering-must-move-beyond-cad-to-realise-the-promise-of-ai-and-additive-manufacturing/),
  *Metal AM*, 2025.
- LEAP 71, [TKL-5 hot-fire and post-test report](https://leap71.com/2024/06/18/leap-71-hot-fires-3d-printed-liquid-fuel-rocket-engine-designed-through-noyron-computational-model/),
  [5 kN aerospike](https://leap71.com/2024/12/23/leap-71-hot-fires-advanced-aerospike-rocket-engine-designed-by-computational-ai/),
  and [20 kN bell/aerospike tests](https://leap71.com/2025/12/11/leap-71-hot-fires-two-orbital-class-methalox-engines-designed-autonomously-by-noyron/).
- Open-source foundations: [PicoGK](https://github.com/leap71/PicoGK),
  [ShapeKernel](https://github.com/leap71/LEAP71_ShapeKernel),
  [LatticeLibrary](https://github.com/leap71/LEAP71_LatticeLibrary),
  [QuasiCrystals](https://github.com/leap71/LEAP71_QuasiCrystals).
