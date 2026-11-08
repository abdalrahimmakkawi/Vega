"""Cheap closed station surfaces for ranking; never a final CAD export."""
import numpy as np
from vega_geometry.sections import contour, validate_stations

def station_surface(stations, section, segments=48):
    stations=validate_stations(stations)
    angles=np.arange(segments)*2*np.pi/segments
    vertices=[];triangles=[]
    for s in stations:
        for extra in (s['wall_mm'],0):
            if section=='rectangular':
                w=s['width_mm']/2+extra;h=s['height_mm']/2+extra
                points=[[w,h,s['z_mm']],[-w,h,s['z_mm']],[-w,-h,s['z_mm']],[w,-h,s['z_mm']]]
            else:points=contour(s,angles,extra).tolist()
            vertices.extend(points)
    n=4 if section=='rectangular' else segments
    def quad(a,b,c,d):triangles.extend([[a,b,c],[a,c,d]])
    for k in range(len(stations)-1):
        a=2*n*k;b=a+2*n
        for i in range(n):
            j=(i+1)%n
            quad(a+i,a+j,b+j,b+i)
            quad(a+n+i,b+n+i,b+n+j,a+n+j)
    end=2*n*(len(stations)-1)
    for i in range(n):
        j=(i+1)%n
        quad(i,n+i,n+j,j);quad(end+i,end+j,end+n+j,end+n+i)
    return {'vertices':vertices,'triangles':triangles,'units':'mm','screening_only':True}
