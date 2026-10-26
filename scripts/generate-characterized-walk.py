#!/usr/bin/env python3
"""Five independent Muse frames from explicitly characterized Grunt poses.
No Warcraft reference images are committed, only new WarConquer sprites.
"""
import argparse, base64, hashlib, io, json, os, urllib.request, urllib.error
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_closing, binary_fill_holes, gaussian_filter, label

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"docs/sprite-motions/grunt-side-right-walk.json"
OUT=ROOT/"assets/spritesheets/drafts/marches_hache_side_walk"
DEBUG=ROOT/"sprite-frame-debug"
CELL=512
REFERENCE_SHA="6ce7fdfb4d68c401782149df83d02414389736c5"

def blob_sha(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def setup():
    config=json.loads(SPEC.read_text(encoding="utf-8"))
    frames=config["frames"]
    if config["schema_version"]!=1 or len(frames)!=5:
        raise ValueError("Need exactly five characterized frames")
    source=config["reference"]
    if source["mirror_git_blob_sha1"]!=REFERENCE_SHA or source["sheet_dimensions_px"]!=[380,631] or source["selected_column_one_based"]!=3:
        raise ValueError("Source is not the inspected right-facing Grunt column")
    unit=(ROOT/config["warconquer_unit"]["image_reference"]).resolve()
    if not unit.is_relative_to((ROOT/"assets/concepts").resolve()) or unit.suffix!=".png" or not unit.is_file():
        raise ValueError("WarConquer unit concept unavailable")
    for idx,frame in enumerate(frames,1):
        x,y,w,h=frame["source_rect_xywh"]
        if frame["index"]!=idx or x!=152 or y!=(idx-1)*55 or w!=76 or not 45<=h<=55:
            raise ValueError(f"Invalid source cell {idx}")
        for field in ("body_axis","torso","legs","feet","arms","weapon"):
            if len(frame["observations"].get(field,""))<18:
                raise ValueError(f"Frame {idx} missing observed limb annotation {field}")
        if len(frame["pose_constraints"])<4:
            raise ValueError(f"Frame {idx} missing explicit pose constraints")
    return config,unit

def source_image(config):
    url=config["reference"]["mirror_url"]
    if not url.startswith("https://raw.githubusercontent.com/DevCrumbs/Warcraft-II/master/docs/Wiki_Files/SpriteSheet/Orcs/Grunt/") or not url.endswith(".png"):
        raise ValueError("Source URL outside approved GitHub mirror")
    request=urllib.request.Request(url,headers={"User-Agent":"WarConquer-Pose-Research/1.0"})
    with urllib.request.urlopen(request,timeout=50) as response:
        raw=response.read(500000)
    if blob_sha(raw)!=REFERENCE_SHA:
        raise ValueError("Reference content changed, refusing paid calls")
    im=Image.open(io.BytesIO(raw)).convert("RGBA")
    if im.size!=(380,631):
        raise ValueError("Reference dimensions changed")
    return im,hashlib.sha256(raw).hexdigest()

def ref_image(img):
    b=io.BytesIO()
    img.convert("RGBA").save(b,format="PNG")
    return {"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(b.getvalue()).decode("ascii")}}

PROMPT="""Produce EXACTLY ONE isolated full-body pose of the ORIGINAL WarConquer Marches AXE WARRIOR, painted richly and sharply as a modern high-definition 2D RTS sprite (NOT pixel art). Near side profile, facing SCREEN RIGHT, slightly elevated game camera. One figure only, no sheet, no tiled grid.

Reference image 1 is a tiny Warcraft II frame. Read its POSE and relative body geometry ONLY: one frame in a five-phase walking cycle. Its legs, bent knees, forward/back foot positions and arms are the essential guidance. NEVER reproduce the Warcraft figure, green orc skin, gear, colors, low-resolution pixels, stylistic features or game assets.

Reference image 2 is our original WarConquer HUMAN axeman concept: match THIS actual warrior's face, hair, proportions, costume, colors, painted detail, dark leather, patched oxblood fabric, copper, and same distinctive axe. The unit must remain the same throughout the five frames. Hold axe consistently, do not change its physical identity.

The LEGS must match this particular frame's observed walking geometry, not a generic walk or idle pose. The relative feet locations are critical. No dramatic attack pose. Same camera direction/scale/lighting in all images. Include complete weapon, boots, head with ample empty margin. Prefer RGBA transparency; if unavailable render on uniformly BLACK background with NO shadow. No writing, labels, landscape, ground plane or other subjects.
"""

def frame_prompt(config,frame):
    obs=frame["observations"]
    fields="\n".join(k.upper()+": "+obs[k] for k in ("body_axis","torso","legs","feet","arms","weapon"))
    constraints="\n".join("* "+s for s in frame["pose_constraints"])
    return (PROMPT+
      "\nOUR UNIT: "+config["warconquer_unit"]["identity"]+
      "\nFIXED AXE HANDEDNESS: "+config["warconquer_unit"]["handedness"]+
      "\nFRAME "+str(frame["index"])+"/5 — "+frame["phase"]+
      "\nOBSERVED SOURCE GEOMETRY: \n"+fields+
      "\nMUST RESPECT ALL THE FOLLOWING:\n"+constraints+
      "\nVisibility uncertainty: "+"; ".join(obs.get("uncertain",[]))+
      "\nKeep those occluded joint identities unknown instead of inventing a confident left/right label. Pose MUST visibly differ from the other gait phases.")

def call_muse(model,key,pose_ref,unit_ref,prompt):
    payload={"model":model,"prompt":prompt,
        "input_references":[ref_image(pose_ref),ref_image(unit_ref)],
        "n":1,"output_format":"png","background":"transparent","aspect_ratio":"1:1"}
    request=urllib.request.Request("https://openrouter.ai/api/v1/images",
        data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(request,timeout=300) as response:
            result=json.load(response)
    except urllib.error.HTTPError as e:
        reason=""
        try:
            err=json.loads(e.read(4096)).get("error",{})
            if isinstance(err,dict):reason=str(err.get("message",""))[:200]
        except Exception:pass
        raise RuntimeError(f"OpenRouter HTTP {e.code}: {reason}. No automatic paid retry") from None
    png=base64.b64decode(result["data"][0]["b64_json"],validate=True)
    im=Image.open(io.BytesIO(png)).convert("RGBA")
    return im,png,result.get("usage",{})

def extract_subject(im):
    rgba=np.asarray(im,dtype=np.uint8)
    rgb=rgba[:,:,:3]
    if rgba[:,:,3].min()<255:
        return im,"native-alpha"
    corners=np.stack([rgb[0,0],rgb[0,-1],rgb[-1,0],rgb[-1,-1]])
    if corners.max()<35:
        mask=rgb.max(axis=2)>22
        matte="black"
    elif corners.min()>225:
        mask=rgb.min(axis=2)<238
        matte="white"
    else:
        # Do NOT repeat the old destructive background removal; preserve raw output.
        raise ValueError("Unsupported Muse background; raw saved for inspection")
    mask=binary_fill_holes(binary_closing(mask,iterations=2))
    labels,n=label(mask)
    if n:
        counts=np.bincount(labels.ravel())
        active=np.zeros(n+1,dtype=bool)
        active[1:]=counts[1:]>=max(30,int(counts[1:].max()*.002))
        mask &= active[labels]
    alpha=(gaussian_filter(mask.astype(np.float32),sigma=.65)*255).clip(0,255).astype(np.uint8)
    data=np.dstack([rgb,alpha])
    if matte=="black":
        denom=np.maximum(alpha.astype(np.float32)/255.,.32)
        data[:,:,:3]=np.minimum(255,rgb.astype(np.float32)/denom[:,:,None]).astype(np.uint8)
    return Image.fromarray(data,"RGBA"),matte+"-matte"

def make_tile(subject):
    a=subject.getchannel("A")
    bbox=a.point(lambda n:255 if n>38 else 0).getbbox()
    if not bbox:raise ValueError("No visible subject")
    x0,y0,x1,y1=bbox
    w,h=subject.size
    if min(x0,y0,w-x1,h-y1)<2:
        raise ValueError("Character cropped in original Muse canvas")
    area=sum(a.histogram()[40:])/(w*h)
    if not .025<=area<=.87:
        raise ValueError(f"Abnormal foreground fraction {area:.4f}")
    cropped=subject.crop(bbox)
    scale=min(1.,.78*CELL/cropped.width,.82*CELL/cropped.height)
    resized=cropped.resize((max(1,round(cropped.width*scale)),max(1,round(cropped.height*scale))),Image.Resampling.LANCZOS)
    left=(CELL-resized.width)//2
    top=CELL-32-resized.height
    if top<5 or left<5:
        raise ValueError("Unsafe normalized margin")
    tile=Image.new("RGBA",(CELL,CELL),(0,0,0,0))
    tile.alpha_composite(resized,(left,top))
    return tile,{"bbox":list(bbox),"foreground_fraction":round(area,5),"rescale":round(scale,5),"foot_baseline_px":CELL-32}

def compose(tiles):
    atlas=Image.new("RGBA",(CELL*5,CELL),(0,0,0,0))
    review=Image.new("RGBA",(CELL*5,CELL+110),"#e7ebee")
    draw=ImageDraw.Draw(review)
    draw.text((18,12),"WARCONQUER / Marche profil droit — 5 poses caracterisees / Muse",fill="#152737")
    draw.text((18,35),f"{len(tiles)}/5 images generees, revision humaine requise",fill="#375169")
    for n,tile in enumerate(tiles):
        atlas.alpha_composite(tile,(n*CELL,0))
        review.alpha_composite(tile,(n*CELL,85))
        draw.rectangle((n*CELL,85,(n+1)*CELL-1,CELL+85),outline="#3688a6",width=2)
        draw.text((n*CELL+14,63),f"FRAME {n+1}",fill="#233b4e")
    for n in range(len(tiles),5):
        draw.text((n*CELL+14,CELL//2),f"MISSING F{n+1}",fill="#b83232")
    return atlas,review.convert("RGB")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dry-run",action="store_true")
    args=ap.parse_args()
    spec,concept=setup()
    if args.dry_run:
        print(json.dumps({"five_pose_specs":True,"frames":len(spec["frames"]),"paid_requests":0}))
        return
    key=os.environ.get("OPENROUTER_API_KEY");model=os.environ.get("OPENROUTER_IMAGE_MODEL")
    if not key or not model:raise ValueError("Muse secrets missing")
    original,guide_hash=source_image(spec)
    unit=Image.open(concept).convert("RGBA")
    OUT.mkdir(parents=True,exist_ok=True)
    DEBUG.mkdir(parents=True,exist_ok=True)
    tiles=[];records=[];failed=False
    for frame in spec["frames"]:
        idx=frame["index"]
        x,y,w,h=frame["source_rect_xywh"]
        crop=original.crop((x,y,x+w,y+h)).resize((608,440),Image.Resampling.NEAREST)
        crop.save(DEBUG/f"guide-frame-{idx:02}.png")
        prompt=frame_prompt(spec,frame)
        record={"frame":idx,"phase":frame["phase"],"source_rect":frame["source_rect_xywh"],
            "guide_sha256":guide_hash,"concept_sha256":hashlib.sha256(concept.read_bytes()).hexdigest(),
            "model":model,"pose_characterization":frame,"prompt":prompt}
        try:
            rawim,raw,usage=call_muse(model,key,crop,unit,prompt)
            (DEBUG/f"muse-raw-{idx:02}.png").write_bytes(raw)
            cut,method=extract_subject(rawim)
            tile,stats=make_tile(cut)
            output=OUT/f"frame-{idx:02}.png"
            tile.save(output)
            record.update({"status":"awaiting-visual-pose-review","matte":method,
                "original_size":list(rawim.size),"output_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
                "usage":usage,**stats})
            tiles.append(tile)
            print(f"FRAME_{idx}_SUCCESS alpha={stats['foreground_fraction']} background={method}",flush=True)
        except Exception as err:
            record.update({"status":"failed","error_type":type(err).__name__,"error":str(err)[:400]})
            failed=True
            print(f"::error title=Muse frame {idx} failed::{type(err).__name__}: {str(err)[:350]}",flush=True)
        records.append(record)
        if failed:break
    if tiles:
        atlas,preview=compose(tiles)
        atlas.save(OUT/"walk-strip.png")
        preview.save(OUT/"walk-strip-review.png")
    report={"status":"awaiting-human-pose-review" if len(tiles)==5 and not failed else "partial",
        "expected":5,"generated":len(tiles),"approved":False,
        "warning":"Metrics cannot verify anatomical pose; user must review every image.",
        "frames":records}
    (OUT/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if failed or len(tiles)!=5:raise SystemExit(1)

if __name__=="__main__":main()
