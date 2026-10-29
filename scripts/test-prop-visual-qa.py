#!/usr/bin/env python3
"""Offline regression: every real frame and phase-specific vision rule counts."""
import copy
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location("wc_visual_qa",
    Path(__file__).with_name("verify-prop-visual-qa.py"))
qa=importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)

names=["front","walk","action","action_mid_1","action_mid_2"]
def positive(name):
    return {"id":name,"hands_contact":True,
        "action_feature_correct":True,"orientation_constraints_met":True,
        "collision_free":True,"confidence":.95,"issues":[],"regions":[]}
good={"go":True,"confidence":.94,"issues":[],
    "explanation":"Both hands and action features are source-confirmed in all sampled frames.",
    "frames":[positive(name) for name in names]}
assert qa.check_response(good,names)

for broken in (
    lambda p:p["frames"][2].update(hands_contact=False),
    lambda p:p["frames"][2].update(action_feature_correct=False),
    lambda p:p["frames"][0].update(orientation_constraints_met=False),
    lambda p:p["frames"][1].update(collision_free=False),
    lambda p:p["frames"][4].update(confidence=.4),
    lambda p:p["frames"][3].update(issues=["Second palm is floating"]),
    lambda p:p.update(go=False),
):
    answer=copy.deepcopy(good)
    broken(answer)
    assert not qa.check_response(answer,names)

for broken in (
    lambda p:p["frames"].pop(),
    lambda p:p["frames"][2].update(id="walk"),
    lambda p:p["frames"][0].pop("hands_contact"),
    lambda p:p["frames"][0].update(hands_contact="unknown"),
):
    answer=copy.deepcopy(good)
    broken(answer)
    try:qa.check_response(answer,names)
    except ValueError:pass
    else:raise AssertionError("Vision QA accepted missing or invented per-frame proof")

assert "heavy end BELOW" not in qa.PROMPT
assert "optional secondary-hand" not in qa.PROMPT
assert "Two-hand modes REQUIRE two visible contacts" in qa.PROMPT
print("PASS: every sampled pose requires source-specific visible contact and direction")
