#!/usr/bin/env python3
"""Repeatable, phase-aware vision QA of actual Babylon pose screenshots.

Each named review pass is a separate, cached OpenRouter inference; a new pass
can examine the same source from another perspective without any arbitrary
one-call ceiling. Identical passes never pay twice.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODEL = "google/gemini-2.5-flash-lite"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
FRAME_SCHEMA = {"type":"object","additionalProperties":False,"properties":{
    "id":{"type":"string"},"hands_contact":{"type":"boolean"},
    "action_feature_correct":{"type":"boolean"},
    "orientation_constraints_met":{"type":"boolean"},
    "collision_free":{"type":"boolean"},"confidence":{"type":"number"},
    "issues":{"type":"array","items":{"type":"string"}}
},"required":["id","hands_contact","action_feature_correct",
    "orientation_constraints_met","collision_free","confidence","issues"]}
SCHEMA = {"type":"object","additionalProperties":False,"properties":{
    "go":{"type":"boolean"},"confidence":{"type":"number"},
    "issues":{"type":"array","items":{"type":"string"}},
    "explanation":{"type":"string"},
    "frames":{"type":"array","items":FRAME_SCHEMA}
},"required":["go","confidence","issues","explanation","frames"]}
PROMPT = (
    "You are an independent visual judge of a 3D object held by a character. "
    "IMAGE 1 is the source object; remaining labeled images are REAL Babylon "
    "renders at named poses. The supplied object/character/Mixamo interaction "
    "contract supplies EXACT expected hands, named grips, active features, "
    "directions and state-dependent physical constraints for each phase. "
    "Follow those phase-specific facts. NEVER impose a generic assumption "
    "such as 'the heavy end must hang below the hand': a pot carried full "
    "must keep its opening upright; a firearm must aim its muzzle at its target; "
    "a chopping axe must orient its sharp edge in the intended action. "
    "Two-hand modes REQUIRE two visible contacts, including the secondary "
    "hand; no equipment class gets an automatic exemption. Other body contacts "
    "(strap, forearm, shoulder) are valid only when the contract declares them. "
    "Check each named pose separately: hand(s) on the correct regions, "
    "functional part facing the correct way, declared orientation constraints, "
    "and collisions. Never claim to see a hidden contact; when the screenshot "
    "cannot resolve it, say NO-GO and request an additional camera view. "
    "Do not infer real physical state (liquid, loaded, sealed) from image alone; "
    "use only the supplied game state. Do not judge UI, terrain or visual style. "
    "Return one frame verdict for EVERY labeled screenshot and an aggregate GO "
    "only if all required criteria hold with sufficient evidence."
)


def image_part(path: Path):
    image = Image.open(path).convert("RGB")
    image.thumbnail((1060, 860))
    stream=io.BytesIO();image.save(stream,format="JPEG",quality=82)
    return {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+
        base64.b64encode(stream.getvalue()).decode("ascii")}}


def interaction(plan):
    provenance=plan.get("interaction_provenance")
    if not isinstance(provenance,dict):
        raise ValueError("Vision QA requires a source-confirmed object/actor/Mixamo contract")
    rel=provenance.get("path", "")
    if not isinstance(rel,str) or not rel or rel.startswith("/") or "\\" in rel:
        raise ValueError("Invalid interaction contract path")
    path=(ROOT/rel).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError("Missing authoritative interaction contract")
    if hashlib.sha256(path.read_bytes()).hexdigest()!=provenance.get("sha256"):
        raise ValueError("Interaction contract has changed since GLB fitting")
    answer=json.loads(path.read_text())
    if answer.get("semantic_status")!="confirmed":
        raise ValueError("Unconfirmed object semantics cannot pass visual QA")
    return answer


def signature(plan, contract, shots, model, pass_id):
    dependencies=("scripts/character-lab-client.js",
                  "scripts/capture-prop-contact.mjs",
                  "scripts/prop-motion-contact.js",
                  "scripts/weapon-grip-geometry.js",
                  "scripts/rig-contact-landmarks.js")
    input_data={"qa_prompt_sha256":hashlib.sha256(PROMPT.encode()).hexdigest(),
                "model":model,"pass_id":pass_id,
                "interaction":contract,
                "plan":plan.get("mesh_landmarks"),
                "specifications":plan.get("specifications"),
                "glb":plan["input_hashes"]["prop_glb_sha256"],
                "screenshots":{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in shots},
                "solver":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                          for p in dependencies}}
    return hashlib.sha256(json.dumps(input_data,sort_keys=True).encode()).hexdigest()


def check_response(answer, names):
    if not isinstance(answer,dict) or set(answer)!=set(SCHEMA["properties"]):
        raise ValueError("Invalid JSON visual verdict")
    if not isinstance(answer["go"],bool) or not isinstance(answer["confidence"],(int,float)):
        raise ValueError("Invalid visual verdict types")
    if not 0<=answer["confidence"]<=1 or not isinstance(answer["issues"],list) or any(
            not isinstance(x,str) for x in answer["issues"]):
        raise ValueError("Invalid visual QA confidence or issues")
    if not isinstance(answer["explanation"],str) or not answer["explanation"]:
        raise ValueError("Missing visual decision rationale")
    frames=answer["frames"]
    if not isinstance(frames,list) or len(frames)!=len(names) or (
            {f.get("id") for f in frames if isinstance(f,dict)}!=set(names)):
        raise ValueError("Vision reviewer omitted/duplicated actual pose screenshots")
    all_pass=True
    for frame in frames:
        if not isinstance(frame,dict) or set(frame)!=set(FRAME_SCHEMA["properties"]):
            raise ValueError("Incomplete per-frame contact verdict")
        if not all(type(frame[k]) is bool for k in
                   ("hands_contact","action_feature_correct",
                    "orientation_constraints_met","collision_free")):
            raise ValueError("Missing visual contact/orientation judgment")
        if (type(frame["confidence"]) not in (int,float) or
                not 0<=frame["confidence"]<=1 or
                not isinstance(frame["issues"],list) or
                any(not isinstance(x,str) for x in frame["issues"])):
            raise ValueError("Invalid per-frame vision confidence/issues")
        all_pass=all_pass and all(frame[k] for k in
            ("hands_contact","action_feature_correct",
             "orientation_constraints_met","collision_free")) and (
                frame["confidence"]>=.75 and not frame["issues"])
    return answer["go"] and answer["confidence"]>=.75 and not answer["issues"] and all_pass


def review(plan_path: Path, shots_dir: Path, pass_id="primary", model=MODEL):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,48}",pass_id):
        raise ValueError("Review pass must have a stable safe identifier")
    if not isinstance(model,str) or not re.fullmatch(r"[a-zA-Z0-9_./:-]{3,120}",model):
        raise ValueError("Invalid reviewed OpenRouter model ID")
    if not plan_path.is_file() or not plan_path.resolve().is_relative_to(ROOT):
        raise ValueError("Expected canonical repository grip plan")
    plan=json.loads(plan_path.read_text())
    if plan.get("mesh_landmarks",{}).get("glb_sha256")!=plan["input_hashes"]["prop_glb_sha256"]:
        raise ValueError("GLB functional landmarks not ready")
    contract=interaction(plan)
    shots=[shots_dir/(label+".png") for label in
           ("front","side","back","walk","run","action","action_mid")]
    shots.extend(sorted(shots_dir.glob("action_mid_*.png")))
    shots=[p for p in shots if p.is_file()]
    if len(shots)<3:raise ValueError("Need three real browser view screenshots")
    fingerprint=signature(plan,contract,shots,model,pass_id)
    existing=plan.get("visual_qa",{})
    if existing.get("signature")==fingerprint:
        print("VISUAL_GO_CACHED" if existing.get("status")=="approved" else "VISUAL_NO_GO_CACHED")
        return existing.get("status")=="approved"
    receipt_dir=plan_path.parent/"vision-qa-receipts"
    receipt=receipt_dir/("qa-"+fingerprint+".json")
    answer=None
    if receipt.exists():
        recorded=json.loads(receipt.read_text())
        if recorded.get("signature")==fingerprint and "raw_review" in recorded:
            answer=recorded["raw_review"]
            print("Reusing source-matched paid vision GO response for",pass_id)
        else:
            raise ValueError("Pending/invalid paid response; no blind resubmission")
    if answer is None:
        key=os.environ.get("OPENROUTER_API_KEY","").strip()
        if not key:raise RuntimeError("Missing OPENROUTER_API_KEY")
        parts=[{"type":"text","text":"IMAGE 1: isolated original prop design"},
               image_part(ROOT/plan["inputs"]["object_image"])]
        parts.append({"type":"text","text":"AUTHORITATIVE OBJECT + CHARACTER + MIXAMO "
            "SEMANTICS; phases, hands, named grips and active features: "+
            json.dumps(contract["characterization"],ensure_ascii=False)})
        if contract.get("object_state") or contract.get("constraints"):
            parts.append({"type":"text","text":"GAME-DECLARED STATE/CONSTRAINTS: "+
                json.dumps({k:contract[k] for k in ("object_state","constraints")
                            if k in contract},ensure_ascii=False)})
        for path in shots:
            mode="use" if path.stem.startswith("action") else "carry"
            matching=[m for m in contract["characterization"]["modes"] if m["phase"]==mode]
            if not matching:
                raise ValueError("No authoritative "+mode+" mode for screenshot "+path.stem)
            parts.append({"type":"text","text":"FRAME "+path.stem+" expected "+mode+
                " contacts/actions: "+json.dumps(matching,ensure_ascii=False)})
        for path in shots:
            parts.extend([{"type":"text","text":"Actual Babylon screenshot: "+path.stem},
                          image_part(path)])
        payload={"model":model,"temperature":0,"max_tokens":2500,
            "provider":{"require_parameters":True},
            "response_format":{"type":"json_schema","json_schema":{
                "name":"real_3d_prop_attachment_go","strict":True,"schema":SCHEMA}},
            "messages":[{"role":"system","content":PROMPT},
                        {"role":"user","content":parts}]}
        receipt_dir.mkdir(parents=True,exist_ok=True)
        receipt.write_text(json.dumps({"schema":2,"signature":fingerprint,
            "status":"submission-outcome-unknown","pass_id":pass_id,"model":model},
            ensure_ascii=False,indent=2)+"\n")
        req=Request(ENDPOINT,data=json.dumps(payload).encode(),method="POST",
            headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
                     "HTTP-Referer":"https://github.com/leye0/WarConquer",
                     "X-Title":"WarConquer generic equipment visual QA"})
        with urlopen(req,timeout=150) as response:
            result=json.loads(response.read(160000))
        answer=json.loads((result.get("choices") or [{}])[0]["message"]["content"])
        receipt.write_text(json.dumps({"schema":2,"signature":fingerprint,
            "pass_id":pass_id,"vision_model":model,"raw_review":answer},
            ensure_ascii=False,indent=2)+"\n")
        print("Saved independent paid vision response",pass_id)
    go=check_response(answer,[p.stem for p in shots])
    plan["visual_qa"]={"status":"approved" if go else "rejected",
        "signature":fingerprint,"confidence":answer["confidence"],
        "issues":answer["issues"],"reason":answer["explanation"],
        "vision_model":model,"pass_id":pass_id,
        "per_frame":answer["frames"],"checked_views":[p.stem for p in shots]}
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n")
    print("VISUAL_GO" if go else "VISUAL_NO_GO",answer["explanation"])
    return go


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",required=True)
    parser.add_argument("--screenshots",required=True)
    parser.add_argument("--pass-id",default="primary",
        help="Distinct independent vision review ID; no arbitrary paid-call ceiling")
    parser.add_argument("--model",default=MODEL)
    args=parser.parse_args()
    raise SystemExit(0 if review((ROOT/args.plan).resolve(),
        Path(args.screenshots).resolve(),args.pass_id,args.model) else 1)
