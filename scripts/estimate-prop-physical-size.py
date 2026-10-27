#!/usr/bin/env python3
"""Estimate an object's approximate physical length from its source, once.

The vision model knows the original creation description and sees the original
object illustration plus the unit concept. It has no previous ratio, model
outputs, 3D game screenshots, or mesh measurements. Result is *centimetres*.
No automatic retry and no implicit hard-coded weapon dimensions.
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
DEFAULT = "assets/experiments/props/marches_hache/trellis-v1/physical-size-request.json"
MODEL = "google/gemini-2.5-flash-lite"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

FIELDS = {
    "estimated_length_cm": {"type": "number"},
    "confidence": {"type": "number"},
    "reason": {"type": "string"},
}
SCHEMA = {"type": "object", "properties": FIELDS, "required": list(FIELDS),
          "additionalProperties": False}
PROMPT = (
    "Estimate the approximate real-world LENGTH in CENTIMETRES of the SINGLE "
    "equipment object described and pictured. You are given its ORIGINAL "
    "GENERATION DESCRIPTION, its isolated design (IMAGE 1), and the original "
    "character concept holding it (IMAGE 2). You know what the object is; "
    "use common-sense physical dimensions and the design to choose a "
    "plausible approximate length, not pixel ratios. For elongated tools "
    "or weapons, LENGTH means distance from the handle butt to the end "
    "along the handle's main axis, not a diagonal to the side of a blade. "
    "Do not derive size from the isolated image canvas; it has no scale. "
    "Do not replicate an existing fitted 3D result; none is supplied. "
    "Do not assume that two-handed means taller than the wearer. "
    "Return ONLY estimated_length_cm, confidence and a brief rationale. "
    "An approximation is expected, not a precise measurement."
)

def local(path: str) -> Path:
    if not isinstance(path, str) or not path or path.startswith("/"):
        raise ValueError("Invalid relative path")
    value = (ROOT / path).resolve()
    if not value.is_relative_to(ROOT) or not value.is_file():
        raise ValueError("Missing source file " + path)
    return value

def load(request: str):
    cfg = json.loads(local(request).read_text())
    expected = {"schema", "object_image", "character_image", "generation_request",
                "output_path", "vision_model", "maximum_paid_requests",
                "automatic_paid_retries"}
    if set(cfg) != expected or cfg["schema"] != 1 or cfg["vision_model"] != MODEL:
        raise ValueError("Invalid object size request")
    if cfg["maximum_paid_requests"] != 1 or cfg["automatic_paid_retries"] != 0:
        raise ValueError("Request may only make one paid inference")
    paths = {k: local(cfg[k]) for k in ("object_image", "character_image", "generation_request")}
    brief = json.loads(paths["generation_request"].read_text())
    if brief.get("output") != cfg["object_image"] or cfg["character_image"] not in brief.get("references", []):
        raise ValueError("Object description or character provenance mismatch")
    if not isinstance(brief.get("prompt"), str) or not brief["prompt"]:
        raise ValueError("Missing original equipment description")
    out = (ROOT / cfg["output_path"]).resolve()
    if not out.is_relative_to(ROOT) or out.suffix != ".json":
        raise ValueError("Unsafe output path")
    hashes = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()}
    return cfg, paths, brief["prompt"], out, hashes

def validate(raw):
    if not isinstance(raw, dict) or set(raw) != set(FIELDS):
        raise ValueError("Incomplete physical length estimate")
    length = raw["estimated_length_cm"]
    confidence = raw["confidence"]
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v)
           for v in (length, confidence)):
        raise ValueError("Invalid size / confidence")
    if not 2 <= length <= 1000 or not 0 <= confidence <= 1:
        raise ValueError("Implausible object length; no silent clamp")
    if not isinstance(raw["reason"], str) or len(raw["reason"]) < 15:
        raise ValueError("Missing reasoning")
    return raw

def store(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)

def to_image(path):
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    content = path.read_bytes()
    if len(content) > 9_000_000:
        raise ValueError("Original image too large")
    return {"type": "image_url", "image_url": {
        "url": "data:" + mime + ";base64," + base64.b64encode(content).decode()}}

def run(request, check):
    cfg, paths, brief, out, hashes = load(request)
    checkpoint = out.with_name(out.stem + "-response.json")
    if out.exists():
        doc = json.loads(out.read_text())
        if doc.get("input_hashes") != hashes or doc.get("vision_model") != MODEL:
            raise ValueError("Old output belongs to another source; use new filename")
        validate({k: doc[k] for k in FIELDS})
        print("Existing size estimate:", doc["estimated_length_cm"], "cm; no cost")
        return
    if check:
        print("Inputs valid; no previous estimate; no model call")
        return
    if checkpoint.exists():
        response = json.loads(checkpoint.read_text())
        if response.get("input_hashes") != hashes or response.get("vision_model") != MODEL:
            raise ValueError("Cached provider response belongs to another source")
        estimate = response["estimate"]
    else:
        secret = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not secret:
            raise ValueError("Missing OPENROUTER_API_KEY")
        payload = {
            "model": MODEL, "temperature": 0, "max_tokens": 700,
            "usage": {"include": True},
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "equipment_physical_length", "strict": True, "schema": SCHEMA}},
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "Original generation description:\n" + brief},
                    {"type": "text", "text": "IMAGE 1: isolated equipment"},
                    to_image(paths["object_image"]),
                    {"type": "text", "text": "IMAGE 2: original wearer carrying the equipment"},
                    to_image(paths["character_image"])
                ]}
            ],
        }
        req = Request(ENDPOINT, data=json.dumps(payload).encode(), method="POST",
                      headers={"Authorization": "Bearer " + secret,
                               "Content-Type": "application/json",
                               "HTTP-Referer": "https://github.com/leye0/WarConquer",
                               "X-Title": "WarConquer approximate physical equipment length"})
        with urlopen(req, timeout=130) as result:
            answer = json.loads(result.read(150000))
        message = (answer.get("choices") or [{}])[0].get("message", {}).get("content")
        if not isinstance(message, str):
            raise ValueError("Provider returned no usable response")
        estimate = json.loads(message)
        usage = answer.get("usage") or {}
        cost = usage.get("cost") if isinstance(usage, dict) else None
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
            cost = None
        # Cache before validation; no automatic billable retry on bad numbers.
        store(checkpoint, {"schema": 1, "vision_model": MODEL,
                           "input_hashes": hashes, "estimate": estimate,
                           "usage": usage, "observed_cost_usd": cost})
    validate(estimate)
    used = json.loads(checkpoint.read_text())
    store(out, {"schema": 1, "vision_model": MODEL, "input_hashes": hashes,
                **estimate, "units": "cm", "source": "original_design",
                "usage": used.get("usage"), "observed_cost_usd": used.get("observed_cost_usd")})
    print("Physical length estimate:", estimate["estimated_length_cm"], "cm",
          "| OpenRouter USD:", used.get("observed_cost_usd"))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--request", default=DEFAULT)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    run(args.request, args.check)
