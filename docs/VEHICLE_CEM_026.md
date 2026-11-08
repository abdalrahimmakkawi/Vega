# Vehicle mass, orbital resources and inverse sizing

Version 0.26 adds executable vehicle-level calculations to the existing propulsion
and assembly chain. The intended scope remains the whole spacecraft and propulsion.
This increment does not constitute a complete spacecraft CEM.

## Calculation chain

1. Requirements set orbital altitude, electrical load, material densities and
   explicitly assumed efficiencies, temperatures and equipment allowances.
2. A circular-Earth-orbit, zero-beta central eclipse determines sunlight and eclipse
   duration. Solar array energy covers the full-orbit load and battery losses.
3. Battery nominal energy covers eclipse load at the declared discharge efficiency
   and allowed depth of discharge. One isothermal radiator node rejects the design
   electrical load and mean battery losses to an assumed effective sink.
4. Assumed areal mass and battery specific energy produce array, radiator and battery
   mass estimates. These enter the same component budget as the saved assembly.
5. Assembly masses use signed component mesh volumes. Core pressure shell mass
   uses piecewise-frustum volume; tanks use capped-cylinder shell volume; feed lines
   use annular area times saved centerline length. The injector is an uncut cylinder.
6. Equipment allowance and contingency produce a dry estimate. In **component
   estimate** mode, that dry mass and the assembly envelope diameter drive both the
   mission speed budget and vertical diagnostic. In **specified** mode the original
   user assumptions remain active and are checked against the estimate/envelope.

The circular orbit is an assumed operating condition, not a demonstrated arrival,
orbit-lifetime prediction or ascent solution. Electrical loads are design inputs;
guidance, communications and payload performance are not inferred from their watts.

## Inverse sizing

For a frozen local tank family, `P = (exp(dv/ve)-1) * (F + k*P)`, where F includes
payload and non-scaling dry mass, and k is the continuous cylindrical tank material
mass increase per kilogram of propellant, including dry-mass contingency.

If `(exp(dv/ve)-1)*k >= 1`, no finite propellant quantity closes this particular
single-stage model. Otherwise the algebraic solution records its delta-v residual
and burn-duration-domain check. This is a conditional diagnostic, not an automatic
hardware redesign: tank radii, wall thickness, all non-tank masses and the assembly
are frozen. The slope excludes the sub-millimetre tank-length round-up used by
current tank sizing. Wider tanks, different materials, staging or a different
propulsion architecture need new design calculations and constraints.

## Assumptions and limits

Default densities (core 8900, tanks/assembly 2700 kg/m³) are user assumptions, not
qualified material selections. Different structural allowables and thermal
properties are still independent assumptions. Gross mass sums can double-count
overlapping joints and omit port cuts, core ribs/jacket and unmodeled hardware;
they are neither an upper nor a lower manufactured-mass bound.

The equipment allowance is not an independently solved vehicle skin, payload bay,
wing, pressurant bottle, valve, avionics or thermal-protection design. The power
model assumes normal solar incidence, fixed conversion efficiencies and constant
load. The thermal model omits surface solar/albedo heating, view factors, transients,
conduction networks, aerothermal loads and reentry. No solar-array or radiator
installation/deployment geometry is claimed. Orbital resource masses remain
preliminary assumptions until selected hardware and environment analyses exist.

## Verification

Saved native study: `6f695b5862d14c9487372a09ae842be9`.
Its modeled dry estimate is about 415.09 kg under the declared 100 kg equipment
allowance and 20% contingency. At the default 1 kW electrical load and 20% power
margin, the resource model sizes about 7.29 m² of solar array, 1119.36 Wh nominal
battery energy and 4.05 m² of radiator at 320 K with a 250 K effective sink.
The orbital mission still fails. Frozen-tank inverse sizing reports no finite
single-stage solution. These are model outputs, not qualified spacecraft values.

The system connection contract now binds resource masses → vehicle mass → mission
and flight inputs, as well as propulsion → native geometry. Tests reject a changed
mission dry mass or an orbital resource mass omitted from the component budget.
`CEM026_VERIFICATION.json` records the selected study's inputs, outputs and audits.

Tests cover independent cylinder/cavity volume, inverse rocket equation closure,
no-finite-solution conditions, density sensitivity, component mass closure, mission
and flight mass identity, reference-area identity, orbital geometry, delivered
eclipse energy, whole-orbit energy balance, load/emissivity sensitivity, zero load,
invalid boundaries and power-mass feedback into mission delta-v.

## Primary references

- [NASA ideal rocket equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/)
- [NASA small-spacecraft power systems](https://www.nasa.gov/smallsat-institute/sst-soa/power-subsystems/)
- [NASA small-spacecraft thermal control](https://www.nasa.gov/wp-content/uploads/2021/10/7.soa_thermal_2021_0.pdf)
- [NASA mission simulation and margins](https://s3vi.ndc.nasa.gov/ssri-kb/topics/2/)
