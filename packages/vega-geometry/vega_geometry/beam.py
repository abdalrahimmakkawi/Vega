"""Closed, graded solid beam surface for explicit structural graphs."""
from math import sqrt, cos, sin, pi, isfinite, ceil
from . import point


def beam(start, end, radius_mm, segments=12, *, screening=False):
    a,b=point(start),point(end)
    if isinstance(radius_mm,bool) or not isfinite(radius_mm) or radius_mm<=0:raise ValueError('Invalid beam radius')
    if type(segments)!=int or not 6<=segments<=128:raise ValueError('Invalid beam resolution')
    def cross(u,v):return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    def norm(v):
        size=sqrt(sum(x*x for x in v))
        if size<1e-9:raise ValueError('Zero length beam')
        return [x/size for x in v]
    tangent=norm([b[i]-a[i] for i in range(3)])
    u=norm(cross(tangent,[0,0,1] if abs(tangent[2])<.9 else [0,1,0]));v=cross(tangent,u)
    length=sqrt(sum((b[k]-a[k])**2 for k in range(3)))
    chord=2*radius_mm*sin(pi/segments)
    # Keep the displayed bar surface triangles close to square in local scale.
    # The cap bounds assembly memory for unusually long/slender concept bars.
    steps=1 if screening else min(192,max(1,ceil(length/(1.2*chord))))
    vertices=[];n=segments
    for level in range(steps+1):
        t=level/steps;p=[a[k]+t*(b[k]-a[k]) for k in range(3)]
        for j in range(n):
            angle=2*pi*j/n
            vertices.append([p[k]+radius_mm*(u[k]*cos(angle)+v[k]*sin(angle)) for k in range(3)])
    vertices.extend([list(a),list(b)]);triangles=[]
    for level in range(steps):
        base=level*n
        for i in range(n):
            j=(i+1)%n
            triangles.extend([[base+i,base+j,base+n+j],[base+i,base+n+j,base+n+i]])
    bottom=(steps+1)*n;top=bottom+1
    for i in range(n):
        j=(i+1)%n
        triangles.extend([[bottom,j,i],[top,steps*n+i,steps*n+j]])
    return {'vertices':vertices,'triangles':triangles,'units':'mm','generator':'Vega Geometry / beam'}
