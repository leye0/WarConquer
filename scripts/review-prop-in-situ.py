#!/usr/bin/env python3
"""Offline-preview-safe LLM vision critique of an *equipped rendered* prop.

The original item generation brief is preserved. Unlike an isolated 2D prop
analysis, vision sees the real 3D grip in Idle/Attack and the source character.
One paid response is checkpointed before validation. No automatic reruns.
"""
from __future__ import annotations
import argparse, base64, hashlib, io, json, math, os
from PIL import Image, ImageOps
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DEFAULT="assets/experiments/props/marches_hache/trellis-v1/grip-render-review-request-v5.json"
ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
MODEL="google/gemini-2.5-flash-lite"
REASONING_EFFORT="low"
MAX_OUTPUT_TOKENS=2200
MAX_IMAGE_EDGE=1152
MAX_TOTAL_IMAGE_BYTES=2500000
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
 "Judge whether the equipment is appropriately proportioned to its wearer "
 "and works ergonomically. Return a "
 "target_length_relative_character_height that YOU choose after evaluating "
 "all images and the original design intent. The geometric solver sets "
 "the prop length to wearer height multiplied by your selected ratio. "
 "Choose the proper proportion from the artwork; do not copy the size "
 "currently visible in the test scene if it appears wrong. "
 "Choose the desired grip fraction measured FROM THE HANDLE BUTT toward the "
 "head (fraction of FULL object axis, approximately 0.04..0.64), "
 "and one semantic head/edge direction from the JSON enumerations. "
 "The 3D solver computes quaternions, DO NOT supply Euler angles. "
 "If a visually credible adjustment cannot be inferred, set confidence low "
 "and explain the missing evidence. "
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
 if cfg["vision_model"]!=MODEL:raise ValueError("Unsupported vision model; change model only in a new versioned request")
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

def vision_text(brief):
 # Intentionally isolated: prior plan ratios and previous model explanations
 # must not contaminate the model's independent scale judgement.
 return ("ORIGINAL GENERATION BRIEF:\\n"+brief+
         "\\nAnalyze the original designed proportions and equipped renders. "
         "Choose the best proportional size, grip and orientation; "
         "ignore game UI overlays and diagnose the visible equipment independently.")

def image(p, arena=False):
 # Modest, deterministic image budget; text and images only, never binary GLB.
 with Image.open(p) as original:
  rgba=original.convert("RGBA")
  background=Image.new("RGBA",rgba.size,"white")
  background.alpha_composite(rgba)
  ready=ImageOps.exif_transpose(background.convert("RGB"))
  # Exclude the Character Lab sidebar/HUD from rendered-scene evidence.
  # No textual feedback, model numbers, or size figures from the UI.
  if arena:
   w,h=ready.size
   ready=ready.crop((round(w*.02),round(h*.15),round(w*.73),round(h*.83)))
  ready.thumbnail((MAX_IMAGE_EDGE,MAX_IMAGE_EDGE),Image.Resampling.LANCZOS)
  output=io.BytesIO()
  ready.save(output,format="JPEG",quality=85,optimize=True)
  payload=output.getvalue()
  if len(payload)>750000:raise ValueError("Too-large image after budgeted resampling")
  return {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+base64.b64encode(payload).decode()}},len(payload)

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
  images={key:image(paths[key],arena=key.startswith("current_render_")) for key in
    ("source_character","source_prop","current_render_idle","current_render_attack")}
  total_bytes=sum(size for _,size in images.values())
  if total_bytes>MAX_TOTAL_IMAGE_BYTES:raise ValueError("Image payload budget exceeded")
  print("Reasoning vision image sizes:",[size for _,size in images.values()],
    "bytes; total",total_bytes,"max output tokens",MAX_OUTPUT_TOKENS)
  payload={
    "model":cfg["vision_model"],"temperature":0,"max_tokens":MAX_OUTPUT_TOKENS,
    "reasoning":{"effort":REASONING_EFFORT,"exclude":True},
    "usage":{"include":True},
    "provider":{"require_parameters":True},
    "response_format":{"type":"json_schema","json_schema":{"name":"equipped_prop_critique","strict":True,"schema":SCHEMA}},
    "messages":[
      {"role":"system","content":PROMPT},
      {"role":"user","content":[
        {"type":"text","text":vision_text(source["prompt"])},
        {"type":"text","text":"IMAGE 1: source unit with originally designed equipment"},images["source_character"][0],
        {"type":"text","text":"IMAGE 2: isolated prop rendering"},images["source_prop"][0],
        {"type":"text","text":"IMAGE 3: live 3D rendered arena IDLE"},images["current_render_idle"][0],
        {"type":"text","text":"IMAGE 4: live 3D rendered arena ATTACK"},images["current_render_attack"][0]
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
  # Capture actual billing data, rather than an estimate from token counts.
  usage=answer.get("usage",{})
  cost=usage.get("cost")
  if cost is not None and (not isinstance(cost,(int,float)) or cost<0):cost=None
  save(checkpoint,{"schema":1,"input_hashes":hashes,"vision_model":cfg["vision_model"],
                   "raw_vision_review":raw,"paid_vision_requests":1,
                   "usage":usage,"observed_cost_usd":cost,
                   "reasoning_effort":REASONING_EFFORT,
                   "max_output_tokens":MAX_OUTPUT_TOKENS,
                   "image_bytes_sent":total_bytes})
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
  "paid_vision_requests":1,"automatic_paid_retries":0,
  "usage":json.loads(checkpoint.read_text()).get("usage",{}),
  "observed_cost_usd":json.loads(checkpoint.read_text()).get("observed_cost_usd")
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
