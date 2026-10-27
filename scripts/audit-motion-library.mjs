#!/usr/bin/env node
/** Audit real Mixamo sources vs animations actually embedded in the playable GLB.
 * Offline only; no file downloads, generative inference or API credentials.
 */
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createRequire} from "node:module";
const require=createRequire(import.meta.url);
const {resolve}=require("./equipment-animation-policy.js");
const data=JSON.parse(readFileSync(new URL("../data/motion-library.json",import.meta.url),"utf8"));
assert.equal(data.schema,1);
const raw=readFileSync(new URL("../"+data.playable,import.meta.url));
assert.equal(raw.toString("ascii",0,4),"glTF");
assert.equal(raw.readUInt32LE(4),2);
const length=raw.readUInt32LE(12);
const gltf=JSON.parse(raw.subarray(20,20+length).toString("utf8"));
const actual=(gltf.animations||[]).map(a=>a.name||"");
const included=data.clips.filter(c=>c.included);
assert.equal(included.length,8);
assert.equal(new Set(included.map(c=>c.source_fbx)).size,included.length);
for(const clip of included){
 assert(clip.source_fbx.endsWith(".fbx"));
 assert(actual.some(name=>name.startsWith(clip.group_prefix)),
  "Missing real embedded animation "+clip.group_prefix+" from "+clip.source_fbx);
}
const equipped=resolve({object_kind:"axe",hold_mode:"two_hands"},actual);
assert(equipped.ready && equipped.motion,"Axe must have authentic compatible attack");
const bow=resolve({object_kind:"bow",hold_mode:"two_hands"},actual);
assert(!bow.ready && bow.missing.includes("compatible_animation"),
 "An existing axe animation must not masquerade as an archery animation");
const option=process.argv[2]||"";
if(option){
 const requested=resolve({object_kind:option},actual);
 console.log(JSON.stringify({equipment:option,ready:requested.ready,
  actual_motion:requested.motion,missing:requested.missing,
  suggested_mixamo_queries:requested.motionQueries},null,2));
}else{
 console.log("PASS: "+included.length+" genuine Mixamo animations verified inside playable GLB");
 console.log("Axe action: "+equipped.motion+"; bow action not available without real bow clip, adapter and release event");
}
