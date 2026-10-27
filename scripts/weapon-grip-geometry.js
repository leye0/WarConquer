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

  function fitGrip(points, gripFraction, category="axe") {
    if (!Array.isArray(points) || points.length<60 || points.some(p=>
      !Array.isArray(p) || p.length!==3 || p.some(x=>!Number.isFinite(x))))
      throw Error("Not enough valid GLB vertex positions to infer the handle");
    if (!(gripFraction>.03 && gripFraction<.65)) throw Error("Invalid vision grip fraction");
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
    if (category==="axe" && spreadRatio<1.23)
      throw Error("Axe head not distinguishable from handle in 3D; manual review required");
    const signed=headAtMax ? axis : mul(axis,-1); // butt -> cutting head
    const butt=headAtMax ? pMin : -pMax;
    const distance=projection.map(t=>(headAtMax?t:-t)-butt);
    // The grip landmark from the original image is expressed as a fraction of
    // *handle* length. The last ~20% of the GLB is the head, not the handle.
    const gripDistance=length*gripFraction*.8;
    const shaftCandidates=[];
    for(let i=0;i<points.length;i++)
      if(Math.abs(distance[i]-gripDistance)<length*.048)shaftCandidates.push(points[i]);
    if(shaftCandidates.length<8)throw Error("No shaft vertices near the grip");
    const radialCenter=centroid(shaftCandidates);
    const grip=add(radialCenter,mul(signed,gripDistance-dot(sub(radialCenter,center),signed)+butt));
    // Head mass displaced off the shaft reveals the blade plane and which side
    // of the shaft to point forward in the character's local frame.
    const headCandidates=[];
    for(let i=0;i<points.length;i++)
      if(distance[i]>length*.76)headCandidates.push(points[i]);
    if(headCandidates.length<8)throw Error("No discernible weapon head vertices");
    const headCenter=centroid(headCandidates);
    const transverse=sub(sub(headCenter,grip),mul(signed,dot(sub(headCenter,grip),signed)));
    const blade=unit(transverse);
    if(!blade || norm(transverse)<length*.023)
      throw Error("Weapon head has no reliable side; manual review required");
    return {grip,shaft:signed,blade,length,headWidthRatio:spreadRatio,
      gripFractionFromButt:gripFraction,vertexCount:points.length};
  }
  return {fitGrip,cross,dot,unit,sub,mul,add,norm};
});
