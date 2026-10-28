#!/usr/bin/env python3
"""Independent, Studio-style labeled bbox audit of vision-grounded GLB grips.

Same contract as leye0/studio/services/create-scene-assets/src/
scene-bbox-detector.js and rain-splash-zone-detector.js: one target image,
exact labels, box_2d [xmin,ymin,xmax,ymax] normalized to 0..1000.
Only the *actual textured GLB view* is sent to the region detector. Geometry
projects existing GLB contact landmarks back to that same 2D image and tests
agreement; geometry NEVER assigns semantic roles by length, axes or silhouette.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import math
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wc_mesh_landmarks", ROOT / "scripts/prop-mesh-landmarks.py")
mesh_vision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesh_vision)
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.5-flash"


def expected_labels(semantic):
    """No source-image coordinates: only the already confirmed semantic roles."""
    labels = {"handle_butt": "Physical bottom tip of handle, not empty space",
        "grip_center": "Actual palm contact on shaft, not blade",
        "working_head": "Metal head body or active working section",
        "functional_edge": "Narrow visible SHARP cutting edge or functional front, not head body"}
    labels.update({g["id"]: g["surface"] for g in semantic["grips"]})
    labels.update({f["id"]: f["function"] for f in semantic["features"]})
    return labels


def parse_response(content):
    if not isinstance(content,str):raise ValueError("Vision model omitted JSON text")
    raw=content.strip()
    if raw.startswith("```"):
        raw=re.sub(r"^```(?:json)?\s*", "", raw, count=1, flags=re.I)
        raw=re.sub(r"\s*```$", "", raw, count=1)
    try:return json.loads(raw)
    except json.JSONDecodeError:
        start=raw.find("{");end=raw.rfind("}")
        if start<0 or end<=start:raise ValueError("No labeled region JSON from vision")
        return json.loads(raw[start:end+1])


def validate_boxes(answer,labels):
    if not isinstance(answer,dict) or not isinstance(answer.get("objects"),dict):
        raise ValueError("Vision must return objects keyed by exact role IDs")
    if set(answer["objects"])!=set(labels):
        raise ValueError("Vision invented or omitted confirmed named regions")
    results={}
    for label,entry in answer["objects"].items():
        if not isinstance(entry,dict) or type(entry.get("visible")) is not bool:
            raise ValueError("Invalid visible flag for "+label)
        if not entry["visible"]:
            results[label]={"visible":False,"box_2d":None,"confidence":0.}
            continue
        box=entry.get("box_2d")
        if (not isinstance(box,list) or len(box)!=4 or
            any(isinstance(x,bool) or not isinstance(x,(int,float)) or
                not math.isfinite(x) or x<0 or x>1000 for x in box) or
            box[2]<=box[0] or box[3]<=box[1]):
            raise ValueError("Invalid box_2d [xmin,ymin,xmax,ymax] for "+label)
        confidence=entry.get("confidence",0.)
        if isinstance(confidence,bool) or not isinstance(confidence,(int,float)) or not 0<=confidence<=1:
            raise ValueError("Invalid confidence for "+label)
        results[label]={"visible":True,"box_2d":box,"confidence":confidence}
    return results


def project_confirmed_point(point,meshes,view):
    """Reproject an existing semantic 3D contact, never invent its role."""
    local=np.array(point["local"],dtype=float)
    target=next((m for m in meshes if m["mesh"]==point["mesh"] and
        m["primitive"]==point["primitive"]),None)
    if target is None:raise ValueError("Previously annotated mesh disappeared")
    idx=int(np.argmin(np.linalg.norm(target["local"]-local,axis=1)))
    if np.linalg.norm(target["local"][idx]-local)>1e-4:
        raise ValueError("Previously annotated vertex disappeared")
    world=target["world"][idx];delta=world-view["center"]
    return [round(float(.5+delta@view["right"]*view["scale"]/mesh_vision.VIEW_SIZE)*1000,1),
        round(float(.5-delta@view["up"]*view["scale"]/mesh_vision.VIEW_SIZE)*1000,1)]


def projected_landmarks(plan,meshes,view):
    points=plan["mesh_landmarks"]["points"]
    located={k:project_confirmed_point(v,meshes,view) for k,v in points.items()}
    located.update({k:project_confirmed_point(v,meshes,view)
        for k,v in plan["mesh_landmarks"].get("grips",{}).items()})
    for name,detail in plan["mesh_landmarks"].get("features",{}).items():
        located[name]=project_confirmed_point(detail["origin"],meshes,view)
        # Both origin and action endpoint are separately tested: the first
        # must be on the named head, the tip on the named functional edge.
    return located


def qa_points(plan,meshes,view,boxes):
    located=projected_landmarks(plan,meshes,view)
    issues=[]
    for label,point in located.items():
        region=boxes.get(label)
        if not region or not region["visible"]:
            issues.append(label+": independently detected region is invisible")
            continue
        x0,y0,x1,y1=region["box_2d"];x,y=point
        if not (x0<=x<=x1 and y0<=y<=y1):
            issues.append(label+": existing GLB landmark is OUTSIDE independently vision-labeled bbox")
    return located,issues


def named_crops(panel,labels,points):
    """Studio's labeled close-ups: independent source-matched image coordinates.

    The already-annotated points select only a REVIEW CAMERA CROP, never a
    functional region. The independent model receives no previous points.
    """
    crops={};size=min(panel.width,180)
    for name in labels:
        px=round(points[name][0]*panel.width/1000)
        py=round(points[name][1]*panel.height/1000)
        left=max(0,min(panel.width-size,px-size//2))
        top=max(0,min(panel.height-size,py-size//2))
        zoom=panel.crop((left,top,left+size,top+size))
        zoom=zoom.resize((720,720),Image.Resampling.LANCZOS)
        output=io.BytesIO();zoom.save(output,format="PNG")
        crops[name]={"left":left,"top":top,"size":size,
            "image":output.getvalue()}
    return crops


def remap_crop_boxes(boxes,crops,panel_size):
    """Map native Studio 0..1000 TARGET-CROP box_2d to its real GLB view."""
    mapped={}
    for name,item in boxes.items():
        if not item["visible"]:
            mapped[name]=dict(item);continue
        crop=crops[name]
        x0,y0,x1,y1=item["box_2d"]
        box=[(crop["left"]+x0*crop["size"]/1000)/panel_size*1000,
             (crop["top"]+y0*crop["size"]/1000)/panel_size*1000,
             (crop["left"]+x1*crop["size"]/1000)/panel_size*1000,
             (crop["top"]+y1*crop["size"]/1000)/panel_size*1000]
        mapped[name]={**item,"box_2d":[round(x,1) for x in box]}
    return mapped


def render_overlay(panel,boxes,points):
    out=panel.copy().convert("RGB");draw=ImageDraw.Draw(out)
    for name,item in boxes.items():
        if not item["visible"]:continue
        x0,y0,x1,y1=[v*panel.width/1000 for v in item["box_2d"]]
        color=(224,64,76) if "edge" in name or "head" in name else (20,120,230)
        draw.rectangle((x0,y0,x1,y1),outline=color,width=3)
        draw.text((x0,max(1,y0-12)),name,fill=color)
    for name,(x,y) in points.items():
        px=x*panel.width/1000;py=y*panel.height/1000
        draw.ellipse((px-4,py-4,px+4,py+4),fill=(18,151,89),outline="white",width=1)
    stream=io.BytesIO();out.save(stream,format="PNG");return stream.getvalue()


def audit(plan_path,pass_id,model):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,48}",pass_id):
        raise ValueError("Immutable Studio-style vision pass ID required")
    if not re.fullmatch(r"[a-zA-Z0-9_./:-]{3,120}",model):
        raise ValueError("Invalid OpenRouter model")
    plan=json.loads(plan_path.read_text())
    landmark=plan.get("mesh_landmarks",{})
    if landmark.get("schema")!=1 or "interaction_sha256" not in landmark:
        raise ValueError("Audit requires previous validated named GLB landmarks")
    semantic,semantic_hash=mesh_vision.confirmed_interaction(plan_path,plan)
    if semantic_hash!=landmark["interaction_sha256"]:
        raise ValueError("Existing semantic 3D contact is stale")
    meshes=mesh_vision.glb_geometry(ROOT/plan["inputs"]["object_glb"])
    rendered,views=mesh_vision.make_views(meshes)
    selected=int(landmark["view"]);width=mesh_vision.VIEW_SIZE
    panel=Image.open(io.BytesIO(rendered)).crop(((selected%2)*width,(selected//2)*width,
        (selected%2+1)*width,(selected//2+1)*width))
    labels=expected_labels(semantic)
    prior_points=projected_landmarks(plan,meshes,views[selected])
    crops=named_crops(panel,labels,prior_points)
    prompt=("Inspect each of the following INDEPENDENT, enlarged TARGET CROPS "
        "of the ACTUAL textured 3D GLB. Each crop is explicitly paired with "
        "ONE exact label in the following messages, as in Studio's labeled "
        "contact-sheet crop protocol. "
        "Independently LOCATE every requested functional region from visible pixels. "
        "Return JSON only: {\"objects\":{\"<exact label>\":{\"visible\":true,"
        "\"box_2d\":[xmin,ymin,xmax,ymax],\"confidence\":0.9}}}. "
        "Use each exact label below, no invented labels. box_2d is an integer "
        "[xmin,ymin,xmax,ymax] normalized to 0..1000 of THAT LABEL'S OWN "
        "TARGET CROP IMAGE, NEVER the full GLB view or all-image mosaic, "
        "as in Studio's scene-bbox-detector and rain-splash-zone-detector. "
        "Give a TIGHT rectangle around the named VISIBLE physical part, not "
        "background. A sharp blade's functional_edge is the visible thin "
        "sharpened OUTER cutting strip, not the whole blade or poll. "
        "If no visually supported region can be found, visible=false, "
        "omit box_2d and set confidence=0. "
        "No other illustrations, source-image coordinates or old GLB point "
        "annotations are supplied; do NOT infer them. REQUESTED LABELS:\n"+
        json.dumps(labels,ensure_ascii=False,indent=2))
    content=[{"type":"text","text":prompt}]
    base="studio-"+pass_id
    for label,crop in crops.items():
        content.append({"type":"text","text":"TARGET CROP for EXACT label " +
            label + ": " + labels[label] +
            ". Report box_2d relative to THIS IMAGE only."})
        content.append(mesh_vision.image_part(crop["image"]))
        (plan_path.parent/("vision-input-glb-"+base+"-"+label+".png")).write_bytes(crop["image"])
    signature=hashlib.sha256(json.dumps({"model":model,"pass_id":pass_id,
        "image_sha":{k:hashlib.sha256(v["image"]).hexdigest() for k,v in crops.items()},
        "semantic_sha":semantic_hash,
        "landmark_sha":hashlib.sha256(json.dumps(landmark,sort_keys=True).encode()).hexdigest(),
        "prompt":prompt},sort_keys=True).encode()).hexdigest()
    folder=plan_path.parent/"vision-region-receipts";folder.mkdir(parents=True,exist_ok=True)
    receipt=folder/(base+"-"+signature+".json")
    if receipt.exists():
        doc=json.loads(receipt.read_text())
        if doc.get("signature")!=signature or "answer" not in doc:
            raise ValueError("Previous Studio region request failed or is uncertain; use distinct pass ID")
        answer=doc["answer"]
    else:
        key=os.environ.get("OPENROUTER_API_KEY","").strip()
        if not key:raise RuntimeError("OPENROUTER_API_KEY required in Actions")
        receipt.write_text(json.dumps({"signature":signature,"model":model,
            "status":"submission-outcome-unknown"},indent=2)+"\n")
        payload={"model":model,"temperature":0,
            "provider":{"sort":"price","max_price":{"prompt":3,"completion":3}},
            "messages":[{"role":"user","content":content}]}
        request=Request(ENDPOINT,data=json.dumps(payload).encode(),method="POST",
            headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
                "X-OpenRouter-Title":"WarConquer Studio-style 3D grounding"})
        with urlopen(request,timeout=150) as response:
            answer=parse_response(json.loads(response.read(200000))["choices"][0]["message"]["content"])
        receipt.write_text(json.dumps({"signature":signature,"model":model,
            "answer":answer},ensure_ascii=False,indent=2)+"\n")
    crop_boxes=validate_boxes(answer,labels)
    boxes=remap_crop_boxes(crop_boxes,crops,width)
    existing_points,issues=qa_points(plan,meshes,views[selected],boxes)
    for label,entry in boxes.items():
        if entry["visible"] and entry["confidence"]<.75:
            issues.append(label+": independent bounding box has low vision confidence")
    overlay=plan_path.parent/("vision-regions-"+base+".png")
    overlay.write_bytes(render_overlay(panel,boxes,existing_points))
    report={"schema":1,"model":model,"pass_id":pass_id,"glb_view":selected,
        "bbox_convention":"xyxy_normalized_1000","receipt":str(receipt.relative_to(ROOT)),
        "overlay":str(overlay.relative_to(ROOT)),"boxes":boxes,
        "boxes_within_labeled_crops_1000":crop_boxes,
        "original_point_positions_1000":existing_points,
        "status":"confirmed" if not issues else "rejected","issues":issues}
    report_path=plan_path.parent/("vision-region-review-"+base+".json")
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    plan["mesh_region_review"]={"schema":1,"status":report["status"],
        "glb_sha256":landmark["glb_sha256"],
        "interaction_sha256":semantic_hash,"model":model,
        "bbox_convention":"xyxy_normalized_1000",
        "review":str(report_path.relative_to(ROOT)),
        "overlay":str(overlay.relative_to(ROOT))}
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n")
    if issues:raise ValueError("Independent Studio-style vision disagrees: "+"; ".join(issues))
    print("PASS: Studio-style labeled physical regions corroborate GLB contacts",report_path.relative_to(ROOT))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",required=True)
    parser.add_argument("--pass-id",default="studio_flash_audit")
    parser.add_argument("--model",default=MODEL)
    args=parser.parse_args()
    target=(ROOT/args.plan).resolve()
    if not target.is_file() or not target.is_relative_to(ROOT):
        raise ValueError("Audited plan must be a canonical repository file")
    audit(target,args.pass_id,args.model)
