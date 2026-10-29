#!/usr/bin/env node
/* No browser/network: signed role labels + actual two-hand anatomy only. */
import assert from "node:assert/strict";
import {createRequire} from "node:module";
const require=createRequire(import.meta.url);
const {solveTwoGrips,armReach,twoBoneElbow,reachableSecondaryGripTarget,
  reachablePrimaryGripTarget,
  resolveMode}=require("./prop-motion-contact.js");
const v=require("./weapon-grip-geometry.js");
const close=(a,b,tol=1e-9)=>assert(v.norm(v.sub(a,b))<tol,`${a} != ${b}`);
const labelled={sourcePrimary:[0,-.5,0],sourceSecondary:[0,.3,0],
  featureOrigin:[0,.7,0],featureTip:[-.4,.7,0]};

// A genuinely rotated item has the identical solution. Neither the longest
// axis nor an assumed 'right side' decides where the sharp edge is.
const sourceWorld=p=>[p[2],p[0],p[1]];
for(const sign of [-1,1]){
  const input=Object.fromEntries(Object.entries(labelled).map(([k,p])=>
    [k,sourceWorld(p.map((x,i)=>i===0?x*sign:x))]));
  const solve=solveTwoGrips({...input,primaryPalm:[.5,1.25,.2],
    secondaryPalm:[.5,1.25+.8,.2],actionForward:[sign,0,0],scale:1});
  assert.equal(solve.status,"geometrically_consistent");
  assert(solve.residual<1e-9);
  close(solve.secondaryIKTarget,[.5,2.05,.2]);
  assert(solve.alignedAction>.999);
}

const held=solveTwoGrips({...labelled,
  primaryPalm:[0,1.1,0],secondaryPalm:[0,1.25,0],
  actionForward:[-1,0,0],scale:1,
  secondaryArm:{shoulder:[0,1.8,0],elbow:[0,1.65,0],wrist:[0,1.25,0]}});
assert.equal(held.status,"ik_unreachable");
assert(Math.abs(held.requiredLength-.8)<1e-9);
assert(held.residual>.045);
assert(held.secondaryArmReach.reachDeficit>0);
assert(armReach([0,0,0],[1,0,0],[2,0,0],[1,1,0]).reachable);
assert(!armReach([0,0,0],[1,0,0],[2,0,0],[5,0,0]).reachable);
const ik=twoBoneElbow([0,0,0],[1,1,0],[2,0,0],[1.5,.5,0]);
assert(Math.abs(v.norm(ik.elbow)-Math.SQRT2)<1e-9);
assert(Math.abs(v.norm(v.sub(ik.elbow,ik.wrist))-Math.SQRT2)<1e-9);
assert(ik.elbow[1]>0,"Elbow keeps the observed bend side");
assert.throws(()=>twoBoneElbow([0,0,0],[1,1,0],[2,0,0],[5,0,0]),/reach/);
assert.throws(()=>twoBoneElbow([0,0,0],[1,0,0],[2,0,0],[1.5,.5,0]),/bend side/);
const grasp={sourcePrimary:[0,0,0],sourceSecondary:[0,.8,0],scale:1,
  primaryPalm:[0,0,0],secondaryPalm:[-.3,0,0],
  shoulder:[1,0,0],elbow:[1,.4,0],wrist:[1.4,.4,0]};
const constrained=reachableSecondaryGripTarget(grasp);
assert(constrained.reachAdjusted,"Unreachable Mixamo palm must change target direction");
assert(Math.abs(v.norm(constrained.target)-.8)<1e-8,
  "Known vision grip spacing may not shrink to fake a contact");
assert(v.norm(v.sub(constrained.target,grasp.shoulder))<constrained.reach.max,
  "Secondary palm must remain within the measured anatomical reach");
const natural=reachableSecondaryGripTarget({...grasp,secondaryPalm:[.8,0,0]});
assert(!natural.reachAdjusted,"Already reachable real Mixamo contacts are preserved");
close(natural.target,[.8,0,0]);
assert.throws(()=>reachableSecondaryGripTarget({...grasp,shoulder:[5,0,0],
  elbow:[5,.4,0],wrist:[5.4,.4,0]}),/cannot satisfy/);
const bothArms={sourcePrimary:[0,0,0],sourceSecondary:[.3,0,0],scale:1,
  primaryPalm:[1.1,0,0],primaryShoulder:[0,0,0],
  primaryElbow:[.3,.2,0],primaryWrist:[.6,0,0],
  primaryPalmOffset:[.5,0,0],
  secondaryShoulder:[0,0,0],secondaryElbow:[-.3,.2,0],
  secondaryWrist:[-.6,0,0]};
const both=reachablePrimaryGripTarget(bothArms);
assert(both.adjusted,"Leading Mixamo palm must move when the other real arm cannot reach");
assert(both.target[0]<bothArms.primaryPalm[0]);
assert(v.norm(v.sub(both.target,bothArms.secondaryShoulder))<=
  both.secondaryReach.max+both.spacing-.03+1e-9);
assert(both.primaryReach.reachable,"The leading arm must reach its corrected grip");
const bothNatural=reachablePrimaryGripTarget({...bothArms,primaryPalm:[.8,0,0]});
assert(!bothNatural.adjusted,"Keep valid Mixamo primary palm motion intact");
close(bothNatural.target,[.8,0,0]);
assert.throws(()=>reachablePrimaryGripTarget({...bothArms,
  secondaryShoulder:[-4,0,0],secondaryElbow:[-4.3,.2,0],
  secondaryWrist:[-4.6,0,0]}),/physically incompatible/);
assert.throws(()=>solveTwoGrips({...labelled,
  primaryPalm:[0,0,0],secondaryPalm:[0,1,0],actionForward:[0,1,0],scale:1}),
  /ambiguous/);
assert.throws(()=>solveTwoGrips({...labelled,sourceSecondary:[0,-.5,0],
  primaryPalm:[0,0,0],secondaryPalm:[0,1,0],actionForward:[1,0,0],scale:1}),
  /distinct labelled grips/);
const semantics={grips:[{id:"lower"},{id:"upper"}],features:[{id:"edge"}],modes:[
  {id:"walk_one",phase:"carry",mixamo_role:"none",hands:1,
   primary_hand:"right",primary_grip:"lower"},
  {id:"chop_two",phase:"use",mixamo_role:"axe_chop",hands:2,
   primary_hand:"right",primary_grip:"lower",secondary_hand:"left",secondary_grip:"upper",
   functional_feature:"edge",action_direction:"forward"}]};
assert.equal(resolveMode(semantics,"carry","run").hands,1);
assert.equal(resolveMode(semantics,"use","axe_chop").hands,2);
assert.throws(()=>resolveMode(semantics,"use","sword_slash"),/No unique/);
assert.throws(()=>resolveMode({...semantics,modes:[...semantics.modes,semantics.modes[1]]},
  "use","axe_chop"),/No unique/);
console.log("PASS: two vision-labelled GLB grips, functional sign, pose-derived IK targets/reach");
