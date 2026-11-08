"""Original indexed rectangular duct mesher, independent of PicoGK.

Stations contain z_mm, width_mm, height_mm (internal dimensions). Matching
corners are connected by planar triangles. No booleans or general CAD kernel.
"""
from math import isfinite, cos, sin, pi


def rectangular_duct(stations, wall_mm):
    if isinstance(wall_mm, bool) or not isfinite(wall_mm) or wall_mm <= 0:
        raise ValueError('Wall must be finite and positive')
    stations = list(stations)
    if len(stations) < 2:
        raise ValueError('At least two stations required')
    last = float('-inf')
    vertices, triangles = [], []
    for s in stations:
        z, w, h = (s[k] for k in ('z_mm', 'width_mm', 'height_mm'))
        if any(isinstance(v, bool) or not isfinite(v) for v in (z,w,h)) or z<=last or min(w,h)<=0:
            raise ValueError('Stations require increasing z and positive finite dimensions')
        last = z
        for width, height in ((w+2*wall_mm,h+2*wall_mm),(w,h)):
            vertices.extend([[x*width/2,y*height/2,z] for x,y in ((-1,-1),(1,-1),(1,1),(-1,1))])

    def quad(a,b,c,d):
        triangles.extend([[a,b,c],[a,c,d]])

    for k in range(len(stations)-1):
        a,b=8*k,8*(k+1)
        for i in range(4):
            j=(i+1)%4
            quad(a+i,a+j,b+j,b+i)          # outer wall
            quad(a+4+i,b+4+i,b+4+j,a+4+j)  # inner wall
    end=8*(len(stations)-1)
    for i in range(4):
        j=(i+1)%4
        quad(i,4+i,4+j,j)                 # inlet rim, not a blockage
        quad(end+i,end+j,end+4+j,end+4+i)
    return {'vertices':vertices,'triangles':triangles,'units':'mm',
            'generator':'Vega Geometry / rectangular_duct',
            'scope':'Piecewise linear hollow loft with open inlet and outlet; geometry only.'}


def elliptical_duct(stations, wall_mm, segments=96):
    """Elliptical station loft; wall input expands semi-axes, not normal offset."""
    if not isinstance(segments,int) or isinstance(segments,bool) or not 12<=segments<=512:
        raise ValueError('Ellipse resolution must be an integer from 12 to 512')
    # Share input validation with the rectangular primitive.
    stations=list(stations)
    rectangular_duct(stations,wall_mm)
    vertices,triangles=[],[]
    n=segments
    for s in stations:
        for extra in (wall_mm,0):
            vertices.extend([[(s['width_mm']/2+extra)*cos(2*pi*j/n),
                              (s['height_mm']/2+extra)*sin(2*pi*j/n),s['z_mm']] for j in range(n)])
    def quad(a,b,c,d):triangles.extend([[a,b,c],[a,c,d]])
    for k in range(len(stations)-1):
        a,b=2*n*k,2*n*(k+1)
        for i in range(n):
            j=(i+1)%n
            quad(a+i,a+j,b+j,b+i)
            quad(a+n+i,b+n+i,b+n+j,a+n+j)
    end=2*n*(len(stations)-1)
    for i in range(n):
        j=(i+1)%n
        quad(i,n+i,n+j,j)
        quad(end+i,end+j,end+n+j,end+n+i)
    return {'vertices':vertices,'triangles':triangles,'units':'mm',
            'generator':'Vega Geometry / elliptical_duct',
            'scope':'Polygonal elliptical station loft; semi-axis wall expansion is not a constant normal offset.'}
