#!/usr/bin/env python3
"""One-shot fal.ai textured GLB -> Uthana skin -> archived Mixamo motions.

This pipeline never projects or re-bakes UVs. The original fal material and
geometry are carried into the skinned output; unexpected texture loss stops it.
A prediction checkpoint prevents accidental duplicate paid rig submissions.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "assets/experiments/rig-ready-3d/marches_hache/tpose-v2"
MOTION = BASE / "motion/fal-mixamo-v1"
INPUT = BASE / "fal-textured.glb"
RIGGED = MOTION / "fal-rigged.glb"
PLAYABLE = MOTION / "warconquer-textured-playable.glb"
CHECKPOINT = MOTION / "rig-prediction.json"
REPORT = MOTION / "report.json"
REQUEST = ROOT / "fal-rig-request.json"
MODEL = "uthana/create-character-v1"
ACTIVE_UNIT = "marches_hache"

def set_unit(unit):
    """All paths derive from the selected JSON, not GitHub Actions."""
    global BASE, MOTION, INPUT, RIGGED, PLAYABLE, CHECKPOINT, REPORT, REQUEST, ACTIVE_UNIT
    if unit == "marches_hache":
        return
    from pathlib import Path
    import json
    if not isinstance(unit,str) or not unit or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in unit):
        raise ValueError("Invalid unit")
    manifest_path=ROOT / "data/units" / (unit+".json")
    doc=json.loads(manifest_path.read_text(encoding="utf8"))
    if doc.get("id")!=unit or doc.get("schema")!=1 or doc.get("adapter")!="manifest_v1":
        raise ValueError("Unsupported rig unit manifest")
    src=(ROOT/doc["body"]["glb"]).resolve()
    out=(ROOT/doc["body"]["rigged_glb"]).resolve()
    playable=(ROOT/doc["body"]["playable_glb"]).resolve()
    if not all(x.is_relative_to(ROOT/"assets/experiments/rig-ready-3d"/unit) for x in (src,out,playable)):
        raise ValueError("Cross-unit rig or animation path")
    BASE=src.parent
    MOTION=out.parent
    INPUT=src
    RIGGED=out
    PLAYABLE=playable
    CHECKPOINT=MOTION/"rig-prediction.json"
    REPORT=MOTION/"report.json"
    REQUEST=ROOT/"data/units"/unit/"rig-request.json"
    ACTIVE_UNIT=unit


def support(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

glb = support("wc_fal_glb_helpers", "scripts/build-mixamo-playable.py")
replicate_helpers = support("wc_replicate_helpers", "scripts/build-rig-ready-3d.py")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)

def approval():
    cfg = json.loads(REQUEST.read_text(encoding="utf-8"))
    if ACTIVE_UNIT != "marches_hache":
        exact = {
            "schema": 1, "unit": ACTIVE_UNIT,
            "source": str(INPUT.relative_to(ROOT)),
            "source_sha256": sha(INPUT),
            "rig_model": MODEL,
            "maximum_new_paid_rig_predictions": 1,
            "require_textured_output": True,
            "motion_source": "archived_mixamo_fbx",
        }
        if cfg != exact:
            raise ValueError("Selected unit rig request is not approved for one call")
        source, _ = glb.load_glb(INPUT)
        if not texture_stats(source)["valid"]:
            raise ValueError("Selected unit lacks embedded native UV texture")
        return cfg
    exact = {
        "schema": 1,
        "source": str(INPUT.relative_to(ROOT)),
        "source_sha256": "6f297890dc42f25640049b63a4c55ca12494bee62f37a590eb57573e68c8afb2",
        "rig_model": MODEL,
        "maximum_new_paid_rig_predictions": 1,
        "require_textured_output": True,
        "motion_source": "archived_mixamo_fbx",
    }
    if cfg != exact:
        raise ValueError("Fal rig request is not the reviewed single-call approval")
    if not INPUT.is_file() or sha(INPUT) != cfg["source_sha256"]:
        raise ValueError("Source fal GLB fingerprint mismatch; no paid call")
    source, _ = glb.load_glb(INPUT)
    if not texture_stats(source)["valid"]:
        raise ValueError("Source fal model lacks fully embedded UV texture")
    return cfg

def texture_stats(doc):
    images = doc.get("images", [])
    textures = doc.get("textures", [])
    materials = doc.get("materials", [])
    primitives = [p for mesh in doc.get("meshes", []) for p in mesh.get("primitives", [])]
    uv = [p for p in primitives if "TEXCOORD_0" in p.get("attributes", {})]
    textured = []
    for p in primitives:
        material = materials[p["material"]] if p.get("material", -1) in range(len(materials)) else {}
        base_color = material.get("pbrMetallicRoughness", {}).get("baseColorTexture", {})
        index = base_color.get("index", -1)
        if index in range(len(textures)):
            src = textures[index].get("source", -1)
            if src in range(len(images)) and "TEXCOORD_0" in p.get("attributes", {}):
                textured.append(p)
    embedded = [i for i in images if "bufferView" in i or i.get("uri", "").startswith("data:")]
    return {
        "valid": bool(primitives and uv and textured and len(embedded) == len(images) and images),
        "mesh_count": len(doc.get("meshes", [])),
        "primitive_count": len(primitives),
        "uv_primitives": len(uv),
        "textured_primitives": len(textured),
        "image_count": len(images),
        "embedded_images": len(embedded),
        "material_count": len(materials),
        "skin_count": len(doc.get("skins", [])),
        "joint_count": sum(len(s.get("joints", [])) for s in doc.get("skins", [])),
        "skinned_primitives": sum("JOINTS_0" in p.get("attributes", {}) and
                                  "WEIGHTS_0" in p.get("attributes", {}) for p in primitives),
        "animation_count": len(doc.get("animations", [])),
    }

def rig_submit():
    if RIGGED.exists() or CHECKPOINT.exists():
        print("SAFE SKIP: previously submitted or completed rig inference")
        return
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN secret missing; no submission")
    import replicate
    api = replicate.Client(api_token=token)
    version = api.models.get(MODEL).latest_version.id
    if not version:
        raise RuntimeError("Uthana has no advertised model version")
    # No pre-existing approval checkpoint means exactly one allowed attempt.
    with INPUT.open("rb") as source:
        prediction = api.predictions.create(version=version, input={
            "character_file": source,
            "auto_rig": True,
            "front_facing": True,
        })
    if not prediction.id:
        raise RuntimeError("Provider returned no ID: stop, never retry automatically")
    save(CHECKPOINT, {
        "model": MODEL, "version": version, "prediction_id": prediction.id,
        "source_sha256": sha(INPUT), "paid_predictions_submitted": 1,
        "initial_status": prediction.status,
    })
    print("Uthana one-shot rig prediction accepted:", prediction.id)

def rig_collect():
    if RIGGED.exists():
        print("Rigged fal GLB already downloaded")
        return
    if not CHECKPOINT.exists():
        raise RuntimeError("No prior prediction checkpoint; do not resubmit")
    rec = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    if rec.get("source_sha256") != sha(INPUT) or rec.get("paid_predictions_submitted") != 1:
        raise RuntimeError("Stored rig prediction fingerprint mismatch")
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing Replicate secret for collection")
    import replicate
    api = replicate.Client(api_token=token)
    deadline = time.monotonic() + 24 * 60
    prediction = None
    while time.monotonic() < deadline:
        prediction = api.predictions.get(rec["prediction_id"])
        print("Uthana collection:", prediction.status, flush=True)
        if prediction.status in ("succeeded", "failed", "canceled"):
            break
        time.sleep(15)
    if not prediction or prediction.status != "succeeded":
        raise RuntimeError("Rig prediction not succeeded; use checkpoint to resume, never resubmit")
    uri = replicate_helpers.uri_for_glb(prediction.output)
    if not uri:
        raise ValueError("Uthana returned no GLB URL; do not resubmit")
    MOTION.mkdir(parents=True, exist_ok=True)
    replicate_helpers.download_glb(uri, RIGGED)
    doc, _ = glb.load_glb(RIGGED)
    stats = texture_stats(doc)
    save(MOTION / "rig-qa.json", {
        "source_sha256": sha(INPUT), "rigged_sha256": sha(RIGGED),
        "source_texture": texture_stats(glb.load_glb(INPUT)[0]),
        "result": stats,
        "preserved_native_uv_texture": stats["valid"],
        "note": "Native UVs must be present; screenshot review will assess visual quality.",
    })
    if not (stats["valid"] and stats["joint_count"] == 52 and
            stats["skin_count"] >= 1 and stats["skinned_primitives"] >= 1):
        raise RuntimeError("Uthana rig did not preserve a textured 52-bone skinned GLB")
    print("RIG_AND_TEXTURE_VALID", json.dumps(stats))

def animate():
    if not RIGGED.exists():
        raise RuntimeError("Rigged and textured fal GLB not collected")
    folder = os.environ.get("MIXAMO_CONVERTED_DIR", "")
    if not folder:
        raise ValueError("MIXAMO_CONVERTED_DIR missing")
    doc, binary = glb.load_glb(RIGGED)
    before = texture_stats(doc)
    if not before["valid"] or before["joint_count"] != 52 or not before["skinned_primitives"]:
        raise RuntimeError("Cannot animate untextured or unskinned model")
    original_skins = json.dumps(doc["skins"], sort_keys=True)
    original_materials = json.dumps(doc.get("materials", []), sort_keys=True)
    original_textures = json.dumps(doc.get("textures", []), sort_keys=True)
    original_images = json.dumps(doc.get("images", []), sort_keys=True)
    extras = [
        ("Idle_Relaxed", "Unarmed_Idle_01_2"),
        ("Idle_Wipe", "Wiping_Sweat"),
        ("Idle_Magic", "Standing_Idle_03"),
        ("Cast_Fireball", "Standing_1H_Magic_Attack_01"),
    ]
    if ACTIVE_UNIT != "marches_hache":
        # No real bow draw/release clip is available yet. Retain neutral idle,
        # walking and running; never label a downward AXE strike as archery.
        extras=[("Idle_Relaxed","Unarmed_Idle_01_2"),("Idle_Wipe","Wiping_Sweat")]
    clips = glb.transfer_clips(doc, binary, Path(folder),
                               clip_stems={"Idle": "Standard_Idle"}, extra_clips=extras)
    if ACTIVE_UNIT != "marches_hache":
        doc["animations"]=[a for a in doc.get("animations",[])
                           if not a.get("name","").startswith("Attack_")]
        clips=[c for c in clips if not (c.get("name","").startswith("Attack_")
                                       if isinstance(c,dict) else str(c).startswith("Attack"))]
    expected=8 if ACTIVE_UNIT=="marches_hache" else 5
    if len(clips)!=expected or len(doc.get("animations",[]))!=expected:
        raise RuntimeError("Selected unit's genuine Mixamo clip count mismatch")
    if (json.dumps(doc["skins"], sort_keys=True) != original_skins or
        json.dumps(doc.get("materials", []), sort_keys=True) != original_materials or
        json.dumps(doc.get("textures", []), sort_keys=True) != original_textures or
        json.dumps(doc.get("images", []), sort_keys=True) != original_images):
        raise RuntimeError("Native fal skin or texture altered unexpectedly")
    glb.write_glb(doc, binary, PLAYABLE)
    output, _ = glb.load_glb(PLAYABLE)
    after = texture_stats(output)
    if not (after["valid"] and after["joint_count"] == 52 and
            after["animation_count"] == expected and after["skinned_primitives"] >= 1):
        raise RuntimeError("Playable GLB fails material/skeleton/motion validation")
    report = {
        "status": "generated-awaiting-live-browser-QA",
        "source": str(INPUT.relative_to(ROOT)),
        "rigged_model": str(RIGGED.relative_to(ROOT)),
        "playable_model": str(PLAYABLE.relative_to(ROOT)),
        "output_sha256": sha(PLAYABLE), "bytes": PLAYABLE.stat().st_size,
        "texture_method": "original fal.ai native embedded UV/PBR, no new projection",
        "rigging_model": MODEL, "rigging_prediction": json.loads(CHECKPOINT.read_text())["prediction_id"],
        "animations_origin": "genuine archived Mixamo FBX converted with FBX2glTF",
        "texture_and_skeleton": after,
        "animation_clips": clips,
        "visual_QA": "pending: joints, materials, walk, run; bow draw/release not yet implemented",
    }
    save(REPORT, report)
    print("PLAYABLE_VALID", json.dumps(report))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("validate", "rig-submit", "rig-collect", "animate"), required=True)
    parser.add_argument("--unit", default="marches_hache")
    args=parser.parse_args()
    set_unit(args.unit)
    stage=args.stage
    approval()
    if stage == "validate":
        print("Approved original fal UV-textured source and SHA256; ready for one Uthana submission")
    elif stage == "rig-submit":
        rig_submit()
    elif stage == "rig-collect":
        rig_collect()
    else:
        animate()

if __name__ == "__main__":
    main()
