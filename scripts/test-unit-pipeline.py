#!/usr/bin/env python3
"""Regression tests for project-owned WarConquer build orchestration (no paid API)."""
from __future__ import annotations
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("wc_unit_pipeline",root/"scripts/unit-pipeline.py")
pipeline=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

m=pipeline.manifest("marches_hache")
assert m["id"]=="marches_hache"
assert m["adapter"]=="legacy_marches_hache"
assert [e["id"] for e in m["equipment"]]==["axe"]
assert pipeline.unit_ids()==["couronne_archer","marches_hache"],pipeline.unit_ids()
archer=pipeline.manifest("couronne_archer")
assert archer["id"]=="couronne_archer"
assert archer["equipment"][0]["kind"]=="bow"
assert archer["adapter"]=="manifest_v1"
assert "equipment_identify" in pipeline.STAGES
assert pipeline.state(archer,"source")["ready"],"Archer original concept exists"
assert pipeline.state(archer,"turnaround")["ready"],"Four archer views must exist after real pilot"
assert pipeline.state(archer,"body")["ready"],"Archer fal GLB must be independently generated"
assert "/couronne_archer/" in pipeline.assets_for(archer,"rig")[0], "Archer cannot reuse the Marches rig"
assert pipeline.main(["run","--unit","couronne_archer","--stage","source"])==0
assert pipeline.main(["run","--unit","couronne_archer","--stage","all","--dry-run"])==0
assert pipeline.main(["run","--unit","couronne_archer","--stage","body","--dry-run"])==0
assert pipeline.main(["run","--unit","couronne_archer","--stage","rig","--dry-run"])==0
with patch.object(pipeline,"state",return_value={"ready":False,"files":{"missing-rig.glb":"missing"}}),patch.object(pipeline,"execute") as execute:
 try:pipeline.main(["run","--unit","couronne_archer","--stage","rig"])
 except pipeline.PipelineError as e:assert "--allow-paid" in str(e)
 else:raise AssertionError("3D paid generation without consent")
 execute.assert_not_called()
assert set(pipeline.PAID).issubset(pipeline.STAGES)
for stage in pipeline.STAGES:
    st=pipeline.state(m,stage)
    assert st["ready"],(stage,st)
assert pipeline.inspect(m["equipment"][0]["physical_size"])=="ready"
assert len(pipeline.assets_for(m,"turnaround"))==4
assert any(x.endswith("warconquer-textured-playable.glb")
           for x in pipeline.assets_for(m,"integrate"))
for bad in ("../secrets","/tmp/secrets","", "OTHER UNIT"):
    try:pipeline.manifest(bad)
    except pipeline.PipelineError:pass
    else:raise AssertionError("Unsafe unit ID allowed: "+repr(bad))
try:pipeline.safe_path("../hidden")
except pipeline.PipelineError:pass
else:raise AssertionError("Traversal allowed")
bad=dict(m)
bad["id"]="not_marches_hache"
assert pipeline.execute.__code__.co_names.count("ensure_adapter")==0, "No weapon-specific adapter gate"

# A newly created unit does not need precomputed paths, a 3D generator
# adapter or an equipment-specific script. The source seed can be minimal.
with tempfile.TemporaryDirectory(prefix="wc-unit-minimal-") as location:
    temp=Path(location)
    units=temp/"data/units"
    units.mkdir(parents=True)
    (units/"new_unit.json").write_text(json.dumps({"schema":1,"id":"new_unit",
        "name":"Nouvelle unité","source":{"character_image":"assets/concepts/couronne/units/new.png"},
        "equipment":[{"id":"object","kind":"other"}]}))
    with patch.object(pipeline,"ROOT",temp),patch.object(pipeline,"UNITS",units),patch.object(
            pipeline,"equipment_tools",return_value=SimpleNamespace(descriptors=lambda unit:[])):
        generated=pipeline.manifest("new_unit")
        assert generated["adapter"]=="manifest_v1"
        assert generated["source"]["views"]["front"].endswith("/new_unit/tpose-v1/front.png")
        assert generated["body"]["glb"].endswith("/new_unit/tpose-v1/fal-textured.glb")
        assert generated["equipment"][0]["glb"]=="assets/experiments/props/new_unit/object/mesh.glb"

# Missing outputs require explicit authorization; do not even invoke Python scripts.
missing={"ready":False,"files":{"missing.glb":"missing"}}
with patch.object(pipeline,"state",return_value=missing),patch.object(pipeline,"execute") as do:
    try:pipeline.main(["run","--unit","marches_hache","--stage","object_size"])
    except pipeline.PipelineError as e:assert "--allow-paid" in str(e)
    else:raise AssertionError("Missing paid stage was not blocked")
    do.assert_not_called()
    assert pipeline.main(["run","--unit","marches_hache","--stage","object_size","--dry-run"])==0
    do.assert_not_called()

assert pipeline.main(["run","--unit","marches_hache","--stage","all","--dry-run"])==0
assert pipeline.main(["status","--unit","marches_hache","--stage","object_size","--json"])==0
print("PASS: per-unit manifest, staged outputs, safe paths, no paid rebuild by default")
