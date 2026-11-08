"""Bounded content-addressed cache for expensive deterministic surface audits."""
from collections import OrderedDict
from copy import deepcopy
import hashlib
import struct
import threading
import numpy as np
from vega_geometry.topology import mesh_topology
from .meshing.quality import audit_triangle_quality

_CACHE=OrderedDict()
_LOCK=threading.Lock()
_LIMIT=64


def inspect_surface(shape):
    digest=hashlib.sha256()
    digest.update(struct.pack('<QQ',len(shape['vertices']),len(shape['triangles'])))
    for key,dtype in (('vertices','<f8'),('triangles','<i8')):
        data=np.ascontiguousarray(shape[key],dtype=dtype)
        digest.update(memoryview(data).cast('B'))
    identity=digest.digest()
    with _LOCK:
        if identity in _CACHE:
            _CACHE.move_to_end(identity)
            return deepcopy(_CACHE[identity])
    result=(mesh_topology(shape),audit_triangle_quality(shape['vertices'],shape['triangles']))
    with _LOCK:
        _CACHE[identity]=deepcopy(result)
        _CACHE.move_to_end(identity)
        while len(_CACHE)>_LIMIT:_CACHE.popitem(last=False)
    return result
