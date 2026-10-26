#!/usr/bin/env python3
"""SW single-job textured safety frame experiment: existing SW axeman only.

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
OUT=ROOT/"assets/experiments/video-sw-textured"
REQ=ROOT/"video-sw-textured-request.json"
API="https://openrouter.ai/api/v1"
MODEL="x-ai/grok-imagine-video-1.5-lite"
WIDTH=768
VIDEO_NAME="SW-walk-then-attack-textured.mp4"
PROMPT="""NON-NEGOTIABLE CONSTRAINTS:

1. The visible textured border, warning band and central safe area are intentional spatial composition constraints, NOT scenery.
2. Preserve the ENTIRE dark textured border, gray warning band, safe-area boundary and four corner markers at EXACTLY the same fixed image coordinates throughout all eight seconds.
3. The complete character, BOTH feet, BOTH hands and the ENTIRE axe including its blade tip at the HIGHEST wind-up must remain fully inside the central pale safe area on EVERY FRAME.
4. No part of the character or axe may touch or enter the gray warning band, markers or dark textured border.
5. NO zooming, panning, camera tracking, reframing, automatic recentering, subject enlargement, scale changes, cropping or image stabilization that shifts the frame.
6. The character must stay at the SAME apparent size through the complete sequence. Border width, all corners and safe-zone geometry must stay pixel-stable.
7. The character must remain facing SOUTHWEST, toward the image LOWER-LEFT corner (both left and down) throughout.
8. The ENTIRE BODY must face southwest: head, shoulders, chest, pelvis, knees and BOTH feet. Never rotate only the head or turn the torso or feet toward another direction.
9. Preserve EXACTLY the same WarConquer man of the Marches: face, beard, hair, oxblood-red cloak and clothing, leather armor, copper ornaments, limbs and proportions, handcrafted axe, accessories and anatomical handedness of the reference.
10. Walk and attack occur within ONE continuous eight-second video with no cut or scene transition.

EXACT ACTION SEQUENCE:

0-4 seconds -- WALKING ONLY. Natural alternating footsteps with visible foot contact, walking toward SOUTHWEST: LEFT AND DOWN simultaneously on screen. Modest travel, approximately FIVE percent of overall image dimensions, keeping ample clearance from the warning band. The whole body remains facing southwest. No attack in this phase.

4-8 seconds -- ATTACKING ONLY. Stop walking COMPLETELY, plant BOTH feet, then make one or two clearly readable controlled, compact axe strikes toward the SOUTHWEST / LOWER-LEFT. Include preparation, wind-up, strike, follow-through and recovery. Do not move the feet across the image or rotate the torso. The whole axe, from handle to the very tip of its blade, must remain inside the CENTRAL SAFE AREA throughout its ENTIRE trajectory including maximum height and extension.

ADDITIONAL REQUIREMENTS: Fixed slightly elevated orthographic RTS camera. Modern highly detailed hand-painted 2D game art, NOT pixel art. Exactly ONE character. Uniform pale off-white empty center without scenery, environment, obstacles, additional actors, shadows, interface, text, special effects, cinematic transitions or audio. NEVER remove, reinterpret, move, redraw inconsistently, animate, zoom, pan or crop the safety frame. The safety frame is a permanent composition constraint, NOT a prop or a background environment. Preserve full weapon visibility, constant subject scale and correct whole-body SW orientation over spectacular movement.
"""

def log(msg):
    print(msg,flush=True)

def config():
    j=json.loads(REQ.read_text(encoding="utf-8"))
    required={"version":3,"direction":"SW","model":MODEL,"duration_seconds":8,
        "resolution":"480p","aspect_ratio":"1:1","walk_seconds":4,"attack_seconds":4,
        "reference_size_px":WIDTH,"max_accepted_jobs":1,"audio":False,
        "border_px":22,"warning_band_px":54,
        "first_frame":"assets/experiments/standing-turnaround/marches_hache/SW.png"}
    for key,val in required.items():
        if j.get(key)!=val:raise ValueError(f"Expected {key}={val!r}")
    if not REF.is_file():raise ValueError("Existing SW still image missing")
    return j

def make_ref():
    original=Image.open(REF).convert("RGBA")
    alpha=original.getchannel("A")
    bbox=alpha.point(lambda x:255 if x>=30 else 0).getbbox()
    if bbox is None:raise ValueError("Source SW character alpha missing")
    fig=original.crop(bbox)
    scale=min((WIDTH*.35)/fig.height,(WIDTH*.27)/fig.width)
    size=(max(1,round(fig.width*scale)),max(1,round(fig.height*scale)))
    small=fig.resize(size,Image.Resampling.LANCZOS)
    # Dark textured 22px exterior + plain 54px medium-grey warning band.
    canvas=Image.new("RGB",(WIDTH,WIDTH),(40,46,55))
    draw=ImageDraw.Draw(canvas)
    for offset in range(8,WIDTH,16):
        for y in (11,WIDTH-12):
            draw.line([(offset-4,y),(offset,y-4),(offset+4,y),(offset,y+4),(offset-4,y)],
                      fill=(77,83,92),width=1)
        for x in (11,WIDTH-12):
            draw.line([(x-4,offset),(x,offset-4),(x+4,offset),(x,offset+4),(x-4,offset)],
                      fill=(77,83,92),width=1)
    draw.rectangle((22,22,WIDTH-23,WIDTH-23),fill=(145,149,154))
    draw.rectangle((76,76,WIDTH-77,WIDTH-77),fill=(246,244,238))
    # Corner registration marks stay entirely in the grey warning band.
    for on_left in (True,False):
        for on_top in (True,False):
            x=48 if on_left else WIDTH-49
            y=48 if on_top else WIDTH-49
            sx=1 if on_left else -1
            sy=1 if on_top else -1
            draw.line([(x,y+sy*20),(x,y),(x+sx*20,y)],fill=(60,67,76),width=3)
            draw.line((x+sx*5,y+sy*5,x+sx*13,y+sy*5),fill=(207,210,213),width=2)
    center_x=round(WIDTH*.61)
    baseline_y=round(WIDTH*.70)
    x=center_x-small.width//2
    y=baseline_y-small.height
    if min(x-76,y-76,WIDTH-76-x-small.width,WIDTH-76-y-small.height)<35:
        raise ValueError("Character insufficiently inset within central safe area")
    canvas.paste(small,(x,y),small.getchannel("A"))
    OUT.mkdir(parents=True,exist_ok=True)
    fname=OUT/"reference-SW-textured-safe-768.png"
    canvas.save(fname,optimize=True)
    return fname,{"input_dimensions":list(original.size),"source_bbox":list(bbox),
        "new_dimensions":[WIDTH,WIDTH],"dark_textured_border_px":22,
        "warning_band_px":54,"central_safe_area_xyxy":[76,76,692,692],
        "character_fraction_height":round(small.height/WIDTH,4),
        "subject_box":[x,y,x+small.width,y+small.height],
        "center_x_fraction":.61,"feet_y_fraction":.70,
        "source_sha256":sha(REF)}

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
      "actual_submissions":1,"workflow_run_id":os.environ.get("GITHUB_RUN_ID"),
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

def subject_bbox(arr,within_safe=True):
    h,w,_=arr.shape
    lum=arr.mean(axis=2)
    mask=(lum<203)&(arr.min(axis=2)<182)
    if within_safe:
        m=round(w*76/768)+2
        mask[:m,:]=False
        mask[-m:,:]=False
        mask[:,:m]=False
        mask[:,-m:]=False
    yy,xx=np.nonzero(mask)
    if len(xx)<75:return None
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]

def rough_old_clip(path):
    if not path.is_file():return {"available":False,"reason":"MP4 unavailable"}
    gen=imageio_ffmpeg.read_frames(str(path),pix_fmt="rgb24",output_params=["-vf","fps=4"])
    info=next(gen);w,h=info["size"]
    heights=[];top_hits=0;count=0
    try:
        for idx,data in enumerate(gen):
            if idx>=32:break
            a=np.frombuffer(data,dtype=np.uint8).reshape((h,w,3)).copy()
            bbox=subject_bbox(a,False)
            if bbox:
                if idx<16:heights.append(bbox[3]-bbox[1])
                if idx>=16 and bbox[1]<=max(3,round(.012*h)):top_hits+=1
            count+=1
    finally:
        try:gen.close()
        except Exception:pass
    ratio=None
    if len(heights)>=8:
        ratio=round(float(np.median(heights[-4:])/max(1,np.median(heights[:4]))),3)
    return {"available":True,"frames_sampled_at_4fps":count,
            "walk_bbox_height_end_over_start":ratio,
            "attack_frames_touching_top_edge_heuristic":top_hits,
            "caveat":"Bounding box includes pose/axe, does not prove zoom or weapon completeness"}

def inspect(video):
    gen=imageio_ffmpeg.read_frames(str(video),pix_fmt="rgb24",output_params=["-vf","fps=4"])
    info=next(gen);w,h=info["size"]
    if min(w,h)<200:raise ValueError("Unexpected tiny video")
    ref=np.asarray(Image.open(OUT/"reference-SW-textured-safe-768.png").convert("RGB").resize((w,h),Image.Resampling.BICUBIC),dtype=np.int16)
    xx,yy=np.meshgrid(np.arange(w),np.arange(h))
    o=max(1,round(w*22/768));b=round(w*76/768)
    outer=(xx<o)|(xx>=w-o)|(yy<o)|(yy>=h-o)
    warning=(~outer)&((xx<b)|(xx>=w-b)|(yy<b)|(yy>=h-b))
    edges=outer|warning
    sheet=Image.new("RGB",(4*320,2*325+76),"#e6ecf1")
    draw=ImageDraw.Draw(sheet)
    draw.rectangle((0,0,sheet.width,75),fill="#243747")
    draw.text((14,13),"SW / TEXTURED SAFETY FRAME / WALK 0-4s / ATTACK 4-8s",fill="white")
    draw.text((14,42),"8 of 32 FFmpeg control frames. Visual approval remains REQUIRED.",fill="#c4d7e5")
    positions={2:0,6:1,10:2,14:3,18:4,22:5,26:6,30:7}
    frames_dir=OUT/"frames-4fps"
    frames_dir.mkdir(parents=True,exist_ok=True)
    first=None;rows=[];heights=[];widths=[];anomalies=[];border_flags=[]
    try:
        for idx,data in enumerate(gen):
            if idx>=33:break
            arr=np.frombuffer(data,dtype=np.uint8).reshape((h,w,3)).copy()
            im=Image.fromarray(arr,"RGB")
            im.save(frames_dir/f"frame-{idx:02d}.jpg",quality=84,optimize=True)
            values=arr.astype(np.int16)
            if first is None:first=values.copy()
            lum=arr.mean(axis=2)
            xmid=slice(round(.30*w),round(.70*w))
            ymid=slice(round(.30*h),round(.70*h))
            dark={
              "top":float((lum[:o,xmid]<122).mean()),
              "bottom":float((lum[-o:,xmid]<122).mean()),
              "left":float((lum[ymid,:o]<122).mean()),
              "right":float((lum[ymid,-o:]<122).mean())}
            gray={
              "top":float(((lum[o:b,xmid]>95)&(lum[o:b,xmid]<205)).mean()),
              "bottom":float(((lum[h-b:h-o,xmid]>95)&(lum[h-b:h-o,xmid]<205)).mean()),
              "left":float(((lum[ymid,o:b]>95)&(lum[ymid,o:b]<205)).mean()),
              "right":float(((lum[ymid,w-b:w-o]>95)&(lum[ymid,w-b:w-o]<205)).mean())}
            bounds={}
            profiles={"top":np.median(lum[:b+20,xmid],axis=1),
                      "bottom":np.median(lum[::-1][:b+20,xmid],axis=1),
                      "left":np.median(lum[ymid,:b+20],axis=0),
                      "right":np.median(lum[ymid,::-1][:,:b+20],axis=0)}
            for name,profile in profiles.items():
                v=np.flatnonzero(profile>211)
                bounds[name]=int(v[0]) if len(v) else None
            bbox=subject_bbox(arr)
            if bbox is not None and idx<16:
                heights.append(bbox[3]-bbox[1])
                widths.append(bbox[2]-bbox[0])
            border_input_mae=float(np.abs(values-ref)[edges].mean())
            border_first_mae=float(np.abs(values-first)[edges].mean())
            warning_mae=float(np.abs(values-ref)[warning].mean())
            # A disturbed band may reflect geometry drift OR character overlap.
            dark_band_fraction=float(((lum<83)&warning).sum()/max(1,warning.sum()))
            if warning_mae>48 or dark_band_fraction>.035:anomalies.append(idx)
            if min(dark.values())<.60 or min(gray.values())<.65 or any(v is None or abs(v-b)>4 for v in bounds.values()):
                border_flags.append(idx)
            rows.append({
                "sample_index":idx,"approx_time_seconds":round((idx+.5)/4,3),
                "dark_border_presence_by_side":{k:round(v,3) for k,v in dark.items()},
                "gray_warning_presence_by_side":{k:round(v,3) for k,v in gray.items()},
                "safe_boundary_positions_px":bounds,"expected_boundary_px":b,
                "border_mae_vs_original_reference":round(border_input_mae,2),
                "border_mae_vs_first_video_frame":round(border_first_mae,2),
                "warning_mae_vs_original_reference":round(warning_mae,2),
                "warning_dark_pixel_fraction":round(dark_band_fraction,4),
                "foreground_bbox_inside_safe_area":bbox})
            if idx in positions:
                k=positions[idx]
                tile=im.copy()
                tile.thumbnail((303,282),Image.Resampling.LANCZOS)
                x=(k%4)*320+(320-tile.width)//2
                y=76+(k//4)*325+30
                sheet.paste(tile,(x,y))
                draw.text(((k%4)*320+12,76+(k//4)*325+8),
                    f"{(idx+.5)/4:.2f}s  "+("WALK" if idx<16 else "ATTACK"),fill="#29485a")
    finally:
        try:gen.close()
        except Exception:pass
    if len(rows)<30:raise ValueError("Too few frames at 4 fps for an eight-second clip")
    sheet.save(OUT/"contact-sheet.jpg",quality=92,optimize=True)
    def ratio(vals):
        return round(float(np.median(vals[-4:])/max(1,np.median(vals[:4]))),3) if len(vals)>=8 else None
    height_ratio=ratio(heights)
    width_ratio=ratio(widths)
    baseline={
        "v1":rough_old_clip(ROOT/"assets/experiments/video-sw/SW-walk-then-attack.mp4"),
        "v2":rough_old_clip(ROOT/"assets/experiments/video-sw-v2/SW-walk-then-attack-framed.mp4"),
        "known_previous_visual_observations":{
            "v1":"Axe blade cut at top near 4.5s in earlier human QA",
            "v2":"Full axe visible in sampled attack poses, but subject visibly enlarges during walk"}}
    old=baseline["v2"].get("walk_bbox_height_end_over_start")
    baseline["new_minus_v2_walk_height_ratio"]=round(height_ratio-old,3) if isinstance(height_ratio,(int,float)) and isinstance(old,(int,float)) else None
    boundary_errors=[abs(v-b) for r in rows for v in r["safe_boundary_positions_px"].values() if v is not None]
    max_border_drift=max(r["border_mae_vs_first_video_frame"] for r in rows)
    border_heuristic=(not border_flags and max_border_drift<45 and len(boundary_errors)==len(rows)*4)
    report={
        "experiment":"SW-v3-textured-safety-frame",
        "status":"UNCERTAIN_PENDING_USER_VISUAL_APPROVAL",
        "automated_quality_not_equivalent_to_visual_approval":True,
        "sampling":{"tool":"FFmpeg/imageio-ffmpeg","fps":4,"frames_analyzed":len(rows),
                    "dimensions_px":[w,h],"frames_path":"frames-4fps/",
                    "eight_frame_sheet":"contact-sheet.jpg"},
        "reference_geometry_px":{"input_dimensions":[768,768],
             "dark_border_px":22,"warning_band_px":54,"safe_rectangle":[76,76,692,692]},
        "border":{"heuristic_consistent":border_heuristic,
            "flagged_frame_indices":border_flags,
            "max_pixel_change_from_first_frame":round(max_border_drift,2),
            "largest_inner_boundary_offset_px":max(boundary_errors) if boundary_errors else None,
            "note":"Heuristic only; chromatic drift or redrawn texture can fool a pixel detector"},
        "warning_band":{"possible_disturbance_frames":anomalies,
            "no_character_or_axe_contact":"UNCERTAIN; requires inspection of all 32 frames and MP4"},
        "scale":{"walk_bbox_height_end_over_start":height_ratio,
            "walk_bbox_width_end_over_start":width_ratio,
            "possible_scale_drift":height_ratio is None or abs(height_ratio-1)>.1,
            "note":"Bounding box may grow from posture and axe motion; not proof of camera zoom"},
        "motion":{"walk_only_0_to_4":"UNCERTAIN_REQUIRES_VISUAL_REVIEW",
                  "attack_only_4_to_8":"UNCERTAIN_REQUIRES_VISUAL_REVIEW",
                  "feet_planted_during_attack":"UNCERTAIN_REQUIRES_VISUAL_REVIEW",
                  "continuous_scene":"UNCERTAIN_REQUIRES_VISUAL_REVIEW"},
        "anatomy":{"whole_body_SW":"UNCERTAIN_REQUIRES_VISUAL_REVIEW",
                   "same_identity_and_handedness":"UNCERTAIN_REQUIRES_VISUAL_REVIEW",
                   "full_weapon_visible":"UNCERTAIN_REQUIRES_VISUAL_REVIEW",
                   "no_weapon_tip_missing":"UNCERTAIN_REQUIRES_VISUAL_REVIEW"},
        "previous_experiments":baseline,
        "per_frame":rows}
    (OUT/"quality-report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return {"decoded_frames":len(rows),"dimensions":[w,h],
        "possible_warning_contact_or_band_drift_frames":anomalies,
        "border_flagged_frames":border_flags,
        "border_heuristic_consistent":border_heuristic,
        "walk_scale_height_ratio":height_ratio,
        "v2_walk_scale_height_ratio":old,
        "visual_approval":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("phase",choices=("prepare","submit","finish"))
    args=p.parse_args()
    conf=config()
    jobfile=OUT/"job.json"
    ref=OUT/"reference-SW-textured-safe-768.png"
    if args.phase=="prepare":
        if jobfile.exists() or (OUT/VIDEO_NAME).exists():
            raise RuntimeError("Experiment already reserved. No new paid job allowed.")
        image,framing=make_ref()
        run_id=os.environ.get("GITHUB_RUN_ID")
        if not run_id:raise RuntimeError("Must execute in GitHub Actions")
        (OUT/"prompt.txt").write_text(PROMPT,encoding="utf-8")
        save({"status":"prepared-no-paid-call","approved":False,"model":MODEL,
              "actual_submissions":0,"workflow_run_id":run_id,
              "workflow_run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),
              "reference_sha256":sha(image),"reference_framing":framing,
              "request":conf,"prompt":PROMPT,"estimated_cost_usd":.17,
              "warning":"The prepared state is checkpointed to main BEFORE the sole paid POST; no ambiguous retries."})
        log(json.dumps({"ready":True,"paid_calls":0,"reference":framing},ensure_ascii=False))
        return
    if not jobfile.exists() or not ref.exists():
        raise RuntimeError("Missing previously committed preparation; refusing paid submit")
    job=json.loads(jobfile.read_text(encoding="utf-8"))
    if sha(ref)!=job.get("reference_sha256"):
        raise ValueError("Prepared first frame changed")
    if args.phase=="submit":
        if (job.get("status")!="prepared-no-paid-call" or job.get("actual_submissions")!=0 or
            job.get("workflow_run_id")!=os.environ.get("GITHUB_RUN_ID") or
            os.environ.get("GITHUB_RUN_ATTEMPT")!="1"):
            raise RuntimeError("Only initial Actions run can submit exactly one paid POST. No retry.")
        key=os.environ.get("OPENROUTER_API_KEY")
        if not key:raise RuntimeError("Missing OpenRouter Actions secret")
        # Ambiguous submissions remain permanently locked after this save.
        job["status"]="submission-attempted-possibly-ambiguous"
        job["actual_submissions"]=1
        job["attempt_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
        save(job)
        try:
            accepted=submit(ref,key,job["reference_framing"])
            accepted["request"]=conf
            accepted["estimated_cost_usd"]=.17
            save(accepted)
            log(json.dumps({"status":"accepted","id":accepted["id"],"paid_jobs":1}))
        except Exception as exc:
            job["last_error"]=type(exc).__name__+": "+str(exc)[:350]
            save(job)
            raise
        return
    if job.get("status")!="submitted" or not job.get("id"):
        raise RuntimeError("No confirmed existing OpenRouter job ID; NO further paid request")
    key=os.environ.get("OPENROUTER_API_KEY")
    if not key:raise RuntimeError("Missing OpenRouter Actions secret")
    try:
        if (OUT/VIDEO_NAME).exists() and (OUT/VIDEO_NAME).stat().st_size>2000:
            outcome={"usage":job.get("usage") or {}}
        else:
            outcome=poll(job,key)
            download(job,key)
        video=OUT/VIDEO_NAME
        qa=inspect(video)
        job.update({"status":"completed-reviewed-not-approved","approved":False,
            "video_path":str(video.relative_to(ROOT)),"video_sha256":sha(video),
            "video_bytes":video.stat().st_size,
            "usage":outcome.get("usage") or job.get("usage") or {},
            "qa":qa,"quality_report":str((OUT/"quality-report.json").relative_to(ROOT))})
        save(job)
        quality_file=OUT/"quality-report.json"
        quality=json.loads(quality_file.read_text(encoding="utf-8"))
        quality["model"]=MODEL
        quality["prompt_path"]="prompt.txt"
        quality["model_settings"]={"duration":8,"resolution":"480p",
                                   "aspect_ratio":"1:1","generate_audio":False}
        quality["openrouter_usage"]=job["usage"]
        quality["actual_cost_usd_if_reported"]=job["usage"].get("cost")
        quality["video_sha256"]=job["video_sha256"]
        quality["reference_sha256"]=job["reference_sha256"]
        quality_file.write_text(json.dumps(quality,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        (OUT/"QA.md").write_text(
            "# SW textured frame experiment — draft for user validation\n\n"
            "One continuous 8-second video: walk SW for 0-4 seconds, plant feet, then attack SW for 4-8 seconds. "
            "No Muse image generation, no audio, and no automatic paid retries.\n\n"
            "- [Original-character textured reference](reference-SW-textured-safe-768.png)\n"
            "- [MP4](SW-walk-then-attack-textured.mp4)\n"
            "- [Eight-frame contact sheet](contact-sheet.jpg)\n"
            "- [32 frames sampled at 4 fps](frames-4fps/)\n"
            "- [Quantitative and uncertain-quality report](quality-report.json)\n"
            "- [Exact prompt](prompt.txt)\n"
            "- [OpenRouter job metadata and billed usage](job.json)\n\n"
            "OpenRouter model: "+MODEL+"; 480p square, 8s, no audio. "
            "Usage: "+json.dumps(job["usage"],ensure_ascii=False)+".\n\n"
            "Border heuristic consistent: "+str(qa["border_heuristic_consistent"])+
            "; warning-band anomaly frames: "+str(qa["possible_warning_contact_or_band_drift_frames"])+
            "; subject walking bbox height end/start: "+str(qa["walk_scale_height_ratio"])+
            "; old v2: "+str(qa["v2_walk_scale_height_ratio"])+".\n\n"
            "**PENDING USER VISUAL APPROVAL.** Pixel and bbox heuristics cannot conclusively "
            "detect cropped axe tips, warning-band intersection, anatomical SW orientation, "
            "a continuous shot or correct walk-then-attack timing. Inspect the actual MP4. "
            "Previously generated videos remain intact under "
            "[SW v1](../video-sw/) and [SW v2](../video-sw-v2/).\n",
            encoding="utf-8")
        log(json.dumps({"video":job["video_path"],"model":MODEL,
            "cost":job["usage"].get("cost"),"qa":qa,"approved":False},ensure_ascii=False))
    except Exception as exc:
        job["pipeline_error_type"]=type(exc).__name__
        job["pipeline_error"]=str(exc)[:500]
        save(job)
        raise

if __name__=="__main__": main()
