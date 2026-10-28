#!/usr/bin/env node
import assert from "node:assert/strict";
import {createRequire} from "node:module";
const require=createRequire(import.meta.url);
const {hit}=require("./perception-combat.js");

{
  const items=[{id:"enemy",kind:"unit",team:"red",x:2,z:0,health:100,name:"Raider"},
    {id:"wood",kind:"resource",x:1,z:0}];
  const actor={x:.6,z:0};
  const strike=()=>hit({items,entityId:"enemy",actor,reach:1.6,damage:34});
  assert.equal(hit({items,entityId:"wood",actor}).reason,"not_enemy");
  assert.equal(hit({items,entityId:"enemy",actor:{x:0,z:0}}).reason,"out_of_range");
  assert.equal(strike().health,66);
  assert.equal(strike().health,32);
  const last=strike();
  assert.equal(last.health,0);assert(last.defeated);
  assert.equal(last.damage,32,"Damage cannot exceed remaining health");
  assert.equal(items.some(o=>o.id==="enemy"),false,"Defeated enemy leaves the world");
  assert.equal(strike().reason,"not_found","No double hit on a removed enemy");
}
{
  const items=[{id:"ally",kind:"unit",team:"blue",x:0,z:0}];
  assert.equal(hit({items,entityId:"ally",actor:{x:0,z:0}}).reason,"not_enemy");
  assert.equal(items.length,1);
}

console.log("PASS: melee hit range, damage, friendly safety and defeat");
