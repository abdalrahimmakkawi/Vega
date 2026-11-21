/* GPU orbit viewer. Geometry is uploaded once; interaction changes uniforms only. */
(() => {
  'use strict';
  class VegaRenderer {
    constructor(canvas) {
      this.canvas = canvas;
      const gl = this.gl = canvas.getContext('webgl', {alpha:false, antialias:true, preserveDrawingBuffer:false});
      if (!gl) throw Error('WebGL is unavailable in this browser. Engineering section remains available.');
      const vertex = `attribute vec3 position; attribute vec3 normal; attribute vec2 meshInfo;
        uniform mat3 rotation; uniform vec3 focus; uniform vec3 componentOffset; uniform vec2 viewport; uniform float scale; uniform bool pointMode;
        varying vec3 shadeNormal; varying vec3 localPosition; varying vec3 barycentric; varying float triangleQuality;
        void main(){ vec3 p=rotation*(position+componentOffset-focus); shadeNormal=rotation*normal;localPosition=position+componentOffset;
          triangleQuality=meshInfo.x;barycentric=vec3(meshInfo.y<0.5?1.0:0.0,(meshInfo.y>0.5&&meshInfo.y<1.5)?1.0:0.0,meshInfo.y>1.5?1.0:0.0);
          gl_Position=vec4(p.x*scale*2.0/viewport.x,-p.y*scale*2.0/viewport.y,-p.z*0.5,1.0);
          gl_PointSize=pointMode?2.5:1.0; }`;
      const fragment = `precision mediump float; varying vec3 shadeNormal; varying vec3 localPosition; varying vec3 barycentric; varying float triangleQuality;
        uniform vec3 color; uniform bool cutaway; uniform bool unlit; uniform bool pointMode; uniform vec2 axialRange; uniform bool highlighted; uniform bool wireMode; uniform bool qualityMode;
        void main(){if(cutaway && localPosition.z>0.0) discard;
          if(pointMode && distance(gl_PointCoord,vec2(0.5))>0.49) discard;
          float light=unlit?1.0:0.40+0.60*max(dot(normalize(shadeNormal),normalize(vec3(0.2,-0.5,1.0))),0.0);
          vec3 tint=(highlighted && localPosition.x>=axialRange.x && localPosition.x<=axialRange.y)?vec3(0.88,0.51,0.16):color;
          if(qualityMode){float q=clamp(triangleQuality,0.0,1.0);tint=q<0.3?mix(vec3(0.88,0.12,0.06),vec3(0.98,0.72,0.16),q/0.3):mix(vec3(0.98,0.72,0.16),vec3(0.12,0.63,0.46),clamp((q-0.3)/0.5,0.0,1.0));light=1.0;}
          if(wireMode&&min(barycentric.x,min(barycentric.y,barycentric.z))<0.025){tint=vec3(0.07,0.14,0.18);light=1.0;}
          gl_FragColor=vec4(tint*light,1.0);}`;
      const compile = (type, source) => {
        const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
        if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(shader));
        return shader;
      };
      const program=this.program=gl.createProgram(),vs=compile(gl.VERTEX_SHADER,vertex),fs=compile(gl.FRAGMENT_SHADER,fragment);
      gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);
      if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
      gl.deleteShader(vs);gl.deleteShader(fs);
      this.attributes={position:gl.getAttribLocation(program,'position'),normal:gl.getAttribLocation(program,'normal')};
      this.uniforms=Object.fromEntries(['rotation','focus','componentOffset','viewport','scale','color','cutaway','unlit','pointMode','axialRange','highlighted','wireMode','qualityMode'].map(n=>[n,gl.getUniformLocation(program,n)]));
      this.meshInfoAttribute=gl.getAttribLocation(program,'meshInfo');this.meshInfoBuffer=gl.createBuffer();
      this.meshBuffer=gl.createBuffer();this.studyBuffer=gl.createBuffer();this.routeBuffer=gl.createBuffer();this.meshCount=0;this.studyCount=0;this.routeCount=0;
      this.width=1;this.height=1;this.frameTimes=[];
      canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();canvas.dataset.renderer='context-lost';});
    }
    setMesh(mesh,dimensions,source='envelope') {
      const L=dimensions.length_mm,vertices=mesh.vertices,triangles=mesh.triangles;
      let minZ=Infinity,maxZ=-Infinity;for(const v of vertices){minZ=Math.min(minZ,v[2]);maxZ=Math.max(maxZ,v[2]);}const centerZ=(minZ+maxZ)/2;
      this.centerZ=centerZ;
      const data=new Float32Array(triangles.length*18);let offset=0;
      for(const t of triangles){const p=vertices[t[0]],q=vertices[t[1]],r=vertices[t[2]];
        const ux=q[0]-p[0],uy=q[1]-p[1],uz=q[2]-p[2],vx=r[0]-p[0],vy=r[1]-p[1],vz=r[2]-p[2];
        const nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx,len=Math.hypot(nx,ny,nz)||1;
        for(const i of t){const v=vertices[i];data[offset++]=(v[2]-centerZ)/L;data[offset++]=v[0]/L;data[offset++]=v[1]/L;
          data[offset++]=nz/len;data[offset++]=nx/len;data[offset++]=ny/len;}
      }
      this.setPackedMesh(data,dimensions,source,mesh.bodies||null);
    }
    setPackedMesh(data,dimensions,source='native',bodies=null,bodyBounds=null) {
      const gl=this.gl;this.dimensions=dimensions;this.meshCount=data.length/6;this.source=source;
      if(!bodyBounds&&bodies?.length){
        bodyBounds={};
        for(const body of bodies){const box=[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity];
          for(let i=body.first_triangle*18;i<(body.first_triangle+body.triangle_count)*18;i+=6)
            for(let axis=0;axis<3;axis++){box[axis]=Math.min(box[axis],data[i+axis]);box[axis+3]=Math.max(box[axis+3],data[i+axis]);}
          bodyBounds[body.component_id]=box;
        }
      }
      this.bodies=bodies;this.bodyBounds=bodyBounds;this.hiddenComponents||=new Set();
      this.frameTimes=[];
      gl.bindBuffer(gl.ARRAY_BUFFER,this.meshBuffer);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);
      const info=new Float32Array(this.meshCount*2);let qMin=1,qSum=0,qPoor=0;
      for(let t=0;t<this.meshCount/3;t++){
        const a=t*18,b=a+6,c=a+12;
        const ux=data[b]-data[a],uy=data[b+1]-data[a+1],uz=data[b+2]-data[a+2],vx=data[c]-data[a],vy=data[c+1]-data[a+1],vz=data[c+2]-data[a+2];
        const nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;
        const l0=Math.hypot(ux,uy,uz),l1=Math.hypot(vx,vy,vz),l2=Math.hypot(vx-ux,vy-uy,vz-uz),s=(l0+l1+l2)/2;
        const q=Math.min(1,Math.max(0,2*(nx*nx+ny*ny+nz*nz)/(s*l0*l1*l2)||0));
        qMin=Math.min(qMin,q);qSum+=q;if(q<.2)qPoor++;
        for(let j=0;j<3;j++){info[t*6+j*2]=q;info[t*6+j*2+1]=j;}
      }
      gl.bindBuffer(gl.ARRAY_BUFFER,this.meshInfoBuffer);gl.bufferData(gl.ARRAY_BUFFER,info,gl.STATIC_DRAW);
      this.canvas.dataset.meshQuality=JSON.stringify({minimum:qMin,mean:qSum/(this.meshCount/3),belowPointTwo:qPoor,triangles:this.meshCount/3,metric:'2r/R'});
      // The study view samples native STL vertices by component. It is a view
      // of the saved geometry, so it follows every new run and stays cheap to orbit.
      const spans=bodies?.length?bodies:[{component_id:'all',first_triangle:0,triangle_count:this.meshCount/3}];
      const points=[],studyBodies=[];
      for(const body of spans){const first=points.length/6,step=Math.max(1,Math.ceil(body.triangle_count/4500));
        for(let t=body.first_triangle;t<body.first_triangle+body.triangle_count;t+=step){const offset=t*18;
          for(let k=0;k<6;k++)points.push(data[offset+k]);
        }
        studyBodies.push({...body,first_point:first,point_count:points.length/6-first});
      }
      this.studyBodies=studyBodies;this.studyCount=points.length/6;
      gl.bindBuffer(gl.ARRAY_BUFFER,this.studyBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(points),gl.STATIC_DRAW);
      this.canvas.dataset.meshSource=source;this.canvas.dataset.triangles=String(this.meshCount/3);
      this.canvas.dataset.studyPoints=String(this.studyCount);
    }
    clear(){this.meshCount=0;this.studyCount=0;this.routeCount=0;this.highlight=null;this.highlightComponent=null;this.bodies=null;this.bodyBounds=null;this.studyBodies=null;this.hiddenGroups=new Set();this.hiddenComponents=new Set();this.isolatedComponent=null;}
    dispose(){const gl=this.gl;gl.deleteBuffer(this.meshBuffer);gl.deleteBuffer(this.studyBuffer);gl.deleteBuffer(this.routeBuffer);gl.deleteBuffer(this.meshInfoBuffer);gl.deleteProgram(this.program);gl.getExtension('WEBGL_lose_context')?.loseContext();}
    setHighlight(part,dimensions){this.highlight=part?part.axial_mm.map(z=>(z-(this.centerZ??dimensions.length_mm/2))/dimensions.length_mm):null;this.highlightComponent=part?.id||null;}
    setRoutes(lines, dimensions, side=0) {
      const data=[];this.routeKinds=[];
      for(const line of lines){
        const first=data.length/6;
        for(let i=1;i<line.points.length;i++){
          let a=line.points[i-1],b=line.points[i];
          if(side && side*a[1]<0 && side*b[1]<0)continue;
          if(side && side*a[1]*side*b[1]<0){
            const t=-a[1]/(b[1]-a[1]),p=a.map((v,k)=>v+t*(b[k]-v));
            if(side*a[1]<0)a=p;else b=p;
          }
          for(const p of [a,b])data.push((p[2]-this.centerZ)/dimensions.length_mm,p[0]/dimensions.length_mm,p[1]/dimensions.length_mm,0,0,1);
        }
        this.routeKinds.push({kind:line.kind,first,count:data.length/6-first});
      }
      this.routeCount=data.length/6;
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.routeBuffer);
      this.gl.bufferData(this.gl.ARRAY_BUFFER,new Float32Array(data),this.gl.STATIC_DRAW);
    }
    resize(w,h) {
      this.width=w;this.height=h;const dpr=Math.min(devicePixelRatio||1,2),pw=Math.max(1,Math.round(w*dpr)),ph=Math.max(1,Math.round(h*dpr));
      if(this.canvas.width!==pw||this.canvas.height!==ph){this.canvas.width=pw;this.canvas.height=ph;}
      this.gl.viewport(0,0,pw,ph);
    }
    projectWorld(point,componentId){
      const state=this.projection;if(!state)return null;
      const length=this.dimensions.length_mm,offset=this.componentOffsets?.[componentId]||[0,0,0];
      const p=[(point[2]-this.centerZ)/length,point[0]/length,point[1]/length].map((v,i)=>v+offset[i]-state.focus[i]);
      return {x:this.width/2+(state.cy*p[0]-state.sy*p[1])*state.scale,
        y:this.height/2+(-state.st*state.sy*p[0]-state.st*state.cy*p[1]+state.ct*p[2])*state.scale};
    }
    bind(buffer){const gl=this.gl;gl.bindBuffer(gl.ARRAY_BUFFER,buffer);for(const [name,offset] of [['position',0],['normal',12]]){const loc=this.attributes[name];gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,24,offset);}}
    render(yaw,tilt,zoom,{cutaway=false,routes=true,mode='solid'}={}) {
      const started=performance.now(),gl=this.gl,u=this.uniforms;
      const sectionable=['solid','mesh','quality'].includes(mode);
      if(gl.isContextLost())return;
      if(mode==='study')gl.clearColor(.075,.086,.077,1);else gl.clearColor(.94,.96,.97,1);
      gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);if(!this.meshCount)return;
      gl.useProgram(this.program);const cy=Math.cos(yaw),sy=Math.sin(yaw),ct=Math.cos(tilt),st=Math.sin(tilt);
      gl.uniformMatrix3fv(u.rotation,false,new Float32Array([cy,-st*sy,ct*sy,-sy,-st*cy,ct*cy,0,ct,st]));
      gl.uniform2f(u.viewport,this.width,this.height);
      const d=this.dimensions;let scale=Math.min((this.width-55)/d.length_mm,(this.height-65)/(d.diameter_mm*1.8))*d.length_mm*zoom;
      let focus=[0,0,0];
      if(this.bodyBounds){
        const box=[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity];let visible=0;
        for(const body of this.bodies||[]){
          if(this.hiddenGroups?.has(body.group)||this.hiddenComponents?.has(body.component_id)||(mode==='interior'&&['shell','frame'].includes(body.group))||
             (this.isolatedComponent&&body.component_id!==this.isolatedComponent))continue;
          const raw=this.bodyBounds[body.component_id];if(!raw)continue;visible++;
          const offset=this.componentOffsets?.[body.component_id]||[0,0,0],b=raw.map((value,i)=>value+offset[i%3]);
          for(let axis=0;axis<3;axis++){box[axis]=Math.min(box[axis],b[axis]);box[axis+3]=Math.max(box[axis+3],b[axis+3]);}
        }
        if(visible){
          focus=[(box[0]+box[3])/2,(box[1]+box[4])/2,(box[2]+box[5])/2];
          let xlo=Infinity,xhi=-Infinity,ylo=Infinity,yhi=-Infinity;
          for(const x of [box[0],box[3]])for(const y of [box[1],box[4]])for(const z of [box[2],box[5]]){
            const px=cy*x-sy*y,py=-st*sy*x-st*cy*y+ct*z;
            xlo=Math.min(xlo,px);xhi=Math.max(xhi,px);ylo=Math.min(ylo,py);yhi=Math.max(yhi,py);
          }
          scale=Math.min((this.width-75)/Math.max(xhi-xlo,.015),(this.height-75)/Math.max(yhi-ylo,.015))*zoom;
        }
      }
      if(this.scaleLockPxPerMm>0)scale=this.scaleLockPxPerMm*d.length_mm*zoom;
      this.projection={cy,sy,ct,st,focus,scale};
      gl.uniform3f(u.focus,...focus);gl.uniform1f(u.scale,scale);gl.uniform3f(u.color,.48,.65,.40);gl.uniform1i(u.cutaway,cutaway && sectionable);gl.uniform1i(u.unlit,mode==='study');gl.uniform1i(u.pointMode,mode==='study');gl.uniform1i(u.wireMode,mode==='mesh');gl.uniform1i(u.qualityMode,mode==='quality');
      gl.uniform1i(u.highlighted,!!this.highlight);gl.uniform2f(u.axialRange,...(this.highlight||[0,0]));
      if(mode==='study')gl.disable(gl.DEPTH_TEST);else{gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);}
      this.bind(mode==='study'?this.studyBuffer:this.meshBuffer);
      gl.bindBuffer(gl.ARRAY_BUFFER,this.meshInfoBuffer);gl.enableVertexAttribArray(this.meshInfoAttribute);gl.vertexAttribPointer(this.meshInfoAttribute,2,gl.FLOAT,false,8,0);
      const palette={chamber:[.48,.65,.40],convergent:[.76,.51,.31],nozzle:[.39,.57,.56]};
      const bodies=mode==='study'?this.studyBodies:this.bodies;
      let visibleBodies=0,visibleTriangles=0;
      gl.uniform3f(u.componentOffset,0,0,0);
      if(bodies){for(const body of bodies){
        if(this.hiddenGroups?.has(body.group)||this.hiddenComponents?.has(body.component_id)||(mode==='interior' && ['shell','frame'].includes(body.group)) || (this.isolatedComponent && body.component_id!==this.isolatedComponent))continue;
        visibleBodies++;visibleTriangles+=body.triangle_count||0;
        gl.uniform3f(u.componentOffset,...(this.componentOffsets?.[body.component_id]||[0,0,0]));
        gl.uniform1i(u.cutaway,sectionable && ((cutaway && !['core','frame','mounts'].includes(body.group)) || this.cutawayComponents?.has(body.component_id)));
        gl.uniform3fv(u.color,body.color||palette[body.component_id]||[.81,.53,.32]);gl.uniform1i(u.highlighted,!!this.highlight && body.component_id===this.highlightComponent);
        if(mode==='study')gl.drawArrays(gl.POINTS,body.first_point,body.point_count);
        else gl.drawArrays(gl.TRIANGLES,body.first_triangle*3,body.triangle_count*3);
      }}else gl.drawArrays(gl.TRIANGLES,0,this.meshCount);
      gl.uniform3f(u.componentOffset,0,0,0);
      if(routes&&this.routeCount){gl.disable(gl.DEPTH_TEST);gl.uniform1i(u.cutaway,false);gl.uniform1i(u.unlit,true);gl.uniform1i(u.wireMode,false);gl.uniform1i(u.qualityMode,false);gl.disableVertexAttribArray(this.meshInfoAttribute);gl.vertexAttrib2f(this.meshInfoAttribute,1,0);this.bind(this.routeBuffer);
        gl.uniform1i(u.highlighted,false);
        for(const line of this.routeKinds){if(line.kind==='gas')gl.uniform3f(u.color,.85,.34,.12);else if(line.kind==='collector')gl.uniform3f(u.color,.12,.48,.85);else gl.uniform3f(u.color,.05,.62,.62);gl.drawArrays(gl.LINES,line.first,line.count);}
      }
      this.frameTimes.push(performance.now()-started);if(this.frameTimes.length>90)this.frameTimes.shift();
      const sorted=this.frameTimes.slice().sort((a,b)=>a-b);
      this.canvas.dataset.renderStats=JSON.stringify({renderer:'WebGL',source:this.source,mode,triangles:this.meshCount/3,visibleBodies,visibleTriangles,studyPoints:this.studyCount,fitCenter:focus,fitScale:scale,frames:this.frameTimes.length,medianCpuMs:sorted[Math.floor(sorted.length/2)],lastCpuMs:this.frameTimes[this.frameTimes.length-1]});
      this.canvas.dataset.renderer='webgl';
    }
  }
  window.VegaRenderer=VegaRenderer;
})();
