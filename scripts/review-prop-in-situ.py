#!/usr/bin/env python3
"""Offline-preview-safe LLM vision critique of an *equipped rendered* prop.

The original item generation brief is preserved. Unlike an isolated 2D prop
analysis, vision sees the real 3D grip in Idle/Attack and the source character.
One paid response is checkpointed before validation. No automatic reruns.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, math, os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DEFAULT="assets/experiments/props/marches_hache/trellis-v1/grip-render-review-request.json"
ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
REQUIRED={"schema","experiment","generation_request","source_character",
          "source_prop","current_render_idle","current_render_attack",
          "current_plan","semantic_plan","output_path","vision_model",
          "maximum_paid_requests","automatic_paid_retries"}
PROPS={
  "target_length_relative_character_height":{"type":"number"},
  "grip_fraction_from_butt":{"type":"number"},
  "head_direction":{"type":"string","enum":["toward_elbow","toward_fingers","up","down","forward","backward"]},
  "edge_direction":{"type":"string","enum":["forward","backward","outward","inward"]},
  "change_needed":{"type":"boolean"},
  "confidence":{"type":"number"},
  "visual_diagnosis":{"type":"string"},
  "proposed_correction_reason":{"type":"string"}
}
SCHEMA={"type":"object","properties":PROPS,
        "required":list(PROPS),"additionalProperties":False}
PROMPT=(
 "You are the art director and technical weapon-grip specialist of the "
 "WarConquer 3D game. This object was generated FROM THE ATTACHED ORIGINAL "
 "DESIGN BRIEF; its identity, construction and real intended use are already "
 "known. Do not re-identify it from scratch. Observe image 1 (the original "
 "unit concept with equipment), image 2 (original isolated equipment), "
 "image 3 (the actual Babylon GLB scene with equipment attached during idle), "
 "and image 4 (the real Babylon axe attack). Judge the CURRENT ON-SCREEN "
 "RELATIVE SIZE of the equipped prop versus the wearer, handle contact, "
 "orientation of the head/blade, and practical physical plausibility. "
 "You are correcting a real rendered scene, NOT proposing a textbook weapon "
 "size and NOT accepting the previous model's ratio by default. Return a "
 "target_length_relative_character_height that YOU choose after evaluating "
 "both images and original design intent. Character mesh is rendered at "
 "exactly 1.9 world units tall; the geometric solver sets prop length to "
 "character_height * your target ratio (not to a fixed pixel size). "
 "Choose the desired grip fraction measured FROM THE HANDLE BUTT toward the "
 "head (fraction of FULL object axis, approximately 0.04..0.64), "
 "and one semantic head/edge direction from the JSON enumerations. "
 "The 3D solver computes quaternions, DO NOT supply Euler angles. "
 "If a visually credible adjustment cannot be inferred, set confidence low "
 "and explain the missing evidence. Do not blindly echo old values. "
 "The purpose is a functional believable weapon resembling the unit concept. "
 "Ground the diagnosis in what is visibly wrong/right in the render."
)

def local(rel):
 if not isinstance(rel,str) or not rel or rel.startswith("/"):
  raise ValueError("Unsafe relative asset path")
 p=(ROOT/rel).resolve()
 if not p.is_relative_to(ROOT) or not p.is_file():raise ValueError("Missing asset "+rel)
 return p

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_suffix(".tmp")
 t.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n")
 t.replace(p)

def prepare(req):
 cfg=json.loads(local(req).read_text())
 if set(cfg)!=REQUIRED or cfg["schema"]!=1 or cfg["maximum_paid_requests"]!=1 or cfg["automatic_paid_retries"]!=0:
  raise ValueError("Unexpected request; no extra paid calls")
 if cfg["vision_model"]!="google/gemini-2.5-flash-lite":raise ValueError("Unsupported vision model")
 paths={k:local(cfg[k]) for k in REQUIRED-{"schema","experiment","output_path","vision_model","maximum_paid_requests","automatic_paid_retries"}}
 source=json.loads(paths["generation_request"].read_text())
 prior=json.loads(paths["current_plan"].read_text())
 semantic=json.loads(paths["semantic_plan"].read_text())
 if source["output"]!=cfg["source_prop"] or cfg["source_character"] not in source["references"]:
  raise ValueError("Original generation prompt is unrelated to this prop")
 if prior.get("schema")!=2 or semantic.get("schema")!=3:raise ValueError("Unsupported plan lineage")
 if prior["inputs"]["object_glb"]!=semantic["inputs"]["object_glb"]:
  raise ValueError("Misidentified 3D object")
 out=(ROOT/cfg["output_path"]).resolve()
 if not out.is_relative_to(ROOT) or out.suffix!=".json":raise ValueError("Invalid output")
 hashes={key+"_sha256":digest(path) for key,path in paths.items()}
 return cfg,paths,source,prior,semantic,out,hashes

def valid(raw):
 if not isinstance(raw,dict) or set(raw)!=set(PROPS):raise ValueError("Incomplete vision feedback")
 for field in ("target_length_relative_character_height","grip_fraction_from_butt","confidence"):
  n=raw[field]
  if isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n):
   raise ValueError("Invalid vision numeric "+field)
 if not .13<=raw["target_length_relative_character_height"]<=1.85:
  raise ValueError("Implausible relative scale; human review, no silent clamp")
 if not .04<raw["grip_fraction_from_butt"]<.64 or not 0<=raw["confidence"]<=1:
  raise ValueError("Invalid grip/confidence")
 if raw["head_direction"] not in PROPS["head_direction"]["enum"] or raw["edge_direction"] not in PROPS["edge_direction"]["enum"]:
  raise ValueError("Invalid 3D semantics")
 if not isinstance(raw["change_needed"],bool):
  raise ValueError("Invalid visual verdict")
 for field in ("visual_diagnosis","proposed_correction_reason"):
  if not isinstance(raw[field],str) or not 35<=len(raw[field])<=1200:
   raise ValueError("Insufficient visual reasoning")
 if raw["confidence"]<.65:raise ValueError("Vision not confident enough for a 3D preview")
 return raw

def image(p):
 mime="image/png" if p.suffix.lower()==".png" else "image/jpeg"
 return {"type":"image_url","image_url":{"url":"data:"+mime+";base64,"+base64.b64encode(p.read_bytes()).decode()}}

def run(request,check):
 cfg,paths,source,current,semantic,out,hashes=prepare(request)
 checkpoint=out.with_name(out.stem+"-response.json")
 if out.is_file():
  saved=json.loads(out.read_text())
  if saved.get("input_hashes")!=hashes or saved.get("vision_model")!=cfg["vision_model"]:
   raise ValueError("Stored review has different source assets; create new experiment")
  valid(saved["vision_review"])
  print("Reused pinned in-situ vision review (zero paid calls)")
  return
 if check:
  print("No accepted 3D visual review yet")
  return
 if checkpoint.is_file():
  old=json.loads(checkpoint.read_text())
  if old.get("input_hashes")!=hashes or old.get("vision_model")!=cfg["vision_model"]:
   raise ValueError("Paid checkpoint cannot be reused for changed images")
  raw=old["raw_vision_review"]
  print("Resuming checkpointed review, no paid call")
 else:
  key=os.environ.get("OPENROUTER_API_KEY","").strip()
  if not key:raise ValueError("Missing OPENROUTER_API_KEY")
  old=current["specifications"]
  payload={
    "model":cfg["vision_model"],"temperature":0,"max_tokens":1100,
    "provider":{"require_parameters":True},
    "response_format":{"type":"json_schema","json_schema":{"name":"equipped_prop_critique","strict":True,"schema":SCHEMA}},
    "messages":[
      {"role":"system","content":PROMPT},
      {"role":"user","content":[
        {"type":"text","text":"ORIGINAL GENERATION BRIEF:\n"+source["prompt"]+
         "\nCURRENT ACTUAL RENDERED LENGTH/CHARACTER HEIGHT: "+str(old["length_relative_character_height"])+
         "\nPrevious vision analysis (may be wrong): "+json.dumps(semantic["specifications"],ensure_ascii=False)+
         "\nReturn your own corrected scale and orientation from visual evidence."},
        {"type":"text","text":"IMAGE 1: source unit with originally designed equipment"},image(paths["source_character"]),
        {"type":"text","text":"IMAGE 2: isolated prop rendering"},image(paths["source_prop"]),
        {"type":"text","text":"IMAGE 3: live 3D rendered arena IDLE"},image(paths["current_render_idle"]),
        {"type":"text","text":"IMAGE 4: live 3D rendered arena ATTACK"},image(paths["current_render_attack"])
      ]}
    ]
  }
  req=Request(ENDPOINT,data=json.dumps(payload).encode(),method="POST",
              headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
                       "HTTP-Referer":"https://github.com/leye0/WarConquer",
                       "X-Title":"WarConquer in-situ vision equipment critique"})
  with urlopen(req,timeout=150) as response:
   answer=json.loads(response.read(230000))
  message=(answer.get("choices") or [{}])[0].get("message",{}).get("content")
  if not isinstance(message,str):raise ValueError("Vision provider did not return structured response")
  raw=json.loads(message)
  save(checkpoint,{"schema":1,"input_hashes":hashes,"vision_model":cfg["vision_model"],
                   "raw_vision_review":raw,"paid_vision_requests":1})
 validated=valid(raw)
 new=dict(semantic["specifications"])
 new["length_relative_character_height"]=validated["target_length_relative_character_height"]
 new["head_direction"]=validated["head_direction"]
 new["edge_direction"]=validated["edge_direction"]
 # LLM updates 3D grip position, the geometry fitter still computes the mesh frame.
 derived=dict(semantic["derived_image_geometry"])
 derived["grip_fraction_from_butt"]=validated["grip_fraction_from_butt"]
 plan={
  "schema":4,"experiment":cfg["experiment"],"vision_model":cfg["vision_model"],
  "inputs":semantic["inputs"],"input_hashes":hashes,
  "source_provenance":semantic["source_provenance"],
  "specifications":new,"derived_image_geometry":derived,
  "vision_review":validated,
  # Preview will be rendered and independently checked before promotion.
  "visual_qa":{"status":"candidate","reason":"LLM viewed live Idle and Attack; not yet independently checked after applying new transform"},
  "paid_vision_requests":1,"automatic_paid_retries":0
 }
 save(out,plan)
 print("LLM-chosen new equipped object/body ratio:",new["length_relative_character_height"],
       "vs old:",current["specifications"]["length_relative_character_height"])

if __name__=="__main__":
 a=argparse.ArgumentParser()
 a.add_argument("--request",default=DEFAULT)
 a.add_argument("--check",action="store_true")
 z=a.parse_args()
 run(z.request,z.check)
