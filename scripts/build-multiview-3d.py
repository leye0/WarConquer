#!/usr/bin/env python3
"""One controlled four-view WarConquer mesh experiment on Replicate."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import time
from urllib.parse import urlparse
from urllib.request import urlopen

import numpy as np
from PIL import Image, ImageDraw

REQUEST = Path("multiview-3d-request.json")
MODEL = "tencent/hunyuan3d-2mv"
SOURCE_ROOT = Path("assets/experiments/standing-turnaround/marches_hache")
OUTPUT = Path("assets/experiments/3d-reconstruction/marches_hache/hunyuan3d-2mv")
VIEWS = {
    "front_image": "S",
    "back_image": "N",
    "left_image": "W",
    "right_image": "E",
}
TERMINAL = {"succeeded", "failed", "canceled"}


def read_request():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    expected = {
        "schema": 1,
        "trial_id": "marches-axeman-fourviews-hunyuan2mv-2026-10-27",
        "model": MODEL,
        "source_directory": str(SOURCE_ROOT),
        "directions": VIEWS,
        "output_directory": str(OUTPUT),
        "model_settings": {
            "steps": 30,
            "guidance_scale": 5,
            "octree_resolution": 256,
            "target_face_num": 25000,
            "remove_background": False,
            "randomize_seed": False,
            "seed": 1234,
            "file_type": "glb",
        },
        "maximum_generations": 1,
        "expected_cost_usd": 0.11,
    }
    if request != expected:
        raise ValueError("Request differs from the approved four-view one-shot test.")
    return request


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def validate_views():
    view_metadata = {}
    for field, direction in VIEWS.items():
        path = SOURCE_ROOT / (direction + ".png")
        if not path.is_file():
            raise FileNotFoundError("Missing source artwork: " + str(path))
        with Image.open(path) as image:
            if image.size != (1024, 1024) or image.format != "PNG":
                raise ValueError("Unexpected image dimensions/format: " + str(path))
            if image.mode != "RGBA":
                raise ValueError("Source should preserve transparent RGBA: " + str(path))
            bounds = image.getchannel("A").getbbox()
            if not bounds:
                raise ValueError("Fully transparent source: " + str(path))
        view_metadata[field] = {
            "path": str(path),
            "sha256": sha256(path),
            "foreground_bounds_xyxy": list(bounds),
        }
    return view_metadata


def write_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def replicate_client():
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("REPLICATE_API_KEY secret unavailable on Actions.")
    import replicate
    return replicate.Client(api_token=token)


def submit(request, sources):
    checkpoint = OUTPUT / "prediction.json"
    if (OUTPUT / "report.json").exists():
        print("Already completed. No extra paid calls.")
        return
    if checkpoint.exists():
        prior = json.loads(checkpoint.read_text(encoding="utf-8"))
        if prior.get("trial_id") != request["trial_id"] or prior.get("source_views") != sources:
            raise ValueError("Existing prediction has different source fingerprints.")
        print("Resume existing prediction", prior["prediction_id"], "without new model call.")
        return
    api = replicate_client()
    model = api.models.get(MODEL)
    version = model.latest_version.id
    if not version:
        raise RuntimeError("No current version published for multiview model.")
    with ExitStack() as stack:
        inputs = {
            field: stack.enter_context((SOURCE_ROOT / (direction + ".png")).open("rb"))
            for field, direction in VIEWS.items()
        }
        inputs.update(request["model_settings"])
        prediction = api.predictions.create(version=version, input=inputs)
    if not prediction.id:
        raise RuntimeError("Prediction ID missing. Do not retry automatically.")
    write_json(checkpoint, {
        "trial_id": request["trial_id"],
        "model": MODEL,
        "version": version,
        "prediction_id": prediction.id,
        "initial_status": prediction.status,
        "source_views": sources,
        "generations_submitted": 1,
        "estimated_cost_usd_before_run": request["expected_cost_usd"],
    })
    print("Exactly one multiview prediction submitted:", prediction.id)


def download(url, destination):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not (host == "replicate.delivery" or host.endswith(".replicate.delivery")):
        raise ValueError("Unexpected GLB host.")
    byte_count = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=180) as remote, destination.open("wb") as target:
        while chunk := remote.read(1024 * 1024):
            byte_count += len(chunk)
            if byte_count > 75 * 1024 * 1024:
                raise ValueError("Mesh exceeds the 75-MiB experiment ceiling.")
            target.write(chunk)
    if byte_count < 1000:
        raise RuntimeError("Generated GLB is too small.")
    return byte_count


def inspect_mesh(glb_path):
    import trimesh
    scene = trimesh.load(str(glb_path), force="scene", process=False)
    geometries = [item for item in scene.geometry.values() if isinstance(item, trimesh.Trimesh)]
    if not geometries:
        raise ValueError("No triangle mesh found inside the generated GLB.")
    mesh = scene.dump(concatenate=True)
    if mesh is None or len(mesh.faces) == 0:
        raise ValueError("Generated 3D mesh has no faces.")
    return mesh, {
        "mesh_count": len(geometries),
        "faces": int(sum(len(m.faces) for m in geometries)),
        "vertices": int(sum(len(m.vertices) for m in geometries)),
        "bounds": np.asarray(mesh.bounds).round(5).tolist(),
        "watertight": bool(mesh.is_watertight),
        "visual_kinds": [str(m.visual.kind) for m in geometries],
        "has_texture_visuals": any(m.visual.kind == "texture" for m in geometries),
    }


def render_contact_sheet(mesh, output_path):
    # Lightweight, deterministic software silhouette shading; no Blender/GPU.
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    if len(faces) > 120000:
        step = math.ceil(len(faces) / 120000)
        faces = faces[::step]
    lo, hi = vertices.min(axis=0), vertices.max(axis=0)
    center = (lo + hi) / 2
    extent = hi - lo
    scale = max(float(extent.max()), 1e-6)
    pts = (vertices - center) / scale
    up = int(np.argmax(extent))
    horizontal = [i for i in range(3) if i != up]
    side, depth_axis = horizontal[0], horizontal[1]
    canvas = Image.new("RGB", (4 * 360, 400), "#17191d")
    labeler = ImageDraw.Draw(canvas)
    for k, degrees in enumerate((0, 90, 180, 270)):
        radians = math.radians(degrees)
        projected_side = pts[:, side] * math.cos(radians) + pts[:, depth_axis] * math.sin(radians)
        depth = -pts[:, side] * math.sin(radians) + pts[:, depth_axis] * math.cos(radians)
        vertical = pts[:, up]
        px = (projected_side * 310 + 180).astype(np.float64)
        py = (200 - vertical * 310).astype(np.float64)
        centroid_depth = depth[faces].mean(axis=1)
        order = np.argsort(centroid_depth)
        panel = Image.new("RGB", (360, 360), "#202329")
        drawer = ImageDraw.Draw(panel)
        for face_id in order:
            a, b, c = map(int, faces[face_id])
            if a == b or b == c or a == c:
                continue
            # Slight face-to-face shading makes volume visible without needing texture.
            ux, uy = px[b] - px[a], py[b] - py[a]
            vx, vy = px[c] - px[a], py[c] - py[a]
            shade = min(210, max(70, int(135 + 60 * math.tanh((ux * vy - uy * vx) / 5000))))
            drawer.polygon([(float(px[i]), float(py[i])) for i in (a, b, c)], fill=(shade, shade + 5, shade + 13))
        canvas.paste(panel, (k * 360, 0))
        labeler.text((k * 360 + 12, 372), f"Mesh rotation {degrees} degrees", fill="#eeeeee")
    canvas.save(output_path, optimize=True)


def collect(request, sources):
    checkpoint_path = OUTPUT / "prediction.json"
    if not checkpoint_path.exists():
        raise RuntimeError("Cannot collect: no prediction checkpoint.")
    record = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if record.get("trial_id") != request["trial_id"] or record.get("source_views") != sources:
        raise ValueError("Input fingerprints differ from paid prediction.")
    report_path = OUTPUT / "report.json"
    if report_path.exists():
        print("Collection already finished. No new model call.")
        return
    prediction_id = record["prediction_id"]
    api = replicate_client()
    deadline = time.monotonic() + 22 * 60
    result = None
    while time.monotonic() < deadline:
        result = api.predictions.get(prediction_id)
        print("Replicate:", prediction_id, result.status, flush=True)
        if result.status in TERMINAL:
            break
        time.sleep(20)
    if result is None or result.status not in TERMINAL:
        raise TimeoutError("Prediction unfinished; rerun collection without resubmission.")
    if result.status != "succeeded":
        write_json(report_path, {
            "status": result.status,
            "prediction_id": prediction_id,
            "error": str(result.error or "No GLB produced.")[:1500],
            "generations_submitted": 1,
        })
        raise RuntimeError("Replicate 3D prediction did not succeed.")
    glb_url = result.output
    if not isinstance(glb_url, str):
        raise TypeError("Expected a GLB URI from Hunyuan3D-2mv.")
    glb_path = OUTPUT / "marches-axeman-fourviews.glb"
    size_bytes = download(glb_url, glb_path)
    preview_error = None
    try:
        mesh, metrics = inspect_mesh(glb_path)
        render_contact_sheet(mesh, OUTPUT / "mesh-rotations.png")
    except Exception as exc:
        metrics = {"validation_warning": str(exc)[:500]}
        preview_error = str(exc)[:500]
    write_json(report_path, {
        "status": "generated_not_artist_approved",
        "trial_id": request["trial_id"],
        "model": MODEL,
        "prediction_id": prediction_id,
        "model_version": record["version"],
        "generations_submitted": 1,
        "expected_cost_usd_not_receipt": request["expected_cost_usd"],
        "source_views": sources,
        "glb": glb_path.name,
        "glb_bytes": size_bytes,
        "glb_sha256": sha256(glb_path),
        "mesh": metrics,
        "preview_warning": preview_error,
        "next_step": "Inspect actual 3D geometry and whether additional texturing/rigging is needed.",
    })
    print("GLB saved:", size_bytes, "bytes; mesh:", metrics)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("validate", "submit", "collect"))
    options = parser.parse_args()
    request = read_request()
    sources = validate_views()
    if options.stage == "validate":
        print("4 RGBA sources validated: S front, N back, W left, E right. No API call.")
    elif options.stage == "submit":
        submit(request, sources)
    else:
        collect(request, sources)


if __name__ == "__main__":
    main()
