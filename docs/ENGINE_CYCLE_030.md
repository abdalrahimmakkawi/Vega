# Vega 0.30 coupled engine-cycle closure

Vega now evaluates a steady reduced-order combined-cycle operating point after
the rocket nozzle and inlet station calculations. The cycle is part of the
same run record consumed by the CEM trace.

The solver closes captured-air, rocket-primary and air-side fuel mass flow;
mass-weighted perfect-gas properties; mixer and combustor total-pressure
losses; declared air-fuel ratio and combustion efficiency; combustor heat
addition; common-nozzle choking and supersonic expansion; gross thrust; inlet
momentum drag; and installed net thrust. It reports mass, energy and force
residuals and refuses a closed status if any check fails.

The previously reported 1.43 kN result used an incorrect nozzle exit-pressure
calculation and is withdrawn. Recalculate existing results with the corrected
code. The resulting value is a design-screen output, not a
validated engine rating. The model still assumes perfect-gas mixing, fixed
air-fuel ratio, fixed combustion efficiency, bounded mixer/combustor pressure
losses and one-dimensional steady nozzle flow. Reacting CFD, finite-rate
chemistry, boundary-layer separation, inlet unstart, transient controls,
structural thermal coupling and hot-fire calibration remain required.

The implementation is in `vega/engine_cycle.py`; `screen_combined_cycle` now
stores its result under `vehicle_screen.engine_cycle`, and the computational
model trace reports the `combined_cycle` stage as `screened_closed` when all
residual checks pass.
