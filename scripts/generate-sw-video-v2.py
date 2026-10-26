#!/usr/bin/env python3
"""SW walking-then-attacking video, v2: motion-safe extra-wide framing.

Runs via GitHub Actions. One accepted paid job max; no silent retries.
All results remain DRAFT pending visual inspection of the actual MP4.
"""
import argparse, base64, hashlib, io, json, os, time
import urllib.error, urllib.parse, urllib.request
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/"assets/experiments/standing-turnaround/marches_hache/SW.png"
OUT=ROOT/"assets/experiments/video-sw-v2"
REQ=ROOT/"video-sw-framed-request.json"
API="https://openrouter.ai/api/v1"
MODEL="x-ai/grok-imagine-video-1.5-lite"
WIDTH=768
VIDEO_NAME="SW-walk-then-attack-framed.mp4"
PROMPT="""Make a single continuous eight-second image-to-video animation of THIS EXACT ORIGINAL WARCONQUER AXE WARRIOR, preserving his identity, handmade axe, crimson textile, dark leather armor, copper components, body proportions and all equipment. Hand-painted high-definition 2D RTS illustration, NOT pixel art.

HIGHEST PRIORITY: NEVER CROP THE CHARACTER OR HIS AXE. The provided FIRST FRAME is deliberately very WIDE FRAMED: the entire character is SMALL, occupying approximately 35 percent of the image height, located in the center-right lower half. ALL EMPTY BACKGROUND IS INTENTIONAL PROTECTED ACTION SPACE, NOT AN ERROR TO CORRECT. Keep EXACTLY the same static wide camera and image scale for the entire clip. Never zoom in, punch in, pan, track, recenter, upscale the character to fill the frame, crop, rotate the camera, or change lens. ALL parts of the character and weapon must remain at least ten percent of total frame width/height INSIDE the video edges on EVERY SINGLE FRAME, including the highest axe upswing and widest horizontal swing. The complete swinging-axe silhouette must be fully visible from handle to blade tip at all times. When the axe rises, there must still be abundant blank background above it.

Facing is SOUTHWEST (SW), i.e. diagonally toward the BOTTOM-LEFT CORNER of the image. Lock the actor's body orientation 45 degrees between screen-down and screen-left. Not due south. Not due west. Not sideways toward the camera. No body spin, no turn, no camera rotation. View camera fixed at a moderately elevated 2D RTS orthographic three-quarter perspective for the complete clip.

EXACT MOTION TIMING:
0.0-4.0s: WALKING ONLY. Walk smoothly SW with clear alternating legs and contact of feet on the ground. Travel a SHORT, controlled distance, no more than six percent of the FRAME width leftward and five percent of the FRAME height downward. Keep the same heading SW. The figure must NEVER approach the left or lower edges.
4.0-8.0s: ATTACKING ONLY. Come to a FULL STOP with feet planted, then make one or two CLEAR HEAVY AXE STRIKES into open space SW (screen bottom-left). Attack is an intentional wind-up and strike; the body remains facing SW. Swing the axe diagonally forward and downward with a LIMITED COMPACT ARC, arms and weapon contained inside the generous canvas at all times. Absolutely NO towering overhead wind-up that exits the image; no cropped axe head, no disappearing handle. Return to ready position between strikes.

Full body and full axe always visible with lots of blank space around them throughout. Keep fixed subject scale and clean white / very pale neutral featureless background. No scenery, obstacles, other actors, motion blur, cinematic camera, UI, captions, or sound. Readable game animation. Direction SW, two distinct phases and complete uncropped axe take precedence over cinematic flair.
"""

def log(msg):
    print(msg,flush=True)

def config():
    j=json.loads(REQ.read_text(encoding="utf-8"))
    required={"direction":"SW","model":MODEL,"duration_seconds":8,
        "resolution":"480p","aspect_ratio":"1:1",
        "walk_seconds":4,"attack_seconds":4,"reference_size_px":WIDTH,
        "max_accepted_jobs":1}
    for key,val in required.items():
        if j.get(key)!=val:raise ValueError(f"Expected {key}={val!r}")
    if not REF.is_file():raise ValueError("Existing SW still image missing")
    return j

def make_ref():
    original=Image.open(REF).convert("RGBA")
    alpha=original.getchannel("A")
    # Respect actual alpha, not fake black canvas seen in alpha image viewers.
    bbox=alpha.point(lambda x:255 if x>=35 else 0).getbbox()
    if bbox is None: raise ValueError("SW character missing")
    fig=original.crop(bbox)
    # Keep character at exactly <=35% of canvas height; axe has room to rise.
    target_h=round(WIDTH*.35)
    scale=min(target_h/fig.height,(WIDTH*.27)/fig.width)
    size=(max(1,round(fig.width*scale)),max(1,round(fig.height*scale)))
    small=fig.resize(size,Image.Resampling.LANCZOS)
    canvas=Image.new("RGBA",(WIDTH,WIDTH),(246,247,247,255))
    center_x=round(WIDTH*.61)
    baseline_y=round(WIDTH*.78)
    x=center_x-small.width//2
    y=baseline_y-small.height
    if min(x,y,WIDTH-(x+small.width),WIDTH-(y+small.height))<.12*WIDTH:
        raise ValueError("Reference not sufficiently padded")
    canvas.alpha_composite(small,(x,y))
    OUT.mkdir(parents=True,exist_ok=True)
    fname=OUT/"reference-SW-padded-768.png"
    canvas.convert("RGB").save(fname)
    return fname,{"input_dimensions":list(original.size),"source_bbox":list(bbox),
                  "new_dimensions":[WIDTH,WIDTH],"character_fraction_height":round(small.height/WIDTH,4),
                  "subject_box":[x,y,x+small.width,y+small.height]}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(job):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"job.json").write_text(json.dumps(job,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def api(endpoint,key,method="GET",payload=None,timeout=90):
    url=API+endpoint
    headers={"Authorization":"Bearer "+key,"Accept":"application/json"}
    data=None
    if payload is not None:
        headers["Content-Type"]="application/json"
        data=json.dumps(payload).encode("utf-8")
    req=urllib.request.Request(url,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        details=""
        try:
            v=json.loads(exc.read(2000))
            err=v.get("error",{}) if isinstance(v,dict) else {}
            details=str(err.get("message",""))[:200] if isinstance(err,dict) else ""
        except Exception:pass
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {details}; no automatic retry") from None

def submit(ref,key,metrics):
    caps=api("/videos/models",key)
    models={m.get("id"):m for m in caps.get("data",[]) if isinstance(m,dict)}
    model=models.get(MODEL)
    if not model:raise ValueError("Requested image-to-video model currently unavailable")
    if "first_frame" not in (model.get("supported_frame_images") or []):
        raise ValueError("Model does not support first-frame image")
    if 8 not in (model.get("supported_durations") or []):
        raise ValueError("8-second duration unsupported")
    if "480p" not in (model.get("supported_resolutions") or []):
        raise ValueError("480p unsupported")
    if "1:1" not in (model.get("supported_aspect_ratios") or []):
        raise ValueError("Square frame unsupported")
    data_url="data:image/png;base64,"+base64.b64encode(ref.read_bytes()).decode("ascii")
    payload={"model":MODEL,"prompt":PROMPT,"duration":8,"resolution":"480p",
       "aspect_ratio":"1:1","generate_audio":False,"frame_images":[
           {"type":"image_url","image_url":{"url":data_url},"frame_type":"first_frame"}]}
    log("Submitting exactly one "+MODEL+" video from padded 768px SW reference.")
    response=api("/videos",key,method="POST",payload=payload,timeout=90)
    job_id=response.get("id") if isinstance(response,dict) else None
    if not job_id:
        raise RuntimeError("Ambiguous submission response: do not submit another video")
    job={"status":"submitted","approved":False,"model":MODEL,
      "id":job_id,"prompt":PROMPT,"duration_seconds":8,
      "reference_sha256":sha(ref),"reference_framing":metrics,
      "usage":response.get("usage",{}),
      "warning":"No automatic second model or paid attempt."}
    save(job)
    return job

def poll(job,key):
    job_id=job["id"]
    if not job_id or not isinstance(job_id,str) or "/" in job_id:
        raise ValueError("Invalid provider job ID")
    encoded=urllib.parse.quote(job_id,safe="")
    deadline=time.monotonic()+16*60
    while True:
        result=api("/videos/"+encoded,key,timeout=60)
        status=result.get("status")
        if result.get("usage"):
            job["usage"]=result["usage"]
        job["status"]=status
        save(job)
        log("Video status: "+str(status))
        if status=="completed":return result
        if status in ("failed","cancelled","expired"):
            job["provider_error"]=str(result.get("error","no detail"))[:400]
            save(job)
            raise RuntimeError("Video generation ended as "+status)
        if status not in ("pending","in_progress"):
            raise RuntimeError("Unrecognized provider job status: "+str(status))
        if time.monotonic()>deadline:
            job["status"]="timed-out-keep-job-id"
            save(job)
            raise TimeoutError("Existing job can be resumed, not resubmitted")
        time.sleep(20)

def download(job,key):
    job_id=urllib.parse.quote(job["id"],safe="")
    req=urllib.request.Request(
       API+"/videos/"+job_id+"/content?index=0",
       headers={"Authorization":"Bearer "+key})
    target=OUT/VIDEO_NAME
    with urllib.request.urlopen(req,timeout=170) as response, open(target,"wb") as f:
        total=0
        while True:
            data=response.read(1<<20)
            if not data:break
            total+=len(data)
            if total>60*1024*1024:
                raise ValueError("Video over 60MB cap")
            f.write(data)
    if target.stat().st_size<2000:raise ValueError("Invalid video bytes")
    return target

def inspect(video):
    # Analyze at 4 fps, INCLUDING attack frames between the contact-sheet samples.
    # Off-white background lets us assess contact against each frame edge.
    gen=imageio_ffmpeg.read_frames(str(video),pix_fmt="rgb24",
        output_params=["-vf","fps=4"])
    meta=next(gen)
    w,h=meta["size"]
    if min(w,h)<200:raise ValueError("Unexpected tiny video")
    samples=[];flags=[];frame_count=0
    ncol=4;tilew=330;tileh=310;head=72
    review=Image.new("RGB",(ncol*tilew,2*tileh+head),"#e8edf1")
    painter=ImageDraw.Draw(review)
    painter.rectangle((0,0,ncol*tilew,head),fill="#24384a")
    painter.text((14,13),"SW / FRAME SAFETY • WALK 0–4s • ATTACK 4–8s",fill="white")
    painter.text((14,41),"Look for axe clipping, zoom, direction drift and action timing",fill="#cbdae4")
    positions={2:0,6:1,10:2,14:3,18:4,22:5,26:6,30:7}
    edge_px=max(4,round(min(w,h)*.02))
    try:
        for idx,data in enumerate(gen):
            if idx>=34:break
            arr=np.frombuffer(data,dtype=np.uint8).reshape((h,w,3))
            # Assume plain light background; detect pronounced colored/dark foreground.
            mask=(arr.min(axis=2)<170) & (arr.mean(axis=2)<215)
            edges={
             "top":float(mask[:edge_px,:].mean()),
             "bottom":float(mask[-edge_px:,:].mean()),
             "left":float(mask[:,:edge_px].mean()),
             "right":float(mask[:,-edge_px:].mean()),
            }
            if any(v>.007 for v in edges.values()):
                flags.append({"approx_second":round((idx+.5)/4,2),"edge_fractions":edges})
            if idx in positions:
                k=positions[idx]
                im=Image.fromarray(arr.copy(),"RGB")
                im.thumbnail((tilew-16,tileh-43),Image.Resampling.LANCZOS)
                px=(k%4)*tilew+(tilew-im.width)//2
                py=head+(k//4)*tileh+30
                review.paste(im,(px,py))
                painter.text(((k%4)*tilew+13,head+(k//4)*tileh+9),
                   f"{(idx+.5)/4:.2f}s   "+("WALK" if idx<16 else "ATTACK"),
                   fill="#294558")
                samples.append(idx)
            frame_count+=1
    finally:
        try: gen.close()
        except Exception:pass
    if len(samples)!=8:
        raise ValueError(f"Only {len(samples)} of eight QA frames extracted")
    path=OUT/"contact-sheet.jpg"
    review.save(path,quality=90,optimize=True)
    return {"decoded_frames":frame_count,"dimensions":[w,h],
        "edge_contact_flags":flags,"possible_clipping":bool(flags),
        "visual_approval":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args()
    conf=config()
    image,framing=make_ref()
    if args.dry_run:
        log(json.dumps({"ready":True,"new_paid_calls":0,"model":MODEL,
          "reference_framing":framing,"duration":8},ensure_ascii=False))
        return
    key=os.environ.get("OPENROUTER_API_KEY")
    if not key:raise ValueError("OpenRouter secret missing")
    jobfile=OUT/"job.json"
    if jobfile.exists():
        job=json.loads(jobfile.read_text(encoding="utf-8"))
        if not job.get("id"):
            raise ValueError("Existing unfinished job state without ID; do not resubmit")
        log("Resume existing video generation ID without submitting a second video")
    else:
        job=submit(image,key,framing)
    try:
        if (OUT/VIDEO_NAME).exists():
            video=OUT/VIDEO_NAME
            outcome={"usage":job.get("usage",{})}
        else:
            outcome=poll(job,key)
            video=download(job,key)
        qa=inspect(video)
        job.update({"status":"completed-reviewed-not-approved","approved":False,
            "video_path":str(video.relative_to(ROOT)),
            "video_sha256":sha(video),
            "video_bytes":video.stat().st_size,
            "usage":outcome.get("usage") or job.get("usage") or {},
            "qa":qa})
        save(job)
        log(json.dumps({"video":job["video_path"],"model":MODEL,
          "cost":job["usage"].get("cost"),"edge_contact_flags":len(qa["edge_contact_flags"]),
          "approved":False},ensure_ascii=False))
    except Exception as e:
        job["pipeline_error_type"]=type(e).__name__
        job["pipeline_error"]=str(e)[:500]
        save(job)
        raise

if __name__=="__main__": main()
