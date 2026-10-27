#!/usr/bin/env python3
"""Inspect head/neck animation against the actual approved rig's bind pose.

Pure read-only glTF math: reports angular deviation of each animated joint
relative to its original local bind rotation and the motion range within the
clip. No assumptions about mesh face direction or Blender axis conventions.
"""
from __future__ import annotations
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/fal-mixamo-v1/warconquer-textured-playable.glb"


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def degrees_between(a, b):
    x = math.sqrt(sum(float(q) ** 2 for q in a))
    y = math.sqrt(sum(float(q) ** 2 for q in b))
    dot = sum(float(u) * float(v) for u, v in zip(a, b)) / max(x * y, 1e-12)
    return 2 * math.degrees(math.acos(min(1.0, abs(dot))))


def inspect():
    glb = module(ROOT / "scripts/build-mixamo-playable.py", "wc_glb_head_diag")
    doc, raw = glb.load_glb(TARGET)
    joints = {}
    for i, n in enumerate(doc["nodes"]):
        name = "".join(c for c in n.get("name", "").lower() if c.isalnum())
        for part in ("head", "neck"):
            if name.endswith(part):
                joints[part] = i
    if set(joints) != {"head", "neck"}:
        raise RuntimeError("Head and neck joints not both identified: " + repr(joints))
    results = []
    for animation in doc["animations"]:
        for part, idx in joints.items():
            channels = [c for c in animation["channels"]
                        if c["target"]["node"] == idx and c["target"]["path"] == "rotation"]
            if len(channels) != 1:
                raise RuntimeError("Head/neck expected one rotation track per animation")
            values = glb.accessor(doc, raw,
                animation["samplers"][channels[0]["sampler"]]["output"])
            rest = doc["nodes"][idx].get("rotation", [0, 0, 0, 1])
            errors = [degrees_between(q, rest) for q in values]
            first = values[0]
            spread = [degrees_between(q, first) for q in values]
            results.append({
                "clip": animation["name"], "bone": part,
                "start_degrees_from_bind": round(errors[0], 2),
                "average_degrees_from_bind": round(sum(errors) / len(errors), 2),
                "max_degrees_from_bind": round(max(errors), 2),
                "max_motion_degrees_from_first_frame": round(max(spread), 2),
                "frames": len(values),
            })
    print("HEAD_ANIMATION_DIAGNOSTIC", json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    inspect()
