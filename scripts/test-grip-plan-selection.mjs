#!/usr/bin/env node
// Regression: the published catalog reads one canonical plan per equipment.
// Git history, not sibling v3/v4/v5 files, preserves earlier generations.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { inventory } from "./serve-character-lab.mjs";

const catalog=inventory();
for(const unit of catalog.characters)for(const prop of unit.props){
  const plan=JSON.parse(readFileSync(new URL("../"+prop.gripPlan.replace(/^\//,""),import.meta.url),"utf8"));
  assert([2,3,4].includes(plan.schema));
  assert.equal(plan.inputs.object_glb,prop.model.replace(/^\//,""));
  assert(prop.gripPlan.endsWith("/grip-plan.json"));
  assert.equal(prop.gripReviewStatus,plan.visual_qa?.status||"baseline");
  assert(typeof prop.id==="string"&&prop.id.length>0);
}

// The source-of-truth is the current manifest. A vision rejection is a real
// state, not a reason to hard-code a special fixture's earlier direction.
console.log("PASS: inventory uses one canonical grip plan and current review per prop");
