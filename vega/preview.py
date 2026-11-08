"""Fast recipe-surface preview. Native boolean and passage verification stays separate."""
from copy import deepcopy
from .rocket import design, mesh
from .geometry_model import fingerprint
from vega_geometry.beam import beam


def geometry_preview(brief):
    run=design(brief);candidate=run['candidates'][0];assembly=candidate['assembly']
    combined=assembly.get('status')=='concept_assembly'
    scene=deepcopy(assembly['scene']) if combined else {'vertices':[],'triangles':[],'bodies':[],'units':'mm'}
    offset=assembly['core_placement']['translation_mm'] if combined else [0,0,0]
    def append(identity,name,shape,color):
        base=len(scene['vertices']);first=len(scene['triangles'])
        scene['vertices'].extend([[p[k]+offset[k] for k in range(3)] for p in shape['vertices']])
        scene['triangles'].extend([[v+base for v in t] for t in shape['triangles']])
        scene['bodies'].append({'component_id':'core_'+identity,'name':name,'group':'core',
            'color':color,'first_triangle':first,'triangle_count':len(scene['triangles'])-first})
    shell=mesh(candidate)
    for body in shell['bodies']:
        first=body['first_triangle'];count=body['triangle_count']
        append(body['component_id'],body['name'],{'vertices':shell['vertices'],
            'triangles':shell['triangles'][first:first+count]},[.65,.48,.31])
    g=candidate['geometry']
    for tank in g['systems']['tanks']:
        start=list(tank['center']);end=list(start)
        start[2]-=tank['length_mm']/2;end[2]+=tank['length_mm']/2
        append(tank['id'],tank['name'],beam(start,end,tank['radius_mm']+tank['wall_mm'],64),[.53,.62,.68])
    for tube in g['systems']['manifolds']:
        shape={'vertices':[],'triangles':[]}
        for start,end in zip(tube['points'],tube['points'][1:]):
            part=beam(start,end,tube['outer_radius_mm'],24);base=len(shape['vertices'])
            shape['vertices'].extend(part['vertices']);shape['triangles'].extend([[i+base for i in t] for t in part['triangles']])
        append(tube['id'],tube['name'],shape,[.68,.47,.28])
    return {'kind':'unsaved_recipe_preview','scene':scene,'geometry_sha256':fingerprint(scene),
        'dimensions':assembly['dimensions'] if combined else candidate['dimensions'],
        'requirements':run['requirements'],'computational_model':run['computational_model'],
        'vehicle_screen':candidate['vehicle_screen'],
        'scope':'Recomputed recipe surfaces and outer tank/feed envelopes. Cooling cuts, injector holes, experimental jacket and native boolean operations require Generate exact design. This preview is not a validated export.'}
