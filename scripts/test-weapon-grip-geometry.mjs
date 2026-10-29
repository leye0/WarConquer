#!/usr/bin/env node
// Deterministic, axis-invariant synthetic QA for the geometry part of grip fitting.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require=createRequire(import.meta.url);
const {fitGrip,frameFromLandmarks,chooseNonCollidingCarry,rotationBetweenFrames,dot,sub,norm}=require("./weapon-grip-geometry.js");

// A grip frame must actually point in the requested direction after fitting.
// The old matrix product reversed these operations, causing 180° flips when
// source and target axes differed from the identity frame.
const normalize=v=>v.map(n=>n/norm(v));
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const basis=(shaft,blade)=>{
  const y=normalize(shaft),x=normalize(sub(blade,y.map(n=>n*dot(y,blade))));
  return [x,y,normalize(cross(x,y))];
};
const transformRow=(v,m)=>[0,1,2].map(j=>v.reduce((sum,n,i)=>sum+n*m[3*i+j],0));
for(const [name,source,target] of [
  ["quarter-turn",[[0,0,1],[1,0,0]],[[0,1,0],[0,0,1]]],
  ["half-turn",[[0,-1,0],[1,0,0]],[[0,1,0],[-1,0,0]]],
  ["arbitrary-orientations",[[2,3,-1],[-2,1,2]],[[-1,2,3],[2,4,-1]]],
]) {
  const m=rotationBetweenFrames(...source,...target);
  const a=basis(...source),b=basis(...target);
  for(let i=0;i<3;i++)assert(norm(sub(transformRow(a[i],m),b[i]))<1e-9,
    name+": final rotation must map each geometric source axis to its requested direction");
  const determinant=dot(transformRow(a[0],m),cross(transformRow(a[1],m),transformRow(a[2],m)));
  assert(Math.abs(determinant-1)<1e-9,name+": no mirrored or inverted frame");
}
assert.throws(()=>rotationBetweenFrames([0,1,0],[0,2,0],[0,1,0],[1,0,0]),/ambiguous/);
console.log("PASS generic source-to-hand rotation including 180-degree orientation");

function syntheticAxe(transform=p=>p) {
  const vertices=[];
  for(let i=0;i<=90;i++){
    const y=-1+1.78*i/90;
    for(let j=0;j<32;j++){
      const a=j*Math.PI*2/32;
      vertices.push(transform([.032*Math.cos(a),y,.032*Math.sin(a)]));
    }
  }
  for(let i=0;i<34;i++)for(let j=0;j<32;j++){
    const y=.70+i*.011;
    const x=.09+j*.011;
    for(const z of [-.021,.021])vertices.push(transform([x,y,z]));
  }
  return vertices;
}
// The legacy PCA classifier is deliberately unavailable. A geometric mesh
// alone cannot decide whether a feature is a blade, a muzzle or a handle.
assert.throws(()=>fitGrip(syntheticAxe(),.19,"axe"),/vision-labelled/,
  "No geometric semantic fallback may silently classify an object");
console.log("PASS: geometry refuses to invent semantic grip roles");


// Signed *functional* edge points are vision-provided and GLB-derived. The
// broadest part of an asymmetric head is not necessarily the cutting edge.
// Both models here have the same PCA, but opposite annotated sharp sides.
for(const move of [p=>p,p=>[p[1],-p[2],p[0]]]){
  const vertices=syntheticAxe(move);
  for(const edgeSign of [-1,1]){
    const landmarks={handle_butt:move([0,-1,0]),grip_center:move([0,-.48,0]),
      working_head:move([0,.82,0]),functional_edge:move([edgeSign*.38,.82,0])};
    const solved=frameFromLandmarks(landmarks,vertices);
    assert(dot(solved.shaft,move([0,1,0]))>.999);
    assert(dot(solved.blade,move([edgeSign,0,0]))>.999,
      "Functional face sign is determined by landmarks, never a guessed PCA axis");
    assert(solved.length>1.6);
    assert.equal(solved.bladeMethod,"signed-vision-glb-functional-edge");
    assert(solved.carryShaft&&dot(solved.carryShaft,move([0,1,0]))>.8,
      "A head-heavy prop should let its actual mass hang below the palm");
  }
}
assert.throws(()=>frameFromLandmarks({grip_center:[0,0,0]},syntheticAxe()),/Missing intrinsic/);
console.log("PASS: signed contact frames preserve the real sharp edge on rotated GLBs");

// Neutral carry uses a detailed rig body volume, not a named weapon offset.
// When a heavy object would penetrate the torso, a generic search tilts it
// outward just enough to clear the character while preserving the hand grip.
const genericProp=[];
for(let t=.2;t<=1;t+=.025)for(const x of [-.035,.035])for(const z of [-.025,.025])
  genericProp.push([x,t,z]);
const contactSource={grip:[0,0,0],shaft:[0,1,0],blade:[1,0,0],
  carryShaft:[0,1,0],length:1};
const torso=[{a:[0,0,0],b:[0,1.8,0],radius:.32}];
const fit=chooseNonCollidingCarry(genericProp,contactSource,[.22,1.1,0],
  [1,0,0],[1,0,0],1,torso);
assert(fit.tilt>0,"The solver must move a long prop away from an intersecting torso");
assert(fit.shaft[0]>.05&&fit.shaft[1]<0,
  "The generic solver keeps gravity downward while introducing an outward component");
console.log("PASS: anatomical body capsule prevents generic carried-prop collision");
