"""Combinatorial topology checks, independent of physics and mesh appearance."""
from collections import Counter, defaultdict
from math import isfinite


def graph_topology(nodes, edges):
    nodes=list(nodes)
    if len(set(nodes))!=len(nodes): raise ValueError('Duplicate topology node')
    adjacency={n:set() for n in nodes};seen=set()
    for a,b in edges:
        if a not in adjacency or b not in adjacency or a==b:
            raise ValueError('Invalid topology edge')
        key=frozenset((a,b))
        if key in seen: raise ValueError('Duplicate topology edge')
        seen.add(key);adjacency[a].add(b);adjacency[b].add(a)
    groups=[];remaining=set(nodes)
    while remaining:
        stack=[min(remaining)];group=set()
        while stack:
            n=stack.pop()
            if n in group: continue
            group.add(n);stack.extend(adjacency[n]-group)
        remaining-=group;groups.append(sorted(group))
    return {'vertices':len(nodes),'edges':len(seen),'connected_components':len(groups),
            'cycle_rank':len(seen)-len(nodes)+len(groups),'groups':groups,
            'isolated_nodes':sorted(n for n in nodes if not adjacency[n])}


def reachable(edges, source, target):
    graph=defaultdict(set)
    for a,b in edges: graph[a].add(b)
    todo=[source];seen=set()
    while todo:
        n=todo.pop()
        if n==target:return True
        if n not in seen: seen.add(n);todo.extend(graph[n]-seen)
    return False


def mesh_topology(mesh):
    """Indexed surface incidence, vertex links, Euler characteristic and genus.

    Does not detect geometric self-intersection, leaks under pressure or stress.
    No coordinate welding is performed: indices define this surface complex.
    """
    vertices=mesh['vertices'];faces=mesh['triangles'];edges=defaultdict(list)
    links=defaultdict(list);used=set();degenerate=0;volume=0.
    import numpy as np
    points=np.asarray(vertices, dtype=float).reshape((-1,3)) if not vertices else np.asarray(vertices, dtype=float)
    triangles=np.asarray(faces)
    if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all():
        raise ValueError('Invalid mesh point')
    if faces:
        if any(type(i)!=int for t in faces for i in t):raise ValueError('Invalid face')
        if triangles.ndim!=2 or triangles.shape[1]!=3 or triangles.dtype.kind not in 'iu' or np.any(triangles<0) or np.any(triangles>=len(vertices)):
            raise ValueError('Invalid face')
        # Array arithmetic avoids millions of Python coordinate operations while
        # retaining the same geometric degeneracy and signed-volume checks.
        a,b,c=(points[triangles[:,i]] for i in range(3))
        cross=np.cross(b-a,c-a)
        degenerate=int(np.count_nonzero((np.einsum('ij,ij->i',cross,cross)<1e-20) |
            (triangles[:,0]==triangles[:,1]) | (triangles[:,1]==triangles[:,2]) | (triangles[:,2]==triangles[:,0])))
        volume=float(np.einsum('ij,ij->',a,cross)/6)
        used=set(triangles.ravel().tolist())
    if faces and not degenerate:
        fast=_sparse_surface_topology(triangles,volume)
        if fast is not None:return fast
    for index,t in enumerate(faces):
        for i in range(3):
            x,y=t[i],t[(i+1)%3];edges[tuple(sorted((x,y)))].append((index,x,y))
            links[x].append((y,t[(i+2)%3]))
    adjacency=[set() for _ in faces]
    for items in edges.values():
        for f,_,_ in items[1:]:adjacency[items[0][0]].add(f);adjacency[f].add(items[0][0])
    remaining=set(range(len(faces)));shells=0
    while remaining:
        shells+=1;todo=[next(iter(remaining))];remaining.remove(todo[0])
        while todo:
            f=todo.pop();new=adjacency[f]&remaining;remaining-=new;todo.extend(new)
    bad_vertices=0
    for pairs in links.values():
        link=defaultdict(set);degree=Counter()
        for a,b in pairs:link[a].add(b);link[b].add(a);degree[a]+=1;degree[b]+=1
        pending=[next(iter(link))];seen=set()
        while pending:
            n=pending.pop()
            if n not in seen:seen.add(n);pending.extend(link[n]-seen)
        if len(seen)!=len(link) or any(d!=2 for d in degree.values()):bad_vertices+=1
    boundary=sum(len(x)==1 for x in edges.values());nonmanifold=sum(len(x)>2 for x in edges.values())
    winding=all(len(items)!=2 or items[0][1:] == items[1][1:][::-1] for items in edges.values())
    closed=bool(faces) and not (boundary or nonmanifold or degenerate or bad_vertices)
    chi=len(used)-len(edges)+len(faces)
    genus=(2*shells-chi)//2 if closed and winding and (2*shells-chi)%2==0 else None
    return {'vertices':len(used),'edges':len(edges),'faces':len(faces),'surface_components':shells,
            'boundary_edges':boundary,'nonmanifold_edges':nonmanifold,'nonmanifold_vertices':bad_vertices,
            'degenerate_faces':degenerate,'winding_consistent':winding,'closed_manifold':closed,
            'euler_characteristic':chi,'total_genus':genus,'signed_volume_mm3':volume,
            'scope':'Combinatorial surface topology; self-intersection and physical qualification are not assessed.'}


def _sparse_surface_topology(t, volume):
    """Exact incidence/fan checks using sparse graphs; no welding or sampling.

    The Python reference path handles degenerate/nonmanifold-edge cases and
    installations without SciPy. A corner graph detects disconnected vertex fans
    (bow-ties) which edge counts alone cannot detect.
    """
    try:
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
    except ImportError:return None
    import numpy as np
    n=len(t);flat=t.ravel();nxt=t[:,[1,2,0]].ravel()
    ends=np.stack((np.minimum(flat,nxt),np.maximum(flat,nxt)),axis=1)
    order=np.lexsort((ends[:,1],ends[:,0]));ordered=ends[order]
    starts=np.r_[0,1+np.flatnonzero(np.any(ordered[1:]!=ordered[:-1],axis=1))]
    counts=np.diff(np.r_[starts,len(order)])
    if np.any(counts>2):return None
    paired=starts[counts==2];a=order[paired];b=order[paired+1]
    boundary_edges=ends[order[starts[counts==1]]]
    def graph_labels(left,right,size):
        g=coo_matrix((np.ones(len(left),dtype=np.int8),(left,right)),shape=(size,size)).tocsr()
        return connected_components(g,directed=False)
    shells,_=graph_labels(a//3,b//3,n)
    corners=np.arange(3*n);next_corner=(corners//3)*3+(corners+1)%3
    low=np.where(flat<nxt,corners,next_corner);high=np.where(flat<nxt,next_corner,corners)
    _,fans=graph_labels(np.r_[low[a],high[a]],np.r_[low[b],high[b]],3*n)
    unique_fans=np.unique(np.stack((flat,fans),axis=1),axis=0)
    vertices,fan_counts=np.unique(unique_fans[:,0],return_counts=True)
    bad=np.union1d(vertices[fan_counts>1],np.unique(boundary_edges))
    winding=bool(np.all((flat[a]==nxt[b]) & (nxt[a]==flat[b])))
    boundary=int(np.count_nonzero(counts==1));closed=not (boundary or len(bad))
    chi=len(vertices)-len(starts)+n
    genus=(2*shells-chi)//2 if closed and winding and (2*shells-chi)%2==0 else None
    return {'vertices':len(vertices),'edges':len(starts),'faces':n,'surface_components':int(shells),
            'boundary_edges':boundary,'nonmanifold_edges':0,'nonmanifold_vertices':len(bad),
            'degenerate_faces':0,'winding_consistent':winding,'closed_manifold':closed,
            'euler_characteristic':chi,'total_genus':int(genus) if genus is not None else None,
            'signed_volume_mm3':volume,
            'scope':'Combinatorial surface topology; self-intersection and physical qualification are not assessed.'}
