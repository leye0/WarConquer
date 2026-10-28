#!/usr/bin/env node
// Equipment compatibility is based on actual animation names, never guesses.
import assert from "node:assert/strict";
import {createRequire} from "node:module";
const require=createRequire(import.meta.url);
const {profiles,normalizeKind,resolve}=require("./equipment-animation-policy.js");
const existing=["Idle_Mixamo_WithAxe","Walk_Mixamo_WithAxe",
  "Run_Mixamo_WithAxe","Attack_Mixamo_WithAxe",
  "Cast_Fireball_Mixamo"];
const axe=resolve({object_kind:"axe",hold_mode:"two_hands"},existing);
assert.equal(axe.ready,true);
assert.equal(axe.motion,"Attack_Mixamo_WithAxe");
assert.equal(axe.qualityWarning,"secondary_hand_not_constrained");
assert.equal(resolve({object_kind:"bow"},existing).ready,false,
  "Do not shoot a bow using a downward axe animation");
assert(resolve({object_kind:"bow"},existing).missing.includes("arrow_release"));
assert(resolve({object_kind:"shield"},existing).missing.includes("compatible_animation"));
assert.equal(resolve({object_kind:"sword"},existing).motion,null);
assert.equal(resolve({object_kind:"other"},existing).ready,false);
assert.equal(normalizeKind("__unknown__"),"other");
assert(Object.keys(profiles).length>=10);
for(const [kind,entry] of Object.entries(profiles)){
  for(const pattern of entry.patterns)new RegExp(pattern,"i");
  assert.equal(resolve({object_kind:kind},[]).kind,kind);
}
const bow=resolve({object_kind:"bow"},["Bow_Shoot_Mixamo"],["arrow_release"]);
assert(bow.ready,"A rigid bow is attachable with one hand; a real shot only requires a compatible clip/event");
assert.equal(bow.needsSecondaryHandIK,false);
assert.equal(bow.motion,"Bow_Shoot_Mixamo");
console.log("PASS: 12 equipment categories, strict animation matching, no imaginary bow shooting");
