"""Non-firing subsystem review layout. No operating-cycle or hot-fire claim."""
import numpy as np
import trimesh

BASE_RUN='b0ce0e98b2d145639cddef3904c392e7'

def modules():
    parts=[]
    def add(identity,name,xy,z,r,length,kind='duct',wall=1.4,role='',group='external'):
        if 'exchanger' in name.lower() or identity=='intercooler':kind='heat-exchanger'
        p=dict(id=identity,name=name,kind=kind,center_mm=xy,profile=[[z,r],[z+length,r]],wall=wall,
               role=role,group=group,voxel_mm=.1,reference='A'+str(40+len(parts)),
               color=[.38,.65,.69] if group=='external' else [.64,.62,.77])
        if kind=='rotor':p.update(hub_outer=r,tip_radius=21,blade_count=10,z_start=z,z_end=z+length)
        parts.append(p);return p
    add('lp-compressor','Low-pressure compressor stage',[0,0],50,12,4,'rotor',3,'First static compressor row; pressure ratio and shaft matching not solved.','core')
    add('hp-compressor','High-pressure compressor stage',[0,0],56,12,4,'rotor',3,'Second static compressor row; replaces the generic compressor in this review.','core')
    add('bypass-fan','Bypass fan representation',[0,0],14,10,4,'rotor',1.5,'Static fan row. A sealed bypass branch and fan map remain unresolved.','core')
    p=add('hub-turbine','Hub turbine representation',[0,0],119,5,3,'rotor',2,'Static turbine row; no shaft power prediction.','core');p['tip_radius']=14
    add('intercooler','Intercooler',[-72,-35],45,7,20,role='External review envelope; connection between compressor stages is proposed, not a built internal air duct.')
    add('main-heat-exchanger','Main heat exchanger',[-72,0],45,8,24,role='External main thermal exchange module; two-fluid passages and thermal duty remain undefined.')
    add('hx3','HX3 / pre-burner heat exchanger',[-72,35],85,7,20,role='Thermal interface proposed near pre-burner; no hot-flow operation.')
    add('lox-heat-exchanger','LOX heat exchanger',[72,-35],85,7,20,role='Alternative oxidizer thermal-conditioning envelope; no cryogenic performance.')
    add('high-temperature-hx','High-temperature heat exchanger',[72,35],125,8,24,role='High-temperature exchanger envelope only; no material temperature rating.')
    add('liquid-air-hx','Liquid-air heat exchanger',[-72,-35],125,8,24,role='Alternative air-conditioning subsystem. Air liquefaction is not established or required by the baseline case.')
    add('gas-generator','Gas generator representation',[-72,0],101,7,18,role='Non-firing gas-generator housing with open inspection passage.')
    for identity,name,x in [('lh2-reservoir','LH2 tank / reservoir representation',-112),('lox-reservoir','LOX tank / reservoir representation',112)]:
        add(identity,name,[x,0],28,13,44,'tank',role='Solid display envelope only. Not a pressure vessel or cryogenic tank design.')
    for identity,name,x in [('hydrogen-isolation-valve','Hydrogen isolation valve representation',-112),('oxygen-isolation-valve','LOX isolation valve representation',112)]:
        add(identity,name,[x,0],77,4,9,'valve',role='Static valve envelope; no shutoff, seal or actuation model.')
    add('injector-face','Injector-face representation',[0,0],135,10.5,2,wall=7,role='Annular interface placeholder; no fuel injection or atomization design.',group='core')
    add('chamber-liner','Chamber liner representation',[0,0],139,8.8,8,wall=1,role='Static liner inside the existing chamber. No firing or thermal qualification.',group='core')
    p=add('turbine-exhaust','Turbine exhaust outlet',[0,0],132,18,3,wall=1.2,role='Annular exhaust collector envelope; fluid separation from the chamber is unresolved.',group='core')
    p=add('bypass-nozzle','Annular bypass nozzle',[0,0],187,30,20,wall=1.6,role='Dedicated annular outlet geometry; upstream bypass duct and performance are not established.',group='core')
    p['profile']=[[187,30],[192,30],[207,26]]
    return parts

def input_mesh(part):
    if part['kind']=='tank':
        mesh=trimesh.creation.icosphere(subdivisions=3)
        mesh.apply_scale([13,13,22]);mesh.apply_translation([*part['center_mm'],50]);return mesh
    rows=np.asarray(part['profile'],float)
    polygon=np.vstack([rows[:,[1,0]],np.column_stack([rows[::-1,1]-part['wall'],rows[::-1,0]]),rows[0,[1,0]]])
    mesh=trimesh.creation.revolve(polygon,sections=80)
    if mesh.volume<0:mesh.invert()
    mesh.apply_translation([*part['center_mm'],0])
    if not mesh.is_volume:raise ValueError('Open subsystem input: '+part['id'])
    return mesh

def connections():
    # These are proposed functional relationships, never claims of fluid continuity.
    return [dict(source=a,target=b,medium=medium,status='proposed; not flow-validated') for a,b,medium in [
        ('precooler','lp-compressor','air'),('lp-compressor','intercooler','air'),('intercooler','hp-compressor','air'),
        ('hp-compressor','bell-chamber','air'),('bypass-fan','bypass-nozzle','bypass air'),
        ('hub-turbine','bypass-fan','shaft power'),('drive-turbine','hp-compressor','shaft power'),
        ('lh2-reservoir','hydrogen-isolation-valve','hydrogen-labelled supply'),
        ('hydrogen-isolation-valve','hydrogen-pump','hydrogen-labelled supply'),
        ('lox-reservoir','oxygen-isolation-valve','oxygen-labelled supply'),
        ('oxygen-isolation-valve','lox-pump','oxygen-labelled supply'),
        ('lox-pump','lox-heat-exchanger','optional oxidizer conditioning'),
        ('main-heat-exchanger','helium-circulator','thermal loop'),('helium-circulator','precooler','thermal loop'),
        ('hx3','pre-burner','thermal interface'),('gas-generator','drive-turbine','concept gas path'),
        ('drive-turbine','turbine-exhaust','concept exhaust'),('injector-face','chamber-liner','chamber interface'),
        ('high-temperature-hx','main-heat-exchanger','optional thermal exchange'),
        ('liquid-air-hx','main-heat-exchanger','alternative thermal arrangement')]]
