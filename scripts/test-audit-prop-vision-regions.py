#!/usr/bin/env python3
"""Offline regressions for Studio's labeled 0..1000 vision rectangle convention."""
import importlib.util
import io
import json
from pathlib import Path

from PIL import Image

path=Path(__file__).with_name("audit-prop-vision-regions.py")
spec=importlib.util.spec_from_file_location("wc_studio_prop_bbox_audit",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

contract=json.loads((module.ROOT/
    "assets/experiments/props/marches_hache/trellis-v1/interaction-contract.json").read_text())
semantic=contract["characterization"]
roles=module.expected_labels(semantic)
assert set(roles)=={"handle_butt","grip_center","working_head",
    "functional_edge","grip_lower_haft","grip_upper_haft","axe_head"}
assert not any("point" in role or "origin" in role for role in roles)

answer={"objects":{label:{"visible":True,
    "box_2d":[120,200,180,265],"confidence":.94} for label in roles}}
parsed=module.parse_response("```json\n"+json.dumps(answer)+"\n```")
assert parsed==answer
boxes=module.validate_boxes(parsed,roles)
assert boxes["functional_edge"]["box_2d"]==[120,200,180,265]
image=module.render_overlay(Image.new("RGB",(510,510),"white"),boxes,
    {"functional_edge":[150,230]})
assert Image.open(io.BytesIO(image)).size==(510,510)
focus=module.named_crops(Image.new("RGB",(510,510),"white"),roles,
    {name:[480,600] for name in roles})
assert all(Image.open(io.BytesIO(c["image"])).size==(720,720)
           for c in focus.values())
centered={name:{"visible":True,"box_2d":[400,400,600,600],"confidence":.9}
          for name in roles}
mapped=module.remap_crop_boxes(centered,focus,510)
assert all(x["box_2d"][0]<=480<=x["box_2d"][2]
    and x["box_2d"][1]<=600<=x["box_2d"][3] for x in mapped.values())

wrong=json.loads(json.dumps(answer));wrong["objects"]["axe_head"]["box_2d"]=[10,20,30]
try:module.validate_boxes(wrong,roles)
except ValueError as error:assert "box_2d" in str(error)
else:raise AssertionError("Accepted missing 4-point physical region")

wrong=json.loads(json.dumps(answer));wrong["objects"]["fictional_grip"]={"visible":True,
    "box_2d":[20,40,50,70],"confidence":.95}
try:module.validate_boxes(wrong,roles)
except ValueError as error:assert "invented" in str(error)
else:raise AssertionError("Invented semantic grip not blocked")

print("PASS: Studio 0..1000 labeled bboxes, exact IDs and visible review overlays")
