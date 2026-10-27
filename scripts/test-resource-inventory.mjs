#!/usr/bin/env node
import assert from "node:assert/strict";
import {createRequire} from "node:module";
const require=createRequire(import.meta.url);
const {inventory,collect}=require("./resource-inventory.js");
const {Brain,cell}=require("./perception-brain.js");
{
  const bag=inventory();
  const items=[{id:"ore-1",name:"Gisement",kind:"resource",
    resourceType:"ore",quantity:3,x:2,z:2}];
  const first=collect({items,bag,entityId:"ore-1",actor:{x:1,z:2},reach:1.25});
  assert.equal(first.ok,true);
  assert.equal(first.amount,3);
  assert.equal(bag.ore,3);
  assert.equal(items.length,0,"Collected resources leave the world");
  assert.equal(collect({items,bag,entityId:"ore-1",actor:{x:1,z:2}}).reason,"not_found");
  assert.equal(bag.ore,3,"Repeated ticks must never duplicate inventory");
}
{
  const bag=inventory();
  const items=[{id:"wood",kind:"resource",resourceType:"wood",quantity:1,x:5,z:5},
    {id:"enemy",kind:"unit",resourceType:"food",x:0,z:0}];
  assert.equal(collect({items,bag,entityId:"wood",actor:{x:0,z:0}}).reason,"out_of_range");
  assert.equal(collect({items,bag,entityId:"enemy",actor:{x:0,z:0}}).reason,"not_a_resource");
  assert.equal(items.length,2);assert.equal(bag.wood,0);
}
{
  const bag=inventory();
  const items=[{id:"bad",kind:"resource",resourceType:"gold",x:0,z:0}];
  assert.equal(collect({items,bag,entityId:"bad",actor:{x:0,z:0}}).reason,"unknown_resource_type");
  assert.equal(items.length,1);
}

{
  // End-to-end: an interaction waypoint is NOT the resource itself.
  // Pickup fires only when the actual resource is within physical reach.
  const items=[{id:"ore",kind:"resource",resourceType:"ore",quantity:2,
    x:5.5,z:5.5,radius:.4,blocking:false,opaque:false}];
  const world={grid:Array.from({length:12},()=> ".".repeat(12)),objects:items};
  const brain=new Brain({id:"scout",x:.5,z:.5,visionRange:12});
  const bag=inventory();let x=.5,z=.5,transaction=null;
  for(let ms=100;ms<=12000;ms+=100){
    brain.setPose({x,z});
    const d=brain.step(world,{type:"collect",entityId:"ore",distance:1.2},100,ms);
    if(d.action){
      assert(Math.hypot(x-5.5,z-5.5)<=1.2+1e-6,
        "Never perform an interaction from a merely nearby waypoint");
      transaction=collect({items,bag,entityId:"ore",actor:{x,z},reach:1.2});
      break;
    }
    const n=cell(world,x+d.move.dx,z+d.move.dz);
    const accepted=n.x>=0&&n.x<12&&n.z>=0&&n.z<12&&world.grid[n.z][n.x]!== "#";
    brain.reportMoveResult({accepted,attempted:d.move,blockedCell:accepted?null:n,nowMs:ms});
    if(accepted){x+=d.move.dx;z+=d.move.dz;}
  }
  assert.equal(transaction?.ok,true,"The scout must reach and collect the resource");
  assert.equal(bag.ore,2);
  assert.equal(items.length,0);
}


{
  const resource={id:"blocking-wood",kind:"resource",resourceType:"wood",quantity:1,
    x:4,z:4,radius:.8,blocking:true,opaque:false};
  const bag=inventory(),items=[resource],grid=[];
  for(let z=0;z<12;z++){
    let row="";
    for(let x=0;x<12;x++){
      const dx=Math.max(0,Math.abs(x+.5-resource.x)-.5);
      const dz=Math.max(0,Math.abs(z+.5-resource.z)-.5);
      row+=Math.hypot(dx,dz)<resource.radius?"#":".";
    }
    grid.push(row);
  }
  const world={grid,occlusion:Array.from({length:12},()=> ".".repeat(12)),objects:items};
  const brain=new Brain({id:"scout",x:.5,z:.5,visionRange:9});
  let x=.5,z=.5,done=false;
  for(let ms=100;ms<=8000;ms+=100){
    brain.setPose({x,z});
    const d=brain.step(world,{type:"collect",entityId:resource.id,distance:1.8},100,ms);
    assert.notEqual(d.status,"stuck","A resource obstacle must not cause infinite bouncing");
    if(d.action){
      const transaction=collect({items,bag,entityId:resource.id,actor:{x,z},reach:1.8});
      assert.equal(transaction.ok,true);done=true;break;
    }
    const n=cell(world,x+d.move.dx,z+d.move.dz);
    const accepted=n.x>=0&&n.x<12&&n.z>=0&&n.z<12&&grid[n.z][n.x]!== "#";
    brain.reportMoveResult({accepted,attempted:d.move,blockedCell:accepted?null:n,nowMs:ms});
    if(accepted){x+=d.move.dx;z+=d.move.dz;}
  }
  assert(done,"The brain must navigate to a free interaction position and collect");
  assert.equal(bag.wood,1);
}

console.log("PASS: atomic pickup, inventory, true proximity, blocking resources and no oscillation");
