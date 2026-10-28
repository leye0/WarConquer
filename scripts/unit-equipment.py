#!/usr/bin/env python3
"""Discover equipment from an original unit concept and prepare its build inputs.

This is a project-owned, unit-independent bridge between the unit manifest and
the existing Muse, TRELLIS, physical-size and grip tools. A paid vision result
is checkpointed before validation; it is never silently resubmitted.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MODEL = "google/gemini-2.5-flash-lite"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def safe(rel):
    if not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel:
        raise ValueError("Invalid repository-relative path")
    path = (ROOT / rel).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("Path outside repository")
    return path


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    temp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_manifest(unit):
    if not re.fullmatch(r"[a-z][a-z0-9_]*", unit):
        raise ValueError("Invalid unit ID")
    doc = json.loads(safe(f"data/units/{unit}.json").read_text(encoding="utf8"))
    if doc.get("id") != unit or doc.get("schema") != 1:
        raise ValueError("Unit manifest mismatch")
    return doc


def analysis_path(unit):
    return safe(f"data/units/{unit}/equipment-analysis.json")


def source_image(doc):
    path = safe(doc["source"]["character_image"])
    if not path.is_file() or path.suffix.lower() != ".png":
        raise ValueError("Missing original unit illustration")
    return path


def image_part(path):
    return {"type": "image_url", "image_url": {
        "url": "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")}}


def validate_items(items, hints):
    if not isinstance(items, list) or len(items) > 8:
        raise ValueError("Expected at most eight separate equipment items")
    if hints and len(items) != len(hints):
        raise ValueError("Vision omitted or added an expected equipment item")
    found = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"id", "kind", "description", "confidence"}:
            raise ValueError("Invalid equipment description")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", item["id"]) or item["id"] in found:
            raise ValueError("Unsafe or duplicate equipment ID")
        found.add(item["id"])
        if (not re.fullmatch(r"[a-z][a-z0-9_]*", item["kind"])
                or not isinstance(item["description"], str)
                or not 25 <= len(item["description"]) <= 1000
                or isinstance(item["confidence"], bool)
                or not isinstance(item["confidence"], (int, float))
                or not .65 <= item["confidence"] <= 1):
            raise ValueError("Uncertain or incomplete equipment identification")
    if hints and {i["id"] for i in hints} != found:
        raise ValueError("Equipment identity differs from original unit definition")
    for hint in hints:
        if hint.get("kind") and next(i for i in items if i["id"] == hint["id"])["kind"] != hint["kind"]:
            raise ValueError("Vision found equipment of a different type than the manifest")
    return items


def describe(unit, paid=False):
    doc = raw_manifest(unit)
    concept = source_image(doc)
    hints = doc.get("equipment") or []
    target = analysis_path(unit)
    provenance = {"unit": unit, "source_sha256": sha(concept), "model": MODEL}
    if target.is_file():
        result = json.loads(target.read_text(encoding="utf8"))
        if any(result.get(k) != v for k, v in provenance.items()):
            raise ValueError("Concept changed; existing equipment analysis must be reviewed")
        return validate_items(result["items"], hints)
    # Existing designed objects already have their own creation prompts: do not
    # spend a vision call merely to rediscover those exact descriptions.
    prior = []
    if hints:
        for hint in hints:
            request = hint.get("source_request")
            path = safe(request) if request else None
            if not path or not path.is_file():
                break
            brief = json.loads(path.read_text(encoding="utf8"))
            if (brief.get("output") != hint.get("source_image")
                    or doc["source"]["character_image"] not in brief.get("references", [])
                    or not isinstance(brief.get("prompt"), str)):
                break
            prior.append({"id": hint["id"], "kind": hint["kind"],
                          "description": brief["prompt"], "confidence": 1.0})
    if hints and len(prior) == len(hints):
        items = validate_items(prior, hints)
        save(target, {"schema": 1, **provenance, "items": items, "source": "original_generation_brief"})
        return items
    checkpoint = target.with_name("equipment-analysis-response.json")
    if checkpoint.is_file():
        response = json.loads(checkpoint.read_text(encoding="utf8"))
        if any(response.get(k) != v for k, v in provenance.items()):
            raise ValueError("Paid vision response belongs to a different concept")
        if "items" not in response:
            raise ValueError("Previous vision submission outcome unknown; no automatic paid retry")
        items = response["items"]
    else:
        if not paid:
            raise ValueError("Equipment analysis requires --allow-paid (no request submitted)")
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise ValueError("OPENROUTER_API_KEY missing; no request submitted")
        props = {"id": {"type": "string"}, "kind": {"type": "string"},
                 "description": {"type": "string"}, "confidence": {"type": "number"}}
        schema = {"type": "object", "properties": {"items": {"type": "array", "items": {
            "type": "object", "properties": props, "required": list(props),
            "additionalProperties": False}}}, "required": ["items"], "additionalProperties": False}
        wanted = [{"id": h["id"], "kind": h.get("kind")} for h in hints]
        message = (
            "Identify separate removable equipment visible in this ORIGINAL game character concept. "
            "Exclude clothing, limbs and permanent armor, but include visible weapons, shields, tools "
            "or other held equipment. Describe each object's precise silhouette, materials, colors, "
            "handle, functional ends and visible proportions; this description will drive a new isolated "
            "Muse image of the SAME object. No invented details. IDs and kinds must be simple lowercase "
            "snake_case. If expected IDs are supplied, return exactly one item per ID, using the "
            "supplied kind. If no equipment is visible and no IDs are expected, return an empty array. "
            "Return low confidence if ambiguous; never invent certainty. Expected IDs/kinds: "
            + json.dumps(wanted))
        payload = {"model": MODEL, "temperature": 0, "max_tokens": 1250,
                   "response_format": {"type": "json_schema", "json_schema": {
                       "name": "unit_equipment_discovery", "strict": True, "schema": schema}},
                   "messages": [{"role": "system", "content": message},
                                {"role": "user", "content": [image_part(concept)]}]}
        req = Request(ENDPOINT, data=json.dumps(payload).encode(), method="POST",
                      headers={"Authorization": "Bearer " + key,
                               "Content-Type": "application/json"})
        save(checkpoint, {"schema": 1, **provenance,
                          "status": "submission-outcome-unknown", "automatic_paid_retries": 0})
        with urlopen(req, timeout=150) as response:
            result = json.load(response)
        content = (result.get("choices") or [{}])[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError("Paid response returned no JSON; do not retry automatically")
        items = json.loads(content)["items"]
        save(checkpoint, {"schema": 1, **provenance, "items": items, "paid_calls": 1})
    items = validate_items(items, hints)
    save(target, {"schema": 1, **provenance, "items": items, "source": "vision"})
    return items


def descriptors(unit):
    target = analysis_path(unit)
    if not target.is_file():
        return []
    doc = raw_manifest(unit)
    result = json.loads(target.read_text(encoding="utf8"))
    if result.get("source_sha256") != sha(source_image(doc)):
        raise ValueError("Equipment analysis is stale")
    return validate_items(result["items"], doc.get("equipment") or [])


def prepare_requests(doc, prop):
    """Materialize reproducible requests from a vision description, never overwrite edits."""
    description = prop.get("description")
    if not description:
        # Historical units may already have an original, hand-reviewed
        # generation brief instead of an equipment-analysis receipt. Reuse
        # that SOURCE evidence; do not hallucinate a description or charge a
        # new identification call merely to backfill metadata.
        original = safe(prop["source_request"])
        if original.is_file():
            old = json.loads(original.read_text(encoding="utf8"))
            if (old.get("output") == prop["source_image"] and
                    doc["source"]["character_image"] in old.get("references", []) and
                    isinstance(old.get("prompt"), str) and old["prompt"].strip()):
                description = old["prompt"]
        if not description:
            raise ValueError("No source-grounded equipment description for " + prop["id"])
    image = doc["source"]["character_image"]
    source_req = {"prompt": "Reconstruct exactly ONE separate removable equipment object from "
                  "the supplied original character image. Preserve the original object's design, "
                  "colors, materials, proportions, distinctive details and construction. "
                  "Draw only the object, unobstructed in a three-quarter view, with its gripping "
                  "area and functional ends clearly visible. No human, hands, duplicate items, "
                  "surroundings, shadow or text. Original design description: " + description,
                  "output": prop["source_image"], "references": [image],
                  "reference_role": "identity"}
    # Existing original generation briefs remain authoritative and are reused.
    records = [(prop["source_request"], source_req),
       (prop["interaction_request"], {"schema": 1,
          "object_id": prop["id"], "object_kind": prop["kind"],
          "object_image": prop["source_image"],
          "character_image": image,
          "generation_request": prop["source_request"],
          "motion_library": doc.get("body", {}).get("animations", "data/motion-library.json"),
          "output_path": prop["interaction"], "vision_model": MODEL,
          "maximum_paid_requests": 1, "automatic_paid_retries": 0}),
       (prop["trellis_request"], {"schema": 1, "source_image": prop["source_image"],
          "output_path": prop["glb"], "replicate_model": "firtoz/trellis",
          "maximum_paid_predictions": 1, "automatic_paid_retries": 0}),
       (prop["physical_size_request"], {"schema": 1, "object_image": prop["source_image"],
          "character_image": image, "generation_request": prop["source_request"],
          "output_path": prop["physical_size"], "vision_model": MODEL,
          "maximum_paid_requests": 1, "automatic_paid_retries": 0}),
       (prop["grip_request"], {"schema": 2,
          "experiment": doc["id"] + "-" + prop["id"] + "-grip",
          "object_image": prop["source_image"], "character_image": image,
          "object_glb": prop["glb"], "interaction_contract": prop["interaction"],
          "output_path": prop["grip"],
          "vision_model": MODEL, "maximum_paid_requests": 1,
          "automatic_paid_retries": 0})]
    for rel, record in records:
        path = safe(rel)
        if path.exists():
            # Legacy requests may contain model-version pins and human approvals.
            # Never replace them automatically or discard original provenance.
            continue
        save(path, record)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", required=True)
    parser.add_argument("--allow-paid", action="store_true")
    args = parser.parse_args()
    print(json.dumps(describe(args.unit, args.allow_paid), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
