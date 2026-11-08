# Routed thermal resistance model

Select **Distributed thermal resistance** in Vega, or submit
`thermal_model: "thermal_resistance"` through the run API. Old runs and API briefs
without this field retain the prescribed-flux model. The legacy heat-flux input
does not drive the resistance model.

Each actual coolant-route segment supplies its centerline length. The hot-side
profile supplies gas-side area, while channel count, radius and route length
give total coolant-side area. The hot-face ligament is wall/2 minus channel radius.
With constant properties within a segment:

R = 1/(hg Ag) + t/(k Ag) + 1/(hc Ac)

Tout = Tg - (Tg - Tin) exp[-1/(R mdot cp)]

Q = mdot cp (Tout - Tin)

The wall temperatures follow the same convection/conduction resistance network.
The calculation propagates coolant temperature along the existing routed geometry,
retains segment energy residuals, and computes peak wall temperature and gradient.
It repeats at the solved unthrottled operating fuel flow and chamber chemistry.
Temperature gates and the existing conservative thermal-stress screen affect each
alternative's pass/fail status and ranking before geometry selection.

## Assumptions and evidence

This is a one-dimensional distributed resistance calculation, **not a CFD
conjugate heat-transfer solution**. A constant gas reservoir at chamber temperature
is imposed across the cooled span. Both film coefficients and wall conductivity
are supplied assumptions. Liquids have constant density, viscosity and heat
capacity. The model omits boiling, radiation, gas-side energy depletion, contact
resistance, axial conduction and circumferential spreading. Hydraulic losses do
not yet respond to temperature-dependent viscosity. The planar ligament treatment
does not resolve the actual three-dimensional solid between circular channels.

Verification covers the independently evaluated constant-reservoir analytical
solution, invariance under segment subdivision, energy conservation, sensitivity
to coolant film resistance, and propagation into model gates. These checks do
not constitute experimental validation. A thermal failure is retained as a failed
concept; Vega does not silently change limits to make it pass.

Reference for convection/conduction resistances in series:
[NPTEL, Overall heat-transfer coefficient](https://archive.nptel.ac.in/content/storage2/courses/103103032/module3/lec10/3.html).
