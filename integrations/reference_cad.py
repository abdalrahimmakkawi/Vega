"""Independent envelope-only CAD check of Vega's shared axial profile.

These solids deliberately omit passages, tanks and lattices. PicoGK remains the
source of the full component scene and mesh.
"""
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
backend,recipe_file,output_file=sys.argv[1:4]
recipe=json.loads(Path(recipe_file).read_text())
profile=recipe['profile_mm']
wall=recipe['wall_mm']
polygon=[(r,z) for z,r in profile]+[(r+wall,z) for z,r in reversed(profile)]

if backend=='cadquery':
    sys.path.insert(0,str(root/'.tools'/'cadquery'))
    import cadquery as cq
    shape=cq.Workplane('XZ').polyline(polygon).close().revolve(360,(0,0),(0,1))
    cq.exporters.export(shape,output_file)
    volume=float(shape.val().Volume())
elif backend=='build123d':
    sys.path.insert(0,str(root/'.tools'/'build123d'))
    from build123d import Plane,Polygon,revolve,Axis
    shape=revolve(Plane.XZ*Polygon(*polygon,align=None),axis=Axis.Z)
    volume=float(shape.volume)
else:
    raise ValueError('Unsupported CAD backend')

print(json.dumps({'backend':backend,'pressure_shell_envelope_volume_mm3':volume,
                  'scope':'Uncut profile envelope only; not an alternate full engine model.'}))
