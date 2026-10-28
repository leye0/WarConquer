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
import re
import struct
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

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


def confirmed_interaction(plan_path: Path, plan: dict):
    """Resolve exact semantic IDs; a GLB annotator cannot invent its own roles."""
    provenance = plan.get("interaction_provenance")
    if not provenance:
        return None, None  # Explicit historical compatibility, no invented second grip.
    if not isinstance(provenance, dict):
        raise ValueError("Malformed interaction provenance")
    rel = provenance.get("path", "")
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        raise ValueError("Unsafe interaction provenance path")
    contract_path = (ROOT / rel).resolve()
    if (not contract_path.is_relative_to(ROOT) or
            not contract_path.is_relative_to(ROOT) or not contract_path.is_file()):
        raise ValueError("Missing authoritative interaction contract")
    content = contract_path.read_bytes()
    fingerprint = hashlib.sha256(content).hexdigest()
    contract = json.loads(content)
    image_path = ROOT / plan["inputs"]["object_image"]
    if (fingerprint != provenance.get("sha256") or
            contract.get("schema") != 1 or
            contract.get("semantic_status") != "confirmed" or
            contract.get("mixamo_pose_status") != "pending_real_joint_validation" or
            contract.get("source_hashes", {}).get("object_image") !=
                hashlib.sha256(image_path.read_bytes()).hexdigest()):
        raise ValueError("Unconfirmed or stale object/character/Mixamo roles")
    sem = contract.get("characterization", {})
    grips, features = sem.get("grips"), sem.get("features")
    if (not isinstance(grips, list) or not grips or
            not isinstance(features, list) or not features or
            any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
                for item in grips + features)):
        raise ValueError("Missing vision-confirmed named grip or action features")
    return sem, fingerprint


def named_schema(semantic):
    """Only the already confirmed IDs can be annotated on actual mesh views."""
    if semantic is None:
        return SCHEMA
    extra = {}
    for collection, point_fields in (("grips", ("point",)),
                                     ("features", ("origin", "direction_tip"))):
        names = [item["id"] for item in semantic[collection]]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate source-confirmed semantic identifier")
        props = {"id": {"type": "string", "enum": names},
                 "view": {"type": "integer", "enum": [0, 1, 2, 3]},
                 "region": {"type": "array", "items": {"type": "number"}},
                 "evidence": {"type": "string"}}
        props.update({field: {"type": "array", "items": {"type": "number"}}
                      for field in point_fields})
        extra[collection] = {"type": "array", "items": {"type": "object",
            "additionalProperties": False, "properties": props,
            "required": list(props)}}
    return {"type": "object", "additionalProperties": False,
            "properties": {**SCHEMA["properties"], **extra},
            "required": [*SCHEMA["required"], *extra]}


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
    texture_cache={}
    def material_texture(primitive):
        index=primitive.get("material")
        if index is None:return None
        material=doc.get("materials",[])[index]
        color=material.get("pbrMetallicRoughness",{}).get("baseColorTexture")
        if not isinstance(color,dict):return None
        texture_idx=color["index"]
        image_idx=doc["textures"][texture_idx]["source"]
        if image_idx not in texture_cache:
            image=doc["images"][image_idx]
            if "bufferView" not in image:
                raise ValueError("GLB texture must be embedded for source-grounded render QA")
            view=views[image["bufferView"]]
            start=view.get("byteOffset",0)
            data=binary[start:start+view["byteLength"]]
            texture_cache[image_idx]=np.array(Image.open(io.BytesIO(data)).convert("RGB"))
        return texture_cache[image_idx]
    def accessor(index):
        a = accessors[index]; view = views[a["bufferView"]]
        components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
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
                uv=(accessor(primitive["attributes"]["TEXCOORD_0"]).astype(float)
                    if "TEXCOORD_0" in primitive["attributes"] else None)
                texture=material_texture(primitive)
                world = (np.column_stack([local, np.ones(len(local))]) @ matrix.T)[:, :3]
                indices = accessor(primitive["indices"]).reshape(-1) if "indices" in primitive else np.arange(len(local))
                if len(indices) % 3:
                    raise ValueError("Non-triangle primitive")
                meshes.append({"local": local, "world": world,
                    "faces": indices.reshape(-1, 3), "node": n.get("name", ""),
                    "mesh": n["mesh"], "primitive": primitive_index,
                    "uv":uv,"texture":texture})
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
        # CPU-rasterize the ACTUAL GLB baseColorTexture using its UVs and a
        # depth buffer. Flat brown silhouettes erase exactly the material
        # evidence that vision needs to distinguish wood, metal and sharp edge.
        pixels=np.full((VIEW_SIZE,VIEW_SIZE,3),(250,250,249),dtype=np.uint8)
        zbuffer=np.full((VIEW_SIZE,VIEW_SIZE),-np.inf,dtype=float)
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
                vertices=np.array([(x[j],y[j]) for j in f],dtype=float)
                x0,y0=vertices[0];x1,y1=vertices[1];x2,y2=vertices[2]
                denom=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
                if abs(denom)<1e-8:continue
                left=max(0,int(math.floor(min(x0,x1,x2))))
                top=max(0,int(math.floor(min(y0,y1,y2))))
                right_px=min(VIEW_SIZE-1,int(math.ceil(max(x0,x1,x2))))
                bottom_px=min(VIEW_SIZE-1,int(math.ceil(max(y0,y1,y2))))
                if left>right_px or top>bottom_px:continue
                xx,yy=np.meshgrid(np.arange(left,right_px+1)+.5,
                                  np.arange(top,bottom_px+1)+.5)
                a=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/denom
                b=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/denom
                c=1-a-b
                mask=(a>=-1e-5)&(b>=-1e-5)&(c>=-1e-5)
                if not mask.any():continue
                surface_depth=a*depth[f[0]]+b*depth[f[1]]+c*depth[f[2]]
                region_z=zbuffer[top:bottom_px+1,left:right_px+1]
                front=mask&(surface_depth>region_z)
                if not front.any():continue
                brightness=.70+.30*abs(float(np.dot(normal/n,camera)))
                if mesh.get("texture") is not None and mesh.get("uv") is not None:
                    uv=mesh["uv"]
                    u=a*uv[f[0],0]+b*uv[f[1],0]+c*uv[f[2],0]
                    v=a*uv[f[0],1]+b*uv[f[1],1]+c*uv[f[2],1]
                    texture=mesh["texture"]
                    tx=(np.mod(u,1)*(texture.shape[1]-1)).astype(int)
                    ty=(np.mod(1-v,1)*(texture.shape[0]-1)).astype(int)
                    color=texture[ty,tx]
                else:
                    color=np.full((*xx.shape,3),(178,151,124),dtype=np.uint8)
                region_pixels=pixels[top:bottom_px+1,left:right_px+1]
                region_pixels[front]=np.clip(color[front]*brightness,0,255).astype(np.uint8)
                region_z[front]=surface_depth[front]
        panel=Image.fromarray(pixels,"RGB")
        draw=ImageDraw.Draw(panel)
        draw.rectangle((0, 0, VIEW_SIZE-1, VIEW_SIZE-1), outline=(70, 78, 84), width=2)
        draw.rectangle((10, 10, 127, 38), fill=(34, 43, 50))
        draw.text((18, 17), f"VIEW {i}", fill="white")
        canvas.paste(panel, ((i%2)*VIEW_SIZE, (i//2)*VIEW_SIZE))
    buffer = io.BytesIO(); canvas.save(buffer, format="PNG")
    return buffer.getvalue(), views


def image_part(data: bytes):
    return {"type": "image_url", "image_url": {"url":
        "data:image/png;base64,"+base64.b64encode(data).decode("ascii")}}


def source_reference_bytes(path):
    """The exact source-object PNG submitted as IMAGE 2 to OpenRouter."""
    original=Image.open(path).convert("RGBA")
    if original.getbbox():original=original.crop(original.getbbox())
    original.thumbnail((720,720))
    original=ImageOps.contain(original,(720,720))
    # A deterministic light matte avoids relying on OpenRouter's unknown
    # presentation of transparent image pixels (sometimes black in previews).
    matte=Image.new("RGB",original.size,(250,250,249))
    matte.paste(original,mask=original.getchannel("A"))
    buffer=io.BytesIO();matte.save(buffer,format="PNG")
    return buffer.getvalue()


def save_model_inputs(plan_path, source_image, rendered_glb, pass_id):
    """User-auditable bit-for-bit visual evidence of what the model receives."""
    glb_path=plan_path.with_name("vision-input-glb-"+pass_id+".png")
    source_path=plan_path.with_name("vision-input-source-"+pass_id+".png")
    glb_path.write_bytes(rendered_glb)
    source_path.write_bytes(source_reference_bytes(source_image))
    print("VISION_INPUT_IMAGES",glb_path.relative_to(ROOT),source_path.relative_to(ROOT))


def vision_point(point, label):
    if not isinstance(point, list) or len(point) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or
            not math.isfinite(v) or not .01 <= v <= .99 for v in point):
        raise ValueError("Invalid vision point: " + label)


def vision_region(region, label):
    """A named functional part must have an explicit visible 2D boundary."""
    if (not isinstance(region, list) or len(region) != 4 or
            any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or
                v < 0 or v > 1 for v in region) or
            region[2]-region[0]<.012 or region[3]-region[1]<.012):
        raise ValueError("Vision did not bound actual region: " + label)


def validate_answer(answer, semantic=None):
    if not isinstance(answer, dict) or set(answer) != set(named_schema(semantic)["properties"]):
        raise ValueError("Vision landmark response has unexpected fields")
    if type(answer["view"]) is not int or answer["view"] not in (0, 1, 2, 3):
        raise ValueError("Invalid view")
    if (isinstance(answer["confidence"], bool) or
            not isinstance(answer["confidence"], (float, int)) or
            not math.isfinite(answer["confidence"]) or answer["confidence"] < .72 or
            answer["confidence"] > 1):
        raise ValueError("Functional edge insufficiently visible to annotate")
    for name in LANDMARKS:
        vision_point(answer[name], name)
    if semantic is not None:
        for collection, coordinate_fields in (("grips", ("point",)),
                                             ("features", ("origin", "direction_tip"))):
            wanted = {item["id"] for item in semantic[collection]}
            items = answer[collection]
            if (not isinstance(items, list) or len(items) != len(wanted) or
                    any(not isinstance(item, dict) or
                        set(item) != {"id", "view", "region", "evidence", *coordinate_fields} or
                        not isinstance(item["id"], str) or
                        type(item["view"]) is not int or
                        item["view"] not in (0, 1, 2, 3)
                        for item in items) or
                    {item["id"] for item in items} != wanted):
                raise ValueError("Cannot invent, omit or rename confirmed " + collection)
            for item in items:
                vision_region(item["region"], collection + "." + item["id"])
                if not isinstance(item["evidence"], str) or len(item["evidence"].strip())<15:
                    raise ValueError("Missing visible-function evidence for " + item["id"])
                for key in coordinate_fields:
                    vision_point(item[key], collection + "." + item["id"] + "." + key)
                    x,y=item[key]
                    left,top,right,bottom=item["region"]
                    if not left<=x<=right or not top<=y<=bottom:
                        raise ValueError("Vision point lies outside its named region: " + item["id"])
    if not isinstance(answer["explanation"], str):raise ValueError("Missing explanation")


def project_labelled_vertex(meshes, view, point):
    """Lift ONLY a supplied 2D vision point; never select a functional extremity."""
    pixel = np.array(point) * VIEW_SIZE
    nearby = []
    for mesh in meshes:
        world = mesh["world"]
        projection = np.column_stack([(world-view["center"]) @ view["right"],
            (world-view["center"]) @ view["up"]]) * view["scale"]
        pixels = np.column_stack([VIEW_SIZE/2+projection[:, 0],
                                  VIEW_SIZE/2-projection[:, 1]])
        distances = np.linalg.norm(pixels-pixel, axis=1)
        depth = (world-view["center"]) @ view["camera"]
        for i in np.argsort(distances)[:4]:
            nearby.append((float(distances[i]), -float(depth[i]), mesh, int(i)))
    nearby.sort(key=lambda entry: (entry[0], entry[1]))
    distance, _, mesh, index = nearby[0]
    if distance > VIEW_SIZE * .035:
        raise ValueError("Vision landmark lies outside the GLB: re-annotate")
    return {"local": [round(float(x), 7) for x in mesh["local"][index]],
            "mesh": mesh["mesh"], "primitive": mesh["primitive"],
            "error_px": round(distance, 1), "method": "vision-nearest-surface"}


def lift_landmarks(meshes, views, answer, semantic=None):
    """Lift vision-labelled roles onto the real GLB, without semantic guesses.

    Geometry may project a confirmed point to a surface, but must not invent
    which extremity is a working head or which silhouette is functional.
    """
    validate_answer(answer, semantic)
    result = {}
    # Every semantic role comes from vision, not a mesh length or width rule.
    for name in LANDMARKS:
        try:
            result[name] = project_labelled_vertex(meshes, views[answer["view"]], answer[name])
        except ValueError as error:
            raise ValueError(f"Vision landmark {name} lies outside the GLB: re-annotate") from error
    def pos(name):
        item = result[name]
        for m in meshes:
            if m["mesh"] == item["mesh"] and m["primitive"] == item["primitive"]:
                local = np.array(item["local"])
                j = np.argmin(np.linalg.norm(m["local"]-local, axis=1))
                return m["world"][j]
        raise ValueError("Landmark mesh missing")
    # These are sanity checks on the FOUR labelled points, not rules for
    # assigning any point's function to a particular part of the mesh.
    if np.linalg.norm(pos("handle_butt")-pos("grip_center"))<1e-5:
        raise ValueError("Vision identified a collapsed handle")
    shaft = pos("working_head")-pos("grip_center")
    blade = pos("functional_edge")-pos("working_head")
    if np.linalg.norm(shaft)<1e-6:raise ValueError("Grip and working head coincide")
    transverse = blade-shaft*np.dot(blade,shaft)/np.dot(shaft,shaft)
    if np.linalg.norm(transverse)<.025*np.linalg.norm(shaft):
        raise ValueError("Working edge indistinguishable from object shaft in 3D")
    if np.dot(pos("working_head")-pos("grip_center"), pos("grip_center")-pos("handle_butt")) < 0:
        raise ValueError("Vision chose incompatible handle/head ordering")
    return result


def lift_named_landmarks(meshes, views, answer, semantic):
    """Physically locate EVERY source-named handhold and action direction."""
    validate_answer(answer, semantic)
    result = {"grips": {}, "features": {}}
    for grip in answer["grips"]:
        result["grips"][grip["id"]] = project_labelled_vertex(
            meshes, views[grip["view"]], grip["point"])
    for feature in answer["features"]:
        origin = project_labelled_vertex(meshes, views[feature["view"]], feature["origin"])
        tip = project_labelled_vertex(meshes, views[feature["view"]], feature["direction_tip"])
        if origin["mesh"] == tip["mesh"] and origin["local"] == tip["local"]:
            raise ValueError("Functional direction collapses on the 3D object: re-annotate")
        result["features"][feature["id"]] = {"origin": origin, "direction_tip": tip}
    return result


def annotated_view_image(source, answer):
    """Make the model's actual claimed semantic regions inspectable as PNG."""
    picture=Image.open(io.BytesIO(source)).convert("RGB")
    draw=ImageDraw.Draw(picture)
    for kind,color,points in (("grips",(20,115,230),("point",)),
                              ("features",(223,45,67),("origin","direction_tip"))):
        for item in answer.get(kind,[]):
            if not isinstance(item,dict) or item.get("view") not in (0,1,2,3):continue
            view=item["view"]
            ox,oy=(view%2)*VIEW_SIZE,(view//2)*VIEW_SIZE
            region=item.get("region",[])
            if isinstance(region,list) and len(region)==4:
                box=[ox+region[0]*VIEW_SIZE,oy+region[1]*VIEW_SIZE,
                     ox+region[2]*VIEW_SIZE,oy+region[3]*VIEW_SIZE]
                draw.rectangle(box,outline=color,width=3)
                draw.text((box[0],max(40,box[1]-18)),item.get("id","?"),fill=color)
            for name in points:
                point=item.get(name,[])
                if isinstance(point,list) and len(point)==2:
                    x,y=ox+point[0]*VIEW_SIZE,oy+point[1]*VIEW_SIZE
                    draw.ellipse((x-5,y-5,x+5,y+5),fill=color,outline=(255,255,255),width=2)
            if kind=="features" and all(isinstance(item.get(k),list) and
                    len(item[k])==2 for k in points):
                a,b=(item[k] for k in points)
                draw.line((ox+a[0]*VIEW_SIZE,oy+a[1]*VIEW_SIZE,
                           ox+b[0]*VIEW_SIZE,oy+b[1]*VIEW_SIZE),fill=color,width=3)
    out=io.BytesIO();picture.save(out,format="PNG")
    return out.getvalue()


def run(plan_path: Path, check=False, pass_id="primary", model=MODEL):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,48}",pass_id):
        raise ValueError("Vision pass ID must identify one immutable analysis")
    if not re.fullmatch(r"[a-zA-Z0-9_./:-]{3,120}",model):
        raise ValueError("Invalid OpenRouter spatial vision model")
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
    semantic, interaction_hash = confirmed_interaction(plan_path, plan)
    previous = plan.get("mesh_landmarks", {})
    complete_named = (semantic is None or
        (previous.get("interaction_sha256") == interaction_hash and
         set(previous.get("grips", {})) == {g["id"] for g in semantic["grips"]} and
         set(previous.get("features", {})) == {f["id"] for f in semantic["features"]}))
    if previous.get("glb_sha256") == digest and complete_named and pass_id=="primary":
        print("3D functional landmarks already present; zero paid requests")
        return
    if check:
        print("3D functional landmarks missing")
        return
    meshes = glb_geometry(glb)
    render, views = make_views(meshes)
    save_model_inputs(plan_path,image,render,pass_id)
    receipt_dir=plan_path.parent/"vision-landmark-receipts"
    signature=hashlib.sha256(json.dumps({"glb":digest,
        "interaction":interaction_hash,"pass_id":pass_id,"model":model,
        "schema":named_schema(semantic),"prompt":PROMPT,
        "actual_glb_image_sha256":hashlib.sha256(render).hexdigest(),
        "source_reference_image_sha256":hashlib.sha256(source_reference_bytes(image)).hexdigest()},
        sort_keys=True).encode()).hexdigest()
    receipt=receipt_dir/("landmarks-"+signature+".json")
    if receipt.exists():
        cached = json.loads(receipt.read_text())
        if (cached.get("glb_sha256") != digest or
                cached.get("interaction_sha256") != interaction_hash or
                cached.get("pass_signature") != signature or
                "raw_landmarks" not in cached):
            raise ValueError("Prior spatial vision pass is pending/invalid; no blind paid retry")
        answer = cached["raw_landmarks"]
    else:
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:raise RuntimeError("Missing OPENROUTER_API_KEY (run the pipeline Actions)")
        parts = [
            {"type": "text", "text": "IMAGE 1: generated 3D GLB, four labeled views"},
            image_part(render),
            {"type": "text", "text": "IMAGE 2: reference concept for functional edge only"},
            image_part(source_reference_bytes(image)),
        ]
        if semantic is not None:
            parts.append({"type": "text", "text":
                "AUTHORITATIVE VISUAL CHARACTERIZATION: annotate EACH named grip "
                "and EACH functional direction on the ACTUAL GLB. You may choose "
                "a DIFFERENT VIEW for each grip or functional feature; the origin "
                "and tip of one direction share a view. Use ONLY the supplied IDs. "
                "For EVERY named role, first DRAW a tight region as normalized "
                "[xmin,ymin,xmax,ymax] in that panel, then choose physical "
                "point(s) INSIDE that region and describe visible evidence. "
                "The region must bound the REAL part, not the whole object or background. "
                "If a handhold, working region or direction is not truly visible "
                "on the 3D object, lower confidence. Never infer which end or "
                "surface is functional by length or width. " +
                json.dumps({key: semantic[key] for key in ("object_kind", "grips", "features", "modes")},
                    ensure_ascii=False)})
        payload = {"model": model, "temperature": 0, "max_tokens": 2400 if semantic else 520,
            "provider": {"require_parameters": True},
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "glb_prop_landmarks", "strict": True,
                "schema": named_schema(semantic)}},
            "messages": [{"role": "system", "content": PROMPT},
                {"role": "user", "content": parts}]}
        receipt_dir.mkdir(parents=True,exist_ok=True)
        receipt.write_text(json.dumps({"schema":2,"pass_signature":signature,
            "glb_sha256":digest,"interaction_sha256":interaction_hash,
            "pass_id":pass_id,"model":model,
            "status":"submission-outcome-unknown"},indent=2)+"\n")
        request = Request(ENDPOINT, data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": "Bearer "+key, "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/leye0/WarConquer",
                     "X-Title": "WarConquer intrinsic GLB grip landmarks"})
        with urlopen(request, timeout=150) as response:
            data = json.loads(response.read(160000))
        answer = json.loads((data.get("choices") or [{}])[0]["message"]["content"])
        receipt.write_text(json.dumps({"schema":2, "glb_sha256": digest,
            "interaction_sha256": interaction_hash,
            "pass_signature":signature,"pass_id":pass_id,
            "model":model, "raw_landmarks":answer}, indent=2)+"\n")
    preview=plan_path.with_name("vision-landmarks-"+pass_id+".png")
    preview.write_bytes(annotated_view_image(render,answer))
    landmarks = lift_landmarks(meshes, views, answer, semantic)
    named = lift_named_landmarks(meshes, views, answer, semantic) if semantic else {}
    plan["mesh_landmarks"] = {"schema":1,"glb_sha256":digest,
        "model":model,"view":answer["view"],"confidence":answer["confidence"],
        "points":landmarks,"explanation":answer["explanation"],
        **({"interaction_sha256": interaction_hash, **named} if semantic else {})}
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+"\n")
    print("Saved reusable 3D grip/contact landmark contract:", plan_path.relative_to(ROOT))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--pass-id",default="primary",
        help="Distinct source-matched OpenRouter spatial analysis; no one-call limit")
    parser.add_argument("--model",default=MODEL)
    parser.add_argument("--render-preview",action="store_true",
        help="Save exactly the two texture/source images supplied to vision, without API calls")
    args = parser.parse_args()
    target=(ROOT/args.plan).resolve()
    if args.render_preview:
        if not target.is_file() or not target.is_relative_to(ROOT):
            raise ValueError("Invalid canonical plan for preview")
        plan=json.loads(target.read_text())
        mesh=glb_geometry(ROOT/plan["inputs"]["object_glb"])
        render,_=make_views(mesh)
        save_model_inputs(target,ROOT/plan["inputs"]["object_image"],render,args.pass_id)
    else:
        run(target,args.check,args.pass_id,args.model)
