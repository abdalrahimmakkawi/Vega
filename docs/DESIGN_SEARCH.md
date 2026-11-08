# Vega design search

Vega 0.24 no longer sends every generation request through one fixed geometry
state. The Studio's default generation action submits an engineering brief to
`POST /api/design-studies`.

For each study Vega:

1. Holds mission targets, propellants, operating pressures, materials, thermal
   limits, manufacturing limits, and all unlisted requirements fixed.
2. Creates eight deterministic proposals across geometry families supported by
   the computational model.
3. Solves the coupled engineering model for every proposal. Proposals that
   cannot produce a valid state are rejected with their reason preserved.
4. Ranks by failed engineering screens, then geometric separation, then the
   existing engineering score.
5. Selects at most three candidates and runs each state through its own native
   export, mesh checks, assembly export, and system contract.
6. Rejects the study if fewer than two successful candidates have different
   native mesh hashes.

## Variables and invariants

The present bounded search varies:

- bell versus conical nozzle contour;
- paired versus staggered tank packaging;
- chamber length and chamber-to-throat area ratio;
- rectangular versus elliptical air inlet;
- inlet aspect ratio and inlet length.

Everything else in the submitted brief remains fixed. Each study stores exact
varied and fixed fields, rejected proposals, unmeshed alternatives, selected
run identifiers, engineering screens, native mesh hashes, envelope dimensions,
wall-temperature estimate, and structural utilization.

## Interpretation

This is genuine multi-candidate generation within Vega's supported geometry
families, not arbitrary invention of a new propulsion cycle. A distinct mesh
hash proves that the exported bytes differ; it does not prove feasibility,
optimality, manufacturability, or experimental validity. Candidates that fail
thermal or structural screens remain visible as failed concepts and must not be
treated as build-ready hardware.


## Configurable synthesis budget

The workbench starts with an empty viewer. Saved studies are available through
history and never seed new geometry. Search defaults to 64 evaluations and up
to 12 distinct mesh builds. Inputs `search_evaluations` (8–512) and
`search_mesh_limit` (2–64) set explicit compute budgets; they must be integers.
Increasing a budget preserves the earlier proposal sequence. Continuous chamber,
nozzle-angle, packaging and duct dimensions are sampled reproducibly from the
requirements. Every proposal is recalculated and screened before diversity
selection. Failed checks remain visible; selection is not physical qualification.

The supported geometry families still bound this search. It does not synthesize
arbitrary combustion cycles or prove printability. Nozzle and full-airpath CFD
volumes represent gas, not solid printable parts. Process-specific supports,
powder removal, build envelope and material qualification remain unresolved.
