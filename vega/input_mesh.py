"""Closed triangular shells consumed by PicoGK before voxel operations."""
import numpy as np
import trimesh


def shell_mesh(rows,wall):
    radii=np.asarray([r['radii_mm'] for r in rows],float)
    z=np.asarray([r['z_mm'] for r in rows],float)
    if radii.ndim!=2 or min(radii.shape)<3 or not np.isfinite(radii).all() or not np.isfinite(z).all() or np.any(radii<=0) or not np.all(np.diff(z)>0) or not np.isfinite(wall) or wall<=0:
        raise ValueError('Invalid mesh sections')
    m,n=radii.shape; angles=np.arange(n)*2*np.pi/n
    vertices=[]
    for offset in (0,wall):
        r=radii+offset
        vertices.extend(np.stack((r*np.cos(angles),r*np.sin(angles),np.broadcast_to(z[:,None],r.shape)),axis=-1).reshape(-1,3))
    faces=[]; size=m*n
    def quad(a,b,c,d):faces.extend(((a,b,c),(a,c,d)))
    for i in range(m-1):
        for j in range(n):
            k=(j+1)%n;a=i*n+j;b=i*n+k;c=(i+1)*n+k;d=(i+1)*n+j
            quad(a,d,c,b) # inner surface faces the passage
            quad(a+size,b+size,c+size,d+size)
    for j in range(n):
        k=(j+1)%n
        quad(j,k,k+size,j+size)
        a=(m-1)*n+j;b=(m-1)*n+k
        quad(a,a+size,b+size,b)
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    if not mesh.is_volume:raise ValueError('Input shell must be closed and outward wound')
    return mesh


def write_input_mesh(design,path):
    mesh=trimesh.util.concatenate([shell_mesh(design[key],design['wall_mm']) for key in ('outer','core')])
    mesh.export(path)
    # Verify the actual serialized triangles, not just the in-memory topology.
    saved=trimesh.load_mesh(path,process=True)
    shells=saved.split(only_watertight=False,repair=False)
    passed=len(shells)==2 and all(s.is_volume for s in shells)
    if not passed:raise ValueError('Serialized input meshes failed closed-solid validation')
    return dict(triangles=len(saved.faces),closed_shells=len(shells),passed=passed,
        units='mm',scope='Nacelle and core triangular shells; downstream features use implicit fields and lattices')
