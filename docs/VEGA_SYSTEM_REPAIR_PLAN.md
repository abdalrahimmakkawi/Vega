<!-- /autoplan restore point: "C:\\Users\\abdal\\.codex\\visualizations\\2026\\11\\01\\01a197fa-2ff3-7360-8294-2a81554108b4\\vega-autoplan-restore-20261105.md" -->
## Implementation plan
# Vega system diagnosis and repair plan

Status: implementation in progress; remaining acceptance gates are open. Review date: 2026-11-05.

## User outcome

Vega must turn engineering requirements into multiple meaningfully different, traceable designs, provide usable geometry promptly, and distinguish printable solids from analysis domains and unverified concepts. Preserve the user's long-term ambition for unconventional engine designs. Physical constraints, manufacturing constraints, and measured evidence must drive design choices; visual novelty is not an engineering objective by itself.

## Evidence and limits

The audit covers requirements, design search, reduced-order calculations, assembly generation, native export, analysis orchestration, persistence and UI polling. It is not a certification of the engine physics or an exhaustive proof that the whole repository is bug-free. No new expensive 64-candidate study was launched. Saved studies and focused tests provide the starting evidence; a timed baseline still needs to be measured.

- `vega/design_search.py`: proposals seed the random generator from requirements excluding search controls. Identical inputs repeat the sequence. This is intentional reproducibility; the UI lacks explicit explore-new versus replay semantics.
- The same file searches a fixed grammar: bell/conical, paired/staggered tanks, rectangular/elliptical ducts, rails/braced/optimized frames, and dimensional variations. Hashes and parameter distance measure identity and input variation, not engineering novelty or architecture diversity.
- `server.py`: the first-candidate callback executes the whole `run_job` synchronously before continuing search. This includes expensive native export, assembly reconstruction and analysis. Subsequent selected proposals are screened again. Full assembly evaluation has a 120-second subprocess limit; native export has its own limits.
- `server.py`: full assembly failure is caught and recorded, but the parent candidate may still become `complete`. Search-study state is saved at the end, while live jobs exist only in memory. Selected-candidate re-evaluation occurs outside the child error boundary.
- `vega/meshing/study.py`: CFD and FEA follow selection rather than feeding the search objective. Default `mesh_run_solvers=1` adds this work to generation. Rectangular ducts have an unsupported analysis path. Cold-flow checks are not hot reacting-engine validation.
- `vega/meshing/cad.py`: OCC lofting/boolean construction, meshing, topology audits and cache operations need separate timing. Preserve existing edge/chord/voxel tolerances during optimization; do not assume a particular kernel operation is the measured bottleneck yet.
- `web/rocket.js`: polling depends on in-memory jobs; restart returns unknown. Partial outputs and stage-specific failures need explicit UI representation. Candidate-view buttons currently depend on coarse completion state.
- Saved study `e13eff55d02c47dd812b00ff0609f658`: 54 evaluated, 10 rejected, 12 selected, 11 labelled complete, one failed. The existing proposed `SPEC-mesh-generation.md` records 10 assembly timeouts and only one computed assembly.
- Saved study `fb256493627d461a8913c77f51cbf987`: 56 evaluated, 8 rejected, 12 selected, 12 labelled complete. All 12 selected rows contain five failed engineering checks. Twelve distinct recorded scene hashes do not establish twelve different engine architectures.
- The repository has an unborn `master` branch and no usable commit baseline; existing local work must remain untouched. Source/version fingerprints and a baseline snapshot are required before implementation.

## Proposed product contract

1. An attempt is always accounted for: evaluated, rejected, duplicate, cancelled or failed. Distinguish requested attempt budget from selected export count.
2. A study may finish successfully with zero feasible designs. Explain violated constraints; never fill a success gallery with failed designs merely to reach a quota.
3. Feasibility, geometry availability, analysis completion and evidence level are independent fields. A completed computation is not a physically validated design.
4. Retain diagnostic geometry for failed candidates and allow inspection, with its failures visible. Do not erase useful partial work.
5. Explicit actions: Explore new candidates, Replay this study, Continue this search. Store seed, proposal cursor, fixed-requirements hash, generator version and solver/material provenance.
6. New exploration changes the search sequence while replay remains reproducible. Requirement changes start a new lineage. Unsupported families or analysis stages must be explicit.
7. Define design diversity with topology/connectivity and normalized geometric descriptors, then a configurable near-duplicate threshold. Keep exact content hashes for artifact integrity only.
8. Materials remain selectable; unknown process, material or printer limits yield unresolved manufacturing checks, not print-ready approval.

## Delivery sequence

### P0: Truthful outcomes and durable jobs

Files: `server.py`, `vega/design_search.py`, run persistence helpers, `web/rocket.js`, focused job-lifecycle tests.

- Add a versioned study/candidate/stage manifest with status, timestamps, attempt index, errors and artifact references. Reuse atomic run-index/file patterns already in the repository; no new service is needed.
- Persist at each transition and artifact publication, using temporary files plus atomic replacement. Recover interrupted work on restart and retain already verified artifacts.
- Separate core solid, assembly solid, printable eligibility, nozzle fluid domain, airpath fluid domain and analysis results. Derive overall complete/partial/failed/cancelled from required stages, not only process exit.
- Move selected-candidate re-evaluation inside a per-candidate failure boundary. Record duplicates and all rejections. Do not let one failed candidate abort unrelated results.
- Add cancellation, heartbeat and bounded subprocess cleanup. Limit concurrency around shared chemistry/kernel state; do not blindly increase the global thread count.
- UI shows attempted/total, feasible, selected, artifacts available, current stage, elapsed time, last progress and errors. Restore jobs from durable state after reload/restart. Keep diagnostic outputs accessible.

Acceptance: injected assembly timeout, native-export failure, solver failure, cancellation and server restart all reach truthful terminal states; partial artifacts survive; a 64-attempt manifest accounts for all 64 attempts. An all-infeasible study reports zero feasible designs.

### P1: Measure and remove unnecessary work

Files: `server.py`, `vega/meshing/cad.py`, `vega/meshing/study.py`, export/assembly helpers.

- Record wall time and peak memory per stage: screening, chemistry, CAD construction, surface meshing, native export, integrity checks, JSON encoding, browser load, volume meshing, CFD and FEA.
- Reproduce one saved rectangular case, one elliptical case and one historical failure in isolated workers with time/resource caps. Then establish a 64-attempt benchmark on this machine, preserving exact requirements and tolerances.
- Decouple publication from analysis. Publish a clearly labelled preview and each verified solid as ready. Queue requested detailed analysis after artifacts are available; keep explicit full-analysis mode.
- Remove duplicate screening/reconstruction where a versioned evaluated state is reusable. Inspect and reuse the existing CAD cache; extend only missing content-addressed reuse. Include geometry inputs, kernel/code versions and relevant controls; reject corrupt or stale cache entries.
- Profile loft/boolean complexity before changing CAD algorithms. Reduce redundant work or reuse invariant components without changing geometry or loosening tolerances.
- Bound independent worker concurrency after memory profiling, isolate work directories, and serialize unsafe shared libraries.

Acceptance: benchmark the same inputs before/after and report first preview, first verified solid, full selected export, analysis duration, peak RAM and cache-hit rate separately. Proposed targets: first verified solid within five minutes and selected exports within 30 minutes for the agreed fixture; these are targets, not achieved results. Every speed improvement must retain geometric/mesh-quality checks.

### P2: Meaningful exploration and feasibility selection

Files: `vega/design_search.py`, `vega/rocket.py`, `vega/cem_state.py`, `vega/assembly.py`, comparison/UI helpers.

- Implement explicit new/replay/continue semantics and persist lineage. Remove forced inclusion of the first attempted candidate in final selection; early preview does not grant final rank.
- Separate hard constraints from advisory checks; unknown required evidence is unresolved. Rank feasible candidates by interpretable engineering objectives and report a Pareto set instead of presenting one opaque scalar as definitive.
- Add geometry/topology descriptors and near-duplicate rejection after cheap screening. Explain each selected candidate's meaningful differences and tradeoffs. Never promise 12 feasible outputs for infeasible requirements.
- Feed available validated evaluation outcomes back into ranking or subsequent proposals, with fidelity and uncertainty explicit. Do not treat current cold-flow solver outputs as validated engine-performance objectives.
- Document actual grammar coverage and unsupported mechanisms. Distinguish dimensional variants, shape variants and topology variants in the UI.

Acceptance: exact replay reproduces proposals; new exploration explores another recorded sequence; continuation does not repeat prior attempts; remeshing an unchanged shape does not count as a new design; rank is not privileged by arrival order; fixed requirements never mutate; infeasible candidates stay diagnostic.

### P3: Expand computational engineering design freedom

Files: explicit architecture/geometry schema, `vega/cem_state.py`, `vega/assembly.py`, physics and manufacturing contracts, geometry package tests.

- Preserve working calculations and regression cases while replacing the fixed assembly grammar behind a versioned interface. The legacy generator can remain available for replay, but must not silently stand in for new-generation capability.
- Represent permitted component connectivity, interfaces, load cases, flow paths and manufacturing constraints explicitly. Support topology alternatives only when their equations, geometry construction and checks are implemented.
- Start with one verified design domain and at least two genuinely different supported configurations, selected using measurable engineering objectives. Expand to additional families after benchmark coverage; do not fabricate an unrestricted engine synthesizer.
- Make cooling paths, structural layout and shape respond to coupled engineering evaluations. Separate existing heuristic shaping/truss sizing from demonstrated optimization.
- Apply build-envelope, minimum wall/ligament, channel accessibility, trapped-volume, assembly-interface and process-specific checks. Report unknowns for unspecified manufacturing choices.
- Establish reference cases, conservation checks, convergence/mesh-sensitivity studies and eventual physical-test correlation before making performance or test-readiness claims.

Acceptance: supported topology changes alter connectivity, not only tessellation; each carries appropriate physics/manufacturing checks and traceable decisions; infeasible/unsupported designs are rejected or marked unresolved; deterministic replay remains available across generator versions.

## Founder perspective and scope

The near-term product demonstration should prove a repeatable engineering loop: requirements → distinct candidates → constraint evidence → selected solid → explicit test plan. A large gallery of visually different meshes is not proof of utility. Track time to first usable artifact, feasible-design yield, meaningful diversity, export reliability and evaluation provenance.

Keep the long-term spacecraft/hybrid-engine ambition. Stage its delivery behind measured evidence. This plan does not claim a flight-ready engine, unrestricted invention, certification, or experimentally proven performance. Full airframe design and launch operations are outside this repair scope.

## Verification plan

- Retain existing design-search, progressive-search, CEM, manufacturing, mesh-validation, system-contract and browser/renderer checks.
- Add real orchestration tests with stub subprocess boundaries: first artifact publication must not wait for CFD; assembly/solver failure must not label all outputs complete; restart/cancel preserve manifests and files; one candidate failure cannot abort the study.
- Add search semantics and shape-equivalence tests, using known duplicate shapes with different triangle order/resolution.
- Add cache invalidation tests for code, material, requirements, fidelity and tolerance changes; corrupt/truncated artifact tests.
- Run instrumented native rectangular/elliptical integration cases and then a complete 64-attempt benchmark. Store artifacts, hardware/software versions, tolerances, timings and quality results together.
- Manual UI check: reload mid-job, inspect partial outputs, cancel, resume after restart, compare candidates, download the intended solid, view analysis domains separately and verify truthful labels.

## Decisions proposed for review

Prefer repairing lifecycle and observability before attempting broad architecture synthesis. Preserve design freedom as a required later milestone. Prefer explicit exploration seeds over accidental randomness; retain reproducibility. Prefer staged artifact delivery over reducing the requested search budget. Preserve existing tolerances and verified files. These are proposed implementation choices, not completed fixes.

<!-- autoplan-accepted:ceo -->
- Required stages are frozen when a request is accepted. Preview mode requires evaluated geometry only; solid mode requires the selected core or assembly solid plus its integrity audit; analysis mode additionally requires the explicitly requested domain and analysis stages. Unrequested stages are not required. A stage records pending/running/succeeded/failed/unsupported/cancelled/interrupted and evidence separately. All required stages succeeded means candidate complete; a required stage failure with a usable requested artifact means partial; required-stage failure without one means failed; explicit cancellation means cancelled with retained artifacts. Unsupported required stages are failures of capability, not successful analysis. Failed optional stages appear as warnings without failing the requested output. Study execution can complete with zero feasible candidates; the outcome summary must distinguish complete search from feasible-design count and export/analysis failures. Test the mode/stage/outcome matrix including unsupported and optional failures.
- On restart, recover durable manifests and verify published artifact references; mark unfinished stages interrupted and perform no automatic expensive restart. Resume interrupted work is an explicit action within the original attempt budget and lineage: retry only unfinished stages under a new execution ID, retaining the same proposal/attempt index and recording retry history, without double-counting attempts. Continue search adds an explicit additional attempt budget after the prior proposal cursor; it is distinct from resume. The original budget includes completed, duplicate, rejected and interrupted attempts; not-yet-started slots remain pending, or become cancelled if the study is cancelled. Persist every proposal before evaluation so recovery cannot silently sample a replacement. Test crash before/after artifact publication and both cancellation-versus-completion orders; late execution results cannot overwrite a terminal cancellation or newer execution.
- Replay means reproduce the recorded proposal sequence and recorded evaluation-feedback inputs, not promise bit-identical solver/tessellation output on another runtime. Persist exact proposals, adaptive feedback, generator schema/version, relevant runtime/material provenance and artifact hashes. Historical artifacts remain viewable. Re-evaluation under historical versions is offered only when the required runtime is retained and available; otherwise report unavailable and offer an explicitly new lineage under current versions. Preserve a replay adapter or immutable recorded proposals when replacing the legacy generator. Test fixed-seed replay, adaptive feedback replay, continuation cursors and unavailable historical runtimes without silently substituting a current generator.
- Before feasibility ranking changes, define a reference decision: an engine designer compares assembly candidates under fixed requirements to choose a fit/flow prototype for further evaluation. Use the existing rectangular and elliptical assembly cases as initial within-family fixtures; do not count those section choices as new propulsion architectures. A usable solid must identify its intended interfaces, dimensions, units and unresolved manufacturing limits. Verify each hard screening check's units, applicability, source and evidence on a known admissible case and deliberate violation cases; label results model-screened, never experimentally validated without test evidence. P3 must select a distinct connectivity pair and its validation domain before topology implementation, with an explicit supported-capability milestone and baseline comparison; broad architecture synthesis remains in scope but is not unrestricted implementation-ready work.
- Preserve the 64-attempt benchmark and compare staged search against the existing deterministic configuration baseline and selective detailed analysis. Report distinct, model-screened feasible yield, decision time, export reliability and compute cost at identical requirements and tolerances. Choose performance work from measured stage costs; do not reduce user-requested budgets to manufacture a speed claim. P3 expansion requires a demonstrated improvement in supported configuration coverage, constraint satisfaction or decision time relative to the current generator, with failed comparisons recorded as a reason to revise the approach rather than silently declare success.
- Make admission atomic and idempotent; validate cancel/resume IDs and origins with existing server rules. Require execution-token checks for late worker results and test both cancellation/completion orders. Protect publication from disk-full/replace failure; use a compatible schema-versioned historical reader, leave old data unchanged, and provide app-only rollback that preserves manifests and artifacts. Add accessible status text, keyboard actions, and readable narrow-layout progress/downloads. Verify these at the HTTP/orchestration and browser boundaries, not only helper functions.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:design -->
- Present study execution state and primary action first, then attempts/budget, model-screened feasible count and requested artifacts available, then selected candidates. Keep detailed timing and errors expandable. Distinguish finished search, zero feasible candidates and incomplete exports. Render a unit-aligned comparison with objective direction, constraint results, evidence fidelity/unknowns, meaningful-difference text and linked geometry; classify dimensional, shape and connectivity changes. Show failed candidates as inspectable diagnostics outside the default feasible comparison. Pareto choices are tradeoffs, not a fabricated single winner.
- Define each artifact by role, actual available format and units: core solid, assembly solid, preview, nozzle fluid domain (analysis only), airpath fluid domain (analysis only). Never advertise STEP unless generated. Make the requested available solid the primary download; put integrity, manufacturing eligibility, evidence and unresolved/failed checks beside it. Diagnostic downloads say diagnostic. Early previews carry stable IDs and provisional labels, update disposition with reasons, and stay inspectable if rejected or deduplicated without silently switching the current view.
- Provide the visible state/action table specified in this plan: no studies -> enter requirements; running without artifacts -> stage/counts/elapsed/cancel; partial -> inspect retained output and error; zero feasible -> violations/diagnostics/revise requirements into new lineage; connection lost -> retained last-known results/timestamp/retry without changing job outcome; interrupted -> resume within original budget; corrupt artifact -> unavailable and explicit retry/rebuild; unavailable historical runtime -> recorded replay or explicitly new-version lineage; complete -> compare/download with evidence. Distinguish resume, additional-budget continue, new exploration and recorded replay in an action menu; show requirements lineage and requested output mode before submission. Execution retries remain subordinate to the study in history.
- Preserve focus and selected candidate during updates; announce meaningful stage changes through a polite live region, not every poll. Make status/checks/dimensions/downloads available outside the 3D canvas, use visible focus and non-color status, and verify keyboard-only comparison/cancel/recovery. Keep existing workspace visual tokens; inventory them before changes, use body/status text at least 16px, verify body contrast at least 4.5:1 and touch targets at least 44px. Narrow layouts show selected-candidate detail plus selector; comparison overflow has clear row labels and reachable actions. Verify long names, unknown values, large result sets and all state-table paths in browser tests/manual checks. Do not claim rendered compliance from this source-only review.
<!-- /autoplan-accepted:design -->

<!-- autoplan-accepted:dx -->
- Reuse setup.ps1, start.ps1 and vega.runtime to document and verify a clean-environment quickstart, with prerequisites, isolated CAD installations, required versus optional capabilities for each requested mode, exact setup/start/submit commands and expected output. Add an inexpensive checked-in fixture and measure readiness-to-first-screened-preview on a declared provisioned machine against a five-minute target; separately report clean install time and full-solid/64-attempt timings. Do not claim an unavailable dependency can be bypassed when the requested stage needs it. Ship a short quickstart, action reference, artifact-role guide and stable-code troubleshooting catalog with copy-paste examples tested against the implementation.
- Define a versioned local HTTP contract for new exploration, recorded replay, additional-budget continue and interrupted-stage resume before implementation. Use consistent request_id, study_id and execution_id; persist idempotency key plus canonical request digest, return the original result for an identical replay and reject a conflicting payload. Specify accepted response, progress and per-stage error schemas. The new UI defaults to preview plus requested native solids with analysis explicitly opt-in; preserve explicit legacy mesh_run_solvers requests through a documented adapter rather than silently changing their meaning. Declare the effective mode before submission. Do not require a new public SDK or hosted service.
- Add a shared error catalog covering stage timeout, native export, solver, selected re-evaluation, unsupported domain, corrupt cache/artifact, missing artifact, disk full, publication failure, interrupted execution, unavailable historical runtime, invalid identifiers/origin and lost action response. Every applicable error reports operation/stage, actual elapsed/limit or invalid value, stable code and documentation anchor, safe actionable first/last-line fix, recovery class, side-effect state, bounded retries and effective model/runtime settings. Unexpected failures include a correlation ID with protected local trace; expected validation/capability errors need no stack trace. Redact credentials and credential-bearing URLs recursively, including dependency causes. Rejected API actions use appropriate non-2xx problem-details responses; a successful status GET may return 200 with a truthfully failed job. Normal infeasibility, cancellation and duplicate proposals are domain outcomes, not automatically transport errors.
- For stage failures, retain verified artifacts and identify the failed stage, actual limit and stopped execution before an explicit retry. Allow at most one automatic retry for a classified transient failure; deterministic physics, unsupported capability and invalid-input failures require changed input or an explicit supported-mode decision. For publication/corruption failures, inspect persisted execution ownership, manifest and artifact hashes before one repair/rebuild attempt; restore writable storage first on disk-full. Never rerun an action with an unknown outcome without reconciling its persisted idempotency record. Connection recovery uses bounded exponential backoff (1, 2, 4, 8, 15 seconds, then a visible disconnected state and explicit retry); this bounds consecutive failed requests, not the duration of legitimate running jobs. Restored connectivity first resolves the original request. Historical-runtime errors show required/available versions and offer recorded replay or explicit new-version lineage; validation errors identify accepted fields and state that rejected requests changed nothing. Origin failures must never recommend disabling origin protection.
- Inventory operational settings and document override surface, precedence, safe range and effective provenance for concurrency, timeouts, memory/resource caps, cache rebuild, polling and diagnostics. Preserve truthfulness, artifact integrity, immutable lineage requirements and stale-result rejection as non-overridable invariants. Version durable manifests with compatibility and migration rules; retain original records, reject unsupported versions explicitly, and test older-record reading, interrupted migration and rollback without manufacturing invented evidence. Test documented action examples, recursive redaction, HTTP failure contracts, ambiguous submissions and recovery after restart. Keep dependency isolation and existing build/test entry points; public SDKs, community infrastructure, hosted deployment and generic telemetry remain outside this repair scope.
<!-- /autoplan-accepted:dx -->
## Review record

### CEO Step 0 — diagnosis, scope and premises

Review depth: implementation planning for P0–P2; P3 remains a research-backed architecture milestone, not a claim of validated novel engine synthesis. Mode SELECTIVE EXPANSION is selected by the user's invoked autoplan workflow, not by a stored personal preference. Base fallback is main, but there is no resolvable base commit or remote; git history cannot prove previous fixes.

The user premise is partly supported: geometry generation holds back delivered assemblies, but meshing alone cannot expand the upstream design grammar. Saved current-study evidence was re-derived: 9/12 assembly evaluations failed at 120 seconds; 3/12 produced assemblies and then returned unsupported_section for analysis; all 12 were labelled complete. All 12 selected rows contain five failed engineering checks. Twenty focused tests passed in 292.818 seconds; they do not exercise this complete real orchestration failure.

Current → proposed → desired trajectory:

```text
Fixed grammar + deterministic sequence + misleading completion
  -> durable staged generation + explicit exploration + feasibility-aware comparison
  -> extensible, experimentally calibrated computational engineering system
```

Alternatives considered: mesher-only replacement would preserve the fixed grammar and false status; complete rewrite would discard useful physics, geometry audits and reproducibility without resolving unknown kernel costs; staged repair preserves those assets while adding missing capabilities. Proposed delivery order P0→P1→P2→P3 is a taste decision for the final gate. It preserves all requested outcomes rather than dropping design freedom.

Reuse references: `vega/run_index.py` atomic index replacement, `vega/manufacturing.py` cached catalog, and `vega/meshing/cad.py` versioned CAD caching. Avoid the coarse completion and exception boundaries in `server.py` and input-space-only diversity in `vega/design_search.py`.

Landscape: [LEAP 71 describes Noyron](https://leap71.com/Noyron/) as engineering logic, physics and manufacturing constraints in one framework; its [rocket program](https://leap71.com/rp/) explicitly discusses physical validation. [Gmsh documentation](https://gmsh.info/doc/texinfo/gmsh.html) separates CAD kernels from mesh generation/size controls. Inference for Vega: the valuable product is a traceable engineering loop; a new tessellation engine alone cannot supply missing design reasoning. No competitor benchmark or customer demand was established by this review.

Five small improvements within the existing scope: persistent stage elapsed time; separate attempted/feasible/exported counts; immediate partial-artifact inspection; explicit replay/new labels; plain solid-versus-fluid-domain descriptions. Their implementation and regressions remain proposed under P0/P2. No new infrastructure, model-training platform or cloud service is added.

Complexity: estimated 8–14 existing files plus focused tests across multiple delivery waves. Keep job manifest logic separate from the already dense request handler; reuse file-backed persistence before considering infrastructure. P3 cannot be promised as a one-day software task: the required physics and experimental evidence determine its schedule.

Temporal questions: foundations require a source snapshot and contract/schema; core logic requires exact feasibility rules and replay lineage; integration must account for process-global chemistry/kernel state and cached geometry; verification must cover late process completion after cancellation and restart. P0/P1 implementation effort is provisionally several engineering days plus native benchmark time; P3 remains unestimated until a supported architecture pair and validation domain are selected. No automated coding speed multiplier is evidence for hardware validation speed.

| ID | Decision | Classification | Authority / disposition |
|---|---|---|---|
| D1 | Preserve all requested design outcomes; stage delivery P0→P3 | Taste | Autoplan provisional recommendation; final approval pending |
| D2 | Keep replay deterministic and make new exploration explicit | Mechanical | Autoplan P5; repairs the named repetition issue |
| D3 | Preserve tolerances and partial artifacts | Mechanical | User print/design intent; autoplan P1 |
| D4 | Treat unknown manufacturing/physics evidence as unresolved | Mechanical | Required to distinguish geometry from demonstrated feasibility |
| D5 | Do not replace the entire codebase or install new services | Mechanical | Autoplan reuse and simplicity principles |

<!-- autoplan-accepted:ceo -->
- Required stages are frozen when a request is accepted. Preview mode requires evaluated geometry only; solid mode requires the selected core or assembly solid plus its integrity audit; analysis mode additionally requires the explicitly requested domain and analysis stages. Unrequested stages are not required. A stage records pending/running/succeeded/failed/unsupported/cancelled/interrupted and evidence separately. All required stages succeeded means candidate complete; a required stage failure with a usable requested artifact means partial; required-stage failure without one means failed; explicit cancellation means cancelled with retained artifacts. Unsupported required stages are failures of capability, not successful analysis. Failed optional stages appear as warnings without failing the requested output. Study execution can complete with zero feasible candidates; the outcome summary must distinguish complete search from feasible-design count and export/analysis failures. Test the mode/stage/outcome matrix including unsupported and optional failures.
- On restart, recover durable manifests and verify published artifact references; mark unfinished stages interrupted and perform no automatic expensive restart. Resume interrupted work is an explicit action within the original attempt budget and lineage: retry only unfinished stages under a new execution ID, retaining the same proposal/attempt index and recording retry history, without double-counting attempts. Continue search adds an explicit additional attempt budget after the prior proposal cursor; it is distinct from resume. The original budget includes completed, duplicate, rejected and interrupted attempts; not-yet-started slots remain pending, or become cancelled if the study is cancelled. Persist every proposal before evaluation so recovery cannot silently sample a replacement. Test crash before/after artifact publication and both cancellation-versus-completion orders; late execution results cannot overwrite a terminal cancellation or newer execution.
- Replay means reproduce the recorded proposal sequence and recorded evaluation-feedback inputs, not promise bit-identical solver/tessellation output on another runtime. Persist exact proposals, adaptive feedback, generator schema/version, relevant runtime/material provenance and artifact hashes. Historical artifacts remain viewable. Re-evaluation under historical versions is offered only when the required runtime is retained and available; otherwise report unavailable and offer an explicitly new lineage under current versions. Preserve a replay adapter or immutable recorded proposals when replacing the legacy generator. Test fixed-seed replay, adaptive feedback replay, continuation cursors and unavailable historical runtimes without silently substituting a current generator.
- Before feasibility ranking changes, define a reference decision: an engine designer compares assembly candidates under fixed requirements to choose a fit/flow prototype for further evaluation. Use the existing rectangular and elliptical assembly cases as initial within-family fixtures; do not count those section choices as new propulsion architectures. A usable solid must identify its intended interfaces, dimensions, units and unresolved manufacturing limits. Verify each hard screening check's units, applicability, source and evidence on a known admissible case and deliberate violation cases; label results model-screened, never experimentally validated without test evidence. P3 must select a distinct connectivity pair and its validation domain before topology implementation, with an explicit supported-capability milestone and baseline comparison; broad architecture synthesis remains in scope but is not unrestricted implementation-ready work.
- Preserve the 64-attempt benchmark and compare staged search against the existing deterministic configuration baseline and selective detailed analysis. Report distinct, model-screened feasible yield, decision time, export reliability and compute cost at identical requirements and tolerances. Choose performance work from measured stage costs; do not reduce user-requested budgets to manufacture a speed claim. P3 expansion requires a demonstrated improvement in supported configuration coverage, constraint satisfaction or decision time relative to the current generator, with failed comparisons recorded as a reason to revise the approach rather than silently declare success.
- Make admission atomic and idempotent; validate cancel/resume IDs and origins with existing server rules. Require execution-token checks for late worker results and test both cancellation/completion orders. Protect publication from disk-full/replace failure; use a compatible schema-versioned historical reader, leave old data unchanged, and provide app-only rollback that preserves manifests and artifacts. Add accessible status text, keyboard actions, and readable narrow-layout progress/downloads. Verify these at the HTTP/orchestration and browser boundaries, not only helper functions.
<!-- /autoplan-accepted:ceo -->

### CEO independent review and decisions

Spec review: two complete reviews; first 8/10 with three gaps, second 9/10 PASS with all three fixes confirmed. Metrics persisted to the global gstack analytics record. Native CEO review input SHA: `3bf7185200c81ab4794fbe63f1f8c1eddd06424a18cb54312c3008e71d4fec98`; completed with four findings: reference task unclear (high), evidence behind feasibility unclear (high), outcome performance comparison missing (medium), expansion milestone insufficiently bounded (high). Accept the clarifications below as provisional plan choices under autoplan P1/P3/P5. They preserve the user's original outcomes.

The outside transfer was rejected by automatic approval review; user then explicitly chose “Keep the review local (recommended)”. Outside CEO/Design/DX/Eng opinions are therefore skipped by user instruction. No cross-model consensus is claimed.

| CEO dimension | Native result | Outside | Consensus |
|---|---|---|---|
| Premises | Mesh problem real; physics/check validity unverified | Skipped | N/A |
| Right problem | Reliability yes; define useful engineering decision | Skipped | N/A |
| Scope | Retain staged repair with bounded expansion | Skipped | N/A |
| Alternatives | Compare staged search and deterministic baseline | Skipped | N/A |
| Competitive risk | No demonstrated comparative advantage yet | Skipped | N/A |
| Six-month trajectory | Avoid reliable generation without engineering value | Skipped | N/A |

### CEO Sections 1–11

1. Architecture: the single callback couples screening to full export/analysis. Retain the current computation libraries but isolate orchestration and publication. A single durable manifest owns mutable study state; workers return immutable stage results and cannot independently overwrite cancellation. Required stages are fixed at admission.

```text
Requirements -> validate/freeze -> durable proposal ledger -> cheap screening
                                                        | failure/duplicate -> recorded outcome
                                                        v
Evidence-qualified selection -> bounded solid workers -> audit -> artifact publication
                                                        v
                                      requested analysis queue -> result/evidence record
UI polls manifest -> inspect/compare/download/resume/cancel
```

2. Errors: assembly timeout is currently converted to a warning while success remains. Move error boundaries around each selected attempt and each stage. Retain existing solids on downstream failure; record exception class, attempt/execution IDs and artifact disposition. The registry below covers the new orchestration boundaries.

3. Security: this is a local application; no cloud or new authentication service is proposed. New cancel/resume actions must use existing host/origin checks, validated IDs and request size limits; output paths remain derived from server-generated identifiers. Avoid shell interpolation of user input. Concurrent publication and arbitrary-path parameters are the material risks introduced by this plan; tests must cover rejected IDs and stale execution tokens.

4. Data and interactions: restart, late subprocess completion, double-click, changed requirements and cancellation are distinct paths. Admission must check-and-create under one lock, with idempotent submission tokens so a retry cannot duplicate a study. A worker completion is accepted only if its execution token is still current; test completion-before-cancel and cancel-before-completion. Empty feasible sets are normal results, not endless loading.

```text
missing/wrong input -> reject before job creation
valid input -> persisted pending -> running -> complete | partial | failed
running -> cancel request -> cancelled (late completion cannot overwrite)
process restart -> interrupted -> explicit resume with new execution token
all infeasible -> search complete, feasible=0, diagnostics retained
```

5. Code quality: `server.py` mixes HTTP handling, native build, analysis and study selection. Extract only the state/lifecycle boundary and reuse existing domain helpers; avoid a generic workflow framework. Broad outer exception handling may preserve service availability, but stage handlers must retain specific exception causes rather than collapse everything into a success warning.

6. Tests: the 20 focused tests passed, but the mocked first-publish callback does not prove real artifact publication precedes analysis. Add controlled subprocess pause/release tests at the orchestrator boundary. Seed tests protect reproducibility but do not prove useful novelty; require geometry-equivalence and meaningful-difference fixtures. Native benchmarks are necessary for kernel performance and cannot be replaced by mocked tests.

```text
admission/state -> unit: nil/type/duplicate/terminal transitions
orchestrator -> integration with paused workers: timeout/cancel/restart/order
search -> unit+fixtures: replay/continuation/fixed inputs/duplicate shapes
native export -> integration: rectangular+elliptical+historical failure
UI -> browser: reload/partial/zero-feasible/download labels
physics -> reference cases: known passing and known violation; no hot-test claim
```

7. Performance: three suspected costs are assembly CAD construction, native export/audit and downstream CFD/FEA; no stage p99 is measured. The saved 120-second failures establish a timeout boundary, not which operation consumes it. Profile before increasing concurrency; duplicated large JSON/mesh arrays can exhaust memory. Existing CAD cache reuse and removal of duplicate evaluations precede new infrastructure or looser tolerances.

8. Observability: current study persistence cannot reconstruct all in-flight work after restart. Store per-stage times, heartbeat, worker execution ID, specific error and verified output references. User-facing warnings must name the unavailable artifact and action; no invented ETA. A compact local diagnostics download supports reproduction without introducing remote monitoring.

9. Rollout: no committed baseline exists, so preserve a source/dependency fingerprint and existing data before implementation. Add a schema-versioned reader that keeps historical records read-only; old records are labelled legacy/unverified rather than rewritten to imply new checks. Deploy writer plus compatible reader before enabling new lifecycle actions. Rollback disables new admission, stops owned workers, preserves new manifests/artifacts and restores the previous application snapshot; do not restore over user-generated data.

```text
snapshot -> compatible reader -> new manifest writer -> lifecycle tests -> enable actions
failure -> stop new admission -> stop owned work -> preserve data -> restore app snapshot
```

10. Trajectory: durable provenance, geometry identity and fidelity labels support later design-family expansion. A large generic optimizer or new surrogate-model platform would be premature; keep interfaces tied to executable physics/geometry contracts. Reversibility is high for orchestration changes and lower for replacing generator behavior, hence retained proposal records and versioned adapters. P3 is a gated engineering milestone, with no promised hardware-validation schedule.

11. UX: lead with the engineering task, then trustworthy progress, candidate differences and artifacts. Show loading, interrupted, empty, error, partial and complete states; distinguish simulation fluid domains from physical solids. Preserve keyboard access and visible text statuses instead of color alone. Desktop candidate comparison is the initial recording workflow; narrow views must keep stage status and downloads readable without compressed tables.

### Error & Rescue / Failure Modes registry

| Boundary | Failure / exception | Proposed rescue | User result | Required proof |
|---|---|---|---|---|
| Admission | ValueError/type/ID/origin rejection | Reject before manifest creation | Specific input error | Unit + HTTP test |
| Evaluation | TimeoutExpired / worker exit | Terminate owned worker tree; record stage failed | Partial or failed per required-stage matrix | Controlled timeout integration |
| Native export | CalledProcessError / malformed output | Keep previous verified artifacts; refuse invalid publication | Export failed with diagnostic | Native + injected failure |
| Persistence | OSError / disk full / partial JSON | Atomic publication; stop admission if durable state cannot be written | Explicit persistence failure | Write/replace fault injection |
| Restart | Worker lost / unfinished stage | Recover manifest; mark interrupted | Resume action and retained outputs | Restart before/after publish |
| Analysis | Solver exit / unsupported domain | Preserve solid; apply requested-stage matrix | Analysis unavailable/failed, solid still visible | Optional/required matrix |
| Cancel race | Late completion with obsolete token | Reject stale update; cleanup owned temporary output | Cancelled remains cancelled | Both completion orders |
| Cache read | Invalid hash/schema/version | Invalidate and rebuild; never silently trust | Rebuild status | Corrupt/version/tolerance fixtures |
| Selection | No feasible candidates | Finish search with diagnostics | Zero feasible, not an error spinner | All-infeasible test |

These are planned rescues, not implemented guarantees. Current critical gaps: false completion after assembly failure, loss of in-memory job state, and candidate evaluation outside its failure boundary.

### NOT in scope / what already exists / dream delta

No requested repair is dropped. Flight certification, complete airframe synthesis and launch operations are outside this software plan. Reuse the material catalog, run index, CAD cache, mesh integrity audits, deterministic proposals and existing reference tests. The delta is reliable, evidence-labelled exploration first; the eventual goal remains a larger verified design grammar, not merely a faster mesh gallery.

### CEO completion summary

Step 0 and Sections 1–11 examined. Nine error/rescue rows, three current critical implementation gaps. Six diagrams above cover architecture, shadow/state paths, tests and rollout/rollback. Native CEO: four findings accepted into the proposal; spec reviewer: three fixes confirmed. Outside skipped by user. No implementation is cleared yet. Measurements and P3 architecture choice remain explicit gates, not hidden assumptions. No changes to Vega executable code.

### CEO reality checks and task ledger

REALITY: premise-table finding Meshing is not the only constraint; fixed proposal grammar and deterministic seed are explicit. unverified=1 for the exact dominant CAD operation pending profiling. vega/design_search.py:19
REALITY: already-done finding No committed base or remote exists; previous fix history cannot be established. Existing proposed reliability specification overlaps this plan. SPEC-mesh-generation.md:1
REALITY: surface-check pass Current job, run and design-study routes were inspected; new resume/cancel actions are proposals, not existing routes. server.py:279
REALITY: binding-decisions pass User requests multiple physically constrained printable designs and local reviews; staged plan preserves them. docs/VEGA_SYSTEM_REPAIR_PLAN.md:9
REALITY: numbers pass Saved study counters and failures were recomputed; runtime targets remain estimates and require baseline measurement. data/studies/fb256493627d461a8913c77f51cbf987.json:1
REALITY: deferred-asks pass No linked issue; no user-requested repair is removed from scope. docs/VEGA_SYSTEM_REPAIR_PLAN.md:9
REALITY: pr-count pass Local uncommitted repository; no PR creation is planned. Delivery waves are not separate PR authorization. SPEC-mesh-generation.md:1

- [ ] T1 — Durable lifecycle, truthful outcomes and partial artifacts. Verify timeout, restart, cancellation, all-infeasible and optional/required-stage cases.
- [ ] T2 — Stage profiling and early artifact delivery. Verify unchanged tolerances on native fixtures and the 64-attempt benchmark.
- [ ] T3 — New/replay/continue semantics and evidence-qualified ranking. Verify exact proposal replay, continuation accounting, geometry equivalence and reference checks.
- [ ] T4 — Specify the first topology pair and reference benchmark before implementing broader design grammar. Verify measurable connectivity change and supported engineering checks.

Task history was saved locally; the helper identifies the unborn branch as unknown. This is not a commit-linked implementation record. All task effort estimates are provisional, and physical validation has no inferred coding-speed multiplier.

### Design review — seven passes

Methodology read through EOF, including recovered truncated pass text. UI scope: generation progress, results, comparison, artifacts and recovery. Initial impression 6/10: useful backend semantics, insufficient presentation contracts. No DESIGN.md found in the inspected paths; reuse current workspace/navigation and existing CSS tokens before adding styles. Designer binary unavailable; no generated mockups. Browser control returned unavailable, so pixel/contrast validation remains an implementation check.

Native design review completed on input `35a25c0fd8db9e78b18f099469fb8a5ff4b27b47cfb3ae40f47bd3412e40592a`: seven findings, four high and three medium, none critical. Outside skipped by user. Each finding is accepted as a structural clarification under autoplan P1/P5; the specific arrangement of the candidate table and side-by-side viewer is a provisional taste decision.

1. Information architecture: 6→8/10. The original KPI inventory did not prioritize the user's next decision. Specify study state/action first, truthful counts second, selected results third, expandable timing/errors last. Primary artifact and comparison controls are explicit. Remaining visual confidence requires rendered verification.
2. State coverage: 7→9/10. Backend semantics existed, but no-studies, no-artifacts-yet, connection loss and lost/corrupt saved artifact states lacked presentation. The accepted block below supplies visible content and actions. Preview disposition changes retain identity and never silently replace the viewed candidate.
3. Journey: 6→8/10. An early preview could look like the promised final design before later rejection. The sequence now reads request → credible progress → provisional inspection → evidence → comparison → intended solid download. Stable identity and visible reasons preserve trust through setbacks.
4. Specificity: 7→8/10. Classifier OPERATE: this is an engineering workspace, not a marketing page. Use aligned unit-bearing comparisons and a large selected geometry view; avoid decorative KPI mosaics or achievement claims. No evidence of a required generic hero/card design was found in the plan; the artifact is the visual anchor.
5. Design system: 5→8/10 at plan level. No verified design-system document is available; capture and reuse the current CSS color/type/spacing tokens when implementing. New labels and actions must inherit those tokens, with body/status text at least 16px and verified body contrast at least 4.5:1; do not introduce a font download or wholesale visual rebrand for this repair.
6. Responsive/accessibility: 5→8/10. The plan now names focus preservation, meaningful live announcements, visible non-color status and a textual alternative to 3D. At narrow widths the comparison is a selected-candidate detail view with a candidate selector; the full comparison table may scroll horizontally with fixed row labels. Keyboard actions and touch targets require browser verification.
7. Decisions: seven structural clarifications auto-decided provisionally; no requested feature is dropped. Table-plus-linked-viewer composition remains a taste item at the final gate. No actual UI changes or visual pass is claimed.

```text
Study header: execution state + primary next action
  -> counts: attempts/budget | screened feasible | requested artifacts ready
  -> selected candidate table <-> geometry viewer
  -> artifact/evidence panel -> intended solid download
  -> expandable rejected/provisional diagnostics and stage details
```

| State | Visible result | Action |
|---|---|---|
| No studies | Explain requirements-to-candidates workflow | Enter requirements |
| Running, no artifact | Attempt counts, stage, elapsed and last heartbeat | Cancel; inspect stage detail |
| Provisional artifact | Stable candidate ID and provisional label | Inspect without selection promise |
| Partial | Available artifact plus failed requested stage | Inspect/download diagnostic; stage details |
| Zero feasible | Search finished and violated-constraint counts | Inspect diagnostics; revise requirements into new lineage |
| Connection lost | Last known results and timestamp; connection warning | Retry connection; do not mark server job failed |
| Interrupted | Retained verified outputs and original budget | Resume interrupted work |
| Corrupt/missing artifact | Artifact unavailable; other results retained | Rebuild/retry explicitly; never stale download |
| Historical runtime absent | Recorded proposals/artifacts accessible | Replay records or start new-version lineage |
| Complete | Requested outputs ready; evidence remains explicit | Compare and download requested solid |

Litmus (plan-level): brand first screen not specified; artifact anchor yes; scannable headings yes; one purpose per section yes; decorative cards unnecessary; motion unnecessary for this workflow; hierarchy must work without shadows. Outside/consensus cells N/A for all seven. Overall six-pass minimum 5→8/10; these are editorial ratings of the amended specification, not measured UI quality.

<!-- autoplan-accepted:design -->
- Present study execution state and primary action first, then attempts/budget, model-screened feasible count and requested artifacts available, then selected candidates. Keep detailed timing and errors expandable. Distinguish finished search, zero feasible candidates and incomplete exports. Render a unit-aligned comparison with objective direction, constraint results, evidence fidelity/unknowns, meaningful-difference text and linked geometry; classify dimensional, shape and connectivity changes. Show failed candidates as inspectable diagnostics outside the default feasible comparison. Pareto choices are tradeoffs, not a fabricated single winner.
- Define each artifact by role, actual available format and units: core solid, assembly solid, preview, nozzle fluid domain (analysis only), airpath fluid domain (analysis only). Never advertise STEP unless generated. Make the requested available solid the primary download; put integrity, manufacturing eligibility, evidence and unresolved/failed checks beside it. Diagnostic downloads say diagnostic. Early previews carry stable IDs and provisional labels, update disposition with reasons, and stay inspectable if rejected or deduplicated without silently switching the current view.
- Provide the visible state/action table specified in this plan: no studies -> enter requirements; running without artifacts -> stage/counts/elapsed/cancel; partial -> inspect retained output and error; zero feasible -> violations/diagnostics/revise requirements into new lineage; connection lost -> retained last-known results/timestamp/retry without changing job outcome; interrupted -> resume within original budget; corrupt artifact -> unavailable and explicit retry/rebuild; unavailable historical runtime -> recorded replay or explicitly new-version lineage; complete -> compare/download with evidence. Distinguish resume, additional-budget continue, new exploration and recorded replay in an action menu; show requirements lineage and requested output mode before submission. Execution retries remain subordinate to the study in history.
- Preserve focus and selected candidate during updates; announce meaningful stage changes through a polite live region, not every poll. Make status/checks/dimensions/downloads available outside the 3D canvas, use visible focus and non-color status, and verify keyboard-only comparison/cancel/recovery. Keep existing workspace visual tokens; inventory them before changes, use body/status text at least 16px, verify body contrast at least 4.5:1 and touch targets at least 44px. Narrow layouts show selected-candidate detail plus selector; comparison overflow has clear row labels and reachable actions. Verify long names, unknown values, large result sets and all state-table paths in browser tests/manual checks. Do not claim rendered compliance from this source-only review.
<!-- /autoplan-accepted:design -->

### DX review — local developer workflow

Mode: DX POLISH. Persona: QuinV's founder/engineering maintainer operating the local Windows workbench; a coding assistant is a secondary API/error consumer. This is not a new public SDK or hosted developer platform. Source evidence: README.md documents multiple isolated native environments; setup.ps1 already offers setup and CheckOnly; start.ps1 runs vega.runtime then server.py; runtime readiness currently requires all dependency groups together. Reuse these entry points. A clean install was not executed, and time to hello world (TTHW) is unknown.

**Predicted developer experience, not an observed user session:** I want to open Vega, give it requirements, and see a meaningful result without having to understand every native dependency. The existing startup scripts give me an entry point, but a dependency failure does not tell me whether a simpler requested output can still run. Once the server opens, I need a small example that tells me what successful publication looks like. A 64-attempt study is useful for a benchmark but too expensive as my first troubleshooting step. If I lose the response to a submission, I need to find that request before starting another study. If an assembly fails, I want to keep the core and see the actual stage, timeout and next action. I also need to know whether a restored result used the same model versions. As the maintainer, I want a short diagnostic report that a coding assistant can interpret without exposing secrets or changing the engineering checks. I will trust the workflow when the first preview, full solid, screening results and analysis evidence each have a clear meaning, and when restarting Vega preserves that meaning.

Reference benchmark: use the skill's supplied examples as qualitative design references only: Stripe for consistent IDs/idempotency, Rust for stable diagnostic codes, and migration pipelines for versioned records. No current competitor timings or product rankings were independently measured. Target: on an already provisioned reference machine, dependency check through an inexpensive screened preview within five minutes; record full fresh-install time separately, with no invented five-minute install promise. A preview is not a native solid, physics verification or print eligibility. The native-solid and 64-attempt performance gates remain separate.

| Journey | Existing evidence / predicted friction | Planned acceptance |
|---|---|---|
| Discover | Long README contains real limitations but lacks a short repair-workflow entry | One quickstart index, explicit output meanings |
| Install | setup.ps1 and isolated CAD targets exist | Required/optional capability checks, actionable failure, tested setup instructions |
| Hello world | No inexpensive reproducible first-preview fixture in this plan | Checked-in fixture, exact commands and expected output, measured ready-machine time |
| Real usage | New/replay/continue/resume semantics are planned | Versioned request/response examples, output mode and effective settings |
| Debug | Partial states are planned; complete recovery contracts were missing | Code-linked errors, retained outputs, idempotent reconciliation before retries |
| Upgrade | Runtime/grammar versions are recorded in the proposal | Versioned manifest reader, compatibility policy and migration/rollback tests |

First-time confusion report (predicted sequence, no fabricated timestamps): Which dependencies are needed for my output? What counts as a successful preview? Did my lost submission start? Can I retry without losing the core? Can old studies still be read? All five are implementation acceptance checks below.

Native independent review INPUT dx a6503ea2c677efc3f5d2dd1811ead7b5211ce9e6c6cad25893be490731e38783: ten findings, five High and five Medium. All accepted as requirements, not claimed fixed in software. High findings concern stage repairs, persistence reconciliation, lost action responses, unavailable historical runtimes and rejected-request guidance. Medium findings concern quickstart, wire contracts, shared error/redaction schema, documentation and operational overrides. Outside review skipped by user; all six dual-voice dimensions have no cross-provider consensus. Native scores: getting started 3, API 7, errors 4, docs 4, escape hatches 6; overall 5. CAP6 applies to missing recovery/fix details in the earlier proposal. No CAP4 established for proposed behavior.

Eight parent passes (plan specification ratings, not tested product quality): getting started 3→8, API 7→8, errors 4→8, documentation 4→8, upgrade 5→8, environment 5→8, ecosystem 6→8 (reuse existing scientific stack; public community expansion outside scope), measurement 4→8. All passes used their corresponding Hall of Fame reference; reference statistics are not adopted as product evidence. Overall minimum 3→8. Competitive tier and achieved TTHW remain unmeasured. First meaningful preview is the planned demonstration; no new marketing sandbox. Principles covered by quickstart, runnable fixture, precise states, documented defaults, contextual errors, early preview and machine-readable diagnostics.

<!-- autoplan-accepted:dx -->
- Reuse setup.ps1, start.ps1 and vega.runtime to document and verify a clean-environment quickstart, with prerequisites, isolated CAD installations, required versus optional capabilities for each requested mode, exact setup/start/submit commands and expected output. Add an inexpensive checked-in fixture and measure readiness-to-first-screened-preview on a declared provisioned machine against a five-minute target; separately report clean install time and full-solid/64-attempt timings. Do not claim an unavailable dependency can be bypassed when the requested stage needs it. Ship a short quickstart, action reference, artifact-role guide and stable-code troubleshooting catalog with copy-paste examples tested against the implementation.
- Define a versioned local HTTP contract for new exploration, recorded replay, additional-budget continue and interrupted-stage resume before implementation. Use consistent request_id, study_id and execution_id; persist idempotency key plus canonical request digest, return the original result for an identical replay and reject a conflicting payload. Specify accepted response, progress and per-stage error schemas. The new UI defaults to preview plus requested native solids with analysis explicitly opt-in; preserve explicit legacy mesh_run_solvers requests through a documented adapter rather than silently changing their meaning. Declare the effective mode before submission. Do not require a new public SDK or hosted service.
- Add a shared error catalog covering stage timeout, native export, solver, selected re-evaluation, unsupported domain, corrupt cache/artifact, missing artifact, disk full, publication failure, interrupted execution, unavailable historical runtime, invalid identifiers/origin and lost action response. Every applicable error reports operation/stage, actual elapsed/limit or invalid value, stable code and documentation anchor, safe actionable first/last-line fix, recovery class, side-effect state, bounded retries and effective model/runtime settings. Unexpected failures include a correlation ID with protected local trace; expected validation/capability errors need no stack trace. Redact credentials and credential-bearing URLs recursively, including dependency causes. Rejected API actions use appropriate non-2xx problem-details responses; a successful status GET may return 200 with a truthfully failed job. Normal infeasibility, cancellation and duplicate proposals are domain outcomes, not automatically transport errors.
- For stage failures, retain verified artifacts and identify the failed stage, actual limit and stopped execution before an explicit retry. Allow at most one automatic retry for a classified transient failure; deterministic physics, unsupported capability and invalid-input failures require changed input or an explicit supported-mode decision. For publication/corruption failures, inspect persisted execution ownership, manifest and artifact hashes before one repair/rebuild attempt; restore writable storage first on disk-full. Never rerun an action with an unknown outcome without reconciling its persisted idempotency record. Connection recovery uses bounded exponential backoff (1, 2, 4, 8, 15 seconds, then a visible disconnected state and explicit retry); this bounds consecutive failed requests, not the duration of legitimate running jobs. Restored connectivity first resolves the original request. Historical-runtime errors show required/available versions and offer recorded replay or explicit new-version lineage; validation errors identify accepted fields and state that rejected requests changed nothing. Origin failures must never recommend disabling origin protection.
- Inventory operational settings and document override surface, precedence, safe range and effective provenance for concurrency, timeouts, memory/resource caps, cache rebuild, polling and diagnostics. Preserve truthfulness, artifact integrity, immutable lineage requirements and stale-result rejection as non-overridable invariants. Version durable manifests with compatibility and migration rules; retain original records, reject unsupported versions explicitly, and test older-record reading, interrupted migration and rollback without manufacturing invented evidence. Test documented action examples, recursive redaction, HTTP failure contracts, ambiguous submissions and recovery after restart. Keep dependency isolation and existing build/test entry points; public SDKs, community infrastructure, hosted deployment and generic telemetry remain outside this repair scope.
<!-- /autoplan-accepted:dx -->

DX implementation checklist: [ ] runnable fixture/quickstart; [ ] mode capability readiness; [ ] consistent action contract; [ ] all catalog errors and redaction; [ ] versioned migration examples; [ ] declared resource settings; [ ] measured preview and install timings; [ ] tested examples and recovery. These are planned checks, not completed validations. Tasks map to P0 lifecycle/error contracts, P1 startup/performance and P2 action documentation; no separate platform expansion.

### Final engineering review — 2026-11-05

Scope accepted as proposed under Autoplan's authorized planning decisions; no implementation approval inferred. Count estimate: at least 12 authored source/UI/test files across the roadmap, two proposed ownership boundaries (durable job coordinator and supervised worker runner), zero new services. Keep the local architecture. No git history comparison is possible on the unborn branch; no remote is configured. No TODOS.md was found in the inspected file inventory. P3 remains in this plan, conditional on its engineering domain gate, rather than silently becoming an optional backlog item.

**Independent native review:** INPUT eng 643953006b348dc11391b0388a39b0adef0c35a80573951fd781fd239b7b48a7. Seven findings (five High, two Medium), all incorporated below. Outside voice skipped by user. Architecture, tests, performance, security, errors and deployment therefore have native coverage but N/A cross-provider consensus. These findings describe gaps in the proposal, not seven newly reproduced runtime defects.

| ID | Severity / confidence | Motivating proposal and existing evidence | Disposition |
|---|---|---|---|
| E1 | High / 9 | P0 says atomic replacement; server.py:161 and vega/run_index.py's replacement pattern do not establish a multi-file transaction | One manifest authority and coordinator; indexes derived |
| E2 | High / 8 | P1 says bound workers; server.py:345 already limits active generation, but new scheduling must retain aggregate limits | Preserve admission cap, bound queues/storage, measure resource defaults |
| E3 | High / 8 | P0 introduces resume/rebuild paths; server.py:230 validates existing run IDs and server.py:325 caps payload size | Extend existing boundaries to every new path; no claim existing routes lack these controls |
| E4 | High / 9 | P2 adds adaptive feedback; vega/design_search.py:19 currently deterministic sequential proposals | Ordered feedback frontier and atomic cursor publication |
| E5 | High / 9 | Accepted CEO requirement says retry unfinished stages | Define dependency fingerprints so stale descendants cannot survive a changed parent |
| E6 | Medium / 8 | P2 proposes feasibility/Pareto ranking; vega/design_search.py:70 currently sorts failure counts and score | Finite values, explicit units/tolerances and deterministic ties |
| E7 | Medium / 8 | P0 requires bounded cleanup; server.py:112 uses subprocess.run timeouts | Add real Windows subprocess-tree integration test, beyond mocks |

Parent architecture review: E1, E3, E4 and E5 accepted. Compare two shapes: (A) one in-process coordinator owns schema-versioned per-study manifests, admission and execution leases; workers only return results; derived indexes may be rebuilt. (B) SQLite owns jobs, requests and leases while artifact files remain external. Choose A initially because the current single-writer local service and whole-study reads fit its boundary; B adds migration without removing the filesystem publication protocol. Revisit B only for independently updated/query-heavy state or multiple coordinator processes. This is an engineering proposal, not an assertion that atomic replacement alone gives transactions. Use a process-level data-root lock plus per-study revision checks. Proposed interface: submit(request), act(study_id, action), status(study_id), commit_result(execution_token, result); no exposing storage internals to workers.

Eight architecture flags checked: avoid shallow stage setters by enforcing transitions inside coordinator; parse wire data once to avoid information leakage; group ownership by job state rather than execution-order modules; no new pass-through wrappers; one manifest writer prevents split ownership; route legacy and new submissions through one owner; keep worker/coordinator internals private; derive UI capability/stage labels from the shared versioned response contract with mismatch tests. Distribution remains the existing local Windows setup; hosted install/publishing is outside scope.

```text
UI / local HTTP client
  -> validate host/origin/body/IDs -> reject without mutation
  -> coordinator.submit / act [admission + request digest + root lock]
       -> authoritative study manifest (revision, request, proposals, leases)
       -> bounded ready stages -> supervised isolated worker
            -> immutable artifact bytes -> audit/hash -> commit_result(token)
       -> verify token + dependencies -> publish manifest reference
       -> derived history index -> status/progress -> UI and solid download

stage DAG: recorded proposal -> model screening -> core / assembly construction
              -> native solid -> integrity audit -> requested domain -> solver
              -> selection descriptors / ranking (evidence and fidelity explicit)
crash: recover manifest -> verify artifacts + fingerprints -> interrupted
resume: explicit new execution -> invalid descendants pending -> retained history
cancel: persist terminal intent -> stop owned process tree -> reject late writes
```

Parent code-quality review: E6 and one duplicate-publication-policy concern accepted. Existing server.py:136,161,171 and 221 repeat temp-write/replace operations with different contexts; vega/run_index.py:42 has a derived-index replacement. Reuse the pattern, but do not merge authoritative job commits and derived index writes into an option-heavy generic persistence API. Move job publication policy to the coordinator, keep derived indexing separate. Estimated source churn: 20–50 repeated publication lines removed, 100–200 coordinator/protocol lines added, net growth 50–180 before tests; these are rough planning estimates, not measured savings. Reliability is the rationale. Keep CAD and chemistry process isolation; do not DRY incompatible native environments. Document state/DAG diagrams beside the owning implementation and update them with behavior changes.

**Test review (existing source read directly):** tests/test_design_search.py tests fixed requirements, parameter diversity and budget prefix; tests/test_progressive_search.py tests callback ordering, screening without CAD and sparse topology agreement. The callback test invokes a short publisher; it does not prove that server.run_job avoids blocking search. tests/test_run_index.py covers source-change indexing, not crash recovery. tests/test_mesh_validation.py covers content-audit reuse, not artifact publication. tests/test_runtime.py covers import failure/timeout, not mode-dependent capabilities. Twenty focused tests passed earlier in this audit; no new acceptance tests were written. Existing tests do not certify these proposed paths.

```text
Code / observable user flow                         Existing / proposed proof
requirements -> proposals, fixed fields             TESTED unit; extend new/replay/continue
first callback -> short publication                  TESTED unit; real orchestration GAP
submit twice / lost response / conflicting digest   GAP -> HTTP + coordinator integration
validate origin/IDs/size/path -> reject              GAP -> negative HTTP/filesystem cases
mode -> required DAG -> complete/partial/failed      GAP -> table-driven lifecycle integration
proposal -> fail/reject/duplicate/empty frontier     PARTIAL unit -> ledger + selection tests
stage publish -> crash before/after manifest        GAP -> fault-injected storage integration
restart -> verify -> resume -> invalidate children  GAP -> dependency/recovery integration
cancel queued/running -> reject late results        GAP -> race integration + real process tree
adaptive feedback -> next proposal -> continuation  GAP -> opposing completion orders/restart
finite objectives -> feasible/Pareto -> ties         GAP -> admissible/nonfinite/boundary tests
cache changed key/corruption -> rebuild/reuse        PARTIAL unit -> real publication integration
native CAD -> audited solid -> analysis optional    GAP -> bounded rectangular/elliptical cases
reload/connection loss/partial/zero -> inspect       GAP -> browser integration + manual checks
compare/download/keyboard/focus/narrow layout        GAP -> browser/manual; live UI not inspected
provisioned setup -> cheap preview                  GAP -> documented quickstart execution
```

Coverage is qualitative, not an invented branch-coverage percentage. The sixteen behavior groups above require new or extended coverage for their proposed changes; the existing callback/screening/topology tests are not counted as those acceptance tests. No LLM model/prompt behavior changes are in this repair, so LLM evals are N/A. No existing tests are proposed for retirement; replace an assertion only when its formerly intended behavior is deliberately superseded and the replacement contract is independently covered. Full QA requirements are saved separately for implementation.

Parent performance review: E2 plus repeated validation work accepted. server.py:29–45 repeatedly reconstructs identity and reads artifact bytes; server.py:188 blocks screening on run_job. Scale: the inspected study has twelve selected rows, but stage CPU/RAM/I/O breakdown remains unknown. Benchmark one worker first, then bounded parallel workers only if memory and dependency isolation permit. Preserve existing CAD/audit caches. Status polling must read small manifests, not rehash entire STL files; audit at publication and validate on recovery/download with bounded cached verification that cannot conceal changed bytes. Stream large downloads and cap response/log sizes. Do not weaken integrity or classify preview completion as a solid speedup.

Failure registry: duplicate admission -> request digest/HTTP conflict test; disk-full or interrupted replacement -> retained previous manifest + recovery test; corrupt parent -> invalidate descendants test; numerical failure -> diagnostic rejection test; hung child -> deadline/tree cleanup test; unknown submission -> reconcile request test; unsupported analysis -> explicit capability failure test; cancellation race -> token test; network loss -> UI disconnected/retry test; missing legacy runtime -> recorded replay/new-lineage test. Each has planned visible handling and proof; zero unassigned silent failure paths in this proposal. This is not a claim all runtime failures were exercised.

<!-- autoplan-accepted:eng -->
- Make the coordinator the sole writer of authoritative versioned study manifests. Acquire an exclusive operating-system lock for the data root and use per-study mutation locks plus monotonically increasing revisions and execution tokens. Initial accepted manifest includes canonical request digest, idempotency key and execution identity in one publication; rebuild request/history indexes from manifests on startup. Under a global admission lock, an identical committed request returns its study, a conflicting payload is rejected, and an uncommitted request may be retried without a second accepted study. Flush and verify immutable artifact bytes before atomically publishing their references; indexes are derived, never authorities. Record and test crashes before/after initial manifest and artifact/reference writes, stale revisions and both cancel/commit orders. Power-loss durability is not claimed from atomic rename alone; validate flush/recovery behavior on the target filesystem. Never acknowledge acceptance before its authoritative commit succeeds.
- Preserve the existing one-active-generation admission limit initially; reject additional studies before work instead of introducing an unbounded queue. Bound submitted stages to the remaining accepted attempt/export budgets; schedule incrementally and prioritize ready preview/solid work ahead of optional analysis between non-preemptible stages. Keep numeric payload/budget limits, and declare configurable finite per-study disk/log and process-tree memory limits from the one-worker baseline before enabling parallelism. Reject or truthfully stop new work when reserves are insufficient, retaining existing outputs; never silently delete user artifacts. Bound log buffers, status payloads and streaming downloads. Multi-study saturation tests must verify admission rejection, responsive status/cancel and retained outputs; no fairness guarantee for an already running non-preemptible native call beyond its deadline.
- Resolve server-owned artifact IDs only within validated artifact/work roots. Reject traversal and symlink/reparse-point escapes in input and recovered manifests; do not trust stored absolute paths. Continue argument-array subprocess launches without shell interpolation. Preserve existing host/origin, identifier, JSON type, finite-number and body-size checks across new actions/downloads. Add negative tests for encoded traversal, invalid IDs, reparse escapes, oversized bodies, numeric overflow and wrong origins. A successful status lookup may expose a failed job; rejected mutations must return an error without side effects.
- For adaptive search, consume feedback in deterministic attempt-ordered batches with a versioned fixed batch size. Persist each batch's proposals before dispatch and atomically commit its ordered feedback frontier, next cursor and generator state; terminal failures are explicit feedback entries and cannot block the frontier forever. New exploration under identical seed/versions/recorded feedback is schedule-independent; historical replay consumes recorded feedback, not new solver results. Test reversed completion order, early-attempt failure and crashes at both frontier/proposal boundaries. Scope fixed-seed guarantees to proposal logic and recorded inputs, not bit-identical floating-point/native geometry on other runtimes.
- Define each stage's dependencies and immutable input/output fingerprints. Resume may reuse a succeeded stage only if artifacts verify and all dependency/runtime fingerprints match. A rebuilt parent invalidates affected audits, meshes and solver results in the new execution; preserve obsolete outputs as labelled history. A changed model/runtime requires explicit new-version lineage rather than silently resuming incompatible work. Test missing/corrupt parents, changed rebuild hashes and changed runtime. Operator resume/rebuild is explicit; within an already active stage, at most one automatic retry is permitted only for a classified transient failure after proving the old process is stopped and reconciling side effects. No automatic expensive restart after server restart.
- Validate finite, unit-normalized objective/check values before selection. Feasible means every applicable required check passes; missing or contradictory required evidence is unresolved, explicit violation is failed. Do not place unresolved/nonfinite/incomplete-objective candidates on the feasible Pareto frontier. Define check-specific numerical tolerances from model precision, not an arbitrary global epsilon; record these with provenance, use stable attempt IDs for objective ties, and keep dimensional/shape/connectivity diversity separate. Test admissible, violation, exact-boundary, missing, NaN/infinite, tied and empty-frontier cases through the real selection path.
- Supervise workers as owned process trees with stage deadlines independent of heartbeat. On Windows use a tested Job Object or equivalent containment with kill-on-close and resource limits; refuse to launch uncontained heavy workers if required containment fails. Record process identity with creation time to avoid killing a reused PID. On cancel/deadline, request graceful shutdown, then terminate the owned tree within a documented short grace period; startup reconciles any owned orphan before resuming. Add a real bounded helper-process test that spawns a child, holds an output file and ignores graceful shutdown; assert descendant exit, lock/file release and rejection of late publication. Preserve native-library serialization until isolated concurrency is demonstrated.
- Benchmark in seconds and bytes with declared hardware, runtime, immutable input/version snapshot, tolerances and cache condition. Start with bounded single-candidate rectangular/elliptical and historical-failure cases; compare interleaved baseline/new runs, reporting sample count, individual values and only statistically supportable summaries. With few expensive full-study repetitions, mark p95 unavailable rather than infer it. Run the unchanged 64-attempt fixture after bounded cases pass. Compare feasible-set retention and deduplication against a small exhaustive reference set grouped by supported family, and carry the same physical/mesh-quality acceptance throughout. Treat repeated status/hash/encoding work as a profiling target, not a proven dominant cost.
<!-- /autoplan-accepted:eng -->

Engineering decision trail: E1 manifest authority [P5 simpler local ownership; rejected new database initially]; E2 preserve bounded admission [P1 complete reliability]; E3 extend security boundaries [P1]; E4 deterministic feedback [P5 explicit reproducibility]; E5 dependency invalidation [P1]; E6 finite-value ranking [P1]; E7 real cleanup proof [P1]; repeated validation profiling [P5 measure first]. These are autonomous plan refinements under /autoplan, subject to final plan approval. No destructive action, data deletion or remote transfer approved. Architecture storage choice is provisional taste; the alternatives preserve feature scope. P3 domain/connectivity selection remains a later explicit design gate.

NOT in scope: hosted orchestration, public SDKs/community infrastructure, changes to vendor kernels, flight certification, complete spacecraft/launch design, speculative new solver physics and guaranteed runtime speedups. What already exists: deterministic search, basic screens, native solid builder, CAD/audit caches, atomic file pattern, indexed history, host/origin/body protections and isolated native environments; preserve and build on them. Public implementation references: [Python subprocess](https://docs.python.org/3/library/subprocess.html), [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects). These support bounded process handling; the proposed Vega ownership protocol remains a local design inference.

Implementation sequencing: first preserve a source/data baseline, then P0 coordinator/contracts/UI states, P1 measured staged pipeline, P2 search/ranking and P3 gated grammar expansion. Shared server/search/model modules make the core work sequential. After response/schema contracts stabilize, documentation and browser acceptance work can proceed in a disjoint web/docs lane, coordinated before integration. No worktrees are created during this review; the unborn repository needs a baseline strategy before branch-based work. Estimated effort is provisional: P0 3–6 engineer-days / 1–3 assisted days; P1 3–7 / 1–4 plus native runtime; P2 4–8 / 2–5; P3 domain research and experimental validation cannot be estimated responsibly yet. These are planning estimates, not delivery promises or automatic AI compression ratios.

REALITY: premise-table pass Saved failure evidence verified; dominant kernel operation remains unverified=1 server.py:112
REALITY: already-done pass No usable commit/remote baseline; existing implementations inspected rather than claiming upstream absence server.py:119
REALITY: surface-check pass Existing routes and payload limit inspected; new action routes remain proposals server.py:323
REALITY: binding-decisions pass Local-only review preserves user direction and pending plan approval docs/VEGA_SYSTEM_REPAIR_PLAN.md:1
REALITY: numbers pass Timeout derives from source; benchmark durations remain targets, not measurements server.py:113
REALITY: deferred-asks pass Full design freedom and materials retained in staged scope; no linked issue omitted docs/VEGA_SYSTEM_REPAIR_PLAN.md:1
REALITY: pr-count pass No PR exists or can be based on current unborn branch; default one reviewable change per delivery phase, no additional split proposed docs/VEGA_SYSTEM_REPAIR_PLAN.md:1
REALITY: prior-art pass No vendor change proposed; reuse native boundaries and official process containment interfaces server.py:112
REALITY: contract-assumptions pass Existing solver-default request field verified, compatibility adapter required vega/rocket.py:125
REALITY: falsification-box pass Profile bounded isolated cases first; if CAD is not dominant prioritize measured stage instead server.py:112
REALITY: stop-reasons pass Every proposed stop reason maps to lifecycle, recovery or process-tree proof in review registry docs/VEGA_SYSTEM_REPAIR_PLAN.md:1
REALITY: reporter-environment pass Target Windows local workflow identified; native timing reproduction still required start.ps1:1
REALITY: units pass Runtime limits use seconds; geometric dimensions retain explicit units and unchanged tolerances server.py:113
REALITY: perf-table pass Interleaved baseline/new instrumented fixture protocol specified; no fabricated percentile data docs/VEGA_SYSTEM_REPAIR_PLAN.md:1
REALITY: recall pass Small exhaustive supported-family fixture planned to detect feasible-set loss and false deduplication vega/design_search.py:59
REALITY: dependency-fallback pass P0 truthfulness ships before P1 speed; P2 remains fixed grammar until P3 gate docs/VEGA_SYSTEM_REPAIR_PLAN.md:1
REALITY: obligation-tiers pass Lifecycle proof must ship with P0; timing proof with P1; topology expansion requires P3 gate docs/VEGA_SYSTEM_REPAIR_PLAN.md:1

Completion summary: full scope retained; architecture 4 findings, code quality 2, test groups needing coverage 16, performance 2 (24 four-section findings/coverage groups; overlapping native findings are not extra defects). Native reviewer 7 findings. Critical missing-handling/test assignments after amendment: zero; implementation and verification still outstanding. One final implementation-approval decision plus the carried P3 domain gate remain open. Lake Score N/A: no scored human choices. Autoplan completion review logs are deferred until final approval as the driver requires; no shipping-clearance claim.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|---|---|---|---|---|---|
| Specification | CEO workflow | Plan clarity | 2 | PASS for staged proposal | 3 gaps fixed and rechecked; latest score 9/10 |
| CEO | /autoplan + /plan-ceo-review | Scope and strategy | 1 | Findings incorporated | 4 native findings |
| Outside | User decision | Additional opinion | 0 completed | Skipped by user | Private-plan transfer rejected; local-only review retained |
| Design | /autoplan | UI and artifacts | 1 | Findings incorporated | 7 native findings; rendered checks remain |
| DX | /autoplan | Developer workflow | 1 | Findings incorporated | 10 native findings; eight parent passes; setup timing unmeasured |
| Engineering | /autoplan | Final architecture/tests/performance | 1 | Findings incorporated; implementation work open | 7 native findings; 24 parent findings/coverage groups mapped to tasks |

OUTSIDE COVERAGE: none; local-only instruction applies to every remaining phase.
VERDICT: Local plan review complete; proposed repairs are ready for owner review. This is not implementation, full-system bug-free assurance, performance validation or shipping clearance.
**UNRESOLVED DECISIONS:**
- Final approval of delivery sequencing and implementation scope is pending.
- P3 topology pair and validation domain remain an explicit engineering design gate.

## Implementation progress � 2026-11-05

Implementation is in progress; the full plan is not complete. Search proposals now persist before evaluation, terminal attempt records retain their proposal inputs, unexpected evaluator exceptions are isolated, and progress updates preserve the ledger. Job writes flush before atomic replacement. Accepted jobs retain their requirements and kind. Studies with no exported solids retain their study report and terminate without indexing a missing result; the UI handles that outcome. Validation: 14 search tests and 3 job recovery tests passed; Python compilation passed. Resume, cancellation/process containment, authoritative stage manifests, benchmark evidence, and P3 validation remain outstanding.
