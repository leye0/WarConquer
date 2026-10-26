#!/usr/bin/env python3
"""Reusable WarConquer 8-direction stills -> eight walk/attack videos, via OpenRouter.
Designed for GitHub Actions; paid operations checkpoint separately.
"""
import argparse,base64,hashlib,io,json,os,re,runpy,time,urllib.request,urllib.error,urllib.parse
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
API="https://openrouter.ai/api/v1"
CONFIG=ROOT/"character-motion-request.json"
ORDER=("N","E","S","W","NE","SE","SW","NW")
DISPLAY=("NW","N","NE","W","S","E","SW","SE")
TURNS={
 "N": "fully from BEHIND, face/chest/hips/toes directed AWAY from camera toward screen TOP",
 "E": "true RIGHT SIDE profile, face/chest/hips/toes pointing screen RIGHT",
 "S": "true FRONT view, face/chest/hips/toes pointing directly toward camera/screen BOTTOM",
 "W": "true LEFT SIDE profile, face/chest/hips/toes pointing screen LEFT",
 "NE": "three-quarter REAR-RIGHT; ENTIRE body and both toes point UPPER-RIGHT, away from camera",
 "SE": "three-quarter FRONT-RIGHT; ENTIRE body and both toes point LOWER-RIGHT, toward camera",
 "SW": "three-quarter FRONT-LEFT; ENTIRE body and both toes point LOWER-LEFT, toward camera",
 "NW": "three-quarter REAR-LEFT; ENTIRE body and both toes point UPPER-LEFT, away from camera",
}
NEIGHBORS={"NE":("N","E"),"SE":("S","E"),"SW":("S","W"),"NW":("N","W")}
MOTION={"N":(0,-1),"NE":(1,-1),"E":(1,0),"SE":(1,1),
        "S":(0,1),"SW":(-1,1),"W":(-1,0),"NW":(-1,-1)}
VIDEO_MODEL="x-ai/grok-imagine-video-1.5-lite"
VIDEO_COST_RESERVE=.22
DURATION=8

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def cfg():
    o=json.loads(CONFIG.read_text(encoding="utf-8"))
    for key in ("character_id","run_id"):
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,48}",o.get(key,"")):
            raise ValueError("Invalid "+key)
    source=(ROOT/o["concept_path"]).resolve()
    if not source.is_relative_to((ROOT/"assets/concepts").resolve()) or not source.is_file() or source.suffix!=".png":
        raise ValueError("Concept must be existing PNG within assets/concepts/")
    for k in ("appearance","equipment","attack_motion"):
        if not isinstance(o.get(k),str) or len(o[k])<12:raise ValueError("Missing "+k)
    if o.get("directions")!=list(DISPLAY):raise ValueError("Expected 8 directions only")
    if o.get("video_model")!=VIDEO_MODEL or o.get("video_duration")!=8 or o.get("video_resolution")!="480p":
        raise ValueError("Only tested cheap image-to-video configuration permitted")
    if o.get("budget_usd",0)<1.95 or o["budget_usd"]>4:
        raise ValueError("Please set budget_usd between 1.95 and 4.00")
    out=ROOT/"assets/experiments/character-motion"/o["character_id"]/o["run_id"]
    fingerprint=digest(CONFIG)
    for f in out.rglob("*.json") if out.is_dir() else []:
        v=json.loads(f.read_text())
        if v.get("request_sha256") and v["request_sha256"]!=fingerprint:
            raise RuntimeError("Run configuration changed; choose new run_id (no silent repaying)")
    return o,source,out,fingerprint
def still_path(out,d):return out/"stills"/(d+".png")
def still_meta(out,d):return out/"stills"/(d+".json")
def video_folder(out,d):return out/"videos"/d
def video_meta(out,d):return video_folder(out,d)/"job.json"
def video_file(out,d):return video_folder(out,d)/"walk-then-attack.mp4"
def image_ref(path):
    return {"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(path.read_bytes()).decode("ascii")}}
def key():
    k=os.environ.get("OPENROUTER_API_KEY")
    if not k:raise ValueError("Missing OpenRouter key secret")
    return k
def api(path,method="GET",data=None,timeout=60):
    headers={"Authorization":"Bearer "+key(),"Accept":"application/json"}
    raw=json.dumps(data).encode("utf-8") if data is not None else None
    if raw is not None:headers["Content-Type"]="application/json"
    req=urllib.request.Request(API+path,data=raw,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
    except urllib.error.HTTPError as e:
        msg=""
        try:
            obj=json.loads(e.read(3000))
            msg=str(obj.get("error",{}).get("message",""))[:250]
        except Exception:pass
        raise RuntimeError("OpenRouter HTTP "+str(e.code)+" "+msg) from None
def pose_prompt(o,d):
    part=f"""ONE ORIGINAL WARCONQUER CHARACTER, visually IDENTICAL to the input concept in costume, body proportions, head, hair, color palette and equipment. Character identity: {o['appearance']}. Equipment: {o['equipment']}. Handedness: {o.get('handedness','Keep equipment in the exact same anatomical hand for all views.')}

Render ONE standing STILL full-body character, feet planted in a neutral stance, arms relaxed, no walking, action or movement. High-detail clean antialiased hand-painted 2D fantasy RTS, NOT pixel art, NOT 3D. Orthographic/slightly elevated RTS camera pitched 25–35 degrees, consistent scale. Entire figure including BOTH boots and full weapon visible with large margins, centered on transparent uniform background; plain black/white acceptable. No scenery, floor, other subjects, labels, arrows, text, effects or shadows.

THE COMPASS FACING IS A ROTATION OF THE WHOLE BODY, NOT JUST THE HEAD. Head, shoulders, sternum, chest, torso, waist belt, pelvis, BOTH thighs, knees and BOTH toes must ALL point in EXACTLY the same direction. A twisted head looking in the right direction while chest or feet face EAST is a FAILURE. Keep costume asymmetries and weapon attached to the correct same anatomical side. BODY ORIENTATION takes priority over facial gaze. Target {d}: {TURNS[d]}.
"""
    if d in NEIGHBORS:
        a,b=NEIGHBORS[d]
        part+=f"""Reference image 1 is the existing {a} direction of the SAME character. Image 2 is {b}. Image 3 is original character identity. Generate the MIDPOINT 45-degree yaw rotation of the ENTIRE RIGID TORSO AND LOWER BODY between {a} and {b}, not an in-place neck rotation. BOTH boots must point {d} (including their toe boxes), shoulders and hip line physically rotated halfway between both guides, while the character stands still. The desired output is not merely {a} or {b}. """
        if d=="NW":
            part+="NW SPECIAL: true BACK-LEFT three-quarter view: back dominant but distinct LEFT-WARD yaw, both feet aimed UPPER-LEFT. An east-facing torso with NW head, or straight N back with head swiveled left, are BOTH WRONG. "
    return part

def check_identical(out,d,path,meta,fingerprint):
    if not path.exists() and not meta.exists():return False
    if not path.exists() or not meta.exists():raise RuntimeError("Partial paid still exists; do not resubmit "+d)
    value=json.loads(meta.read_text())
    if value.get("request_sha256")!=fingerprint or value.get("image_sha256")!=digest(path):
        raise RuntimeError("Inconsistent paid still checkpoint "+d)
    print("REUSE STILL",d,flush=True)
    return True

def still(o,concept,out,fingerprint,d):
    dst=still_path(out,d);meta=still_meta(out,d)
    if check_identical(out,d,dst,meta,fingerprint):return
    model=os.environ.get("OPENROUTER_IMAGE_MODEL","")
    if model!="meta/muse-image":raise ValueError("Image model must remain meta/muse-image")
    refs=[concept]
    if d in NEIGHBORS:
        a,b=NEIGHBORS[d]
        refs=[still_path(out,a),still_path(out,b),concept]
        if not all(x.is_file() for x in refs):raise RuntimeError("Missing base directions for "+d)
    prompt=pose_prompt(o,d)
    result=api("/images","POST",{"model":model,"prompt":prompt,
        "input_references":[image_ref(x) for x in refs],"n":1,
        "output_format":"png","background":"transparent","aspect_ratio":"1:1"},300)
    if not result.get("data") or not result["data"][0].get("b64_json"):
        raise RuntimeError("Muse response missing image bytes")
    raw=base64.b64decode(result["data"][0]["b64_json"],validate=True)
    debug=ROOT/"character-motion-debug"/o["run_id"]/"muse"
    debug.mkdir(parents=True,exist_ok=True)
    (debug/(d+".png")).write_bytes(raw)
    original=Image.open(io.BytesIO(raw)).convert("RGBA")
    # Reuse the successful pre-existing WarConquer alpha and sprite normalization logic.
    shared=runpy.run_path(str(ROOT/"scripts/generate-standing-directions.py"))
    transparent,extraction=shared["extract_alpha"](original)
    norm,geom=shared["place_character"](transparent)
    dst.parent.mkdir(parents=True,exist_ok=True)
    norm.save(dst)
    save(meta,{"direction":d,"request_sha256":fingerprint,"image_sha256":digest(dst),
        "approved":False,"status":"generated-unreviewed","model":model,
        "refs":[str(p.relative_to(ROOT)) for p in refs],
        "prompt":prompt,"cutout":extraction,"geometry":geom,
        "usage":result.get("usage",{})})
    print("STILL",d,"saved",dst.relative_to(ROOT),"cost",result.get("usage",{}).get("cost"),flush=True)

def still_contact(o,out,fingerprint):
    if not all(still_path(out,d).is_file() for d in DISPLAY):
        raise RuntimeError("All 8 stills required for videos")
    tile=424;gap=12;header=74
    board=Image.new("RGB",(4*(tile+gap)+gap,2*(tile+gap)+gap+header),"#e7edf0")
    draw=ImageDraw.Draw(board)
    draw.rectangle((0,0,board.width,header),fill="#203649")
    draw.text((18,14),o["character_id"]+" | 8 VUES IMMOBILES | MUSE",fill="white")
    draw.text((18,39),"Vérifier les épaules, le bassin et les deux pieds — validation humaine requise",fill="#c7d7e0")
    for i,d in enumerate(DISPLAY):
        x=gap+(i%4)*(tile+gap);y=header+gap+(i//4)*(tile+gap)
        draw.rectangle((x,y,x+tile-2,y+tile-2),fill="#fbfcfc",outline="#bac8d2",width=2)
        p=Image.open(still_path(out,d)).convert("RGBA")
        p.thumbnail((tile-12,tile-36),Image.Resampling.LANCZOS)
        board.paste(p,(x+(tile-p.width)//2,y+23),p)
        draw.text((x+11,y+8),d,fill="#203849")
    target=out/"review-8-directions.png"
    target.parent.mkdir(parents=True,exist_ok=True)
    board.save(target)
    print("STILLS REVIEW",str(target.relative_to(ROOT)),flush=True)

def video_reference(out,d):
    src=Image.open(still_path(out,d)).convert("RGBA")
    bbox=src.getchannel("A").point(lambda n:255 if n>38 else 0).getbbox()
    if not bbox:raise ValueError("Empty still")
    cropped=src.crop(bbox)
    scale=min(768*.35/cropped.height,768*.27/cropped.width)
    figure=cropped.resize((max(1,round(cropped.width*scale)),max(1,round(cropped.height*scale))),Image.Resampling.LANCZOS)
    dx,dy=MOTION[d]
    cx=round(768*(.5-dx*.05));fy=round(768*(.73-dy*.035))
    x=cx-figure.width//2;y=fy-figure.height
    margins=[x,y,768-x-figure.width,768-y-figure.height]
    if min(margins)<85:raise ValueError("Insufficient extra safe padding "+d)
    canvas=Image.new("RGBA",(768,768),(246,247,247,255))
    canvas.alpha_composite(figure,(x,y))
    target=video_folder(out,d)/"reference-768.png"
    target.parent.mkdir(parents=True,exist_ok=True)
    canvas.convert("RGB").save(target)
    return target,{"figure_bbox":[x,y,x+figure.width,y+figure.height],
                   "fraction_of_frame":round(figure.height/768,4),"margins":margins}
def video_prompt(o,d):
    dx,dy=MOTION[d]
    return f"""IMAGE-TO-VIDEO of this EXACT original WarConquer game character. Preserve identical costume, head, hair, body proportions, armor, equipment and anatomical weapon hand from the given first-frame reference. Highly detailed painted 2D RTS, NOT pixel art.

COMPASS-LOCK {d}. ALL body parts (HEAD, sternum, shoulder line, PELVIS, KNEES AND BOTH BOOT TOES) face {d} for the entire eight seconds. Screen travel vector is x={dx}, y={dy}, x RIGHT-positive and y DOWN-positive. Move and strike only in this direction. No turning, twisting, spin, new camera angle or flipping.

CRITICAL FIXED CAMERA AND SAFE MARGINS. The supplied image is intentionally an EXTRA-WIDE camera framing with character occupying only 35% of frame height. The surrounding empty pale background is PRESERVED ARTISTIC ACTION SPACE for full weapon reach. NEVER zoom, track, recenter, change subject scale, enlarge character or crop. Full body and COMPLETE EQUIPMENT including extreme tip at top of wind-up must remain at least 10% inside video boundaries on EVERY frame. Compact axe swing/attack arc, not a huge theatrical swing that hits the top of frame. Whole figure always visible.

TIMING STRICT:
0–4 SECONDS: WALK ONLY, controlled natural alternating leg gait in exact {d} ({TURNS[d]}), traveling no more than 5% of frame along (dx={dx},dy={dy}). No attack, no zoom.
4–8 SECONDS: STOP WALKING COMPLETELY and plant both feet. ATTACK in exact {d}: {o['attack_motion']} . Distinct wind-up, strike, follow-through and reset; do not turn the body, do not keep walking, no camera movement. Keep the entire weapon visible throughout the complete swing.

Character identity: {o['appearance']}. Equipment: {o['equipment']}.
Visual intent: readable for game sprite extraction, fixed elevated orthographic RTS viewpoint, neutral flat off-white background, full character, no scenery, UI, lettering, cinematic cuts, camera tricks, new subjects, blur or effects. Priority: CORRECT FULL-BODY {d} yaw, UNCROPPED WEAPON, walk THEN attack, CONSTANT SIZE."""
def model_check():
    obj=api("/videos/models")
    found=next((r for r in obj.get("data",[]) if r.get("id")==VIDEO_MODEL),None)
    if not found:raise RuntimeError("Video model unavailable")
    for key,val in (("supported_durations",8),("supported_resolutions","480p"),
                    ("supported_aspect_ratios","1:1"),("supported_frame_images","first_frame")):
        if val not in (found.get(key) or []):raise RuntimeError("Video model does not support "+str(val))
    return found

def spent(out):
    total=0.
    for d in ORDER:
        m=still_meta(out,d)
        if m.exists():total+=float(json.loads(m.read_text()).get("usage",{}).get("cost") or 0)
        p=video_meta(out,d)
        if p.exists():
            j=json.loads(p.read_text())
            if j.get("job_id"):
                price=j.get("usage",{}).get("cost")
                total+=float(price) if price is not None else VIDEO_COST_RESERVE
    return total
def video_submit(o,out,fingerprint,d):
    if not all(still_path(out,x).is_file() for x in ORDER):
        raise RuntimeError("Eight complete stills required before any video submission")
    f=video_meta(out,d)
    if f.exists():
        old=json.loads(f.read_text())
        if old.get("request_sha256")==fingerprint and old.get("job_id"):
            print("REUSE ACCEPTED VIDEO JOB",d,flush=True)
            return
        raise RuntimeError("Previous ambiguous video request must be inspected manually before retry "+d)
    if spent(out)+VIDEO_COST_RESERVE>float(o["budget_usd"])+1e-6:
        raise RuntimeError("Spend guard reached; refuse next billable video")
    model_check()
    ref,framing=video_reference(out,d)
    state={"direction":d,"model":VIDEO_MODEL,"request_sha256":fingerprint,
       "source_image_sha256":digest(still_path(out,d)),
       "status":"preparing","approved":False,"framing":framing,
       "prompt":video_prompt(o,d),"estimated_cost_reserve":VIDEO_COST_RESERVE}
    payload={"model":VIDEO_MODEL,"prompt":state["prompt"],"duration":8,"resolution":"480p",
        "aspect_ratio":"1:1","generate_audio":False,
        "frame_images":[{"type":"image_url","image_url":{"url":"data:image/png;base64,"+
        base64.b64encode(ref.read_bytes()).decode("ascii")},"frame_type":"first_frame"}]}
    try:
        response=api("/videos","POST",payload,100)
    except BaseException as e:
        state["status"]="uncertain-submission-no-automatic-retry"
        state["error"]=type(e).__name__+": "+str(e)[:280]
        save(f,state)
        raise
    job_id=response.get("id") if isinstance(response,dict) else None
    if not isinstance(job_id,str) or not job_id or "/" in job_id or "?" in job_id:
        state["status"]="ambiguous-response-no-automatic-retry"
        save(f,state)
        raise RuntimeError("Provider did not return valid accepted job id")
    state.update({"status":"submitted","job_id":job_id,"usage":response.get("usage") or {}})
    save(f,state)
    print("VIDEO JOB ACCEPTED",d,job_id,flush=True)
def video_collect(o,out,fingerprint,d):
    path=video_meta(out,d)
    if not path.exists():raise ValueError("Video must be submitted and checkpointed first")
    state=json.loads(path.read_text())
    if state.get("request_sha256")!=fingerprint or not state.get("job_id"):
        raise RuntimeError("No accepted id; never generate another job automatically")
    output=video_file(out,d)
    if output.exists() and state.get("status")=="completed-reviewed-unapproved":
        print("REUSE VIDEO",d,flush=True);return
    job_id=state["job_id"]
    if not output.exists():
        deadline=time.monotonic()+14*60
        while True:
            ans=api("/videos/"+urllib.parse.quote(job_id,safe=""))
            status=ans.get("status")
            state["status"]=status
            if ans.get("usage"):state["usage"]=ans["usage"]
            save(path,state)
            print("POLL",d,status,flush=True)
            if status=="completed":break
            if status in ("failed","cancelled","expired"):
                state["error"]=str(ans.get("error",""))[:250];save(path,state)
                raise RuntimeError("Accepted job failed; never submit another automatically")
            if status not in ("pending","in_progress"):raise RuntimeError("Unknown job state "+str(status))
            if time.monotonic()>deadline:raise TimeoutError("Keep job_id and resume; never repurchase")
            time.sleep(20)
        url=API+"/videos/"+urllib.parse.quote(job_id,safe="")+"/content?index=0"
        request=urllib.request.Request(url,headers={"Authorization":"Bearer "+key()})
        temp=output.with_suffix(".download")
        try:
            with urllib.request.urlopen(request,timeout=150) as response,open(temp,"wb") as target:
                size=0
                while True:
                    chunk=response.read(1<<20)
                    if not chunk:break
                    size+=len(chunk)
                    if size>65_000_000:raise RuntimeError("Oversized video")
                    target.write(chunk)
            if temp.stat().st_size<3000:raise ValueError("Invalid MP4")
            temp.replace(output)
        finally:
            if temp.exists():temp.unlink()
    quality=review_clip(output,video_folder(out,d),d)
    state.update({"status":"completed-reviewed-unapproved","approved":False,
        "video_sha256":digest(output),"video_bytes":output.stat().st_size,
        "qa":quality})
    save(path,state)
    print("VIDEO DONE",d,"cost",state.get("usage",{}).get("cost"),"QA",quality,flush=True)

def review_clip(video,out,d):
    import imageio_ffmpeg
    gen=imageio_ffmpeg.read_frames(str(video),pix_fmt="rgb24",output_params=["-vf","fps=4"])
    m=next(gen);w,h=m["size"]
    cell=315;head=75
    board=Image.new("RGB",(4*cell,2*cell+head),"#e6edf1");draw=ImageDraw.Draw(board)
    draw.rectangle((0,0,board.width,head),fill="#23384b")
    draw.text((16,14),d+" : MARCHE 0–4s / ATTAQUE 4–8s",fill="white")
    draw.text((16,41),"Inspecter cadrage de l'arme, orientation, echelle fixe et mouvements",fill="#c4d3df")
    targets=(2,6,10,14,18,22,26,30);count=0;clips=0;ratios=[]
    try:
        for i,raw in enumerate(gen):
            if i>=33:break
            arr=np.frombuffer(raw,dtype=np.uint8).reshape((h,w,3))
            mask=(arr.min(axis=2)<170)&(arr.mean(axis=2)<215)
            edge=max(3,min(w,h)//35)
            if mask[:edge,:].mean()>.006 or mask[-edge:,:].mean()>.006 or mask[:,:edge].mean()>.006 or mask[:,-edge:].mean()>.006:clips+=1
            ys,xs=np.where(mask)
            if len(xs)>50:ratios.append(ys.max()-ys.min()+1)
            if i in targets:
                n=targets.index(i);x=(n%4)*cell;y=head+(n//4)*cell
                draw.rectangle((x,y,x+cell-2,y+cell-2),fill="#f9fbfd")
                image=Image.fromarray(arr.copy(),"RGB");image.thumbnail((cell-12,cell-43),Image.Resampling.LANCZOS)
                board.paste(image,(x+(cell-image.width)//2,y+37))
                draw.text((x+12,y+12),str(round((i+.5)/4,2))+"s "+("WALK" if i<16 else "ATTACK"),fill="#294252")
                count+=1
    finally:
        try:gen.close()
        except Exception:pass
    if count!=8:raise RuntimeError("Incomplete video contact sheet")
    board.save(out/"contact-sheet.jpg",quality=88)
    zoom=(max(ratios)/min(ratios)) if ratios and min(ratios)>0 else None
    return {"samples":count,"edge_contact_frames":clips,
        "potential_weapon_clipping":clips>0,
        "height_drift_ratio":round(zoom,3) if zoom else None,
        "potential_scale_drift":bool(zoom and zoom>1.3),
        "verified_human":False}
def final(o,out,fingerprint):
    images={d:still_path(out,d).exists() for d in DISPLAY}
    videos={d:video_file(out,d).exists() for d in DISPLAY}
    report={"run_id":o["run_id"],"character":o["character_id"],
        "request_sha256":fingerprint,"images":images,"videos":videos,
        "images_complete":all(images.values()),"videos_complete":all(videos.values()),
        "reported_cost_usd":round(spent(out),4),"approved":False,
        "status":"requires-human-inspection",
        "warning":"Existence of files does not imply that all eight whole-body directions, fixed camera, timing, and weapons are correct."}
    save(out/"report.json",report)
    print("RUN REPORT",json.dumps(report),flush=True)
    if not all(images.values()) or not all(videos.values()):raise SystemExit(1)
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",required=True,choices=("validate","still","stills-contact","video-submit","video-collect","final"))
    parser.add_argument("--direction",choices=DISPLAY)
    args=parser.parse_args()
    o,concept,out,fp=cfg()
    if args.stage=="validate":
        Image.open(concept).verify()
        print(json.dumps({"ready":True,"paid_calls":0,"output":str(out.relative_to(ROOT)),
            "directions":list(DISPLAY),"budget_usd":o["budget_usd"]}),flush=True)
    elif args.stage=="still":
        if not args.direction:raise ValueError("--direction required")
        still(o,concept,out,fp,args.direction)
    elif args.stage=="stills-contact":still_contact(o,out,fp)
    elif args.stage=="video-submit":
        if not args.direction:raise ValueError("--direction required")
        video_submit(o,out,fp,args.direction)
    elif args.stage=="video-collect":
        if not args.direction:raise ValueError("--direction required")
        video_collect(o,out,fp,args.direction)
    elif args.stage=="final":final(o,out,fp)
if __name__=="__main__":main()
