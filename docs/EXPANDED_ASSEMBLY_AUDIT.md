# Expanded assembly audit — 15 November 2026

Revision: `b1073594abad461e9b844aece476e20d`, derived from `ee8c18fe554244c38d4ac96addb3f985`.

The system contains partial engineering logic. Seven independently recomputed baseline quantities agree with their stored values: intake area and radius, assumed heat duty, required and selected exchange area, tube clearance, and assumed compressor power. Agreement verifies arithmetic under the supplied assumptions, not measured performance.

The added compressor rows, fan, turbine, heat exchangers and reservoir representations use fixed profiles and placement. Their geometry is not derived from a solved operating point, shaft-power balance or complete thermal cycle.

## Connection repairs and limits

Three new native 0.1 mm voxel couplings bridge the two reservoir-to-valve gaps and the LP/HP compressor hub gap. The builder converts closed triangular inputs to PicoGK voxels, runs Boolean reference checks, checks closed connected output solids, and samples each coupling at 16 material points on each adjoining native part. It also checks 32 centerline samples within each coupling. These are sampled static attachment checks, not full interference, seal or mechanical qualification.

Reservoirs remain solid envelopes. Their attached couplings do not establish a fluid passage through the reservoir. The compressor hub coupling establishes static material contact only; it does not model a rotating shaft or operating compressor.

| Remaining relationship | Required before calling it connected |
| --- | --- |
| LP stage → intercooler → HP stage | Separated stage inlet/outlet plenums and continuous air ducts; current adjacent rows do not establish this external detour |
| Fan → bypass nozzle | Continuous separated annular bypass duct and checked clearances |
| Reservoirs → valves → pumps | Hollow inert-test reservoir domains, defined pump ports, open connected bores and explicit valve state |
| Main/HX3/other exchangers → thermal loop | Two separate fluid domains per exchanger, named ports and a consistent selection of cycle components |
| Gas generator → turbine → exhaust | Defined non-firing passage topology and separation from the main air path |
| Injector placeholder → liner | Defined non-firing distributor passage; current annulus is not an injector design |
| Turbines → compressor/fan | Shaft arrangement, supports, clearances, speed and power matching |

Adding decorative tubes between outer surfaces would not resolve these conditions. Eighteen of the twenty new functional relationships remain proposed; two have static couplings but blocked reservoir passages. No new complete fluid circuit is established.

## Linux run

The separate `/home/abdal/Vega-Sim` project runs an OpenFOAM low-speed enclosure pilot for this revision. The surface manifest identifies the revision, report hash and component surface hashes. Existing surfaces were reused only after confirming unchanged source hashes. Casings come from the display mesh; other components come from native surfaces, with closed-solid simplification checked for volume change. Volume preservation does not bound local surface error.

The enclosure bounds are derived from all component bounds plus padding, so the expanded reservoirs lie inside the domain. The pilot uses prescribed 0.1 m/s room-temperature air, stationary walls and a laminar steady solver. Its approximately millimetre-scale fluid mesh does not inherit the 0.1 mm geometry resolution and may not resolve narrow cooling channels.

The run can report enclosure velocity, pressure and mass conservation. It includes flow around the engine and cannot report engine throughflow, heat-transfer capability, shaft power, thrust, structural strength or whole-engine operability. Mesh convergence remains outstanding.

Machine-readable engineering findings are in `data/design-audits/b1073594abad461e9b844aece476e20d.json`. Geometry checks are in the revision's `report.json`. Linux solver logs and numerical results remain separate from immutable geometry artifacts.

The completed pilot passed `checkMesh` with 941,388 cells, maximum non-orthogonality 54.10 degrees and maximum skewness 3.43. SIMPLE converged at iteration 214. The last scheduled monitors, at iteration 210, give enclosure inflow 0.00503048668 m³/s, relative inlet/outlet imbalance 4.99e-9 and enclosure pressure difference 0.00355596 Pa at density 1.2 kg/m³. These are numerical checks for this enclosure, not engine performance. Results are copied to `data/simulation-results/b1073594abad461e9b844aece476e20d/`; the interactive Linux state is `results/interactive-b1073594abad461e9b844aece476e20d/Vega-cold-flow.pvsm` under the simulation project.
