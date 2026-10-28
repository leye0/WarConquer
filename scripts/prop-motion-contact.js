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
  return {solveTwoGrips,armReach,rowTransform,resolveMode};
});
