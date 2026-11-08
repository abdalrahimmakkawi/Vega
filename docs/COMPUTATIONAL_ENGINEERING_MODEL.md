# Vega computational engineering model

Every generated run now contains a `computational_model` record built from that
run's solved values. Its stage graph is also shown in the studio under
**Computational engineering model**. The record fingerprints the requirements
and model trace so a reviewer can distinguish one calculation from another.

The executable order is requirements/domain checks → chamber state → ideal
nozzle solution → shared core profile and passage recipe → feed-network mass,
pressure, and tank calculations → routed coolant heat and friction balance →
structure/manufacturing screens → channel design-space ranking → core geometry
→ optional conditional combined-cycle state → connected assembly → vehicle
screen → PicoGK conversion and export audit. The combined-cycle branch is only
created when that architecture is selected. Each stage lists the values it
consumes and produces, equations/method, assumptions, upstream dependencies,
and checks. The saved trace is generated after mesh/export so it can report
the actual PicoGK and assembly audit outcomes.

The pressure-fed core currently executes these governing relations:

* Isentropic area–Mach relation is inverted by bounded bisection to obtain exit
  Mach; ideal thrust is `F = mdot Ve + (pe - pa) Ae`.
* Choked mass flow uses chamber pressure, temperature, `gamma`, and gas
  constant. RocketCEA supplies equilibrium chamber properties for supported
  propellants. Proptools independently checks choked mass flow when available.
* Fuel and oxidizer split by mixture ratio. Tank capacity follows burn mass,
  liquid density, and ullage. Routed pressure loss uses Darcy–Weisbach with a
  laminar relation below the implemented Reynolds cutoff and a smooth-pipe
  turbulent approximation above it.
* Routed cooling integrates specified heat flux along the generated cooling
  centerline and closes `Q = mdot cp (Tout - Tin)`. The wall-temperature result
  is a conduction/film screen using declared conductivity and heat-transfer
  coefficient.
* Thin-wall hoop stress, thermal stress, passage ligaments, velocity, feature
  size, and pressure margin are screening constraints. Three channel layouts
  are evaluated under the same model and ranked with an explicit heuristic.
* One shared solved profile and registered route recipe drives the generated
  component geometry. For the combined-cycle branch, conditional mixer/airpath
  calculations are recorded with their assumed pressure recovery; they do not
  solve installed airbreathing thrust.

Verification and validation are separate. Mass/energy closure, network
conservation, route checks, independent calculation checks, system-contract
identities, and mesh-integrity checks verify implementation consistency at
their stated scope. They do not validate hot-gas behavior or a physical engine.
The model record explicitly says when there is no matched measurement set.
Numerical convergence is not claimed for a discretized CFD or FEA solution;
Vega does not currently run either one. Test correlation, material allowables,
property-domain coverage, uncertainty propagation, and holdout validation
remain required before claiming predictive accuracy.

## Development sequence

1. Keep requirements, equations, units, boundary conditions, and validity
   domains explicit in the model record.
2. Add hand-calculated analytical benchmark tests for each solver before adding
   coupled physics.
3. Add mesh/discretization convergence studies only alongside actual CFD/FEA
   solvers and solver-specific residual criteria.
4. Expand parameter sweeps and sensitivity/uncertainty propagation across
   coupled requirements, properties, and manufacturing tolerances.
5. Calibrate only from traceable measurements tied to the exact candidate;
   reserve independent runs as a validation holdout.

The current implementation is a coupled reduced-order preliminary design
model, not a qualified engine design system. The NASA M&S standard describes
model credibility across the lifecycle, including acceptance criteria,
sensitivity analysis, uncertainty, verification, and validation. NASA's CFD
verification guidance distinguishes implementation verification from physical
validation and calls for conservation checks, analytical benchmarks, and grid
convergence where discretized solvers are used. OpenMDAO provides a documented
example of connecting explicit discipline components into coupled models and
solving their multidisciplinary state.

References:

* [NASA-STD-7009B, Standard for Models and Simulations](https://standards.nasa.gov/node/263)
* [NASA CFD Verification and Validation tutorial](https://www.grc.nasa.gov/www/wind/valid/tutorial/overview.html)
* [NASA SWE-070, Models, Simulations, and Tools](https://swehb.nasa.gov/spaces/7150/pages/16449960/SWE-070%2B-%2BModels%2BSimulations%2BTools)
* [OpenMDAO documentation](https://openmdao.org/newdocs/versions/latest/)
