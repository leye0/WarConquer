#!/usr/bin/env python3
"""Recover Muse PNG sprites from a dark-background composite. No paid API calls."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_closing, binary_fill_holes, gaussian_filter, label

ROOT=Path(__file__).resolve().parents[1]
CELL=448
RAW_SHA256="390107869a4aeefb73885bff8ddb66e972dec895843fe99a2162e081386f2677"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="sprite-output-raw/muse-original-response.png")
    p.add_argument("--output-dir",default="assets/spritesheets/drafts")
    p.add_argument("--run-id",default="new")
    p.add_argument("--expected-sha256",default="")
    args=p.parse_args()
    src=(ROOT/args.input).resolve()
    if not src.is_file():raise FileNotFoundError("Muse raw artifact missing")
    raw_bytes=src.read_bytes()
    expected=args.expected_sha256 or (RAW_SHA256 if args.run_id=="40358268004" else "")
    if expected and hashlib.sha256(raw_bytes).hexdigest()!=expected:
        raise ValueError("Unexpected Muse raw image; abort postprocessing")
    rgb=np.asarray(Image.open(src).convert("RGB"),dtype=np.uint8)
    h,w=rgb.shape[:2]
    if w%5:raise ValueError("Five columns required")
    profile=(rgb.max(axis=2)>25).sum(axis=1)
    on=profile>10
    runs=[];start=None
    for i,val in enumerate(on):
        if val and start is None:start=i
        if (not val or i==h-1) and start is not None:
            end=i if not val else i+1
            if end-start>28:runs.append((start,end))
            start=None
    if len(runs)<2 or len(runs)>8:raise ValueError("Ambiguous frame rows: "+str(runs))
    out=ROOT/args.output_dir
    if not out.resolve().is_relative_to(ROOT/"assets/spritesheets/drafts"):
        raise ValueError("Invalid output location")
    out.mkdir(exist_ok=True,parents=True)
    atlas=Image.new("RGBA",(CELL*5,CELL*len(runs)),(0,0,0,0))
    fill=[];bounds=[]
    for ri,(a,b) in enumerate(runs):
        row=[];boxes=[]
        for ci in range(5):
            x0=ci*w//5;x1=(ci+1)*w//5
            crop=rgb[max(0,a-8):min(h,b+8),x0:x1,:]
            mask=binary_closing(crop.max(axis=2)>20,iterations=2)
            mask=binary_fill_holes(mask)
            components,num=label(mask)
            if num:
                counts=np.bincount(components.ravel())
                valid=np.zeros(num+1,dtype=bool)
                valid[1:]=counts[1:]>=45
                mask=valid[components]
            alpha=(gaussian_filter(mask.astype(np.float32),.65)*255).clip(0,255).astype(np.uint8)
            gamma=np.maximum(alpha[...,None].astype(np.float32)/255.,.30)
            pixel=(crop.astype(np.float32)/gamma).clip(0,255).astype(np.uint8)
            layer=Image.fromarray(np.dstack([pixel,alpha]),"RGBA")
            box=layer.getchannel("A").point(lambda z:255 if z>35 else 0).getbbox()
            if box is None:raise ValueError(f"Blank frame {ri+1}/{ci+1}")
            l,t,r,bb=box
            tile=layer.crop(box)
            dx=(CELL-tile.width)//2
            dy=CELL-30-tile.height
            if dx<6 or dy<6:raise ValueError(f"Overflow in row {ri+1}, column {ci+1}")
            atlas.alpha_composite(tile,(ci*CELL+dx,ri*CELL+dy))
            row.append(round(float((alpha>60).mean()),4))
            boxes.append([int(l),int(t),int(r),int(bb)])
        fill.append(row);bounds.append(boxes)
    base="marches_hache_walk_pilot"
    imgpath=out/(base+".png")
    atlas.save(imgpath)
    preview=Image.new("RGBA",(CELL*5,108+CELL*len(runs)),"#e2e8ec")
    preview.alpha_composite(atlas,(0,108))
    draw=ImageDraw.Draw(preview)
    draw.text((22,13),"WarConquer — Hache des Marches / Muse / revue des poses",fill="#182b3b")
    draw.text((22,39),f"{len(runs)} phases de marche x 5 orientations | reference Warcraft II | sprites detailles, PAS pixel art",fill="#294a62")
    if len(runs)!=5:
        draw.text((22,67),f"INCOMPLET : {len(runs)} rangees sur 5 demandees. Verification necessaire.",fill="#a33b2f")
    else:draw.text((22,67),"A verifier visuellement. Pas d'approbation automatique.",fill="#40546b")
    for c in range(1,5):
        draw.line([(c*CELL,108),(c*CELL,preview.height)],fill="#398eb6",width=3)
    for r in range(1,len(runs)):
        draw.line([(0,108+r*CELL),(preview.width,108+r*CELL)],fill="#398eb6",width=3)
    reviewpath=out/(base+"_review.png")
    preview.convert("RGB").save(reviewpath)
    meta={
      "source_run_id":str(args.run_id),"model":"meta/muse-image",
      "status":"incomplete-draft-awaiting-human-review" if len(runs)!=5 else "draft-awaiting-human-review","expected_grid":[5,5],
      "actual_grid":[5,len(runs)],"frame_size":[CELL,CELL],
      "source_dimensions":[w,h],"output_dimensions":list(atlas.size),
      "row_intervals":runs,"cell_alpha_coverage":fill,"source_frame_bounds":bounds,
      "matte_method":"connected-components foreground + black-background alpha extraction; rembg avoided",
      "source_raw_sha256":hashlib.sha256(raw_bytes).hexdigest(),
      "output_sha256":hashlib.sha256(imgpath.read_bytes()).hexdigest(),
      "warnings":["Muse produced four rows instead of five",
                  "Angles and gait still need review before this guide can be accepted"],
    }
    (out/(base+".json")).write_text(json.dumps(meta,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"result":"draft","actual_grid":meta["actual_grid"],"output":str(imgpath.relative_to(ROOT)),"review":str(reviewpath.relative_to(ROOT))}))

if __name__=="__main__":main()
