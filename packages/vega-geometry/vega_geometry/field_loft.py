"""Field-driven hollow loft for physics-responsive computational geometry."""
from math import cos, sin, pi, sqrt, isfinite


def field_duct(stations, default_wall_mm, segments=128):
    """Loft elliptical/lobed stations while preserving their reference area.

    Optional station fields are lobe_amplitude, lobe_count, twist_rad and
    wall_mm.  Separate parts sharing the same station therefore share the same
    contour.  Semi-axis expansion is a geometric wall approximation.
    """
    stations=list(stations)
    if not isinstance(segments,int) or not 24<=segments<=512:
        raise ValueError('Field loft resolution must be 24 to 512')
    if len(stations)<2 or not isfinite(default_wall_mm) or default_wall_mm<=0:
        raise ValueError('Field loft requires stations and a positive wall')
    last=float('-inf');vertices=[];triangles=[]
    for station in stations:
        z=float(station['z_mm']);width=float(station['width_mm']);height=float(station['height_mm'])
        amplitude=float(station.get('lobe_amplitude',0));count=int(station.get('lobe_count',1))
        twist=float(station.get('twist_rad',0));wall=float(station.get('wall_mm',default_wall_mm))
        if z<=last or min(width,height,wall)<=0 or not all(isfinite(v) for v in (z,width,height,amplitude,twist,wall)):
            raise ValueError('Invalid field loft station')
        if not 1<=count<=24 or not 0<=amplitude<=.25:raise ValueError('Invalid lobe field')
        last=z;normalizer=sqrt(1+amplitude*amplitude/2)
        for extra in (wall,0):
            a=width/2+extra;b=height/2+extra
            for j in range(segments):
                angle=2*pi*j/segments
                field=(1+amplitude*cos(count*angle+twist))/normalizer
                vertices.append([a*field*cos(angle),b*field*sin(angle),z])
    def quad(a,b,c,d):triangles.extend([[a,b,c],[a,c,d]])
    n=segments
    for k in range(len(stations)-1):
        a,b=2*n*k,2*n*(k+1)
        for i in range(n):
            j=(i+1)%n
            quad(a+i,a+j,b+j,b+i);quad(a+n+i,b+n+i,b+n+j,a+n+j)
    end=2*n*(len(stations)-1)
    for i in range(n):
        j=(i+1)%n
        quad(i,n+i,n+j,j);quad(end+i,end+j,end+n+j,end+n+i)
    return {'vertices':vertices,'triangles':triangles,'units':'mm',
            'generator':'Vega Geometry / field_duct',
            'scope':'Area-normalized lobed elliptical loft driven by saved design-state fields; no CFD claim.'}
