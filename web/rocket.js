'use strict';
const $=id=>document.getElementById(id);
let renderer,report,currentId,token,sceneData,view='half',yaw=.12,tilt=-1.05,zoom=1,epoch=0,loadEpoch=0,busy=false;
const canvas=$('geometry');
let selectedAnatomy=null,anatomyEntries=[];
let latestId=null,auditParts=[];
const anatomyDefinitions=[
  {id:'A01',name:'Two-cone centrebody',body:'centrebody',anchor:[0,0,-8],range:[-30,70],pin:true,description:'Silver inlet cone and its sliding shaft. The two cone sections form the intake concept; the travel control moves this part forward and back.',kind:'Separate component · movable preview ±4 mm'},
  {id:'A02',name:'Precooler',body:'precooler',anchor:[0,18,34],range:[20,49],pin:true,description:'Cyan tube bundle, ring headers and represented helium-loop connections. It represents the air-cooling stage ahead of the compressor.',kind:'Separate component · solid tube and pipe representations'},
  {id:'A03',name:'He circulator',body:'helium-circulator',anchor:[-38,0,40],range:[25,55],pin:true,description:'Gold external pod connected to the represented helium loop. He means helium; this part represents circulation through the precooler loop.',kind:'Separate component · static circulation-machine representation'},
  {id:'A04',name:'Air turbo-compressor',body:'air-compressor',anchor:[11,13,55],range:[48,63],pin:true,description:'Purple hub and blade rows behind the precooler. This represents the air-compression stage; the current model does not rotate or predict compressor performance.',kind:'Separate component · static blade and hub representation'},
  {id:'A05',name:'Hydrogen pump',body:'hydrogen-pump',anchor:[38,0,68],range:[55,82],pin:true,description:'Copper-colored external pod reserved for the hydrogen-pump architecture. Its ports are represented as solid features; a functioning hydrogen circuit is not installed.',kind:'Separate component · static pump representation'},
  {id:'A06',name:'Centrebody guide',body:'casing',anchor:[0,5,53],range:[48,62],description:'Sleeve supporting the sliding centrebody shaft, connected to the casing by radial supports. The bore is 5.2 mm across around a 4 mm stem.',kind:'Integrated casing feature · highlighted axial region'},
  {id:'A07',name:'Nacelle / casing',body:'casing',anchor:[-23,10,16],range:[0,120],pin:true,description:'Outer teal housing surrounding the airflow path. It separates into casing halves A and B for interior inspection.',kind:'Two casing halves · selected half highlighted'},
  {id:'A08',name:'Cooling channels',body:'casing',anchor:[6,7,89],range:[76,112],pin:true,description:'Four curved passages surrounding the aft inner flow body. They connect the front and rear collectors; the route overlay helps trace their paths.',kind:'Integrated passages · highlighted axial region'},
  {id:'A09',name:'Collectors + ports',body:'casing',anchor:[8,8,76],range:[73,79],description:'Ring manifolds and external access ports at the ends of the cooling branches. The front collector is near z=76 mm and the rear one near z=112 mm.',kind:'Integrated casing features · front collector region highlighted'},
  {id:'A10',name:'Inspection throat',body:'casing',anchor:[3.8,3.8,98],range:[95,101],description:'Narrowest section of the aft central passage. Its inspection bore is 7 mm in diameter; it is not a validated firing nozzle.',kind:'Integrated flow-body feature · highlighted axial region'},
  {id:'A11',name:'Outlet / nozzle',body:'casing',anchor:[13,5,117],range:[108,120],pin:true,description:'Flared aft outlet and end collar. The central exit bore is 17 mm in diameter; air leaves the demonstrator here.',kind:'Integrated flow-body feature · highlighted axial region'},
  {id:'A12',name:'Lattice jacket',body:'casing',anchor:[-25,10,38],range:[7,64],description:'BCC lattice near the inlet and gyroid pattern along the outer casing. Rotate the model or choose Assembled to inspect the external pattern.',kind:'Integrated casing feature · highlighted axial region'}
];
function anatomyBody(entry){return entry.body==='casing'?(view==='other'?'half-b':'half-a'):entry.body;}
function buildAnatomy(){
  const baseDefinitions=anatomyDefinitions.filter(entry=>!(report.recipe.concept_systems&&entry.body==='air-compressor')).map(entry=>({...entry}));
  selectedAnatomy=null;anatomyEntries=report.recipe.intake?baseDefinitions:[];
  if(report.recipe.architecture_modules){
    const descriptions={
      'pre-burner':'Separate pre-burner canister in the expanded architecture. This is a non-firing component representation; mixture preparation, injection and combustion are not modeled.',
      're-heater':'Re-heater canister represented as a separate heat-addition stage. Thermal performance and its working-fluid circuit are not established.',
      'drive-turbine':'Twelve-vane turbine representation in the aft review cartridge. Shaft power, rotation, blade stress and coupling are not simulated.',
      'regenerators':'Paired ribbed regenerator canisters with a connecting support. These represent heat-storage hardware; matrix media and heat exchange are not solved.',
      'heat-shield':'Open-sector outer shield around the aft cartridge. The cutaway exposes the internal parts. Material choice and heat protection are not validated.',
      'bell-chamber':'Separate thrust-chamber and bell-nozzle representation behind the inspection outlet. Chamber, throat and bell are geometric review shapes; no firing or thrust performance is established.',
      'ramjet-burner':'Burner-can representation downstream of the spill duct. This is a non-firing architecture addition; ramjet combustion and operability are not modeled.',
      'lox-pump':'Blue LOX (liquid oxygen) pump representation. It identifies the proposed oxygen-feed accessory; cryogenic operation and fluid connections are not validated.',
      'spill-duct':'External spill-flow duct with a flared entry, leading toward the represented ramjet burner. The existing intake CFD does not simulate this duct.'};
    anatomyEntries=[...baseDefinitions,...report.recipe.components.filter(c=>c.anatomy_reference&&c.anatomy_reference!=='A04').map(c=>({id:c.anatomy_reference,name:c.name.replace(' representation',''),body:c.id,anchor:c.review_anchor_mm,range:[-50,220],pin:['A13','A18','A20','A22'].includes(c.anatomy_reference),description:descriptions[c.id],kind:'Separate component · genuine 0.1 mm voxel STL · simplified review display'}))];
  }
  if(report.integration)for(const entry of anatomyEntries){
    const joints=report.integration.joints.filter(j=>j.source===entry.body||j.part===entry.body);
    const component=report.recipe.components.find(c=>c.id===entry.body);
    if(component?.anatomy_reference?.match(/^A(2[2-9]|3[0-6])$/)){
      entry.description=['mount-frame','mount-frame-right','aft-coupling','static-drive'].includes(entry.body)?'Common accessory saddles, aft transition housing, hollow static shaft, bearing webs, spill-duct coupling and heat-shield supports. The shaft is a static representation; it does not drive machinery.':entry.body.endsWith('-line')||entry.body==='helium-link'?'Hollow service harness attached to the existing solid machinery stubs. Both interfaces remain blind; this is a static routing representation.':'Hollow inspection link with rounded bends and tapered annular couplings between the named canisters. Its centerline was sampled for openness; sealing and flow performance remain untested.';
    }
    if(entry.body.endsWith('-test-port'))entry.description='Open annular cold-air test coupling attached to the existing cooling circuit. Native 0.1 mm mesh, sampled open bore and material contact checked. Sealing and instrumentation are not yet qualified.';
    if(entry.body==='spill-outlet-nozzle')entry.description='Open cold-flow outlet attached to the spill-duct burner representation. Defines an outlet for the next airflow case. Its taper is a test geometry, not a thrust-optimized nozzle.';
    if(entry.body.startsWith('bell-cooling-'))entry.description='Three hollow branches in this inspection half join front and rear ring manifolds. Together the halves form six bell-cooling passages. The split seam requires sealing; heat-transfer performance is not established.';
    if(entry.body==='cooling-supply')entry.description='Open passage from the existing core cooling collector to the bell inlet manifold. This continues the cold-flow circuit; it does not connect to a working pump.';
    if(entry.body==='cooling-return')entry.description='Open bell outlet routed behind the casing, with a casing support and accessible test return. Pressure drop is screened by the Python network; leakage is unmeasured.';
    if(joints.length)entry.kind=`Connected · ${joints.length} sampled material joint${joints.length===1?'':'s'} · ${entry.body==='mount-frame'?'static frame':'0.1 mm integration'}`;
    if(entry.body==='centrebody')entry.kind='Sliding joint · ±4 mm preview · retained guide clearance';
  }
  for(const part of report.recipe.concept_systems?.modules||[]){const entry=anatomyEntries.find(e=>e.body===part.id);if(entry){entry.description=part.role;entry.kind='Non-firing concept representation · 0.1 mm native voxels';}}
  for(const part of report.recipe.checked_joints?.parts||[]){const entry=anatomyEntries.find(e=>e.body===part.id);if(entry){entry.description='Static coupling with sampled native material contact at both ends. Open coupling bore; adjacent tank envelopes remain solid. No sealing, fluid-circuit or shaft performance validation.';entry.kind='Checked static attachment · 0.1 mm native voxels';}}
  if(report.recipe.cold_connections){
    for(const entry of anatomyEntries){
      const ports=report.recipe.cold_connections.ports.filter(p=>p.component===entry.body);
      if(ports.length){entry.description='Connected to the cold-air inspection supply/return manifold through open service ports. '+(entry.body.includes('reservoir')?'Hollow reservoir with an open valve connection. Not a cryogenic or pressure-vessel design.':'Static housing; no pump or heat-transfer performance validation.');entry.kind='Cold-air service connection · 0.1 mm native voxels';}
      if(ports.length&&entry.body.startsWith('cooling-'))entry.description='Open connection between the inspection-air manifold and the existing core/bell cooling circuit. The saved baseline cooling estimate does not include the new external header losses.';
      if(['lh2-valve-coupling','lox-valve-coupling'].includes(entry.body))entry.description='Static coupling between the opened reservoir passage and valve housing. No pressure or seal qualification.';
      if(entry.body.startsWith('cold-air-'))entry.description='Connected cold-air inspection header section with routed branches to the equipment housings. This is an inert test circuit, not a propellant cycle.';
      if(entry.body==='core-service-carrier')entry.description='Continuous static backbone joining fan, compressor rows, turbine housings, chamber interfaces, shield and nozzle. No rotating-shaft or load qualification.';
    }
  }
  $('anatomy-panel').hidden=!anatomyEntries.length;$('anatomy-list').replaceChildren();$('anatomy-overlay').replaceChildren();
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('width','100%');svg.setAttribute('height','100%');svg.style.position='absolute';svg.style.inset='0';$('anatomy-overlay').append(svg);
  for(const entry of anatomyEntries){
    const button=document.createElement('button');button.type='button';button.className='anatomy-item';button.dataset.anatomy=entry.id;button.setAttribute('aria-pressed','false');
    const code=document.createElement('b');code.textContent=entry.id;const label=document.createElement('span');label.textContent=entry.name;button.append(code,label);button.addEventListener('click',()=>selectAnatomy(entry.id));$('anatomy-list').append(button);
    const pin=button.cloneNode(true);pin.className='anatomy-pin';pin.title=`${entry.id} · ${entry.name}`;pin.addEventListener('click',()=>selectAnatomy(entry.id));$('anatomy-overlay').append(pin);entry.pinElement=pin;
    const line=document.createElementNS(svg.namespaceURI,'line');line.setAttribute('stroke','#3c7775');line.setAttribute('stroke-width','1');svg.append(line);entry.lineElement=line;
    const dot=document.createElementNS(svg.namespaceURI,'circle');dot.setAttribute('r','3');dot.setAttribute('fill','#236d6a');dot.setAttribute('stroke','#fff');svg.append(dot);entry.dotElement=dot;
  }
  $('anatomy-name').textContent='Select a part';$('anatomy-description').textContent='Use the same reference when asking for additions or changes.';$('anatomy-kind').textContent='';$('anatomy-focus').disabled=true;$('anatomy-copy').disabled=true;$('anatomy-copy-status').textContent='';
}
function updateAnatomy(){
  const enabled=$('show-anatomy').checked&&anatomyEntries.length&&!['baseline','print','detail'].includes(view);$('anatomy-overlay').hidden=!enabled;if(!enabled)return;
  const occupied=[];
  for(const entry of anatomyEntries){
    const body=anatomyBody(entry),visible=(!renderer.isolatedComponent||renderer.isolatedComponent===body)&&!renderer.hiddenComponents?.has(body)&&(entry.pin||selectedAnatomy===entry);
    const pin=entry.pinElement;pin.hidden=!visible;entry.lineElement.style.display=entry.dotElement.style.display=visible?'':'none';if(!visible)continue;
    const anchor=[...entry.anchor];if(entry.body==='centrebody')anchor[2]+=report.recipe.intake.centrebody_mm;
    if(entry.body==='casing'&&view==='other')anchor[1]*=-1;
    const projected=renderer.projectWorld(anchor,body);if(!projected){pin.hidden=true;entry.lineElement.style.display=entry.dotElement.style.display='none';continue;}
    if(projected.x<0||projected.x>renderer.width||projected.y<0||projected.y>renderer.height){pin.hidden=true;entry.lineElement.style.display=entry.dotElement.style.display='none';continue;}
    const w=pin.offsetWidth||140,h=pin.offsetHeight||32;let x=Math.max(8,Math.min(renderer.width-w-8,projected.x-12)),y=Math.max(75,Math.min(renderer.height-h-35,projected.y-12));
    for(let attempt=0;attempt<12&&occupied.some(r=>x<r.x+r.w+6&&x+w+6>r.x&&y<r.y+r.h+5&&y+h+5>r.y);attempt++)y=75+((y-75+h+8)%Math.max(1,renderer.height-h-115));
    occupied.push({x,y,w,h});pin.style.left=`${x+12}px`;pin.style.top=`${y+12}px`;
    const line=entry.lineElement;line.setAttribute('x1',projected.x);line.setAttribute('y1',projected.y);line.setAttribute('x2',x+15);line.setAttribute('y2',y+h/2);
    entry.dotElement.setAttribute('cx',projected.x);entry.dotElement.setAttribute('cy',projected.y);
    pin.setAttribute('aria-pressed',String(selectedAnatomy===entry));
  }
}
async function selectAnatomy(id){
  const entry=anatomyEntries.find(p=>p.id===id);if(!entry)return;selectedAnatomy=entry;
  if(entry.body==='heat-shield')$('show-shield').checked=true;
  if(['baseline','print','detail'].includes(view)||(view==='component'&&renderer.isolatedComponent!==anatomyBody(entry)))await setView('half');
  $('anatomy-name').textContent=`${entry.id} · ${entry.name}`;$('anatomy-description').textContent=entry.description;$('anatomy-kind').textContent=entry.kind;
  $('anatomy-focus').disabled=false;$('anatomy-focus').textContent=entry.body==='casing'?'Show open casing':'Isolate part';$('anatomy-copy').disabled=false;$('anatomy-copy-status').textContent='';
  document.querySelectorAll('.anatomy-item').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.anatomy===id)));draw();
}
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
async function request(url,options){const response=await fetch(url,options),data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');return data;}
function draw(){if(!renderer)return;
  renderer.cutawayComponents=new Set(view==='cooling'?['bell-chamber']:report?.integration&&view==='half'?['aft-coupling']:[]);
  renderer.hiddenComponents=new Set(view==='half'?['half-b']:view==='other'?['half-a']:[]);
  if(!['baseline','print','detail'].includes(view))for(const id of report?.hidden_component_ids||[])renderer.hiddenComponents.add(id);
  if(view==='cooling')for(const body of report.bodies)if(!['bell-chamber','bell-cooling-a','bell-cooling-b','cooling-supply','cooling-return'].includes(body.component_id))renderer.hiddenComponents.add(body.component_id);
  if(view==='audit')for(const body of report.bodies)if(!auditParts.includes(body.component_id))renderer.hiddenComponents.add(body.component_id);
  if(!['component','baseline','print','detail'].includes(view)&&!$('show-shield').checked)renderer.hiddenComponents.add('heat-shield');
  renderer.componentOffsets=report&&!['baseline','print','detail'].includes(view)?{centrebody:[(Number($('centrebody-position').value)-(report.recipe.intake?.centrebody_mm||0))/120,0,0]}:{};renderer.setHighlight(selectedAnatomy&&!['baseline','print','detail'].includes(view)?{id:anatomyBody(selectedAnatomy),axial_mm:selectedAnatomy.range}:null,{length_mm:120});renderer.render(yaw,tilt,zoom,{mode:$('wireframe').checked?'mesh':'solid',routes:$('show-routes').checked&&!['print','detail','component'].includes(view)});updateAnatomy();}
function reset(){yaw=view==='print'?1.42:.12;tilt=({half:-1.05,baseline:-1.05,other:1.05,assembly:.6,cooling:-.9,audit:-.9,print:.65,component:-1.05,detail:-.8})[view];zoom=1;draw();}
function item(parent,text,className=''){const li=document.createElement('li');li.textContent=text;li.className=className;parent.append(li);return li;}
function cells(parent,values){for(const value of values){const cell=document.createElement('td');cell.textContent=value;parent.append(cell);}}
async function meshFile(identity,name,dimensions,bodies,smooth=false,extension=false){
  const response=await fetch(`/api/prints/${identity}/${name}`);if(!response.ok)throw Error('Checked mesh unavailable. Generate again.');
  const buffer=await response.arrayBuffer();let smoothBuffer;
  if(smooth){const normals=await fetch(`/api/prints/${identity}/scene-normals.bin`);if(!normals.ok)throw Error('Display normals unavailable');smoothBuffer=await normals.arrayBuffer();}
  const layers=Array.isArray(extension)?extension:extension?[{mesh:'integration-scene.stl',normals:'integration-normals.bin'}]:[];
  const extraChunks=await Promise.all(layers.map(async layer=>{
    const [mesh,normals]=await Promise.all([fetch(`/api/prints/${identity}/${layer.mesh}`),fetch(`/api/prints/${identity}/${layer.normals}`)]);
    if(!mesh.ok||!normals.ok)throw Error('Checked assembly layer unavailable');
    return {buffer:await mesh.arrayBuffer(),normals:await normals.arrayBuffer()};
  }));
  return new Promise((resolve,reject)=>{const worker=new Worker('/mesh-worker.js');const timer=setTimeout(()=>{worker.terminate();reject(Error('Mesh loading timed out'));},60000);
    worker.onerror=()=>{clearTimeout(timer);worker.terminate();reject(Error('Mesh worker failed'));};worker.onmessage=({data})=>{clearTimeout(timer);worker.terminate();data.error?reject(Error(data.error)):resolve(data);};
    worker.postMessage({buffer,length:dimensions.length_mm,bodies,smoothBuffer,extraChunks},[buffer,smoothBuffer,...extraChunks.flatMap(c=>[c.buffer,c.normals])].filter(Boolean));});
}
async function setView(next){
  view=next;const ticket=++epoch;document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===view)));
  if(view!=='component')$('component-select').value='';
  if(view==='component'){$('component-download').href=`/api/prints/${currentId}/${$('component-select').value}.stl`;$('component-download').hidden=false;}else if(view!=='detail')$('component-download').hidden=true;
  $('view-title').textContent=({half:'Systems assembly · open half',baseline:'Previous design · comparison',other:'The matching half',assembly:'The complete demonstrator',cooling:'Bell cooling · channels and manifolds',print:'Flat mating face on the bed',component:$('component-select').selectedOptions[0]?.textContent,detail:`${report?.detail?.voxel_mm.toFixed(3)} mm · local geometry detail`})[view];
  $('show-routes').disabled=['print','detail','component'].includes(view);if(!renderer||!report||!sceneData)return;
  if(view==='audit')$('view-title').textContent='Assembly audit · intersecting service lines';
  try{
    let data=sceneData,dimensions={length_mm:120,diameter_mm:60},bodies=report.bodies,displayedReport=report;
    if(view==='baseline'){const baseline=report.recipe.design_changes?.baseline_run;if(!baseline)throw Error('No baseline comparison for this run');displayedReport=await request(`/api/prints/${baseline}/report.json`);bodies=displayedReport.bodies;data=await meshFile(baseline,'scene.stl',dimensions,bodies,displayedReport.smooth_normals,displayedReport.scene_layers||!!displayedReport.scene_extension);}
    if(view==='print'){const size=report.parts['half-a'].size_mm;dimensions={length_mm:size[2],diameter_mm:Math.max(size[0],size[1])};bodies=[{component_id:'print',first_triangle:0,triangle_count:report.parts['half-a'].triangles,color:[.19,.60,.60]}];data=await meshFile(currentId,'half-a.stl',dimensions,bodies);}
    if(view==='detail'){dimensions={length_mm:report.detail.crop_size_mm||2,diameter_mm:report.detail.crop_size_mm||2};bodies=[{component_id:'detail',first_triangle:0,triangle_count:report.detail.triangles,color:[.66,.70,.76]}];data=await meshFile(currentId,report.detail.file||'intake-detail.stl',dimensions,bodies);}
    if(ticket!==epoch)return;renderer.clear();renderer.centerZ=data.centerZ;renderer.setPackedMesh(data.packed,dimensions,'PicoGK',bodies,data.bounds);
    renderer.isolatedComponent=view==='baseline'?'half-a':view==='component'?$('component-select').value:null;
    renderer.hiddenComponents=new Set(view==='half'?['half-b']:view==='other'?['half-a']:[]);
    if(!['print','detail','component'].includes(view)&&displayedReport.recipe.cooling){const c=displayedReport.recipe.cooling;renderer.setRoutes([...c.routes.map(r=>({...r,kind:'cooling'})),...[...c.collectors,...c.ports].map(r=>({...r,kind:'collector'})),{kind:'gas',points:[[0,0,66],[0,0,120]]}],dimensions,['half','baseline'].includes(view)?1:view==='other'?-1:0);}
    const selectedId=view==='component'?$('component-select').value:null,selectedBody=bodies.find(b=>b.component_id===selectedId);
    if(displayedReport.recipe.bell_cooling&&!['print','detail','component','baseline'].includes(view)){
      const c=displayedReport.recipe.bell_cooling;
      const paths=[...c.branches,...c.rings,...c.ports,{points:c.supply},{points:c.return}].map(r=>({...r,kind:'cooling'}));
      if(view!=='cooling')paths.push(...displayedReport.recipe.cooling.routes.map(r=>({...r,kind:'cooling'})));
      renderer.setRoutes(paths,dimensions,0);
    }
    const pitch=view==='detail'?report.detail.voxel_mm:selectedBody?.voxel_mm||displayedReport.recipe.voxel_mm;
    const resolutionText=displayedReport.display_meshes&&view!=='detail'&&!selectedId?'0.1 mm additions / 0.2 mm base':`${pitch.toFixed(pitch<.01?3:2)} mm voxels`;
    $('mesh-info').textContent=`${view==='baseline'?'PREVIOUS · ':''}${resolutionText} · ${(view==='detail'?report.detail.triangles:selectedBody?selectedBody.triangle_count:bodies.reduce((n,b)=>n+b.triangle_count,0)).toLocaleString()} ${displayedReport.display_meshes&&view!=='detail'?'display triangles · full-resolution STL downloads':'triangles'}`;
    reset();
  }catch(error){status(error.message,true);}
}
function showSystems(loaded){
  const r=loaded.recipe,c=r.cooling,n=loaded.native,cem=loaded.cem;
  for(const id of ['channel-rows','cem-checks','cem-stages'])$(id).replaceChildren();
  $('cooling-detail').textContent=c?`${c.routes.length} branches, ${(2*c.routes[0].bore_radius_mm).toFixed(2)} mm nominal bores, two collectors and two access ports. ${(n.cooling_clearance_samples||0).toLocaleString()} cross-section samples checked.`:'Regenerate to inspect channels.';
  $('nozzle-detail').textContent=r.nozzle_geometry?`Throat diameter ${(2*r.nozzle_geometry.throat_radius_mm).toFixed(1)} mm; exit ${(2*r.nozzle_geometry.exit_radius_mm).toFixed(2)} mm. Fixed inspection contour; no thrust sizing.`:'';
  $('mesh-pipeline').textContent=cem?`${loaded.input_mesh.triangles.toLocaleString()} validated input triangles → ${n.voxel_mm} mm PicoGK voxels → implicit features and Boolean channels → checked STL parts. Input SHA-256: ${loaded.input_mesh.sha256}`:'';
  $('boolean-evidence').textContent=n.boolean_operations?`${n.boolean_reference_samples} Boolean reference probes passed. Add ${n.boolean_operations.Add}, Subtract ${n.boolean_operations.Subtract}, Intersect ${n.boolean_operations.Intersect}. Failed operations block publication.`:'';
  if(loaded.module_native){const m=loaded.module_native;$('boolean-evidence').textContent+=` New 0.1 mm modules: ${m.boolean_reference_samples} additional reference probes passed; Add ${m.boolean_operations.Add}, Intersect ${m.boolean_operations.Intersect}.`;$('mesh-pipeline').textContent+=` New modules: ${Object.values(loaded.module_input_meshes).reduce((sum,p)=>sum+p.triangles,0).toLocaleString()} closed input triangles → 0.1 mm voxels → checked full-resolution component STLs.`;}
  $('connection-panel').hidden=!loaded.integration;
  if(loaded.integration){
    const a=loaded.integration,m=loaded.integration_native;
    $('connection-summary').textContent=`${a.fixed_parts_connected} fixed parts connected through ${a.joints.length} sampled material joints. Centrebody: sliding guide, ±4 mm preview.`;
    $('connection-scope').textContent=a.fluid_scope;
    $('connection-rows').replaceChildren();
    const label=id=>{const p=loaded.recipe.components.find(p=>p.id===id);return p?`${p.anatomy_reference||''} ${p.name}`.trim():id;};
    for(const j of a.joints){const row=document.createElement('tr');cells(row,[label(j.part),label(j.source),j.name,'Contact passed']);$('connection-rows').append(row);}
    $('boolean-evidence').textContent+=` Integration: ${m.boolean_reference_samples} reference probes; Add ${m.boolean_operations.Add}, Subtract ${m.boolean_operations.Subtract}; ${a.source_contact_probes} source-material probes passed.`;
    $('mesh-pipeline').textContent+=' Integration additions: closed triangular inputs → 0.1 mm voxels → implicit beams and subtracted bores.';
  }
  if(!cem)return;const network=cem.channel_network;$('cooling-flow').value=network.total_flow_ml_s;
  $('cycle-detail').textContent=`Branch-only pressure drop: ${network.branch_only_pressure_drop_pa.toFixed(2)} Pa at ${network.total_flow_ml_s} mL/s. Heat-capacity rate: ${network.heat_capacity_rate_w_k.toFixed(4)} W/K; achieved cooling duty remains unmeasured.`;
  for(const b of network.branches){const row=document.createElement('tr');cells(row,[b.id,`${b.length_mm.toFixed(2)} mm`,`${b.flow_ml_s.toFixed(2)} mL/s`,b.reynolds.toFixed(0),`${b.pressure_drop_pa.toFixed(2)} Pa`]);$('channel-rows').append(row);}
  for(const check of cem.checks)item($('cem-checks'),`${check.status} · ${check.id.replaceAll('_',' ')}`,check.status==='passed'?'check-pass':'check-open').title=check.scope||check.evidence;
  for(const stage of cem.stages)item($('cem-stages'),stage.method);
  for(const [id,file] of [['cem-link','cem.json'],['input-mesh-link','input-body.stl']]){$(id).href=`/api/prints/${currentId}/${file}`;$(id).hidden=false;}
}
function showAnalysis(data,preview){
  $('analysis-status').textContent=`${preview?'Live analysis; generate to save this position':'Saved analysis'} · centrebody ${data.centrebody_mm.toFixed(1)} mm. Reduced models solved; physical validation pending.`;
  const c=data.cfd,f=data.fea;
  $('cfd-summary').textContent=`${c.cells.toLocaleString()} cells at ${c.grid_mm} mm. Peak speed ${c.peak_velocity_m_s.toFixed(3)} m/s; relative mass imbalance ${c.relative_mass_imbalance.toExponential(2)}. Peak-speed change across two grids: ${c.grid_comparison.peak_velocity_change_percent.toFixed(2)}%. Grid independence remains unestablished.`;
  $('fea-summary').textContent=`${f.elements} elements. Tip deflection ${f.tip_displacement_mm.toFixed(4)} mm; nominal peak bending stress ${(f.maximum_bending_stress_pa/1e6).toFixed(3)} MPa. Refinement deflection change: ${f.mesh_comparison.tip_displacement_change_percent.toFixed(3)}%. No strength acceptance is claimed.`;
  const cv=$('cfd-plot'),ctx=cv.getContext('2d');ctx.clearRect(0,0,cv.width,cv.height);ctx.fillStyle='#fff';ctx.fillRect(0,0,cv.width,cv.height);const [lo,hi]=c.pressure_range_pa;
  for(const [z,r,uz,ur,p] of c.field){const t=(p-lo)/Math.max(hi-lo,1e-9);ctx.fillStyle=`hsl(${240*(1-t)},65%,52%)`;ctx.fillRect(45+(z+24)/48*720,235-r/30*210,c.grid_mm/48*720+1,c.grid_mm/30*210+1);}
  ctx.fillStyle='#233e3a';ctx.font='14px sans-serif';ctx.fillText(`Pressure variation: ${lo.toFixed(2)} to ${hi.toFixed(2)} Pa`,45,22);ctx.fillText('Axial position z: -24 to +24 mm',260,270);ctx.fillText('r (mm)',3,48);
  const fv=$('fea-plot'),fx=fv.getContext('2d');fx.clearRect(0,0,fv.width,fv.height);fx.fillStyle='#fff';fx.fillRect(0,0,fv.width,fv.height);const zs=f.nodes_z_mm,ds=f.displacement_mm,max=Math.max(...ds.map(Math.abs),1e-12);fx.strokeStyle='#257d78';fx.lineWidth=3;fx.beginPath();
  for(let i=0;i<zs.length;i++){const x=45+(zs[i]-zs[0])/(zs.at(-1)-zs[0])*710,y=235-ds[i]/max*180;i?fx.lineTo(x,y):fx.moveTo(x,y);}fx.stroke();fx.fillStyle='#233e3a';fx.font='14px sans-serif';fx.fillText(`Lateral displacement: 0 to ${max.toFixed(4)} mm (exaggerated plot)`,45,22);fx.fillText('Tip to guide clamp at z = 48 mm',250,270);
}
async function load(identity){
  $('design-audit-panel').hidden=true;
  const ticket=++loadEpoch;++epoch;$('downloads').hidden=true;$('report-link').hidden=true;status('Loading checked native geometry…');
  const loaded=await request(`/api/prints/${identity}/report.json`);if(ticket!==loadEpoch)return;
  if(loaded.recipe.architecture!=='sabre_inspired_precooled_combined_cycle')throw Error('Legacy architecture. Generate a new study.');
  currentId=identity;report=loaded;showSystems(report);buildAnatomy();
  const expanded=!!report.recipe.architecture_modules;
  for(const id of ['reference-flow','cooling-flow','resolution'])$(id).disabled=expanded&&!report.recipe.concept_systems;
  $('generate').textContent=expanded?'Rebuild 0.1 mm modules':'Synthesize & generate';
  $('module-resolution-note').hidden=!expanded;
  $('module-resolution-note').textContent=expanded?'New and upgraded modules: genuine 0.1 mm voxels. Accepted base casing and original accessories: 0.2 mm. Display meshes are simplified; downloads retain the native component resolution. CFD/FEA cover the intake and centrebody only.':'';
  $('centrebody-position').value=String(report.recipe.intake?.centrebody_mm||0);$('travel-value').textContent=`${Number($('centrebody-position').value).toFixed(1)} mm`;
  $('centrebody-position').nextElementSibling.textContent=report.integration?'±4 mm movement preview. Rebuilding this connected assembly retains the saved centrebody position. Run CFD + FEA to analyze the preview position.':'Moves the centrebody in the viewer. Generate to save that position; Run CFD + FEA to solve the selected position.';
  $('component-select').replaceChildren(new Option('Whole system',''));for(const c of report.recipe.components||[])$('component-select').add(new Option(c.name,c.id));$('detail-view').disabled=!report.detail;$('component-download').hidden=true;
  $('analysis-download').hidden=true;
  if(report.analysis_summary){showAnalysis(await request(`/api/prints/${identity}/analysis.json`),false);$('analysis-download').href=`/api/prints/${identity}/analysis.json`;$('analysis-download').hidden=false;$('detail-evidence').textContent=`Detail: ${report.detail.voxel_mm.toFixed(3)} mm native voxels · ${report.detail.triangles.toLocaleString()} triangles · ${report.detail.scope}. Full assembly: ${report.recipe.voxel_mm} mm voxels with interpolated display normals.`;}
  $('baseline-view').hidden=!report.recipe.design_changes;$('design-change').hidden=!report.recipe.design_changes;$('design-change').textContent=report.recipe.design_changes?report.recipe.design_changes.description:'';
  if(renderer){const parsed=await meshFile(identity,'scene.stl',{length_mm:120,diameter_mm:60},report.bodies,report.smooth_normals,report.scene_layers||!!report.scene_extension);if(ticket!==loadEpoch)return;sceneData=parsed;await setView('half');}
  if(ticket!==loadEpoch)return;$('empty-state').hidden=!!renderer;$('resolution').value=String(report.recipe.voxel_mm);
  const synthesis=report.recipe.synthesis,search=synthesis.search,selected=search.selected;
  $('reference-flow').value=String(synthesis.reference.mass_flow_kg_s*1000);
  $('synthesis-summary').textContent=`Selected ${selected.tube_count} tubes × ${selected.length_mm} mm from ${search.evaluated} candidates (${search.feasible} feasible). ${search.material_proxy_reduction_percent.toFixed(1)}% less tube material proxy than ${search.baseline}, meeting the assumed area and clearance targets. This is a geometric comparison, not measured cooling performance.`;
  $('equation-results').replaceChildren();
  const ribStudy = report.recipe.inlet_revision?.topology_optimization;
  if (ribStudy) {
    const card = document.createElement('div');
    card.className = 'equation-card';
    const heading = document.createElement('strong');
    heading.textContent = 'Inlet reinforcement';
    const detail = document.createElement('p');
    detail.textContent = `Four external ribs selected from ${ribStudy.candidates} layouts. Under two assumed 1 N handling cases, modeled worst compliance changes from ${ribStudy.original_mm_per_n.toFixed(4)} to ${ribStudy.reinforced_mm_per_n.toFixed(4)} mm/N. Assumes a fixed casing seat.`;
    card.append(heading, detail);
    $('equation-results').append(card);
  }
  if (selected.bundle_screen) {
    const screen = selected.bundle_screen;
    const card = document.createElement('div');
    card.className = 'equation-card';
    const heading = document.createElement('strong');
    heading.textContent = 'Precooler midspan and thermal margin';
    const detail = document.createElement('p');
    detail.textContent = `Open section ${screen.open_area_mm2.toFixed(0)} mm² against ${screen.required_area_mm2.toFixed(0)} mm² required. Bulk air speed ${screen.midspan_velocity_m_s.toFixed(2)} m/s. With the assumed constant-temperature sink, outlet ${screen.isothermal_sink_outlet_k.toFixed(1)} K against the ${synthesis.reference.cooled_temperature_k} K target.`;
    card.append(heading, detail);
    $('equation-results').append(card);
  }
  for(const [title,equation,result] of [['Intake continuity','A = mass flow / (density × velocity)',`Reference intake radius ${synthesis.geometry.intake_inner_radius_mm.toFixed(2)} mm`],['Precooler surface screen','Q = mass flow × cp × delta T; A = Q / (U × LMTD)',`${synthesis.equations[1].outputs.heat_duty_w.toFixed(1)} W hypothetical duty · ${selected.surface_area_mm2.toFixed(0)} mm² tube surface`],['Channel network','delta p = Q × R; R = 8 viscosity L / (pi r^4)',report.cem?`${report.cem.channel_network.branch_only_pressure_drop_pa.toFixed(2)} Pa branch-only estimate`:'Regenerate to evaluate channel resistance']]){const card=document.createElement('div');card.className='equation-card';const heading=document.createElement('strong');heading.textContent=title;card.append(heading);for(const value of [equation,result]){const p=document.createElement('p');p.textContent=value;card.append(p);}$('equation-results').append(card);}
  $('candidate-rows').replaceChildren();for(const c of search.candidates){const row=document.createElement('tr');if(c.id===selected.id)row.className='selected';cells(row,[c.id,c.surface_area_mm2.toFixed(0),c.tube_gap_mm.toFixed(2),c.material_proxy_mm3.toFixed(0),c.id===selected.id?'Selected':c.feasible?'Feasible':c.rejection]);$('candidate-rows').append(row);}
  const list=document.createElement('ul');for(const text of ['Both casing halves are watertight, consistently wound and connected',`${report.native.sampled_open_path_points.toLocaleString()} casing open-path samples checked`,`${report.native.precooler_tube_count} synthesized precooler tubes exported`,`${Object.keys(report.components||{}).length} separate component surfaces checked`,'Physical fit, leakage, machinery operation and cooling duty remain unverified'])item(list,text);$('checks').replaceChildren(list);
  for(const [id,file] of [['kit-link','vega-one-print-kit.zip'],['part-a','half-a.stl'],['part-b','half-b.stl'],['guide-link','PRINT.txt'],['report-link','report.json']])$(id).href=`/api/prints/${identity}/${file}`;
  $('kit-link').textContent=report.integration?'Download integration additions ↓ ZIP':'Download print kit ↓ ZIP';
  $('base-kit-link').hidden=!report.integration;
  $('kit-description').textContent=report.integration?'Revision 9 adds eleven integration parts to the accepted base. Download both kits for the complete set, or use the component selector for individual STLs. Shared coordinates align the parts; fabrication tolerances, fasteners and supports still need review.':'Download the checked casing and component STLs. Review orientation, supports and physical fit before printing.';
  if(report.integration)$('base-kit-link').href=`/api/prints/${report.base_run}/vega-one-print-kit.zip`;
  if(report.integration){
    item(list,`${report.integration.fixed_parts_connected} fixed parts in one sampled material-contact network; centrebody retains its sliding joint`);
    item(list,report.integration.fluid_scope);
    $('generate').textContent='Rebuild connected assembly';
    $('module-resolution-note').textContent+=' Mounts and routed connections: 0.1 mm. Original machinery ports remain blind.';
  }
  $('cooling-view').hidden=!report.recipe.bell_cooling;
  $('whole-engine-panel').hidden=!report.whole_engine_assessment;
  $('whole-engine-summary').textContent='';
  if(report.whole_engine_assessment){
    $('whole-engine-result').textContent=report.whole_engine_assessment.conclusion;
    $('whole-engine-checks').replaceChildren();
    for(const c of report.whole_engine_assessment.checks||[]){const row=document.createElement('tr');cells(row,[c.id.replaceAll('_',' '),c.status.replaceAll('_',' '),c.evidence]);$('whole-engine-checks').append(row);}
    $('assessment-link').href=`/api/prints/${identity}/whole-engine-assessment.json`;
    $('network-link').href=`/api/prints/${identity}/cooling-network.json`;
    if(report.cooling_network?.edges)showCoolingNetwork(report.cooling_network,false);
    else $('cold-network-summary').textContent='Expanded architecture has not been simulated. The saved cooling calculation covers the baseline only.';
    $('detail-view').textContent='0.009 mm cooling detail';
    $('generate').textContent='Rebuild bell cooling';
    $('kit-description').textContent='Revision 10 cooling additions and replacement service lines. Use the revision 9 integration kit together with its revision 8 base kit; each base revision links to its predecessor. Individual component downloads retain native resolution.';
    $('module-resolution-note').textContent+=' Local cooling detail: 0.009 mm. This does not change the full assembly pitch.';
  }
  $('generate').disabled=busy;
  if(report.recipe.concept_systems){
    const concept=report.recipe.concept_systems;
    $('generate').textContent='Generate separate base airflow mesh';
    $('module-resolution-note').textContent='Expanded non-firing architecture: 19 subsystem representations and two review frames at 0.1 mm. Tanks, valves and heat exchangers are review envelopes. New cycle, fluid continuity and mechanical fit are unverified.';
    $('analysis-status').textContent='The plots below are inherited baseline intake/centrebody calculations. They do not analyse the added machinery or validate this revision.';
    $('whole-engine-result').textContent='Expanded assembly simulation has not run. Proposed subsystem connections must be resolved into fluid domains and operating conditions first.';
    $('connection-summary').textContent='Baseline joint samples plus proposed subsystem relationships. The new relationships below do not establish physical fluid continuity.';
    const label=id=>report.recipe.components.find(p=>p.id===id)?.name||id;
    for(const link of concept.connections){const row=document.createElement('tr');cells(row,[label(link.source),label(link.target),link.medium,link.status]);$('connection-rows').append(row);}
    $('kit-description').textContent='New non-firing subsystem representations and review frames, plus a nested baseline-interface kit. Original engine components remain available from the baseline revision. This is a concept-review export, not manufacturing approval.';
    if(report.recipe.checked_joints){
      $('module-resolution-note').textContent+=' Three static couplings A61–A63 added at 0.1 mm; sampled contact checked. Reservoir flow passages remain blocked.';
      $('kit-description').textContent='This revision kit contains the three static couplings and their scope note. Other components are available individually; the preceding concept revision contains the subsystem kit. These files do not establish fabrication or operating readiness.';
    }
    if(report.recipe.cold_connections){
      $('module-resolution-note').textContent='Connected cold-air inspection assembly: hollow reservoirs, opened service ports, routed supply/return headers and continuous core carrier. Changed geometry uses 0.1 mm voxels; the 0.009 mm cooling sample remains local.';
      $('whole-engine-result').textContent='Connected cold-air inspection geometry; updated simulation required.';
      $('whole-engine-summary').textContent='Reservoirs and external housings are connected to a common inspection-air manifold. This does not implement the proposed propellant or thermal cycle. Previous Linux CFD belongs to the earlier geometry.';
      $('connection-summary').textContent='New cold-air service connections below are separate from the proposed engine-cycle relationships. Geometry connection checks do not establish seals or performance.';
      for(const link of report.recipe.cold_connections.connections){const row=document.createElement('tr');cells(row,[label(link.source),label(link.target),'Room-temperature inspection air',link.status]);$('connection-rows').append(row);}
      $('kit-description').textContent='Changed parts: opened equipment housings and reservoirs, supply/return headers and core carrier. Individual unchanged components remain available. Non-firing geometry review only.';
    }
  }
  $('downloads').hidden=false;$('report-link').hidden=false;$('run-id').textContent=`RUN ${identity.slice(0,8)} · ${report.recipe.recipe_sha256.slice(0,12)}`;history.replaceState(null,'',`#print=${identity}`);status('Mesh checks passed. Inspect components and analyses.');
  let notice=$('revision-notice');if(!notice){notice=document.createElement('p');notice.id='revision-notice';notice.className='design-change';document.querySelector('.viewer-heading').after(notice);}notice.replaceChildren();notice.hidden=!latestId||latestId===identity;
  if(!notice.hidden){notice.append('You are viewing an older assembly. ');const link=document.createElement('a');link.href=`#print=${latestId}`;link.textContent='Open latest revision';notice.append(link);}
  let networkPanel=$('component-network-panel');if(!networkPanel){networkPanel=document.createElement('p');networkPanel.id='component-network-panel';networkPanel.className='design-change';$('downloads').before(networkPanel);}networkPanel.textContent='Checking component requirements…';
  try{const network=await request(`/api/component-network/${identity}`);if(ticket!==loadEpoch)return;const v=network.validation;networkPanel.textContent=`Required circuits: ${network.model.circuits.map(c=>c.id).join(', ')}. Topology ${v.topology_valid?'passes':'fails'}. ${v.missing_data.length} missing engineering inputs. ${v.ready_for_sizing?'Inputs declared; physics still requires validation.':'Not ready for sizing.'} Geometry connectivity is unverified. `;const link=document.createElement('a');link.href=`/api/component-network/${identity}`;link.textContent='Read component, port and connectivity report';networkPanel.append(link);networkPanel.append(' · ');const inputs=document.createElement('a');inputs.href=`/api/engineering-inputs/${identity}`;inputs.textContent='Engineering input ledger';networkPanel.append(inputs);for(const [file,label] of [['cfd-case.json','CFD manifest'],['fluent-case.json','Fluent manifest'],['openfoam-case.zip','OpenFOAM case']]){networkPanel.append(' · ');const download=document.createElement('a');download.href=`/api/prints/${identity}/${file}`;download.textContent=label;networkPanel.append(download);}try{const cfd=await request(`/api/prints/${identity}/cfd-case.json`);networkPanel.append(' · OpenFOAM: '+(cfd.simulation?.status||'not-run')+'; design geometry is unchanged until a solved field is fed back.');}catch{networkPanel.append(' · OpenFOAM: case export unavailable for this run.');}}catch(error){if(ticket===loadEpoch)networkPanel.textContent=`Component requirements unavailable: ${error.message}`;}
  if(ticket===loadEpoch){
    const requirement=document.createElement('p');
    requirement.textContent='Full-size concept target: 11 kN net thrust at sea-level static conditions (Mach 0, 101325 Pa, 288.15 K). Achieved thrust remains unverified.';
    networkPanel.append(requirement);
  }
  try{const audit=await request(`/api/design-audits/${identity}`);if(ticket!==loadEpoch)return;if(audit.available)showDesignAudit(audit);}catch(error){if(ticket===loadEpoch)status(`Design audit unavailable: ${error.message}`,true);}
}
function showDesignAudit(audit){
  $('design-audit-panel').hidden=false;$('design-audit-result').textContent=audit.conclusion;
  $('design-audit-summary').textContent=`${audit.assembly_size_mm ? 'Current assembly: '+audit.assembly_size_mm.map(v=>v.toFixed(1)).join(' × ')+' mm. ' : ''}Reference arithmetic: ${audit.arithmetic.filter(c=>c.passed).length}/${audit.arithmetic.length} checks passed. Whole-engine operation remains unverified.`;
  $('design-audit-checks').replaceChildren();$('design-audit-logic').replaceChildren();$('design-audit-conflicts').replaceChildren();
  for(const c of audit.checks){const row=document.createElement('tr');cells(row,[c.id.replaceAll('_',' '),c.status,c.evidence]);$('design-audit-checks').append(row);}
  for(const c of audit.logic){const row=document.createElement('tr');cells(row,[c.system,c.method,c.coupling]);$('design-audit-logic').append(row);}
  const label=id=>{const c=report.recipe.components.find(p=>p.id===id);return c?`${c.anatomy_reference||''} ${c.name}`:id;};
  for(const c of audit.route_conflicts){const p=document.createElement('p');p.textContent=`${c.parts.map(label).join(' ↔ ')}: ${c.kind.replaceAll('_',' ')}. ${c.native_evidence?.status==='confirmed_shared_material'?'Shared material confirmed in native STLs.':'Nominal envelope overlap; native confirmation pending.'} `;const button=document.createElement('button');button.type='button';button.textContent='Inspect these two parts';button.addEventListener('click',async()=>{auditParts=c.parts;selectedAnatomy=null;$('show-routes').checked=false;await setView('audit');$('geometry').scrollIntoView({behavior:'smooth',block:'center'});});p.append(button);$('design-audit-conflicts').append(p);}
  $('design-audit-link').href=`/api/design-audits/${currentId}`;
  if(audit.external_simulation){
    const sim=audit.external_simulation;
    $('whole-engine-result').textContent=sim.status==='numerical_checks_passed'?'Linux cold-air pilot completed; whole-engine operation unverified.':'Linux cold-air pilot: '+sim.status.replaceAll('_',' ')+'. Whole-engine operation unverified.';
    $('whole-engine-summary').textContent=sim.scope;
  }
  if(audit.cooling_network?.edges){
    showCoolingNetwork(audit.cooling_network,true);
    $('cold-network-summary').textContent+=' Updated audit model: finite core collectors included. Assumes unobstructed pipes; assembly conflicts remain. Saved revision downloads preserve the earlier calculation.';
  }
  const unresolved=audit.checks.some(c=>['blocked','failed','incomplete'].includes(c.status));
  status(audit.route_conflicts.length?'Assembly audit found routing conflicts. See the design review below.':unresolved?'Engineering audit found incomplete sizing or connections. See the design review below.':'Targeted design audit loaded.',!!audit.route_conflicts.length||unresolved);
}
async function follow(identity){busy=true;$('generate').disabled=true;try{for(;;){const state=await request(`/api/jobs/${identity}`);status(state.message);if(state.status==='complete'){latestId=identity;await load(identity);return;}if(['failed','interrupted'].includes(state.status))throw Error(state.message);await new Promise(resolve=>setTimeout(resolve,1200));}}finally{busy=false;$('generate').disabled=false;}}
function options(){return {voxel_mm:Number($('resolution').value),reference_flow_g_s:Number($('reference-flow').value),cooling_flow_ml_s:Number($('cooling-flow').value),centrebody_mm:Number($('centrebody-position').value)};}
$('generate-form').addEventListener('submit',async event=>{
  event.preventDefault();
  if(busy)return;
  busy=true;$('generate').disabled=true;status('Starting the specialized CEM…');
  try {
    let requestOptions=options();
    if(report?.recipe.cold_connections){
      requestOptions={expanded_inlet:true,reference_flow_g_s:Number($('reference-flow').value)};
    }else if(!report?.recipe.concept_systems){
      if(report?.recipe.bell_cooling)requestOptions={bell_cooling:true};
      else if(report?.integration)requestOptions={assembly_integration:true,centrebody_mm:report.recipe.intake.centrebody_mm};
      else if(report?.recipe.architecture_modules)requestOptions={architecture_expansion:true,centrebody_mm:Number($('centrebody-position').value)};
    }
    const job=await request('/api/build',{method:'POST',headers:{'Content-Type':'application/json','X-Vega-Token':token},body:JSON.stringify(requestOptions)});
    await follow(job.id);
  }catch(error){status(error.message,true);}finally{busy=false;$('generate').disabled=false;}
});
$('centrebody-position').addEventListener('input',()=>{$('travel-value').textContent=`${Number($('centrebody-position').value).toFixed(1)} mm`;draw();$('analysis-status').textContent='Centrebody preview moved. Run CFD + FEA for this position, or generate to save its mesh.';});
$('component-select').addEventListener('change',()=>{const id=$('component-select').value;$('component-download').hidden=!id;if(id)$('component-download').href=`/api/prints/${currentId}/${id}.stl`;setView(id?'component':'half');});
$('detail-view').addEventListener('click',()=>{if(report?.detail){$('component-download').href=`/api/prints/${currentId}/${report.detail.file||'intake-detail.stl'}`;$('component-download').hidden=false;setView('detail');}});
$('run-analysis').addEventListener('click',async()=>{const button=$('run-analysis');button.disabled=true;$('analysis-status').textContent='Solving intake finite volumes and centrebody finite elements…';try{showAnalysis(await request('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json','X-Vega-Token':token},body:JSON.stringify(options())}),true);}catch(error){$('analysis-status').textContent=error.message;}finally{button.disabled=false;}});
for(const id of ['reference-flow','cooling-flow','resolution'])$(id).addEventListener('change',()=>{if(report)status('Inputs changed. Generate to update the geometry and report.');});
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>setView(button.dataset.view)));
window.addEventListener('hashchange',()=>{const identity=new URLSearchParams(location.hash.slice(1)).get('print');if(identity&&/^[a-f0-9]{32}$/.test(identity)&&identity!==currentId)load(identity).catch(error=>status(error.message,true));});
for(const id of ['wireframe','show-routes','show-shield'])$(id).addEventListener('change',draw);$('reset-view').addEventListener('click',reset);
$('show-anatomy').addEventListener('change',draw);
$('anatomy-focus').addEventListener('click',async()=>{if(!selectedAnatomy)return;const entry=selectedAnatomy;if(entry.body==='casing')await setView('half');else{$('component-select').value=entry.body;await setView('component');}await selectAnatomy(entry.id);});
$('anatomy-copy').addEventListener('click',async()=>{if(!selectedAnatomy)return;const reference=`${selectedAnatomy.id} · ${selectedAnatomy.name}`;try{await navigator.clipboard.writeText(reference);$('anatomy-copy-status').textContent=`Copied ${reference}`;}catch{$('anatomy-copy-status').textContent=`Reference: ${reference}`;}});
function meanAirSpeed(input){const samples=input.split(',').map(v=>v.trim());if(samples.length!==3||samples.some(v=>!/^\d*\.?\d+$/.test(v)))throw Error('Enter exactly three nonnegative readings separated by commas.');const mean=samples.map(Number).reduce((total,v)=>total+v/3,0);if(!Number.isFinite(mean))throw Error('Enter finite air-speed readings.');return mean;}
$('airflow-test').addEventListener('input',()=>{$('airflow-result').textContent='';});$('airflow-test').addEventListener('submit',event=>{event.preventDefault();try{const a=meanAirSpeed($('fan-only').value),b=meanAirSpeed($('fan-with-print').value);$('airflow-result').textContent=`Fan only: ${a.toFixed(3)} m/s. With print: ${b.toFixed(3)} m/s. Change: ${(b-a).toFixed(3)} m/s.`;}catch(error){$('airflow-result').textContent=error.message;}});
try{renderer=new VegaRenderer(canvas);new ResizeObserver(()=>{const r=canvas.getBoundingClientRect();renderer.resize(r.width,r.height);draw();}).observe(canvas);let drag;canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-drag[0])*.008;tilt+=(e.clientY-drag[1])*.008;drag=[e.clientX,e.clientY];draw();});for(const name of ['pointerup','pointercancel'])canvas.addEventListener(name,()=>drag=null);canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.min(3,Math.max(.35,zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});}catch(error){$('empty-state').textContent=error.message+' Checked files can still be downloaded.';}
(async()=>{try{const state=await request('/api/state');token=state.token;latestId=state.latest;const linked=new URLSearchParams(location.hash.slice(1)).get('print');if(linked&&/^[a-f0-9]{32}$/.test(linked))await load(linked);else if(state.latest)await load(state.latest);else status('Ready. Generate the first model.');if(state.active)await follow(state.active);}catch(error){status(error.message,true);}})();

function showCoolingNetwork(data,preview){
  $('cold-network-summary').textContent=`${preview?'Preview calculation':'Saved calculation'}: ${data.total_flow_ml_s} mL/s of room-temperature air; estimated circuit pressure difference ${data.required_pressure_difference_pa.toFixed(1)} Pa. Relative mass-balance residual ${data.relative_mass_balance_residual.toExponential(2)}. Assumes unobstructed passages; check the assembly audit for interference. This is a cooling-circuit submodel, not whole-engine CFD or proof of operation.`;
  $('bell-branch-rows').replaceChildren();
  for(const edge of data.edges.filter(e=>e.group==='bell channel')){const row=document.createElement('tr');cells(row,[edge.id,edge.length_mm.toFixed(1),edge.flow_ml_s.toFixed(3),edge.reynolds.toFixed(0)]);$('bell-branch-rows').append(row);}
}
$('run-cooling-screen').addEventListener('click',async()=>{
  const button=$('run-cooling-screen');button.disabled=true;
  try{const data=await request('/api/cooling-screen',{method:'POST',headers:{'Content-Type':'application/json','X-Vega-Token':token},body:JSON.stringify({id:currentId,flow_ml_s:Number($('cold-screen-flow').value)})});showCoolingNetwork(data,true);}
  catch(error){$('cold-network-summary').textContent=error.message;}finally{button.disabled=false;}
});
