#!/usr/bin/env node
// Regression: the published catalog reads one canonical plan per equipment.
// Git history, not sibling v3/v4/v5 files, preserves earlier generations.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { inventory } from "./serve-character-lab.mjs";

const catalog=inventory();
for(const unit of catalog.characters)for(const prop of unit.props){
  assert(["baseline","candidate","approved"].includes(prop.gripReviewStatus));
  const plan=JSON.parse(readFileSync(new URL("../"+prop.gripPlan.replace(/^\//,""),import.meta.url),"utf8"));
  assert([2,3,4].includes(plan.schema));
  assert.equal(plan.inputs.object_glb,prop.model.replace(/^\//,""));
  assert(prop.gripPlan.endsWith("/grip-plan.json"));
  if(prop.gripReviewStatus!=="baseline")assert.equal(plan.visual_qa.status,prop.gripReviewStatus);
}

// Concrete regression: the source-matched in-situ review must already be
// merged into the canonical plan, never selected by a version lookup at runtime.
const warrior=catalog.characters.find(c=>c.id==="marches_hache");
const axe=warrior?.props.find(p=>p.id.endsWith("/trellis-v1"));
assert(axe,"Expected the existing real axe geometry in the generic inventory");
assert.equal(axe.gripReviewStatus,"candidate");
assert(axe.gripPlan.endsWith("/grip-plan.json"));
const proposal=JSON.parse(readFileSync(new URL("../"+axe.gripPlan.slice(1),import.meta.url),"utf8"));
assert.equal(proposal.specifications.head_direction,"toward_elbow");
assert.equal(proposal.vision_review.change_needed,true);
console.log("PASS: exactly one canonical grip plan per prop, with reviewed direction");
