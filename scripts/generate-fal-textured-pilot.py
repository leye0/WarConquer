#!/usr/bin/env python3
"""One paid fal.ai multiview textured-mesh pilot; never overwrite the rigged asset."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
POSE = ROOT / "assets/experiments/rig-ready-3d/marches_hache/tpose-v2"
INPUT = ROOT / "assets/experiments/rig-source-turnaround/marches_hache/tpose-v2"
MESH = POSE / "fal-textured.glb"
RECEIPT = POSE / "fal-receipt.json"
REPORT = POSE / "fal-texture-report.json"
MODEL = "fal-ai/hunyuan3d/v2/multi-view"
SEED = 20261027
MAX_BYTES = 45_000_000


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def png_info(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 32 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG: " + str(path))
    width, height = struct.unpack_from(">II", raw, 16)
    if (width, height) != (1024, 1024):
        raise ValueError("Source turnaround PNG dimensions changed")
    return {"path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "width": width, "height": height, "bytes": len(raw)}


def verify_textured_glb(raw: bytes) -> dict:
    if len(raw) < 28:
        raise ValueError("Empty or truncated GLB")
    magic, version, length = struct.unpack_from("<4sII", raw)
    if (magic, version, length) != (b"glTF", 2, len(raw)):
        raise ValueError("Invalid GLB header")
    n, chunk_type = struct.unpack_from("<I4s", raw, 12)
    if chunk_type != b"JSON" or n > 4_000_000:
        raise ValueError("Invalid GLB JSON chunk")
    doc = json.loads(raw[20:20+n])
    primitives = [p for mesh in doc.get("meshes", [])
                  for p in mesh.get("primitives", [])]
    with_uv = sum("TEXCOORD_0" in p.get("attributes", {}) for p in primitives)
    with_texture = sum("baseColorTexture" in m.get("pbrMetallicRoughness", {})
                       for m in doc.get("materials", []))
    stats = {"mesh_count": len(doc.get("meshes", [])),
             "primitive_count": len(primitives), "uv_primitives": with_uv,
             "texture_images": len(doc.get("images", [])),
             "textured_materials": with_texture,
             "skin_count": len(doc.get("skins", [])),
             "animation_count": len(doc.get("animations", []))}
    if not primitives or not with_uv or not with_texture or not stats["texture_images"]:
        raise ValueError("fal returned geometry without proper UV/material texture: " + str(stats))
    return stats


def main() -> None:
    POSE.mkdir(parents=True, exist_ok=True)
    if MESH.exists() and MESH.stat().st_size > 100_000:
        print("Existing fal pilot found: skipping any further paid submission")
        return
    if not os.environ.get("FAL_KEY"):
        raise RuntimeError("Missing GitHub Actions secret FAL_API_KEY")
    source = {name: INPUT / (name + ".png")
              for name in ("front", "back", "left")}
    inputs = {name: png_info(path) for name, path in source.items()}
    # fal's three-view endpoint does not accept the fourth right.png.
    inputs["right_unused_by_api"] = png_info(INPUT / "right.png")
    import fal_client

    resume_id = os.environ.get("FAL_RESUME_REQUEST_ID", "").strip()
    if resume_id:
        print("Resuming pre-existing fal request WITHOUT new submission", flush=True)
        handle = fal_client.get_handle(MODEL, resume_id)
    else:
        urls = {name + "_image_url": fal_client.upload_file(str(path))
                for name, path in source.items()}
        print("Three images uploaded. Sending ONE paid textured request.", flush=True)
        handle = fal_client.submit(MODEL, arguments={
            **urls, "textured_mesh": True, "seed": SEED,
            "num_inference_steps": 50, "guidance_scale": 7.5,
            "octree_resolution": 256,
        })
    receipt = {"model": MODEL, "seed": SEED, "request_id": handle.request_id,
               "resumed": bool(resume_id), "inputs": inputs,
               "status": "submitted"}
    write_json(RECEIPT, receipt)
    print("fal REQUEST ID:", handle.request_id, flush=True)
    print("If interrupted, RESUME this ID; do not submit again.", flush=True)
    result = handle.get()
    url = (result.get("model_mesh") or {}).get("url")
    if not isinstance(url, str) or urlparse(url).scheme != "https":
        raise ValueError("fal did not return a secure model URL")
    with urlopen(url, timeout=180) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Output exceeds 45 MB")
    MESH.write_bytes(raw)
    stats = verify_textured_glb(raw)
    receipt["status"] = "downloaded-and-structurally-validated"
    write_json(RECEIPT, receipt)
    report = {
        "status": "textured-unrigged-awaiting-visual-QA",
        "model": MODEL, "request_id": handle.request_id,
        "estimated_cost_usd": 0.48,
        "seed": SEED, "input_images": inputs,
        "output": str(MESH.relative_to(ROOT)),
        "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        "note": "Separate non-rigged pilot; face and topology still require visual QA.",
        **stats
    }
    write_json(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
