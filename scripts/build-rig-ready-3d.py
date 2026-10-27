#!/usr/bin/env python3
"""Resumable approved four-T-pose to Hunyuan GLB to Uthana rig pipeline.

This stage stays disabled until a reviewed request containing all four
SHA-256 fingerprints is explicitly committed. No automatic paid retries.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "rig-ready-3d-request.json"
SOURCE = ROOT / "assets/experiments/rig-source-turnaround/marches_hache/tpose-v1"
OUTPUT = ROOT / "assets/experiments/rig-ready-3d/marches_hache/tpose-v1"
ORDER = ("front", "back", "left", "right")
MESH_MODEL = "tencent/hunyuan3d-2mv"
RIG_MODEL = "uthana/create-character-v1"
MESH_VERSION = "71798fbc3c9f7b7097e3bb85496e5a797d8b8f616b550692e7c3e176a8e9e5db"
MESH_SETTINGS = {
    "steps": 30, "guidance_scale": 5, "octree_resolution": 256,
    "target_face_num": 25000, "remove_background": False,
    "randomize_seed": False, "seed": 1234, "file_type": "glb",
}
TERMINAL = {"succeeded", "failed", "canceled"}

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for buf in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)

def request():
    cfg = json.loads(REQUEST.read_text(encoding="utf-8"))
    expected = {
        "schema": 1,
        "trial_id": "marches-axeman-rig-ready-tpose-v1",
        "source_directory": str(SOURCE.relative_to(ROOT)),
        "visually_approved": True,
        "reviewed_source_sha256": cfg.get("reviewed_source_sha256"),
        "mesh_model": MESH_MODEL,
        "mesh_settings": MESH_SETTINGS,
        "rig_model": RIG_MODEL,
        "maximum_mesh_predictions": 1,
        "maximum_rig_predictions": 1,
        "output_directory": str(OUTPUT.relative_to(ROOT)),
    }
    if cfg != expected:
        raise ValueError("Unexpected or unapproved rig-ready reconstruction request")
    hashes = cfg["reviewed_source_sha256"]
    if not isinstance(hashes, dict) or set(hashes) != set(ORDER):
        raise ValueError("Approval must contain all four exact source SHA256 fingerprints")
    for direction in ORDER:
        image = SOURCE / (direction + ".png")
        expected_hash = hashes[direction]
        if not isinstance(expected_hash, str) or not re.fullmatch("[0-9a-f]{64}", expected_hash):
            raise ValueError("Invalid source SHA fingerprint for " + direction)
        if not image.is_file() or sha(image) != expected_hash:
            raise ValueError("Approved source missing or modified: " + direction)
        from PIL import Image
        with Image.open(image) as check:
            if check.size != (1024, 1024) or check.mode != "RGBA":
                raise ValueError("Expected reviewed 1024 RGBA PNG: " + direction)
    return cfg

def client():
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing Replicate secret")
    import replicate
    return replicate.Client(api_token=token)

def stage_submit(stage, cfg):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checkpoint = OUTPUT / (stage + "-prediction.json")
    final = OUTPUT / ("unrigged.glb" if stage == "mesh" else "rigged.glb")
    if final.exists() or checkpoint.exists():
        print("No new paid call: existing output/prediction for", stage, flush=True)
        return
    if stage == "rig" and not (OUTPUT / "unrigged.glb").is_file():
        raise RuntimeError("Cannot rig before approved mesh collection")
    model_name = MESH_MODEL if stage == "mesh" else RIG_MODEL
    api = client()
    model = api.models.get(model_name)
    version = MESH_VERSION if stage == "mesh" else model.latest_version.id
    if not version:
        raise RuntimeError("Replicate model has no available version")
    if stage == "mesh":
        sources = {
            field: (SOURCE / (direction + ".png")).open("rb")
            for field, direction in (("front_image", "front"), ("back_image", "back"),
                                     ("left_image", "left"), ("right_image", "right"))
        }
        inputs = {**sources, **MESH_SETTINGS}
    else:
        inputs = {"character_file": (OUTPUT / "unrigged.glb").open("rb"),
                  "auto_rig": True, "front_facing": True}
        sources = {"character_file": inputs["character_file"]}
    try:
        prediction = api.predictions.create(version=version, input=inputs)
    finally:
        for source_file in sources.values():
            source_file.close()
    if not prediction.id:
        raise RuntimeError("Prediction accepted with no ID; DO NOT retry automatically")
    save(checkpoint, {
        "trial_id": cfg["trial_id"], "stage": stage,
        "model": model_name, "model_version": version,
        "prediction_id": prediction.id, "initial_status": prediction.status,
        "source_sha256": cfg["reviewed_source_sha256"],
        "input_mesh_sha256": sha(OUTPUT / "unrigged.glb") if stage == "rig" else None,
        "paid_predictions_submitted": 1,
    })
    print("Accepted paid prediction:", stage, prediction.id, flush=True)

def uri_for_glb(output):
    if isinstance(output, str):
        return output if ".glb" in urlparse(output).path.lower() else None
    if isinstance(output, list):
        return next((found for part in output if (found := uri_for_glb(part))), None)
    if isinstance(output, dict):
        for key in ("glb", "rigged_glb", "file", "character", "output", "url", "files"):
            if key in output:
                found = uri_for_glb(output[key])
                if found:
                    return found
        for item in output.values():
            found = uri_for_glb(item)
            if found:
                return found
    return None

def download_glb(uri, target):
    parsed = urlparse(uri)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not (host == "replicate.delivery" or host.endswith(".replicate.delivery")):
        raise ValueError("Unexpected output delivery host: output not downloaded")
    total = 0
    partial = target.with_suffix(".partial")
    with urlopen(uri, timeout=180) as remote, partial.open("wb") as output:
        for buf in iter(lambda: remote.read(1024 * 1024), b""):
            total += len(buf)
            if total > 75 * 1024 * 1024:
                raise ValueError("GLB exceeds 75 MiB output cap")
            output.write(buf)
    if total < 1024:
        raise ValueError("Empty GLB downloaded")
    partial.replace(target)
    return total

def inspect_glb(path):
    with path.open("rb") as infile:
        magic, version, length = struct.unpack("<4sII", infile.read(12))
        if (magic, version) != (b"glTF", 2) or length != path.stat().st_size:
            raise ValueError("Invalid GLB header or byte length")
        json_len, json_type = struct.unpack("<I4s", infile.read(8))
        if json_type != b"JSON" or json_len > 16 * 1024 * 1024:
            raise ValueError("Invalid GLB JSON chunk")
        document = json.loads(infile.read(json_len))
    meshes, skins = document.get("meshes", []), document.get("skins", [])
    if not meshes:
        raise ValueError("GLB has no mesh")
    skin_attrs = []
    for mesh in meshes:
        for primitive in mesh.get("primitives", []):
            attributes = primitive.get("attributes", {})
            skin_attrs.append("JOINTS_0" in attributes and "WEIGHTS_0" in attributes)
    return {
        "mesh_count": len(meshes), "node_count": len(document.get("nodes", [])),
        "skin_count": len(skins), "joint_count": sum(len(s.get("joints", [])) for s in skins),
        "skinned_primitive_count": sum(skin_attrs),
        "animations_in_file": len(document.get("animations", [])),
        "has_materials": bool(document.get("materials")),
        "has_texture_images": bool(document.get("images")),
    }

def stage_collect(stage, cfg):
    checkpoint = OUTPUT / (stage + "-prediction.json")
    if not checkpoint.is_file():
        raise RuntimeError("Cannot collect; no checkpoint (must not submit again)")
    rec = json.loads(checkpoint.read_text(encoding="utf-8"))
    if rec["trial_id"] != cfg["trial_id"] or rec["stage"] != stage or rec["source_sha256"] != cfg["reviewed_source_sha256"]:
        raise RuntimeError("Prediction fingerprint mismatch")
    dest = OUTPUT / ("unrigged.glb" if stage == "mesh" else "rigged.glb")
    if dest.is_file():
        print("Already collected:", dest, flush=True)
        return
    api = client()
    deadline = time.monotonic() + 22 * 60
    prediction = None
    while time.monotonic() < deadline:
        prediction = api.predictions.get(rec["prediction_id"])
        print(stage, prediction.status, flush=True)
        if prediction.status in TERMINAL:
            break
        time.sleep(20)
    if prediction is None or prediction.status not in TERMINAL:
        raise TimeoutError("Prediction pending. Collect again, do not resubmit.")
    if prediction.status != "succeeded":
        save(OUTPUT / (stage + "-error.json"), {
            "stage": stage, "status": prediction.status,
            "prediction_id": rec["prediction_id"], "error": str(prediction.error)[:1000]})
        raise RuntimeError("Prediction failed; no automatic paid retry")
    uri = uri_for_glb(prediction.output)
    if not uri:
        raise ValueError("Prediction succeeded but no GLB URL found. Inspect output manually; do not resubmit.")
    size = download_glb(uri, dest)
    try:
        geometry = inspect_glb(dest)
    except Exception:
        # Invalid generated data must not be mistaken for an approved character.
        dest.rename(OUTPUT / (stage + "-invalid-output.glb"))
        raise
    accepted = stage == "mesh" and geometry["mesh_count"] > 0
    if stage == "rig":
        accepted = geometry["skin_count"] > 0 and geometry["joint_count"] >= 12 and geometry["skinned_primitive_count"] > 0
    save(OUTPUT / (stage + "-report.json"), {
        "status": "technical-check-passed-awaiting-visual-QA" if accepted else "technical-check-failed",
        "stage": stage, "model": rec["model"], "model_version": rec["model_version"],
        "prediction_id": rec["prediction_id"], "glb_bytes": size,
        "glb_sha256": sha(dest), "glb_geometry": geometry, "paid_predictions_submitted": 1,
        "human_review_required": True,
        "limitations": "Joint placement, skin deformation, correct face direction and detailed texture not artist-approved."
    })
    if not accepted:
        raise RuntimeError("GLB created but essential rig/skeleton checks failed")
    print("Collected", stage, dest, geometry, flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("validate", "mesh-submit", "mesh-collect",
                                            "rig-submit", "rig-collect"), required=True)
    args = parser.parse_args()
    cfg = request()
    if args.stage == "validate":
        print("Approval SHA256 matches four T-pose references; no API calls.")
    else:
        stage, action = args.stage.split("-")
        if action == "submit":
            stage_submit(stage, cfg)
        else:
            stage_collect(stage, cfg)

if __name__ == "__main__":
    main()
