# Component and port requirements

`vega/component_network.py` derives a provisional port graph from the current
recipe's component inventory. It deliberately does not interpret the shared
cold-air inspection manifold as an intended internal circuit.

The first non-firing baseline uses four separate, open ambient-air circuits:

| Circuit | Required flow order |
| --- | --- |
| Main air | Precooler air side → LP row → intercooler air side → HP row → chamber outlet |
| Bypass air | Static bypass fan → spill duct → bypass nozzle |
| Exchanger cooling | Precooler secondary side → intercooler secondary side → main exchanger |
| Jacket cooling | Core jacket → bell jacket |

Older recipes use their single compressor in place of the LP/intercooler/HP
sequence. These are proposed requirements, not recovered as-built passages.
Separate main/bypass supplies avoid pretending an inlet splitter has been
designed. Exchanger series order is provisional pending a heat balance. Air is
the non-firing test fluid; this does not define an operating helium cycle.

Every recipe component is either assigned geometry for an active flow component
or retained with an explicit exclusion reason. Structural and historical engine
representations are excluded from fluid duty pending review. Casing halves and
bell halves are mapped to logical jacket components. Missing geometry is listed.
Test fixtures cannot supply active circuit ports. Each exchanger side has its
own ports and internal passage, so thermal contact never implies fluid mixing.

Port dimensions use mm; positions and outward unit normals use assembly
coordinates. Diameter, position, normal and mating interface remain null until
measured or designed. Component dimensions, mechanical interface, loss model,
thermal model, and machinery performance maps are also explicitly unknown.
Boundary pressures, temperatures and flow rates are unresolved. Nothing is
silently assigned zero loss or infinite heat capacity.

The automatic check rejects invalid references, duplicate IDs/edges, wrong flow
direction, fluid/circuit mismatches, incompatible declared diameters/interfaces,
missing internal passages, unused active components and disconnected islands.
Every required port needs one external connection and a directed source-to-sink
path. Branches must be represented by explicit splitter components when added.

`topology_valid` only means the declared graph passes. `ready_for_sizing` also
requires engineering inputs; the current baseline is false. `geometry_verified`
is always false at this stage: graph validation cannot detect obstructed bores,
wall thickness, clearances, leaks or failed Boolean cuts.

The UI links the assessment for any hash-verified existing run at
`/api/component-network/<run-id>`. New server builds save and hash
`component-network.json`; topology errors prevent publication. Existing runs
remain immutable, and their assessments are computed on request from the checked
report. The assessment includes a hash of the source recipe.

Next gates: supply measured interfaces and boundary conditions; solve the whole
network and heat balance; size and route geometry; verify actual openings and
clearances; run selected Linux CFD and defined-load FEA. The existing manifold
solver and prior CFD results do not validate this proposed topology.
