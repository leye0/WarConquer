#!/usr/bin/env python3
"""Eight still turnaround directions of one WarConquer character via OpenRouter Muse.

Not animation: one standing figure for each compass direction.
Results are drafts requiring actual image review, not silently approved sprites.
"""
import argparse, base64, hashlib, io, json, os, traceback, urllib.error, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_closing, binary_fill_holes, gaussian_filter, label

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "standing-directions-request.json"
DIRECTIONS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
REVIEW_ORDER = ("NW", "N", "NE", "W", "S", "E", "SW", "SE")
TILE_SIZE = 1024
THUMB = 460
DESCRIPTIONS = {
    "N":  "rear view, facing directly AWAY from the viewer toward screen-top; back of head, shoulders, coat and axe are visible; face not visible",
    "NE": "three-quarter REAR view, body directed to upper-right of screen; back and character's right side visible, face almost hidden",
    "E":  "exact RIGHT SIDE profile, facing directly screen-right; nose points right, only one side of face visible",
    "SE": "three-quarter FRONT view, body directed lower-right of screen; face, chest and right-hand silhouette visible",
    "S":  "full FRONT view facing directly toward viewer / bottom of screen; full face and chest visible, body symmetrical in perspective",
    "SW": "three-quarter FRONT view, body directed lower-left of screen; face, chest and left-hand silhouette visible",
    "W":  "exact LEFT SIDE profile, facing directly screen-left; nose points left, only one side of face visible",
    "NW": "three-quarter REAR view, body directed upper-left of screen; back and character's left side visible, face almost hidden",
}
PROMPT = """HIGH-RESOLUTION 2D hand-painted fantasy RTS CHARACTER TURNAROUND: ONE single complete adult human character standing completely STILL in a perfectly neutral idle stance.

Image input reference is the ACTUAL ORIGINAL WarConquer soldier. Reproduce this exact SAME CHARACTER faithfully: identical head shape, hair, costume design, axe head, axe shaft, hands, gear, materials, repairs, accessories, scarf, colors, and body proportions. Show a ROTATED CAMERA VIEW OF THE SAME CHARACTER, NOT a new character. Reconstruct the physically correct back, sides and profile, respecting what is visible and occluded in this camera direction. The axe remains in the SAME anatomical hand across all eight outputs and has the SAME exact construction and blade shape. All other clothing and equipment stay in consistent anatomical positions.

PHYSICAL POSE IS STATIC AND IDENTICAL IN ALL DIRECTIONS: weight centered and evenly supported; feet planted near shoulder width and at the same depth; knees relaxed but straight; pelvis not twisted; torso upright and not leaning; shoulders level; arms down relaxed naturally, axe held low beside the body. NO walking, NO stepping, NO attack pose, NO running, NO swinging, NO floating or dancing. Preserve body scale and uniform orthographic/near-orthographic moderately elevated RTS camera (approximately 25-35 degrees above horizontal), flat consistent light.

MANDATORY FACING FOR THIS ONE IMAGE: {description}. Strictly honor this viewing angle even when the concept reference has a different angle. It must be clear that this is {direction} in a conventional eight-direction RTS with N away from camera, S toward camera, E toward image-right, W toward image-left.

Visually beautiful detailed HD antialiased hand-painted 2D illustration, NOT pixel art, NOT 3D scene, no blocky low-resolution stylization. Only one isolated full-body warrior centered on square frame. All of boots, head and axe must fit completely with generous margins. Transparent clean background preferred; if alpha cannot be rendered, use a COMPLETELY PLAIN BLACK OR PURE WHITE background for later extraction. No scenery, ground, text, arrows, labels, UI, borders, grids, motion lines, shadow or extra characters.
"""

def safe_output(request):
    if request.get("character")!="marches_hache" or request.get("directions")!=list(DIRECTIONS):
        raise ValueError("Pilot must contain exactly eight N/NE/E/SE/S/SW/W/NW directions of marches_hache")
    if request.get("stance")!="standing_still" or request.get("frames_per_direction")!=1:
        raise ValueError("This is an eight-image STANDING STILL test; no animations")
    out=(ROOT / request.get("output_dir","")).resolve()
    allowed=(ROOT/"assets/experiments/standing-turnaround").resolve()
    if out!=allowed/"marches_hache": raise ValueError("Unexpected output directory")
    ref=(ROOT/request.get("reference","")).resolve()
    if ref!=(ROOT/"assets/concepts/marches/units/hache.png").resolve() or not ref.is_file():
        raise ValueError("Existing WarConquer character reference missing")
    return ref,out

def reference_payload(raw):
    return [{"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(raw).decode("ascii")}}]

def call_muse(prompt, refs, model):
    payload={"model":model,"prompt":prompt,"input_references":refs,
             "n":1,"output_format":"png","background":"transparent","aspect_ratio":"1:1"}
    req=urllib.request.Request(
        "https://openrouter.ai/api/v1/images",data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req,timeout=300) as response: result=json.load(response)
    except urllib.error.HTTPError as exc:
        reason=""
        try:
            error=json.loads(exc.read(4096))
            reason=str(error.get("error",{}).get("message",""))[:250]
        except (ValueError,AttributeError,TypeError): pass
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {reason}; no retry") from None
    img_bytes=base64.b64decode(result["data"][0]["b64_json"],validate=True)
    image=Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    return image,img_bytes,result.get("usage",{})

def extract_alpha(image):
    rgb=np.asarray(image.convert("RGB"),dtype=np.uint8)
    original_alpha=np.asarray(image.getchannel("A"))
    if original_alpha.min()!=255:
        return image,"native-alpha"
    corners=np.array([rgb[0,0],rgb[0,-1],rgb[-1,0],rgb[-1,-1]])
    if corners.max()<35:
        mask=rgb.max(axis=2)>23
        background="black"
    elif corners.min()>225:
        mask=rgb.min(axis=2)<236
        background="white"
    else:
        raise ValueError("Unsupported opaque Muse background; raw image preserved for review")
    mask=binary_fill_holes(binary_closing(mask,iterations=2))
    components,n=label(mask)
    if n:
        counts=np.bincount(components.ravel())
        significant=np.zeros(n+1,dtype=bool)
        significant[1:]=counts[1:]>=max(35,int(counts[1:].max()*.001))
        mask &= significant[components]
    a=(gaussian_filter(mask.astype(np.float32),.7)*255).clip(0,255).astype(np.uint8)
    data=np.dstack([rgb,a])
    if background=="black":
        denom=np.maximum(a.astype(np.float32)/255.,.33)
        data[:,:,:3]=np.minimum(255,rgb.astype(np.float32)/denom[:,:,None]).astype(np.uint8)
    return Image.fromarray(data,"RGBA"),f"{background}-background-matte"

def place_character(image):
    alpha=image.getchannel("A")
    bbox=alpha.point(lambda a:255 if a>36 else 0).getbbox()
    if not bbox:raise ValueError("No opaque foreground")
    left,top,right,bottom=bbox
    source_edge_contact=min(left,top,image.width-right,image.height-bottom)<=3
    if source_edge_contact:
        # Preserve the raw file; don't claim a complete visible character.
        raise ValueError(f"Foreground clipped by Muse source image: {bbox}")
    foreground=sum(alpha.histogram()[48:])/(image.width*image.height)
    if foreground<.018 or foreground>.85:
        raise ValueError(f"Unlikely character coverage {foreground:.4f}")
    crop=image.crop(bbox)
    scale=min(.99,(TILE_SIZE*.65)/crop.width,(TILE_SIZE*.72)/crop.height)
    new_size=(max(1,round(crop.width*scale)),max(1,round(crop.height*scale)))
    resized=crop.resize(new_size,Image.Resampling.LANCZOS)
    canvas=Image.new("RGBA",(TILE_SIZE,TILE_SIZE),(0,0,0,0))
    x=(TILE_SIZE-resized.width)//2
    y=TILE_SIZE-125-resized.height
    if x<25 or y<25:raise ValueError("Character does not fit canvas with margins")
    canvas.alpha_composite(resized,(x,y))
    return canvas,{"raw_bbox":list(bbox),"source_edge_contact":source_edge_contact,
                   "foreground_fraction":round(foreground,5),"normalization_scale":round(scale,5),
                   "feet_baseline_px":TILE_SIZE-125}

def contact_sheet(output,results):
    unit=THUMB;gutter=14;header=98
    w=(unit+gutter)*4+gutter
    h=header+(unit+gutter)*2+gutter
    board=Image.new("RGB",(w,h),"#e1e8ee")
    draw=ImageDraw.Draw(board)
    draw.rectangle((0,0,w,header),fill="#203345")
    draw.text((20,20),"WARCONQUER — UN PERSONNAGE, 8 DIRECTIONS, IMMOBILE",fill="white")
    draw.text((20,48),"PROTOTYPE MUSE • 1 seule image par orientation • validation visuelle obligatoire",fill="#b6c9d8")
    by_dir={r["direction"]:r for r in results if r["status"]=="generated-awaiting-visual-review"}
    for i,d in enumerate(DIRECTIONS):
        x=gutter+(i%4)*(unit+gutter)
        y=header+gutter+(i//4)*(unit+gutter)
        draw.rectangle((x,y,x+unit-1,y+unit-1),fill="#f7f9fa",outline="#c2cdd4",width=2)
        if d in by_dir:
            src=Image.open(output/f"{d}.png").convert("RGBA")
            src.thumbnail((unit-12,unit-36))
            board.paste(src,(x+(unit-src.width)//2,y+22),src)
        else:
            draw.text((x+90,y+unit//2),"IMAGE NON PRODUITE",fill="#a43b31")
        draw.text((x+14,y+9),d,fill="#22394b")
    board.save(output/"review-8-directions.png")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    request=json.loads(REQUEST.read_text(encoding="utf-8"))
    ref,out=safe_output(request)
    if args.dry_run:
        print(json.dumps({"ready":True,"number_of_images":8,"stance":"standing_still",
          "directions":list(DIRECTIONS),"paid_calls":0},ensure_ascii=False))
        return
    model=os.environ.get("OPENROUTER_IMAGE_MODEL")
    key=os.environ.get("OPENROUTER_API_KEY")
    if not key or not model:raise ValueError("OpenRouter API key/model missing")
    out.mkdir(parents=True,exist_ok=True)
    raw_dir=ROOT/"standing-output"/"raw"
    raw_dir.mkdir(parents=True,exist_ok=True)
    src=ref.read_bytes()
    reference_hash=hashlib.sha256(src).hexdigest()
    refs=reference_payload(src)
    results=[]
    for i,d in enumerate(DIRECTIONS,1):
        target=out/(d+".png")
        if target.exists():
            results.append({"direction":d,"status":"generated-awaiting-visual-review",
                            "note":"existing result preserved without paid call"})
            continue
        prompt=PROMPT.format(direction=d,description=DESCRIPTIONS[d])
        rec={"direction":d,"camera_description":DESCRIPTIONS[d],"reference_sha256":reference_hash,
             "model":model,"stance":"standing_still","sequence":i,"prompt":prompt}
        try:
            raw,bytes_raw,usage=call_muse(prompt,refs,model)
            (raw_dir/(d+".png")).write_bytes(bytes_raw)
            with_alpha,method=extract_alpha(raw)
            png,geometry=place_character(with_alpha)
            png.save(target)
            rec.update({"status":"generated-awaiting-visual-review","matte_method":method,
                        "raw_dimensions":list(raw.size),"final_dimensions":list(png.size),
                        "output_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
                        "usage":usage,**geometry})
            print(f"GENERATED {d} | {method} | {png.size}",flush=True)
        except Exception as exc:
            rec.update({"status":"failed","error_type":type(exc).__name__,"error":str(exc)[:500]})
            print(f"::error title=Standing direction {d} failed::{type(exc).__name__}: {str(exc)[:250]}",flush=True)
        (out/(d+".json")).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+"\n")
        results.append(rec)
    contact_sheet(out,results)
    report={"experiment":"eight-standstill-views","model":model,"reference":str(ref.relative_to(ROOT)),
            "directions":list(DIRECTIONS),"generated":sum(x["status"]=="generated-awaiting-visual-review" for x in results),
            "expected":8,"approved":False,"status":"draft-awaiting-review",
            "warning":"Generator validation cannot prove correct camera angles, anatomy, consistent weapon or same character.",
            "results":[{"direction":r["direction"],"status":r["status"],"error":r.get("error")} for r in results]}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"generated":report["generated"],"expected":8,"status":report["status"]}),flush=True)
    if report["generated"]<8:raise SystemExit(1)

if __name__=="__main__": main()
