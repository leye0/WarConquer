#!/usr/bin/env python3
"""One small, deterministic vision pass on an isolated prop, never on live clients.

Produces semantic 2D landmarks. The 3D grip is subsequently derived from the
actual GLB vertices (not assumed to share the source image's orientation).
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
SOURCE = ROOT / "assets/concepts/marches/objects/hache_arme.png"
TARGET = ROOT / "assets/experiments/props/marches_hache/trellis-v1/grip-vision.json"
MODEL = "openai/gpt-4.1-mini"
URL = "https://openrouter.ai/api/v1/chat/completions"

POINT = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
PROPERTIES = {
    "object_type": {"type": "string", "enum": ["axe", "sword", "spear", "staff", "hammer", "other"]},
    "holding_hand": {"type": "string", "enum": ["right", "left", "either"]},
    "handle_butt": POINT,
    "handle_near_head": POINT,
    "grip_center": POINT,
    "head_center": POINT,
    "striking_edge": POINT,
    "confidence": {"type": "number"},
}
SCHEMA = {
    "type": "object", "properties": PROPERTIES,
    "required": list(PROPERTIES), "additionalProperties": False,
}
PROMPT = (
    "Analyze ONLY the isolated handheld game-asset image. Return normalized [x,y] "
    "pixel locations (0=left/top, 1=right/bottom). Locate the extreme butt/pommel "
    "end of the HANDLE, where handle meets weapon head, center of a realistic ONE-HANDED "
    "grip (the palm envelops the shaft, not the blade or head), center of the weighted "
    "head, and the outward-facing striking edge. Do not confuse axe blade with handle. "
    "The 3D model may be rotated, so do not output 3D Euler angles or guess a 3D axis. "
    "Classify the weapon and suggest the hand. Return a confidence from 0 to 1."
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_points(raw: dict) -> dict:
    if set(raw) != set(PROPERTIES):
        raise ValueError("Vision JSON has missing or unexpected keys")
    if raw["object_type"] not in SCHEMA["properties"]["object_type"]["enum"]:
        raise ValueError("Unexpected weapon category")
    if raw["holding_hand"] not in ("right", "left", "either"):
        raise ValueError("Unexpected holding hand")
    if not isinstance(raw["confidence"], (float, int)) or not .55 <= raw["confidence"] <= 1:
        raise ValueError("Vision confidence too low; request human review")
    for k in ("handle_butt", "handle_near_head", "grip_center", "head_center", "striking_edge"):
        p = raw[k]
        if not isinstance(p, list) or len(p) != 2 or any(
            not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in p
        ):
            raise ValueError("Invalid normalized landmark " + k)
    start, end, grip = (raw[k] for k in ("handle_butt", "handle_near_head", "grip_center"))
    axis = [end[0] - start[0], end[1] - start[1]]
    sq = axis[0] ** 2 + axis[1] ** 2
    if sq < .0144:
        raise ValueError("Handle endpoints too close")
    fraction = ((grip[0] - start[0]) * axis[0] + (grip[1] - start[1]) * axis[1]) / sq
    deviation = abs((grip[0] - start[0]) * axis[1] - (grip[1] - start[1]) * axis[0]) / math.sqrt(sq)
    if not .04 <= fraction <= .62 or deviation > .14:
        raise ValueError("Grip is not on the lower handle; manual review required")
    return {"landmarks": raw, "grip_fraction_from_butt": round(fraction, 5),
            "image_handle_deviation": round(deviation, 5)}


def analyze() -> None:
    sha = digest(SOURCE)
    if TARGET.exists():
        data = json.loads(TARGET.read_text())
        if data.get("source_sha256") != sha:
            raise ValueError("Source changed: do not overwrite approved analysis silently")
        validate_points(data["analysis"]["landmarks"])
        print("Reusing pinned vision landmarks; no API charge")
        return
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY GitHub Actions secret")
    encoded = base64.b64encode(SOURCE.read_bytes()).decode("ascii")
    payload = {
        "model": MODEL, "temperature": 0, "seed": 20261027,
        "max_tokens": 420,
        "provider": {"require_parameters": True},
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "handheld_prop_landmarks", "strict": True, "schema": SCHEMA},
        },
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Identify a natural grip on this exact source PNG."},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + encoded}},
            ]},
        ],
    }
    request = Request(URL, data=json.dumps(payload).encode("utf-8"),
                      headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                               "HTTP-Referer": "https://github.com/leye0/WarConquer",
                               "X-Title": "WarConquer prop grip analyzer"}, method="POST")
    # A single paid vision request: no automatic retries or guessed fallback.
    with urlopen(request, timeout=120) as response:
        result = json.loads(response.read(120000))
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("Vision model returned no choices")
    raw = json.loads(choices[0]["message"]["content"])
    checked = validate_points(raw)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps({
        "schema": 1, "source_image": str(SOURCE.relative_to(ROOT)),
        "source_sha256": sha, "vision_model": MODEL, "analysis": checked,
        "geometry_note": "2D semantics only; GLB principal axis, head end, shaft center and palm transform are calculated at runtime.",
        "paid_vision_requests": 1,
    }, ensure_ascii=False, indent=2) + "\n")
    print("Vision analysis saved and validated; fraction from butt =", checked["grip_fraction_from_butt"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate existing output without a network call")
    args = parser.parse_args()
    if args.check:
        if TARGET.exists():
            data = json.loads(TARGET.read_text())
            if data["source_sha256"] != digest(SOURCE):
                raise ValueError("Stale landmark source")
            print(validate_points(data["analysis"]["landmarks"]))
        else:
            print("No analysis yet; waiting for first scheduled Actions vision run")
    else:
        analyze()
