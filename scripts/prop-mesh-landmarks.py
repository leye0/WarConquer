#!/usr/bin/env python3
"""Vision-grounded, reusable 3D contact landmarks for arbitrary handheld GLBs.

The cheap vision model sees four real orthographic renders of the GENERATED GLB
plus its source illustration. It identifies functional points *on the mesh*,
which we lift to actual vertex coordinates. A runtime solver maps these points
onto any articulated humanoid hand; no named unit or weapon rotation constants.

One canonical grip-plan.json is updated in place. Raw paid answers are kept as
one resumable receipt, never as numbered grip-plan variants.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
import os
import struct
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.5-flash-lite"
LANDMARKS = ("handle_butt", "grip_center", "working_head", "functional_edge")
VIEW_SIZE = 510
MARGIN = 38
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "view": {"type": "integer", "enum": [0, 1, 2, 3]},
        **{name: {"type": "array", "items": {"type": "number"}} for name in LANDMARKS},
        "confidence": {"type": "number"},
        "explanation": {"type": "string"},
    },
    "required": ["view", *LANDMARKS, "confidence", "explanation"],
}
PROMPT = (
    "You are annotating a real 3D prop mesh for reuse by ANY humanoid character. "
    "IMAGE 1 is a four-panel orthographic 3D render of the actual GLB, each "
    "panel labeled VIEW 0 through VIEW 3. IMAGE 2 is the original object "
    "illustration, only for identifying what the 3D prop's parts do. "
    "Select ONE of the four views where the functional working edge and "
    "handle are CLEARLY visible. Coordinates of ALL four landmarks must be "
    "normalized [x,y] (0..1) WITHIN THE SELECTED PANEL, including its margin. "
    "handle_butt: the far end of the handle away from the working end; "
    "grip_center: where an actual palm grasps the handle (not the blade); "
    "working_head: center of the working head, or the upper functional end "
    "of a curved frame; functional_edge: the ACTUAL working/cutting edge's "
    "outer edge or the functional FRONT of the object, NOT the back/poll. "
    "For an axe, make CERTAIN functional_edge points to the SHARP side of "
    "the head, not the flat back. Never use generic assumptions about which "
    "way the mesh axes point. For a symmetric double-edge, choose either "
    "equivalent cutting edge. If the mesh is unclear, lower confidence."
)


def glb_geometry(path: Path):
    """Return GLB world-space coordinates and their raw mesh-local counterparts."""
    raw = path.read_bytes()
    if len(raw) < 20 or raw[:4] != b"glTF" or struct.unpack_from("<I", raw, 4)[0] != 2:
        raise ValueError("Expected binary glTF 2.0")
    pos = 12
    chunks = {}
    while pos < len(raw):
        n, kind = struct.unpack_from("<II", raw, pos)
        pos += 8
        chunks[kind] = raw[pos:pos+n]
        pos += n
    doc = json.loads(chunks[0x4E4F534A]); binary = chunks[0x004E4942]
    accessors, views = doc["accessors"], doc["bufferViews"]
    dtype = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
    def accessor(index):
        a = accessors[index]; view = views[a["bufferView"]]
        components = {"SCALAR": 1, "VEC3": 3}[a["type"]]
        dt = np.dtype(dtype[a["componentType"]]).newbyteorder("<")
        item_size = dt.itemsize * components
        stride = view.get("byteStride", item_size)
        start = view.get("byteOffset", 0) + a.get("byteOffset", 0)
        if stride == item_size:
            result = np.frombuffer(binary, dtype=dt, count=a["count"]*components, offset=start)
            return result.reshape(-1, components).copy()
        return np.array([np.frombuffer(binary, dtype=dt, count=components,
            offset=start+i*stride) for i in range(a["count"])])
    nodes = doc.get("nodes", [])
    children = {child for n in nodes for child in n.get("children", [])}
    roots = doc.get("scenes", [{}])[doc.get("scene", 0)].get("nodes", []) if doc.get("scenes") else list(set(range(len(nodes)))-children)
    meshes = []
    def visit(node_index, parent):
        n = nodes[node_index]
        if "matrix" in n:
            m = np.array(n["matrix"], dtype=float).reshape(4, 4).T
        else:
            t = np.array(n.get("translation", [0, 0, 0]), dtype=float)
            s = np.array(n.get("scale", [1, 1, 1]), dtype=float)
            x, y, z, w = n.get("rotation", [0, 0, 0, 1])
            r = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                          [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                          [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
            m = np.eye(4); m[:3, :3] = r @ np.diag(s); m[:3, 3] = t
        matrix = parent @ m
        if "mesh" in n:
            for primitive_index, primitive in enumerate(doc["meshes"][n["mesh"]]["primitives"]):
                if "POSITION" not in primitive["attributes"] or primitive.get("mode", 4) != 4:
                    continue
                local = accessor(primitive["attributes"]["POSITION"]).astype(float)
                world = (np.column_stack([local, np.ones(len(local))]) @ matrix.T)[:, :3]
                indices = accessor(primitive["indices"]).reshape(-1) if "indices" in primitive else np.arange(len(local))
                if len(indices) % 3:
                    raise ValueError("Non-triangle primitive")
                meshes.append({"local": local, "world": world,
                    "faces": indices.reshape(-1, 3), "node": n.get("name", ""),
                    "mesh": n["mesh"], "primitive": primitive_index})
        for child in n.get("children", []):visit(child, matrix)
    for root in roots:visit(root, np.eye(4))
    if not meshes or sum(len(m["local"]) for m in meshes) < 40:
        raise ValueError("GLB has no usable triangle mesh")
    return meshes


def make_views(meshes):
    """Render four real mesh views; return projection metadata for 2D→3D lift."""
    points = np.vstack([m["world"] for m in meshes])
    center = points.mean(axis=0)
    _, _, vh = np.linalg.svd(points-center, full_matrices=False)
    direction = vh[0]
    # Cameras rotate around the object's LONG axis, showing two sides of the
    # working head. Signed mesh coordinates do not imply a grip orientation.
    cameras = [vh[1], -vh[1], vh[2], -vh[2]]
    span = max(np.ptp((points-center) @ vh[0]), np.ptp((points-center) @ vh[1]), np.ptp((points-center) @ vh[2]))
    # All four panels share the same scale so model points are comparable.
    scale = (VIEW_SIZE-2*MARGIN) / (span*1.17)
    canvas = Image.new("RGB", (VIEW_SIZE*2, VIEW_SIZE*2), (226, 229, 232))
    views = []
    for i, camera in enumerate(cameras):
        right = np.cross(camera, direction)
        right /= np.linalg.norm(right)
        up = direction
        info = {"right": right, "up": up, "camera": camera,
                "center": center, "scale": scale, "view": i}
        views.append(info)
        panel = Image.new("RGB", (VIEW_SIZE, VIEW_SIZE), (250, 250, 249))
        draw = ImageDraw.Draw(panel)
        faces = []
        for mesh in meshes:
            coords = mesh["world"]-center
            x = VIEW_SIZE/2 + coords@right*scale
            y = VIEW_SIZE/2 - coords@up*scale
            depth = coords@camera
            for f in mesh["faces"]:
                triangle = np.array([mesh["world"][j] for j in f])
                normal = np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0])
                n = np.linalg.norm(normal)
                if n < 1e-9:continue
                shade = 130 + round(60*abs(float(np.dot(normal/n,camera))))
                faces.append((float(depth[f].mean()), [(float(x[j]),float(y[j])) for j in f], shade))
        for _, triangle, shade in sorted(faces):
            draw.polygon(triangle, fill=(shade, round(shade*.87), round(shade*.69)))
        draw.rectangle((0, 0, VIEW_SIZE-1, VIEW_SIZE-1), outline=(70, 78, 84), width=2)
        draw.rectangle((10, 10, 127, 38), fill=(34, 43, 50))
        draw.text((18, 17), f"VIEW {i}", fill="white")
        canvas.paste(panel, ((i%2)*VIEW_SIZE, (i//2)*VIEW_SIZE))
    buffer = io.BytesIO(); canvas.save(buffer, format="PNG")
    return buffer.getvalue(), views


def image_part(data: bytes):
    return {"type": "image_url", "image_url": {"url":
        "data:image/png;base64,"+base64.b64encode(data).decode("ascii")}}


def validate_answer(answer):
    if not isinstance(answer, dict) or set(answer) != set(SCHEMA["properties"]):
        raise ValueError("Vision landmark response has unexpected fields")
    if answer["view"] not in (0, 1, 2, 3):raise ValueError("Invalid view")
    if not isinstance(answer["confidence"], (float, int)) or answer["confidence"] < .72:
        raise ValueError("Functional edge insufficiently visible to annotate")
    for name in LANDMARKS:
        p = answer[name]
        if not isinstance(p, list) or len(p) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or
            not math.isfinite(v) or not .01 <= v <= .99 for v in p):
            raise ValueError("Invalid vision point: "+name)
    if not isinstance(answer["explanation"], str):raise ValueError("Missing explanation")


def lift_landmarks(meshes, views, answer):
    """Use vision for semantic SIGNS; use geometry for actual 3D contacts.

    Pixel coordinates from tiny vision models can be approximate. A point on
    the *correct side* of a blade must project onto the real mesh silhouette,
    even when the model placed it outside that silhouette. We do not accept
    guessed 3D coordinates or blindly snap both head/edge to one vertex.
    """
    validate_answer(answer)
    v = views[answer["view"]]
    candidates = []
    for m in meshes:
        world = m["world"]
        projection = np.column_stack([(world-v["center"])@v["right"],
            (world-v["center"])@v["up"]]) * v["scale"]
        pixels = np.column_stack([VIEW_SIZE/2+projection[:, 0], VIEW_SIZE/2-projection[:, 1]])
        depth = (world-v["center"])@v["camera"]
        candidates.append((m, pixels, depth))
    result = {}
    def record(mesh, idx, distance, method):
        return {"local": [round(float(x), 7) for x in mesh["local"][idx]],
                "mesh": mesh["mesh"], "primitive": mesh["primitive"],
                "error_px": round(float(distance), 1), "method": method}
    def nearest_surface(pixel):
        nearby = []
        for m, projected, depth in candidates:
            delta = np.linalg.norm(projected-pixel, axis=1)
            for idx in np.argsort(delta)[:4]:
                nearby.append((float(delta[idx]),-float(depth[idx]),m,int(idx)))
        nearby.sort(key=lambda entry:(entry[0],entry[1]))
        distance, _, mesh, index = nearby[0]
        return mesh, index, distance
    # These two references are on the narrow handle; direct nearest-surface
    # projection is stable without assuming any mesh coordinates or axes.
    for name in ("handle_butt", "grip_center"):
        target = np.array(answer[name])*VIEW_SIZE
        mesh, idx, distance = nearest_surface(target)
        if distance > VIEW_SIZE*.085:
            raise ValueError(f"Handle landmark {name} is outside the real GLB")
        result[name] = record(mesh,idx,distance,"vision-nearest-surface")
    def pos(name):
        item = result[name]
        for m in meshes:
            if m["mesh"] == item["mesh"] and m["primitive"] == item["primitive"]:
                local = np.array(item["local"])
                j = np.argmin(np.linalg.norm(m["local"]-local, axis=1))
                return m["world"][j]
        raise ValueError("Landmark mesh missing")
    # Estimate where the HEAD lives from the long axis of the handle. This
    # is independent of its shape, material, category or facing direction.
    butt, grip = pos("handle_butt"), pos("grip_center")
    axis = grip-butt
    length = np.linalg.norm(axis)
    if length < 1e-5:raise ValueError("Handle endpoints collapse")
    axis /= length
    world = np.vstack([m["world"] for m in meshes])
    projection = (world-butt)@axis
    low, high = float(projection.min()), float(projection.max())
    if high-low < length*.8:raise ValueError("Model shaft too short")
    head_mask = projection > low+.69*(high-low)
    active_mask = projection > low+.49*(high-low)
    if head_mask.sum()<8 or active_mask.sum()<12:
        raise ValueError("No recognizable working end of the mesh")
    center = world[head_mask].mean(axis=0)
    # Choose a REAL surface vertex close to the head's geometric center.
    offsets = np.linalg.norm(world-center, axis=1)
    offsets[~head_mask] = np.inf
    head_index = int(np.argmin(offsets))
    def at_global(index):
        for m in meshes:
            if index < len(m["world"]):return m,index
            index -= len(m["world"])
        raise ValueError("Missing mesh vertex")
    head_mesh, head_local = at_global(head_index)
    head_pixel = np.array([VIEW_SIZE/2+(center-v["center"])@v["right"]*v["scale"],
                           VIEW_SIZE/2-(center-v["center"])@v["up"]*v["scale"]])
    # The *sign* of the functional face is a visual-semantic decision. Its
    # position and outermost point are solved from the actual GLB silhouette.
    expected_head = np.array(answer["working_head"])*VIEW_SIZE
    expected_edge = np.array(answer["functional_edge"])*VIEW_SIZE
    to_edge = expected_edge-expected_head
    edge_distance = np.linalg.norm(to_edge)
    if edge_distance < VIEW_SIZE*.035:
        raise ValueError("Vision cannot distinguish working edge from its head")
    if np.linalg.norm(expected_head-head_pixel)>VIEW_SIZE*.28:
        raise ValueError("Vision working head does not match the mesh's working end")
    to_edge /= edge_distance
    pixels = np.column_stack([
        VIEW_SIZE/2+(world-v["center"])@v["right"]*v["scale"],
        VIEW_SIZE/2-(world-v["center"])@v["up"]*v["scale"]])
    signed = (pixels-head_pixel)@to_edge
    signed[~active_mask] = -np.inf
    edge_index = int(np.argmax(signed))
    edge_mesh, edge_local = at_global(edge_index)
    edge_pixel = pixels[edge_index]
    if signed[edge_index]<VIEW_SIZE*.04:
        raise ValueError("No functional surface extends toward the vision-defined side")
    result["working_head"] = record(head_mesh,head_local,
        np.linalg.norm(expected_head-pixels[head_index]),"3d-working-head-centroid")
    result["functional_edge"] = record(edge_mesh,edge_local,
        np.linalg.norm(expected_edge-edge_pixel),"signed-mesh-silhouette-extreme")
    shaft = pos("working_head")-pos("grip_center")
    blade = pos("functional_edge")-pos("working_head")
    if np.linalg.norm(shaft)<1e-6:raise ValueError("Grip and working head coincide")
    transverse = blade-shaft*np.dot(blade,shaft)/np.dot(shaft,shaft)
    if np.linalg.norm(transverse)<.025*np.linalg.norm(shaft):
        raise ValueError("Working edge indistinguishable from object shaft in 3D")
    if np.dot(pos("working_head")-pos("grip_center"), pos("grip_center")-pos("handle_butt")) < 0:
        raise ValueError("Vision chose incompatible handle/head ordering")
    return result


def run(plan_path: Path, check=False):
    if not plan_path.is_file() or not plan_path.resolve().is_relative_to(ROOT):
        raise ValueError("A canonical repository grip plan is required")
    plan = json.loads(plan_path.read_text())
    image = ROOT/plan["inputs"]["object_image"]
    glb = ROOT/plan["inputs"]["object_glb"]
    if not all(p.is_file() and p.resolve().is_relative_to(ROOT) for p in (image,glb)):
        raise ValueError("Missing source illustration or GLB")
    digest = hashlib.sha256(glb.read_bytes()).hexdigest()
    if digest != plan["input_hashes"]["prop_glb_sha256"]:
        raise ValueError("GLB changed: regenerate the canonical grip plan")
    if plan.get("mesh_landmarks",{}).get("glb_sha256") == digest:
        print("3D functional landmarks already present; zero paid requests")
        return
    if check:
        print("3D functional landmarks missing")
        return
    meshes = glb_geometry(glb)
    render, views = make_views(meshes)
    receipt = plan_path.with_name("grip-landmarks-response.json")
    if receipt.exists():
        cached = json.loads(receipt.read_text())
        if cached.get("glb_sha256") != digest:
            raise ValueError("Cached vision answer belongs to a different GLB")
        answer = cached["raw_landmarks"]
    else:
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:raise RuntimeError("Missing OPENROUTER_API_KEY (run the pipeline Actions)")
        from PIL import ImageOps
        original = Image.open(image).convert("RGBA")
        if original.getbbox():original = original.crop(original.getbbox())
        original.thumbnail((720, 720))
        original = ImageOps.contain(original, (720, 720))
        original_bytes = io.BytesIO(); original.save(original_bytes, format="PNG")
        payload = {"model": MODEL, "temperature": 0, "max_tokens": 520,
            "provider": {"require_parameters": True},
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "glb_prop_landmarks", "strict": True, "schema": SCHEMA}},
            "messages": [{"role": "system", "content": PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "IMAGE 1: generated 3D GLB, four labeled views"},
                    image_part(render),
                    {"type": "text", "text": "IMAGE 2: reference concept for functional edge only"},
                    image_part(original_bytes.getvalue())]}]}
        request = Request(ENDPOINT, data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": "Bearer "+key, "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/leye0/WarConquer",
                     "X-Title": "WarConquer intrinsic GLB grip landmarks"})
        with urlopen(request, timeout=150) as response:
            data = json.loads(response.read(160000))
        answer = json.loads((data.get("choices") or [{}])[0]["message"]["content"])
        receipt.write_text(json.dumps({"schema":1, "glb_sha256": digest,
            "model": MODEL, "raw_landmarks":answer}, indent=2)+"\n")
    landmarks = lift_landmarks(meshes, views, answer)
    plan["mesh_landmarks"] = {"schema":1,"glb_sha256":digest,
        "model": MODEL,"view":answer["view"],"confidence":answer["confidence"],
        "points":landmarks,"explanation":answer["explanation"]}
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+"\n")
    print("Saved reusable 3D grip/contact landmark contract:", plan_path.relative_to(ROOT))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run((ROOT/args.plan).resolve(), args.check)
