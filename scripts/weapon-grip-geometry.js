/* WarConquer reusable geometry fit for handheld props.
 * No expected model axes, vertex order, GLB handedness or hard-coded weapon coordinates.
 * Exported to Node for deterministic synthetic geometry tests.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WCWeaponGrip = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";
  const sub = (a,b) => [a[0]-b[0],a[1]-b[1],a[2]-b[2]];
  const add = (a,b) => [a[0]+b[0],a[1]+b[1],a[2]+b[2]];
  const mul = (a,k) => [a[0]*k,a[1]*k,a[2]*k];
  const dot = (a,b) => a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  const cross = (a,b) => [
    a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]
  ];
  const norm = a => Math.sqrt(dot(a,a));
  const unit = a => { const n=norm(a); return n>1e-9 ? mul(a,1/n) : null; };
  const centroid = points => mul(points.reduce(add,[0,0,0]),1/points.length);
  const q90 = values => {
    if (!values.length) return 0;
    values.sort((a,b) => a-b);
    return values[Math.floor((values.length-1)*.9)];
  };

  // Fit a contact frame from the actual geometry of a curved/flat rigid object.
  // Unlike a shaft, its grip may be midway between TWO functional ends.
  // This is a geometry class, not a bow/weapon-specific mounting script.
  function fitFrame(points, gripFraction) {
    const center=centroid(points);
    const cov=[0,0,0,0,0,0,0,0,0];
    for(const p of points){
      const v=sub(p,center);
      for(let i=0;i<3;i++)for(let j=0;j<3;j++)cov[i*3+j]+=v[i]*v[j];
    }
    let axis=[1,0,0];
    for(let k=0;k<50;k++){
      const next=unit([dot(cov.slice(0,3),axis),dot(cov.slice(3,6),axis),dot(cov.slice(6,9),axis)]);
      if(!next)throw Error("Degenerate frame covariance");
      axis=next;
    }
    // Stable principal axis sign, independent from model coordinate handedness.
    const dominant=axis.map(Math.abs).indexOf(Math.max(...axis.map(Math.abs)));
    if(axis[dominant]<0)axis=mul(axis,-1);
    const positions=points.map(p=>dot(sub(p,center),axis));
    const lo=Math.min(...positions),hi=Math.max(...positions),length=hi-lo;
    if(length<.001)throw Error("Degenerate frame length");
    const slice=points.filter((p,i)=>Math.abs((positions[i]-lo)/length-gripFraction)<.055);
    if(slice.length<8)throw Error("No frame geometry near the visual handhold");
    const grip=centroid(slice);
    const base=Math.abs(axis[0])<.8?[1,0,0]:[0,1,0];
    let transverse=unit(sub(base,mul(axis,dot(base,axis))));
    for(let k=0;k<48;k++){
      const raw=[dot(cov.slice(0,3),transverse),dot(cov.slice(3,6),transverse),dot(cov.slice(6,9),transverse)];
      const next=unit(sub(raw,mul(axis,dot(raw,axis))));
      if(!next)throw Error("Frame transverse direction not identifiable");
      transverse=next;
    }
    const normal=unit(cross(axis,transverse));
    const variance=v=>points.reduce((sum,p)=>{const n=dot(sub(p,center),v);return sum+n*n;},0);
    if(variance(transverse)/Math.max(1e-8,variance(normal))<1.15)
      throw Error("Frame plane ambiguous; image/GLB review required");
    return {grip,shaft:axis,blade:transverse,length,headWidthRatio:1,
      gripFractionFromButt:gripFraction,vertexCount:points.length,
      bladeMethod:"generic-frame-pca"};
  }

  function fitGrip(points, gripFraction, geometry="shaft") {
    if (!Array.isArray(points) || points.length<60 || points.some(p=>
      !Array.isArray(p) || p.length!==3 || p.some(x=>!Number.isFinite(x))))
      throw Error("Not enough valid GLB vertex positions to infer the handle");
    if (!(gripFraction>.03 && gripFraction<.75)) throw Error("Invalid vision grip fraction");
    if(geometry==="frame")return fitFrame(points,gripFraction);
    if(geometry!=="shaft" && geometry!=="axe")
      throw Error("Unsupported geometric contact class");
    const center=centroid(points);
    const bounds=[0,1,2].map(i=>[
      Math.min(...points.map(p=>p[i])),Math.max(...points.map(p=>p[i]))
    ]);
    const spans=bounds.map(([lo,hi])=>hi-lo);
    let axis=[0,0,0];
    axis[spans.indexOf(Math.max(...spans))]=1;
    // Dominant PCA eigenvector via a fixed number of matrix-vector multiplications.
    // This is orientation-invariant; diagonal shaft axes are supported.
    const cov=[0,0,0,0,0,0,0,0,0];
    for (const p of points) {
      const v=sub(p,center);
      for (let i=0;i<3;i++)for (let j=0;j<3;j++)cov[i*3+j]+=v[i]*v[j];
    }
    for (let iter=0;iter<48;iter++) {
      const next=unit([dot(cov.slice(0,3),axis),dot(cov.slice(3,6),axis),
        dot(cov.slice(6,9),axis)]);
      if (!next) throw Error("Degenerate geometry covariance");
      axis=next;
    }
    const projection=points.map(p=>dot(sub(p,center),axis));
    const pMin=Math.min(...projection),pMax=Math.max(...projection),length=pMax-pMin;
    if (!(length>.001))throw Error("Degenerate GLB axis");
    const radial=points.map((p,i)=>{
      const delta=sub(p,center);
      const r=sub(delta,mul(axis,projection[i]));
      return norm(r);
    });
    const endWidth=which => {
      const selected=[];
      for(let i=0;i<points.length;i++){
        const t=(projection[i]-pMin)/length;
        if(which==="min" ? t<=.23 : t>=.77)selected.push(radial[i]);
      }
      return q90(selected);
    };
    const nearMin=endWidth("min"),nearMax=endWidth("max");
    const headAtMax=nearMax>=nearMin;
    const spreadRatio=Math.max(nearMax,nearMin)/Math.max(.000001,Math.min(nearMax,nearMin));
    if (spreadRatio<1.23)
      throw Error("Handle and functional head not distinguishable in 3D; review required");
    const coarseShaft=headAtMax ? axis : mul(axis,-1);
    const coarseDistance=projection.map(t=>headAtMax?t-pMin:pMax-t);
    // The blade skews global PCA. Refit the *handle itself* before locating
    // its centerline; otherwise the axe head can pull the grip toward the blade.
    const shaftVertices=points.filter((p,i)=>
      coarseDistance[i]>=length*.07 && coarseDistance[i]<=length*.57);
    if(shaftVertices.length<40)throw Error("Not enough handle vertices to fit centerline");
    const handleCenter=centroid(shaftVertices);
    const shaftCov=[0,0,0,0,0,0,0,0,0];
    for(const p of shaftVertices){
      const v=sub(p,handleCenter);
      for(let i=0;i<3;i++)for(let j=0;j<3;j++)shaftCov[i*3+j]+=v[i]*v[j];
    }
    let signed=coarseShaft;
    for(let iter=0;iter<40;iter++){
      const next=unit([dot(shaftCov.slice(0,3),signed),
        dot(shaftCov.slice(3,6),signed),dot(shaftCov.slice(6,9),signed)]);
      if(!next)throw Error("Degenerate handle geometry");
      signed=next;
    }
    if(dot(signed,coarseShaft)<0)signed=mul(signed,-1);
    const onShaft=points.map(p=>dot(sub(p,handleCenter),signed));
    const shaftButt=Math.min(...onShaft);
    const trueLength=Math.max(...onShaft)-shaftButt;
    const distance=onShaft.map(t=>t-shaftButt);
    const gripDistance=trueLength*gripFraction*.8;
    const shaftCandidates=[];
    for(let i=0;i<points.length;i++)
      if(Math.abs(distance[i]-gripDistance)<trueLength*.035)shaftCandidates.push(points[i]);
    if(shaftCandidates.length<8)throw Error("No shaft vertices near the grip");
    const radialCenter=centroid(shaftCandidates);
    const grip=add(radialCenter,mul(signed,gripDistance-(dot(sub(radialCenter,handleCenter),signed)-shaftButt)));
    const headCandidates=[];
    for(let i=0;i<points.length;i++)
      if(distance[i]>trueLength*.76)headCandidates.push(points[i]);
    if(headCandidates.length<8)throw Error("No discernible weapon head vertices");
    const headCenter=centroid(headCandidates);
    const transverse=sub(sub(headCenter,grip),mul(signed,dot(sub(headCenter,grip),signed)));
    let blade=unit(transverse);
    let bladeMethod="asymmetric-head-centroid";
    if(!blade || norm(transverse)<trueLength*.02) {
      // A double-edged axe may be centred on the shaft. Its silhouette still
      // has an oriented blade plane: solve the strongest perpendicular PCA
      // direction within the head, not the centroid direction.
      bladeMethod="head-transverse-covariance";
      const base=Math.abs(signed[0])<.8 ? [1,0,0] : [0,1,0];
      let candidate=unit(sub(base,mul(signed,dot(base,signed))));
      const headCov=[0,0,0,0,0,0,0,0,0];
      for(const p of headCandidates){
        const d=sub(p,headCenter);
        const v=sub(d,mul(signed,dot(d,signed)));
        for(let i=0;i<3;i++)for(let j=0;j<3;j++)headCov[i*3+j]+=v[i]*v[j];
      }
      for(let iter=0;iter<45;iter++) {
        const raw=[dot(headCov.slice(0,3),candidate),dot(headCov.slice(3,6),candidate),
          dot(headCov.slice(6,9),candidate)];
        const projected=sub(raw,mul(signed,dot(raw,signed)));
        const next=unit(projected);
        if(!next)throw Error("Weapon head has no dominant transverse plane");
        candidate=next;
      }
      const other=unit(cross(signed,candidate));
      const variance=vector=>headCandidates.reduce((sum,p)=>{
        const n=dot(sub(p,headCenter),vector);
        return sum+n*n;
      },0);
      const anisotropy=variance(candidate)/Math.max(1e-8,variance(other));
      if(anisotropy<1.3)
        throw Error("Weapon head is transversely symmetric: edge plane indeterminate");
      // Pick a stable sign from its furthest extent; for a true double blade
      // either sign presents an equivalent cutting direction.
      const projections=headCandidates.map(p=>dot(sub(p,headCenter),candidate));
      const extreme=Math.max(...projections)+Math.min(...projections);
      blade=extreme<0 ? mul(candidate,-1) : candidate;
    }
    return {grip,shaft:signed,blade,length:trueLength,headWidthRatio:spreadRatio,
      gripFractionFromButt:gripFraction,vertexCount:points.length,bladeMethod};
  }
  return {fitGrip,cross,dot,unit,sub,mul,add,norm};
});
