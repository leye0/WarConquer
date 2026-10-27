#!/usr/bin/env python3
"""Offline safeguards: original source description and scale disagreement."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("grip_v3",root/"scripts/plan-prop-attachment-v3.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
req="assets/experiments/props/marches_hache/trellis-v1/grip-request-v3.json"
cfg,obj,char,out,source,brief,hashes=module.load(req)
assert "TWO-HANDED FOREST AXE" in brief
assert "practical rather than oversized ornamental fantasy proportions" in brief
assert cfg["object_image"]==json.loads(source.read_text())["output"]
assert hashes["generation_brief_sha256"]==module.digest(source)
assert out!=root/"assets/experiments/props/marches_hache/trellis-v1/grip-plan.json"
old=json.loads((root/"assets/experiments/props/marches_hache/trellis-v1/grip-plan.json").read_text())
example={**old["specifications"],
   "character_image_size_ratio":.74,
   "character_image_shows_full_object":True,
   "size_reasoning":"Concept art shows the full axe beside the character, enabling a relative silhouette comparison."}
try:
    module.validate(example)
except ValueError as err:
    assert "contradicts" in str(err),str(err)
else: raise AssertionError("Reject implausible 1.10 ratio versus 0.74 measured source ratio")
example["length_relative_character_height"]=.76
base,derived,scale=module.validate(example)
assert abs(base["length_relative_character_height"]-.76)<1e-7
assert scale["character_image_size_ratio"]==.74
example["character_image_shows_full_object"]=False
try: module.validate(example)
except ValueError as err:
    assert "full weapon" in str(err)
else:raise AssertionError("Reject ungrounded sizing without visible original weapon")
print("PASS: source generation description and relative-size evidence bound to the same item; legacy plan kept")
