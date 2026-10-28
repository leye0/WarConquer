#!/usr/bin/env python3
"""Offline tests for generic equipment discovery, requests and frame semantics."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


equipment = module("test_generic_equipment", "unit-equipment.py")
trellis = module("test_generic_trellis", "build-prop-trellis.py")
grip = module("test_generic_grip", "plan-prop-attachment.py")

with tempfile.TemporaryDirectory(prefix="wc-equipment-offline-") as location:
    root = Path(location)
    original = "assets/concepts/couronne/units/example.png"
    obj = "assets/concepts/couronne/objects/example_bow.png"
    for rel in (original, obj):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        im = Image.new("RGBA", (1024, 1024), (0,0,0,0))
        ImageDraw.Draw(im).rectangle((180,120,800,900),fill=(130,80,40,255))
        im.save(path)
    seed = {"schema":1,"id":"example","name":"Exemple","source":{"character_image":original},
        "equipment":[{"id":"bow","kind":"bow","source_image":obj,
                      "source_request":"data/units/example/bow-image-request.json"}]}
    path = root / "data/units/example.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seed))
    request = {"prompt":"Original handmade longbow of bent dark oak with an ivory grip and a thin string",
        "output":obj,"references":[original]}
    brief = root / "data/units/example/bow-image-request.json"
    brief.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text(json.dumps(request))
    with patch.object(equipment,"ROOT",root),patch.object(trellis,"ROOT",root):
        identified = equipment.describe("example", paid=False)
        assert len(identified)==1 and identified[0]["kind"]=="bow"
        assert equipment.descriptors("example")==identified
        prop={"id":"bow","kind":"bow","description":identified[0]["description"],
            "source_image":obj,"source_request":"data/units/example/bow-image-request.json",
            "glb":"assets/experiments/props/example/bow/mesh.glb",
            "trellis_request":"data/units/example/bow-trellis-request.json",
            "interaction_request":"assets/experiments/props/example/bow/interaction-request.json",
            "interaction":"assets/experiments/props/example/bow/interaction-contract.json",
            "physical_size_request":"assets/experiments/props/example/bow/physical-size-request.json",
            "physical_size":"assets/experiments/props/example/bow/physical-size.json",
            "grip_request":"assets/experiments/props/example/bow/grip-request.json",
            "grip":"assets/experiments/props/example/bow/grip-plan.json"}
        equipment.prepare_requests(seed,prop)
        # Existing human-authored brief is valid source evidence for legacy
        # objects even when no separate vision description was persisted.
        equipment.prepare_requests(seed,{k:v for k,v in prop.items() if k!="description"})
        _, img, dest = trellis.load(prop["trellis_request"])
        assert img == root / obj and dest == root / prop["glb"]
        assert json.loads(brief.read_text())==request, "Existing human-authored brief is preserved"
        physical=json.loads((root/prop["physical_size_request"]).read_text())
        assert physical["generation_request"]==prop["source_request"]
        semantic=json.loads((root/prop["grip_request"]).read_text())
        assert semantic["schema"]==2
        assert semantic["object_glb"]==prop["glb"]
        assert semantic["interaction_contract"]==prop["interaction"]
        interaction=json.loads((root/prop["interaction_request"]).read_text())
        assert interaction["object_image"]==obj
        assert interaction["motion_library"]=="data/motion-library.json"
        assert interaction["maximum_paid_requests"]==1

# Frame grip near the center is valid regardless of object_kind (geometry,
# not a handcrafted transform for a named weapon).
spec = {"object_kind":"bow", "grip_geometry":"frame", "hold_mode":"one_hand",
    "dominant_hand":"left", "handle_butt":[.5,.1],"handle_near_head":[.5,.9],
    "grip_point":[.5,.5],"head_center":[.5,.1],"action_edge":[.6,.5],
    "head_direction":"up", "edge_direction":"forward",
    "length_relative_character_height":.7,"palm_from_wrist":.5,
    "confidence":.9,"explanation":"Stable central frame grip shown in the original unit concept"}
fit=grip.validate(spec)
assert fit["supported_by_current_geometry_fitter"] is True
assert abs(fit["grip_fraction_from_butt"]-.5)<.01
contract={"characterization":{"object_kind":"bow","grips":[
    {"id":"bow_handhold","point":[.5,.5]}],"modes":[
    {"id":"carrying","phase":"carry","hands":1,
     "primary_hand":"left","primary_grip":"bow_handhold"},
    {"id":"drawing","phase":"use","hands":2,
     "primary_hand":"left","primary_grip":"bow_handhold"}]}}
grip.check_grip_consistency(spec,contract)
for change in ({"hold_mode":"two_hands"},{"dominant_hand":"right"},
               {"grip_point":[.9,.9]},{"object_kind":"axe"}):
    mutated={**spec,**change}
    try:grip.check_grip_consistency(mutated,contract)
    except ValueError:pass
    else:raise AssertionError("Fitter overrode the prior visual contract: "+repr(change))
print("PASS: generic equipment image provenance, request derivation, TRELLIS and bow frame")
