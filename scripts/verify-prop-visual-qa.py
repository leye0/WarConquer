#!/usr/bin/env python3
"""Final visual GO/NO-GO of a held prop, judged on REAL Babylon screenshots.

Generically usable for any object, body and animation. Coordinates are fitted
by code; cheap vision judges the resulting visual hold. One raw response is
cached per plan/rig-code signature so retrying CI never repeats a paid call.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODEL = "google/gemini-2.5-flash-lite"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
SCHEMA = {"type":"object","additionalProperties":False,"properties":{
    "go":{"type":"boolean"},"confidence":{"type":"number"},
    "issues":{"type":"array","items":{"type":"string"}},
    "explanation":{"type":"string"}
},"required":["go","confidence","issues","explanation"]}
PROMPT = (
    "You are the final visual QA judge of a generic 3D game prop attachment. "
    "IMAGE 1 is the ORIGINAL isolated prop concept. The remaining images are "
    "REAL browser screenshots of the same 3D object held by an animated "
    "humanoid in a NEUTRAL IDLE stance, viewed from front, side and back. "
    "Give GO only if the character truly GRIPS the object at its handle/holding "
    "region, not at the sharp head; the functional/cutting face points the "
    "physically expected direction for that type of object; the scale is "
    "plausible; and the object is neither floating nor piercing the hand. "
    "A wrong-facing cutting edge in the IDLE stance is an automatic NO-GO, "
    "even if the head points downward correctly. Focus on the actual 3D "
    "holding pose, not UI, terrain, or a transient backswing in an animation. "
    "Do not require bow-string simulation or optional secondary-hand IK. "
    "If unsure, return NO-GO with actionable reasons. For a GO, issues MUST "
    "be an empty list. Return JSON only."
)


def image_part(path: Path):
    image = Image.open(path).convert("RGB")
    image.thumbnail((1060, 860))
    stream=io.BytesIO();image.save(stream,format="JPEG",quality=82)
    return {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+
        base64.b64encode(stream.getvalue()).decode("ascii")}}


def signature(plan):
    dependencies=("scripts/character-lab-client.js",
                  "scripts/weapon-grip-geometry.js",
                  "scripts/rig-contact-landmarks.js")
    input_data={"qa_prompt_sha256":hashlib.sha256(PROMPT.encode()).hexdigest(),
                "points":plan["mesh_landmarks"]["points"],
                "specifications":plan["specifications"],
                "glb":plan["input_hashes"]["prop_glb_sha256"],
                "solver":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                          for p in dependencies}}
    return hashlib.sha256(json.dumps(input_data,sort_keys=True).encode()).hexdigest()


def check_response(answer):
    if not isinstance(answer,dict) or set(answer)!=set(SCHEMA["properties"]):
        raise ValueError("Invalid JSON visual verdict")
    if not isinstance(answer["go"],bool) or not isinstance(answer["confidence"],(int,float)):
        raise ValueError("Invalid visual verdict types")
    if not 0<=answer["confidence"]<=1 or not isinstance(answer["issues"],list) or any(
            not isinstance(x,str) for x in answer["issues"]):
        raise ValueError("Invalid visual QA confidence or issues")
    if not isinstance(answer["explanation"],str) or not answer["explanation"]:
        raise ValueError("Missing visual decision rationale")
    return answer["go"] and answer["confidence"]>=.75 and not answer["issues"]


def review(plan_path: Path, shots_dir: Path):
    if not plan_path.is_file() or not plan_path.resolve().is_relative_to(ROOT):
        raise ValueError("Expected canonical repository grip plan")
    plan=json.loads(plan_path.read_text())
    if plan.get("mesh_landmarks",{}).get("glb_sha256")!=plan["input_hashes"]["prop_glb_sha256"]:
        raise ValueError("GLB functional landmarks not ready")
    fingerprint=signature(plan)
    existing=plan.get("visual_qa",{})
    if existing.get("signature")==fingerprint:
        print("VISUAL_GO_CACHED" if existing.get("status")=="approved" else "VISUAL_NO_GO_CACHED")
        return existing.get("status")=="approved"
    # Action clips have dynamic backswing phases; one arbitrary captured frame
    # cannot certify a NEUTRAL attachment orientation. Real Mixamo action
    # compatibility is tested separately in the browser smoke suite.
    shots=[shots_dir/(label+".png") for label in ("front","side","back")]
    shots=[p for p in shots if p.is_file()]
    if len(shots)<3:raise ValueError("Need three real browser view screenshots")
    receipt=plan_path.with_name("grip-visual-qa-response.json")
    answer=None
    if receipt.exists():
        recorded=json.loads(receipt.read_text())
        if recorded.get("signature")==fingerprint:
            answer=recorded["raw_review"]
            print("Reusing the existing paid vision GO response")
    if answer is None:
        key=os.environ.get("OPENROUTER_API_KEY","").strip()
        if not key:raise RuntimeError("Missing OPENROUTER_API_KEY")
        parts=[{"type":"text","text":"IMAGE 1: isolated original prop design"},
               image_part(ROOT/plan["inputs"]["object_image"])]
        for path in shots:
            parts.extend([{"type":"text","text":"Actual Babylon screenshot: "+path.stem},
                          image_part(path)])
        payload={"model":MODEL,"temperature":0,"max_tokens":460,
            "provider":{"require_parameters":True},
            "response_format":{"type":"json_schema","json_schema":{
                "name":"real_3d_prop_attachment_go","strict":True,"schema":SCHEMA}},
            "messages":[{"role":"system","content":PROMPT},
                        {"role":"user","content":parts}]}
        req=Request(ENDPOINT,data=json.dumps(payload).encode(),method="POST",
            headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
                     "HTTP-Referer":"https://github.com/leye0/WarConquer",
                     "X-Title":"WarConquer generic equipment visual QA"})
        with urlopen(req,timeout=150) as response:
            result=json.loads(response.read(160000))
        answer=json.loads((result.get("choices") or [{}])[0]["message"]["content"])
        receipt.write_text(json.dumps({"schema":1,"signature":fingerprint,
            "vision_model":MODEL,"raw_review":answer},ensure_ascii=False,indent=2)+"\n")
        print("Saved one paid vision response before deciding GO/NO-GO")
    go=check_response(answer)
    plan["visual_qa"]={"status":"approved" if go else "rejected",
        "signature":fingerprint,"confidence":answer["confidence"],
        "issues":answer["issues"],"reason":answer["explanation"],
        "vision_model":MODEL,"checked_views":[p.stem for p in shots]}
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n")
    print("VISUAL_GO" if go else "VISUAL_NO_GO",answer["explanation"])
    return go


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",required=True)
    parser.add_argument("--screenshots",required=True)
    args=parser.parse_args()
    raise SystemExit(0 if review((ROOT/args.plan).resolve(),
        Path(args.screenshots).resolve()) else 1)
