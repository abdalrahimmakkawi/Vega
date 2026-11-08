"""One Vega assembly recipe shared by topology, meshing, inspection and export.

RBCC/ejector packaging study. The existing rocket hardware is placed without
scaling. An ideal mixer balance bounds the generated throat; pressure loss,
combustion and installed performance remain unresolved.
"""
import math
from .geometry_model import fingerprint
from vega_geometry.beam import beam
from vega_geometry.topology import graph_topology, mesh_topology, reachable
from .cem_state import rbcc_design_state
from .frame_optimization import optimize_frame
from .meshing.cad import cad_duct
from .mesh_validation import inspect_surface


def build_assembly(b, candidate, *, screening=False):
    if b.propulsion_family=='rocket_only':return {'status':'not_requested'}
    if b.propulsion_family=='tbcc':
        return {'status':'unsupported_family','reason':'TBCC requires turbine maps and a separate turbine flowpath; the RBCC assembly is not substituted.'}
    reference=candidate['vehicle_screen']['inlet_reference']
    if not reference or not reference.get('mesh'):
        return {'status':'outside_reference_domain','reason':reference.get('reason','No inlet state') if reference else 'No inlet state'}
    g=candidate['geometry'];wall=b.inlet_wall_mm;ratio=b.inlet_aspect_ratio
    coeff=1 if b.inlet_section=='rectangular' else math.pi/4
    core_min=min(t['center'][2]-t['length_mm']/2 for t in g['systems']['tanks'])
    core_end=g['profile_mm'][-1][0]
    inlet_end=max(b.inlet_length_m*1000,core_end-core_min+100)
    offset=inlet_end-core_end
    xbound=candidate['dimensions']['diameter_mm']/2
    ybound=max([t['radius_mm']+t['wall_mm'] for t in g['systems']['tanks']]+
               [r+b.wall_mm for _,r in g['profile_mm']]+[g['jacket']['outer_radius_mm']])
    clearance=max(10,2*wall)
    # Bounding-box allowance is conservative, not the actual wetted blockage.
    blockage=4*xbound*ybound/1e6
    package_area=4*coeff*((xbound+clearance)**2/ratio+(ybound+clearance)**2*ratio)/.8/1e6
    stations=[]
    def station(z,area,**fields):
        width=math.sqrt(area*1e6*ratio/coeff)
        return {'z_mm':z,'width_mm':width,'height_mm':width/ratio,'gross_area_m2':area,
                'lobe_amplitude':fields.get('lobe_amplitude',0.0),
                'lobe_count':fields.get('lobe_count',1),'twist_rad':fields.get('twist_rad',0.0),
                'wall_mm':fields.get('wall_mm',wall)}
    for s in reference['stations']:
        z=s['z_mm']/reference['dimensions']['length_mm']*inlet_end
        area=s['area_m2']
        if z>=core_min+offset-clearance:area=max(area+blockage,package_area)
        stations.append(station(z,area))
    # Ensure the station immediately before the embedded core also contains it.
    before=max(i for i,s in enumerate(stations) if s['z_mm']<=core_min+offset)
    for i in range(before,len(stations)):
        stations[i]=station(stations[i]['z_mm'],max(stations[i]['gross_area_m2'],package_area,reference['stations'][i]['area_m2']+blockage))
    interface=stations[-1];area=interface['gross_area_m2']
    width,height=interface['width_mm'],interface['height_mm']
    hydraulic_diameter=2*width*height/(width+height) # rectangular perimeter proxy, labeled below
    specifications=[('air_inlet','Air inlet / core bay',stations,'cold_reference_with_packaging_allowance'),
                    ('mixer','Lobed rocket / air mixer',None,'mass_and_momentum_responsive'),
                    ('isolator','Twisted isolator envelope',None,'thermal_and_flow_responsive'),
                    ('air_combustor','Lobed air combustor envelope',None,'thermal_and_flow_responsive'),
                    ('common_nozzle','Morphing common expansion nozzle',None,'flow_responsive')]
    z=inlet_end
    rocket_exit_area=candidate['performance']['exit_area_m2']
    design_state=rbcc_design_state(b,candidate,area,hydraulic_diameter)
    areas=design_state['area_m2'];fields=design_state['geometry_fields']
    downstream=[(b.mixer_length_dh*hydraulic_diameter,areas['mixer_exit']),
                (1.25*hydraulic_diameter,areas['isolator_exit']),
                (b.combustor_length_dh*hydraulic_diameter,areas['combustor_exit']),
                (3*hydraulic_diameter,areas['common_nozzle_exit'])]
    sections=[stations]
    for index,(length,target_area) in enumerate(downstream):
        start=sections[-1][-1];section=[start]
        for j in range(1,25):
            t=j/24;blend=t*t*(3-2*t)
            if index in (0,3):
                transition=.30 if index==0 else .25
                throat=areas['mixer_throat'] if index==0 else areas['common_nozzle_throat']
                if t<transition:
                    u=t/transition;current=start['gross_area_m2']+(throat-start['gross_area_m2'])*u*u*(3-2*u)
                else:
                    u=(t-transition)/(1-transition);current=throat+(target_area-throat)*u*u*(3-2*u)
            else:current=start['gross_area_m2']+(target_area-start['gross_area_m2'])*blend
            peak=fields['peak_lobe_amplitude'];start_amp=start.get('lobe_amplitude',0)
            targets=(.45*peak,.28*peak,.65*peak,0.0)
            amplitude=start_amp+(targets[index]-start_amp)*blend
            twist=start.get('twist_rad',0)+fields['total_twist_rad']*(.45,.15,.25,.15)[index]*blend
            wall_target=wall*(1,1.05,fields['hot_wall_factor'],1+.12*fields['hot_wall_factor'])[index]
            local_wall=start.get('wall_mm',wall)+(wall_target-start.get('wall_mm',wall))*blend
            section.append(station(z+t*length,current,lobe_amplitude=amplitude,
                                   lobe_count=fields['lobe_count'],twist_rad=twist,wall_mm=local_wall))
        z+=length;sections.append(section)
    scene={'vertices':[],'triangles':[],'bodies':[],'units':'mm'};parts=[];audits={};quality={};tessellation={}
    def append(identity,name,shape,color,group,role):
        start=len(scene['triangles']);base=len(scene['vertices'])
        scene['vertices'].extend(shape['vertices']);scene['triangles'].extend([[i+base for i in t] for t in shape['triangles']])
        span=[min(p[2] for p in shape['vertices']),max(p[2] for p in shape['vertices'])]
        scene['bodies'].append({'component_id':identity,'name':name,'first_triangle':start,
            'triangle_count':len(shape['triangles']),'color':color,'group':group})
        parts.append({'id':identity,'name':name,'axial_mm':span,'role':role,'group':group})
        audit,quality[identity]=inspect_surface(shape);audits[identity]=audit
        if shape.get('tessellation'):tessellation[identity]=shape['tessellation']
        if len(scene['triangles'])>2500000:raise ValueError('Assembly surface mesh exceeds 2.5 million triangles; relax mesh controls')
        if not audit['closed_manifold'] or not audit['winding_consistent'] or audit['signed_volume_mm3']<=0:
            raise ValueError('Vega topology check failed: '+identity)
    resolution=None  # CAD mesher chooses local edge density; there is no global ring grid.
    for i,(identity,name,_,state) in enumerate(specifications):
        if screening:
            from .meshing.screening import station_surface
            shape=station_surface(sections[i],b.inlet_section)
        else:shape=cad_duct(sections[i],b.mesh_surface_edge_mm,b.mesh_chord_tolerance_mm,b.inlet_section)
        append(identity,name,shape,[[.34,.55,.61],[.46,.61,.51],[.57,.53,.38],[.76,.40,.25],[.33,.45,.59]][i],
               'shell',state.replace('_',' ')+'. Generated from the shared CEM state; combustion, mixing, losses and startability remain unresolved.')
    interfaces=[]
    for i in range(len(sections)-1):
        a,bound=sections[i][-1],sections[i+1][0]
        interfaces.append({'from':specifications[i][0],'to':specifications[i+1][0],
                           'station':a,'gap_mm':abs(a['z_mm']-bound['z_mm']),
                           'section_mismatch_mm':max(abs(a[k]-bound[k]) for k in ('width_mm','height_mm','lobe_amplitude','twist_rad','wall_mm'))})
    # Frame graph: straight bars, matching the axial-bar FE discretization.
    # A curved wrap is not mechanically equivalent to the analyzed chord.
    frame_sections=[sections[0][0]]+[s[-1] for s in sections]
    nodes={};edges=[];sectors=int(b.frame_sectors);beam_radius=max(fields['rib_radius_mm'],wall*.35,b.minimum_ligament_mm)
    frame_standoff=24*beam_radius
    for k,s in enumerate(frame_sections):
        for j in range(sectors):
            angle=2*math.pi*j/sectors
            envelope=1+s.get('lobe_amplitude',0)
            nodes[f'r{k}.{j}']=[(s['width_mm']/2*envelope+s.get('wall_mm',wall)+frame_standoff)*math.cos(angle),
                               (s['height_mm']/2*envelope+s.get('wall_mm',wall)+frame_standoff)*math.sin(angle),s['z_mm']]
    # For rectangular ducts, locate frame nodes outside rectangle corners.
    if b.inlet_section=='rectangular':
        for key,p in nodes.items():
            k=int(key.split('.')[0][1:]);s=frame_sections[k]
            scale=1/max(abs(math.cos(2*math.pi*int(key.split('.')[1])/sectors)),abs(math.sin(2*math.pi*int(key.split('.')[1])/sectors)))
            p[0]*=scale;p[1]*=scale
    for k in range(len(frame_sections)):
        for j in range(sectors):
            edges.append((f'r{k}.{j}',f'r{k}.{(j+1)%sectors}'))
            if k:
                edges.append((f'r{k-1}.{j}',f'r{k}.{j}'))
                if b.frame_topology in ('braced','optimized'):
                    edges.append((f'r{k-1}.{j}',f'r{k}.{(j+1)%sectors}'))
                if b.frame_topology=='optimized':
                    edges.append((f'r{k-1}.{j}',f'r{k}.{(j-1)%sectors}'))
    optimization=None
    if b.frame_topology=='optimized':
        optimization=optimize_frame(nodes,edges,sectors,beam_radius,
            max(1.0,b.minimum_ligament_mm/2),b.frame_volume_fraction,
            b.thrust_n,candidate['vehicle_screen']['transition']['dynamic_pressure_pa'],
            b.inlet_capture_area_m2)
        edges=[(a,d) for a,d in edges if f'{a}|{d}' in optimization['edge_radii_mm']]
    # Members are distinct solids meeting at graph nodes, not a boolean union.
    frame={'vertices':[],'triangles':[],'units':'mm'}
    profile=sections[0]+[s for section in sections[1:] for s in section[1:]]
    def state_at(z):
        for a,d in zip(profile,profile[1:]):
            if z<=d['z_mm']+1e-7:
                t=max(0,min(1,(z-a['z_mm'])/(d['z_mm']-a['z_mm'])))
                return {key:a[key]+t*(d[key]-a[key]) for key in ('width_mm','height_mm','lobe_amplitude','twist_rad','wall_mm')}
        return {key:profile[-1][key] for key in ('width_mm','height_mm','lobe_amplitude','twist_rad','wall_mm')}
    def dimensions_at(z):
        state=state_at(z);return [state['width_mm'],state['height_mm']]
    def surface_point(z,angle,clearance):
        state=state_at(z);co,si=math.cos(angle),math.sin(angle)
        if b.inlet_section=='rectangular':
            scale=1/max(abs(co),abs(si));field=1
        else:
            scale=1;field=1+state['lobe_amplitude']*math.cos(fields['lobe_count']*angle+state['twist_rad'])
        return [(state['width_mm']/2*field+state['wall_mm']+clearance)*co*scale,
                (state['height_mm']/2*field+state['wall_mm']+clearance)*si*scale,z]
    def frame_point(z,angle):
        return surface_point(z,angle,frame_standoff)
    def add_beam(mesh,a,d,radius,segments=8):
        shape=beam(a,d,radius,segments,screening=screening)
        base=len(mesh['vertices']);mesh['vertices'].extend(shape['vertices']);mesh['triangles'].extend([[i+base for i in t] for t in shape['triangles']])
    def append_beam(a,d,radius):add_beam(frame,a,d,radius,12)
    frame_samples=[];frame_members=[]
    for a,d in edges:
        start,end=nodes[a],nodes[d]
        radius=optimization['edge_radii_mm'][f'{a}|{d}'] if optimization else beam_radius
        append_beam(start,end,radius)
        frame_samples.extend(([start[k]+i/64*(end[k]-start[k]) for k in range(3)],radius) for i in range(65))
        frame_members.append({'nodes':[a,d],'start_mm':list(start),'end_mm':list(end),
                              'radius_mm':radius,'length_mm':math.dist(start,end)})
    # Tie each frame ring to its wall at preserved attachment regions.
    for k,s in enumerate(frame_sections):
        for j in range(sectors):
            angle=2*math.pi*j/sectors;co,si=math.cos(angle),math.sin(angle)
            scale=1 if b.inlet_section=='elliptical' else 1/max(abs(co),abs(si))
            anchor=surface_point(s['z_mm'],angle,-s.get('wall_mm',wall)*.3)
            key=f'anchor{k}.{j}';nodes[key]=anchor;edges_to_add=(key,f'r{k}.{j}')
            append_beam(anchor,nodes[edges_to_add[1]],beam_radius)
    edges.extend((f'anchor{k}.{j}',f'r{k}.{j}') for k in range(len(frame_sections)) for j in range(sectors))
    append('frame','Optimized load-path frame' if optimization else 'Branching support frame',frame,[.66,.67,.59],'frame',
           ('Member radii follow a volume-constrained axial-truss compliance optimization. '+optimization['limits']) if optimization else
           'Generated from a connected ring/rail graph. Beam joints are overlapping component solids; loads and buckling are unresolved.')

    # CEM-field geometry: counter-wound conformal ribs respond to the saved
    # thermal index, air/rocket mass fraction and manufacturing feature screen.
    thermal={'vertices':[],'triangles':[]};thermal_routes=[]
    hot_start=sections[3][0]['z_mm'];hot_end=sections[4][-1]['z_mm'];samples=72
    for hand in (-1,1):
        route=[]
        for i in range(samples+1):
            t=i/samples;at_z=hot_start+t*(hot_end-hot_start)
            angle=hand*2*math.pi*fields['rib_turns']*t+(0 if hand==1 else math.pi/sectors)
            route.append(surface_point(at_z,angle,fields['rib_radius_mm']*1.8))
        for p,q in zip(route,route[1:]):add_beam(thermal,p,q,fields['rib_radius_mm'],10)
        thermal_routes.append({'handedness':hand,'points':route})
    for station_value in (sections[3][0],sections[3][-1],sections[4][-1]):
        ring=[surface_point(station_value['z_mm'],2*math.pi*i/48,fields['rib_radius_mm']*1.8) for i in range(48)]
        for p,q in zip(ring,ring[1:]+ring[:1]):add_beam(thermal,p,q,fields['rib_radius_mm'],10)
    append('thermal_reinforcement','Counter-wound thermal reinforcement',thermal,[.82,.48,.22],'thermal',
           'Conformal double helix and interface rings are sized by the shared thermal/manufacturing fields. They are a structural heat-spreading hypothesis; loads and heat conduction are not solved.')

    # Internal mixer strakes expose the rocket/air coupling as geometry. Their
    # count, curvature and size derive from the same flow-responsive state.
    strakes={'vertices':[],'triangles':[]};strake_routes=[];mixer=sections[1]
    core_radius=max(math.sqrt(candidate['performance']['exit_area_m2']/math.pi)*1000,g['profile_mm'][-1][1])
    for index in range(fields['lobe_count']):
        start_angle=2*math.pi*index/fields['lobe_count'];route=[]
        for j in range(9):
            t=j/8;sample=mixer[round(t*(len(mixer)-1))]
            angle=start_angle+.35*fields['total_twist_rad']*t
            inner=core_radius+fields['strake_radius_mm']*2
            outer=.38*min(sample['width_mm'],sample['height_mm'])
            radial=inner+(outer-inner)*t
            route.append([radial*math.cos(angle),radial*math.sin(angle),sample['z_mm']])
        for p,q in zip(route,route[1:]):add_beam(strakes,p,q,fields['strake_radius_mm'],10)
        strake_routes.append(route)
    append('mixer_strakes','Helical mixer strakes',strakes,[.88,.66,.31],'mixing',
           'Curved strakes scale with rocket exit radius, air/rocket mass fraction and the manufacturing feature screen. Mixing effectiveness and pressure loss require CFD or test evidence.')
    # Explicit supports prevent the placed core from being a floating subassembly.
    # Their attachment regions are geometric inputs, not load-sized mount designs.
    mounts={'vertices':[],'triangles':[]};mount_routes=[]
    chamber_radius=g['profile_mm'][0][1]
    for local_z in (b.chamber_length_mm*.25,b.chamber_length_mm*.75):
        at_z=local_z+offset;_,height=dimensions_at(at_z)
        for sign in (-1,1):
            start=[0,sign*(chamber_radius+b.wall_mm-2),at_z]
            end=[0,sign*(height/2+wall*.5),at_z]
            shape=beam(start,end,beam_radius,12);base=len(mounts['vertices'])
            mounts['vertices'].extend(shape['vertices']);mounts['triangles'].extend([[i+base for i in t] for t in shape['triangles']])
            mount_routes.append({'start_mm':start,'end_mm':end})
    append('core_mounts','Core-to-duct mounting struts',mounts,[.62,.66,.69],'mounts',
           'Four radial supports connect pressure-shell attachment regions to duct walls. Attachment stress, cooling interference and aerodynamic blockage require analysis.')
    # The propellant network comes from the registered geometry ports and
    # routes. Do not maintain a second, hand-written diagram that can disagree
    # with the tubes and cooling circuit sent to the native mesher.
    model=candidate['geometry_model']
    ports={p['id']:p for p in model['ports']}
    alias={'cooling_channels':'cooling','injector_head':'injector'}
    def owner(port_id):
        return alias.get(ports[port_id]['component'],ports[port_id]['component'])
    flow_edges=[[owner(r['source']),route_id] for route_id,r in model['routes'].items()]
    flow_edges.extend([route_id,owner(r['target'])] for route_id,r in model['routes'].items())
    flow_edges.extend([['air_inlet','mixer'],['rocket_core','mixer'],['mixer','isolator'],
                       ['isolator','air_combustor'],['air_combustor','common_nozzle'],
                       ['injector','rocket_core']])
    flow_nodes=list(dict.fromkeys(n for edge in flow_edges for n in edge))
    frame_audit=graph_topology(nodes,edges);flow_audit=graph_topology(flow_nodes,flow_edges)
    # Centerline sample screen only. Full swept-solid interference is unresolved.
    def outside_shell(p,radius):
        state=state_at(p[2]);factor=1+state['lobe_amplitude']
        # This gate protects the internal flow opening. Full frame/skin swept
        # solid interference remains an explicitly unresolved check.
        xlimit=state['width_mm']/2*factor+state['wall_mm']+radius
        ylimit=state['height_mm']/2*factor+state['wall_mm']+radius
        return ((p[0]/xlimit)**2+(p[1]/ylimit)**2>1 if b.inlet_section=='elliptical'
                else max(abs(p[0])/xlimit,abs(p[1])/ylimit)>1)
    frame_clear=all(outside_shell(p,radius) for p,radius in frame_samples)
    scene_hash=fingerprint(scene)
    result={'screening_only':screening,'schema_version':4,'status':'concept_assembly','generator':'Vega Geometry 0.4.0 conditional-flow CEM','family':b.propulsion_family,
            'scene':scene,'components':parts,'interfaces':interfaces,'sections':sections,
            'design_state':design_state,
            'frame_optimization':optimization,
            'mesh_quality':quality,'surface_tessellation':tessellation,
            'mesh_policy':{'version':2,'backend':'Station-surface screening' if screening else 'Gmsh/OpenCASCADE','surface_edge_mm':b.mesh_surface_edge_mm,
                           'chord_tolerance_mm':b.mesh_chord_tolerance_mm,'shared_angular_segments':resolution,
                           'support_bar_surface':'radius/chord axial subdivision, 12-sided rings, 192-level cap',
                           'scope':'Gmsh CAD surface meshing for elliptical/lobed and rectangular ducts. Hybrid CFD and solid FEA volumes are separate solver artifacts.'},
            'frame_members':frame_members,
            'section_design':{'mixer_inlet_area_m2':areas['mixer_inlet'],'mixer_throat_area_m2':areas['mixer_throat'],
                              'mixer_exit_area_m2':areas['mixer_exit'],'isolator_exit_area_m2':areas['isolator_exit'],
                              'combustor_exit_area_m2':areas['combustor_exit'],'common_nozzle_throat_area_m2':areas['common_nozzle_throat'],
                              'common_nozzle_exit_area_m2':areas['common_nozzle_exit'],
                              'peak_lobe_amplitude':fields['peak_lobe_amplitude'],'total_twist_rad':fields['total_twist_rad'],
                              'minimum_ideal_choked_area_m2':areas['minimum_ideal_choked'],
                              'status':'conditional_ideal_mixing_no_closed_hot_flow'},
            'generated_field_routes':{'thermal_reinforcement':thermal_routes,'mixer_strakes':strake_routes},
            'core_mount_routes':mount_routes,
            'core_placement':{'translation_mm':[0,0,offset],'scale':1,'bounding_box_half_xy_mm':[xbound,ybound],
                              'minimum_z_mm':core_min+offset,'exit_z_mm':core_end+offset},
            'dimensions':{'length_mm':z+2*beam_radius,'diameter_mm':max(math.hypot(s['width_mm'],s['height_mm'])*(1+s.get('lobe_amplitude',0))+2*s.get('wall_mm',wall) for section in sections for s in section)+2*frame_standoff},
            'topology':{'flow':{**flow_audit,'nodes':flow_nodes,'edges':flow_edges},
                        'frame':{**frame_audit,'nodes':nodes,'edges':edges,'kind':b.frame_topology},
                        'mounts':graph_topology(['core','mounts','duct','frame'],[('core','mounts'),('mounts','duct'),('duct','frame')]),'surfaces':audits},
            'checks':{'shared_sections_coincident':all(i['gap_mm']<1e-6 and i['section_mismatch_mm']<1e-6 for i in interfaces),
                      'rocket_exit_at_mixer_inlet':abs(core_end+offset-inlet_end)<1e-6,
                      'core_inside_axial_bay':core_min+offset>=0,
                      'frame_graph_connected':frame_audit['connected_components']==1,
                      'optimized_frame_improves_compliance':optimization['optimized_compliance_n_mm']<=optimization['baseline_uniform_compliance_n_mm']*(1+1e-6) if optimization else True,
                      'optimized_frame_volume_respected':optimization['volume_fraction_actual']<=b.frame_volume_fraction+1e-4 if optimization else True,
                      'frame_centerline_samples_outside_flow':frame_clear,
                      'shared_cem_state_passed':all(design_state['checks'].values()),
                      'field_geometry_generated':all(identity in audits for identity in ('thermal_reinforcement','mixer_strakes')),
                      'all_supplies_reach_exhaust':all(reachable(flow_edges,s,'common_nozzle') for s in ('air_inlet','fuel_tank','oxidizer_tank')),
                      'closed_component_surfaces':all(a['closed_manifold'] for a in audits.values())},
            'unknown_checks':design_state['unresolved']+['Frame/skin interference and joint manufacture',
                'Frame bending, buckling, joint strength, thermal stress and validated load cases'] if optimization else design_state['unresolved']+['Frame/skin interference and joint manufacture'],
            'assumptions':design_state['heuristics']+[
                           'Stage length scale uses rectangular hydraulic-diameter proxy 2wh/(w+h), including for elliptical sections.',
                           'A conservative rocket-package bounding box expands the inlet bay; the original unobstructed cold-flow reference does not describe installed flow.',
                           'All core bodies retain physical scale. Frame and duct exports are a multi-body assembly, not a fused manufacturing solid.'],
            'sources':['https://ntrs.nasa.gov/citations/19980237203','https://ntrs.nasa.gov/citations/20000038202']+design_state['ideal_mixer']['sources']+([optimization['source']] if optimization else []),
            'scene_sha256':scene_hash}
    result['recipe_sha256']=fingerprint({'scene':scene_hash,'core':candidate['geometry'],'placement':result['core_placement'],
                                         'frame':b.frame_topology,'frame_optimization':optimization,'design_state':design_state})
    if not all(result['checks'].values()):
        raise ValueError('Assembly topology or placement failed: '+', '.join(k for k,v in result['checks'].items() if not v))
    return result
