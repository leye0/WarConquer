#!/usr/bin/env python3
"""Vision grip v3: provenance-aware, image-grounded prop scale and orientation.

A prop is not unknown when we generated it. Read its original generation
brief, verify it produced this image, and pass that brief to the vision model.
The model measures relative scale against the *character image*, not merely
asserting a generic axe size. Old grip-plan.json remains immutable.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DEFAULT="assets/experiments/props/marches_hache/trellis-v1/grip-request-v3.json"
ENDPOINT="https://openrouter.ai/api/v1/chat/completions"

def legacy():
    spec=importlib.util.spec_from_file_location("legacy_grip",ROOT/"scripts/plan-prop-attachment.py")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

OLD=legacy()
EXTENDED={
    "character_image_size_ratio":{"type":"number"},
    "character_image_shows_full_object":{"type":"boolean"},
    "size_reasoning":{"type":"string"}
}
JSON_SCHEMA={"type":"object","properties":{**OLD.PROPS,**EXTENDED},
             "required":[*OLD.PROPS,*EXTENDED],"additionalProperties":False}
PROMPT=(
    "You are the 3D equipment attachment analyst for WarConquer. "
    "The ORIGINAL GENERATION BRIEF, below, is provenance: the item is already "
    "identified, it was deliberately generated from this description. Treat "
    "its category, function, material, grip geometry and intent as established "
    "design constraints, not as a question to rediscover. Confirm these "
    "attributes against IMAGE 1 (isolated original prop) and IMAGE 2 (unit "
    "concept featuring that prop). If the images contradict the brief, do "
    "not improvise. Return accurate landmarks, hand choice, working-edge "
    "orientation and relative size grounded in *how the object appears on "
    "the unit*, never its size within IMAGE 1 (isolated images have no scale). "
    "If IMAGE 2 actually shows the full item, report its measured length as "
    "character_image_size_ratio = object length / person height, comparing "
    "the silhouette lengths without including empty transparent margins. "
    "Otherwise set character_image_shows_full_object=false and report a "
    "conservative semantic estimate with lower confidence for human review. "
    "Set length_relative_character_height consistent with that evidence; "
    "do NOT scale a practical weapon to fantasy proportions simply because "
    "the prompt uses words like LONG or TWO-HANDED. Explain the scale with "
    "observable facts in size_reasoning. The renderer, not you, calculates "
    "the GLB mesh axes. Return the strict JSON schema, no markdown."
)

def local(rel):
    if not isinstance(rel,str) or not rel or rel.startswith("/"):
        raise ValueError("Unsafe file path")
    p=(ROOT/rel).resolve()
    if not p.is_relative_to(ROOT) or not p.is_file():
        raise ValueError("Missing repository file: "+str(rel))
    return p

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(cfgfile):
    config=json.loads(local(cfgfile).read_text())
    required={"schema","experiment","object_image","character_image",
              "object_glb","object_generation_request","output_path",
              "vision_model","maximum_paid_requests","automatic_paid_retries"}
    if set(config)!=required or config["schema"]!=3:
        raise ValueError("Unexpected v3 request fields")
    if config["maximum_paid_requests"]!=1 or config["automatic_paid_retries"]!=0:
        raise ValueError("No repeat paid requests allowed")
    if config["vision_model"]!="google/gemini-2.5-flash-lite":
        raise ValueError("Unexpected vision model")
    obj=local(config["object_image"])
    char=local(config["character_image"])
    glb=local(config["object_glb"])
    source=local(config["object_generation_request"])
    out=(ROOT/config["output_path"]).resolve()
    if not out.is_relative_to(ROOT) or not out.name.endswith(".json") or out==source:
        raise ValueError("Invalid output")
    if obj.suffix.lower() not in (".png",".jpg",".jpeg") or char.suffix.lower() not in (".png",".jpg",".jpeg") or glb.suffix.lower()!=".glb":
        raise ValueError("Invalid source types")
    provenance=json.loads(source.read_text())
    if provenance.get("output")!=config["object_image"] or not provenance.get("prompt"):
        raise ValueError("Generation description cannot be traced to this prop image")
    if config["character_image"] not in provenance.get("references",[]):
        raise ValueError("Character concept was not used as design reference")
    # Preserve identities on any paid response; changes require a new version.
    hashes={
       "object_image_sha256":digest(obj),
       "character_image_sha256":digest(char),
       "prop_glb_sha256":digest(glb),
       "generation_brief_sha256":digest(source)
    }
    return config,obj,char,out,source,provenance["prompt"],hashes

def image(path):
    media="image/png" if path.suffix.lower()==".png" else "image/jpeg"
    return {"type":"image_url","image_url":{"url":
        "data:"+media+";base64,"+base64.b64encode(path.read_bytes()).decode()}}

def validate(raw):
    if not isinstance(raw,dict) or set(raw)!=set(JSON_SCHEMA["properties"]):
        raise ValueError("Incomplete semantic and scale analysis")
    base={k:raw[k] for k in OLD.PROPS}
    derived=OLD.validate(base)
    kind=base["object_kind"]
    full=raw["character_image_shows_full_object"]
    observed=raw["character_image_size_ratio"]
    desired=base["length_relative_character_height"]
    if not isinstance(full,bool):
        raise ValueError("Full silhouette evidence must be boolean")
    if isinstance(observed,bool) or not isinstance(observed,(int,float)) or not math.isfinite(observed) or not .08<=observed<=1.8:
        raise ValueError("Unreliable character image length ratio")
    reason=raw["size_reasoning"]
    if not isinstance(reason,str) or not 24<=len(reason)<=850:
        raise ValueError("Missing evidence-backed scale reasoning")
    if not full:
        raise ValueError("Cannot auto-promote size without full weapon and wearer in reference image")
    if abs(observed-desired)>.15 or abs(observed-desired)/observed>.20:
        raise ValueError("Estimated prop scale contradicts the character source image")
    return base,derived,{"character_image_size_ratio":round(observed,5),
                        "character_image_shows_full_object":full,
                        "reasoning":reason}

def save(path,doc):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n")
    tmp.replace(path)

def run(request,check):
    cfg,obj,char,out,source,brief,hashes=load(request)
    checkpoint=out.with_name(out.stem+"-response.json")
    if out.is_file():
        existing=json.loads(out.read_text())
        if (existing.get("input_hashes")!=hashes or
            existing.get("vision_model")!=cfg["vision_model"] or
            existing.get("source_provenance",{}).get("generation_request")!=cfg["object_generation_request"]):
            raise ValueError("v3 plan is stale; create a NEW version, never overwrite a paid result")
        validate({**existing["specifications"],
                  "character_image_size_ratio":existing["scale_observation"]["character_image_size_ratio"],
                  "character_image_shows_full_object":existing["scale_observation"]["character_image_shows_full_object"],
                  "size_reasoning":existing["scale_observation"]["reasoning"]})
        print("Verified pinned v3 plan and generation description, zero additional calls")
        return
    if check and not checkpoint.is_file():
        print("No v3 vision analysis yet, no network call")
        return
    if checkpoint.is_file():
        response=json.loads(checkpoint.read_text())
        if response.get("input_hashes")!=hashes or response.get("vision_model")!=cfg["vision_model"]:
            raise ValueError("Paid response checkpoint has mismatched source hashes")
        raw=response["raw_specifications"]
        print("Reusing paid v3 response with no new cost")
    else:
        if check:
            print("No accepted plan, but checkpoint exists")
            return
        token=os.environ.get("OPENROUTER_API_KEY","").strip()
        if not token: raise ValueError("Missing OPENROUTER_API_KEY")
        user=[
          {"type":"text","text":"ORIGINAL ITEM GENERATION BRIEF (authoritative intention):\n"+brief},
          {"type":"text","text":"IMAGE 1: isolated equipment actually generated from that brief."},
          image(obj),
          {"type":"text","text":"IMAGE 2: original character concept with equipment. Compare their real silhouette proportions."},
          image(char)
        ]
        payload={"model":cfg["vision_model"],"temperature":0,"max_tokens":1200,
          "provider":{"require_parameters":True},
          "response_format":{"type":"json_schema","json_schema":{
            "name":"prop_attachment_from_original_brief","strict":True,"schema":JSON_SCHEMA}},
          "messages":[{"role":"system","content":PROMPT+"\n"+OLD.PROMPT},
                      {"role":"user","content":user}]}
        req=Request(ENDPOINT,data=json.dumps(payload).encode(),method="POST",
           headers={"Authorization":"Bearer "+token,
                    "Content-Type":"application/json",
                    "HTTP-Referer":"https://github.com/leye0/WarConquer",
                    "X-Title":"WarConquer provenance-aware prop grip v3"})
        with urlopen(req,timeout=150) as r:
            answer=json.loads(r.read(200000))
        message=(answer.get("choices") or [{}])[0].get("message",{}).get("content")
        if not isinstance(message,str):
            raise ValueError("Provider did not return structured JSON text")
        raw=json.loads(message)
        # Cache paid response before semantic validation so retries cost $0.
        save(checkpoint,{"schema":3,"experiment":cfg["experiment"],
            "vision_model":cfg["vision_model"],"input_hashes":hashes,
            "raw_specifications":raw,"paid_vision_requests":1})
    spec,derived,scale=validate(raw)
    save(out,{"schema":3,"experiment":cfg["experiment"],
        "vision_model":cfg["vision_model"],
        "inputs":{k:cfg[k] for k in ("object_image","character_image","object_glb")},
        "source_provenance":{
          "generation_request":cfg["object_generation_request"],
          "generation_brief_sha256":hashes["generation_brief_sha256"]},
        "input_hashes":hashes,"specifications":spec,
        "derived_image_geometry":derived,
        "scale_observation":scale,
        "paid_vision_requests":1,"automatic_paid_retries":0})
    print("Accepted description-grounded object length/character height:",
          spec["length_relative_character_height"],"observed:",scale["character_image_size_ratio"])

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--request",default=DEFAULT)
    a.add_argument("--check",action="store_true")
    z=a.parse_args()
    run(z.request,z.check)
