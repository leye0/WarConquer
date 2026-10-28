#!/usr/bin/env python3
"""Generic unit image->3D builder. Selection and outputs come from a unit JSON.

Actions may call this exact script; neither paid generation nor path selection
lives in an Actions YAML. Every external prediction is recorded, never retried
implicitly, and existing outputs are reused.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import struct
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
STAGES=("turnaround","body")
VIEWS=("front","back","left","right")
POSE=(
 "Precisely preserve the person, head, facial expression, clothing, materials, colors, "
 "boots, proportions and identity from the FIRST attached original unit concept. "
 "This is the SAME character being prepared for 3D retopology. "
 "Draw ONE complete full-body adult character in exact symmetric anatomical T-POSE: "
 "both arms straight out sideways at the same shoulder height, palms down or open, "
 "legs straight with feet flat and hip-width apart. No bow, quiver, arrow, weapon, "
 "shield or held objects. Hands separate from torso; no fabric bridging elbows. "
 "Full body from hair top to boots within frame. Neutral clean soft lighting, "
 "no floor, text, backdrop or shadow. 1024-square canvas, orthographic camera, "
 "transparent background. Match hand-painted detailed fantasy RTS visual style. "
 "The reference is the identity, NOT an invitation to keep the arms in their "
 "original weapon-holding pose."
)
CAMERAS={
 "front":"Straight-on FRONT orthographic camera: show face, front armor and both ears symmetrically. Arms extend toward image sides.",
 "back":"Exact REAR BACK orthographic camera: back of head and clothing, both shoulders, no face or chest. Arms extend toward image sides.",
 "left":"Exact character LEFT side profile orthographic camera. Nose points image LEFT; both arms extend toward/away from camera and overlap narrow torso, no frontal chest.",
 "right":"Exact character RIGHT side profile orthographic camera. Nose points image RIGHT; both arms extend toward/away from camera and overlap narrow torso, no frontal chest.",
}

def local(rel):
 if not isinstance(rel,str) or not rel or rel.startswith("/") or "\\" in rel:
  raise ValueError("Unsafe relative path")
 p=(ROOT/rel).resolve()
 if not p.is_relative_to(ROOT):raise ValueError("Path escapes repository")
 return p

def manifest(unit):
 if not unit or not all(c.islower() or c.isdigit() or c=="_" for c in unit):
  raise ValueError("Invalid unit ID")
 path=local("data/units/"+unit+".json")
 data=json.loads(path.read_text())
 if data.get("id")!=unit or data.get("schema")!=1:raise ValueError("Unit id/schema mismatch")
 if set(data["source"]["views"])!=set(VIEWS):raise ValueError("Four physical views required")
 if data["body"]["glb"].endswith("/marches_hache/tpose-v2/fal-textured.glb") and unit!="marches_hache":
  raise ValueError("Cross-unit GLB output forbidden")
 return data

def sha(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix(path.suffix+".tmp")
 tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
 tmp.replace(path)

def image_qa(path):
 if not path.is_file():raise ValueError("Missing PNG "+str(path))
 from PIL import Image
 with Image.open(path) as im:
  if im.size!=(1024,1024) or im.mode!="RGBA":
   raise ValueError("Expected 1024x1024 RGBA T-pose")
  bbox=im.getchannel("A").point(lambda x:255 if x>48 else 0).getbbox()
  if not bbox:raise ValueError("No silhouette")
  margin=min(bbox[0],bbox[1],1024-bbox[2],1024-bbox[3])
  if margin<24:raise ValueError("T-pose clipped: "+str(bbox))
  return {"sha256":sha(path),"bbox":list(bbox),"margin_px":margin}

def get_muse():
 spec=importlib.util.spec_from_file_location("rig_muse_helpers",ROOT/"scripts/rig-muse-helpers.py")
 module=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(module)
 return module

def turnaround(data,paid):
 original=local(data["source"]["character_image"])
 if not original.is_file():raise ValueError("Missing original concept")
 helper=get_muse()
 output={}
 for view in VIEWS:
  path=local(data["source"]["views"][view])
  rec=path.with_suffix(".json")
  if path.is_file():
   output[view]={"status":"existing","qa":image_qa(path)}
   continue
  if rec.is_file():
   raise RuntimeError("Request already recorded for "+view+"; no paid resubmission. Review "+str(rec))
  if not paid:raise RuntimeError("Missing "+view+"; pass --allow-paid")
  if os.environ.get("OPENROUTER_IMAGE_MODEL")!="meta/muse-image":
   raise RuntimeError("Expected configured meta/muse-image; no paid request sent")
  if not os.environ.get("OPENROUTER_API_KEY"):raise RuntimeError("OPENROUTER_API_KEY missing")
  prompt=POSE+" "+CAMERAS[view]
  refs=[helper.reference_payload(original.read_bytes())[0]]
  front=local(data["source"]["views"]["front"])
  if view!="front" and front.is_file():
   refs.append(helper.reference_payload(front.read_bytes())[0])
  save(rec,{"schema":1,"unit":data["id"],"view":view,
    "status":"requested-outcome-unknown","model":"meta/muse-image",
    "original_sha256":sha(original),
    "prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
    "paid_request_maximum":1})
  try:
   generated,raw,usage=helper.call_muse(prompt,refs,"meta/muse-image")
   clean,alpha=helper.extract_alpha(generated)
   normalized,placement=helper.place_character(clean)
   path.parent.mkdir(parents=True,exist_ok=True)
   normalized.save(path,optimize=True)
   quality=image_qa(path)
   save(rec,{"schema":1,"unit":data["id"],"view":view,
     "status":"generated-review-needed","model":"meta/muse-image",
     "original_sha256":sha(original),"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
     "usage":usage,"alpha":alpha,"placement":placement,"qa":quality,
     "paid_request_maximum":1})
   output[view]={"status":"generated","qa":quality}
   print("GENERATED VIEW",data["id"],view,quality,flush=True)
  except Exception as e:
   prior=json.loads(rec.read_text())
   prior["status"]="failed-or-unresolved-no-automatic-retry"
   prior["error"]=type(e).__name__+": "+str(e)[:360]
   save(rec,prior)
   raise
 return output

def body(data,paid):
 from importlib.util import spec_from_file_location,module_from_spec
 helper_spec=spec_from_file_location("fal_mesh_validation",ROOT/"scripts/generate-fal-textured-pilot.py")
 fal=module_from_spec(helper_spec)
 helper_spec.loader.exec_module(fal)
 dest=local(data["body"]["glb"])
 receipt=dest.with_name("fal-receipt.json")
 report=dest.with_name("fal-texture-report.json")
 if dest.is_file():
  meta=fal.verify_textured_glb(dest.read_bytes())
  print("Existing textured GLB",dest.relative_to(ROOT),meta)
  return
 if not paid:raise RuntimeError("Missing 3D mesh: pass --allow-paid")
 if not os.environ.get("FAL_KEY"):raise RuntimeError("FAL_KEY missing")
 src={v:local(data["source"]["views"][v]) for v in ("front","back","left")}
 refs={v:image_qa(path) for v,path in src.items()}
 if receipt.is_file():
  previous=json.loads(receipt.read_text())
  if previous.get("unit")!=data["id"] or previous.get("source_sha256")!={v:x["sha256"] for v,x in refs.items()}:
   raise RuntimeError("Existing fal receipt refers to different unit/images")
  request_id=previous["request_id"]
 else:
  request_id=None
 import fal_client
 if request_id:
  handle=fal_client.get_handle(fal.MODEL,request_id)
 else:
  uploaded={v+"_image_url":fal_client.upload_file(str(src[v])) for v in src}
  handle=fal_client.submit(fal.MODEL,arguments={**uploaded,
    "textured_mesh":True,"seed":20261027,"num_inference_steps":50,
    "guidance_scale":7.5,"octree_resolution":256})
  receipt_data={"schema":1,"unit":data["id"],"model":fal.MODEL,
     "request_id":handle.request_id,
     "source_sha256":{v:x["sha256"] for v,x in refs.items()},
     "status":"submitted","estimated_cost_usd":0.48}
  save(receipt,receipt_data)
  print("FAL_REQUEST_ID",handle.request_id,flush=True)
 result=handle.get()
 uri=(result.get("model_mesh") or {}).get("url")
 if not isinstance(uri,str) or urlparse(uri).scheme!="https":
  raise RuntimeError("No valid GLB URL from fal")
 with urlopen(uri,timeout=180) as response:
  raw=response.read(45_000_001)
 if len(raw)>45_000_000:raise ValueError("GLB size cap exceeded")
 stats=fal.verify_textured_glb(raw)
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_bytes(raw)
 rec=json.loads(receipt.read_text())
 rec["status"]="downloaded"
 save(receipt,rec)
 save(report,{"schema":1,"unit":data["id"],"model":fal.MODEL,
    "request_id":handle.request_id,"estimated_cost_usd":0.48,
    "output":str(dest.relative_to(ROOT)),"sha256":sha(dest),
    "bytes":len(raw),"visual_qa":"pending",**stats})
 print("GENERATED UNIT 3D",data["id"],stats,"estimated USD",0.48,flush=True)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--unit",required=True)
 p.add_argument("--stage",choices=(*STAGES,"all"),default="all")
 p.add_argument("--allow-paid",action="store_true")
 p.add_argument("--check",action="store_true")
 a=p.parse_args()
 doc=manifest(a.unit)
 if a.check:
  print(json.dumps({"unit":doc["id"],"source":doc["source"]["character_image"],
       "views":{v:local(path).is_file() for v,path in doc["source"]["views"].items()},
       "textured_glb":local(doc["body"]["glb"]).is_file()},indent=2))
  return
 if a.stage in ("turnaround","all"):turnaround(doc,a.allow_paid)
 if a.stage in ("body","all"):body(doc,a.allow_paid)
if __name__=="__main__":main()
