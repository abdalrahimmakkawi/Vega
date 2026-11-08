# Spec: Reliable, faster candidate mesh generation

Status: proposed; awaiting user review. Date: 2026-11-03.

## Objective

Let the local Vega user finish a 64-attempt design search, inspect real exported meshes as they become available, and distinguish a usable core export from a completed requested assembly. Fix the slow and failing generation path without reducing the requested search count, silently loosening geometry tolerances, or claiming that mesh closure establishes engineering validity.

This capability repairs generation and reporting. The wider request for new CEM design families and physics-driven topology synthesis remains outstanding; this repair must not describe the existing bounded geometry-family search as unrestricted engine invention.

## Assumptions and observed baseline

- One local user and one active generation worker; retain the existing localhost application.
- Default search: 64 attempts, up to 12 selected exports. Respect explicit user settings.
- Preserve selectable process/material inputs, their uncertainty, and manufacturing checks.
- Saved study `data/studies/e13eff55d02c47dd812b00ff0609f658.json` contains 54 evaluated candidates and 10 rejected attempts. Twelve candidates were selected; 11 distinct native core meshes succeeded. Only one full assembly was computed; ten assembly evaluations failed at the 120-second limit. The remaining native build failed.
- Current job reporting labels those ten core-only outcomes complete. Selected-candidate reevaluation can also throw outside the per-candidate error boundary and abort the remaining batch.
- No reliable elapsed-time baseline for the entire saved study is available. Proposed performance targets below are acceptance goals, not measured improvements.

## Tech stack

Existing Python HTTP server and subprocess workers; plain JavaScript browser UI; native .NET/PicoGK exports; Gmsh/OpenCASCADE assemblies; CadQuery and build123d reference checks. Runtime pins include NumPy 2.4.4, SciPy 1.15.3, Trimesh 5.1.1, RocketCEA 1.2.3 and Gmsh 4.15.2. Reuse installed packages.

## Commands

Run from the repository root in PowerShell:

```powershell
python -m vega.runtime
powershell -NoProfile -File .\start.ps1
python -m unittest tests.test_progressive_search tests.test_design_search tests.test_manufacturing tests.test_mesh_validation tests.test_stl
node --check web/rocket.js
python -m unittest discover -s tests
```

The full test suite is the broader regression check after focused failures are fixed. Performance validation must exercise the actual native/CAD path through the running application; mocked unit tests cannot establish speed or export quality. Record the exact submitted requirements, machine, dependency versions, cache state, stage durations, artifact counts and peak memory with each measured run.

## Project structure

- `server.py`: request validation, job lifecycle, export orchestration and saved results.
- `vega/design_search.py`: reproducible proposals, screening and diverse selection.
- `vega/rocket.py`, `vega/assembly.py`, `vega/meshing/`: engineering calculations, assembly generation and analysis meshes.
- `packages/vega-geometry/vega_geometry/`: mesh primitives and topology checks.
- `integrations/`: isolated numerical/CAD workers and native export integration.
- `web/rocket.js`: generation progress, result selection and downloads.
- `tests/`: focused regression and failure-path tests.
- `docs/`: user-facing behavior and engineering limitations.
- `data/`: existing generated runs and studies; preserve them.

## Required behavior

1. Account for every attempt as evaluated or rejected, and every selected export as completed, partial or failed. Never silently abandon later selected candidates after one candidate raises an exception.
2. Publish the actual core artifact as soon as export and its existing integrity checks finish. Continue requested assembly and analysis work with visible stage progress and elapsed time.
3. Represent core, assembly and analysis outcomes separately. A core with a failed requested assembly is partial. An unsupported analysis must be identified as unsupported. A finished batch with partial outcomes must show those counts and errors prominently.
4. Preserve available artifacts and errors on later-stage failure. Reloading the page must show saved results and a truthful terminal state; an interrupted job must not remain an endless spinner. Historical core-only runs must not be presented as full assemblies merely because their old job status says complete.
5. Profile representative failing assembly inputs before choosing optimizations. Remove repeated work or improve the measured hot path while preserving geometric intent and declared tolerances. Increasing the timeout alone does not satisfy this repair.
6. Keep bounded execution for external workers. A timed-out stage reports its name and error, terminates owned work, and lets the study continue.
7. Distinguish screening results from checks on final exported geometry. Retain provenance and hashes for the actual delivered artifacts. Do not offer a screening surface as a completed printable assembly.
8. Keep engineering and manufacturing failure/unknown states visible. A successful export is not a fabrication or hot-fire qualification.

## Code style

Use existing functions and plain data structures. Use snake_case for Python names; preserve the browser's existing naming convention. Avoid a new task framework or dependency for lifecycle bookkeeping. Keep failure boundaries per candidate, with shared helpers only when they remove real duplication.

Existing code illustrates atomic replacement of saved results:

```python
tmp = path.with_suffix('.tmp')
tmp.write_text(json.dumps(saved))
tmp.replace(path)
```

User-facing output should name the result and stage, for example: `64 attempts finished; 11 core meshes available; 1 assembly complete; 10 assemblies failed.` Avoid a generic complete label when requested outputs are missing.

## Testing strategy

Use unittest and targeted failure injection at external-worker boundaries. Regressions must demonstrate: core publication before later work; assembly timeout producing partial status; a selected reevaluation failure not stopping subsequent candidates; available artifacts surviving later failures; accurate aggregate counts; and reload behavior for running, interrupted and finished studies.

Retain topology equivalence tests against the reference implementation, including damaged meshes. Validate native artifacts with the existing surface, connectivity, route and ligament checks as applicable. Test the browser generation-to-download flow against the local server, including a partial result and an error. Benchmark real CAD inputs for both rectangular and elliptical sections, including inputs from the saved failing study.

## Boundaries

- Always: preserve user inputs and saved files; measure the actual slow stages; distinguish proposed targets from measured results; run relevant regression checks; retain physics, material and printability limitations.
- Ask first: new dependencies, changes to physical assumptions or default tolerances, removal of supported design families, destructive replacement of saved designs, or changing the requested evaluation/export limits.
- Never: hide failure as success, fabricate material properties, label screening geometry as the finished requested assembly, bypass existing integrity checks for speed, edit vendor code as an incidental shortcut, or claim that all system bugs are eliminated from a limited test run.

## Success criteria

- A 64-attempt replay accounts for all attempts and all selected candidates, with no infinite running state and no loss of successful earlier exports.
- A forced failure in a selected candidate allows the next selected candidate to run and appears in the saved study and UI.
- A forced assembly timeout retains the valid core and reports partial status through persistence, API and UI.
- Valid representative rectangular and elliptical assembly fixtures produce their requested full assemblies, including previously timing-out fixtures. Invalid candidates may be rejected with a specific reason; they must not be made to pass by weakening checks.
- Proposed timing goals on this local machine: first available core within 5 minutes, and a representative 64-attempt / 12-selected study reaching a truthful terminal state within 30 minutes. Record stage timings and compare equivalent inputs and cache conditions. Finishing quickly by rejecting valid candidates does not meet the goal.
- The browser remains responsive while jobs run and exposes each available mesh without waiting for the whole study.
- Focused regressions, script syntax check and the applicable wider test suite pass; actual exported meshes retain the requested tolerances and existing integrity checks.

## Open questions

- Approve the proposed 5-minute first-core and 30-minute full-study timing targets, or specify a different acceptable wait. These targets need measurement on the actual machine.
- No printer or material decision is required for this reliability repair. User-selectable material/process options remain available; physical qualification is outside this repair's acceptance claim.
