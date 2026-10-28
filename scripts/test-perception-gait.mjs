#!/usr/bin/env node
import assert from "node:assert/strict";
import {createRequire} from "node:module";
const require=createRequire(import.meta.url);
const {duration,stride,nominalSpeed,playbackRatio}=require("./perception-gait.js");
const clip=(frames,fps=30)=>({from:0,to:frames,targetedAnimations:[
  {animation:{framePerSecond:fps}}]});
const walk=clip(37),run=clip(24);
const close=(a,b)=>assert(Math.abs(a-b)<1e-8,a+" must equal "+b);
close(duration(walk),37/30);
close(duration(run),24/30);
close(stride("walk"),1.71);
close(stride("run"),2.85);
close(nominalSpeed("walk",walk),1.71/(37/30));
close(nominalSpeed("run",run),2.85/.8);
close(playbackRatio("walk",walk,nominalSpeed("walk",walk)),1);
close(playbackRatio("walk",walk,nominalSpeed("walk",walk)/2),.5);
close(playbackRatio("walk",walk,nominalSpeed("walk",walk,{scale:1.2}),{scale:1.2}),1);
assert.equal(nominalSpeed("walk",null),null);
assert.equal(stride("unknown"),null);
console.log("PASS: GLB cycle duration, physically scaled stride and distance-matched cadence");
