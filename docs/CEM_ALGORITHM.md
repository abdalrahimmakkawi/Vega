# Executable Vega engineering algorithm

Vega runs reduced-order engineering calculations. Numerical convergence is not physical validation, and the supported propulsion grammar remains bounded.

## Executed design loop

1. Validate the requirements and solve the seven-equation ideal nozzle design problem.
2. For automatic cooling, enumerate the supported channel counts and sample radii within the wall/pitch/ligament/voxel bounds. Retain legacy dimensions as comparison samples and refine each best radius interval. At most 24 configurations are evaluated.
3. For each configuration, construct actual routed feed/cooling paths, calculate their losses, solve injector/supply/energy closure, then solve fixed-hardware chamber pressure and branch flows. Named propellants recompute equilibrium chemistry at trial pressure and mixture ratio.
4. Predict thrust on the unchanged throat and exit areas, enforcing feed/nozzle mass closure. Feed operating pressure and fuel flow back into stress and thermal screens, including prescribed-flux and thermal-resistance cases.
5. Rank converged designs with passing analytical checks first, then the existing documented preliminary score. Generate the selected channel geometry with its evaluated radius and count. Retain all radius samples and failed checks in the engineering record.
6. Publish design-point and operating-point performance separately, along with the dependency trace and unvalidated evidence level.

## Entry point

```powershell
python -m vega.algorithm requirements.json --output result.json --screening
```

Omit `--screening` to request the existing full assembly construction. The server evaluation worker calls this same algorithm. Native solid export and CFD/FEA remain separate downstream stages.

## What this does not establish

The finite radius refinement is not a global optimizer. Fixed-hardware performance assumes choked, attached, constant-property ideal nozzle flow; overexpansion is flagged but separation is not solved. Coolant properties and specified heat flux/transfer coefficients retain their stated assumptions. Regulation, transient combustion, boiling, fatigue, hot-fire validation and unrestricted architecture synthesis remain unresolved.

## Verification

`python -m unittest tests.test_channel_synthesis tests.test_algorithm tests.test_computational_model tests.test_equation_system tests.test_coupled_chemistry tests.test_thermal_model`

These tests check objective response, selected geometry consistency, supply-pressure sensitivity with fixed nozzle dimensions, mass and thrust closure, solver residuals, chemistry coupling and thermal behavior. Native assembly quality requires its own integration checks.
