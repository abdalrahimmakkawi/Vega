"""Conforming swept hybrid CFD volumes from Vega's analytic cross-sections.

Gmsh produces an unstructured triangular core. Shared polygon boundary nodes
connect it to graded quadrilateral wall layers. Sweeping creates prisms in the
core and hexahedra at the wall, with matching complete faces at the interface.
This supports star-shaped, single-passage elliptic/lobed ducts, not arbitrary
branched CAD or a domain with an embedded rocket. All supplied stations survive.
"""
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
from vega_geometry.sections import validate_stations, interpolate, contour
from .kernel import model

FACE_MAP = {
    6: ((0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)),
    5: ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)),
}


@dataclass
class VolumeMesh:
    nodes: np.ndarray  # mm
    cells: dict       # Gmsh type -> zero-based connectivity
    faces: dict       # patch -> {3: triangle, 4: quadrangle}
    summary: dict
    axial_levels: np.ndarray


def _cross_section(sectors, layers, growth, core_size):
    if sectors < 24 or sectors % 4 or layers < 2 or not 1 < growth <= 1.5:
        raise ValueError('Invalid hybrid layer controls')
    angle = 2*math.pi*np.arange(sectors)/sectors
    core_radius = .75
    ring = core_radius*np.column_stack((np.cos(angle), np.sin(angle)))
    with model('hybrid-reference-section') as g:
        o = g.model.geo
        pts = [o.addPoint(x,y,0,core_size) for x,y in ring]
        edges = [o.addLine(pts[i],pts[(i+1)%sectors]) for i in range(sectors)]
        o.addPlaneSurface([o.addCurveLoop(edges)]); o.synchronize()
        for edge in edges: g.model.mesh.setTransfiniteCurve(edge,2)
        g.option.setNumber('Mesh.Algorithm',6)
        g.option.setNumber('Mesh.MeshSizeMin',core_size)
        g.option.setNumber('Mesh.MeshSizeMax',core_size)
        g.model.mesh.generate(2)
        tags, xyz, _ = g.model.mesh.getNodes()
        order = np.argsort(tags); tags = tags[order]; xy = xyz.reshape(-1,3)[order,:2]
        triangles = np.searchsorted(tags, g.model.mesh.getElementsByType(2)[1]).reshape(-1,3)
        boundary = np.array([np.searchsorted(tags,g.model.mesh.getNodes(0,p)[0][0]) for p in pts])
    # Correct winding independent of mesher conventions.
    p=xy[triangles]; signed=np.cross(np.c_[p[:,1]-p[:,0],np.zeros(len(p))],np.c_[p[:,2]-p[:,0],np.zeros(len(p))])[:,2]
    triangles[signed<0]=triangles[signed<0][:,[0,2,1]]
    # Wall-outward spacing is reversed: smallest cell sits next to the wall.
    widths=growth**np.arange(layers-1,-1,-1,dtype=float)
    widths*= (1-core_radius)/widths.sum()
    radii=core_radius+np.cumsum(widths)
    quads=[]; all_xy=[xy]; previous=boundary; base=len(xy)
    for radius in radii:
        current=base+np.arange(sectors)
        for i in range(sectors):
            j=(i+1)%sectors
            quads.append([previous[i],current[i],current[j],previous[j]])
        all_xy.append(radius*np.column_stack((np.cos(angle),np.sin(angle))))
        previous=current; base+=sectors
    return np.concatenate(all_xy), triangles, np.asarray(quads), float(widths[-1])


def axial_grid(stations, edge_mm, growth=1.3, indicators=None):
    """Refine area changes and supplied solver-error intervals; enforce dz ratios.

    This guarantees axial spacing growth only. Cross-stream anisotropy is
    intentional in wall layers and is reported separately by the volume audit.
    """
    levels=np.array([s['z_mm'] for s in stations],float)
    area=np.array([s['width_mm']*s['height_mm'] for s in stations],float)
    sizes=edge_mm/np.sqrt(1+4*abs(np.diff(np.log(area))))
    if indicators is not None:
        indicators=np.asarray(indicators,float)
        if indicators.shape != sizes.shape or not np.isfinite(indicators).all() or np.any(indicators<0):
            raise ValueError('One nonnegative error indicator is required per geometry interval')
        sizes/=np.sqrt(1+3*indicators)
    divisions=np.maximum(1,np.ceil(np.diff(levels)/sizes).astype(int))
    for _ in range(10000):
        spacing=np.diff(levels)/divisions
        ratios=np.maximum(spacing[1:]/spacing[:-1],spacing[:-1]/spacing[1:])
        bad=np.flatnonzero(ratios>growth*(1+1e-12))
        if not len(bad): break
        for i in bad:
            coarse=i if spacing[i]>spacing[i+1] else i+1
            fine=i+1 if coarse==i else i
            divisions[coarse]=max(divisions[coarse]+1,math.ceil((levels[coarse+1]-levels[coarse])/(growth*spacing[fine])))
        if divisions.sum()>3000: raise ValueError('Axial refinement budget exceeded')
    else: raise ValueError('Axial grading failed')
    return np.concatenate([np.linspace(a,b,n+1)[:-1] for a,b,n in zip(levels[:-1],levels[1:],divisions)]+[levels[-1:]])


def _all_faces(cells):
    blocks=[]
    for typ, connectivity in cells.items():
        for face in FACE_MAP[typ]:
            f=np.full((len(connectivity),4),-1,dtype=np.int64)
            f[:,:len(face)]=connectivity[:,face]
            blocks.append(f)
    return np.concatenate(blocks)


def boundary_faces(nodes,cells):
    faces=_all_faces(cells)
    _, indices, counts=np.unique(np.sort(faces,axis=1),axis=0,return_index=True,return_counts=True)
    if np.any(counts>2): raise ValueError('Nonmanifold volume face')
    boundary=faces[indices[counts==1]]
    z=nodes[:,2]; low,high=z.min(),z.max()
    patches={name:{3:[],4:[]} for name in ('inlet','outlet','wall')}
    for f in boundary:
        f=f[f>=0]
        name='inlet' if np.all(abs(z[f]-low)<1e-8) else 'outlet' if np.all(abs(z[f]-high)<1e-8) else 'wall'
        patches[name][len(f)].append(f)
    return {name:{n:np.asarray(f,dtype=np.int64).reshape(-1,n) for n,f in block.items()} for name,block in patches.items()},int(np.sum(counts==2))


def audit_volume(nodes,cells):
    with model('volume-audit') as g:
        g.model.addDiscreteEntity(3,1)
        g.model.mesh.addNodes(3,1,np.arange(1,len(nodes)+1),nodes.ravel())
        start=1; all_tags=[]
        for typ, con in cells.items():
            tags=np.arange(start,start+len(con));start+=len(con);all_tags.extend(tags)
            g.model.mesh.addElementsByType(1,typ,tags,(con+1).ravel())
        q=np.asarray(g.model.mesh.getElementQualities(all_tags,'minSJ'))
        jac=np.asarray(g.model.mesh.getElementQualities(all_tags,'minDetJac'))
        volume=np.asarray(g.model.mesh.getElementQualities(all_tags,'volume'))
    if not np.isfinite(q).all() or np.any(jac<=0) or np.any(volume<=0):
        raise ValueError('Hybrid mesh contains inverted or degenerate cells')
    return {'nodes':len(nodes),'cells':sum(len(v) for v in cells.values()),
            'cell_types':{str(k):len(v) for k,v in cells.items()},
            'scaled_jacobian':{'minimum':float(q.min()),'mean':float(q.mean()),'p05':float(np.quantile(q,.05))},
            'minimum_jacobian_mm3':float(jac.min()),'volume_mm3':float(volume.sum()),
            'inverted_cells':int(np.sum(jac<=0)),
            'quality_scope':'Gmsh minSJ/minDetJac samples; OpenFOAM checkMesh additionally checks solver-cell geometry.'}


def build_hybrid(stations,edge_mm=30.,sectors=48,layers=6,growth=1.3,indicators=None,max_cells=300000):
    stations=validate_stations(stations)
    if not math.isfinite(edge_mm) or edge_mm<=0: raise ValueError('Positive edge target required')
    xy,tri,quad,first_fraction=_cross_section(sectors,layers,min(growth,1.25),.15)
    z=axial_grid(stations,edge_mm,growth,indicators)
    if (len(z)-1)*(len(tri)+len(quad))>max_cells: raise ValueError('Hybrid volume cell budget exceeded')
    radius=np.linalg.norm(xy,axis=1); angle=np.arctan2(xy[:,1],xy[:,0])
    nodes=[]
    for level in z:
        s=interpolate(stations,float(level)); xyz=contour(s,angle)
        xyz[:,:2]*=radius[:,None];nodes.append(xyz)
    nodes=np.concatenate(nodes);n=len(xy)
    cells={6:np.concatenate([np.c_[tri+k*n,tri+(k+1)*n] for k in range(len(z)-1)]),
           5:np.concatenate([np.c_[quad+k*n,quad+(k+1)*n] for k in range(len(z)-1)])}
    summary=audit_volume(nodes,cells)
    faces,internal=boundary_faces(nodes,cells)
    # A simply connected swept disk has only two end sections and one outer wall.
    expected_wall=sectors*(len(z)-1)
    if len(faces['wall'][4])!=expected_wall or len(faces['wall'][3]):
        raise ValueError('Unexpected exposed internal faces: nonconforming hybrid interface')
    dz=np.diff(z)
    summary.update({'backend':'Gmsh triangular core + conforming graded quad sweep',
        'internal_faces':internal,'boundary_faces':{k:sum(len(v) for v in b.values()) for k,b in faces.items()},
        'conforming_interface':True,'axial_layers':len(z)-1,'wall_layers':layers,
        'wall_layer_growth':min(growth,1.25),'max_axial_growth':float(max(np.max(dz[1:]/dz[:-1]),np.max(dz[:-1]/dz[1:]))) if len(dz)>1 else 1.,
        'first_layer_fraction_of_radius':first_fraction,
        'minimum_first_layer_mm':first_fraction*min(min(s['width_mm'],s['height_mm'])/2 for s in stations),
        'y_plus_status':'Not prescribed; a solved wall shear and selected turbulence model are required.',
        'adaptation':'solver_indicator' if indicators is not None else 'geometry_area_gradient',
        'scope':'Single unobstructed duct passage. No rocket blockage, combustion, cooling manifolds or full-vehicle CFD.'})
    return VolumeMesh(nodes,cells,faces,summary,z)


def write_msh(mesh,path):
    """ASCII Gmsh 2.2 with SI nodes and stable physical patch names."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='ascii',newline='\n') as f:
        f.write('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n4\n2 1 "inlet"\n2 2 "outlet"\n2 3 "wall"\n3 4 "fluid"\n$EndPhysicalNames\n')
        f.write(f'$Nodes\n{len(mesh.nodes)}\n')
        for i,p in enumerate(mesh.nodes/1000,1):f.write(f'{i} {p[0]:.16g} {p[1]:.16g} {p[2]:.16g}\n')
        count=sum(len(c) for c in mesh.cells.values())+sum(len(c) for b in mesh.faces.values() for c in b.values())
        f.write(f'$EndNodes\n$Elements\n{count}\n');i=1
        for patch,name in enumerate(('inlet','outlet','wall'),1):
            for size,faces in mesh.faces[name].items():
                typ=2 if size==3 else 3
                for face in faces:
                    f.write(f'{i} {typ} 2 {patch} {patch} '+' '.join(map(str,face+1))+'\n');i+=1
        for typ,con in mesh.cells.items():
            for cell in con:
                f.write(f'{i} {typ} 2 4 4 '+' '.join(map(str,cell+1))+'\n');i+=1
        f.write('$EndElements\n')


def inspection_scene(mesh):
    """Expose actual cell faces at a half-domain cut; never invent a display grid."""
    vertices=mesh.nodes.tolist();triangles=[];bodies=[]
    for typ,con in mesh.cells.items():
        selected=con[mesh.nodes[con,0].mean(axis=1)>=-1e-10]
        faces=_all_faces({typ:selected})
        _,idx,count=np.unique(np.sort(faces,axis=1),axis=0,return_index=True,return_counts=True)
        start=len(triangles)
        for face in faces[idx[count==1]]:
            f=face[face>=0].tolist();triangles.append(f[:3])
            if len(f)==4:triangles.append([f[0],f[2],f[3]])
        bodies.append({'component_id':'fluid_core' if typ==6 else 'wall_layers',
            'name':'Unstructured prism core' if typ==6 else 'Structured hex wall layers',
            'first_triangle':start,'triangle_count':len(triangles)-start,
            'color':[.25,.62,.8] if typ==6 else [.85,.55,.18],
            'group':'fluid_core' if typ==6 else 'wall_layers'})
    return {'vertices':vertices,'triangles':triangles,'bodies':bodies,'units':'mm',
            'scope':'Half-domain faces extracted from the actual solver volume mesh.'}
