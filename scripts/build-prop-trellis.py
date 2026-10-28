#!/usr/bin/env python3
"""Unit-independent, resumable TRELLIS image -> textured GLB builder.

This module is deliberately not named after a weapon. Each request supplies
the source and destination, and each prediction is pinned to the source hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MODEL = "firtoz/trellis"
VERSION = "e8f6c45206993f297372f5436b90350817bd9b4a0d52d2a76df50c1c8afa2b3c"
INPUTS = {"generate_model": True, "generate_color": True, "generate_normal": True,
          "texture_size": 1024, "mesh_simplify": .95, "randomize_seed": False,
          "seed": 20261027, "ss_sampling_steps": 12, "slat_sampling_steps": 12,
          "ss_guidance_strength": 7.5, "slat_guidance_strength": 3}


def safe(rel):
    if not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel:
        raise ValueError("Invalid path")
    path = (ROOT / rel).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Path escapes project")
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    tmp.replace(path)


def load(request):
    cfg = json.loads(safe(request).read_text(encoding="utf8"))
    required = {"schema", "source_image", "output_path", "replicate_model",
                "maximum_paid_predictions", "automatic_paid_retries"}
    if (not isinstance(cfg, dict) or set(cfg) != required or cfg["schema"] != 1
            or cfg["replicate_model"] != MODEL
            or cfg["maximum_paid_predictions"] != 1 or cfg["automatic_paid_retries"] != 0):
        raise ValueError("Invalid generic prop request")
    image, glb = safe(cfg["source_image"]), safe(cfg["output_path"])
    if not image.is_file() or image.suffix != ".png" or glb.suffix != ".glb":
        raise ValueError("Missing isolated PNG or invalid output path")
    if not glb.is_relative_to(ROOT / "assets/experiments/props/"):
        raise ValueError("Prop GLB must be under assets/experiments/props")
    from PIL import Image
    with Image.open(image) as im:
        if im.mode != "RGBA" or im.width != im.height or im.width not in (1024, 1600):
            raise ValueError("Isolated equipment must be a square RGBA PNG")
        bbox = im.getchannel("A").getbbox()
        if not bbox or min(bbox[0], bbox[1], im.width-bbox[2], im.height-bbox[3]) < im.width*.005:
            raise ValueError("Equipment cutout empty or cropped")
    return cfg, image, glb


def api():
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN missing; no paid call")
    import replicate
    return replicate.Client(api_token=token)


def submit(cfg, image, glb):
    receipt = glb.with_name(glb.stem + "-prediction.json")
    digest = sha(image)
    if glb.is_file():
        print("SKIP existing GLB", glb)
        return
    if receipt.exists():
        prior = json.loads(receipt.read_text(encoding="utf8"))
        if prior.get("source_sha256") != digest or prior.get("version") != VERSION:
            raise ValueError("Prediction receipt belongs to another image or model")
        print("SKIP prior prediction; collect it instead")
        return
    client = api()
    # Record an uncertain submission BEFORE sending it. A timeout between POST
    # and receipt must never cause a duplicate paid prediction on rerun.
    save(receipt, {"schema": 1, "source_sha256": digest, "model": MODEL,
                   "version": VERSION, "status": "submission-outcome-unknown",
                   "automatic_paid_retries": 0})
    with image.open("rb") as inp:
        prediction = client.predictions.create(version=VERSION, input={**INPUTS, "images": [inp]})
    if not prediction.id:
        raise RuntimeError("No prediction ID; receipt retained to prevent repayment")
    save(receipt, {"schema": 1, "source_sha256": digest, "model": MODEL,
                   "version": VERSION, "prediction_id": prediction.id,
                   "status": prediction.status, "paid_predictions_submitted": 1,
                   "automatic_paid_retries": 0})
    print("TRELLIS prediction submitted:", prediction.id)


def find_glb(value):
    if isinstance(value, str):
        return value if urlparse(value).path.lower().endswith(".glb") else None
    if isinstance(value, list):
        return next((uri for x in value if (uri := find_glb(x))), None)
    if isinstance(value, dict):
        return next((uri for x in value.values() if (uri := find_glb(x))), None)
    return None


def collect(cfg, image, glb):
    receipt = glb.with_name(glb.stem + "-prediction.json")
    if glb.is_file():
        print("SKIP existing GLB", glb)
        return
    rec = json.loads(receipt.read_text(encoding="utf8"))
    if rec.get("source_sha256") != sha(image) or rec.get("version") != VERSION:
        raise ValueError("Source changed since TRELLIS prediction")
    if not rec.get("prediction_id"):
        raise RuntimeError("Submission outcome uncertain; do not submit again")
    client = api()
    deadline = time.monotonic() + 9*60
    while True:
        prediction = client.predictions.get(rec["prediction_id"])
        if prediction.status in ("succeeded", "failed", "canceled"):
            break
        if time.monotonic() > deadline:
            raise TimeoutError("Prediction still running; collect later")
        time.sleep(15)
    if prediction.status != "succeeded":
        raise RuntimeError("TRELLIS did not succeed; original checkpoint retained")
    uri = find_glb(prediction.output)
    host = urlparse(uri or "").hostname or ""
    if (not uri or urlparse(uri).scheme != "https"
            or not (host == "replicate.delivery" or host.endswith(".replicate.delivery"))):
        raise ValueError("Unexpected TRELLIS output URI")
    with urlopen(uri, timeout=160) as response:
        blob = response.read(60*1024*1024+1)
    if not 4096 <= len(blob) <= 60*1024*1024 or blob[:4] != b"glTF":
        raise ValueError("Invalid or oversized GLB")
    _, version, size = struct.unpack_from("<4sII", blob)
    n, typ = struct.unpack_from("<I4s", blob, 12)
    if version != 2 or size != len(blob) or typ != b"JSON":
        raise ValueError("Invalid GLB container")
    doc = json.loads(blob[20:20+n])
    if not all(doc.get(key) for key in ("meshes", "materials", "images")):
        raise ValueError("TRELLIS output lacks textured mesh")
    glb.parent.mkdir(parents=True, exist_ok=True)
    glb.write_bytes(blob)
    save(glb.with_name(glb.stem + "-report.json"), {"schema": 1, "status": "mesh-ready",
         "model": MODEL, "version": VERSION, "prediction_id": rec["prediction_id"],
         "source_sha256": sha(image), "glb_sha256": sha(glb), "glb_bytes": len(blob)})
    print("COLLECTED textured prop", glb)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--stage", choices=("validate", "submit", "collect"), required=True)
    args = parser.parse_args()
    cfg, image, glb = load(args.request)
    if args.stage == "submit":
        submit(cfg, image, glb)
    elif args.stage == "collect":
        collect(cfg, image, glb)
    else:
        print("Validated isolated equipment PNG", image)


if __name__ == "__main__":
    main()
