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
  // Babylon transforms points as ROW vectors. Frame axes are rows, so the
  // source-to-target rotation is transpose(source) * target, not the reverse.
  // Keep this calculation engine-independent so its direction is unit tested.
  function rotationBetweenFrames(sourceShaft, sourceBlade, targetShaft, targetBlade) {
    const frame=(shaft,blade)=>{
      const y=unit(shaft);
      const x=y&&unit(sub(blade,mul(y,dot(y,blade))));
      const z=x&&unit(cross(x,y));
      if(!x||!z)throw Error("Cannot orient an ambiguous grip frame");
      return [x,y,z];
    };
    const source=frame(sourceShaft,sourceBlade);
    const target=frame(targetShaft,targetBlade);
    const rotation=[];
    for(let i=0;i<3;i++)for(let j=0;j<3;j++)
      rotation.push(source.reduce((sum,axis,k)=>sum+axis[i]*target[k][j],0));
    return rotation;
  }

  // Functional directions must come from annotated 3D vertices. PCA can find
  // the long axis but cannot tell the SHARP edge from the blunt poll of an axe.
  // This contract is intrinsic to an object, independent of the holder's rig.
  function frameFromLandmarks(points, vertices) {
    const names=["handle_butt","grip_center","working_head","functional_edge"];
    if(!points || !names.every(name=>Array.isArray(points[name])&&
        points[name].length===3&&points[name].every(Number.isFinite)))
      throw Error("Missing intrinsic GLB contact landmarks");
    const grip=points.grip_center;
    const shaft=sub(points.working_head,grip);
    const blade=sub(points.functional_edge,points.working_head);
    const y=unit(shaft);
    const x=y&&unit(sub(blade,mul(y,dot(blade,y))));
    if(!x || norm(blade)<1e-6)throw Error("Ambiguous functional edge on the real GLB");
    if(dot(sub(points.working_head,grip),sub(grip,points.handle_butt))<=0)
      throw Error("Inverted handle/head landmarks");
    if(!Array.isArray(vertices)||vertices.length<30)
      throw Error("Cannot measure full model length");
    const projected=vertices.map(v=>dot(v,y));
    const length=Math.max(...projected)-Math.min(...projected);
    if(length<1e-4)throw Error("Invalid physical prop length");
    // A passive object hangs with its center of mass below the palm. Surface
    // vertices provide a cheap center-of-volume proxy; if the mass offset is
    // tiny or ambiguous, use the explicitly annotated functional axis.
    // No weapon names or body-specific angles participate in this decision.
    const massCenter=centroid(vertices);
    const balance=sub(massCenter,grip);
    const carryShaft=norm(balance)>.08*length?unit(balance):null;
    return {grip,shaft:y,blade:x,length,massCenter,carryShaft,
      vertexCount:vertices.length,
      bladeMethod:"signed-vision-glb-functional-edge"};
  }

  function capsuleClearance(vertices,capsules){
    let nearest=Infinity;
    for(const point of vertices)for(const capsule of capsules){
      const v=sub(capsule.b,capsule.a),w=sub(point,capsule.a),vv=dot(v,v);
      const t=vv>1e-9?Math.max(0,Math.min(1,dot(w,v)/vv)):0;
      const separation=norm(sub(point,add(capsule.a,mul(v,t))))-capsule.radius;
      nearest=Math.min(nearest,separation);
    }
    return nearest;
  }

  function gravityCarryCandidates(workingWorld,awayWorld){
    const away=unit([awayWorld[0],0,awayWorld[2]]);
    if(!away)throw Error("No usable anatomical outward direction");
    return [0,.1,.2,.35,.5,.7,1,1.4,1.9,2.5].map(tilt=>({
      shaft:unit(add([0,-1,0],mul(away,tilt))),blade:workingWorld,tilt
    }));
  }

  function chooseNonCollidingCarry(vertices,source,gripWorld,workingWorld,awayWorld,
      targetLength,capsules) {
    if(!source.carryShaft||!Array.isArray(capsules)||!capsules.length)
      return {shaft:[0,-1,0],blade:workingWorld,tilt:0,collisionScore:0};
    const scale=targetLength/source.length;
    const sourceShaft=source.carryShaft;
    // The shaft, butt and fittings can also cross the body. Assess the whole
    // object, including vertices on the grip's opposite side.
    const sample=vertices;
    const stride=Math.max(1,Math.ceil(sample.length/850));
    let best=null;
    for(const {shaft,tilt} of gravityCarryCandidates(workingWorld,awayWorld)) {
      let rotation;
      try{rotation=rotationBetweenFrames(sourceShaft,source.blade,shaft,workingWorld);}
      catch{continue;}
      let collisions=0,nearest=Infinity;
      for(let i=0;i<sample.length;i+=stride){
        const p=sub(sample[i],source.grip);
        const point=add(gripWorld,mul([0,1,2].map(j=>
          p[0]*rotation[j]+p[1]*rotation[3+j]+p[2]*rotation[6+j]),scale));
        for(const capsule of capsules){
          const separation=capsuleClearance([point],[capsule]);
          nearest=Math.min(nearest,separation);
          if(separation<0)collisions+=separation*separation;
        }
      }
      // Collisions are expensive; gravity deviation is a small preference.
      const score=collisions*150+tilt*.06;
      if(!best||score<best.score)best={shaft,blade:workingWorld,
        tilt,collisionScore:collisions,nearest,score};
    }
    if(!best)throw Error("No nondegenerate carry frame");
    return best;
  }

  // Legacy entry point is intentionally closed: a mesh cannot identify its
  // own handle, sharp side, muzzle, string or functional front by PCA.
  // Only a vision-labelled 3D frame may enter the active fitter.
  function fitGrip() {
    throw Error("Semantic grip roles require vision-labelled GLB landmarks");
  }
  return {fitGrip,frameFromLandmarks,chooseNonCollidingCarry,capsuleClearance,
    gravityCarryCandidates,
    rotationBetweenFrames,cross,dot,unit,sub,mul,add,norm};
});
