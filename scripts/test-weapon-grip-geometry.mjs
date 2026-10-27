#!/usr/bin/env node
// Deterministic, axis-invariant synthetic QA for the geometry part of grip fitting.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require=createRequire(import.meta.url);
const {fitGrip,dot,sub,norm}=require("./weapon-grip-geometry.js");

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
