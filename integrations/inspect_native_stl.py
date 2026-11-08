"""Mesh-only diagnostics. Never treat edge incidence as engine validation."""
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.tools'/'python'))
import numpy as np

def inspect(path):
    with open(path,'rb') as f:
        f.seek(80);count=struct.unpack('<I',f.read(4))[0]
    dtype=np.dtype([('normal','<f4',(3,)),('vertex','<f4',(3,3)),('attr','<u2')])
    data=np.fromfile(path,dtype=dtype,count=count,offset=84)
    points=data['vertex'].reshape(-1,3)
    _,inverse=np.unique(points,axis=0,return_inverse=True)
    triangles=inverse.reshape(-1,3).astype(np.int32)
    edges=np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]);edges.sort(axis=1)
    edge_keys=np.ascontiguousarray(edges).view(np.dtype((np.void,8))).reshape(-1)
    _,counts=np.unique(edge_keys,return_counts=True)
    v=data['vertex'].astype(np.float64)
    volume=float(np.einsum('ij,ij->i',v[:,0],np.cross(v[:,1],v[:,2])).sum()/6)
    return {'triangles':count,'vertices_exact_float32':int(inverse.max()+1),
       'boundary_or_nonmanifold_edges':int(np.count_nonzero(counts!=2)),
       'signed_volume_mm3':volume,'finite_vertices':bool(np.isfinite(v).all()),
       'scope':'Mesh edge incidence and oriented volume only; not passage connectivity, vertex manifoldness, one-solid certification, or engineering validation.'}

if __name__=='__main__':
    result=inspect(sys.argv[1]);print(json.dumps(result,indent=2))
    if len(sys.argv)>2:Path(sys.argv[2]).write_text(json.dumps(result,indent=2))
