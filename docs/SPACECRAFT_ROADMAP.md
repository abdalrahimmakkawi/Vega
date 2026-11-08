# Spacecraft development status

## Implemented and runnable

- One saved requirement object feeds the engine model, mission budget and native geometry job.
- A rocket-only baseline plus three distinct combined-cycle architecture roadmaps.
- Editable mission inputs, unsaved budget preview, saved results, and subsystem dependencies.
- Conditional ideal rocket delta-v using the same propellant inventory as the tank sizing model.
- Payload included in both mission bookkeeping and the vertical diagnostic.
- Explicit failed / unknown checks instead of assumed feasibility.
- Native rocket-core geometry and existing audits. No generated airframe is claimed.

## Next model gates

1. **Vehicle budget and packaging:** explicit component mass inventory and geometry envelopes, payload volume, tanks, installation clearances and reference axes. Acceptance: mass and volume accounting reconcile, with uncertainties displayed.
2. **One atmospheric propulsion family:** select RBCC as the initial research path; implement inlet, mixer, combustor and nozzle state interfaces with conservation residuals. Acceptance: every modeled station closes within specified tolerances and every missing map remains unknown.
3. **Coupled mission:** integrate forces, propellant consumption and control modes over ascent. Acceptance: mass continuity at transitions; no instantaneous free speed or fuel; orbit requires both position and velocity conditions.
4. **Aerothermal and structural evidence:** use solver results with provenance and valid operating domains. Acceptance: limits affect ranking and invalid designs remain excluded.
5. **Geometry from solved interfaces:** generate packaging and flow paths from shared stations, then inspect interference, voids and clearances. Acceptance: geometry changes have a traceable engineering reason.
6. **Evidence and uncertainty:** compare against matched public or measured experiments; distinguish code verification from physical calibration. No measured engine data have been supplied.

Selecting TBCC in the workbench adds turbine dependencies and a separate orbital rocket to the roadmap; it does not execute a turbine solver. Neither the number of libraries nor the detail of a mesh establishes feasibility.
