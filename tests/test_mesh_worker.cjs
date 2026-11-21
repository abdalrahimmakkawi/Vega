const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function parse(buffer,length=10,bodies=[],smoothBuffer,extensionBuffer,extensionNormals,extraChunks=[]){let response;const self={postMessage:value=>response=value};vm.runInNewContext(fs.readFileSync('web/mesh-worker.js','utf8'),{self,Float32Array,Int8Array,DataView,Math,Number,Error});self.onmessage({data:{buffer,length,bodies,smoothBuffer,extensionBuffer,extensionNormals,extraChunks}});return response;}
function triangle(){const b=new ArrayBuffer(134),d=new DataView(b);d.setUint32(80,1,true);d.setFloat32(88,1,true);const v=[[1,2,0],[2,2,0],[1,3,0]];for(let j=0;j<3;j++)for(let k=0;k<3;k++)d.setFloat32(96+j*12+k*4,v[j][k],true);return b;}
test('parses a binary STL triangle into the centered GPU coordinate system',()=>{const result=parse(triangle());assert.equal(result.triangles,1);assert.equal(result.packed.length,18);assert.equal(result.packed[0],0);assert.ok(Math.abs(result.packed[1]-.1)<1e-6);assert.ok(Math.abs(result.packed[2]-.2)<1e-6);});
test('combines immutable base and extension chunks without losing component ranges or normals',()=>{
  const extension=triangle(),view=new DataView(extension);
  for(let j=0;j<3;j++)view.setFloat32(104+j*12,20,true);
  const normals=new Int8Array([127,0,0,127,0,0,127,0,0]).buffer;
  const bodies=[{component_id:'base',first_triangle:0,triangle_count:1},{component_id:'connector',first_triangle:1,triangle_count:1}];
  const result=parse(triangle(),20,bodies,undefined,extension,normals);
  assert.equal(result.triangles,2);assert.equal(result.centerZ,10);assert.equal(result.rangeAudit.complete,true);
  assert.equal(result.packed[0],-.5);assert.equal(result.packed[18],.5);
  assert.deepEqual(Array.from(result.packed.slice(21,24)),[0,1,0]);
  assert.match(parse(triangle(),20,bodies,undefined,extension,new ArrayBuffer(8)).error,/normals do not match/);
  assert.match(parse(triangle(),20,bodies,undefined,new ArrayBuffer(10)).error,/truncated/);
});
test('smooth normals change lighting without changing geometry coordinates',()=>{const flat=parse(triangle()),smooth=parse(triangle(),10,[],new Int8Array([127,0,0,127,0,0,127,0,0]).buffer);for(let i=0;i<3;i++){assert.deepEqual(Array.from(smooth.packed.slice(i*6,i*6+3)),Array.from(flat.packed.slice(i*6,i*6+3)));assert.deepEqual(Array.from(smooth.packed.slice(i*6+3,i*6+6)),[0,1,0]);}assert.match(parse(triangle(),10,[],new ArrayBuffer(8)).error,/normals do not match/);});
test('centers an assembly spanning negative and positive axial coordinates',()=>{const b=triangle(),v=new DataView(b);v.setFloat32(104,-20,true);v.setFloat32(116,10,true);v.setFloat32(128,20,true);const result=parse(b,40);assert.ok(Math.abs(result.packed[0]+.5)<1e-6);assert.ok(Math.abs(result.packed[6]-.25)<1e-6);assert.ok(Math.abs(result.packed[12]-.5)<1e-6);});
test('rejects truncated and inconsistent STL instead of allocating arbitrary geometry',()=>{assert.match(parse(new ArrayBuffer(20)).error,/truncated/);const b=triangle();new DataView(b).setUint32(80,4000001,true);assert.match(parse(b).error,/oversized/);});
test('rejects nonfinite coordinates',()=>{const b=triangle();new DataView(b).setFloat32(96,NaN,true);assert.match(parse(b).error,/Nonfinite/);});
test('rejects invalid display scales before producing GPU infinities',()=>{for(const scale of [0,-1,NaN,Infinity])assert.match(parse(triangle(),scale).error,/length/);});
test('rejects empty STL instead of returning infinite bounds',()=>{assert.match(parse(new ArrayBuffer(84)).error,/Unsupported/);});
test('returns exact normalized bounds for a named mesh body',()=>{const result=parse(triangle(),10,[{component_id:'core',first_triangle:0,triangle_count:1}]);const box=result.bounds.core;assert.ok(Math.abs(box[1]-.1)<1e-6);assert.ok(Math.abs(box[4]-.2)<1e-6);assert.ok(Math.abs(box[5]-.3)<1e-6);});
test('requires unique component ranges to partition every STL triangle exactly once',()=>{const b=new ArrayBuffer(184),d=new DataView(b);d.setUint32(80,2,true);for(let i=0;i<2;i++){const base=84+i*50;for(let j=0;j<3;j++){d.setFloat32(base+12+j*12,1+j,true);d.setFloat32(base+16+j*12,2,true);d.setFloat32(base+20+j*12,i,true);}}const bodies=[{component_id:'tank',first_triangle:0,triangle_count:1},{component_id:'chamber',first_triangle:1,triangle_count:1}];const result=parse(b,10,bodies);assert.equal(result.rangeAudit.complete,true);assert.equal(result.rangeAudit.coveredTriangles,2);assert.match(parse(b,10,[bodies[0]]).error,/cover 1 of 2/);assert.match(parse(b,10,[bodies[0],{...bodies[1],first_triangle:0}]).error,/missing, overlapping/);});

test('combines three assembly layers with one complete component manifest',()=>{
 const bodies=['base','mounts','cooling'].map((id,i)=>({component_id:id,first_triangle:i,triangle_count:1}));
 const result=parse(triangle(),10,bodies,undefined,undefined,undefined,[{buffer:triangle()},{buffer:triangle()}]);
 assert.equal(result.triangles,3);assert.equal(result.bodyCount,3);assert.equal(result.rangeAudit.complete,true);
});
