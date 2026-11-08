# Conditional airpath fluid dynamics

Vega now computes a one-dimensional station state for the RBCC/ejector airpath. The input air flow comes from the existing cold normal-shock inlet reference, and rocket mass flow and gas properties come from the rocket solution. The existing ideal mixer closes mass and stagnation enthalpy. This stage then applies a **user-specified mixed total-pressure recovery** (default 0.8) to the inlet post-shock total pressure. This recovery is an assumption, not a predicted mixing loss.

At each generated mixer, isolator, combustor-envelope and common-nozzle section, Vega solves the subsonic root of the calorically perfect-gas compressible mass-flow equation for Mach number. It derives static pressure, temperature, density, velocity, dynamic pressure and choking margin from that root. It sizes the mixer and common-nozzle throat to at least 105% of the critical area at the assumed pressure, and raises other section areas to the same floor when necessary. This links the pressure assumption to the actual generated mesh. A lower assumed recovery increases required area; it does not make a physical pressure-loss prediction.

The cold inlet reference also reports local air viscosity from Sutherland's law, a hydraulic-diameter **proxy**, and a Reynolds-number proxy. The proxy does not include wall boundary layers, nonuniform flow, blockage from installed hardware, bleed or friction.

Equations and constants:

- [NASA Glenn mass-flow derivation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/mass-flow-rate-equations/): compressible mass flux and the Mach 1 maximum.
- [NASA Glenn isentropic relations](https://www.grc.nasa.gov/www/k-12/airplane/isentrop.html): static and total pressure/temperature conversion.
- [NASA normal-shock relations](https://www.grc.nasa.gov/WWW/BGH/normal.html): cold inlet total-pressure reference.
- [NASA Sutherland-law reference](https://ntrs.nasa.gov/api/citations/19990046590/downloads/19990046590.pdf): air viscosity reference 1.796e-5 Pa s at 293 K, S=111 K.

The result is a conditional flow screen, not CFD, a combustion solution, or a flight-qualified engine. In particular, mixed-stream momentum/pressure loss, air-mode fuel addition and heat release, friction, supersonic nozzle expansion, unstart, thermal loading, and installed thrust remain unresolved. The mixed stream viscosity and Reynolds number are intentionally not inferred from the air-only viscosity relation.
