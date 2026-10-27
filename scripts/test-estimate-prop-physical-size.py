#!/usr/bin/env python3
"""Cheap equipment sizing is metric, source-only, and independent of rigging."""
import importlib.util
from pathlib import Path

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("physical_size",root/"scripts/estimate-prop-physical-size.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
cfg,paths,description,out,hashes=m.load(
 "assets/experiments/props/marches_hache/trellis-v1/physical-size-request.json")
assert cfg["vision_model"]=="google/gemini-2.5-flash-lite"
assert out.name=="physical-size.json"
assert set(paths)=={"object_image","character_image","generation_request"}
assert "TWO-HANDED FOREST AXE" in description
assert "1.1" not in description and "1.1" not in m.PROMPT
assert "centimetres".lower() in m.PROMPT.lower()
assert set(m.FIELDS)=={"estimated_length_cm","confidence","reason"}
m.validate({"estimated_length_cm":115,"confidence":.7,"reason":"Reasonable axe size given the original design"})
for invalid in (-15,0,float("nan"),1001):
 try:
  m.validate({"estimated_length_cm":invalid,"confidence":.7,"reason":"Plausible object sizing"})
 except ValueError:pass
 else:raise AssertionError("Invalid length accepted")
print("PASS: original object description, two images, centimetres; no prior plan or ratio")
