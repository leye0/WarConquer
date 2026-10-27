#!/usr/bin/env python3
"""Generic, low-cost image-driven attachment specification for any handheld prop.

Inputs: two PNG images (isolated prop + intended character) and an arbitrary GLB.
Output: one pinned, validated semantic grip plan consumed by game-side 3D fitting.
The vision model makes the design decisions; the renderer solves actual transforms.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_REQUEST = "assets/experiments/props/marches_hache/trellis-v1/grip-request.json"
POINT = {"type": "array", "items": {"type": "number"}}
PROPS = {
    "object_kind": {"type": "string", "enum": ["axe", "sword", "spear", "staff", "hammer", "shield", "tool", "other"]},
    "grip_geometry": {"type": "string", "enum": ["shaft", "flat_handle", "body", "unsupported"]},
    "hold_mode": {"type": "string", "enum": ["one_hand", "two_hands", "unsupported"]},
    "dominant_hand": {"type": "string", "enum": ["right", "left", "either"]},
    "handle_butt": POINT,
    "handle_near_head": POINT,
    "grip_point": POINT,
    "head_center": POINT,
    "action_edge": POINT,
    "head_direction": {"type": "string", "enum": ["toward_elbow", "toward_fingers", "up", "down", "forward", "backward"]},
    "edge_direction": {"type": "string", "enum": ["forward", "backward", "outward", "inward"]},
    "length_relative_character_height": {"type": "number"},
    "palm_from_wrist": {"type": "number"},
    "confidence": {"type": "number"},
    "explanation": {"type": "string"},
}
SCHEMA = {"type": "object", "properties": PROPS,
          "required": list(PROPS), "additionalProperties": False}
PROMPT = (
    "You are a technical prop rigger for an isometric 3D game. IMAGE 1 is an isolated "
    "weapon or object; IMAGE 2 is the intended character. Analyze BOTH images and "
    "produce a GENERAL REUSABLE ATTACHMENT SPECIFICATION for an animated character. "
    "Object landmarks must use normalized [x,y] coords of IMAGE 1. The butt is the "
    "end of the handle furthest from its working head. The upper handle endpoint "
    "is the handle's intersection with the head, not the edge. The grip_point "
    "is the center of the character's palm gripping that handle (not the blade). "
    "Decide whether one or two hands are anatomically natural, which hand is primary, "
    "how the head extends relative to the hand in a neutral standing pose, which "
    "direction the cutting/working edge faces relative to the walking character "
    "(forward, backward, inward toward torso, or outward from torso). Estimate the "
    "object length divided by the CHARACTER HEIGHT, accounting for the visual style. "
    "Estimate palm position as 0 at the wrist joint and 1 at the finger knuckles. "
    "Return specs and confidence. If handle cannot be identified, set unsupported "
    "instead of inventing points. DO NOT infer raw GLB axis or Euler coordinates: "
    "the 3D pipeline computes actual axes from imported vertices."
)


def local(path: str) -> Path:
    candidate = (ROOT / path).resolve()
    if not candidate.is_relative_to(ROOT) or not candidate.is_file():
        raise ValueError("Invalid or missing local asset: " + path)
    return candidate


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_request(path: str) -> tuple[dict, Path, Path, Path, Path]:
    cfg = json.loads(local(path).read_text())
    expected = {"schema", "experiment", "object_image", "character_image",
                "object_glb", "output_path", "vision_model",
                "maximum_paid_requests", "automatic_paid_retries"}
    if set(cfg) != expected or cfg["schema"] != 1:
        raise ValueError("Unexpected grip-plan request schema")
    if cfg["maximum_paid_requests"] != 1 or cfg["automatic_paid_retries"] != 0:
        raise ValueError("This experiment permits one vision request and zero retries")
    for key in ("object_image", "character_image", "object_glb", "output_path"):
        if not isinstance(cfg[key], str) or cfg[key].startswith("/"):
            raise ValueError("All paths must be repository-relative")
    if not isinstance(cfg["experiment"], str) or not cfg["experiment"]:
        raise ValueError("Experiment identifier missing")
    if cfg["vision_model"] != "google/gemini-2.5-flash-lite":
        raise ValueError("Explicitly reviewed low-cost vision model required")
    obj = local(cfg["object_image"])
    char = local(cfg["character_image"])
    glb = local(cfg["object_glb"])
    if obj.suffix.lower() not in (".png", ".jpg", ".jpeg") or char.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        raise ValueError("Vision source must be an image")
    if glb.suffix.lower() != ".glb":
        raise ValueError("Missing GLB for the geometry stage")
    output = (ROOT / cfg["output_path"]).resolve()
    if not output.is_relative_to(ROOT) or output.suffix != ".json":
        raise ValueError("Output must be a JSON inside this repository")
    return cfg, obj, char, glb, output


def validate(raw: dict) -> dict:
    if not isinstance(raw, dict) or set(raw) != set(PROPS):
        raise ValueError("Vision output fields differ from the pinned schema")
    for key, spec in PROPS.items():
        if "enum" in spec and raw[key] not in spec["enum"]:
            raise ValueError("Unsupported " + key)
    for field in ("confidence", "length_relative_character_height", "palm_from_wrist"):
        value = raw[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Non-numeric " + field)
    if raw["confidence"] < .6 or raw["confidence"] > 1:
        raise ValueError("Low confidence; do not fabricate grip")
    if not .13 <= raw["length_relative_character_height"] <= 1.85:
        raise ValueError("Implausible prop/character size ratio")
    if not 0 <= raw["palm_from_wrist"] <= 1:
        raise ValueError("Grip anchor outside palm")
    for field in ("handle_butt", "handle_near_head", "grip_point", "head_center", "action_edge"):
        point = raw[field]
        if not isinstance(point, list) or len(point) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            or v < 0 or v > 1 for v in point
        ):
            raise ValueError("Bad landmark " + field)
    if not isinstance(raw["explanation"], str) or not 8 <= len(raw["explanation"]) <= 800:
        raise ValueError("Missing concise semantic justification")
    if raw["grip_geometry"] != "shaft" or raw["hold_mode"] == "unsupported":
        return {"grip_fraction_from_butt": None, "image_deviation": None,
                "supported_by_current_geometry_fitter": False}
    start, end, grip = (raw[key] for key in ("handle_butt", "handle_near_head", "grip_point"))
    axis = [end[0]-start[0],end[1]-start[1]]
    sq = axis[0]**2+axis[1]**2
    if sq < .0144:
        raise ValueError("Shaft image endpoints too close")
    fraction = ((grip[0]-start[0])*axis[0]+(grip[1]-start[1])*axis[1])/sq
    deviation = abs((grip[0]-start[0])*axis[1]-(grip[1]-start[1])*axis[0])/math.sqrt(sq)
    if not .04 <= fraction <= .68 or deviation > .15:
        raise ValueError("Vision grip not located on the shaft")
    return {"grip_fraction_from_butt": round(fraction, 5),
            "image_deviation": round(deviation, 5),
            "supported_by_current_geometry_fitter": True}


def image_part(path: Path) -> dict:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return {"type": "image_url", "image_url": {
        "url": "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    }}


def run(request_path: str, check: bool) -> None:
    cfg, obj, char, glb, output = read_request(request_path)
    provenance = {"object_image_sha256": sha(obj), "character_image_sha256": sha(char),
                  "prop_glb_sha256": sha(glb)}
    if output.exists():
        saved = json.loads(output.read_text())
        if saved.get("input_hashes") != provenance or saved.get("vision_model") != cfg["vision_model"]:
            raise ValueError("Inputs changed; use a new versioned experiment instead of overwriting")
        validate(saved["specifications"])
        print("Vision attachment specifications already pinned: no paid call")
        return
    if check:
        print("No generated plan yet")
        return
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY Actions secret not configured")
    payload = {
        "model": cfg["vision_model"], "temperature": 0, "max_tokens": 850,
        "provider": {"require_parameters": True},
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "prop_attachment_plan", "strict": True, "schema": SCHEMA},
        },
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "IMAGE 1: isolated prop source."},
                image_part(obj),
                {"type": "text", "text": "IMAGE 2: character concept; assess realistic relative scale and grip."},
                image_part(char),
            ]},
        ],
    }
    req = Request(ENDPOINT, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/leye0/WarConquer",
                 "X-Title": "WarConquer generic prop attachment"})
    with urlopen(req, timeout=150) as response:
        answer = json.loads(response.read(160000))
    content = (answer.get("choices") or [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise ValueError("Vision provider returned no JSON text")
    spec = json.loads(content)
    fit = validate(spec)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "schema": 2, "experiment": cfg["experiment"], "vision_model": cfg["vision_model"],
        "inputs": {key: cfg[key] for key in ("object_image", "character_image", "object_glb")},
        "input_hashes": provenance, "specifications": spec, "derived_image_geometry": fit,
        "paid_vision_requests": 1, "automatic_paid_retries": 0
    }, ensure_ascii=False, indent=2) + "\n")
    print("Saved validated generic image-driven attachment specification:",output.relative_to(ROOT))
    print("Object:",spec["object_kind"],"hand:",spec["dominant_hand"],
          "length/height:",spec["length_relative_character_height"],"grip:",fit["grip_fraction_from_butt"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", default=DEFAULT_REQUEST)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.request, args.check)
