# Publication and provenance

This directory contains newly written Vega component-graph and station-loft code.
Its public description should identify it as an early geometry library, not a
complete PicoGK-equivalent solid kernel or validated spaceplane design system.

No license for Vega's original code has been selected by the project owner yet.
Choose and add that license before presenting a public release as open source.
No repository has been created or uploaded by this task.

PicoGK remains a separately attributed third-party backend in the parent
application. Its upstream [Apache-2.0 license](https://github.com/leap71/PicoGK/blob/main/LICENSE)
and notices remain with its source. This package does not contain or relabel it.
If future work copies or modifies upstream code, record the precise revision,
retain its notices, and identify modifications in the affected files.

The cold-flow equations and their sources live in the app's `vega/inlet.py` and
`docs/GEOMETRY_SOURCES.md`, outside this domain-independent package. NASA
equations are independently implemented and tested; no NASA geometry or
validated vehicle is claimed. LEAP 71's proprietary Noyron is not included.

Before an eventual backend replacement, compare the same recipes for topology,
dimensions, bore continuity, isolation, wall thickness, mesh validity, repeatable
exports and performance. The present loft tests cover a much narrower problem.
