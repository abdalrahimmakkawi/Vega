/* Parse native binary STL away from the UI thread; transfer the packed GPU buffer. */
self.onmessage=({data:{buffer,length,bodies=[]}})=>{
  try{
    if(!Number.isFinite(length)||length<=0)throw Error('Mesh display length must be finite and positive.');
    const view=new DataView(buffer);if(view.byteLength<84)throw Error('STL header is truncated.');
    const count=view.getUint32(80,true);if(!count||count>4000000||84+count*50!==view.byteLength)throw Error('Unsupported or oversized binary STL.');
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
    for(let i=0;i<count;i++)for(let j=0;j<3;j++){
      const z=view.getFloat32(84+i*50+12+j*12+8,true);
      if(!Number.isFinite(z))throw Error('Nonfinite STL coordinate.');
      minZ=Math.min(minZ,z);maxZ=Math.max(maxZ,z);
    }
    const centerZ=(minZ+maxZ)/2;
    const packed=new Float32Array(count*18);let out=0;
    const bounds={};let bodyIndex=0;
    for(const body of bodies)bounds[body.component_id]=[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity];
    for(let i=0;i<count;i++){
      while(bodyIndex<bodies.length && i>=bodies[bodyIndex].first_triangle+bodies[bodyIndex].triangle_count)bodyIndex++;
      const box=bodyIndex<bodies.length && i>=bodies[bodyIndex].first_triangle?bounds[bodies[bodyIndex].component_id]:null;
      const base=84+i*50,nx=view.getFloat32(base,true),ny=view.getFloat32(base+4,true),nz=view.getFloat32(base+8,true),norm=Math.hypot(nx,ny,nz)||1;
      for(let j=0;j<3;j++){const b=base+12+j*12,x=view.getFloat32(b,true),y=view.getFloat32(b+4,true),z=view.getFloat32(b+8,true);
        if(!Number.isFinite(x+y+z+nx+ny+nz))throw Error('Nonfinite STL coordinate.');
        const px=(z-centerZ)/length,py=x/length,pz=y/length;
        packed[out++]=px;packed[out++]=py;packed[out++]=pz;
        packed[out++]=nz/norm;packed[out++]=nx/norm;packed[out++]=ny/norm;
        if(box){box[0]=Math.min(box[0],px);box[1]=Math.min(box[1],py);box[2]=Math.min(box[2],pz);
          box[3]=Math.max(box[3],px);box[4]=Math.max(box[4],py);box[5]=Math.max(box[5],pz);}
      }
    }
    self.postMessage({packed,triangles:count,centerZ,bounds,bodyCount:bodies.length,rangeAudit:{complete:!bodies.length||rangeEnd===count,coveredTriangles:rangeEnd,meshTriangles:count}},[packed.buffer]);
  }catch(error){self.postMessage({error:error.message});}
};
