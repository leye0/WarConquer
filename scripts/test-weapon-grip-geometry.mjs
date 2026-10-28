#!/usr/bin/env node
// Deterministic, axis-invariant synthetic QA for the geometry part of grip fitting.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require=createRequire(import.meta.url);
const {fitGrip,frameFromLandmarks,rotationBetweenFrames,dot,sub,norm}=require("./weapon-grip-geometry.js");

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
for(const [label,transform] of [
  ["vertical",p=>p],
  ["horizontal",p=>[p[1],-p[2],p[0]]],
  ["diagonal",p=>[(p[0]+p[1])/Math.SQRT2,(p[1]-p[0])/Math.SQRT2,p[2]]],
  ["flipped",p=>[-p[1],p[0],-p[2]]],
]) {
  const obj=fitGrip(syntheticAxe(transform),.19,"axe");
  const expectedShaft=transform([0,1,0]);
  const expectedBlade=transform([1,0,0]);
  const expectedGrip=transform([0,-.7,0]);
  assert(dot(obj.shaft,expectedShaft)>.85,label+": head must point from handle butt to blade");
  assert(dot(obj.blade,expectedBlade)>.45,label+": blade edge must point outward");
  assert(norm(sub(obj.grip,expectedGrip))<.25,label+": grip must land on narrow handle");
  assert(obj.headWidthRatio>1.23,label+": head/handle asymmetry must be measurable");
  console.log("PASS",label,JSON.stringify({grip:obj.grip,shaft:obj.shaft,ratio:obj.headWidthRatio}));
}
// The head may be symmetric around the shaft: centroid-only heuristics fail.
const doubleBlade=[];
for(let i=0;i<=90;i++)for(let j=0;j<32;j++){
  const y=-1+1.78*i/90,a=j*Math.PI*2/32;
  doubleBlade.push([.032*Math.cos(a),y,.032*Math.sin(a)]);
}
for(let i=0;i<34;i++)for(let j=0;j<30;j++){
  const y=.70+i*.011,x=-.34+j*.023;
  for(const z of [-.021,.021])doubleBlade.push([x,y,z]);
}
const centered=fitGrip(doubleBlade,.19,"axe");
assert.equal(centered.bladeMethod,"head-transverse-covariance",
  "symmetric head must use geometric blade plane instead of invented centroid side");
assert(Math.abs(dot(centered.blade,[1,0,0]))>.85,
  "blade plane must still be recovered from head cross-section");
console.log("PASS symmetric-double-axe",centered.bladeMethod);
const plain=[];
for(let i=0;i<120;i++)for(let j=0;j<10;j++){
  const a=j*Math.PI/5;
  plain.push([.04*Math.cos(a),-1+2*i/120,.04*Math.sin(a)]);
}
assert.throws(()=>fitGrip(plain,.19,"axe"),/head not distinguishable/, "a staff cannot masquerade as an axe");
assert.throws(()=>fitGrip(syntheticAxe(),.92,"axe"),/Invalid vision/);

// A curved rigid frame can attach at its central grip without a bow-specific
// mesh transform, string simulation or secondary-hand IK.
const frame=[];
for(let i=0;i<=100;i++)for(let j=0;j<24;j++){
  const y=-1+2*i/100,a=j*Math.PI*2/24;
  frame.push([.35*(1-y*y)+.025*Math.cos(a),y,.025*Math.sin(a)]);
}
for(const transform of [p=>p,p=>[p[1],-p[2],p[0]]]){
  const grip=fitGrip(frame.map(transform),.5,"frame");
  assert.equal(grip.bladeMethod,"generic-frame-pca");
  assert(norm(sub(grip.grip,transform([.35,0,0])))<.15);
  assert(Math.abs(dot(grip.shaft,transform([0,1,0])))>.85);
}
console.log("PASS generic curved frame one-hand grip");

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
