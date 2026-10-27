#!/usr/bin/env python3
"""Free GLB silhouette projection helpers for 3D rig QA. No legacy sprite workflow."""
import math
import numpy as np
from PIL import Image,ImageDraw

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


