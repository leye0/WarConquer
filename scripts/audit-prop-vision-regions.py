#!/usr/bin/env python3
"""Multi-view region annotation and independent overlay review of real GLBs.

Default schema 2 uses complete views and semantic IDs, without old anchors.
The explicit --legacy-crops option preserves historical schema-1 diagnostics.

Builds on leye0/studio/services/create-scene-assets/src/
scene-bbox-detector.js and rain-splash-zone-detector.js: labeled target crops,
exact semantic IDs, box_2d normalized to 0..1000. On the wire we use each
vision MODEL's documented native coordinate order, converting to XYXY after.
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
from urllib.error import HTTPError

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wc_mesh_landmarks", ROOT / "scripts/prop-mesh-landmarks.py")
mesh_vision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesh_vision)
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.5-flash"


def native_box_order(model):
    """Match the producer's learned grounding convention, not a house style.

    Gemini's official image-understanding docs: [ymin,xmin,ymax,xmax].
    Qwen3-VL's official 2D grounding format: [xmin,ymin,xmax,ymax].
    Explicit support is required; never silently transpose an unknown model.
    """
    if model.startswith("google/gemini-"):
        return "ymin_xmin_ymax_xmax"
    if model.startswith("qwen/qwen3-vl-"):
        return "xmin_ymin_xmax_ymax"
    raise ValueError("Unverified model-specific native box ordering: "+model)


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


def validate_boxes(answer,labels,order="xmin_ymin_xmax_ymax"):
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
            raise ValueError("Invalid native box_2d for "+label)
        confidence=entry.get("confidence",0.)
        if isinstance(confidence,bool) or not isinstance(confidence,(int,float)) or not 0<=confidence<=1:
            raise ValueError("Invalid confidence for "+label)
        if order=="ymin_xmin_ymax_xmax":
            box=[box[1],box[0],box[3],box[2]]
        elif order!="xmin_ymin_xmax_ymax":
            raise ValueError("Unrecognized native bbox ordering")
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



def visible_glb_region_issues(boxes, view):
    """Reject labeled boxes containing no actually rasterized GLB surface.

    Uses the same depth buffer as the exact textured view submitted to vision.
    This is only a geometric visibility gate: a different model must still
    verify the region's semantic identity and the correct side of the mesh.
    """
    mask = view.get("surface_mask")
    if not isinstance(mask, np.ndarray) or mask.shape != (
            mesh_vision.VIEW_SIZE, mesh_vision.VIEW_SIZE):
        raise ValueError("Rendered GLB surface visibility mask is missing")
    size = mesh_vision.VIEW_SIZE
    issues = []
    for label, entry in boxes.items():
        if not entry["visible"]:
            continue
        x0, y0, x1, y1 = entry["box_2d"]
        left = max(0, min(size, math.floor(x0 * size / 1000)))
        top = max(0, min(size, math.floor(y0 * size / 1000)))
        right = max(0, min(size, math.ceil(x1 * size / 1000)))
        bottom = max(0, min(size, math.ceil(y1 * size / 1000)))
        if (right <= left or bottom <= top or
                not np.any(mask[top:bottom, left:right])):
            issues.append(label + ": labeled bbox has no visible GLB surface pixels")
    return issues



def reconcile_physical_regions(plan, meshes, view, boxes):
    """Historical vertex snapping is forbidden until triangle patches exist."""
    raise ValueError(
        "Automatic bbox-center/nearest-vertex repair is disabled; "
        "B5 requires a vision-labeled visible triangle surface")



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
    order=native_box_order(model)
    prior_points=projected_landmarks(plan,meshes,views[selected])
    crops=named_crops(panel,labels,prior_points)
    prompt=("Inspect each of the following INDEPENDENT, enlarged TARGET CROPS "
        "of the ACTUAL textured 3D GLB. Each crop is explicitly paired with "
        "ONE exact label in the following messages, as in Studio's labeled "
        "contact-sheet crop protocol. "
        "Independently LOCATE every requested functional region from visible pixels. "
        "Return JSON only: {\"objects\":{\"<exact label>\":{\"visible\":true,"
        "\"box_2d\":["+order.replace("_",", ")+"],\"confidence\":0.9}}}. "
        "Use each exact label below, no invented labels. box_2d MUST use "
        "the VISION MODEL'S NATIVE coordinate order ["+order.replace("_",", ")+"], "
        "each value an integer normalized to 0..1000 of THAT LABEL'S OWN "
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
    crop_boxes=validate_boxes(answer,labels,order)
    boxes=remap_crop_boxes(crop_boxes,crops,width)
    # Do not silently shift any semantic contact to make a rectangle pass.
    # Historic vertex anchors are diagnostic only until B5 triangles exist.
    existing_points,issues=qa_points(plan,meshes,views[selected],boxes)
    issues.extend(visible_glb_region_issues(boxes,views[selected]))
    for label,entry in boxes.items():
        if entry["visible"] and entry["confidence"]<.75:
            issues.append(label+": independent bounding box has low vision confidence")
    overlay=plan_path.parent/("vision-regions-"+base+".png")
    overlay.write_bytes(render_overlay(panel,boxes,existing_points))
    report={"schema":1,"model":model,"pass_id":pass_id,"glb_view":selected,
        "bbox_convention":"xyxy_normalized_1000",
        "native_bbox_convention":order+"_normalized_1000",
        "raw_native_boxes":answer["objects"],
        "receipt":str(receipt.relative_to(ROOT)),
        "overlay":str(overlay.relative_to(ROOT)),"boxes":boxes,
        "boxes_within_labeled_crops_1000":crop_boxes,
        "physical_region_reconciliations":{},
        "landmark_repair":"disabled_pending_visible_triangle_patches",
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


# Region schema 2 deliberately does not overwrite schema-1 vertex anchors.
# B2-B4 establish image-space evidence; B5 must consume it without snapping.
REGION_PROMPT_VERSION = 3


def region_labels(semantic):
    labels = {g['id']: {'role': 'grasp_region', 'description': g['surface']}
              for g in semantic['grips']}
    for feature in semantic['features']:
        if feature['id'] in labels:
            raise ValueError('Duplicate semantic ID across grips/features')
        labels[feature['id']] = {'role': 'functional_region',
            'description': feature['function'],
            'direction_semantics': feature['direction_semantics']}
    if len(labels) != len(semantic['grips']) + len(semantic['features']):
        raise ValueError('Duplicate semantic IDs')
    return labels


def region_prompt(labels, order):
    return (
        'Locate the supplied semantic regions on FOUR complete views of the SAME '
        'actual textured GLB. Each image is a separate VIEW 0..3. Use ONLY the '
        'supplied IDs and descriptions; ID spelling does not redefine its function. '
        'Identify each region anew from visible material, boundaries and function, '
        'not from its screen position or length. Distinct grasp regions must bound '
        'their distinct usable portions, not the entire shared shaft or body. '
        'A functional region encloses the named EFFECT-producing surface, not the '
        'whole supporting body. For a signed direction, locate origin on its '
        'supporting material and direction_tip on the named functional surface; '
        'the origin may be outside the functional region. Both points must touch '
        'visible object pixels. Do not copy coordinates between views. '
        'Return JSON {"views":[{"view":0,"objects":{"<id>":'
        '{"visible":true,"box_2d":[a,b,c,d],"confidence":0.9,'
        '"evidence":"visible physical identity and boundaries",'
        '"origin":[x,y],"direction_tip":[x,y]}}}, ...]}. '
        'Include each ID in EVERY view. box_2d order is ' + order +
        '; all coordinates are normalized 0..1000 WITHIN that single full image, '
        'including margins. Points ALWAYS use [x,y]. Only functional regions '
        'need origin/direction_tip. For occluded, absent or ambiguous parts return '
        'visible=false, confidence=0 and evidence explaining which additional view '
        'would resolve it; omit box and points. Never invent a hidden location. '
        'Grasp intervals on a uniform material can remain ambiguous: report it. '
        'REQUESTED ROLES:\n' + json.dumps(labels, ensure_ascii=False))


def single_view_prompt(labels, order):
    return (
        'You are a precise visual grounding annotator. Inspect the ONE supplied '
        'image of an actual textured 3D object. Locate only the physical regions '
        'described below. The image includes a coordinate grid with 0.1 increments. '
        'Read x horizontally from left to right and y vertically from top to bottom. '
        'Return coordinates normalized 0..1000 over this ENTIRE image, margins included. '
        'Do not use the textual role name as a location hint: inspect the pixels. '
        'First identify the material and visible boundary, then place a TIGHT box. '
        'For a grasp interval choose the described distinct material/segment only; '
        'never the entire shaft and never beyond its physical end. '
        'For a functional surface choose the actual narrow effect-producing '
        'surface described, not its supporting body. A body, a face and its outer '
        'edge are different regions. State what you actually see. '
        'For functional regions additionally mark origin on the supporting material '
        'and direction_tip ON the effect-producing surface. Both points must land '
        'on visible object pixels; the origin may be outside the functional region. '
        'Do not point into empty space to illustrate a direction. '
        'For an edge-on, hidden or ambiguous surface use visible=false with a '
        'concrete reason; do not invent coordinates to complete the answer. '
        'Return ONE JSON object with an objects map keyed by exactly the supplied IDs. '
        'Each entry: {"visible":true,"box_2d":[xmin,ymin,xmax,ymax],'
        '"confidence":0.9,"evidence":"specific visible boundary/material"}. '
        'Only functional regions add "origin":[x,y],"direction_tip":[x,y]. '
        'Invisible entries: {"visible":false,"confidence":0,"evidence":"why hidden"}. '
        'box_2d order: ' + order + '. Points are always [x,y]. '
        'Before returning, visually check every coordinate against the grid and '
        'the object boundary. Do not claim visibility from an assumed shape. ROLES:\n' +
        json.dumps(labels, ensure_ascii=False))


def annotate_individual_views(folder, model, labels, order, images, provenance, allow_paid):
    rows = []; receipts = []
    for i, image in enumerate(images):
        # No other view or previous response enters this request. The camera ID
        # is supplied by the caller, not inferred/renamed by the model.
        answer, receipt = region_request(folder, f'annotation-view-{i}', model,
            single_view_prompt(labels, order), [image], provenance, allow_paid)
        if isinstance(answer, dict) and set(answer) == set(labels):
            answer = {'objects': answer}  # Only an omitted envelope; IDs remain exact.
        if not isinstance(answer, dict) or set(answer) != {'objects'}:
            raise ValueError('Single-view response must contain exactly objects')
        rows.append({'view': i, 'objects': answer['objects']})
        receipts.append(receipt)
    return {'views': rows}, receipts


def validate_multiview(answer, labels, views, order):
    # Some providers omit only the outer envelope. Preserve raw receipts and
    # validate the exact same four rows/IDs; never repair semantic coordinates.
    records = answer if isinstance(answer, list) else (
        answer.get('views') if isinstance(answer, dict) else None)
    if (not isinstance(records, list) or len(records) != 4 or
            any(not isinstance(r, dict) or type(r.get('view')) is not int for r in records) or
            {r['view'] for r in records} != set(range(4))):
        raise ValueError('Exactly four distinct view IDs required')
    result = []
    for record in sorted(records, key=lambda r: r['view']):
        boxes = validate_boxes(record, labels, order)
        issues = visible_glb_region_issues(boxes, views[record['view']])
        for label, box in boxes.items():
            raw = record['objects'][label]
            evidence = raw.get('evidence')
            if not isinstance(evidence, str) or len(evidence.strip()) < 10:
                raise ValueError('Missing visibility/identity evidence: ' + label)
            box['evidence'] = evidence
            if not box['visible']:
                continue
            if box['confidence'] < .75:
                issues.append(label + ': low confidence')
            if labels[label]['role'] == 'functional_region':
                for field in ('origin', 'direction_tip'):
                    point = raw.get(field)
                    if (not isinstance(point, list) or len(point) != 2 or
                            any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                                not math.isfinite(v) or not 0 <= v < 1000 for v in point)):
                        raise ValueError('Invalid signed direction ' + label + '.' + field)
                    box[field] = point
                    x, y = (int(v * mesh_vision.VIEW_SIZE / 1000) for v in point)
                    if not views[record['view']]['surface_mask'][y, x]:
                        issues.append(label + ': ' + field + ' is on background')
                if math.dist(box['origin'], box['direction_tip']) < 1:
                    issues.append(label + ': signed direction collapses')
                x, y = box['direction_tip']; x0, y0, x1, y1 = box['box_2d']
                if not (x0 <= x <= x1 and y0 <= y <= y1):
                    issues.append(label + ': direction tip outside functional region')
        result.append({'view': record['view'], 'objects': boxes, 'issues': issues})
    return result


def review_prompt(labels):
    return (
        'Independently review the SAME physical part IDs across four actual GLB '
        'views. For each VIEW you receive the untouched image and an overlay. '
        'Inspect every rectangle against visible pixels and the supplied role '
        'description, NOT merely its label. The annotations may be WRONG even when '
        'confident and neatly drawn. Explicitly reject a box on the wrong end, '
        'a copied position on a mirrored view, a floating arrow or a box extending '
        'beyond the object. Explain the actual pixels you see; never repeat the '
        'annotation as evidence. Distinct grasp portions must not be '
        'swapped or merged. Inspect signed arrows: origin -> tip must follow the '
        'supplied physical meaning; an active surface is not the entire body. '
        'Compare the SAME ID across views and report contradictions, occlusion, '
        'depth ambiguity or missing surfaces. Do not endorse unseen surfaces. '
        'Return JSON {"views":[{"view":0,"objects":{"<id>":'
        '{"verdict":"confirmed|rejected|unresolved","reason":"visual evidence"}}}, ...],'
        '"cross_view":{"<id>":{"verdict":"confirmed|rejected|unresolved",'
        '"reason":"identity and direction across views",'
        '"additional_views":["needed camera or detail, if any"]}}}. '
        'Exactly four views and every ID in each view and cross_view are required. '
        'Return confirmed across views only with at least TWO useful views of '
        'the same region and consistent signed directions. ROLES:\n' +
        json.dumps(labels, ensure_ascii=False))


def reviewed_regions(records, review, labels):
    rows = review.get('views') if isinstance(review, dict) else None
    if (not isinstance(rows, list) or len(rows) != 4 or
            any(not isinstance(r, dict) or type(r.get('view')) is not int for r in rows) or
            {r['view'] for r in rows} != set(range(4)) or
            not isinstance(review.get('cross_view'), dict) or
            set(review['cross_view']) != set(labels)):
        raise ValueError('Incomplete independent multi-view review')
    def check(entries):
        if not isinstance(entries, dict) or set(entries) != set(labels):
            raise ValueError('Reviewer omitted or invented region IDs')
        for item in entries.values():
            if (not isinstance(item, dict) or item.get('verdict') not in
                    ('confirmed', 'rejected', 'unresolved') or
                    not isinstance(item.get('reason'), str) or len(item['reason'].strip()) < 10):
                raise ValueError('Invalid independent region verdict')
    by_view = {r['view']: r for r in rows}
    for row in rows: check(row.get('objects'))
    check(review['cross_view'])
    issues = []
    for record in records:
        issues.extend('view ' + str(record['view']) + ': ' + s for s in record['issues'])
    coverage = {}
    for label in labels:
        accepted = []
        for record in records:
            region = record['objects'][label]
            verdict = by_view[record['view']]['objects'][label]
            if verdict['verdict'] == 'rejected':
                issues.append(f'view {record["view"]}: {label}: ' + verdict['reason'])
            if (region['visible'] and region['confidence'] >= .75 and
                    not any(s.startswith(label + ':') for s in record['issues']) and
                    verdict['verdict'] == 'confirmed'):
                accepted.append(record['view'])
        coverage[label] = accepted
        cross = review['cross_view'][label]
        if (not isinstance(cross.get('additional_views'), list) or
                any(not isinstance(v, str) for v in cross['additional_views'])):
            raise ValueError('Missing explicit additional-view requests')
        if len(accepted) < 2:
            issues.append(label + ': fewer than two independently confirmed visible views')
        if cross['verdict'] != 'confirmed' or cross['additional_views']:
            issues.append(label + ': cross-view unresolved: ' + cross['reason'])
    return coverage, issues


def region_request(folder, stage, model, prompt, images, provenance, allow_paid, request_options=None):
    """One immutable request per stage; cache raw provider output before parsing."""
    signature_data = {'schema': REGION_PROMPT_VERSION, 'stage': stage, 'model': model,
        'prompt': prompt, 'images': [{'label': label,
            'sha256': hashlib.sha256(data).hexdigest()} for label, data in images],
        'provenance': provenance}
    if request_options:
        signature_data['request_options'] = request_options
    signature = hashlib.sha256(json.dumps(signature_data, sort_keys=True).encode()).hexdigest()
    receipt = folder / (stage + '-' + signature + '.json')
    if receipt.exists():
        document = json.loads(receipt.read_text())
        if document.get('signature') != signature or 'response' not in document:
            raise ValueError('Previous request outcome unknown; no blind retry')
        response = document['response']
    else:
        if not allow_paid:
            raise ValueError('No cached receipt; explicit --allow-paid required')
        key = os.environ.get('OPENROUTER_API_KEY', '').strip()
        if not key: raise RuntimeError('OPENROUTER_API_KEY required in Actions')
        content = [{'type': 'text', 'text': prompt}]
        for label, data in images:
            content.extend([{'type': 'text', 'text': label}, mesh_vision.image_part(data)])
        payload = {'model': model, 'temperature': 0, 'max_tokens': 6000,
            'provider': {'sort': 'price', 'max_price': {'prompt': 3, 'completion': 3}},
            'messages': [{'role': 'user', 'content': content}]}
        payload.update(request_options or {})
        document = {**signature_data, 'signature': signature, 'status': 'submission-outcome-unknown'}
        receipt.write_text(json.dumps(document, indent=2) + '\n')
        request = Request(ENDPOINT, data=json.dumps(payload).encode(), method='POST',
            headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=150) as response_stream:
                response = json.loads(response_stream.read(400000))
        except HTTPError as error:
            document.update(status='http_error', http_status=error.code,
                            error_body=error.read(400000).decode('utf-8', errors='replace'))
            receipt.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
            raise
        document.update(status='received', response=response, usage=response.get('usage'))
        receipt.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
    choice = response['choices'][0]
    if choice.get('finish_reason') == 'length':
        raise ValueError('Provider exhausted output budget before complete region JSON')
    return parse_response(choice['message']['content']), receipt.name


def audit_multiview(plan_path, pass_id, model, reviewer, allow_paid=False, prepare_only=False):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,48}', pass_id):
        raise ValueError('Immutable region pass ID required')
    if reviewer == model: raise ValueError('Region reviewer must use a different model')
    order = native_box_order(model)
    plan = json.loads(plan_path.read_text())
    semantic, semantic_hash = mesh_vision.confirmed_interaction(plan_path, plan)
    if semantic is None: raise ValueError('Confirmed semantic contract required')
    glb = (ROOT / plan['inputs']['object_glb']).resolve()
    if not glb.is_relative_to(ROOT): raise ValueError('GLB outside repository')
    digest = hashlib.sha256(glb.read_bytes()).hexdigest()
    if digest != plan['input_hashes']['prop_glb_sha256']:
        raise ValueError('Stale GLB provenance')
    labels = region_labels(semantic)
    rendered, views = mesh_vision.make_views(mesh_vision.glb_geometry(glb))
    # Changing an input or either prompt/model produces a new evidence directory.
    bundle_hash = hashlib.sha256(json.dumps({'glb': digest, 'semantic': semantic_hash,
        'render': hashlib.sha256(rendered).hexdigest(), 'model': model, 'reviewer': reviewer,
        'annotation_prompt': single_view_prompt(labels, order),
        'review_prompt': review_prompt(labels), 'schema': REGION_PROMPT_VERSION},
        sort_keys=True).encode()).hexdigest()[:16]
    folder = plan_path.parent / 'vision-region-receipts' / ('multiview-' + pass_id + '-' + bundle_hash)
    folder.mkdir(parents=True, exist_ok=True)
    provenance = {'glb_sha256': digest, 'interaction_sha256': semantic_hash,
        'prompt_version': REGION_PROMPT_VERSION}
    images = []; panels = []
    mosaic = Image.open(io.BytesIO(rendered)); size = mesh_vision.VIEW_SIZE
    cameras = []
    for i, view in enumerate(views):
        panel = mosaic.crop(((i % 2)*size, (i // 2)*size, (i % 2+1)*size, (i // 2+1)*size))
        data = io.BytesIO(); panel.save(data, format='PNG'); data = data.getvalue()
        (folder / f'view-{i}.png').write_bytes(data)
        panels.append(panel); images.append((f'VIEW {i} unannotated full image', data))
        cameras.append({k: v.tolist() if isinstance(v, np.ndarray) else v
                        for k, v in view.items() if k != 'surface_mask'})
    (folder / 'inputs.json').write_text(json.dumps({**provenance, 'roles': labels,
        'coordinate_frame': 'full_view_xyxy_normalized_1000',
        'image_size': [size, size], 'crop': [0, 0, size, size],
        'projection': 'orthographic: x=size/2+(world-center).right*scale; y=size/2-(world-center).up*scale',
        'cameras': cameras, 'images': [{'file': f'view-{i}.png',
            'sha256': hashlib.sha256(data).hexdigest()} for i, (_, data) in enumerate(images)]}, indent=2) + '\n')
    if prepare_only:
        print('Prepared four complete GLB views:', folder.relative_to(ROOT)); return
    report_path = folder / 'report.json'
    report = {**provenance, 'schema': 2, 'status': 'needs_review',
        'glb_surface_status': 'unresolved_pending_B5', 'issues': []}
    try:
        answer, receipts = annotate_individual_views(folder, model, labels, order,
            images, provenance, allow_paid)
        records = validate_multiview(answer, labels, views, order)
        report.update(views=records, annotation_receipts=receipts)
        review_images = []
        for record in records:
            i = record['view']
            overlay = Image.open(io.BytesIO(render_overlay(panels[i], record['objects'], {})))
            draw = ImageDraw.Draw(overlay)
            for region in record['objects'].values():
                if not region['visible'] or 'origin' not in region: continue
                a, b = [[v * size / 1000 for v in region[k]] for k in ('origin', 'direction_tip')]
                draw.line((*a, *b), fill=(255, 80, 0), width=3)
                draw.ellipse((b[0]-4, b[1]-4, b[0]+4, b[1]+4), fill=(255,80,0))
                draw.text(tuple(a), 'origin', fill=(200,60,0)); draw.text(tuple(b), 'tip', fill=(200,60,0))
            data = io.BytesIO(); overlay.save(data, format='PNG'); data = data.getvalue()
            (folder / f'overlay-{i}.png').write_bytes(data)
            review_images.extend([images[i], (f'VIEW {i} labeled regions and signed directions', data)])
        review, review_receipt = region_request(folder, 'review', reviewer,
            review_prompt(labels), review_images, provenance, allow_paid,
            request_options={'reasoning': {'enabled': False}})
        coverage, issues = reviewed_regions(records, review, labels)
        report.update(review=review, review_receipt=review_receipt,
            confirmed_views=coverage, issues=issues,
            status='confirmed_2d' if not issues else 'needs_review')
    except (ValueError, RuntimeError, KeyError, IndexError, TypeError, OSError) as error:
        report['issues'].append(str(error))
        raise
    finally:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        # Publish a source-matched image-space report, never upgrade old vertices,
        # contact anatomy or the existing rejected pose verdict.
        plan['mesh_region_review'] = {'schema': 2, **provenance,
            'status': report['status'], 'review': str(report_path.relative_to(ROOT)),
            'glb_surface_status': report['glb_surface_status']}
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    if report['issues']: raise ValueError('; '.join(report['issues']))
    print('Confirmed 2D regions only; B5 surfaces still unresolved:', report_path.relative_to(ROOT))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",required=True)
    parser.add_argument("--pass-id",default="studio_flash_audit")
    parser.add_argument("--model",default="qwen/qwen3-vl-235b-a22b-instruct")
    parser.add_argument("--reviewer",default="xiaomi/mimo-v2.6-pro")
    parser.add_argument("--legacy-crops",action="store_true")
    parser.add_argument("--allow-paid",action="store_true")
    parser.add_argument("--prepare-only",action="store_true")
    args=parser.parse_args()
    target=(ROOT/args.plan).resolve()
    if not target.is_file() or not target.is_relative_to(ROOT):
        raise ValueError("Audited plan must be a canonical repository file")
    if args.legacy_crops:
        if not args.allow_paid:
            raise ValueError("Legacy audit requires --allow-paid (may reuse receipts)")
        audit(target,args.pass_id,args.model)
    else:
        audit_multiview(target,args.pass_id,args.model,args.reviewer,
                        args.allow_paid,args.prepare_only)
