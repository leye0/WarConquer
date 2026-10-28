#!/usr/bin/env node
// Regression: the published catalog must not silently ignore a source-matched
// in-situ attachment correction and fall back to an older, opposite direction.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { inventory } from "./serve-character-lab.mjs";

const catalog=inventory();
for(const unit of catalog.characters)for(const prop of unit.props){
  assert(["baseline","candidate","approved"].includes(prop.gripReviewStatus));
  const plan=JSON.parse(readFileSync(new URL("../"+prop.gripPlan.replace(/^\//,""),import.meta.url),"utf8"));
  assert([2,3,4].includes(plan.schema));
  assert.equal(plan.inputs.object_glb,prop.model.replace(/^\//,""));
  if(prop.gripReviewStatus!=="baseline"){
    assert.equal(plan.schema,4);
    assert.equal(plan.visual_qa.status,prop.gripReviewStatus);
    assert.equal(plan.vision_review.change_needed,true);
  }
}

// Concrete regression asset: an older semantic plan pointed this weapon's
// working head toward the fingers. A later in-situ visual review corrected it
// toward the elbow. The catalog must use the reviewed direction for testing.
const warrior=catalog.characters.find(c=>c.id==="marches_hache");
const axe=warrior?.props.find(p=>p.id.endsWith("/trellis-v1"));
assert(axe,"Expected the existing real axe geometry in the generic inventory");
assert.equal(axe.gripReviewStatus,"candidate");
assert(axe.gripPlan.endsWith("/grip-plan-v5.json"));
const proposal=JSON.parse(readFileSync(new URL("../"+axe.gripPlan.slice(1),import.meta.url),"utf8"));
assert.equal(proposal.specifications.head_direction,"toward_elbow");
console.log("PASS: generic vision-reviewed grip selection and real 180° axe correction");
