#!/usr/bin/env python3
"""No model has access to an already scaled weapon; pixel measurements are reproducible."""
import importlib.util
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("independent_object_size",root/"scripts/measure-prop-scale-blind.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
request="assets/experiments/props/marches_hache/trellis-v1/grip-scale-blind-request-v6.json"
cfg,paths,brief,out,hashes=m.inputs(request)
assert cfg["vision_model"]=="google/gemini-2.5-flash-lite"
assert set(paths)=={"generation_request","source_character","source_prop"}
assert not any("render" in key or "plan" in key for key in paths),paths
assert all("render" not in str(path) and "grip-plan" not in str(path) for path in paths.values())
assert "TWO-HANDED FOREST AXE" in m.vision_text(brief["prompt"])
assert "current" not in m.SYSTEM.lower()
assert "previous" not in m.SYSTEM.lower()
assert "1.1" not in m.SYSTEM
assert "1.1" not in m.vision_text(brief["prompt"])
raw={
"character_head_top":[.5,.10],"character_foot_bottom":[.5,.90],
"object_handle_butt":[.38,.70],"object_working_tip":[.62,.30],
"object_fully_visible":True,"character_fully_visible":True,
"recognizable_same_object":True,"perspective":"low_distortion",
"preferred_length_relative_character_height":.55,"confidence":.9,
"observations":"The object appears appreciably shorter than the full height of the wearer in the original character design."
}
out=m.calculate(raw,[800,1000])
assert .52<out["projected_length_ratio"]<.58,out
assert not out["manual_review_required"],out
raw["object_fully_visible"]=False
try: m.calculate(raw,[800,1000])
except ValueError as ex: assert "lacks full" in str(ex)
else: raise AssertionError("Missing source object must not be measured")
# The designed output can vary and is not fixed at the previous plan value.
raw["object_fully_visible"]=True
raw["preferred_length_relative_character_height"]=1.2
assert m.calculate(raw,[800,1000])["manual_review_required"]
print("PASS: independent proportions, no 3D screenshots or prior plans sent, ambiguous source rejects")
