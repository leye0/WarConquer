#!/usr/bin/env python3
"""Ensure low-cost vision reviews cannot be anchored to previous plan scales."""
import base64
import importlib.util
import io
import json
from pathlib import Path
from PIL import Image

root=Path(__file__).resolve().parents[1]
path=root/"scripts/review-prop-in-situ.py"
spec=importlib.util.spec_from_file_location("review_prop",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
config="assets/experiments/props/marches_hache/trellis-v1/grip-render-review-request-v5.json"
cfg,paths,source,previous,semantic,out,hashes=m.prepare(config)
assert cfg["vision_model"]=="google/gemini-2.5-flash-lite"
assert out.name=="grip-plan-v5.json"
assert previous["specifications"]["length_relative_character_height"]==1.1
assert semantic["specifications"]["length_relative_character_height"]==1.1
actual=m.vision_text(source["prompt"])
assert "TWO-HANDED FOREST AXE" in actual, "original design identity must be given"
assert "1.1" not in actual, "old relative size must not be shown to the LLM"
assert "Previous vision" not in actual and "CURRENT ACTUAL RENDERED" not in actual
assert "1.1" not in m.PROMPT
assert "1.9 world units" not in m.PROMPT, "world normalizer is not source scale evidence"
for key in ("current_render_idle","current_render_attack"):
 image,size=m.image(paths[key],arena=True)
 data=base64.b64decode(image["image_url"]["url"].split(",",1)[1])
 assert len(data)==size and size<750000
 with Image.open(io.BytesIO(data)) as cropped:
  with Image.open(paths[key]) as original:
   assert cropped.width<original.width*.75,"UI sidebar must not enter LLM image"
   assert cropped.height<original.height*.85
print("PASS: source design preserved, previous 110% hidden from text prompt, UI cropped from live images")
