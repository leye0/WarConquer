#!/usr/bin/env node
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require=createRequire(import.meta.url);
const { bodyFrame,palmFrame,contactFrame }=require("./rig-contact-landmarks.js");
const close=(a,b)=>assert(a.every((n,i)=>Math.abs(n-b[i])<1e-8),
  `Expected ${JSON.stringify(a)} = ${JSON.stringify(b)}`);
const base={
  leftFoot:[-.2,0,0],leftToe:[-.2,0,.22],rightFoot:[.2,0,0],rightToe:[.2,0,.22],
  rightWrist:[.4,1,.05],rightElbow:[.4,1.35,.05],
  rightIndex:[.34,.90,.16],rightMiddle:[.4,.89,.17],rightPinky:[.46,.91,.16],
  leftWrist:[-.4,1,.05],leftElbow:[-.4,1.35,.05],
  leftIndex:[-.46,.90,.16],leftMiddle:[-.4,.89,.17],leftPinky:[-.34,.91,.16]
};
const initial=contactFrame(base,{hand:"right",palm_fraction:.4,
  shaft_direction:"toward_elbow",working_face:"forward"});
close(bodyFrame(base).forward,[0,0,1]);
close(initial.grip,[.4,1,.05].map((v,i)=>v+.4*(initial.palm.knuckles[i]-base.rightWrist[i])));
close(initial.shaft,[0,1,0]);
close(initial.blade,[0,0,1]);
const hanging=contactFrame(base,{hand:"right",shaft_direction:"gravity",working_face:"outward"});
close(hanging.shaft,[0,-1,0]);
close(hanging.blade,[1,0,0]);
assert.equal(palmFrame(base,"left").grip.length,3);

// A different humanoid's joints are scaled, translated and turned 97 degrees.
// Its weapon attachment follows the actual joints, not a preset +Z direction.
const yaw=97*Math.PI/180,scale=1.46,offset=[3,.1,-2];
const turn=p=>[scale*(Math.cos(yaw)*p[0]+Math.sin(yaw)*p[2])+offset[0],
  scale*p[1]+offset[1],scale*(-Math.sin(yaw)*p[0]+Math.cos(yaw)*p[2])+offset[2]];
const second=Object.fromEntries(Object.entries(base).map(([name,p])=>[name,turn(p)]));
const equipped=contactFrame(second,{hand:"right",palm_fraction:.4,
  shaft_direction:"toward_elbow",working_face:"forward"});
close(equipped.grip,turn(initial.grip));
close(equipped.shaft,[0,1,0]);
close(equipped.blade,[Math.sin(yaw),0,Math.cos(yaw)]);
const hangingSecond=contactFrame(second,{hand:"right",shaft_direction:"gravity",working_face:"outward"});
close(hangingSecond.shaft,[0,-1,0]);
assert.throws(()=>contactFrame({rightWrist:[1,2,3]}),/Missing/);
console.log("PASS: one generic prop-contact contract adapts to two differently sized and oriented humanoid skeletons");
