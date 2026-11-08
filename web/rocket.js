'use strict';

const $=s=>document.querySelector(s),canvas=$('#model');

const propellantLabel=document.createElement('label');propellantLabel.textContent='Propellant chemistry';const propellant=document.createElement('select');propellant.name='propellant_model';for(const [value,label] of [['lox_rp1','LOX / RP-1 · RocketCEA'],['lox_lh2','LOX / LH2 · RocketCEA'],['assumed','Manual gas properties']])propellant.append(new Option(label,value));propellantLabel.append(propellant);$('#fields').append(propellantLabel);

const fields=[['thrust_n','Target thrust · N',1000,100,10000],['chamber_pressure_bar','Chamber · bar',20,2,100],['tank_pressure_bar','Tank pressure · bar',35,5,150],['burn_duration_s','Burn duration · s',2,.5,20],['ambient_pressure_bar','Ambient · bar',0,0,2],['expansion_ratio','Exit / throat area',8,1.1,30],['chamber_temperature_k','Gas temperature · K',3000,300,4500],['gamma','Gas gamma',1.22,1.05,1.67],['gas_constant_j_kg_k','Gas R · J/(kg K)',350,100,1000],['chamber_area_ratio','Chamber / throat area',4,2,10],['chamber_length_mm','Chamber length · mm',120,40,500],['wall_mm','Wall thickness · mm',10,2,15],['nozzle_half_angle_deg','Reference cone angle · °',15,8,25],['pressure_reserve_bar','Pressure reserve · bar',2,0,20],['injector_pressure_drop_fraction','Injector loss fraction',.2,.05,.5],['design_heat_flux_mw_m2','Assumed heat flux · MW/m²',.5,.1,5],['max_coolant_outlet_k','Coolant bulk limit · K',425,50,900],['allowable_stress_mpa','Allowable hoop stress · MPa',80,10,1000],['minimum_ligament_mm','Minimum ligament · mm',2,1,5]];

for(const [name,label,value,min,max] of fields){const l=document.createElement('label');l.textContent=label;const i=document.createElement('input');Object.assign(i,{name,type:'number',value,min,max,step:'any',required:true});l.append(i);$('#fields').append(l);}

const mixtureLabel=document.createElement('label');mixtureLabel.textContent='Oxidizer / fuel mass ratio';const mixture=document.createElement('input');Object.assign(mixture,{name:'mixture_ratio',type:'number',value:2.6,min:1,max:8,step:'any',required:true});mixtureLabel.append(mixture);$('#fields').append(mixtureLabel);

function updateChemistryFields(){const manual=propellant.value==='assumed';for(const name of ['chamber_temperature_k','gamma','gas_constant_j_kg_k'])$('#requirements').elements[name].disabled=!manual;mixture.disabled=manual;}

propellant.onchange=updateChemistryFields;updateChemistryFields();

const patternLabel=document.createElement('label');patternLabel.textContent='Experimental outer jacket';const pattern=document.createElement('select');pattern.name='jacket_pattern';for(const [value,label] of [['penrose','Penrose layers · current default'],['none','No jacket · simpler baseline'],['bcc','Body-centred lattice'],['quasi','Quasicrystal clusters']])pattern.append(new Option(label,value));patternLabel.append(pattern);$('#fields').append(patternLabel);

const coolingLabel=document.createElement('label');coolingLabel.textContent='Fuel wall passages';const cooling=document.createElement('select');cooling.name='cooling_passages';cooling.append(new Option('Ranked passage layout','1'),new Option('Disable passage layout','0'));coolingLabel.append(cooling);$('#fields').append(coolingLabel);

const variantLabel=document.createElement('label');variantLabel.textContent='Passage variant to mesh';const variant=document.createElement('select');variant.name='channel_variant';for(const [value,label] of [[0,'Auto · highest ranked'],[8,'8 channels'],[12,'12 channels'],[16,'16 channels']])variant.append(new Option(label,value));variantLabel.append(variant);$('#fields').append(variantLabel);

const contourLabel=document.createElement('label');contourLabel.textContent='Nozzle contour';const contour=document.createElement('select');contour.name='nozzle_contour';for(const [value,label] of [['bell','Cubic bell · current default'],['conical','Straight conical baseline']])contour.append(new Option(label,value));contourLabel.append(contour);$('#fields').append(contourLabel);

const architectureLabel=document.createElement('label');architectureLabel.textContent='Rocket core feed';const architecture=document.createElement('select');architecture.name='architecture';architecture.append(new Option('Pressure-fed · tanks + feed network','pressure_fed'));architectureLabel.append(architecture);$('#fields').append(architectureLabel);

const vehicleLabel=document.createElement('label');vehicleLabel.textContent='Vehicle architecture';const vehicleArchitecture=document.createElement('select');vehicleArchitecture.name='vehicle_architecture';for(const [v,l] of [['spaceplane','Lifting-body spaceplane'],['vertical','Vertical spacecraft'],['air_launch','Air-launch spacecraft']])vehicleArchitecture.append(new Option(l,v));vehicleLabel.append(vehicleArchitecture);$('#fields').append(vehicleLabel);

const familyLabel=document.createElement('label');familyLabel.textContent='Propulsion family';const family=document.createElement('select');family.name='propulsion_family';for(const [v,l] of [['rbcc','RBCC · rocket + airbreathing'],['tbcc','TBCC · turbine + ram/scram'],['ejector_rocket','Ejector rocket'],['rocket_only','Rocket-only baseline']])family.append(new Option(l,v));familyLabel.append(family);$('#fields').append(familyLabel);

for(const [name,label,value,min,max] of [['cell_size_mm','Cell / layer spacing · mm',12,8,25],['beam_radius_mm','Beam radius · mm',2.5,1,3],['jacket_depth_mm','Jacket depth · mm',10,6,20]]){const l=document.createElement('label');l.textContent=label;const i=document.createElement('input');Object.assign(i,{name,type:'number',value,min,max,step:'any',required:true});l.append(i);$('#fields').append(l);}

const thermalLabel=document.createElement('label');thermalLabel.textContent='Thermal model';const thermalSelect=document.createElement('select');thermalSelect.name='thermal_model';thermalSelect.append(new Option('Distributed thermal resistance','thermal_resistance'),new Option('Prescribed heat flux (legacy)','prescribed_flux'));thermalLabel.append(thermalSelect);$('#fields').append(thermalLabel);

const advanced=document.createElement('details');advanced.className='advanced';const summary=document.createElement('summary');summary.textContent='Pressurization and thermal assumptions';advanced.append(summary);const advancedGrid=document.createElement('div');advancedGrid.className='advanced-grid';for(const [name,label,value,min,max] of [['pressurant_storage_bar','Helium storage · bar',200,40,350],['pressurant_temperature_k','Helium temperature · K',293,100,500],['regulator_reserve_bar','Regulator reserve · bar',20,5,80],['valve_loss_bar','Valve loss per branch · bar',.5,0,5],['wall_conductivity_w_m_k','Wall conductivity · W/(m K)',200,5,500],['gas_htc_w_m2_k','Assumed gas HTC (W/m2 K)',1000,10,100000],['coolant_htc_w_m2_k','Coolant HTC · W/(m² K)',10000,100,100000],['max_wall_temperature_k','Hot-wall limit · K',650,100,1500]]){const l=document.createElement('label');l.textContent=label;const i=document.createElement('input');Object.assign(i,{name,type:'number',value,min,max,step:'any',required:true});l.append(i);advancedGrid.append(l);}advanced.append(advancedGrid);$('#fields').append(advanced);

const mission=document.createElement('details');mission.className='advanced';const missionSummary=document.createElement('summary');missionSummary.textContent='Vehicle mission · OpenRocket-inspired flight screen';mission.append(missionSummary);const missionGrid=document.createElement('div');missionGrid.className='advanced-grid';for(const [name,label,value,min,max] of [['vehicle_dry_mass_kg','Dry vehicle, excluding payload · kg',25,1,100000],['vehicle_drag_coefficient','Assumed drag coefficient',.5,0,3],['vehicle_diameter_m','Vehicle diameter · m',.15,.02,10],['launch_altitude_m','Launch altitude · m',0,0,100000],['target_apogee_m','Target apogee · m (0 = none)',0,0,1000000]]){const l=document.createElement('label');l.textContent=label;const i=document.createElement('input');Object.assign(i,{name,type:'number',value,min,max,step:'any',required:true});l.append(i);missionGrid.append(l);}mission.append(missionGrid);$('#fields').append(mission);

const executionNote=document.createElement('p');executionNote.id='library-execution';$('#pipeline').after(executionNote);

missionSummary.textContent='Mission and propulsion architecture';

mission.open=true;

missionGrid.prepend(vehicleLabel,familyLabel);

for(const [name,label,value,min,max] of [

 ['payload_mass_kg','Payload · kg',1000,0,1000000],

 ['orbit_altitude_m','Target orbit altitude · m',200000,80000,2000000],

 ['transition_mach','Requested handover Mach',4,1,15],

 ['transition_altitude_m','Requested handover altitude · m',25000,1000,32000],

 ['inlet_capture_area_m2','Assumed inlet area · m²',.08,.01,1000],

 ['inlet_aspect_ratio','Inlet width / height',3,1,10],

 ['inlet_length_m','Reference diffuser length · m',.6,.5,20],

 ['inlet_wall_mm','Reference duct wall · mm',10,1,50]

]){const l=node('label',label),input=document.createElement('input');Object.assign(input,{name,type:'number',value,min,max,step:'any',required:true});l.append(input);missionGrid.append(l);}

const inletSectionLabel=node('label','Inlet reference section'),inletSection=document.createElement('select');inletSection.name='inlet_section';inletSection.append(new Option('Elliptical · smooth section','elliptical'),new Option('Rectangular · planar section','rectangular'));inletSectionLabel.append(inletSection);missionGrid.append(inletSectionLabel);

for(const [name,label,value,min,max] of [['mixer_length_dh','Mixer length / diameter proxy',2,1,5],['combustor_length_dh','Combustor length / diameter proxy',2.5,1,6],['combined_throat_ratio','Common nozzle throat / inlet area',.68,.55,.85],['combined_exit_ratio','Combined nozzle exit / reference area',2,1.2,4],['airpath_pressure_recovery','Assumed mixed pressure recovery',.8,.5,1]]){const l=node('label',label),i=document.createElement('input');Object.assign(i,{name,type:'number',value,min,max,step:'any',required:true});l.append(i);missionGrid.append(l);}

for(const [name,label,options] of [['frame_topology','Frame topology',[['optimized','Optimized load-path frame'],['braced','Braced rings'],['rails','Rings and rails']]],['frame_sectors','Frame sectors',[[8,'8'],[6,'6'],[12,'12']]]]){const l=node('label',label),i=document.createElement('select');i.name=name;for(const [v,t] of options)i.append(new Option(t,v));l.append(i);missionGrid.append(l);}

const frameVolumeLabel=node('label','Optimized frame material fraction'),frameVolume=document.createElement('input');Object.assign(frameVolume,{name:'frame_volume_fraction',type:'number',value:.65,min:.35,max:1,step:.05,required:true});frameVolumeLabel.append(frameVolume);missionGrid.append(frameVolumeLabel);



$('#fields').prepend(mission);

const coreSettings=node('details','');coreSettings.className='advanced';coreSettings.append(node('summary','Rocket core and geometry settings'));

const coreGrid=node('div','');coreGrid.className='advanced-grid';

for(const child of [...$('#fields').children])if(child!==mission)coreGrid.append(child);

coreSettings.append(coreGrid);$('#fields').append(coreSettings);

const layoutLabel=node('label','Tank placement');const layoutInput=document.createElement('select');layoutInput.name='tank_layout';layoutInput.append(new Option('Staggered · translated fuel tank','staggered'),new Option('Paired · common tank top plane','paired'));layoutLabel.append(layoutInput);coreGrid.prepend(layoutLabel);

const clearanceLabel=node('label','Tank radial clearance input · mm'),clearanceInput=document.createElement('input');Object.assign(clearanceInput,{name:'tank_clearance_mm',type:'number',value:22,min:10,max:50,step:'any',required:true});clearanceLabel.append(clearanceInput);coreGrid.prepend(clearanceLabel);

const meshSettings=node('details','');meshSettings.className='advanced';meshSettings.append(node('summary','Mesh generation quality controls'));const meshGrid=node('div','');meshGrid.className='advanced-grid';

for(const [name,label,value,min,max] of [['mesh_surface_edge_mm','Duct surface target edge · mm',12,4,40],['mesh_chord_tolerance_mm','Duct chord tolerance · mm',.5,.1,2],['mesh_voxel_mm','Native core voxel pitch · mm',.75,.5,2]]){const l=node('label',label),input=document.createElement('input');Object.assign(input,{name,type:'number',value,min,max,step:'any',required:true});l.append(input);meshGrid.append(l);}meshSettings.append(meshGrid,node('p','These controls drive generated surfaces and the native export. Finer settings increase mesh size and build time. Surface quality does not certify a volume simulation mesh.'));coreGrid.prepend(meshSettings);

const previewButton=node('button','Recalculate mission budget');previewButton.type='button';previewButton.id='preview-mission';mission.append(previewButton);

const solverLabel=node('label','Mesh verification'),solverInput=document.createElement('select');solverInput.name='mesh_run_solvers';solverInput.append(new Option('Run adaptive CFD + frame FEA','1'),new Option('Generate volume and solver decks only','0'));solverLabel.append(solverInput);meshGrid.append(solverLabel);

const massSettings=node('details','');massSettings.className='advanced';massSettings.append(node('summary','Vehicle material mass and sizing'));

const massGrid=node('div','');massGrid.className='advanced-grid';

const massModeLabel=node('label','Vehicle mass source'),massMode=document.createElement('select');massMode.name='vehicle_mass_mode';massMode.append(new Option('Specified dry mass · audit against geometry','specified'),new Option('Component estimate → mission mass and size','component_estimate'));massModeLabel.append(massMode);massGrid.append(massModeLabel);

for(const [name,label,value,min,max] of [['core_material_density_kg_m3','Core assumed density · kg/m³',8900,100,22000],['tank_material_density_kg_m3','Tank assumed density · kg/m³',2700,100,22000],['assembly_material_density_kg_m3','Duct/frame assumed density · kg/m³',2700,100,22000],['vehicle_unmodeled_dry_mass_kg','Unmodeled equipment allowance · kg',100,0,100000],['vehicle_mass_margin_fraction','Dry mass contingency fraction',.2,0,1],['mission_delta_v_allowance_m_s','Assumed delta-v allowance · m/s',0,0,10000]]){const labelNode=node('label',label),input=document.createElement('input');Object.assign(input,{name,type:'number',value,min,max,step:'any',required:true});labelNode.append(input);massGrid.append(labelNode);}massSettings.append(massGrid,node('p','Densities, equipment allowance and contingency are assumptions. Component mode uses the assembly envelope as a conservative diameter proxy; it does not solve vehicle aerodynamics.'));mission.append(massSettings);

const resourcesSettings=node('details','');resourcesSettings.className='advanced';resourcesSettings.append(node('summary','Orbital power and thermal assumptions'));const resourcesGrid=node('div','');resourcesGrid.className='advanced-grid';

for(const [name,label,value,min,max] of [['orbital_electrical_load_w','Assumed orbital electrical load · W',1000,0,1000000],['solar_array_efficiency','Solar cell efficiency',.28,.01,.5],['solar_eol_factor','Solar end-of-life derating',.8,.1,1],['battery_specific_energy_wh_kg','Assumed battery specific energy · Wh/kg',150,10,500],['battery_depth_of_discharge','Allowed battery depth of discharge',.7,.1,.9],['power_margin_fraction','Power margin fraction',.2,0,1],['radiator_temperature_k','Radiator operating temperature · K',320,200,600],['radiator_sink_temperature_k','Effective radiative sink · K',250,3,500],['radiator_emissivity','Radiator emissivity',.85,.05,1]]){const l=node('label',label),i=document.createElement('input');Object.assign(i,{name,type:'number',value,min,max,step:'any',required:true});l.append(i);resourcesGrid.append(l);}resourcesSettings.append(resourcesGrid);mission.append(resourcesSettings);

const missionPanel=node('section','');missionPanel.className='mission-panel';missionPanel.id='mission-panel';$('#metrics').after(missionPanel);const anatomy=$('#components').parentElement;anatomy.classList.add('anatomy-panel');

const stageFlow=node('div','');stageFlow.className='stage-flow';$('.viewport').before(stageFlow);

const comparisonPanel=node('section','');comparisonPanel.className='change-panel';comparisonPanel.id='comparison-panel';stageFlow.after(comparisonPanel);

const draftBanner=node('div','');draftBanner.id='mesh-draft-banner';draftBanner.hidden=true;$('.viewport').append(draftBanner);

const topologyPanel=node('section','');topologyPanel.className='mission-panel';topologyPanel.id='topology-panel';anatomy.after(topologyPanel);

const contractPanel=node('section','');contractPanel.className='mission-panel';contractPanel.id='contract-panel';topologyPanel.after(contractPanel);

const volumePanel=node('section','');volumePanel.className='mission-panel';volumePanel.id='volume-mesh-panel';$('.geometry-workspace').after(volumePanel);

function renderVolumeStudy(study,id){

 volumePanel.replaceChildren(node('h3','Simulation passages · not printable hardware'),node('p','These cells fill the empty gas passages for flow calculations. Print the engine assembly hardware, not these fluid regions. Print readiness requires process-specific wall, clearance, support and trapped-powder checks.'));

 $('#geometry-view').querySelector('[value="hybrid"]').disabled=!study?.files?.['scene.json'];

 $('#geometry-view').querySelector('[value="airpath"]').disabled=!study?.files?.['airpath-scene.json'];

 if(!study?.selected_mesh){volumePanel.append(node('p',study?.reason||'This older run has no solver volume. Generate a new study with the Gmsh backend.'));return;}

 const m=study.selected_mesh;volumePanel.append(node('p',`${m.cells.toLocaleString()} volume cells · ${m.cell_types['6'].toLocaleString()} prisms + ${m.cell_types['5'].toLocaleString()} hexahedra · ${m.nodes.toLocaleString()} nodes`),node('p',`Minimum scaled Jacobian ${m.scaled_jacobian.minimum.toFixed(3)} · ${m.inverted_cells} inverted cells · ${m.wall_layers} wall layers · axial growth ${m.max_axial_growth.toFixed(3)}`));

 const view=node('button','Inspect actual hybrid cells');view.type='button';view.onclick=()=>showHybridMesh().catch(e=>status(e.message,true));volumePanel.append(view);

 if(study.airpath_mesh){const full=study.airpath_mesh;volumePanel.append(node('h4','Five-stage connected airpath'),

   node('p',`${full.cells.toLocaleString()} volume cells · minimum scaled Jacobian ${full.scaled_jacobian.minimum.toFixed(3)} · ${full.inverted_cells} inverted cells · four shared stage interfaces.`));

   if(study.airpath_cfd)volumePanel.append(node('p',`Full airpath cold-flow CFD: checkMesh ${study.airpath_cfd.checkMesh}, ${study.airpath_cfd.converged?'converged':'not converged'}, Δp ${study.airpath_cfd.pressure_drop_pa.toPrecision(5)} Pa, relative mass imbalance ${study.airpath_cfd.relative_mass_imbalance.toExponential(2)}.`));

   const inspect=node('button','Inspect full airpath cells');inspect.type='button';inspect.onclick=()=>showHybridMesh('airpath').catch(e=>status(e.message,true));volumePanel.append(inspect);

   volumePanel.append(node('p',full.scope));

 }

 if(study.airpath_error)volumePanel.append(node('p','Full airpath study: '+study.airpath_error));

 const a=study.adaptation;if(a)volumePanel.append(node('p',`Adaptive pass: ${a.coarse_cells.toLocaleString()} → ${a.adaptive_cells.toLocaleString()} cells, driven by solved velocity gradients. Pressure-drop change ${(100*a.relative_pressure_drop_change).toFixed(2)}%. ${a.converged?'Axial two-mesh comparison meets the 5% criterion.':'Mesh convergence has not been established.'}`));

 for(const [label,cfd] of [['Coarse CFD',study.coarse_cfd],['Adaptive CFD',study.adaptive_cfd]])if(cfd)volumePanel.append(node('p',`${label}: checkMesh ${cfd.checkMesh}, ${cfd.converged?'converged':'not converged'}, Δp ${cfd.pressure_drop_pa.toPrecision(5)} Pa, relative mass imbalance ${cfd.relative_mass_imbalance.toExponential(2)}.`));

 if(study.cfd_error)volumePanel.append(node('p','CFD failure: '+study.cfd_error));

 const f=study.fea;if(f?.status==='computed')volumePanel.append(node('p',`CalculiX: ${f.elements} selected frame members · compliance ${f.compliance_n_mm.toFixed(4)} N·mm · optimizer difference ${(100*f.relative_compliance_difference).toPrecision(3)}% · ${f.optimizer_cross_check_passed?'cross-check passed':'cross-check failed'}.`));else if(f)volumePanel.append(node('p','Frame FEA: '+f.status+(f.error?' · '+f.error:'')));

 volumePanel.append(node('p',study.ansys_status||''),node('p',study.scope),node('p',m.y_plus_status));

 for(const [label,path,ext] of [['Download solver volume · Gmsh','volume-mesh','msh'],['Download mesh, solver cases and results','mesh-study-download','zip']]){const a=node('a',label);a.href=`/api/runs/${id}/${path}`;a.download=`Vega-${id.slice(0,8)}-engineering.${ext}`;volumePanel.append(a,node('br',''));}

 if(study.files?.['airpath.msh']){const link=node('a','Download five-stage airpath · Gmsh');link.href=`/api/runs/${id}/airpath-volume-mesh`;link.download=`Vega-${id.slice(0,8)}-airpath.msh`;volumePanel.append(link);}

}

async function showHybridMesh(domain='hybrid'){

 const full=domain==='airpath',name=full?'airpath-scene.json':'scene.json';

 if(!run?.mesh_study?.files?.[name])throw Error('Generate a new volume mesh first.');

 showWorkspaceView('geometry');const seq=++sequence;worker?.terminate();const scene=await api(`/api/runs/${run.id}/${full?'airpath-analysis-mesh':'analysis-mesh'}`);if(seq!==sequence)return;

 let zmin=Infinity,zmax=-Infinity,radius=0;for(const p of scene.vertices){zmin=Math.min(zmin,p[2]);zmax=Math.max(zmax,p[2]);radius=Math.max(radius,Math.hypot(p[0],p[1]));}

 currentDimensions={length_mm:zmax-zmin,diameter_mm:2*radius};renderer?.clear();renderer?.setMesh(scene,currentDimensions,'hybrid-volume');

 if(renderer){renderer.hiddenGroups=new Set();renderer.hiddenComponents.clear();renderer.isolatedComponent=null;renderer.highlightComponent=null;}

 $('#geometry-view').value=domain;$('#render-style').value='mesh';$('#cutaway').checked=false;$('#isolate-part').checked=false;$('#show-shell').checked=true;$('#show-frame').checked=true;

 $('#show-shell-label').textContent='Wall layers';$('#show-frame-label').textContent='Prism core';

 yaw=.5;tilt=.8;zoom=.95;$('#camera-view').value='iso';stageFlow.hidden=true;

 const summary=full?run.mesh_study.airpath_mesh:run.mesh_study.selected_mesh;

 $('#mesh-source').textContent=`Gmsh ${full?'full airpath':'nozzle'} solver volume · ${summary.cells.toLocaleString()} cells · ${summary.adaptation} · source ${run.mesh_study.input_sha256.slice(0,12)}`;

 $('#components').replaceChildren();for(const b of scene.bodies){const row=node('button',b.name);row.className='component-select';row.onclick=()=>{if(renderer){renderer.isolatedComponent=$('#isolate-part').checked?b.component_id:null;renderer.highlightComponent=b.component_id;}$('#detail').textContent=b.name+' · actual volume-cell boundary faces.';draw();};$('#components').append(row);}

 $('#detail').textContent=summary.scope;$('.geometry-workspace .section-title h2').textContent=full?'Five-stage airpath volume':'Common-nozzle hybrid volume';updateViewCaption();draw();

}

const modelPanel=$('#computational-model-panel');

$('.title').after($('#active-run'));$('#active-run').after(modelPanel);modelPanel.after(stageFlow);

const activeRun=$('#active-run');

function renderComputationalModel(model){

 modelPanel.replaceChildren();

 const heading=node('div','');heading.className='cem-heading';const title=node('div','');title.append(node('div','REQUIREMENTS → PHYSICS → COMPONENTS → GEOMETRY'),node('h3','Computational engineering model'));heading.append(title,node('span','RUN TRACE'));heading.lastChild.className='cem-live';modelPanel.append(heading);

 if(!model){modelPanel.append(node('p','Generate a study to create its coupled equation-to-geometry model record.'));return;}

 const stages=model.stages||[],checks=Object.values(model.verification?.checks||{}).flat();

 const passed=checks.filter(check=>check.pass).length,total=checks.length;

 const summary=node('p',`${model.model_class} · ${stages.length} linked stages · ${passed}/${total} internal checks pass · validation ${model.validation?.status?.replaceAll('_',' ')||'not recorded'}`);

 summary.className='mission-status '+(model.validation?.status==='awaiting_measured_data'?'unknown':'pass');modelPanel.append(summary);

 modelPanel.append(node('p',`${model.source_mode||`Model ${model.model_sha256?.slice(0,16)||'—'} · requirements ${model.requirements_sha256?.slice(0,16)||'—'}`} · Changing requirements and generating again creates a distinct trace.`));

 const chain=node('div','');chain.className='cem-chain';

 for(const stage of stages){

  const card=node('details','');card.className='cem-stage';

  const title=node('summary',`${stage.title} · ${stage.status.replaceAll('_',' ')}`);title.dataset.status=stage.status;card.append(title);

  if(stage.depends_on?.length)card.append(node('p',`Depends on: ${stage.depends_on.join(' → ')}`));

  for(const [label,value] of [['Inputs',stage.inputs],['Outputs',stage.outputs]]){const row=node('p','');row.className='cem-data';row.append(node('strong',label+' · '),node('span',JSON.stringify(value)));card.append(row);}

  const equations=node('ul','');for(const eq of stage.equations||[])equations.append(node('li',eq));if(equations.childElementCount)card.append(node('small','Equations / method'),equations);

  const assumptions=node('ul','');for(const item of stage.assumptions||[])assumptions.append(node('li',item));if(assumptions.childElementCount)card.append(node('small','Model scope'),assumptions);

  for(const check of stage.checks||[]){const row=node('p',`${check.pass?'PASS':'FAIL'} · ${check.name}`);row.className='cem-check '+(check.pass?'pass':'fail');card.append(row);}

   for(const solved of [stage.solver,stage.operating_solver].filter(Boolean)){

    card.append(node('p',`Executed ${solved.name} · ${solved.solver} · ${solved.evaluations} evaluations · rank ${solved.jacobian_rank} · tolerance ${solved.tolerance}`));

    if(solved.converged_chemistry){const gas=solved.converged_chemistry;card.append(node('p',`Coupled chamber chemistry · ${solved.chemistry_evaluations} evaluations · ${Number(gas.chamber_temperature_k).toFixed(1)} K · O/F ${Number(gas.mixture_ratio).toFixed(4)} · gamma ${Number(gas.gamma).toFixed(5)}`));}

    const values=node('ul','');for(const [name,item] of Object.entries(solved.variables||{}))values.append(node('li',`${name}: ${Number(item.value).toPrecision(7)} ${item.unit}`));card.append(values);

    const residuals=node('ul','');for(const eq of solved.equations||[])residuals.append(node('li',`${eq.name}: residual ${Number(eq.residual).toExponential(3)} ${eq.unit} · scaled ${Number(eq.scaled_residual).toExponential(3)}`));card.append(residuals);

   }

   chain.append(card);

 }

 modelPanel.append(chain);

 const verification=model.verification||{},validation=model.validation||{};

 const evidence=node('details','');evidence.append(node('summary',`Verification and validation · ${verification.status?.replaceAll('_',' ')||'unknown'} / ${validation.status?.replaceAll('_',' ')||'unknown'}`));

 evidence.append(node('p',verification.numerical_convergence||''),node('p',validation.statement||''));

 if(validation.evidence?.length)for(const item of validation.evidence)evidence.append(node('p',`${item.metric}: predicted ${fmt(item.predicted)} · measured ${fmt(item.measured)} · residual ${fmt(item.residual)} (${fmt(100*item.relative_error)}%)`));

 modelPanel.append(evidence);

 const completion=model.system_completion;

 if(completion){const block=node('details','');block.open=true;block.className='system-completion';block.append(node('summary','Whole spacecraft and propulsion · '+completion.status.replaceAll('_',' ')));if(completion.failed_requirements.length)block.append(node('p','Failed requirements: '+completion.failed_requirements.join(', ').replaceAll('_',' ')));const list=node('ul','');for(const item of completion.obligations)list.append(node('li',item.id.replaceAll('_',' ')+' · '+item.status.replaceAll('_',' ')+' · '+item.required_output));block.append(list);modelPanel.append(block);}

}

function renderContract(contract,run=null){

 contractPanel.replaceChildren(node('h3','One-run system connection'));

 if(!contract){contractPanel.append(node('p','Generate a new study to verify requirements, physics, routed fluids, native components and assembly export as one run.'));return;}

 const checks={...contract.checks};

 if(run?.assembly_artifact){

  const bodies=run.assembly_artifact.bodies||[],sceneBodies=run.candidates[0]?.assembly?.scene?.bodies||[],scene=run.candidates[0]?.assembly?.scene?.triangles||[];

  const ids=new Set();let cursor=0,validRanges=bodies.length>0;

  for(const body of bodies){validRanges=validRanges&&!!body.component_id&&!ids.has(body.component_id)&&Number.isInteger(body.first_triangle)&&Number.isInteger(body.triangle_count)&&body.first_triangle===cursor&&body.triangle_count>0;ids.add(body.component_id);cursor+=body.triangle_count||0;}

  checks.exported_component_triangle_ranges_partition_mesh=validRanges&&cursor===run.assembly_artifact.triangles;

  checks.assembly_body_ranges_match_scene_manifest=sceneBodies.length===run.candidates[0].assembly.components.length&&sceneBodies.every((body,i)=>body.component_id===run.candidates[0].assembly.components[i].id&&body.first_triangle===bodies[i]?.first_triangle&&body.triangle_count===bodies[i]?.triangle_count);

  const core=bodies.filter(body=>body.group==='core');

  checks.native_core_triangle_count_matches_export=core.reduce((sum,body)=>sum+body.triangle_count,0)===run.artifact?.scene_triangles;

  checks.native_core_ranges_follow_assembly_scene=core.every((body,i)=>body.first_triangle===scene.length+core.slice(0,i).reduce((sum,part)=>sum+part.triangle_count,0));

 }

 const count=Object.values(checks).filter(Boolean).length,total=Object.keys(checks).length;

 const result=node('p',`${contract.status.replaceAll('_',' ')} · ${count}/${total} connection checks · ${contract.components.length} exported bodies · ${contract.flow.registered_routes?Object.keys(contract.flow.registered_routes).length:0} registered fluid routes`);

 result.className='mission-status '+(contract.status==='connected_unvalidated'&&count===total?'pass':'fail');contractPanel.append(result);

 contractPanel.append(node('p',contract.scope));

 const flow=node('details','');flow.append(node('summary','Actual flow connections and run identities'));

 for(const [a,b] of contract.flow.edges)flow.append(node('p',`${a} → ${b}`));

 for(const [name,ok] of Object.entries(checks))flow.append(node('p',`${ok?'PASS':'FAIL'} · ${name.replaceAll('_',' ')}`));

 for(const [name,value] of Object.entries(contract.identities))if(value)flow.append(node('p',`${name.replaceAll('_',' ')}: ${value.slice(0,16)}…`));

 contractPanel.append(flow);

 const unresolved=node('details','');unresolved.append(node('summary',`${contract.unresolved.length} unresolved physics or validation obligations`));for(const item of contract.unresolved)unresolved.append(node('p',item));contractPanel.append(unresolved);

}

function renderTopology(a,active,wiring){

 topologyPanel.replaceChildren(node('h3','Topology and component interfaces'));

 const download=$('#assembly-download');download.hidden=!run.assembly_artifact;if(!download.hidden){download.href=`/api/runs/${run.id}/assembly-native`;download.download=run.id+'.assembly.stl';}

 if(a?.status!=='concept_assembly'){topologyPanel.append(node('p',a?.reason||'Generate a new RBCC or ejector study to build the connected assembly.'));return;}

 topologyPanel.append(node('p',`${a.topology.flow.connected_components} flow network | ${a.topology.frame.connected_components} frame network | ${a.topology.frame.cycle_rank} independent frame cycles | ${a.interfaces.length} shared stage interfaces`));

 if(wiring){const gate=node('p',`NASA-informed stage gate: ${wiring.status.replaceAll('_',' ')} · ${Object.values(wiring.checks||{}).filter(Boolean).length}/${Object.keys(wiring.checks||{}).length} checks`);gate.className='mission-status '+(wiring.status==='passed'?'pass':'unknown');topologyPanel.append(gate);}

 if(a.design_state){const d=a.design_state,g=d.geometry_fields,r=d.ratios;topologyPanel.append(node('h3','Shared CEM design state'),node('p',`Ideal air/rocket mass ratio ${fmt(r.air_to_rocket_mass)} · air fraction ${fmt(100*r.air_mass_fraction)}% · thermal index ${fmt(r.thermal_index)} · ${g.lobe_count} lobes · peak amplitude ${fmt(100*g.peak_lobe_amplitude)}% · twist ${fmt(g.total_twist_rad*180/Math.PI)}°.`));if(d.ideal_mixer){const m=d.ideal_mixer;topologyPanel.append(node('h3','Conditional ideal mixer balance'),node('p',`Air ${fmt(m.mass_flow_kg_s.air_ideal_capture)} + rocket ${fmt(m.mass_flow_kg_s.rocket)} = mixed ${fmt(m.mass_flow_kg_s.mixed)} kg/s · ideal mixed total temperature ${fmt(m.stagnation_temperature_k.mixed_ideal)} K · energy residual ${fmt(m.energy_residual_w)} W.`),node('p',`Cold-air pressure bound ${fmt(m.air_total_pressure_after_normal_shock_pa/1000)} kPa · mixer throat requires at least ${fmt(m.required_ideal_stagnation_pressure_at_mixer_throat_pa/1000)} kPa in the ideal gas screen · reference headroom ${fmt(100*m.reference_pressure_headroom_fraction)}% · generated throat ${fmt(d.area_m2.mixer_throat)} m².`),node('p',m.limits));}for(const trace of d.causality)topologyPanel.append(node('p','↳ '+trace));}

 if(a.design_state?.conditional_airpath){const f=a.design_state.conditional_airpath;topologyPanel.append(node('h3','Conditional fluid-dynamics stations'),node('p',`Assumed mixed total-pressure recovery ${fmt(100*f.assumed_mixed_total_pressure_recovery)}% · mixed total pressure ${fmt(f.assumed_mixed_total_pressure_pa/1000)} kPa · minimum choking margin ${fmt(100*f.minimum_choking_margin_fraction)}%.`));const table=node('table','');table.className='evidence-table';const head=node('tr','');for(const label of ['Section','Mach','Static p kPa','Static T K','Speed m/s','q kPa','Choke margin'])head.append(node('th',label));table.append(head);for(const s of f.stations){const row=node('tr','');for(const value of [s.name.replaceAll('_',' '),fmt(s.mach),fmt(s.static_pressure_pa/1000),fmt(s.static_temperature_k),fmt(s.velocity_m_s),fmt(s.dynamic_pressure_pa/1000),fmt(100*s.choking_margin_fraction)+'%'])row.append(node('td',value));table.append(row);}topologyPanel.append(table,node('p',f.limits));}

 if(a.frame_optimization){const o=a.frame_optimization;topologyPanel.append(node('h3','Ground-structure frame optimization'),node('p',`${o.method} · ${o.selected_member_count}/${o.candidate_member_count} members selected · material fraction ${fmt(100*o.volume_fraction_actual)}% · axial-truss compliance improvement ${fmt(100*o.compliance_improvement_fraction)}% versus a uniform frame at the same material volume · ${o.iteration_count} iterations.`),node('p',`Representative loads: ${fmt(o.load_cases_n.axial_total)} N axial, ${fmt(o.load_cases_n.transverse_total)} N transverse. Member radius ${fmt(o.minimum_radius_mm)}–${fmt(Math.max(...Object.values(o.edge_radii_mm)))} mm.`),node('p',o.limits));}

 if(a.mesh_policy){topologyPanel.append(node('h3','Live surface mesh quality'),node('p',`Generated with ${a.mesh_policy.backend||'archived parametric mesher'}, target edge ${fmt(a.mesh_policy.surface_edge_mm)} mm and chord tolerance ${fmt(a.mesh_policy.chord_tolerance_mm)} mm.`));const table=node('table','');table.className='evidence-table';const head=node('tr','');for(const text of ['Body','Triangles','Mean 2r/R','5th percentile','Below 0.2'])head.append(node('th',text));table.append(head);for(const [id,q] of Object.entries(a.mesh_quality||{})){const row=node('tr','');for(const value of [id,q.triangles,Number(q.mean).toFixed(3),Number(q.p05).toFixed(3),q.below_0_2])row.append(node('td',value));table.append(row);}topologyPanel.append(table,node('p','Slender bars and sharp/tiny features can retain poor isotropic surface metrics. This report does not certify a simulation volume mesh.'));}

 topologyPanel.append(node('p','Air inlet + embedded rocket core -> mixer -> isolator -> air combustor envelope -> common nozzle. Core fuel, cooling and oxidizer paths retain their generated geometry. Air-mode fuel staging and hot-flow closure remain unresolved.'));

 for(const [name,ok] of Object.entries(a.checks)){const chip=node('span',(ok?'PASS: ':'FAIL: ')+name.replaceAll('_',' '));chip.className='check '+(ok?'pass':'fail');topologyPanel.append(chip);}

 const details=node('details','');details.append(node('summary','Surface topology, assumptions and sources'));

 for(const [id,t] of Object.entries(a.topology.surfaces))details.append(node('p',`${id}: Euler characteristic ${t.euler_characteristic}; genus sum ${t.total_genus}; ${t.surface_components} closed surfaces; ${t.boundary_edges} boundary edges.`));

 details.append(node('p','Closed component surfaces are not a fused manufacturing solid. Graph cycles do not imply structural optimization.'));

 for(const text of [...a.assumptions,...a.unknown_checks.map(t=>'Unresolved: '+t)])details.append(node('p',text));

 for(const url of a.sources){const link=node('a',url);link.href=url;link.target='_blank';link.rel='noreferrer';details.append(link,node('br',''));}topologyPanel.append(details);

 if(!active)topologyPanel.append(node('p','Select Connected assembly above to inspect the full layout.'));

}



function briefFromForm(){const strings=new Set(['material_id','print_process','test_purpose','architecture','jacket_pattern','propellant_model','vehicle_architecture','propulsion_family','nozzle_contour','tank_layout','inlet_section','frame_topology','thermal_model','vehicle_mass_mode']);return Object.fromEntries([...new FormData($('#requirements'))].map(([k,v])=>[k,strings.has(k)?v:Number(v)]));}

function renderMission(m,label='Saved study'){

 missionPanel.replaceChildren(node('div','MISSION / '+label));missionPanel.firstChild.className='eyebrow';

 if(!m?.budget){missionPanel.append(node('h2','Mission budget not recorded'),node('p','This older study contains engine geometry only. Recalculate the budget or generate a new study.'));return;}

 missionPanel.append(node('h2',m.family_name),node('p','Planned vehicle architecture: '+m.architecture.replaceAll('_',' ')));

 const state=node('p',m.status==='failed'?'Mission budget fails the simplified speed comparison.':'Budget comparison passes; mission feasibility remains incomplete.');state.className='mission-status '+(m.status==='failed'?'fail':'unknown');missionPanel.append(state);

 const metrics=node('div','');metrics.className='mission-metrics';

 for(const [title,value] of [

  ['Rocket propellant',fmt(m.vehicle.rocket_propellant_mass_kg)+' kg'],

  ['Dry mass + payload',fmt(m.vehicle.budget_final_mass_kg)+' kg'],

  ['Ideal rocket delta-v',fmt(m.budget.available_ideal_delta_v_m_s)+' m/s'],

  ['Remaining speed gap',fmt(m.budget.remaining_speed_gap_m_s)+' m/s'],

  ['Velocity margin',fmt(m.budget.velocity_margin_m_s)+' m/s']

 ]){const item=node('div','');item.append(node('small',title),node('strong',value));metrics.append(item);}missionPanel.append(metrics);

 missionPanel.append(node('p',m.budget.scope));

 if(m.orbital_resources){const res=m.orbital_resources,box=node('details','');box.open=true;box.append(node('summary','Orbital power, eclipse battery and heat rejection'));box.append(node('p',`Circular orbit ${fmt(res.orbit.period_s/60)} min · central eclipse ${fmt(res.orbit.eclipse_s/60)} min. Design load ${fmt(res.power.design_load_w)} W → ${fmt(res.power.array_area_m2)} m² solar array and ${fmt(res.power.battery_nominal_energy_wh)} Wh nominal battery. Electrical heat ${fmt(res.thermal.electrical_heat_rejection_w)} W → ${fmt(res.thermal.radiator_area_m2)} m² emitting radiator at ${fmt(res.thermal.radiator_temperature_k)} K.`));box.append(node('p',`Orbital energy residual ${Number(res.power.orbital_energy_residual_wh).toExponential(2)} Wh · thermal residual ${Number(res.thermal.heat_balance_residual_w).toExponential(2)} W. These verify the declared equations, not hardware performance.`),node('p',res.scope));missionPanel.append(box);}

 if(m.mass_budget){const mass=m.mass_budget,box=node('details','');box.open=true;box.append(node('summary','Geometry-derived vehicle mass and inverse sizing'));box.append(node('p',`Modeled component material ${fmt(mass.modeled_material_mass_kg)} kg + equipment allowance ${fmt(mass.unmodeled_equipment_allowance_kg)} kg + ${fmt(100*mass.mass_margin_fraction)}% contingency = ${fmt(mass.estimated_dry_mass_kg)} kg dry estimate. Mission uses ${fmt(mass.selected_dry_mass_kg)} kg and a ${fmt(mass.selected_reference_diameter_m)} m diameter proxy.`));for(const [key,passed] of Object.entries(mass.checks))box.append(node('p',(passed?'PASS · ':'FAIL · ')+key.replaceAll('_',' ')));const inv=mass.inverse_sizing;box.append(node('p',inv.propellant_mass_kg==null?'Tank-growth inverse sizing: no finite single-stage solution under the frozen tank/material assumptions.':`Conditional inverse: ${fmt(inv.propellant_mass_kg)} kg propellant · ${fmt(inv.burn_duration_s)} s burn · ${inv.within_burn_duration_domain?'within':'outside'} current burn-duration model domain.`));box.append(node('p',inv.scope));const rows=node('ul','');for(const item of mass.components)rows.append(node('li',item.id.replaceAll('_',' ')+' · '+fmt(item.mass_kg)+' kg'+(item.assumed_density_kg_m3==null?' · derived subsystem estimate':' · assumed '+fmt(item.assumed_density_kg_m3)+' kg/m³')));box.append(rows,node('p',mass.scope));missionPanel.append(box);}

 if(m.transition){missionPanel.append(node('p',`Requested handover: Mach ${fmt(m.transition.mach)} at ${fmt(m.transition.altitude_m)} m. Ideal air capture ${fmt(m.transition.ideal_capture_mass_flow_kg_s)} kg/s; dynamic pressure ${fmt(m.transition.dynamic_pressure_pa/1000)} kPa. Airbreathing net thrust: not modeled.`));}



 if(m.rbcc_reference){const data=m.rbcc_reference;const table=node('table','');table.className='evidence-table';const caption=node('caption','RBCC reference cases · evaluated at this brief’s altitude');table.append(caption);const head=node('thead',''),hr=node('tr','');for(const label of ['Case','Mode','q (kPa)','Ideal captured air (kg/s)','Shock pt recovery','Cold inlet'])hr.append(node('th',label));head.append(hr);table.append(head);const body=node('tbody','');for(const c of data.source_cases){const row=node('tr','');for(const value of [`${c.id} · M${fmt(c.mach)}`,c.mode,fmt(c.dynamic_pressure_pa/1000),fmt(c.ideal_capture_mass_flow_kg_s),fmt(c.ideal_normal_shock_total_pressure_recovery),c.cold_normal_shock_inlet_supported?'within screen':'outside screen'])row.append(node('td',value));body.append(row);}table.append(body);missionPanel.append(table,node('p','NASA cycle-code comparison Mach points provide operating-condition anchors. These are recalculated free-stream estimates at the altitude above, not recovered test measurements; Vega does not infer airbreathing thrust from them.'));

  for(const [label,url] of [['NASA RBCC cycle-code comparison',data.case_source],['NASA A5 integrated engine architecture',data.architecture_source],['NASA three-stream ejector model',data.mixing_source],['NASA direct-connect test instrumentation',data.validation_source]]){const source=node('a',label);source.href=url;source.target='_blank';source.rel='noreferrer';missionPanel.append(source,node('br',''));}}



 const modes=node('ol','');modes.className='mode-schedule';for(const mode of m.mode_schedule)modes.append(node('li',mode.mode+' · planned'));missionPanel.append(modes);

 const graph=node('div','');graph.className='system-map';const detail=node('p','Select a subsystem to inspect its model status and dependencies.');detail.className='system-detail';

 for(const system of m.systems){const button=node('button','');button.type='button';button.append(node('strong',system.name),node('small',system.status.replaceAll('_',' ')));button.onclick=()=>{for(const b of graph.children)b.setAttribute('aria-pressed',String(b===button));detail.textContent=system.detail+(system.depends_on.length?' Depends on: '+system.depends_on.map(id=>m.systems.find(s=>s.id===id)?.name||id).join(', ')+'.':'');};button.setAttribute('aria-pressed','false');graph.append(button);}missionPanel.append(graph,detail);

 const gates=node('div','');for(const [name,ok] of Object.entries(m.checks)){const check=node('span',(ok===null?'?':ok?'✓':'×')+' '+name.replaceAll('_',' '));check.className='check '+(ok===null?'unknown':ok?'pass':'fail');gates.append(check);}missionPanel.append(gates);

 const evidence=node('details','');evidence.append(node('summary','Equations, assumptions and sources'));

 for(const text of [...m.equations,...m.warnings])evidence.append(node('p',text));

 for(const url of m.sources){const a=node('a',new URL(url).hostname+' / '+url.split('/').filter(Boolean).at(-1));a.href=url;a.target='_blank';a.rel='noreferrer';evidence.append(a,node('br',''));}missionPanel.append(evidence);

}

function syncFamily(){for(const name of ['transition_mach','transition_altitude_m','inlet_capture_area_m2','inlet_aspect_ratio','inlet_length_m','inlet_wall_mm','inlet_section'])$('#requirements').elements[name].disabled=family.value==='rocket_only';}

family.addEventListener('change',syncFamily);syncFamily();

const missionOnlyInputs=new Set(['vehicle_architecture','vehicle_dry_mass_kg','vehicle_drag_coefficient','vehicle_diameter_m','launch_altitude_m','target_apogee_m','payload_mass_kg','orbit_altitude_m','vehicle_mass_mode','core_material_density_kg_m3','tank_material_density_kg_m3','assembly_material_density_kg_m3','vehicle_unmodeled_dry_mass_kg','vehicle_mass_margin_fraction','mission_delta_v_allowance_m_s','orbital_electrical_load_w','solar_array_efficiency','solar_eol_factor','battery_specific_energy_wh_kg','battery_depth_of_discharge','power_margin_fraction','radiator_temperature_k','radiator_sink_temperature_k','radiator_emissivity']);

function markDraft(){

 if(!run)return;

 const current=briefFromForm(),changed=Object.keys(current).filter(k=>current[k]!==run.requirements[k]);

 activeRun.classList.toggle('draft',!!changed.length);modelPanel.classList.toggle('draft',!!changed.length);

 draftBanner.hidden=!changed.length;

 if(!changed.length){missionPanel.classList.remove('draft');return;}

 const geometry=changed.some(k=>!missionOnlyInputs.has(k));

 draftBanner.textContent=`UNSAVED INPUTS · Showing mesh from run ${run.id.slice(0,8)}. ${geometry?'Solve preview or generate to update geometry.':'These mission inputs do not change engine geometry.'}`;

 missionPanel.classList.add('draft');

 status(geometry?'Requirements changed. Generate a new saved mesh.':'Mission-only inputs changed. Recalculate the budget; engine mesh stays the same.');

}

$('#requirements').addEventListener('input',markDraft);

previewButton.onclick=async()=>{setInputsVisible(false);showWorkspaceView('engineering');previewButton.disabled=true;try{status('Recalculating mission budget…');const m=await api('/api/mission/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(briefFromForm())});renderMission(m,'Unsaved inputs · mesh still belongs to saved study');missionPanel.classList.remove('draft');status('Mission budget updated. Generate to save these requirements with a native mesh.');}catch(e){status(e.message,true);}finally{previewButton.disabled=false;}};

let currentDimensions;

let renderer,run,yaw=.5,tilt=.8,zoom=.95,drag,frame=0,sequence=0,worker,knownRuns=[],comparisonBaselineId=null;

try{renderer=new window.VegaRenderer(canvas);}catch(e){status(e.message,true);}

function status(t,error=false){$('#status').textContent=t;$('#status').classList.toggle('error',error);}

function drawingAnnotation(){

 const triad=$('#axis-triad'),ns='http://www.w3.org/2000/svg';triad.replaceChildren();

 const cy=Math.cos(yaw),sy=Math.sin(yaw),ct=Math.cos(tilt),st=Math.sin(tilt);

 for(const [name,x,y,color] of [['Z axial',cy,-st*sy,'#b35a43'],['X',-sy,-st*cy,'#378569'],['Y',0,ct,'#426f9d']]){

  const line=document.createElementNS(ns,'line');for(const [k,v] of Object.entries({x1:48,y1:48,x2:48+32*x,y2:48+32*y,stroke:color,'stroke-width':2}))line.setAttribute(k,v);triad.append(line);

  const text=document.createElementNS(ns,'text');text.setAttribute('x',48+40*x);text.setAttribute('y',48+40*y);text.setAttribute('fill',color);text.setAttribute('font-size',9);text.setAttribute('text-anchor','middle');text.textContent=name;triad.append(text);

 }

 const stats=JSON.parse(canvas.dataset.renderStats||'{}');

 if(currentDimensions&&stats.fitScale){const mmPerPixel=currentDimensions.length_mm/stats.fitScale;const raw=80*mmPerPixel,power=10**Math.floor(Math.log10(raw)),bar=[1,2,5,10].map(v=>v*power).find(v=>v>=raw);const label=$('#drawing-scale');label.textContent=fmt(bar)+' mm';label.style.width=(bar/mmPerPixel)+'px';}

}

function draw(){if(frame)return;frame=requestAnimationFrame(()=>{frame=0;if(renderer){const box=canvas.getBoundingClientRect();if(!box.width||!box.height)return;renderer.resize(box.width,box.height);renderer.render(yaw,tilt,zoom,{cutaway:$('#cutaway').checked,routes:false,mode:$('#render-style').value});drawingAnnotation();}});}

function updateViewCaption(){const mode=$('#render-style').value;$('#view-caption').textContent={study:'Geometry study shows sampled points from the saved mesh, including surfaces behind the outer walls.',solid:'Solid view shows the saved multi-body assembly with surface occlusion.',mesh:'Actual exported triangle edges. Isolate a component and zoom to inspect its tessellation.',quality:'Measured triangle radius quality: red < 0.2, amber near 0.3, green > 0.7. Surface quality is not a FEM/CFD convergence result.',interior:'Interior view hides the duct walls and support frame to expose core hardware and mixer features.'}[mode];if(mode==='quality'&&canvas.dataset.meshQuality){const q=JSON.parse(canvas.dataset.meshQuality);$('#view-caption').textContent+=` Whole-scene mean ${q.mean.toFixed(3)} · ${q.belowPointTwo} triangles below 0.2.`;}if(renderer?.source==='hybrid-volume')$('#view-caption').textContent='Half-domain cut through actual prism and hex cells. Blue: unstructured core; amber: graded wall layers. Display triangles split quadrilateral faces; cell counts and Jacobians are in the volume report.';if(renderer?.source==='recipe-preview')$('#view-caption').textContent='Recomputed recipe surfaces · native boolean details pending.';$('#cutaway').disabled=!['solid','mesh','quality'].includes(mode);draw();}

new ResizeObserver(draw).observe(canvas);$('#render-style').onchange=updateViewCaption;$('#cutaway').onchange=draw;$('#reset').onclick=()=>{yaw=.5;tilt=.8;zoom=.95;$('#camera-view').value='iso';draw();};

$('#camera-view').onchange=()=>{[yaw,tilt]=({iso:[.5,.8],side:[0,0],top:[0,Math.PI/2],end:[Math.PI/2,0]})[$('#camera-view').value];zoom=.95;draw();};

$('#lock-scale').onchange=()=>{if(!renderer||!currentDimensions)return;const stats=JSON.parse(canvas.dataset.renderStats||'{}');renderer.scaleLockPxPerMm=$('#lock-scale').checked?stats.fitScale/currentDimensions.length_mm/zoom:null;draw();};

$('#expand-view').onclick=()=>{const expanded=$('.geometry-workspace').classList.toggle('expanded');$('#expand-view').textContent=expanded?'Close expanded drawing':'Expand drawing';draw();};

document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('.geometry-workspace').classList.contains('expanded'))$('#expand-view').click();});

$('#search-designs').onchange=()=>{$('#generate').textContent=$('#search-designs').checked?'Explore and compare variants ↗':'Generate exact design ↗';};

$('#preview-geometry').disabled=false;

$('#preview-geometry').onclick=async()=>{

 if(!$('#requirements').reportValidity())return;
 setInputsVisible(false);showWorkspaceView('geometry');

 const requested=briefFromForm(),token=++sequence;worker?.terminate();worker=null;

 $('#preview-geometry').disabled=true;$('#generate').disabled=true;$('#history').disabled=true;

 try{

  status('Solving requirements and rebuilding recipe surfaces…');

  const preview=await api('/api/geometry/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(requested)});

  if(token!==sequence)return;

  renderer?.clear();currentDimensions=preview.dimensions;renderer?.setMesh(preview.scene,currentDimensions,'recipe-preview');

  $('#render-style').value='solid';$('#cutaway').checked=false;$('#show-shell').checked=true;$('#show-frame').checked=true;$('#isolate-part').checked=false;

  $('#mesh-source').textContent='UNSAVED RECIPE PREVIEW · '+preview.geometry_sha256.slice(0,16)+' · '+preview.scope;

  activeRun.replaceChildren(node('strong','UNSAVED GEOMETRY PREVIEW'),node('span',preview.requirements.propulsion_family.toUpperCase()+' · '+fmt(preview.requirements.thrust_n)+' N'));activeRun.classList.add('draft');

  renderComputationalModel(preview.computational_model);renderMission(preview.vehicle_screen,'Unsaved solved preview');

  $('#metrics').hidden=true;$('#restore-saved').hidden=!run;draftBanner.hidden=true;contractPanel.hidden=true;topologyPanel.hidden=true;stageFlow.hidden=true;$('.evidence-section').hidden=true;$('.engineering').hidden=true;

  for(const control of $('#components').querySelectorAll('button,input'))control.disabled=true;

  for(const link of $('.actions').querySelectorAll('a'))link.hidden=true;

  yaw=.5;tilt=.8;zoom=.95;$('#camera-view').value='iso';updateViewCaption();

  status('Preview rebuilt from current inputs. Generate exact design to mesh cooling cuts and export checked native hardware.');

 }catch(error){status(error.message,true);}finally{$('#preview-geometry').disabled=false;$('#generate').disabled=false;$('#history').disabled=false;}

};

$('#restore-saved').onclick=()=>{if(run)openRun(run.id).catch(error=>status(error.message,true));};

canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);};canvas.onpointerup=canvas.onpointercancel=()=>drag=null;

canvas.onpointermove=e=>{if(!drag)return;yaw+=(e.clientX-drag[0])*.008;tilt+=(e.clientY-drag[1])*.008;$('#camera-view').value='custom';drag=[e.clientX,e.clientY];draw();};canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.3,Math.min(4,zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});

async function api(url,options){const r=await fetch(url,{...options,signal:AbortSignal.timeout(120000)}),d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d;}

function node(tag,text){const e=document.createElement(tag);e.textContent=text;return e;}

const fmt=v=>Number(v).toLocaleString(undefined,{maximumFractionDigits:2});

async function history(){const runs=knownRuns=await api('/api/runs');$('#history').replaceChildren(new Option('Select a study',''),...runs.map(r=>new Option(`${(r.propulsion_family||'rocket_only').toUpperCase()} · ${(r.nozzle_contour||'conical').toUpperCase()} / ${(r.jacket_pattern||'unknown').toUpperCase()} · ${fmt(r.thrust_n||0)} N · ${r.channel_variant||'?'} ch · ${r.id.slice(0,6)}`,r.id)));return runs;}

function renderComparison(result){

 comparisonPanel.replaceChildren();

 if(!result){comparisonPanel.append(node('strong','Geometry comparison'),node('p','Generate or select another saved study to compare exact component meshes.'));return;}

 const changed=result.components.filter(c=>c.status!=='unchanged');

 comparisonPanel.append(node('strong',`${result.status==='changed'?'Geometry changed':'Geometry unchanged'} vs run ${result.before_run.slice(0,8)}`),

   node('p',`${changed.length} of ${result.components.length} exported bodies changed. Comparison uses saved STL triangles, not triangle counts or a visual guess.`));

 if(result.dimension_change){const d=result.dimension_change;comparisonPanel.append(node('p',`Assembly length ${fmt(d.length_mm.before_mm)} → ${fmt(d.length_mm.after_mm)} mm (${fmt(d.length_mm.change_percent)}%); envelope diameter ${fmt(d.diameter_mm.before_mm)} → ${fmt(d.diameter_mm.after_mm)} mm (${fmt(d.diameter_mm.change_percent)}%).`));}

 if(result.changed_inputs.length){const inputs=result.changed_inputs.map(v=>`${v.name.replaceAll('_',' ')} (${v.geometry_dependency==='mission_only'?'mission only':'engine/geometry input'})`);comparisonPanel.append(node('p','Changed inputs: '+inputs.join(', ')+'.'));}

 if(changed.length){const list=node('div','');list.className='changed-components';for(const part of changed){const button=node('button',part.name+' · '+part.status);button.type='button';button.onclick=()=>{const current=run.assembly_artifact?.components.find(c=>c.id===part.id);if(!current)return;renderer.isolatedComponent=part.id;renderer.setHighlight(current,currentDimensions);$('#isolate-part').checked=true;$('#render-style').value='solid';$('#cutaway').checked=false;updateViewCaption();$('#detail').textContent=current.role+' Changed in the exported mesh relative to '+result.before_run.slice(0,8)+'.';};list.append(button);}comparisonPanel.append(list);}

 else comparisonPanel.append(node('p',result.changed_inputs.length?'The edited inputs did not alter this generated assembly.':'These studies used equivalent geometry inputs.'));

}

function renderDesignCandidates(study,activeId){
 const panel=$('#design-candidates');panel.replaceChildren();generationOutputs.hidden=!!study;
 if(!study){panel.append(node('p','Generate a candidate study to compare designs from the same requirements.'));return;}
 const counts=node('div','');counts.className='study-metrics';
 for(const [label,value] of [['Evaluated',study.evaluated],['Selected',study.candidates.length],['Distinct core meshes',study.distinct_native_meshes??'—'],['Rejected',study.rejected.length]]){
  const metric=node('div','');metric.className='metric';metric.append(node('small',label),node('strong',String(value)));counts.append(metric);
 }
 panel.append(counts,node('p',study.selection_rule));
 if(Number.isInteger(study.search_seed))panel.append(node('p',`Search seed: ${study.search_seed} · Recorded for reproducibility.`));
 const grid=node('div','');grid.className='candidate-grid';
 for(const candidate of study.candidates){
  const card=node('article','');card.className='candidate-card'+(candidate.run_id===activeId?' active':'');
  card.append(node('h4',candidate.name+(candidate.run_id===activeId?' · selected':'')));
  const p=candidate.parameters;
  card.append(node('p',[p.nozzle_contour,p.inlet_section,p.frame_topology].filter(Boolean).join(' / ')));
  const unresolved=candidate.unresolved_checks||[];
  const result=node('p',`${candidate.failed_checks.length} failed screens · ${unresolved.length} unresolved · ${candidate.mesh_status||candidate.status}`);
  result.className='mission-status '+(candidate.failed_checks.length?'fail':'unknown');card.append(result);
  if(candidate.dimensions_mm)card.append(node('p',`${fmt(candidate.dimensions_mm.length_mm)} × ${fmt(candidate.dimensions_mm.diameter_mm)} mm core envelope`));
  const details=node('details','');details.append(node('summary','Parameters and checks'));
  const list=node('dl','');list.className='parameter-list';
  for(const [key,value] of Object.entries(p))list.append(node('dt',key.replaceAll('_',' ')),node('dd',typeof value==='number'?fmt(value):String(value)));
  details.append(list);
  if(candidate.dimensions_mm)details.append(node('p',`Estimated hot wall: ${fmt(candidate.hot_wall_k)} K · stress utilization: ${fmt(candidate.stress_utilization)}`));
  if(candidate.failed_checks.length)details.append(node('p',candidate.failed_checks.join(', ').replaceAll('_',' ')));
  if(unresolved.length)details.append(node('p','Unresolved: '+unresolved.join(', ').replaceAll('_',' ')));
  if(candidate.error)details.append(node('pre',candidate.error));
  if(candidate.mesh_sha256)details.append(node('small',`Mesh identity ${candidate.mesh_sha256.slice(0,16)}`));
  card.append(details);
 const button=node('button',candidate.run_id===activeId?'Selected mesh':'Inspect mesh');button.type='button';button.disabled=!['complete','partial'].includes(candidate.status)||candidate.run_id===activeId;
  button.onclick=()=>{showWorkspaceView('geometry');openRun(candidate.run_id).catch(error=>status(error.message,true));};card.append(button);grid.append(card);
 }
 panel.append(grid,node('p',study.scope));
 if(study.rejected.length){const rejected=node('details','');rejected.className='rejection-details';rejected.append(node('summary',`${study.rejected.length} rejected evaluations · inspect reasons`));for(const item of study.rejected)rejected.append(node('pre',item.reason));panel.append(rejected);}
}

function renderCemResults(candidate){
 const panel=$('#cem-results');panel.replaceChildren();
 const eng=candidate.engineering,o=eng?.operating_performance,s=eng?.channel_synthesis;
 panel.hidden=!o;if(!o)return;
 panel.append(node('h2','Coupled CEM · evaluated engineering decisions'));
 const grid=node('div','');grid.className='cem-result-grid';
 for(const [label,value] of [['Requested ideal thrust',fmt(candidate.performance.thrust_n)+' N'],['Fixed-hardware ideal thrust',fmt(o.thrust_n)+' N'],['Solved chamber pressure',fmt(o.chamber_pressure_pa/100000)+' bar'],['Selected cooling geometry',eng.channel_count+' channels × '+fmt(eng.channel_radius_mm)+' mm radius']]){
  const card=node('div','');card.append(node('small',label),node('strong',value));grid.append(card);
 }
 panel.append(grid);
 if(s)panel.append(node('p',s.evaluations+' coupled cooling configurations evaluated. Selection uses operating convergence, analytical constraint checks, then the engineering score. The selected dimensions drive the geometry.'));
 panel.append(node('p','The operating prediction uses the same fixed nozzle at the solved feed pressure and mixture ratio. Its difference from requested thrust exposes the regulation requirement. Numerical results remain unvalidated.'));
 const detail=node('details','');detail.append(node('summary','Inspect evaluated cooling configurations'));
 if(s){const table=node('table','');table.className='evidence-table';const head=node('tr','');for(const label of ['Channels','Radius (mm)','Score','Analytical checks'])head.append(node('th',label));table.append(head);for(const sample of s.samples){const row=node('tr','');for(const value of [sample.channel_count,fmt(sample.channel_radius_mm),fmt(sample.score),sample.screen_pass?'Pass':sample.failed_checks.join(', ')])row.append(node('td',String(value)));table.append(row);}detail.append(table);}
 panel.append(detail);
}

async function openRun(id,preferredMode=null){const seq=++sequence;worker?.terminate();$('#metrics').hidden=false;$('#restore-saved').hidden=true;contractPanel.hidden=false;topologyPanel.hidden=false;$('.evidence-section').hidden=false;$('.engineering').hidden=false;const preservedInputs=run?.id===id?[...$('#requirements').elements].filter(e=>e.name).map(e=>[e.name,e.value]):null;if(run?.id!==id)comparisonBaselineId=run?.id||knownRuns.find(r=>r.id!==id)?.id||null;comparisonPanel.replaceChildren(node('p','Checking saved geometry against the previous study…'));$('#library-execution').textContent='Loading execution evidence…';run=await api('/api/runs/'+id);if(seq!==sequence)return;const c=run.candidates[0];renderCemResults(c);renderManufacturing(c.manufacturing);renderDesignCandidates(run.design_study,id);renderVolumeStudy(run.mesh_study,id);

 const combined=!!run.assembly_artifact && preferredMode!=='core';

 $('#geometry-view').value=combined?'assembly':'core';$('#geometry-view').options[0].disabled=!run.assembly_artifact;

 $('#show-shell-label').textContent='Duct walls';$('#show-frame-label').textContent='Frame';

 $('.geometry-workspace .section-title h2').textContent=combined?'Geometry and assembly':'Rocket core geometry';

 const dimensions=currentDimensions=combined?c.assembly.dimensions:c.dimensions;

 const inspectionParts=combined?run.assembly_artifact.components:c.components;

 $('.title h2').textContent=combined?'Vega assembly · shared components':run.artifact?'Rocket core · native component geometry':'Rocket core · CEM recipe preview';

 renderTopology(c.assembly,combined,c.rbcc_architecture_wiring);renderContract(run.system_contract,run);if(!run.computational_model?.stages?.length)throw new Error('This saved run has no computational engineering model record. Restart Vega and reload the run.');renderComputationalModel(run.computational_model);activeRun.replaceChildren(node('strong',`ACTIVE RUN · ${run.id.slice(0,8)}`),node('span',`${run.requirements.propulsion_family.toUpperCase()} · ${fmt(run.requirements.thrust_n)} N · ${c.components.length} core parts · ${c.assembly.components?.length||0} assembly bodies`),node('small',run.created_at?new Date(run.created_at).toLocaleString():'Saved study'));activeRun.classList.remove('draft');stageFlow.replaceChildren();stageFlow.hidden=!combined;if(combined){const d=c.assembly.section_design;const areas={air_inlet:[d.mixer_inlet_area_m2],mixer:[d.mixer_inlet_area_m2,d.mixer_throat_area_m2,d.mixer_exit_area_m2],isolator:[d.mixer_exit_area_m2,d.isolator_exit_area_m2],air_combustor:[d.isolator_exit_area_m2,d.combustor_exit_area_m2],common_nozzle:[d.combustor_exit_area_m2,d.common_nozzle_throat_area_m2,d.common_nozzle_exit_area_m2]};for(const part of c.assembly.components.filter(p=>p.group==='shell')){const button=node('button',part.name);button.append(node('small',(areas[part.id]||[]).map(x=>fmt(x)+' m²').join(' → ')));button.onclick=()=>{$('#detail').textContent=part.role+' | Reference area sequence: '+(areas[part.id]||[]).map(x=>fmt(x)+' m²').join(' → ')+'.';renderer?.setHighlight(part,dimensions);draw();};stageFlow.append(button);}}

 materialSearch.value='';materialSearch.dispatchEvent(new Event('input'));

 for(const [key,value] of Object.entries({material_id:'custom',print_process:'unspecified',test_purpose:'concept',print_min_wall_mm:0,print_min_ligament_mm:0,print_build_x_mm:0,print_build_y_mm:0,print_build_z_mm:0}))$('#requirements').elements[key].value=run.requirements[key]??value;

 for(const [k,v] of Object.entries(run.requirements))if($('#requirements').elements[k])$('#requirements').elements[k].value=v;updateChemistryFields();

 for(const [key,value] of Object.entries({tank_layout:'paired',tank_clearance_mm:22,inlet_aspect_ratio:3,inlet_length_m:3,inlet_wall_mm:10,inlet_section:'rectangular',mixer_length_dh:2,combustor_length_dh:2.5,combined_throat_ratio:.68,combined_exit_ratio:2,airpath_pressure_recovery:.8,frame_sectors:8,frame_topology:'braced',frame_volume_fraction:.65}))if(!(key in run.requirements))$('#requirements').elements[key].value=value;

 $('#requirements').elements.vehicle_mass_mode.value=run.requirements.vehicle_mass_mode||'specified';

 $('#requirements').elements.thermal_model.value=run.requirements.thermal_model||'prescribed_flux';

 if(run.requirements.gas_htc_w_m2_k==null)$('#requirements').elements.gas_htc_w_m2_k.value=1000;

 family.value=run.requirements.propulsion_family||'rocket_only';if(preservedInputs)for(const [name,value] of preservedInputs)if($('#requirements').elements[name])$('#requirements').elements[name].value=value;updateChemistryFields();syncFamily();renderMission(c.vehicle_screen,'Saved study '+id.slice(0,8));missionPanel.classList.remove('draft');draftBanner.hidden=true;if(preservedInputs)markDraft();

 $('#history').value=id;$('#empty').hidden=true;$('#metrics').replaceChildren();

 for(const [label,value,unit] of [['IDEAL THRUST',c.performance.thrust_n,'N'],['IDEAL SPECIFIC IMPULSE',c.performance.ideal_isp_s,'s'],['MASS FLOW',c.performance.mass_flow_kg_s,'kg/s'],['EXIT MACH',c.performance.exit_mach,'']]){const e=node('div','');e.className='metric';e.append(node('small',label),node('strong',fmt(value)+' '+unit));$('#metrics').append(e);}

 const analysis=$('#system-analysis'),ranked=$('#alternatives');analysis.replaceChildren();ranked.replaceChildren();

 if(c.geometry_model){const g=c.geometry_model;analysis.append(node('h3',`Vega Geometry ${g.version} · ${g.layout}`),node('p',`${g.connections.length} registered interfaces · ${(g.total_feed_centerline_mm/1000).toFixed(3)} m total feed route · recipe ${g.recipe_sha256.slice(0,12)}`));for(const text of g.trace)analysis.append(node('p',text));for(const [i,a] of (c.layout_alternatives||[]).entries())analysis.append(node('p',`${i+1}. ${a.layout}: ${(a.feed_length_mm/1000).toFixed(3)} m route · ${a.route_screen_pass?'route checks pass':'route checks fail'}${a.selected?' · selected':''}`));analysis.append(node('p','Placement ranking uses total feed length after route checks. It does not establish an optimal airframe package.'));}

 if(c.engineering){const a=c.engineering,p=a.pressure_bar,t=a.thermal,s=a.structural_screen,m=a.manufacturing_screen,pr=a.pressurization_screen,inj=a.injector_screen;

  for(const [label,value] of [['SCREEN',a.analytical_screen_pass?'Analytical gates pass':'Analytical gate failed'],['MASS FLOW',`${fmt(a.mass_flow_kg_s.fuel)} fuel + ${fmt(a.mass_flow_kg_s.oxidizer)} oxidizer kg/s`],['TANK PRESSURE',`${fmt(p.tank_available)} available / ${fmt(Math.max(p.fuel_required,p.oxidizer_required))} required bar`],['PRESSURANT SUPPLY',`${fmt(pr.minimum_bottle_volume_m3*1000)} L minimum ideal-gas storage · ${fmt(pr.delivered_mass_kg*1000)} g delivered`],['SOURCE PRESSURE',`${fmt(pr.pressure_schedule[0].source_pressure_bar)} → ${fmt(pr.pressure_schedule.at(-1).source_pressure_bar)} bar over burn`],['INJECTOR OUTLETS',`Fuel Ø${fmt(2*inj.single_fuel_orifice_radius_mm)} / oxidizer Ø${fmt(2*inj.single_oxidizer_orifice_radius_mm)} mm, area screen`],['FUEL COOLING',`${a.channel_count} × Ø${fmt(2*a.channel_radius_mm)} mm · ${fmt(p.cooling_loss)} bar estimated loss`],['COOLING ROUTE',t.route_length_m==null?'not recorded':`${fmt(t.route_length_m*1000)} mm centerline · ${fmt(t.assumed_heat_load_w/1000)} kW - ${t.thermal_model||'prescribed_flux'}`],['COOLANT BULK',`${fmt(t.estimated_bulk_outlet_k)} K estimate under assumed ${fmt(t.assumed_heat_flux_mw_m2)} MW/m²`],['HOT WALL ESTIMATE',`${fmt(t.estimated_hot_wall_k)} K with assumed conductivity and HTC`],['COMBINED STRESS SCREEN',`${fmt(100*s.utilization)}% of specified allowable`],['MINIMUM LIGAMENT',`${fmt(Math.min(m.radial_ligament_mm,m.throat_circumferential_ligament_mm))} mm calculated`],['FEED CLEARANCE',c.geometry_audit?`${fmt(c.geometry_audit.minimum_cross_propellant_clearance_mm)} mm centerline clearance`:'not recorded'],['TANK CAPACITY',`${fmt(a.tank_sizing.fuel.required_propellant_kg)} kg fuel / ${fmt(a.tank_sizing.oxidizer.required_propellant_kg)} kg oxidizer`]]){const e=node('div','');e.className='analysis-row';e.append(node('span',label),node('strong',value));analysis.append(e);}

  for(const [key,ok] of Object.entries(a.checks)){const e=node('div',`${ok?'✓':'×'} ${key.replaceAll('_',' ')}`);e.className='check '+(ok?'pass':'fail');analysis.append(e);}

  if(c.geometry_audit){analysis.append(node('h3','Geometry route checks'));for(const [key,ok] of Object.entries(c.geometry_audit.checks)){const e=node('div',`${ok?'✓':'×'} ${key.replaceAll('_',' ')}`);e.className='check '+(ok?'pass':'fail');analysis.append(e);}analysis.append(node('p',c.geometry_audit.scope));}}

 if(c.flight_screen){const f=c.flight_screen;analysis.append(node('h3','Rocket-only vertical diagnostic · no airbreathing acceleration'));const rows=[['PAD THRUST',`${fmt(f.pad_thrust_n??c.performance.thrust_n)} N`],['PAD THRUST / WEIGHT',fmt(f.pad_thrust_to_weight)],['VACUUM IDEAL DELTA-V',`${fmt(f.vacuum_ideal_delta_v_m_s??f.ideal_delta_v_m_s)} m/s`],['BURNOUT',`${fmt(f.burnout_altitude_m)} m · ${fmt(f.burnout_speed_m_s)} m/s`],['APOGEE ESTIMATE',`${fmt(f.predicted_apogee_m)} m`],['MAX DYNAMIC PRESSURE',`${fmt(f.maximum_dynamic_pressure_pa)} Pa`],['TARGET',f.target_screen_pass===null?'No apogee target':`${fmt(f.target_apogee_m)} m · ${f.target_screen_pass?'screen pass':'screen fail'}`]];if(f.target_apogee_m)rows.push(['MINIMUM IDEAL THRUST',f.suggested_minimum_ideal_thrust_n==null?'Outside 100–10,000 N screen':`${fmt(f.suggested_minimum_ideal_thrust_n)} N · vehicle-only solve`]);for(const [label,value] of rows){const e=node('div','');e.className='analysis-row';e.append(node('span',label),node('strong',value));analysis.append(e);}analysis.append(node('p',f.limitations));if(f.thrust_suggestion_scope)analysis.append(node('p',f.thrust_suggestion_scope));}

 for(const v of run.alternatives||[]){const e=node('div',`#${v.rank} · ${v.channel_count} passages × radius ${fmt(v.channel_radius_mm)} mm · score ${fmt(v.score)} · ${v.screen_pass?'screen pass':'failed: '+v.failed_checks.join(', ')}`+(v.selected?' · meshed in this run':''));e.className='alternative'+(v.selected?' selected':'');ranked.append(e);}

 if(c.engineering?.operating_performance){const o=c.engineering.operating_performance;ranked.append(node('p',`Fixed-hardware ideal prediction: ${fmt(o.thrust_n)} N at ${fmt(o.chamber_pressure_pa/100000)} bar, mixture ratio ${fmt(o.mixture_ratio)}. Requested design point: ${fmt(c.performance.thrust_n)} N. ${o.scope}`));}
 if(c.engineering?.channel_synthesis){const s=c.engineering.channel_synthesis;ranked.append(node('p',`Cooling sizing evaluated ${s.evaluations} coupled channel configurations. ${s.selection}. ${s.limits}`));}
 if(c.engineering?.ranking_basis)ranked.append(node('p',c.engineering.ranking_basis));

 if(run.calibration)ranked.append(node('p','Calibration: '+run.calibration.status.replaceAll('_',' ')+'. '+(run.calibration.verification||run.calibration.note||'')));

 const componentToolbar=node('div','');componentToolbar.className='component-toolbar';

 const showAll=node('button','Show all');showAll.type='button';showAll.onclick=()=>{if(renderer){renderer.hiddenComponents.clear();draw();}$('#components').querySelectorAll('.component-visible').forEach(x=>x.checked=true);};

 const hideAll=node('button','Hide all');hideAll.type='button';hideAll.onclick=()=>{if(renderer){renderer.hiddenComponents=new Set(inspectionParts.map(p=>p.id));draw();}$('#components').querySelectorAll('.component-visible').forEach(x=>x.checked=false);};

 const coreOnly=node('button','Core only');coreOnly.type='button';coreOnly.onclick=()=>{const hasGroupedCore=inspectionParts.some(p=>p.group==='core');if(renderer){renderer.hiddenComponents=new Set(hasGroupedCore?inspectionParts.filter(p=>p.group!=='core').map(p=>p.id):[]);draw();}$('#components').querySelectorAll('.component-visible').forEach(x=>{x.checked=!hasGroupedCore||x.dataset.group==='core';});};

 componentToolbar.append(showAll,hideAll,coreOnly);$('#components').replaceChildren(componentToolbar);

 const traced=new Map((run.system_contract?.components||[]).map(p=>[p.id,p]));

 for(const part of inspectionParts){

  const row=node('div','');row.className='component-row';

  const b=node('button',part.name);b.type='button';b.className='component-select';

  b.onclick=()=>{$('#components').querySelectorAll('.component-select').forEach(x=>x.classList.toggle('active',x===b));const t=traced.get(part.id);$('#detail').textContent=part.role+' Axial span: '+part.axial_mm.map(fmt).join('–')+' mm.'+(t?' Drivers: '+t.drivers.join(', ')+'. Exported triangles: '+t.triangle_count+'. Evidence: '+t.evidence_class.replaceAll('_',' ')+'.':'');renderer?.setHighlight(part,dimensions);if(renderer)renderer.isolatedComponent=$('#isolate-part').checked?part.id:null;draw();};

  const visibleLabel=node('label','');visibleLabel.className='component-toggle';const visible=document.createElement('input');visible.type='checkbox';visible.className='component-visible';visible.checked=true;visible.dataset.group=part.group||'';visible.setAttribute('aria-label','Show '+part.name);visible.onchange=()=>{if(!renderer)return;if(visible.checked)renderer.hiddenComponents.delete(part.id);else renderer.hiddenComponents.add(part.id);draw();};visibleLabel.append(visible,node('span','Visible'));

  row.append(b,visibleLabel);$('#components').append(row);

 }

 $('#pipeline').replaceChildren();for(const [stage,state] of Object.entries(run.execution)){const e=node('div','');e.className='step';e.dataset.state=/fail|blocked|open_mesh/.test(state)?'fail':/unvalidated|not_|unsupported|awaiting|conditional|pending/.test(state)?'unknown':'pass';e.append(node('span',stage.replaceAll('_',' ')),node('b',state.replaceAll('_',' ')));$('#pipeline').append(e);}

 $('#unresolved').replaceChildren(...run.unresolved.map(t=>node('li',t)));$('#assumptions').replaceChildren(...run.assumptions.map(t=>node('p',t)));$('#warnings').textContent=run.warnings.join(' ');

 for(const [key,path,ext] of [['stl','solid','stl'],['bundle','bundle','json']]){const a=$('#'+key);a.hidden=key==='stl'&&!run.artifact;a.href=`/api/runs/${id}/${path}`;a.download=`Vega-rocket-${id.slice(0,8)}.${ext}`;}

 if(run.artifact?.cad_reference){let reference=$('#envelope');if(!reference){reference=document.createElement('a');reference.id='envelope';reference.textContent='Download reference envelope STEP';$('.actions').append(reference);}reference.href=`/api/runs/${id}/envelope`;reference.download=`Vega-envelope-${id.slice(0,8)}.step`;reference.hidden=false;}

 if(run.artifact?.flow_sha256){let flow=$('#flow');if(!flow){flow=document.createElement('a');flow.id='flow';flow.textContent='Download passage volume';$('.actions').append(flow);}flow.href=`/api/runs/${id}/flow`;flow.download=`Vega-rocket-${id.slice(0,8)}-flow.stl`;flow.hidden=false;}

 renderer?.clear();$('#show-shell').checked=true;$('#show-frame').checked=true;$('#isolate-part').checked=false;$('#cutaway').checked=combined&&!c.assembly.mesh_policy;$('#render-style').value='solid';yaw=.5;tilt=.8;zoom=.95;$('#camera-view').value='iso';updateViewCaption();$('#mesh-source').textContent='Loading shared component preview…';const scene=combined?c.assembly.scene:await api(`/api/runs/${id}/mesh`);if(seq!==sequence)return;renderer?.setMesh(scene,dimensions);draw();

 if(!run.artifact){$('#mesh-source').textContent='Shell preview only — native artifact stale. Generate a new run for the full geometry.';$('#library-execution').textContent='No current native execution evidence for this revision.';return;}

 $('#mesh-source').textContent=combined?'Loading connected assembly mesh…':'Loading PicoGK core mesh…';const [response,checks]=await Promise.all([fetch(`/api/runs/${id}/${combined?'assembly-native':'native'}`),api(`/api/runs/${id}/checks`)]);if(!response.ok)throw Error('Native mesh unavailable');const buffer=await response.arrayBuffer();if(seq!==sequence)return;

 const meshBodies=combined?run.assembly_artifact.bodies:checks.bodies;

 await new Promise((resolve,reject)=>{worker=new Worker('/mesh-worker.js');worker.onerror=()=>reject(Error('Mesh worker failed'));worker.onmessage=({data})=>{worker.terminate();worker=null;if(seq!==sequence)return resolve();if(data.error)return reject(Error(data.error));renderer?.setPackedMesh(data.packed,dimensions,'native',meshBodies,data.bounds);if(renderer){renderer.centerZ=data.centerZ;renderer.hiddenGroups=new Set();renderer.hiddenComponents.clear();renderer.isolatedComponent=null;}const audit=run.artifact.mesh_audit;$('#mesh-source').textContent=`PicoGK · ${run.artifact.triangles.toLocaleString()} triangles in the unioned STL · ${data.triangles.toLocaleString()} in component view · ${data.bodyCount} named ranges cover all ${data.rangeAudit.coveredTriangles.toLocaleString()} STL triangles · Trimesh: ${audit?.outer_shells??'?'} outer shell, ${audit?.internal_void_shells??'?'} enclosed void shells, ${audit?.watertight?'closed':'open'} mesh · ${run.artifact.voxel_mm} mm voxels · revision ${run.artifact.input_sha256.slice(0,12)} · unvalidated concept`;if(combined)$('#mesh-source').textContent=`${c.assembly.mesh_policy?.backend||'Vega Geometry'} + PicoGK core · ${data.triangles.toLocaleString()} triangles · ${data.bodyCount} named components cover every triangle · ${run.artifact.voxel_mm} mm core voxels${c.assembly.mesh_policy?' · '+c.assembly.mesh_policy.surface_edge_mm+' mm duct edge target':''} · recipe ${c.assembly.recipe_sha256.slice(0,12)} · multi-body concept, hot-flow physics unresolved`;draw();resolve();};worker.postMessage({buffer,length:dimensions.length_mm,bodies:meshBodies},[buffer]);});

 if(seq===sequence){const executed=new Set((checks.library_execution||[]).flatMap(x=>x.library.split(/\s*\+\s*|\s*\/\s*/)));const status=['PicoGK','ShapeKernel','LatticeLibrary','QuasiCrystals'].map(name=>`${name}: ${executed.has(name)?'executed':'installed, not selected'}`).join(' · ');$('#library-execution').textContent=`Library status for this mesh: ${status}. Sampled ${fmt(checks.feed_centerline_samples||0)} feed/injector and ${fmt(checks.passage_centerline_samples||0)} cooling centerline positions. Radial ligament screen: ${fmt(checks.radial_ligament_samples||0)} samples, ${fmt(checks.radial_ligament_failures||0)} failures. Executed operations: `+(checks.library_execution||[]).map(x=>x.library+' — '+x.operation).join('; ')+'. '+checks.limitations;if(renderer)draw();}

 if(seq===sequence&&comparisonBaselineId&&comparisonBaselineId!==id&&run.assembly_artifact){try{renderComparison(await api(`/api/runs/${id}/compare/${comparisonBaselineId}`));}catch(e){comparisonPanel.replaceChildren(node('p','Comparison unavailable: '+e.message));}}else if(seq===sequence)renderComparison(null);

}

$('#geometry-view').onchange=()=>{if(run)(['hybrid','airpath'].includes($('#geometry-view').value)?showHybridMesh($('#geometry-view').value):openRun(run.id,$('#geometry-view').value)).catch(e=>status(e.message,true));};

for(const [id,assemblyGroup,volumeGroup] of [['show-shell','shell','wall_layers'],['show-frame','frame','fluid_core']])$('#'+id).onchange=()=>{if(!renderer)return;const group=['hybrid','airpath'].includes($('#geometry-view').value)?volumeGroup:assemblyGroup;renderer.hiddenGroups||=new Set();if($('#'+id).checked)renderer.hiddenGroups.delete(group);else renderer.hiddenGroups.add(group);draw();};

$('#isolate-part').onchange=()=>{if(renderer){renderer.isolatedComponent=$('#isolate-part').checked?renderer.highlightComponent:null;draw();}};

$('#history').onchange=()=>{if($('#history').value)openRun($('#history').value).catch(e=>status(e.message,true));};

const generationOutputs=node('section','');$('#status').after(generationOutputs);

async function monitorGeneration(j){

 $('#generate').disabled=true;

 const inputs=[...$('#requirements').elements].filter(x=>x.name).map(x=>[x.name,x.value]);

 const seen=new Set();let firstShown=false;

 generationOutputs.replaceChildren();

 try{



  let state;

  do{

   await new Promise(r=>setTimeout(r,1500));state=await api('/api/jobs/'+j.id);

   for(const id of state.available_run_ids||[]){

    if(seen.has(id))continue;seen.add(id);

    const button=node('button','Inspect available mesh '+seen.size);button.type='button';button.onclick=()=>{showWorkspaceView('geometry');openRun(id).catch(e=>status(e.message,true));};generationOutputs.append(button);

    if(!firstShown){firstShown=true;await history();await openRun(id);for(const [name,value] of inputs)if($('#requirements').elements[name])$('#requirements').elements[name].value=value;}

   }

   status((state.message||state.status)+(seen.size?' · '+seen.size+' mesh(es) available':''));

   if(state.status==='failed')throw Error(state.error||'Generation failed.');
   if(state.status==='cancelled')throw Error(state.message||'Generation cancelled; saved outputs are retained.');
   if(state.status==='interrupted')throw Error(state.message||'Generation was interrupted. Available meshes remain saved.');

   if(state.status==='unknown')throw Error('This job could not be found. Check Saved model runs for available outputs; submitting again starts a new generation.');

  }while(!['complete','partial'].includes(state.status));

  await history();if(state.study_id&&!state.run_id){status('Search finished without exported solids. The study and attempt diagnostics remain saved.',true);return;}await openRun(state.run_id||j.id);status(state.status==='partial'?'Generation partially completed. Inspect saved meshes and stage errors.':'Generation complete. Saved meshes are available for inspection.');

 }catch(e){status(e.message,true);}finally{$('#generate').disabled=false;$('#history').disabled=false;}

}
$('#requirements').onsubmit=async e=>{
 e.preventDefault();setInputsVisible(false);showWorkspaceView('geometry');$('#generate').disabled=true;
 try{
  const j=await api($('#search-designs').checked?'/api/design-studies':'/api/rocket/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(briefFromForm())});
  location.hash='job='+j.id;await monitorGeneration(j);
 }catch(e){status(e.message,true);$('#generate').disabled=false;}
};

const materialPanel=node('section','');materialPanel.className='mission-panel';

materialPanel.append(node('h3','Material and manufacturing constraints'));

const materialInfo=node('p','Loading local material library…'),materialResults=node('div','');

const materialSearch=document.createElement('input');materialSearch.type='search';materialSearch.placeholder='Search material or family';materialSearch.setAttribute('aria-label','Search materials');

const materialSelect=document.createElement('select');materialSelect.name='material_id';materialSelect.setAttribute('aria-label','Core material');materialSelect.append(new Option('Custom material / entered properties','custom'));

const processSelect=document.createElement('select');processSelect.name='print_process';processSelect.setAttribute('aria-label','Printing process');

const purposeSelect=document.createElement('select');purposeSelect.name='test_purpose';purposeSelect.setAttribute('aria-label','Test purpose');

for(const [v,l] of [['concept','Concept exploration'],['fit','Fit and assembly'],['cold_flow','Cold-flow test article'],['hot_fire','Hot-fire development']])purposeSelect.append(new Option(l,v));

for(const [label,control] of [['Find material',materialSearch],['Core material',materialSelect],['Printing process',processSelect],['Test purpose',purposeSelect]]){const l=node('label',label);l.append(control);materialPanel.append(l);}

for(const [name,label,max] of [['print_min_wall_mm','Process minimum wall · mm',15],['print_min_ligament_mm','Process minimum ligament · mm',5],['print_build_x_mm','Build X · mm',100000],['print_build_y_mm','Build Y · mm',100000],['print_build_z_mm','Build Z · mm',100000]]){const l=node('label',label),i=document.createElement('input');Object.assign(i,{name,type:'number',min:0,max,step:'any',value:0,required:true});l.append(i);materialPanel.append(l);}

materialPanel.append(node('p','Zero means unspecified. Minimum features change the generated geometry. Build dimensions screen its conservative envelope. Material selection applies to the core; tank and frame properties remain separate.'),materialInfo,materialResults);

$('#requirements').prepend(materialPanel);

let materialLibrary=null;

async function loadMaterials(){

 materialLibrary=await api('/api/materials');

 for(const [v,l] of Object.entries(materialLibrary.processes))processSelect.append(new Option(l,v));

 function options(){const current=materialSelect.value,q=materialSearch.value.toLowerCase();materialSelect.replaceChildren(new Option('Custom material / entered properties','custom'));for(const m of materialLibrary.materials)if(m.id===current||(m.name+' '+m.family).toLowerCase().includes(q))materialSelect.append(new Option(m.name+' · '+m.family+(Object.keys(m.properties).length?' · reference data':' · data required'),m.id));materialSelect.value=current;}

 options();materialSearch.oninput=options;

 materialInfo.textContent=materialLibrary.materials.length+' local material candidates. No printer or material is assumed. Enter grade/process properties in the engineering fields. Catalogue references do not establish printed-part strength.';

 materialSelect.onchange=()=>{

  const m=materialLibrary.materials.find(x=>x.id===materialSelect.value);

  if(!m){materialInfo.textContent='Custom properties: use the engineering values you enter.';return;}

  processSelect.value=m.process_family;

  for(const key of ['core_material_density_kg_m3','wall_conductivity_w_m_k','allowable_stress_mpa','max_wall_temperature_k']){const input=$('#requirements').elements[key];input.value=m.properties[key]??'';}

  materialInfo.textContent=m.name+': '+(m.property_condition||'Grade and process data required')+'. Enter missing properties below. Allowable stress and wall-temperature limit are not inferred from a material name.';

  if(m.property_source){const a=node('a',' Reference datasheet');a.href=m.property_source;a.target='_blank';a.rel='noreferrer';materialInfo.append(a);}

  markDraft();

 };

 $('#requirements').elements.wall_conductivity_w_m_k.min=.01;$('#requirements').elements.wall_conductivity_w_m_k.max=1000;

 $('#requirements').elements.allowable_stress_mpa.min=.1;$('#requirements').elements.allowable_stress_mpa.max=2000;

}

function renderManufacturing(report){

 materialResults.replaceChildren();

 if(!report){materialResults.append(node('p','Saved run has no manufacturing constraint record.'));return;}

 materialResults.append(node('h4','Saved manufacturing screen'),node('p',report.material_name+' · '+report.process+' · '+report.test_purpose+' · '+report.status));

 for(const [key,passed] of Object.entries(report.checks))materialResults.append(node('p',(passed?'PASS: ':'FAIL: ')+key.replaceAll('_',' ')));

 materialResults.append(node('p','Unresolved: '+report.unresolved.join('; ')),node('p',report.scope));

}

// Group existing controls and results without changing the model or saved data.
function showWorkspaceView(name){
 for(const panel of document.querySelectorAll('.workspace-view'))panel.hidden=panel.dataset.view!==name;
 for(const button of document.querySelectorAll('.workspace-nav button'))button.setAttribute('aria-pressed',String(button.dataset.view===name));
 draw();
}
function setInputsVisible(visible){
 $('#design-inputs').hidden=!visible;
 document.body.classList.toggle('inputs-open',visible);
 $('#toggle-inputs').setAttribute('aria-expanded',String(visible));
 $('#toggle-inputs').textContent=visible?'Hide inputs':'Show inputs';
 if(visible)$('#close-inputs').focus();else $('#toggle-inputs').focus();
 draw();
}
function organizeWorkbench(){
 const workspace=$('.workspace');
 const panels={};
 for(const name of ['geometry','candidates','engineering','trace']){
  const section=node('section','');section.className='workspace-view';section.dataset.view=name;section.id='view-'+name;
  section.setAttribute('aria-label',name+' workspace');workspace.append(section);panels[name]=section;
 }
 $('#workspace-summary').append($('#metrics'));
 $('#run-picker').append($('.history'));
 $('#active-run').after($('#status'));
 panels.geometry.append($('.geometry-workspace'),anatomy);
 const routing=node('details','');routing.className='routing-details';routing.append(node('summary','Flowpath components'),stageFlow);$('.actions').after(routing);
 panels.candidates.append(node('h2','Explore candidate designs'),generationOutputs,$('#design-candidates'),comparisonPanel);
 generationOutputs.className='generation-outputs';generationOutputs.setAttribute('aria-label','Available meshes');
 panels.engineering.append(node('h2','Engineering evidence'),missionPanel,topologyPanel,contractPanel,$('.evidence-section'),volumePanel,$('.engineering'),$('.limits'));
 panels.trace.append(modelPanel);
 $('.engineering-layout').remove();
 for(const button of document.querySelectorAll('.workspace-nav button')){
  button.setAttribute('aria-controls','view-'+button.dataset.view);
  button.onclick=()=>showWorkspaceView(button.dataset.view);
 }
 $('#toggle-inputs').onclick=()=>setInputsVisible($('#design-inputs').hidden);
 $('#close-inputs').onclick=()=>setInputsVisible(false);
 $('#presentation-mode').onclick=()=>{
  const enabled=document.body.classList.toggle('presentation-mode');
  $('#presentation-mode').setAttribute('aria-pressed',String(enabled));
  $('#presentation-mode').textContent=enabled?'Exit presentation':'Presentation view';
  if(enabled&&!$('#design-inputs').hidden)setInputsVisible(false);
  draw();
 };
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('#design-inputs').hidden)setInputsVisible(false);});
 // Native validation must reveal collapsed input groups before focusing a field.
 $('#requirements').addEventListener('invalid',event=>{
  setInputsVisible(true);
  for(let parent=event.target.parentElement;parent&&parent!==$('#requirements');parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
 },true);
 materialPanel.id='material-panel';
 const materialGroup=node('details','');materialGroup.className='advanced';materialGroup.append(node('summary','Materials and printing'));
 materialPanel.before(materialGroup);materialGroup.append(materialPanel);$('#fields').after(materialGroup);
 materialPanel.querySelector('h3').remove();
 mission.open=false;
 for(const [label,value] of [['Ideal thrust','—'],['Ideal specific impulse','—'],['Mass flow','—'],['Exit Mach','—']]){
  const metric=node('div','');metric.className='metric';metric.append(node('small',label),node('strong',value));$('#metrics').append(metric);
 }
 showWorkspaceView('geometry');
}
organizeWorkbench();

(async()=>{try{await loadMaterials();const runs=await history();renderer?.clear();const resumed=location.hash.match(/^#job=([a-f0-9]{32})$/);if(resumed){await monitorGeneration({id:resumed[1]});return;}const linked=location.hash.match(/^#run=([a-f0-9]{32})$/);if(linked){await openRun(linked[1]);status('Saved CEM run loaded. Coupled results are shown above the workspace.');return;}status('Vega ready. Select assembly or core detail; inspect components and topology below the viewer.');}catch(e){status(e.message,true);}finally{$('#generate').disabled=false;}})();



