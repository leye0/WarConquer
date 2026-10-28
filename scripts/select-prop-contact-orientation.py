#!/usr/bin/env python3
"""One cheap vision vote across four genuine Babylon grip orientations.

The candidates are anatomical directions, not Euler rotations and never
depend on the name of a weapon or character. A wrong candidate simply loses.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw

MODEL="google/gemini-2.5-flash-lite"
ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
ROOT=Path(__file__).resolve().parents[1]
CHOICES=("forward","backward","outward","inward")
SCHEMA={"type":"object","additionalProperties":False,"properties":{
    "direction":{"type":"string","enum":[*CHOICES,"none"]},
    "confidence":{"type":"number"},"explanation":{"type":"string"}
},"required":["direction","confidence","explanation"]}
PROMPT=(
    "You are choosing the BEST physical orientation of a generic handheld "
    "3D prop on a real humanoid in a running game. IMAGE 1 is the isolated "
    "original prop. IMAGES 2 and 3 show FOUR alternatives, labeled by their "
    "anatomical attachment direction. Each option comes from the same actual "
    "3D GLB and the exact same rig/pose; ONLY the direction of the object's "
    "functional face changes. Judge the real visual object: the sharp or "
    "working side must point naturally AWAY from the holder's torso, so the "
    "character can use the object without the blade cutting themself. "
    "The grip must remain in the hand and the object must be physically "
    "oriented. Which candidate is visibly correct from BOTH screenshots? "
    "Do not confuse the back/poll of a head with the real sharp edge. "
    "Return 'none' if every option looks wrong. This is a generic pose "
    "decision, not a named-weapon rotation adjustment. Return JSON only."
)


def contact_sheet(root: Path, view: str):
    sheet=Image.new("RGB",(1200,800),(238,240,241))
    draw=ImageDraw.Draw(sheet)
    for index,direction in enumerate(CHOICES):
        path=root/direction/(view+".png")
        frame=Image.open(path).convert("RGB")
        w,h=frame.size
        # Crop only the actual game canvas region, independent of sidebars.
        fragment=frame.crop((int(w*.02),int(h*.15),int(w*.73),int(h*.84)))
        fragment.thumbnail((580,358))
        x=(index%2)*600+10;y=(index//2)*400+33
        sheet.paste(fragment,(x,y))
        draw.text((x,y-23),direction.upper(),fill=(16,24,30))
    stream=io.BytesIO();sheet.save(stream,format="JPEG",quality=84)
    return stream.getvalue()


def part(payload: bytes):
    return {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+
        base64.b64encode(payload).decode("ascii")}}


def choose(plan_path: Path, views_dir: Path, previously_rejected: str):
    doc=json.loads(plan_path.read_text())
    original=Image.open(ROOT/doc["inputs"]["object_image"])
    original.thumbnail((700,700))
    stream=io.BytesIO();original.convert("RGB").save(stream,format="JPEG",quality=82)
    input_signature=hashlib.sha256(json.dumps({"landmarks":doc["mesh_landmarks"],
        "specifications":doc["specifications"],"rejected":previously_rejected},
        sort_keys=True).encode()).hexdigest()
    receipt=plan_path.with_name("grip-orientation-selection-response.json")
    response=None
    if receipt.is_file():
        record=json.loads(receipt.read_text())
        if record.get("signature")==input_signature:
            response=record["raw_selection"]
    if response is None:
        key=os.environ.get("OPENROUTER_API_KEY","").strip()
        if not key:raise RuntimeError("OPENROUTER_API_KEY is required")
        parts=[{"type":"text","text":"IMAGE 1: original design"},part(stream.getvalue()),
          {"type":"text","text":"IMAGE 2: FRONT views; each labeled by candidate"},
          part(contact_sheet(views_dir,"front")),
          {"type":"text","text":"IMAGE 3: SIDE views; same options and labels"},
          part(contact_sheet(views_dir,"side"))]
        payload={"model":MODEL,"temperature":0,"max_tokens":300,
          "provider":{"require_parameters":True},
          "response_format":{"type":"json_schema","json_schema":{
            "name":"contact_orientation_selection","strict":True,"schema":SCHEMA}},
          "messages":[{"role":"system","content":PROMPT},
                      {"role":"user","content":parts}]}
        req=Request(ENDPOINT,data=json.dumps(payload).encode(),method="POST",
            headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
                "HTTP-Referer":"https://github.com/leye0/WarConquer",
                "X-Title":"WarConquer vision-guided generic pose search"})
        with urlopen(req,timeout=150) as stream_response:
            answer=json.loads(stream_response.read(160000))
        response=json.loads((answer.get("choices") or [{}])[0]["message"]["content"])
        receipt.write_text(json.dumps({"schema":1,"signature":input_signature,
            "model":MODEL,"raw_selection":response},ensure_ascii=False,indent=2)+"\n")
    if (not isinstance(response,dict) or set(response)!=set(SCHEMA["properties"]) or
            response["direction"] not in (*CHOICES,"none") or
            not isinstance(response["confidence"],(float,int)) or
            response["confidence"]<.75):
        raise ValueError("Vision could not select a safe anatomical working-face orientation")
    if response["direction"] in ("none",previously_rejected):
        raise ValueError("Vision rejected all new contact orientations: "+response["explanation"])
    print("VISION_SELECTED_CONTACT_DIRECTION",response["direction"],response["explanation"])
    return response["direction"]
