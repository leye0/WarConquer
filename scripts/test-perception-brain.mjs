#!/usr/bin/env node
// Perception stays bounded, deterministic and independent of GLB/LLM/DOM.
import assert from "node:assert/strict";
import {createRequire} from "node:module";
const require=createRequire(import.meta.url);
const {Brain,cell,lineOfSight}=require("./perception-brain.js");
const grid=rows=>({originX:0,originZ:0,grid:rows,objects:[]});
const clear=grid(Array.from({length:16},()=> ".".repeat(16)));
const me=options=>new Brain({id:"scout",x:.5,z:.5,visionRange:7,...options});

{
  const w=grid([".....","..#..",".....",".....","....."]);
  w.objects=[{id:"hidden",kind:"unit",team:"red",x:4.5,z:1.5},
    {id:"wallside",kind:"resource",x:1.5,z:1.5}];
  const b=me({x:.5,z:1.5});
  b.step(w,{type:"hold"},100,100);
  assert(b.visible.some(e=>e.id==="wallside"),"Near item should be visible");
  assert(!b.visible.some(e=>e.id==="hidden"),"Wall must hide the enemy");
  assert.equal(b.cells.get("2,1")?.blocked,true,"Wall itself can be seen");
  assert(!b.cells.has("4,1"),"Do not give the brain hidden terrain");
  assert.equal(lineOfSight(w,{x:.5,z:1.5},{x:4.5,z:1.5},false),false);
}
{
  const b=me({x:5.5,z:5.5,heading:0,fov:Math.PI/2});
  const w={...clear,objects:[
    {id:"ahead",kind:"resource",x:8.5,z:5.5},
    {id:"behind",kind:"resource",x:3.5,z:5.5}]};
  b.step(w,{type:"hold"},100,100);
  assert.deepEqual(b.visible.map(e=>e.id),["ahead"]);
}
{
  const b=me({x:1.5,z:1.5,heading:0});
  const w={...clear,objects:[]};
  const order={type:"relative",direction:"left",distance:3,id:1};
  const d=b.step(w,order,100,100);
  assert(Math.abs(d.goal.x-1.5)<1e-9&&Math.abs(d.goal.z-4.5)<1e-9);
  b.setPose({x:1.5,z:2,heading:Math.PI/2});
  assert.deepEqual(b.step(w,order,100,200).goal,d.goal,"Relative orders lock origin/direction");
  assert(b.step(w,{type:"relative",direction:"back",distance:2,id:2},100,300).goal.z<2);
}
{
  const w=grid([".......",".#####.",".......",".......","......."]);
  const b=me({x:.5,z:1.5,visionRange:8});
  b.step(w,{type:"hold"},100,100);
  const route=b.path(w,{x:6.5,z:1.5},100);
  assert(route?.length>7,"A* must go around a wall");
  assert(route.every(c=>w.grid[c.z][c.x]!== "#"),"Route crosses a known wall");
}
{
  const b=me({memoryTtlMs:200,maxEntities:3,maxCells:12});
  const w={...clear,objects:Array.from({length:6},(_,i)=>({
    id:"o"+i,kind:"resource",x:1+i,z:1}))};
  b.step(w,{type:"hold"},100,100);
  assert(b.entities.size<=3&&b.cells.size<=12,"Memory budgets enforced");
  b.step({...clear,objects:[]},{type:"hold"},100,500);
  assert.equal(b.entities.size,0,"Observed dynamic entities expire");
}
{
  const w={...clear,objects:[{id:"enemy",kind:"unit",team:"red",x:1.5,z:.5,threat:1}]};
  const b=me({x:.5,z:.5,visionRange:4,bravery:0,autoFlee:true});
  for(let t=100;t<=1200;t+=100)b.step(w,{type:"hold"},100,t);
  assert(b.fleeing,"Close enemies trigger a fear-based flee");
  const d=b.step(w,{type:"hold"},100,1300);
  assert(["fleeing","blocked"].includes(d.status),"Fleeing should have priority");
  for(let t=1400;t<9000;t+=100)b.step({...clear,objects:[]},{type:"hold"},100,t);
  assert(!b.fleeing,"Fear must diminish when threats disappear");
}
{
  const enemy={id:"e",kind:"unit",team:"red",x:1.5,z:.5};
  const resource={id:"r",kind:"resource",x:2.5,z:.5};
  const w={...clear,objects:[enemy,resource]};
  const b=me();
  const a=b.step(w,{type:"attack",entityId:"e",distance:1.2},100,100);
  assert.equal(a.action,"attack");
  assert.equal(b.step(w,{type:"collect",entityId:"e"},100,200).action,null);
  assert(b.step(w,{type:"find",kind:"resource"},100,300).goal);
  const snap=b.snapshot();
  assert(snap.memory.entities.some(x=>x.id==="r"));
  assert.doesNotThrow(()=>JSON.stringify(snap));
}
{
  const w={...clear,objects:[{id:"solid",kind:"obstacle",x:3.5,z:1.5,
    blocking:true,opaque:false,radius:.5}]};
  const b=me({x:.5,z:1.5,visionRange:8});
  b.step(w,{type:"hold"},100,100);
  assert.equal(b.visible.length,1);
  assert.equal(b.knownBlocked(w,cell(w,3.5,1.5),100),true,
    "Known dynamic obstacles block navigation");
}
{
  const b=me();
  const d=b.step({...clear,objects:[]},{type:"find",kind:"resource"},100,100);
  assert(["searching","not_found"].includes(d.status),"Search may explore, never conjure a resource");
}
{
  const many=Array.from({length:100},(_,i)=>new Brain({
    id:"unit-"+i,x:2+(i%10),z:2+Math.floor(i/10),visionRange:5}));
  const before=Date.now();
  for(let t=100;t<=500;t+=100)for(const b of many)
    b.step(clear,{type:"hold"},100,t);
  assert(many.every(b=>b.cells.size<=1024));
  console.log("PASS: 100 cervelets × 5 ticks, "+(Date.now()-before)+" ms (informational)");
}

{
  // Manual orders must not be silently replaced by fear; a future planner
  // can explicitly issue a flee order when it chooses that objective.
  const w={...clear,objects:[{id:"enemy",kind:"unit",team:"red",x:1.5,z:.5}]};
  const b=me({visionRange:4,bravery:0,autoFlee:false});
  let d;
  for(let ms=100;ms<=1400;ms+=100)
    d=b.step(w,{type:"goto",x:8.5,z:8.5},100,ms);
  assert(b.fleeing,"The emotional state may still contain fear");
  assert.notEqual(d.status,"fleeing","Fear must not hijack an explicit manual order");
}
{
  // A solid target's centre is blocked, but reaching its free perimeter is valid.
  const w=grid(["........","........","..##....","........","........"]);
  w.occlusion=Array.from({length:5},()=> "........");
  w.objects=[{id:"rocky",kind:"resource",x:2.5,z:2.5,blocking:true,radius:.8}];
  const b=me({x:.5,z:2.5,visionRange:8});
  const d=b.step(w,{type:"collect",entityId:"rocky",distance:1.3},100,100);
  assert(d.goal,"Find a reachable interaction position outside the blocked cell");
  assert.notEqual(w.grid[cell(w,d.goal.x,d.goal.z).z][cell(w,d.goal.x,d.goal.z).x],"#");
}
{
  const b=me(),order={type:"goto",x:8.5,z:8.5};
  for(let i=1;i<=3;i++){
    const d=b.step(clear,order,100,i*100);
    assert(d.move.dx||d.move.dz,"A step should have been attempted");
    b.reportMoveResult({accepted:false,attempted:d.move,blockedCell:{x:1,z:1},nowMs:i*100});
  }
  const stuck=b.step(clear,order,100,400);
  assert.equal(stuck.status,"stuck","Repeated refused movement must stop");
  assert.deepEqual(stuck.move,{dx:0,dz:0});
  assert.equal(b.snapshot().navigation.blocked,true);
  assert.notEqual(b.step(clear,{type:"hold"},100,500).status,"stuck","A new order resets the stall");
}

console.log("PASS: vision/occlusion, memory, A*, fear, interaction approach, collision feedback and no oscillation");
