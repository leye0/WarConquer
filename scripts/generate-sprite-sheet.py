#!/usr/bin/env python3
"""Generate ONE Muse PNG sprite-sheet pilot from a Warcraft II layout reference and a WarConquer unit image."""
import argparse, base64, hashlib, io, json, os, re, urllib.request, urllib.error
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
REQ=ROOT/"sprite-sheet-request.json"
OUTDIR=ROOT/"assets/spritesheets/drafts"
TMP=ROOT/"sprite-output"

def check(job):
    if job.get("grid")!=[5,5] or job.get("reference_rows")!=5: raise ValueError("Only 5x5 pilot permitted")
    url=urlparse(job["source_url"])
    # Reuse the original Warcraft II sheet via a public GitHub mirror; the
    # source image is ephemeral and is never committed to WarConquer.
    if url.scheme!="https" or url.hostname!="raw.githubusercontent.com" or not url.path.startswith("/DevCrumbs/Warcraft-II/master/docs/Wiki_Files/SpriteSheet/") or not url.path.endswith(".png"):
        raise ValueError("Source must be a known, permitted Warcraft II sheet in the GitHub mirror")
    ref=(ROOT/job["unit_reference"]).resolve()
    if not ref.is_relative_to(ROOT/"assets/concepts") or ref.suffix!=".png" or not ref.is_file(): raise ValueError("Invalid WarConquer ref")
    target=(ROOT/job["output"]).resolve()
    if not target.is_relative_to(OUTDIR) or target.suffix!=".png": raise ValueError("Invalid output path")
    return ref,target

def encoded(img):
    b=io.BytesIO();img.convert("RGBA").save(b,format="PNG")
    return {"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()}}

def source(job):
    req=urllib.request.Request(job["source_url"],headers={"User-Agent":"WarConquer-SpriteSheet-Reference/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=45) as response: raw=response.read(6000000)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Source HTTP {e.code}: Muse NOT called. Reference source unavailable.") from None
    # Pin the upstream bytes by Git blob hash to avoid silently changing poses.
    blob_hash=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    expected=job.get("expected_source_blob_sha")
    if expected and blob_hash!=expected: raise ValueError("Source PNG changed; stop before paid call")
    img=Image.open(io.BytesIO(raw)).convert("RGBA")
    if list(img.size)!=job["expected_source_size"]: raise ValueError(f"Source size changed {img.size}")
    TMP.mkdir(exist_ok=True)
    img.save(TMP/"source-layout-temporary.png")
    top=img.crop((0,0,img.width,job["source_top_px"]))
    top.save(TMP/"source-layout-crop.png")
    return top,hashlib.sha256(raw).hexdigest(),img.size

PROMPT="""Create ONE original WarConquer 2D sprite animation sheet in modern HIGH-DEFINITION, smooth antialiased hand-painted fantasy RTS art. The first input reference is an archival Warcraft II sprite-sheet excerpt for MOTION STRUCTURE ONLY; the second input reference is the visual identity of our WarConquer unit.

EXACT REGULAR GRID: 5 COLUMNS by 5 ROWS, 25 full-body sprites. There are FIVE CAMERA DIRECTIONS across columns: frontal three-quarter, diagonal toward camera, side, diagonal away, back three-quarter, following their precise angles in reference 1. There are FIVE SUCCESSIVE WALKING PHASES DOWN EACH COLUMN (not across rows). Each column must keep its own direction and animate the same walking cycle from the top cell to the bottom cell. Same feet baseline, same body size, same weapon side, matching directional foreshortening.

Use reference 2 as an exclusive CHARACTER DESIGN guide: identical WarConquer clothing, distinct humanoid identity, equipment, weapons, palette and painting treatment in ALL 25 cells. No Warcraft II species, helmets, colors, paintings, pixels, decals, identifiable costumes or figures. Do not pixelate. No game UI, text, captions, white squares, blue backgrounds, shadows or tile borders.

Transparent single composite PNG. Five rows x five columns, all separated with uniform gaps. Nothing clipped or missing, no overlapping tiles. Professional attractive crisp detailed RTS sprites. No alternate characters or poses invented outside the walk-cycle geometry.
"""

def run(job, ref, crop):
    key=os.environ.get("OPENROUTER_API_KEY");model=os.environ.get("OPENROUTER_IMAGE_MODEL")
    if not key or not model: raise ValueError("Missing Muse secrets")
    prompt=PROMPT+"\nUNIT: "+job["unit_description"]+"\n"+job["pose_notes"]
    payload={"model":model,"prompt":prompt,"input_references":[encoded(crop),encoded(Image.open(ref))],
             "n":1,"output_format":"png","background":"transparent","aspect_ratio":"1:1"}
    request=urllib.request.Request("https://openrouter.ai/api/v1/images",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    try:
      with urllib.request.urlopen(request,timeout=300) as response: result=json.load(response)
    except urllib.error.HTTPError as e:
      msg=""
      try:msg=json.loads(e.read(4096)).get("error",{}).get("message","")[:250]
      except Exception:pass
      raise RuntimeError(f"OpenRouter HTTP {e.code}: {msg}; no paid retry") from None
    img=Image.open(io.BytesIO(base64.b64decode(result["data"][0]["b64_json"],validate=True))).convert("RGBA")
    img.save(TMP/"muse-original-response.png")
    return img,model,prompt,result.get("usage",{})

def review(img,dest):
    w,h=img.size;alpha=img.getchannel("A");hist=alpha.histogram()
    fraction=sum(hist[:16])/(w*h)
    cover=[]
    for r in range(5):
      cover.append([])
      for c in range(5):
        a=alpha.crop((c*w//5,r*h//5,(c+1)*w//5,(r+1)*h//5))
        cover[-1].append(round(sum(a.histogram()[96:])/(a.width*a.height),4))
    board=Image.new("RGBA",(w,h+85),(230,238,241,255))
    board.alpha_composite(img)
    d=ImageDraw.Draw(board)
    for i in range(1,5):
      d.line((i*w//5,0,i*w//5,h),fill=(21,122,155,140),width=3)
      d.line((0,i*h//5,w,i*h//5),fill=(21,122,155,140),width=3)
    d.text((16,h+10),"MUSE / WarConquer: 5 x 5 sprite cells — DRAFT ONLY",fill=(17,39,54))
    d.text((16,h+34),"NOT pixel art. Check all poses, continuity, anatomy and framing.",fill=(40,59,72))
    board.convert("RGB").save(dest)
    return {"transparent_fraction":round(fraction,5),"cell_fill":cover,
      "all_cells_present_heuristic":all(.015<e<.96 for row in cover for e in row),
      "status":"draft-awaiting-visual-review",
      "warning":"Pixel statistics do not prove 25 correct poses or consistent identity"}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    request=json.loads(REQ.read_text())
    if len(request.get("jobs",[]))!=1: raise ValueError("One pilot job at a time")
    job=request["jobs"][0];ref,out=check(job)
    if args.dry_run:
      print(json.dumps({"ready":True,"paid":False,"source":job["source_name"],"unit":job["unit_reference"],"output":job["output"]}));return
    crop,sha,dims=source(job)
    img,model,prompt,usage=run(job,ref,crop)
    out.parent.mkdir(parents=True,exist_ok=True)
    opaque=img.getchannel("A").getextrema()[0]==255
    if opaque and all(max(img.getpixel(pos)[:3])<10 for pos in ((0,0),(img.width-1,0),(0,img.height-1),(img.width-1,img.height-1))):
      # Muse frequently returns beautifully painted sprites on solid black.
      # rembg destroys those details. Restore the original raw PNG from matte
      # instead, with measured row geometry; keep DRAFT if phases are missing.
      import subprocess
      subprocess.run(["python","scripts/postprocess-muse-sprites.py",
                      "--input",str(TMP/"muse-original-response.png"),
                      "--run-id",os.environ.get("GITHUB_RUN_ID","new")],
                     cwd=ROOT,check=True)
      return
    if opaque:
      from rembg import remove,new_session
      img=remove(img,session=new_session("u2netp"),alpha_matting=False)
    img.save(out)
    info=review(img,out.with_name(out.stem+"_review.png"))
    info.update({"model":model,"original_reference_url":job["source_url"],"original_sha256":sha,
      "source_dimensions":dims,"source_crop":crop.size,
      "warconquer_unit_reference":job["unit_reference"],
      "warconquer_unit_sha256":hashlib.sha256(ref.read_bytes()).hexdigest(),
      "output_dimensions":img.size,"output_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
      "cutout_applied":opaque,"prompt":prompt,"usage":usage})
    out.with_suffix(".json").write_text(json.dumps(info,indent=2,ensure_ascii=False)+"\n")
    (TMP/"result.json").write_text(json.dumps(info,indent=2,ensure_ascii=False)+"\n")
    print("Produced",str(out.relative_to(ROOT)),"status",info["status"],"geometry-cell-check",info["all_cells_present_heuristic"])

if __name__=="__main__":main()
