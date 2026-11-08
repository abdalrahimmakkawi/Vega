const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function viewer() {
  const draws = [];
  const gl = new Proxy({
    POINTS: 0, TRIANGLES: 4, ARRAY_BUFFER: 34962, STATIC_DRAW: 35044,
    VERTEX_SHADER: 35633, FRAGMENT_SHADER: 35632, COMPILE_STATUS: 35713,
    LINK_STATUS: 35714, DEPTH_TEST: 2929, COLOR_BUFFER_BIT: 16384,
    DEPTH_BUFFER_BIT: 256, LEQUAL: 515, FLOAT: 5126,
    createShader: () => ({}), createProgram: () => ({}), createBuffer: () => ({}),
    getShaderParameter: () => true, getProgramParameter: () => true,
    getAttribLocation: () => 0, getUniformLocation: () => ({}),
    isContextLost: () => false,
    drawArrays: (kind, first, count) => draws.push({kind, first, count}),
  }, {get(target, property) { return property in target ? target[property] : () => {}; }});
  const canvas = {dataset: {}, getContext: () => gl, addEventListener: () => {}};
  const context = {window: {}, performance: {now: () => 0}, devicePixelRatio: 1, Float32Array, Math};
  vm.runInNewContext(fs.readFileSync('web/renderer.js', 'utf8'), context);
  const renderer = new context.window.VegaRenderer(canvas);
  renderer.resize(800, 500);
  const packed = new Float32Array(3 * 3 * 6);
  for (let vertex = 0; vertex < 9; vertex++) packed[vertex * 6] = vertex / 9;
  const bodies = [
    {component_id: 'shell', group: 'shell', first_triangle: 0, triangle_count: 2, color: [1, 0, 0]},
    {component_id: 'strake', group: 'mixing', first_triangle: 2, triangle_count: 1, color: [0, 1, 0]},
  ];
  renderer.setPackedMesh(packed, {length_mm: 100, diameter_mm: 50}, 'native', bodies);
  return {renderer, draws, gl};
}

test('geometry study samples and draws every named STL component', () => {
  const {renderer, draws, gl} = viewer();
  assert.equal(renderer.studyCount, 3);
  assert.equal(renderer.studyBodies[0].point_count, 2);
  assert.equal(renderer.studyBodies[1].first_point, 2);
  renderer.render(0.5, 0.8, 1, {mode: 'study'});
  assert.deepEqual(draws.map(({kind, first, count}) => [kind, first, count]),
    [[gl.POINTS, 0, 2], [gl.POINTS, 2, 1]]);
});

test('physical-scale lock preserves pixels per millimetre across differently sized designs', () => {
  const {renderer}=viewer();
  renderer.scaleLockPxPerMm=2;
  renderer.render(0,0,1);
  const first=JSON.parse(renderer.canvas.dataset.renderStats).fitScale/renderer.dimensions.length_mm;
  renderer.dimensions={length_mm:200,diameter_mm:50};
  renderer.render(0,0,1);
  const second=JSON.parse(renderer.canvas.dataset.renderStats).fitScale/renderer.dimensions.length_mm;
  assert.equal(first,2);assert.equal(second,first);
});

test('solid and interior modes use actual triangles; interior exposes the mixer', () => {
  const {renderer, draws, gl} = viewer();
  renderer.render(0.5, 0.8, 1, {mode: 'solid'});
  assert.deepEqual(draws.map(({kind, first, count}) => [kind, first, count]),
    [[gl.TRIANGLES, 0, 6], [gl.TRIANGLES, 6, 3]]);
  draws.length = 0;
  renderer.render(0.5, 0.8, 1, {mode: 'interior'});
  assert.deepEqual(draws.map(({kind, first, count}) => [kind, first, count]),
    [[gl.TRIANGLES, 6, 3]]);
});

test('triangle inspection and quality modes draw the actual surface triangles', () => {
  const {renderer,draws,gl}=viewer();
  for(const mode of ['mesh','quality']){
    draws.length=0;renderer.render(.5,.8,1,{mode});
    assert.deepEqual(draws.map(({kind,first,count})=>[kind,first,count]),[[gl.TRIANGLES,0,6],[gl.TRIANGLES,6,3]]);
    assert.equal(JSON.parse(renderer.canvas.dataset.renderStats).mode,mode);
  }
});

test('GPU quality attributes use normalized triangle radius quality', () => {
  const {renderer}=viewer();const packed=new Float32Array(18);
  const points=[[0,0,0],[1,0,0],[.5,Math.sqrt(3)/2,0]];
  for(let j=0;j<3;j++){packed.set(points[j],j*6);packed[j*6+5]=1;}
  renderer.setPackedMesh(packed,{length_mm:1,diameter_mm:1});
  const q=JSON.parse(renderer.canvas.dataset.meshQuality);
  assert.ok(q.minimum>.99999);assert.equal(q.belowPointTwo,0);assert.equal(q.triangles,1);
});

test('interior view fits its visible hardware instead of the full duct envelope', () => {
  const {renderer}=viewer();
  renderer.setPackedMesh(new Float32Array(3*3*6),{length_mm:100,diameter_mm:50},'native',[
    {component_id:'shell',group:'shell',first_triangle:0,triangle_count:2,color:[1,0,0]},
    {component_id:'core',group:'core',first_triangle:2,triangle_count:1,color:[0,1,0]},
  ],{
    shell:[-.5,-.2,-.2,.5,.2,.2],
    core:[-.1,-.03,-.03,.1,.03,.03],
  });
  renderer.render(.5,.8,1,{mode:'solid'});
  const full=JSON.parse(renderer.canvas.dataset.renderStats);
  renderer.render(.5,.8,1,{mode:'interior'});
  const interior=JSON.parse(renderer.canvas.dataset.renderStats);
  assert.ok(interior.fitScale>full.fitScale*3);
});

test('individual component visibility changes actual draw calls and visible mesh statistics', () => {
  const {renderer,draws,gl}=viewer();
  renderer.render(.5,.8,1,{mode:'solid'});
  const all=JSON.parse(renderer.canvas.dataset.renderStats);
  assert.equal(all.visibleBodies,2);
  assert.equal(all.visibleTriangles,3);
  renderer.hiddenComponents.add('shell');
  draws.length=0;
  renderer.render(.5,.8,1,{mode:'solid'});
  const selected=JSON.parse(renderer.canvas.dataset.renderStats);
  assert.deepEqual(draws.map(({kind,first,count})=>[kind,first,count]),[[gl.TRIANGLES,6,3]]);
  assert.equal(selected.visibleBodies,1);
  assert.equal(selected.visibleTriangles,1);
});
