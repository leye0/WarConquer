#!/usr/bin/env python3
"""One approved image-to-textured-prop TRELLIS prediction, resumable, no retries.

The weapon stays a separate mesh, not part of the 52-joint skinned body.
First approve the exact isolated PNG SHA256 in trellis-axe-request.json.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/"trellis-axe-request.json"
IMAGE=ROOT/"assets/concepts/marches/objects/hache_arme.png"
DEST=ROOT/"assets/experiments/props/marches_hache/trellis-v1"
GLB=DEST/"axe.glb"
CHECKPOINT=DEST/"prediction.json"
MODEL="firtoz/trellis"
VERSION="e8f6c45206993f297372f5436b90350817bd9b4a0d52d2a76df50c1c8afa2b3c"
INPUTS={"generate_model":True,"generate_color":True,"generate_normal":True,
        "texture_size":1024,"mesh_simplify":0.95,"randomize_seed":False,
        "seed":20261027,"ss_sampling_steps":12,"slat_sampling_steps":12,
        "ss_guidance_strength":7.5,"slat_guidance_strength":3}
TERMINAL={"succeeded","failed","canceled"}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    tmp.replace(path)

def approved():
    cfg=json.loads(REQUEST.read_text())
    expected={"schema":1,"experiment":"marches-axe-prop-trellis-v1",
      "source_image":str(IMAGE.relative_to(ROOT)),
      "source_sha256":cfg.get("source_sha256"),
      "source_visually_approved":True,
      "replicate_model":MODEL,"replicate_version":VERSION,
      "model_inputs":INPUTS,"maximum_paid_predictions":1,
      "automatic_paid_retries":0,
      "output_path":str(GLB.relative_to(ROOT))}
    if cfg!=expected:
        raise ValueError("Trellis contract differs from visually approved input")
    h=cfg["source_sha256"]
    if not isinstance(h,str) or not re.fullmatch("[a-f0-9]{64}",h):
        raise ValueError("Exact source SHA256 is required")
    if not IMAGE.is_file() or sha(IMAGE)!=h:
        raise ValueError("Approved source PNG missing or changed")
    from PIL import Image
    with Image.open(IMAGE) as image:
        if (image.width,image.height) not in ((1024,1024),(1600,1600)) or image.mode!="RGBA":
            raise ValueError("Source must be a reviewed square Muse RGBA PNG")
        bounds=image.getchannel("A").getbbox()
        edge=round(image.width*.005)
        if not bounds or bounds[0]<edge or bounds[1]<edge or bounds[2]>image.width-edge or bounds[3]>image.height-edge:
            raise ValueError("Axe silhouette cropped or empty")
    return cfg

def api():
    import replicate
    token=os.environ.get("REPLICATE_API_TOKEN","").strip()
    if not token:
        raise RuntimeError("Missing existing Replicate Actions secret")
    return replicate.Client(api_token=token)

def submit(cfg):
    if CHECKPOINT.exists() or GLB.exists():
        print("Existing submitted or completed weapon trial, no paid resubmit")
        return
    with IMAGE.open("rb") as inp:
        prediction=api().predictions.create(version=VERSION,
            input={**INPUTS,"images":[inp]})
    if not prediction.id:
        raise RuntimeError("Replicate accepted no prediction ID; do not auto retry")
    save(CHECKPOINT,{"model":MODEL,"version":VERSION,"prediction_id":prediction.id,
         "initial_status":prediction.status,
         "source_sha256":cfg["source_sha256"],
         "paid_predictions_submitted":1,"retry_count":0})
    print("One Trellis prediction submitted:",prediction.id)

def find_glb(value):
    if isinstance(value,str):
        return value if ".glb" in urlparse(value).path.lower() else None
    if isinstance(value,list):
        return next((uri for x in value if (uri:=find_glb(x))),None)
    if isinstance(value,dict):
        return next((uri for x in value.values() if (uri:=find_glb(x))),None)
    return None

def collect(cfg):
    if GLB.exists():
        print("Already collected axe GLB")
        return
    rec=json.loads(CHECKPOINT.read_text())
    if rec["source_sha256"]!=cfg["source_sha256"] or rec["version"]!=VERSION:
        raise ValueError("Pinned Trellis prediction mismatch")
    client=api()
    deadline=time.monotonic()+9*60
    while True:
        prediction=client.predictions.get(rec["prediction_id"])
        print("Trellis prediction:",prediction.status,flush=True)
        if prediction.status in TERMINAL:
            break
        if time.monotonic()>deadline:
            raise TimeoutError("Existing prediction still running; collect later without resubmitting")
        time.sleep(15)
    if prediction.status!="succeeded":
        save(DEST/"error.json",{"prediction_id":rec["prediction_id"],
                                  "status":prediction.status,
                                  "error":str(prediction.error)[:500]})
        raise RuntimeError("TRELLIS trial failed: no automatic retries")
    uri=find_glb(prediction.output)
    if not uri:
        raise ValueError("Prediction succeeded without an identifiable GLB")
    parsed=urlparse(uri)
    host=parsed.hostname or ""
    if parsed.scheme!="https" or not(host=="replicate.delivery" or host.endswith(".replicate.delivery")):
        raise ValueError("Unexpected 3D file download host")
    with urlopen(uri,timeout=160) as resp:
        blob=resp.read(60*1024*1024+1)
    if not 4096<=len(blob)<=60*1024*1024 or blob[:4]!=b"glTF":
        raise ValueError("Invalid or oversized GLB")
    _,version,size=struct.unpack_from("<4sII",blob,0)
    if version!=2 or size!=len(blob):
        raise ValueError("Malformed GLB binary header")
    n,typ=struct.unpack_from("<I4s",blob,12)
    if typ!=b"JSON":
        raise ValueError("Missing GLB JSON")
    doc=json.loads(blob[20:20+n])
    if not doc.get("meshes") or not doc.get("materials") or not doc.get("images"):
        raise ValueError("Missing textured geometry (mesh/material/image)")
    DEST.mkdir(parents=True,exist_ok=True)
    GLB.write_bytes(blob)
    save(DEST/"report.json",{"status":"technical-check-passed-awaiting-visual-and-grip-QA",
       "model":MODEL,"version":VERSION,
       "prediction_id":rec["prediction_id"],
       "source_sha256":cfg["source_sha256"],
       "glb_sha256":sha(GLB),"glb_bytes":len(blob),
       "meshes":len(doc["meshes"]),"materials":len(doc["materials"]),
       "images":len(doc["images"]),
       "rigged":False,"right_hand_attachment_complete":False,
       "limitations":"Axe visual shape, shaft thickness, correct orientation and hand grip are not yet reviewed",
       "paid_predictions_submitted":1})
    print("Collected textured axe:",GLB,len(blob),"bytes")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stage",choices=("validate","submit","collect"),required=True)
    args=p.parse_args()
    cfg=approved()
    if args.stage=="validate":
        print("Approved source SHA256 and model contract valid. No billable calls.")
    elif args.stage=="submit":
        submit(cfg)
    else:
        collect(cfg)

if __name__=="__main__":
    main()
