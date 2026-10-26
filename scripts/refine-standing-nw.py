#!/usr/bin/env python3
"""One targeted NW still-image correction using WarConquer's OpenRouter -> Muse pipeline.

NW must be a complete BODY TURN away and left, not merely a head turn.
Retains the old NW asset and publishes a candidate for human pose validation.
"""
import argparse
import base64
import hashlib
import io
import json
import os
import runpy
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"assets/experiments/standing-turnaround/marches_hache"
REQUEST=ROOT/"standing-nw-fix-request.json"
N=OUT/"N.png"
W=OUT/"W.png"
OLD_NW=OUT/"NW.png"
CONCEPT=ROOT/"assets/concepts/marches/units/hache.png"
RESULT=OUT/"NW-v2.png"
DETAIL=OUT/"NW-v2.json"
COMPARISON=OUT/"review-NW-before-after.png"

PROMPT="""Create precisely ONE full-body STILL portrait/sprite-style game character of the EXACT SAME original WarConquer human axeman shown in the three visual references.

CRITICAL FAILURE TO CORRECT: The previous NW drawing has a head that looks Northwest, but the HIPS, CHEST AND FEET still face East. That is WRONG. Do not repeat it.

RECONSTRUCT A REAL 45-DEGREE FULL-BODY ROTATION:
- Reference image 1 is the existing N (north) BACK VIEW of this exact axeman.
- Reference image 2 is the existing W (west) LEFT-FACING SIDE VIEW of the SAME axeman.
- Reference image 3 is the original WarConquer concept, exclusively for identity, materials and weapon details.
- The required NEW NW view lies HALF-WAY between reference 1's back-facing N orientation and reference 2's side-facing W orientation. Physically rotate the ENTIRE rigid body from N toward W by exactly 45 degrees around its vertical spine. Do not simply swivel the neck, turn the eyes, rotate the arms, or mirror-flip an existing image.
- In screen coordinates, north is away/up and west is left. NW is UP AND LEFT simultaneously, diagonally away from the camera.
- THE CHEST/STERNUM must point AWAY-LEFT, NW. So must the navel, belt buckle, sternum axis, pelvis, thighs, both knees, kneecaps and BOTH FOOT TOE DIRECTIONS. The head is centered over the same rotating torso and looks exactly where the toes and sternum point, not elsewhere.
- The SHOULDER LINE and HIP LINE are correctly foreshortened by the common NW body yaw; the back and red cape are the dominant visible surfaces, with a portion of the character's left flank. The chest/front armor and whole face are mostly OCCLUDED, unlike a profile or front view. The character's back and cape must be a little less square-on than N, and much more visible than in W.
- Both boots are planted in a quiet neutral stance with toes visibly oriented NW in perspective; feet must NOT point screen-right/E or screen-down/S. NO TWIST of neck relative to torso, torso relative to pelvis, or ankles relative to legs.
- The AXE remains in the original anatomical hand, with exactly the same distinctive hammered metal blade and bindings, held LOW and naturally, no attacking.

Show ONE stationary, perfectly upright warrior with relaxed arms, same proportions, same outfit, same hairstyle, beard, red ragged cape and wrappings, bronze/iron attachments, dark leather armor and boots as these references. No new details, no asymmetry reversal, no new or extra weapon. Exactly one human with a full visible body and full visible axe.

This is a MODERN detailed high-definition hand-painted 2D RTS character asset, smooth realistic painted detail and edges. NOT pixel art. 25-35 degree elevated orthographic RTS camera, same scale as N and W references. Isolated character on a transparent plain backdrop (or pure WHITE or BLACK for later alpha processing), no scenery, text, arrows, captions, floor, shadows, checkerboard, UI, additional figures, dramatic tilt or action. Full weapon and boots inside frame with large safe margins.

ABSOLUTE PRIORITY FOR COMPLIANCE: body yaw NW before face/gaze direction; true three-quarter rear-left silhouette; both feet pointing NW; no east-facing torso.
"""

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate():
    config=json.loads(REQUEST.read_text(encoding="utf-8"))
    expected={"character":"marches_hache","direction":"NW","stance":"standing_still",
              "output":"assets/experiments/standing-turnaround/marches_hache/NW-v2.png",
              "max_paid_generations":1}
    for key,v in expected.items():
        if config.get(key)!=v:
            raise ValueError(f"Invalid NW-only request field {key}")
    if config.get("references")!=[
        "assets/experiments/standing-turnaround/marches_hache/N.png",
        "assets/experiments/standing-turnaround/marches_hache/W.png",
        "assets/concepts/marches/units/hache.png",
    ]:
        raise ValueError("Only approved N / W / original concept references permitted")
    for source in (N,W,CONCEPT,OLD_NW):
        if not source.is_file():
            raise FileNotFoundError(source)
        Image.open(source).verify()
    return config

def refs():
    value=[]
    for file in (N,W,CONCEPT):
        content=file.read_bytes()
        value.append({"type":"image_url","image_url":{
            "url":"data:image/png;base64,"+base64.b64encode(content).decode("ascii")}})
    return value

def ask_muse(model,key):
    payload={
        "model":model,"prompt":PROMPT,"input_references":refs(),
        "n":1,"output_format":"png","background":"transparent","aspect_ratio":"1:1"
    }
    req=urllib.request.Request("https://openrouter.ai/api/v1/images",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req,timeout=300) as response:
            response_data=json.load(response)
    except urllib.error.HTTPError as exc:
        detail=""
        try:
            parsed=json.loads(exc.read(4096).decode("utf-8"))
            err=parsed.get("error",{}) if isinstance(parsed,dict) else {}
            detail=str(err.get("message",""))[:250] if isinstance(err,dict) else ""
        except (ValueError, UnicodeError):
            pass
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail}. No paid retry.") from None
    binary=base64.b64decode(response_data["data"][0]["b64_json"],validate=True)
    image=Image.open(io.BytesIO(binary)).convert("RGBA")
    return image,binary,response_data.get("usage",{})

def composite_review():
    names=[("N — back view",N),("NW — previous, incorrect",OLD_NW),
           ("NW — Muse candidate",RESULT),("W — left profile",W)]
    cell=440
    board=Image.new("RGB",(4*cell,cell+92),"#e7edf1")
    draw=ImageDraw.Draw(board)
    draw.rectangle((0,0,4*cell,50),fill="#1e3548")
    draw.text((18,15),"WARCONQUER  |  NW: rotate entire body 45 degrees from N toward W",fill="white")
    for idx,(label,path) in enumerate(names):
        x=idx*cell
        draw.rectangle((x+6,56,x+cell-6,cell+85),fill="#f9fbfb",outline="#c6d3db",width=2)
        picture=Image.open(path).convert("RGBA")
        picture.thumbnail((cell-28,cell-80),Image.Resampling.LANCZOS)
        board.paste(picture,(x+(cell-picture.width)//2,98+(cell-80-picture.height)//2),picture)
        draw.text((x+14,67),label,fill="#23445c")
    board.save(COMPARISON)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dry-run",action="store_true")
    args=ap.parse_args()
    config=validate()
    if args.dry_run:
        print(json.dumps({"ready":True,"model_source":"OPENROUTER_IMAGE_MODEL",
             "frames_to_generate":["NW"],"other_directions_changed":0,
             "paid_calls":0,"references":config["references"]}),flush=True)
        return
    model=os.environ.get("OPENROUTER_IMAGE_MODEL")
    key=os.environ.get("OPENROUTER_API_KEY")
    if not model or not key:raise RuntimeError("Required Muse secrets missing")
    if RESULT.exists():
        print("NW candidate already present; preserve without spending more",flush=True)
        return
    OUT.mkdir(parents=True,exist_ok=True)
    # Reuse original project's successfully tested alpha and canonical baseline pipeline.
    shared=runpy.run_path(str(ROOT/"scripts/generate-standing-directions.py"))
    raw,raw_data,usage=ask_muse(model,key)
    raw_path=ROOT/"nw-output"/"raw"/"NW.png"
    raw_path.parent.mkdir(parents=True,exist_ok=True)
    raw_path.write_bytes(raw_data)
    separated,method=shared["extract_alpha"](raw)
    normalized,geometry=shared["place_character"](separated)
    normalized.save(RESULT)
    composite_review()
    metadata={
        "direction":"NW","status":"draft-awaiting-human-visual-validation","approved":False,
        "experiment":"physically rotate entire character 45 degrees from N toward W",
        "other_directions_unchanged":True,"original_NW_sha256":sha(OLD_NW),
        "new_NW_sha256":sha(RESULT),"reference_sha256":{f.name:sha(f) for f in (N,W,CONCEPT)},
        "model":model,"prompt":PROMPT,"usage":usage,"output_px":list(normalized.size),
        "source_px":list(raw.size),"matte_method":method,**geometry,
        "review_file":str(COMPARISON.relative_to(ROOT)),
        "warning":"Neither successful generation nor alpha checks prove correct NW body yaw. Inspect image and compare foot, hip and chest orientation."
    }
    DETAIL.write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("NW CANDIDATE GENERATED: "+str(RESULT.relative_to(ROOT))
          +" | "+str(geometry)+" | cost "+str(usage),flush=True)

if __name__=="__main__":
    main()
