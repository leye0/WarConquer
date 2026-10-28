#!/usr/bin/env python3
"""Characterize object × character × Mixamo intent before 3D attachment.

Vision supplies every semantic role. The motion index supplies only candidate
clips; real animated joint contact must be validated later. One paid request
maximum, with a persisted receipt and no automatic paid retry.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MODEL = "google/gemini-2.5-flash-lite"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
IDENT = re.compile(r"[a-z][a-z0-9_]*\Z")
JOINT_ANCHORS = {
    "left": {"wrist_chain": ["leftarm", "leftforearm", "lefthand"],
             "contact_bone": "lefthand"},
    "right": {"wrist_chain": ["rightarm", "rightforearm", "righthand"],
              "contact_bone": "righthand"},
}

POINT = {"type": "array", "items": {"type": "number"}}
FEATURE = {"type": "object", "additionalProperties": False, "properties": {
    "id": {"type": "string"}, "function": {"type": "string"},
    "origin": POINT, "direction_tip": POINT,
    "direction_semantics": {"type": "string"}, "evidence": {"type": "string"}},
    "required": ["id", "function", "origin", "direction_tip",
                 "direction_semantics", "evidence"]}
GRIP = {"type": "object", "additionalProperties": False, "properties": {
    "id": {"type": "string"}, "point": POINT,
    "surface": {"type": "string"}, "evidence": {"type": "string"}},
    "required": ["id", "point", "surface", "evidence"]}
MODE = {"type": "object", "additionalProperties": False, "properties": {
    "id": {"type": "string"}, "phase": {"type": "string", "enum": ["carry", "use"]},
    "hands": {"type": "integer", "enum": [1, 2]},
    "primary_hand": {"type": "string", "enum": ["left", "right"]},
    "primary_grip": {"type": "string"},
    "secondary_hand": {"type": "string", "enum": ["none", "left", "right"]},
    "secondary_grip": {"type": "string"},
    "functional_feature": {"type": "string"},
    "action_direction": {"type": "string", "enum": ["none", "forward", "backward",
        "up", "down", "outward", "inward", "gravity", "toward_elbow",
        "toward_fingers", "palm_normal", "back_of_hand", "across_palm",
        "opposite_across_palm"]},
    "mixamo_role": {"type": "string"},
    "action_intent": {"type": "string"}, "evidence": {"type": "string"}},
    "required": ["id", "phase", "hands", "primary_hand", "primary_grip",
                 "secondary_hand", "secondary_grip", "functional_feature", "action_direction",
                 "mixamo_role", "action_intent", "evidence"]}
SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "object_kind": {"type": "string"},
    "object_function": {"type": "string"},
    "object_evidence": {"type": "string"},
    "features": {"type": "array", "items": FEATURE},
    "grips": {"type": "array", "items": GRIP},
    "modes": {"type": "array", "items": MODE},
    "confidence": {"type": "number"},
    "uncertainties": {"type": "array", "items": {"type": "string"}},
    "explanation": {"type": "string"}},
    "required": ["object_kind", "object_function", "object_evidence", "features", "grips",
                 "modes", "confidence", "uncertainties", "explanation"]}
PROMPT = (
    "You are the WarConquer semantic interaction analyst, NOT a geometry fitter. "
    "IMAGE 1 is the isolated object and IMAGE 2 the intended character. "
    "The original design brief and declared object kind are authoritative; "
    "cross-check them with BOTH images and flag contradictions. "
    "The included Mixamo motion catalog lists real source clips and their roles, "
    "but a clip name alone does NOT prove hand contact or physical compatibility. "
    "First identify WHAT every relevant part DOES: handle or other graspable "
    "region, cutting edge, bow front/string, muzzle/trigger, impact face, "
    "shield facing, etc., according to the ACTUAL item. Use open semantic role "
    "names, never assume a long or wide mesh end has a particular function. "
    "Do not label the farthest tip as an action part merely because it is "
    "geometrically extreme: establish functional identity from image + brief. "
    "For each functional feature give its image origin, a direction tip and a "
    "precise explanation of the real-world effect/forward sign. "
    "Specify at least one CARRY and one USE mode. Each mode must name "
    "one or two expected hands and exact labelled grasp regions; a two-hand "
    "mode MUST identify two genuinely distinct regions. Different phases may "
    "have different hand counts, e.g. carrying a bow vs drawing it, carrying "
    "a firearm vs aiming/reloading. Pick the intended primary hand from the "
    "character evidence, never a default side. Select an ACTION_DIRECTION "
    "from the permitted "
    "anatomical/world directions for each USE mode. For passive carrying "
    "action_direction must be 'none'. The direction is where the active "
    "object feature should point relative to the actor/target, and must "
    "come from the action concept, not from which mesh extremity is longest. "
    "Use a candidate Mixamo role "
    "from the provided included clips for USE; use 'none' for unscripted carry. "
    "Do NOT claim that the Mixamo pose is verified; later joint/IK tests do that. "
    "Use the provided standardized Mixamo hand/wrist/forearm joint names for "
    "anatomical hand intent, but do not fabricate unobserved joint positions. "
    "All [x,y] coordinates are normalized within IMAGE 1. If any role, "
    "functional direction, grasp region, or hand choice is ambiguous, report "
    "that in uncertainties and lower confidence. Do not invent missing facts. "
    "Return strictly the requested JSON schema."
)


def local(path, existing=True):
    if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path:
        raise ValueError("Unsafe repository-relative path")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT) or (existing and not resolved.is_file()):
        raise ValueError("Missing or unsafe repository file: " + path)
    return resolved


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image(path):
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return {"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," +
            base64.b64encode(path.read_bytes()).decode("ascii")}}


def read_request(relative):
    cfg = json.loads(local(relative).read_text())
    base = {"schema", "object_id", "object_kind", "object_image", "character_image",
            "generation_request", "motion_library", "output_path", "vision_model"}
    legacy = base | {"maximum_paid_requests", "automatic_paid_retries"}
    iterative = base | {"vision_strategy"}
    if (not ((cfg.get("schema") == 1 and set(cfg) == legacy) or
             (cfg.get("schema") == 2 and set(cfg) == iterative and
              cfg.get("vision_strategy") == "evidence_driven")) or
            not isinstance(cfg["object_id"], str) or not IDENT.fullmatch(cfg["object_id"]) or
            not isinstance(cfg["object_kind"], str) or not IDENT.fullmatch(cfg["object_kind"])):
        raise ValueError("Invalid interaction request schema")
    if cfg["vision_model"] != MODEL:
        raise ValueError("Unrecognized primary vision model; use an explicit review pass")
    obj = local(cfg["object_image"])
    char = local(cfg["character_image"])
    source = local(cfg["generation_request"])
    motion = local(cfg["motion_library"])
    output = local(cfg["output_path"], existing=False)
    if (obj.suffix.lower() not in (".png", ".jpg", ".jpeg") or
            char.suffix.lower() not in (".png", ".jpg", ".jpeg") or
            output.suffix != ".json"):
        raise ValueError("Unexpected interaction asset type")
    brief = json.loads(source.read_text())
    if (brief.get("output") != cfg["object_image"] or
            cfg["character_image"] not in brief.get("references", []) or
            not isinstance(brief.get("prompt"), str)):
        raise ValueError("Original object brief is not proven to match both images")
    catalog = json.loads(motion.read_text())
    clips = [c for c in catalog.get("clips", []) if c.get("included") is True]
    if catalog.get("schema") != 1 or not clips or any(
            not isinstance(c.get("role"), str) for c in clips):
        raise ValueError("No verified Mixamo source catalog")
    hashes = {key: digest(path) for key, path in {
        "object_image": obj, "character_image": char,
        "generation_brief": source, "mixamo_catalog": motion}.items()}
    return cfg, obj, char, brief, clips, output, hashes


def validate(answer, clips, expected_kind=None):
    if not isinstance(answer, dict) or set(answer) != set(SCHEMA["properties"]):
        raise ValueError("Incomplete semantic interaction contract")
    if (not isinstance(answer["uncertainties"], list) or
            any(not isinstance(u, str) for u in answer["uncertainties"]) or
            isinstance(answer["confidence"], bool) or
            not isinstance(answer["confidence"], (int, float)) or
            not math.isfinite(answer["confidence"]) or answer["confidence"] < .82 or
            answer["confidence"] > 1 or answer["uncertainties"]):
        raise ValueError("Uncertain interaction: needs human/vision review")
    if (not isinstance(answer["object_kind"], str) or
            not IDENT.fullmatch(answer["object_kind"]) or
            (expected_kind is not None and answer["object_kind"] != expected_kind)):
        raise ValueError("Vision object identity contradicts the source design")
    for key in ("object_function", "object_evidence", "explanation"):
        if not isinstance(answer[key], str) or len(answer[key].strip()) < 12:
            raise ValueError("Missing source-grounded " + key)
    def named(items, kind):
        if not isinstance(items, list) or not 1 <= len(items) <= 12:
            raise ValueError("Missing " + kind)
        found = {}
        for item in items:
            if not isinstance(item, dict) or set(item) != set(kind["props"]):
                raise ValueError("Invalid " + kind["name"] + " fields")
            if not isinstance(item["id"], str) or not IDENT.fullmatch(item["id"]) or item["id"] in found:
                raise ValueError("Duplicate or unsafe " + kind["name"] + " id")
            for k in kind["texts"]:
                if not isinstance(item[k], str) or len(item[k].strip()) < 8:
                    raise ValueError("Missing semantic evidence for " + item["id"])
            for k in kind["points"]:
                p = item[k]
                if not isinstance(p, list) or len(p) != 2 or any(
                        isinstance(v, bool) or not isinstance(v, (int, float)) or
                        not math.isfinite(v) or not 0 <= v <= 1 for v in p):
                    raise ValueError("Invalid vision coordinate: " + k)
            found[item["id"]] = item
        return found
    features = named(answer["features"], {"name": "feature",
        "props": FEATURE["properties"],
        "texts": ("function", "direction_semantics", "evidence"),
        "points": ("origin", "direction_tip")})
    grips = named(answer["grips"], {"name": "grip",
        "props": GRIP["properties"],
        "texts": ("surface", "evidence"), "points": ("point",)})
    for f in features.values():
        if math.dist(f["origin"], f["direction_tip"]) < .035:
            raise ValueError("Vision cannot show the direction for " + f["id"])
    modes = answer["modes"]
    if not isinstance(modes, list) or not 2 <= len(modes) <= 12:
        raise ValueError("Carry and use modalities required")
    roles = {c["role"] for c in clips if answer["object_kind"] in c.get("equipment", [])}
    phases = set()
    seen = set()
    for mode in modes:
        if not isinstance(mode, dict) or set(mode) != set(MODE["properties"]):
            raise ValueError("Incomplete modal interaction")
        if (not isinstance(mode["id"], str) or not IDENT.fullmatch(mode["id"]) or
                mode["id"] in seen or mode["phase"] not in ("carry", "use") or
                type(mode["hands"]) is not int or mode["hands"] not in (1, 2) or
                mode["primary_hand"] not in ("left", "right") or
                not all(isinstance(mode[k], str) for k in
                        ("primary_grip", "secondary_hand", "secondary_grip",
                         "functional_feature", "mixamo_role", "action_direction")) or
                mode["primary_grip"] not in grips):
            raise ValueError("Invalid hands or grip in mode")
        seen.add(mode["id"]); phases.add(mode["phase"])
        for key in ("action_intent", "evidence"):
            if not isinstance(mode[key], str) or len(mode[key].strip()) < 8:
                raise ValueError("Missing evidence for interaction mode")
        if mode["hands"] == 1:
            if mode["secondary_hand"] != "none" or mode["secondary_grip"]:
                raise ValueError("A one-hand mode cannot claim a second contact")
        elif (mode["secondary_hand"] not in ("left", "right") or
              mode["secondary_hand"] == mode["primary_hand"] or
              mode["secondary_grip"] not in grips or
              mode["secondary_grip"] == mode["primary_grip"]):
            raise ValueError("Two-hand mode requires distinct grips and hands")
        if mode["phase"] == "use":
            if (mode["mixamo_role"] not in roles or mode["functional_feature"] not in features or
                    mode["action_direction"] not in MODE["properties"]["action_direction"]["enum"] or
                    mode["action_direction"] == "none"):
                raise ValueError("Use mode lacks actual candidate Mixamo role or functional feature")
        elif (mode["action_direction"] != "none" or
              mode["mixamo_role"] not in ("none", "idle", "walk", "run")) or (
                mode["functional_feature"] and mode["functional_feature"] not in features):
            raise ValueError("Unsupported carry action semantics")
    if phases != {"carry", "use"}:
        raise ValueError("Both carry and action phases must be characterized")
    return answer


def validate_visible_landmarks(answer, object_image):
    """Reject image coordinates on transparent background, never guess a replacement.

    Transparency is direct pixel evidence, not a heuristic for assigning
    semantic roles. For opaque source photos this test is deliberately neutral.
    """
    from PIL import Image

    with Image.open(object_image) as source:
        if "A" not in source.getbands():
            return
        alpha = source.getchannel("A")
        if alpha.getextrema()[0] == 255:
            return
        width, height = alpha.size

        def visible(point):
            x, y = round(point[0] * (width - 1)), round(point[1] * (height - 1))
            # Allow only a narrow antialiasing/annotation tolerance (<0.6% of
            # the image), never snap a labelled role onto a distant silhouette.
            dx, dy = max(1, round(width * .005)), max(1, round(height * .005))
            region = alpha.crop((max(0, x-dx), max(0, y-dy),
                                 min(width, x+dx+1), min(height, y+dy+1)))
            return region.getextrema()[1] >= 96

        for grip in answer["grips"]:
            if not visible(grip["point"]):
                raise ValueError("Vision grip falls outside the source object: " + grip["id"])
        for feature in answer["features"]:
            for field in ("origin", "direction_tip"):
                if not visible(feature[field]):
                    raise ValueError("Vision functional feature falls outside the source object: " +
                                     feature["id"] + "." + field)


def reviewed_response(review_path, receipt, hashes, obj, clips, expected_kind):
    """Promote an explicit image-grounded review without altering paid evidence."""
    reviewed = json.loads(review_path.read_text())
    raw = receipt["raw_characterization"]
    observations = reviewed.get("source_observations")
    resolutions = reviewed.get("resolved_uncertainties")
    if (set(reviewed) != {"schema", "source_hashes", "paid_response_sha256",
                         "review_method", "source_observations", "resolved_uncertainties",
                         "characterization"} or
            reviewed["schema"] != 1 or reviewed["source_hashes"] != hashes or
            reviewed["paid_response_sha256"] != digest(review_path.with_name("interaction-response.json")) or
            reviewed["review_method"] != "independent_source_image_inspection" or
            not isinstance(observations, list) or len(observations) < 2 or
            {item.get("source") for item in observations if isinstance(item, dict)} !=
                {"object_image", "character_image"} or
            any(not isinstance(item, dict) or set(item) != {"source", "observation"} or
                not isinstance(item["observation"], str) or len(item["observation"].strip()) < 25
                for item in observations) or
            not isinstance(resolutions, list) or
            len(resolutions) != len(raw.get("uncertainties", [])) or
            [item.get("original") for item in resolutions if isinstance(item, dict)] !=
                raw.get("uncertainties", []) or
            any(not isinstance(item, dict) or set(item) != {"original", "resolution"} or
                not isinstance(item["resolution"], str) or len(item["resolution"].strip()) < 30
                for item in resolutions)):
        raise ValueError("Semantic review has no exact paid receipt and two-image evidence")
    answer = validate(reviewed["characterization"], clips, expected_kind)
    validate_visible_landmarks(answer, obj)
    return answer, {"path": str(review_path.relative_to(ROOT)),
                    "sha256": digest(review_path),
                    "paid_response_sha256": digest(review_path.with_name("interaction-response.json")),
                    "method": reviewed["review_method"]}


def run(relative, check=False):
    cfg, obj, char, brief, clips, output, hashes = read_request(relative)
    if output.is_file():
        record = json.loads(output.read_text())
        if record.get("source_hashes") != hashes or record.get("schema") != 1:
            raise ValueError("Interaction contract is stale; do not reuse")
        validate(record["characterization"], clips, cfg["object_kind"])
        validate_visible_landmarks(record["characterization"], obj)
        print("PASS: existing three-source semantic contract; no paid call")
        return
    if check:
        print("MISSING: semantic object × character × Mixamo contract")
        return
    receipt = output.with_name("interaction-response.json")
    if receipt.is_file():
        cached = json.loads(receipt.read_text())
        if cached.get("source_hashes") != hashes or "raw_characterization" not in cached:
            raise ValueError("Prior paid response unknown or source changed; no retry")
        answer = cached["raw_characterization"]
    else:
        token = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not token:
            raise ValueError("OPENROUTER_API_KEY absent; no paid request submitted")
        parts = [{"type": "text", "text": "DECLARED OBJECT KIND: " + cfg["object_kind"]},
                 {"type": "text", "text": "ORIGINAL DESIGN BRIEF: " + brief["prompt"]},
                 {"type": "text", "text": "TARGET ANATOMICAL CONTACT CHAINS (naming reference only; pose is unverified): " +
                  json.dumps(JOINT_ANCHORS)},
                 {"type": "text", "text": "Included Mixamo source clips (roles are candidates, not pose validation): " +
                  json.dumps(clips, ensure_ascii=False)},
                 {"type": "text", "text": "IMAGE 1: isolated original equipment"}, image(obj),
                 {"type": "text", "text": "IMAGE 2: intended character with equipment"}, image(char)]
        payload = {"model": MODEL, "temperature": 0, "max_tokens": 1800,
            "provider": {"require_parameters": True},
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "three_source_prop_interaction", "strict": True, "schema": SCHEMA}},
            "messages": [{"role": "system", "content": PROMPT},
                         {"role": "user", "content": parts}]}
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({"schema": 1, "source_hashes": hashes,
            "status": "submission-outcome-unknown", "automatic_paid_retries": 0}, indent=2) + "\n")
        req = Request(ENDPOINT, data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/leye0/WarConquer",
                     "X-Title": "WarConquer three-source equipment semantics"})
        with urlopen(req, timeout=150) as response:
            result = json.loads(response.read(200000))
        answer = json.loads((result.get("choices") or [{}])[0]["message"]["content"])
        receipt.write_text(json.dumps({"schema": 1, "source_hashes": hashes,
            "raw_characterization": answer, "paid_requests": 1,
            "automatic_paid_retries": 0}, ensure_ascii=False, indent=2) + "\n")
    review_path = output.with_name("interaction-review.json")
    review_provenance = None
    if review_path.is_file():
        if not receipt.is_file():
            raise ValueError("Review cannot replace a missing paid source response")
        answer, review_provenance = reviewed_response(
            review_path, json.loads(receipt.read_text()), hashes, obj, clips, cfg["object_kind"])
    else:
        validate(answer, clips, cfg["object_kind"])
        validate_visible_landmarks(answer, obj)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"schema": 1, "object_id": cfg["object_id"],
        "source_hashes": hashes, "vision_model": MODEL,
        "characterization": answer,
        "expected_joint_anchors": JOINT_ANCHORS,
        "semantic_status": "confirmed",
        "mixamo_pose_status": "pending_real_joint_validation",
        **({"review_provenance": review_provenance} if review_provenance else {})},
        ensure_ascii=False, indent=2) + "\n")
    print("PASS: semantically confirmed interaction; Mixamo joint contact still pending")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.request, args.check)
