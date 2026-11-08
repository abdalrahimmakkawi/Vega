"""External FEA of the exact selected topology-optimized axial-bar frame.

CalculiX T3D2 and Ansys LINK180 decks use the saved member connectivity, radii,
loads and supports. These are axial trusses, not beam/buckling/thermal models.
"""
from pathlib import Path
import json
import math
import re
import numpy as np
from .solvers import linux_run


def frame_decks(assembly,folder):
    optimization=assembly.get('frame_optimization')
    if not optimization: return None
    members=assembly['frame_members'];nodes={}
    for m in members:
        for name,xyz in zip(m['nodes'],(m['start_mm'],m['end_mm'])):
            if name in nodes and not np.allclose(nodes[name],xyz,rtol=0,atol=1e-9):raise ValueError('Conflicting frame node coordinates')
            nodes[name]=xyz
    labels=sorted(nodes);index={name:i+1 for i,name in enumerate(labels)}
    last=max(int(n.split('.')[0][1:]) for n in labels)
    fixed=[index[n] for n in labels if n.startswith(f'r{last}.')]
    first=[index[n] for n in labels if n.startswith('r0.')]
    middle=[index[n] for n in labels if n.startswith(f'r{last//2}.')]
    modulus=optimization['assumed_elastic_modulus_n_mm2']
    loads=[[(i,3,optimization['load_cases_n']['axial_total']/len(first)) for i in first],
           [(i,2,optimization['load_cases_n']['transverse_total']/len(middle)) for i in middle]]
    lines=['*HEADING','Vega selected optimized frame; mm N MPa; axial trusses','*NODE,NSET=ALLNODES']
    apdl=['/PREP7','ET,1,LINK180',f'MP,EX,1,{modulus:.16g}','MP,PRXY,1,0.33']
    for name in labels:
        row=f'{index[name]},'+','.join(f'{v:.10g}' for v in nodes[name]);lines.append(row);apdl.append('N,'+row)
    for i,m in enumerate(members,1):
        area=math.pi*m['radius_mm']**2;a,b=[index[n] for n in m['nodes']]
        direction=np.asarray(m['end_mm'])-m['start_mm']
        reference=np.eye(3)[int(np.argmin(abs(direction)))]
        normal=np.cross(direction,reference);normal/=np.linalg.norm(normal)
        lines.extend([f'*ELEMENT,TYPE=T3D2,ELSET=BAR{i}',f'{i},{a},{b}',
                      f'*SOLID SECTION,ELSET=BAR{i},MATERIAL=FRAME',f'{area:.10g}',
                      ','.join(f'{v:.10g}' for v in normal)])
        apdl.extend([f'SECTYPE,{i},LINK',f'SECDATA,{area:.16g}',f'SECNUM,{i}',f'E,{a},{b}'])
    lines.extend(['*MATERIAL,NAME=FRAME','*ELASTIC',f'{modulus:.16g},0.33','*BOUNDARY'])
    for i in fixed:lines.append(f'{i},1,3,0');apdl.append(f'D,{i},ALL,0')
    apdl.extend(['FINISH','/SOLU','ANTYPE,STATIC'])
    for load in loads:
        lines.extend(['*STEP','*STATIC','*CLOAD,OP=NEW'])
        apdl.append('FDELE,ALL,ALL')
        for i,dof,value in load:
            lines.append(f'{i},{dof},{value:.16g}');apdl.append(f'F,{i},{["FX","FY","FZ"][dof-1]},{value:.16g}')
        lines.extend(['*NODE PRINT,NSET=ALLNODES','U,RF','*NODE FILE','U','*END STEP'])
        apdl.append('SOLVE')
    apdl.extend(['FINISH','/POST1','SET,LAST','PRNSOL,U,COMP','FINISH'])
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    (folder/'frame.inp').write_text('\n'.join(lines)+'\n',encoding='ascii')
    (folder/'frame.mapdl').write_text('\n'.join(apdl)+'\n',encoding='ascii')
    return {'nodes':len(labels),'elements':len(members),'loads':loads,'fixed':fixed,'optimization':optimization}


def run_frame(assembly,folder):
    context=frame_decks(assembly,folder)
    if context is None:return {'status':'not_requested','reason':'No topology-optimized frame in this architecture'}
    folder=Path(folder);log=linux_run(['ccx','-i','frame'],folder,'calculix.log',180)
    if '*ERROR' in log.upper():raise RuntimeError('CalculiX reported an error; inspect calculix.log')
    data=(folder/'frame.dat').read_text()
    blocks=re.findall(r'displacements\s*\(.*?\)\s*for set.*?\n\s*\n(.*?)(?=\n\s*\n)',data,re.S|re.I)
    if len(blocks)!=2:raise RuntimeError('Expected two CalculiX displacement result blocks')
    results=[];compliance=0.
    for block,load in zip(blocks,context['loads']):
        rows=[line.split() for line in block.splitlines() if line.strip()]
        u={int(row[0]):np.array([float(x) for x in row[1:4]]) for row in rows}
        if len(u)!=context['nodes'] or not all(np.isfinite(v).all() for v in u.values()):raise RuntimeError('Incomplete CalculiX displacement field')
        c=float(sum(value*u[i][dof-1] for i,dof,value in load));compliance+=c
        results.append({'compliance_n_mm':c,'maximum_displacement_mm':float(max(np.linalg.norm(v) for v in u.values()))})
    reference=context['optimization']['optimized_compliance_n_mm']
    difference=abs(compliance-reference)/max(abs(reference),1e-30)
    result={'status':'computed','solver':'CalculiX','nodes':context['nodes'],'elements':context['elements'],
        'element_type':'T3D2','load_cases':results,'compliance_n_mm':compliance,
        'optimizer_compliance_n_mm':reference,'relative_compliance_difference':difference,
        'optimizer_cross_check_passed':difference<.02,
        'scope':'Exact selected axial-bar frame and representative loads. No beam bending, buckling, pressure wall or joint validation.'}
    (folder/'result.json').write_text(json.dumps(result,indent=2));return result
