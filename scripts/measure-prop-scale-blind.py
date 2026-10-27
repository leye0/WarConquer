#!/usr/bin/env python3
"""Blind, source-only estimate of equipment size. No previous plan or render access.

The LLM sees the original unit art, the isolated prop (identity only), and its
original generation description; it cannot see an already scaled GLB or any
prior model output. Image landmarks are independently converted into an image-
space ratio. This does not automatically approve a 3D scale.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
DEFAULT="assets/experiments/props/marches_hache/trellis-v1/grip-scale-blind-request-v6.json"
MODEL="google/gemini-2.5-flash-lite"
ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
EXPECTED={"schema","experiment","generation_request","source_character","source_prop",
          "output_path","vision_model","maximum_paid_requests","automatic_paid_retries"}
POINT={"type":"array","items":{"type":"number"}}
FIELDS={
 "character_head_top":POINT,
 "character_foot_bottom":POINT,
 "object_handle_butt":POINT,
 "object_handle_near_head":POINT,
 "object_head_axis_end":POINT,
 "object_blade_side_tip":POINT,
 "object_fully_visible":{"type":"boolean"},
 "character_fully_visible":{"type":"boolean"},
 "recognizable_same_object":{"type":"boolean"},
 "perspective":{"type":"string","enum":["low_distortion","foreshortened","unclear"]},
 "preferred_length_relative_character_height":{"type":"number"},
 "confidence":{"type":"number"},
 "observations":{"type":"string"}
}
SCHEMA={"type":"object","properties":FIELDS,"required":list(FIELDS),
        "additionalProperties":False}
SYSTEM=(
 "You are the equipment proportions specialist for a game. Your ONLY goal "
 "is to estimate the intended size of the equipment relative to the person "
 "in the ORIGINAL PERSON CONCEPT alone, without any game scene. "
 "IMAGE ONE shows the original full character and his original weapon. "
 "IMAGE TWO is the generated isolated weapon, with no physical size reference; "
 "use it ONLY to identify the weapon and its construction. "
 "An original written brief accompanies the images and describes intended "
 "design, material and use. The brief does not specify physical dimensions. "
 "Report image-one normalized coordinates (x/width,y/height) for "
 "head top, lowest foot, butt of the shaft, handle-head junction, "
 "farthest head endpoint ALONG THE SHAFT AXIS, and a blade side tip. "
 "Do not measure corner-to-corner distance from the handle butt to "
 "the outer blade edge as if all that diagonal were weapon length. "
 "The working blade can project sideways from the shaft: measure its "
 "perpendicular width separately from the axial shaft+head length. "
 "Use true image aspect ratio and consider foreshortening explicitly. "
 "Independently select the final "
 "intended equipment-to-person length ratio. If any part of the equipment "
 "is cut off, hidden or unrecognizable, report object_fully_visible=false "
 "and a low confidence instead of inventing invisible endpoints. "
 "The isolated weapon's size on its own canvas is irrelevant. "
 "Do not assume a huge size because the words LONG or TWO-HANDED appear. "
 "Do not use external pictures or game stats. Judge solely these two original source images. Respond in the strict JSON schema."
)

def local(value):
 if not isinstance(value,str) or not value or value.startswith("/"):
  raise ValueError("Unsafe path")
 p=(ROOT/value).resolve()
 if not p.is_relative_to(ROOT) or not p.is_file():raise ValueError("Missing source file: "+value)
 return p

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def store(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_suffix(".tmp")
 tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
 tmp.replace(p)

def inputs(request):
 cfg=json.loads(local(request).read_text())
 if set(cfg)!=EXPECTED or cfg["schema"]!=6 or cfg["vision_model"]!=MODEL:
  raise ValueError("Invalid blind analysis config")
 if cfg["maximum_paid_requests"]!=1 or cfg["automatic_paid_retries"]!=0:
  raise ValueError("Paid call budget must be exactly once")
 # No imported plan or rendered image is even resolvable here.
 required={"generation_request","source_character","source_prop"}
 paths={k:local(cfg[k]) for k in required}
 brief=json.loads(paths["generation_request"].read_text())
 if brief.get("output")!=cfg["source_prop"] or cfg["source_character"] not in brief.get("references",[]):
  raise ValueError("Source object doesn't match the generation brief")
 if not isinstance(brief.get("prompt"),str) or not brief["prompt"]:
  raise ValueError("Missing original object identity")
 dest=(ROOT/cfg["output_path"]).resolve()
 if not dest.is_relative_to(ROOT) or dest.suffix!=".json":
  raise ValueError("Invalid output destination")
 hashes={k+"_sha256":sha(v) for k,v in paths.items()}
 return cfg,paths,brief,dest,hashes

def image(path):
 with Image.open(path) as original:
  png=ImageOps.exif_transpose(original.convert("RGBA"))
  original_size=png.size
  bg=Image.new("RGBA",png.size,"white")
  bg.alpha_composite(png)
  fitted=bg.convert("RGB")
  fitted.thumbnail((1200,1200),Image.Resampling.LANCZOS)
  buf=io.BytesIO()
  fitted.save(buf,format="JPEG",quality=85,optimize=True)
  raw=buf.getvalue()
  if len(raw)>750000:raise ValueError("Excessive JPEG payload")
  return {"type":"image_url","image_url":{
   "url":"data:image/jpeg;base64,"+base64.b64encode(raw).decode()}},list(fitted.size),len(raw)

def calculate(raw,dimensions):
 if not isinstance(raw,dict) or set(raw)!=set(FIELDS):
  raise ValueError("Invalid exact image landmark schema")
 pts={}
 for name in ["character_head_top","character_foot_bottom","object_handle_butt","object_handle_near_head","object_head_axis_end","object_blade_side_tip"]:
  point=raw[name]
  if not isinstance(point,list) or len(point)!=2 or any(isinstance(v,bool)
        or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1
        for v in point):raise ValueError("Invalid visual landmark "+name)
  pts[name]=point
 for k in ("object_fully_visible","character_fully_visible","recognizable_same_object"):
  if not isinstance(raw[k],bool):raise ValueError("Invalid visibility assertion")
 if raw["perspective"] not in FIELDS["perspective"]["enum"]:raise ValueError("Invalid perspective")
 for k in ("confidence","preferred_length_relative_character_height"):
  v=raw[k]
  if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v):
   raise ValueError("Non-numeric "+k)
 if not 0<=raw["confidence"]<=1 or not .1<=raw["preferred_length_relative_character_height"]<=2:
  raise ValueError("Out-of-range confidence or requested scale")
 if not isinstance(raw["observations"],str) or len(raw["observations"])<45:
  raise ValueError("Missing visual explanation")
 w,h=dimensions
 def dist(a,b):
  p,q=pts[a],pts[b]
  return math.hypot((p[0]-q[0])*w,(p[1]-q[1])*h)
 unit=dist("character_head_top","character_foot_bottom")
 handle=dist("object_handle_butt","object_handle_near_head")
 if unit<min(w,h)*.15 or handle<min(w,h)*.05:
  raise ValueError("Insufficient pixel footprint; cannot compute size")
 butt=pts["object_handle_butt"]
 joint=pts["object_handle_near_head"]
 vx=(joint[0]-butt[0])*w/handle
 vy=(joint[1]-butt[1])*h/handle
 end=pts["object_head_axis_end"]
 ex=(end[0]-butt[0])*w
 ey=(end[1]-butt[1])*h
 # Diagonal to the outer blade edge does not represent weapon axial length.
 axial_projection=ex*vx+ey*vy
 side=pts["object_blade_side_tip"]
 bx=(side[0]-butt[0])*w
 by=(side[1]-butt[1])*h
 lateral_extent=abs(bx*vy-by*vx)
 if axial_projection<handle*.90:
  raise ValueError("Head-axis landmark inconsistent with handle orientation")
 ratio=max(axial_projection,handle)/unit
 shaft_ratio=handle/unit
 blade_width_ratio=lateral_extent/unit
 if not .07<=ratio<=2.5 or blade_width_ratio>1.5:
  raise ValueError("Bad source silhouette geometry")
 if not all(raw[k] for k in ("object_fully_visible","character_fully_visible","recognizable_same_object")):
  raise ValueError("Source artwork lacks full measurable wearer/object; requires new views")
 if raw["perspective"]=="unclear" or raw["confidence"]<.60:
  raise ValueError("Ambiguous source perspective/landmarks, not an approved ratio")
 return {"projected_length_ratio":round(ratio,5),
         "shaft_length_ratio":round(shaft_ratio,5),
         "blade_lateral_extent_ratio":round(blade_width_ratio,5),
         "preferred_length_ratio":raw["preferred_length_relative_character_height"],
         "disagreement":round(abs(raw["preferred_length_relative_character_height"]-ratio),5),
         "manual_review_required":raw["perspective"]=="foreshortened"
            or abs(raw["preferred_length_relative_character_height"]-ratio)>.22}
def vision_text(brief):
 return "ORIGINAL EQUIPMENT GENERATION DESCRIPTION:\n"+brief+"\nCharacter concept is IMAGE 1; isolated object is IMAGE 2. Find visual landmarks on IMAGE 1."

def run(request,check):
 cfg,paths,brief,out,hashes=inputs(request)
 checkpoint=out.with_name(out.stem+"-response.json")
 if out.is_file():
  saved=json.loads(out.read_text())
  if saved.get("input_hashes")!=hashes or saved.get("vision_model")!=MODEL:
   raise ValueError("Stale paid output; use a new request")
  calculate(saved["raw_visual_landmarks"],saved["source_image_dimensions"])
  print("Pinned source-only analysis verified; no inference")
  return
 if check:
  print("No accepted source-only plan yet; no paid call")
  return
 if checkpoint.exists():
  saved=json.loads(checkpoint.read_text())
  if saved.get("input_hashes")!=hashes or saved.get("vision_model")!=MODEL:
   raise ValueError("Cached paid response does not match sources")
  raw=saved["raw_visual_landmarks"]
  dimensions=saved["source_image_dimensions"]
  print("Resuming cached paid response")
 else:
  key=os.environ.get("OPENROUTER_API_KEY","").strip()
  if not key:raise ValueError("Missing OPENROUTER_API_KEY")
  unit,dimensions,b1=image(paths["source_character"])
  obj,_,b2=image(paths["source_prop"])
  payload={
   "model":MODEL,"temperature":0,"max_tokens":1850,
   "reasoning":{"effort":"low","exclude":True},
   "usage":{"include":True},
   "provider":{"require_parameters":True},
   "response_format":{"type":"json_schema","json_schema":{"name":"blind_source_equipment_size","strict":True,"schema":SCHEMA}},
   "messages":[
     {"role":"system","content":SYSTEM},
     {"role":"user","content":[
       {"type":"text","text":vision_text(brief["prompt"])},
       {"type":"text","text":"IMAGE 1: original character, use this for all proportional coordinates."},
       unit,
       {"type":"text","text":"IMAGE 2: isolated object, identity and craftsmanship only, absolutely no scale."},
       obj
     ]}
   ]
  }
  print("Source-only source images total bytes:",b1+b2)
  req=Request(ENDPOINT,data=json.dumps(payload).encode(),method="POST",headers={
   "Authorization":"Bearer "+key,
   "Content-Type":"application/json",
   "HTTP-Referer":"https://github.com/leye0/WarConquer",
   "X-Title":"WarConquer blind source proportions"})
  with urlopen(req,timeout=140) as res:
   result=json.loads(res.read(200000))
  content=(result.get("choices") or [{}])[0].get("message",{}).get("content")
  if not isinstance(content,str):raise ValueError("No JSON response from vision provider")
  raw=json.loads(content)
  usage=result.get("usage",{})
  cost=usage.get("cost") if isinstance(usage,dict) else None
  if not isinstance(cost,(int,float)) or isinstance(cost,bool) or cost<0:
   cost=None
  saved={"schema":6,"vision_model":MODEL,"input_hashes":hashes,
         "raw_visual_landmarks":raw,"source_image_dimensions":dimensions,
         "paid_vision_requests":1,"automatic_paid_retries":0,
         "usage":usage,"observed_cost_usd":cost}
  # Commit even if landmarks fail to pass geometric QA; never repay silently.
  store(checkpoint,saved)
 estimate=calculate(raw,dimensions)
 store(out,{"schema":6,"experiment":cfg["experiment"],
            "vision_model":MODEL,"input_hashes":hashes,
            "source_provenance":{"generation_request":cfg["generation_request"]},
            "source_image_dimensions":dimensions,
            "raw_visual_landmarks":raw,"scale_estimate":estimate,
            "visual_qa":{"status":"unverified","reason":"A source-only estimate does not prove rigging/contact/3D correctness"},
            "usage":saved.get("usage"),"observed_cost_usd":saved.get("observed_cost_usd"),
            "paid_vision_requests":1,"automatic_paid_retries":0})
 print("Blind source ratio",estimate,"OpenRouter cost USD",saved.get("observed_cost_usd"))

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--request",default=DEFAULT)
 p.add_argument("--check",action="store_true")
 a=p.parse_args()
 run(a.request,a.check)
