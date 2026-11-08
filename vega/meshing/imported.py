"""Explicit CAD/STL-to-tetrahedron entry point for external and PicoGK solids.

STEP/BREP retain CAD curvature. STL can only retain its supplied faceted boundary.
Intersecting multi-body assembly STL is not automatically repaired into a solid.
Callers supply millimetres and must select boundary conditions independently.
"""
from pathlib import Path
import math
import numpy as np
from .kernel import model


def mesh_solid(source,output,edge_mm,minimum_quality=.05,max_cells=500000):
    source,output=Path(source).resolve(),Path(output).resolve()
    if source==output:raise ValueError('Output must not overwrite source geometry')
    if not source.is_file() or not math.isfinite(edge_mm) or edge_mm<=0:raise ValueError('Existing geometry and positive edge size required')
    if not 0<minimum_quality<1 or type(max_cells) is not int or max_cells<1:raise ValueError('Invalid quality/budget controls')
    with model('imported-solid') as g:
        if source.suffix.lower() in ('.step','.stp','.brep','.iges','.igs'):
            volumes=g.model.occ.importShapes(str(source));g.model.occ.synchronize()
            volumes=[v for v in volumes if v[0]==3]
            if not volumes:raise ValueError('CAD import contains no closed solid')
        elif source.suffix.lower()=='.stl':
            import trimesh
            solid=trimesh.load_mesh(source,process=True)
            if not solid.is_watertight or not solid.is_winding_consistent or len(solid.split())!=1 or solid.volume<=0:
                raise ValueError('STL must be one closed, outward-oriented solid; export the PicoGK union rather than the overlapping assembly')
            g.merge(str(source))
            g.model.mesh.classifySurfaces(math.radians(40),True,True,math.pi)
            g.model.mesh.createGeometry()
            surfaces=[tag for _,tag in g.model.getEntities(2)]
            loop=g.model.geo.addSurfaceLoop(surfaces)
            volumes=[(3,g.model.geo.addVolume([loop]))];g.model.geo.synchronize()
        else:raise ValueError('Supported solid inputs: STEP, BREP, IGES, STL')
        for i,(_,tag) in enumerate(volumes,1):
            g.model.addPhysicalGroup(3,[tag],i);g.model.setPhysicalName(3,i,f'solid_{i}')
        g.option.setNumber('Mesh.MeshSizeMin',edge_mm/4)
        g.option.setNumber('Mesh.MeshSizeMax',edge_mm)
        g.option.setNumber('Mesh.MeshSizeFromCurvature',24)
        g.option.setNumber('Mesh.Algorithm3D',1)
        g.model.mesh.generate(3);g.model.mesh.optimize('')
        tags,xyz,_=g.model.mesh.getNodes();order=np.argsort(tags);tags=tags[order];xyz=xyz.reshape(-1,3)[order]
        element_tags,con=g.model.mesh.getElementsByType(4)
        if not len(element_tags) or len(element_tags)>max_cells:raise ValueError('Solid mesh is empty or exceeds cell budget')
        q=np.asarray(g.model.mesh.getElementQualities(element_tags,'minSICN'))
        jac=np.asarray(g.model.mesh.getElementQualities(element_tags,'minDetJac'))
        if not np.isfinite(q).all() or np.any(jac<=0) or q.min()<minimum_quality:
            raise ValueError(f'Solid quality gate failed: min SICN {q.min():.5g}')
        con=np.searchsorted(tags,con).reshape(-1,4)
        used,inverse=np.unique(con,return_inverse=True)
        output.parent.mkdir(parents=True,exist_ok=True);g.write(str(output))
        return {'nodes_mm':xyz[used],'tetrahedra':inverse.reshape(-1,4),
            'summary':{'source':str(source),'cells':len(con),'nodes':len(used),
                'minimum_sicn':float(q.min()),'mean_sicn':float(q.mean()),'minimum_jacobian_mm3':float(jac.min()),
                'solid_count':len(volumes),'geometry_units':'mm','output':str(output),
                'scope':'Tetrahedral geometry mesh. Boundary conditions, material models and convergence require a separate analysis.'}}
