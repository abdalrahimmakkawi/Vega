# Vega 0.29: connected airpath and support-frame surface mesh

The full airpath mesh joins the five analytic duct stages at four checked
interfaces. The saved demonstration run `0595368cf75a4269b73b1bdd06ede2c2`
has 148,400 conforming cells, 108,540 nodes, no inverted cells and a minimum
sampled scaled Jacobian of 0.9013. OpenFOAM `checkMesh -allTopology -allGeometry`
passed. A steady cold, incompressible laminar solve converged at 600 iterations;
the assumed case produced a 0.120318 Pa pressure drop and a 4.70e-10 relative
inlet/outlet mass imbalance. This is a single mesh with a geometry sizing field.
The separate common-nozzle study has a solution-driven axial refinement pass.

A fresh 0.29 run, `7d1015458c8043619feaa351f4784a6e`, independently
reproduced the 148,400-cell airpath result: minimum sampled scaled Jacobian
0.901288, zero inverted cells, OpenFOAM mesh checks passed, and the cold-flow
solve converged at 600 iterations with a 0.120318 Pa pressure drop. Its common
nozzle grew from 80,878 to 126,882 cells after the solution-driven axial pass;
the minimum sampled scaled Jacobian rose from 0.947668 to 0.951252. Both nozzle
solves converged, with a 2.2585% pressure-drop change, inside the configured
5% comparison tolerance. CalculiX crosschecked the selected 150-element frame
against the optimizer, with a 7.72e-8 relative compliance difference. The
bound engineering bundle passed a full ZIP CRC scan. Exact run hashes and
metrics are recorded in [MESH_029_VERIFICATION.json](MESH_029_VERIFICATION.json).

The analytic airpath volume excludes the embedded PicoGK rocket, mixer strakes,
heat transfer, reactions and mode transition. Its result cannot be used as an
installed propulsion prediction. Ansys solver execution still awaits the
user's license; the OpenFOAM and CalculiX adapters run locally.

Long assembly support bars now have axial subdivisions controlled by their
radius and angular chord. The same actual selected 150-member frame, sampled
with the updated surface mesher, has 685,488 triangles, mean triangle quality
2r/R of 0.611, minimum 0.210 and zero triangles below 0.2. The previous
display surface had 25,344 triangles, mean quality 0.179 and 12,672 below 0.2.
These are display/solid surface metrics. CalculiX uses the exact selected
axial-bar frame, so its truss discretization is a separate model.

The workbench's saved-run listing now indexes summaries by the source JSON's
modification time and size. An unchanged list of 95 runs was read in 0.038 s
locally after its initial index build, compared with 12.0 s for the first
build. The server API returned the indexed list in 1.24 s after restart.

The previous Gmsh, OpenFOAM, CalculiX and ANSYS client setup remains documented
in [MESH_BACKEND_028.md](MESH_BACKEND_028.md). New runs build both the nozzle
and five-stage volumes. Existing runs remain bound to their saved meshes and
reports.
