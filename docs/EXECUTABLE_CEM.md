# Executable CEM scope

The runtime now executes declared equation systems before producing geometry.
`vega/equation_system.py` accepts named unknowns with SI units, bounds and scales,
and named residual equations with separate scales. It rejects nonsquare systems,
nonfinite residuals, failed convergence and a rank-deficient final Jacobian.
Unit labels document the SI interface; they are not automatic dimensional algebra.

`vega/propulsion_model.py` implements two design-point blocks:

1. Seven simultaneous nozzle equations determine exit Mach, temperature, pressure,
   velocity, throat area, exit area and mass flow from thrust and chamber conditions.
2. Five routed-feed equations determine required supply pressures, equivalent
   injector areas and coolant outlet temperature from flow, actual route losses,
   prescribed injector drop and imposed heat load.
3. A separate fixed-hardware operating model solves three coupled equations for
   chamber pressure, fuel flow and oxidizer flow. Both branch pressure balances
   use the same chamber pressure; total flow must equal choked throat flow.
   Darcy losses are reevaluated at the trial flows. Injector areas and throat
   area remain fixed. The design valve drop becomes an assumed quadratic
   resistance. A supply-pressure perturbation test verifies that the model
   predicts different flows without resizing the hardware. For named propellants,
   RocketCEA now recomputes equilibrium chamber temperature, molecular weight and
   gamma at each trial pressure and mixture ratio. Throat flow uses those trial
   properties. Manual gas mode retains the explicitly assumed properties.
4. Each channel alternative is evaluated at its predicted operating pressure
   before ranking. The structural screen uses the greater of requested and
   predicted pressure. The pressure-dependent utilization feeds candidate score
   and pass/fail checks; it is not merely displayed after selection.

`rocket.solve` consumes the first solution. `rocket.design` derives the profile,
evaluates route dimensions and Darcy losses, executes the feed block for each
channel alternative, ranks alternatives, and builds injector geometry from the
selected solution. This is a sequential reduced-order design calculation, not
a monolithic fully coupled multiphysics solver. The feed block is algebraic and
does not improve the constitutive physics simply by using a numerical solver.

Supply pressure is a feasibility inequality against the tank setpoint, not an
extra imposed equality. The remaining pressure would need regulation/throttling;
this is not a prediction of the operating point of unregulated fixed hardware.
That prediction is provided separately by `predict_fixed_hardware`, using
equilibrium chamber chemistry for named propellants. Its pressure and mixture
ratio can differ from the sizing request; no regulator is silently invented.
Infeasible candidates remain inspectable and flagged. Nonconverged alternatives
are excluded from automatic selection; explicitly selecting one raises an error
before mesh generation. CEA-coupled solves use a recorded relative numerical
derivative step of 1e-4 to resolve property changes; residual acceptance remains
1e-8. Saved solver records include values,
units, raw/scaled residuals, tolerance, evaluations and Jacobian rank. Old saved
runs are explicitly marked as lacking a solver record.

## Verification and limits

Tests cover a coupled analytical two-variable system, incompatible and singular
systems, an independently calculated Mach-2 nozzle case, and geometry response
to doubled thrust. These verify numerical behavior and wiring, not hardware.
With unchanged assumptions the new solver should reproduce the previous ideal
nozzle dimensions. A different-looking mesh is not evidence of better physics.

Not solved: combustion stability; variable-property reacting flow; coolant phase
change; hardware valve/regulator operating characteristics; conjugate heat
transfer; full structural FEA/fatigue; combined-cycle net thrust and transitions;
physical calibration. No measured data have been supplied. The existing topology
optimizer and structural screens are not a qualified whole-engine stress model.

## What completion would require

The selectable [routed thermal resistance model](THERMAL_RESISTANCE_MODEL.md) now
couples gas-film, ligament and coolant-film resistances at design and predicted
operating conditions. It replaces prescribed flux only when explicitly selected.
It is not a variable-property or three-dimensional conjugate heat-transfer solver.

A complete model needs an explicit intended-use envelope and acceptance evidence.
Vega currently cannot qualify an engine for manufacture or operation. Remaining
engineering work includes temperature/pressure-dependent liquid properties and
phase limits; gas-side heat transfer coupled to the wall and coolant; injector
mixing/stability; regulator and valve operating curves; structural loads, joints,
fatigue and material/process data; manufacturing tolerances and passage inspection;
and validation against matched physical measurements. The combined-cycle vehicle
also needs airbreathing thrust and transition models before mission claims.

These are missing physical models and evidence, not geometry-library features.
The current mesh remains a preliminary component layout. Equilibrium chemistry
does not predict finite-rate combustion or combustion stability. Higher pressure
changes the stress screen; it does not automatically repair failed geometry.

RocketCEA API units and chamber-property methods:
https://rocketcea.readthedocs.io/en/latest/functions.html

Equation reference: NASA Glenn, Rocket Thrust Equations:
https://www.grc.nasa.gov/www/k-12/airplane/rktthsum.html

Numerical method: SciPy bounded nonlinear least squares:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html
