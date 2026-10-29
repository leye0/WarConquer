/* WarConquer: physically constrained, role-agnostic two-hand prop contact.
 * Every source position and functional direction comes from 3D VISION labels.
 * Every target palm and limb length comes from the animated rig. This module
 * chooses NO weapon role or hand based on mesh extents, names or proportions.
 */
(function(root,factory){
  const geometry=typeof module==="object"&&module.exports
    ? require("./weapon-grip-geometry.js") : root.WCWeaponGrip;
  const api=factory(geometry);
  if(typeof module==="object"&&module.exports)module.exports=api;
  else root.WCPropMotionContact=api;
})(typeof globalThis==="object"?globalThis:this,function(geometry){
  "use strict";
  const valid=p=>Array.isArray(p)&&p.length===3&&p.every(Number.isFinite);
  const requirePoint=(point,label)=>{
    if(!valid(point))throw Error("Missing vision/joint position: "+label);
  };
  const v=geometry;
  const plus=(a,b)=>a.map((x,i)=>x+b[i]);
  const unit=p=>v.unit(p);
  const rowTransform=(point,m)=>[0,1,2].map(j=>point.reduce(
    (sum,n,i)=>sum+n*m[3*i+j],0));

  function armReach(shoulder,elbow,wrist,target,epsilon=1e-5){
    for(const [name,p] of Object.entries({shoulder,elbow,wrist,target}))
      requirePoint(p,name);
    const upper=v.norm(v.sub(elbow,shoulder));
    const lower=v.norm(v.sub(wrist,elbow));
    if(upper<epsilon||lower<epsilon)throw Error("Degenerate observed arm bones");
    const distance=v.norm(v.sub(target,shoulder));
    const min=Math.abs(upper-lower),max=upper+lower;
    return {upper,lower,distance,min,max,
      reachable:distance>=min-epsilon&&distance<=max+epsilon,
      reachDeficit:Math.max(0,min-distance,distance-max)};
  }

  function twoBoneElbow(shoulder,elbow,wrist,target){
    const reach=armReach(shoulder,elbow,wrist,target);
    if(!reach.reachable)throw Error("Secondary wrist target lies beyond actual arm reach");
    if(v.norm(v.cross(v.sub(elbow,shoulder),v.sub(wrist,elbow)))<1e-7)
      throw Error("Source elbow is straight: cannot invent its bend side");
    const direction=unit(v.sub(target,shoulder));
    if(!direction)throw Error("Arm target coincides with shoulder: undefined bend plane");
    const oldUpper=v.sub(elbow,shoulder);
    const bend=unit(v.sub(oldUpper,v.mul(direction,v.dot(oldUpper,direction))));
    if(!bend)throw Error("Source elbow is straight: cannot invent its bend side");
    const along=(reach.upper**2-reach.lower**2+reach.distance**2)/(2*reach.distance);
    const offset=Math.sqrt(Math.max(0,reach.upper**2-along**2));
    return {elbow:plus(plus(shoulder,v.mul(direction,along)),v.mul(bend,offset)),
      wrist:[...target],reach};
  }

  function reachableSecondaryGripTarget({sourcePrimary,sourceSecondary,scale,
      primaryPalm,secondaryPalm,shoulder,elbow,wrist,palmOffset=[0,0,0],
      margin=.025}){
    // The object fixes grip spacing, and the real animated arm fixes reach.
    // The allowable SECOND contact is the INTERSECTION of two spheres:
    //   object radius around the primary palm, limb radius around shoulder.
    // Project the existing Mixamo palm direction to the nearest feasible
    // spherical cap; neither a weapon axis nor a per-clip pose is invented.
    for(const [name,p] of Object.entries({sourcePrimary,sourceSecondary,
        primaryPalm,secondaryPalm,shoulder,elbow,wrist,palmOffset}))
      requirePoint(p,name);
    if(!Number.isFinite(scale)||scale<=0||!Number.isFinite(margin)||margin<0)
      throw Error("Invalid source-vision grip scale or anatomical safety margin");
    const radius=v.norm(v.sub(sourceSecondary,sourcePrimary))*scale;
    if(radius<1e-5)throw Error("Two visual grips are not physically distinct");
    const reach=armReach(shoulder,elbow,wrist,wrist);
    const effectiveShoulder=plus(shoulder,palmOffset);
    const fromPrimary=v.sub(effectiveShoulder,primaryPalm);
    const separation=v.norm(fromPrimary);
    const natural=unit(v.sub(secondaryPalm,primaryPalm));
    if(!natural)throw Error("Animated palms are indistinguishable");
    if(separation<1e-6){
      if(radius>reach.max-margin)
        throw Error("Vision grips farther apart than the real arm can reach");
      return {target:plus(primaryPalm,v.mul(natural,radius)),reach,
        requiredLength:radius,reachAdjusted:false};
    }
    const shoulderDir=v.mul(fromPrimary,1/separation);
    const maxRadius=reach.max-margin;
    const cosine=(radius*radius+separation*separation-maxRadius*maxRadius)/
      (2*radius*separation);
    if(cosine>1+1e-7)
      throw Error("Vision grip spacing and actual shoulder cannot satisfy two-hand carry");
    let direction=natural;
    let adjusted=false;
    if(cosine>-1 && v.dot(direction,shoulderDir)<cosine){
      let tangent=v.sub(direction,v.mul(shoulderDir,v.dot(direction,shoulderDir)));
      if(v.norm(tangent)<1e-7){
        const elbowHint=v.sub(elbow,shoulder);
        tangent=v.sub(elbowHint,v.mul(shoulderDir,v.dot(elbowHint,shoulderDir)));
      }
      const t=unit(tangent);
      if(!t)throw Error("Straight Mixamo arm has no observed bend plane");
      direction=v.add(v.mul(shoulderDir,Math.max(-1,Math.min(1,cosine))),
        v.mul(t,Math.sqrt(Math.max(0,1-cosine*cosine))));
      adjusted=true;
    }
    const target=plus(primaryPalm,v.mul(direction,radius));
    return {target,reach,requiredLength:radius,reachAdjusted:adjusted,
      effectiveShoulder};
  }

  function reachablePrimaryGripTarget({sourcePrimary,sourceSecondary,scale,
      primaryPalm,primaryShoulder,primaryElbow,primaryWrist,
      primaryPalmOffset=[0,0,0],secondaryShoulder,secondaryElbow,
      secondaryWrist,secondaryPalmOffset=[0,0,0],margin=.03}){
    // During a strike Mixamo can move the leading palm OUTSIDE the volume
    // where a rigid two-grip object can be reached by the opposite arm.
    // In that situation, changing the prop rotation cannot solve contact.
    // Project the FIRST palm toward the opposite shoulder by the minimum
    // distance needed to make the pair of real-arm reach spheres intersect.
    // The primary arm must itself be able to reach that projected position.
    for(const [name,p] of Object.entries({sourcePrimary,sourceSecondary,
        primaryPalm,primaryShoulder,primaryElbow,primaryWrist,
        primaryPalmOffset,secondaryShoulder,secondaryElbow,secondaryWrist,
        secondaryPalmOffset}))requirePoint(p,name);
    if(!Number.isFinite(scale)||scale<=0||!Number.isFinite(margin)||margin<0)
      throw Error("Invalid source grips or two-arm anatomical margin");
    const spacing=v.norm(v.sub(sourceSecondary,sourcePrimary))*scale;
    if(spacing<1e-5)throw Error("Two confirmed vision grips must be distinct");
    const secondaryReach=armReach(secondaryShoulder,secondaryElbow,
      secondaryWrist,secondaryWrist);
    const center=plus(secondaryShoulder,secondaryPalmOffset);
    const direction=v.sub(primaryPalm,center),distance=v.norm(direction);
    const limit=secondaryReach.max+spacing-margin;
    if(limit<=0)throw Error("Two-hand source spacing exceeds anatomical reach");
    const adjusted=distance>limit;
    const target=adjusted?plus(center,v.mul(direction,limit/distance)):
      [...primaryPalm];
    const wristTarget=v.sub(target,primaryPalmOffset);
    const primaryReach=armReach(primaryShoulder,primaryElbow,
      primaryWrist,wristTarget);
    if(!primaryReach.reachable && primaryReach.reachDeficit>.025)
      throw Error("Both vision grips are physically incompatible with both actual arms");
    return {target,adjusted,spacing,primaryReach,secondaryReach};
  }

  function solveTwoGrips({sourcePrimary,sourceSecondary,featureOrigin,featureTip,
      primaryPalm,secondaryPalm,actionForward,scale,secondaryArm=null}){
    for(const [name,p] of Object.entries({sourcePrimary,sourceSecondary,
        featureOrigin,featureTip,primaryPalm,secondaryPalm,actionForward}))
      requirePoint(p,name);
    if(!Number.isFinite(scale)||scale<=0)throw Error("Invalid physical scale");
    const sourceBetween=v.sub(sourceSecondary,sourcePrimary);
    const targetBetween=v.sub(secondaryPalm,primaryPalm);
    if(v.norm(sourceBetween)<1e-6||v.norm(targetBetween)<1e-6)
      throw Error("Two distinct labelled grips and two real palms are required");
    const sourceDirection=v.sub(featureTip,featureOrigin);
    if(v.norm(sourceDirection)<1e-6)throw Error("Missing real functional action direction");
    const action=unit(actionForward);
    if(!action)throw Error("Ambiguous joint-derived action direction");
    // Two marked grips determine a physical axis. The SOURCE-CERTIFIED
    // action feature fixes roll about that axis. A collinear feature cannot
    // fix roll: reject it instead of inventing a convenient blade orientation.
    const rotation=v.rotationBetweenFrames(sourceBetween,sourceDirection,
      targetBetween,actionForward);
    const rotate=p=>rowTransform(p,rotation);
    const secondaryIKTarget=plus(primaryPalm,
      v.mul(rotate(sourceBetween),scale));
    const residual=v.norm(v.sub(secondaryIKTarget,secondaryPalm));
    const observedLength=v.norm(targetBetween);
    const requiredLength=v.norm(sourceBetween)*scale;
    const featureWorld=unit(rotate(sourceDirection));
    const alignedAction=featureWorld? v.dot(featureWorld,action):NaN;
    const reach=secondaryArm?armReach(secondaryArm.shoulder,
      secondaryArm.elbow,secondaryArm.wrist,secondaryIKTarget):null;
    return {rotation,primaryWorld:[...primaryPalm],secondaryIKTarget,
      residual,observedLength,requiredLength,alignedAction,
      secondaryArmReach:reach,
      status:reach&&!reach.reachable?"ik_unreachable":
        residual>.045?"secondary_ik_required":"geometrically_consistent"};
  }

  function resolveMode(characterization,phase,mixamoRole){
    if(!["carry","use"].includes(phase)||typeof mixamoRole!=="string")
      throw Error("Invalid animated interaction phase or motion role");
    const options=characterization?.modes;
    if(!Array.isArray(options))throw Error("No source-confirmed interaction modalities");
    let candidates=options.filter(mode=>mode.phase===phase&&mode.mixamo_role===mixamoRole);
    if(!candidates.length&&phase==="carry")
      candidates=options.filter(mode=>mode.phase==="carry"&&mode.mixamo_role==="none");
    if(candidates.length!==1)throw Error("No unique vision-confirmed mode for Mixamo "+mixamoRole);
    const mode=candidates[0], grips=new Set((characterization.grips||[]).map(g=>g.id));
    const features=new Set((characterization.features||[]).map(f=>f.id));
    if(!["left","right"].includes(mode.primary_hand)||!grips.has(mode.primary_grip)||
       ![1,2].includes(mode.hands)||
       (mode.hands===2&&(!["left","right"].includes(mode.secondary_hand)||
         mode.secondary_hand===mode.primary_hand||!grips.has(mode.secondary_grip)||
         mode.secondary_grip===mode.primary_grip))||
       (phase==="use"&&(!features.has(mode.functional_feature)||
         mode.action_direction==="none")))
      throw Error("Invalid confirmed anatomical/functional contact mode");
    return mode;
  }
  return {solveTwoGrips,armReach,twoBoneElbow,reachableSecondaryGripTarget,
    reachablePrimaryGripTarget,
    rowTransform,resolveMode};
});
