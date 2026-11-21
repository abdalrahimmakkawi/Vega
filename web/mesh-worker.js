/* Parse native binary STL away from the UI thread; transfer the packed GPU buffer. */
self.onmessage=({data:{buffer,length,bodies=[],smoothBuffer,extensionBuffer,extensionNormals,extraChunks=[]}})=>{
  try{
    if(!Number.isFinite(length)||length<=0)throw Error('Mesh display length must be finite and positive.');
    const chunks=[{view:new DataView(buffer),smooth:smoothBuffer?new Int8Array(smoothBuffer):null}];
    if(extensionBuffer)chunks.push({view:new DataView(extensionBuffer),smooth:extensionNormals?new Int8Array(extensionNormals):null});
    for(const chunk of extraChunks)chunks.push({view:new DataView(chunk.buffer),smooth:chunk.normals?new Int8Array(chunk.normals):null});
    let count=0;
    for(const chunk of chunks){
      if(chunk.view.byteLength<84)throw Error('STL header is truncated.');
      chunk.first=count;chunk.count=chunk.view.getUint32(80,true);count+=chunk.count;
      if(!chunk.count||count>6_100_000||84+chunk.count*50!==chunk.view.byteLength)throw Error('Unsupported or oversized binary STL.');
      if(chunk.smooth&&chunk.smooth.length!==chunk.count*9)throw Error('Smooth normals do not match the checked scene.');
    }
    let rangeEnd=0;const identities=new Set();
    for(const body of bodies){
      if(!body.component_id||identities.has(body.component_id))throw Error('Component manifest contains a missing or duplicate identity.');
      identities.add(body.component_id);
      if(!Number.isInteger(body.first_triangle)||!Number.isInteger(body.triangle_count)||body.first_triangle!==rangeEnd||body.triangle_count<=0)
        throw Error(`Component ${body.component_id} has a missing, overlapping or empty triangle range.`);
      rangeEnd+=body.triangle_count;
    }
    if(bodies.length&&rangeEnd!==count)throw Error(`Component ranges cover ${rangeEnd} of ${count} STL triangles.`);
    let minZ=Infinity,maxZ=-Infinity;
    for(const chunk of chunks)for(let i=0;i<chunk.count;i++)for(let j=0;j<3;j++){
      const z=chunk.view.getFloat32(84+i*50+12+j*12+8,true);
      if(!Number.isFinite(z))throw Error('Nonfinite STL coordinate.');
      minZ=Math.min(minZ,z);maxZ=Math.max(maxZ,z);
    }
    const centerZ=(minZ+maxZ)/2;
    const packed=new Float32Array(count*18);let out=0;
    const bounds={};let bodyIndex=0;
    for(const body of bodies)bounds[body.component_id]=[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity];
    let chunkIndex=0;
    for(let i=0;i<count;i++){
      while(i>=chunks[chunkIndex].first+chunks[chunkIndex].count)chunkIndex++;
      const {view,smooth,first}=chunks[chunkIndex],local=i-first;
      while(bodyIndex<bodies.length && i>=bodies[bodyIndex].first_triangle+bodies[bodyIndex].triangle_count)bodyIndex++;
      const box=bodyIndex<bodies.length && i>=bodies[bodyIndex].first_triangle?bounds[bodies[bodyIndex].component_id]:null;
      const base=84+local*50,nx=view.getFloat32(base,true),ny=view.getFloat32(base+4,true),nz=view.getFloat32(base+8,true),norm=Math.hypot(nx,ny,nz)||1;
      for(let j=0;j<3;j++){const b=base+12+j*12,x=view.getFloat32(b,true),y=view.getFloat32(b+4,true),z=view.getFloat32(b+8,true);
        if(!Number.isFinite(x+y+z+nx+ny+nz))throw Error('Nonfinite STL coordinate.');
        const px=(z-centerZ)/length,py=x/length,pz=y/length;
        packed[out++]=px;packed[out++]=py;packed[out++]=pz;
        if(smooth){const k=local*9+j*3;packed[out++]=smooth[k+2]/127;packed[out++]=smooth[k]/127;packed[out++]=smooth[k+1]/127;}
        else{packed[out++]=nz/norm;packed[out++]=nx/norm;packed[out++]=ny/norm;}
        if(box){box[0]=Math.min(box[0],px);box[1]=Math.min(box[1],py);box[2]=Math.min(box[2],pz);
          box[3]=Math.max(box[3],px);box[4]=Math.max(box[4],py);box[5]=Math.max(box[5],pz);}
      }
    }
    self.postMessage({packed,triangles:count,centerZ,bounds,bodyCount:bodies.length,rangeAudit:{complete:!bodies.length||rangeEnd===count,coveredTriangles:rangeEnd,meshTriangles:count}},[packed.buffer]);
  }catch(error){self.postMessage({error:error.message});}
};
