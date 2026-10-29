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
assert module.native_box_order("google/gemini-2.5-flash")=="ymin_xmin_ymax_xmax"
assert module.native_box_order("qwen/qwen3-vl-235b-a22b-instruct")=="xmin_ymin_xmax_ymax"
gemini={"objects":{label:{"visible":True,"box_2d":[200,120,265,180],
    "confidence":.94} for label in roles}}
converted=module.validate_boxes(gemini,roles,module.native_box_order("google/gemini-2.5-flash"))
assert converted["functional_edge"]["box_2d"]==[120,200,180,265]
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

# Real textured axe regression: the two independent vision passes disagreed
# about its physical BOTTOM and cutting EDGE. Only the Gemini-confirmed
# labeled rectangles may repair those locations; a numerical longest-axis
# heuristic is prohibited.
meshes=module.mesh_vision.glb_geometry(module.ROOT/
    "assets/experiments/props/marches_hache/trellis-v1/axe.glb")
_,views=module.mesh_vision.make_views(meshes)
real_points={
    "handle_butt": [0.3384636,-0.3916808,0.0331001],
    "grip_center": [0.128259,-0.1000625,-0.0007449],
    "working_head": [-0.1801326,0.3306219,0.0006004],
    "functional_edge": [-0.3051306,0.2297242,-0.0176757]}
annotated={key:{"local":value,"mesh":0,"primitive":0}
           for key,value in real_points.items()}
real_plan={"mesh_landmarks":{"points":annotated,
    "grips":{},"features":{"axe_head":{"origin":annotated["working_head"].copy(),
        "direction_tip":annotated["functional_edge"].copy()}}}}
native_regions={name:{"visible":True,"box_2d":list(box),"confidence":.9}
    for name,box in {
        "handle_butt":(443.1,925.9,500.3,945.6),
        "working_head":(374.2,206.7,608.9,450.2),
        "functional_edge":(272.2,360.8,343.1,456.1)}.items()}
fixed=module.reconcile_physical_regions(real_plan,meshes,views[2],native_regions)
assert set(fixed)=={"handle_butt","functional_edge"},fixed
for name in fixed:
    x,y=module.project_confirmed_point(real_plan["mesh_landmarks"]["points"][name],meshes,views[2])
    x0,y0,x1,y1=native_regions[name]["box_2d"]
    assert x0<=x<=x1 and y0<=y<=y1,(name,x,y)
assert (real_plan["mesh_landmarks"]["features"]["axe_head"]["direction_tip"]==
    real_plan["mesh_landmarks"]["points"]["functional_edge"])
print("PASS: second VLM's native boxes re-anchor real blade/butt, preserve semantic names")
