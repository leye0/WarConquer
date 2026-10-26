#!/usr/bin/env python3
"""One inexpensive image-to-video experiment on WarConquer's existing SW still.

OpenRouter /api/v1/videos: discover capabilities, submit at most one accepted job,
poll that job, download real MP4, and build a visual QA contact sheet.
No automatic resubmission of an accepted job, no speculative paid retry.
"""
import argparse
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "video-sw-request.json"
OUT = ROOT / "assets/experiments/video-sw"
API = "https://openrouter.ai/api/v1"
DIRECTIONS = {"SW"}
MODELS = [
    "bytedance/seedance-1-5-pro:free",
    "bytedance/seedance-1-5-pro",
    "x-ai/grok-imagine-video-1.5-lite",
]
MAX_SECONDS = 8
MAX_VIDEO_BYTES = 60 * 1024 * 1024
PROMPT = """ANIMATION TEST FOR A SINGLE ORIGINAL 2D RTS GAME CHARACTER. Use the reference image as the precise physical identity and INITIAL POSE of the axe-carrying human warrior. The image is a fixed camera view looking diagonally downward at a standing warrior whose facing is SOUTHWEST (SW) in screen/world coordinates. SOUTHWEST MEANS TOWARD THE BOTTOM-LEFT CORNER OF THE IMAGE: LEFT AND DOWN SIMULTANEOUSLY. His body, eyes, chest and axe always point toward the lower-left (screen SW), keeping the EXACT same southwest-facing three-quarter camera view from start to finish. He must NEVER face south only, west only, right, toward the camera, or away from the camera, and must NEVER turn his body around.

EXACT TIMING AND TWO SEPARATE ACTIONS in one continuous shot of exactly eight seconds:
0.0s to 4.0s: WALK ONLY. Natural alternating footsteps with visible knee bends, feet making actual contact with the ground. Walk FORWARD in the direction the warrior is facing: SOUTHWEST, toward screen lower-left (left and down together). Travel only a short distance, no more than half a character's body width, so he remains fully visible, and keep his facing SW constant. DO NOT walk on the spot while facing a different direction. No attack during this interval.
4.0s to 8.0s: STOP WALKING COMPLETELY, PLANT BOTH FEET, and execute deliberate readable AXE STRIKES aimed TOWARD THE SAME SOUTHWEST direction, downward and toward screen lower-left. Swing, follow-through, reset, repeat once if time allows. Never spin or change facing. No walking during this interval.

Character design must remain EXACTLY the same individual as the reference, with the identical face, hairstyle, crimson/oxblood and charcoal clothing, leather armor, bracelets, detailed large axe head, shaft, belts and attachments. Same axe in the same anatomical hand. Head, boots and axe all visible at ALL times. Modern sharply detailed hand-painted 2D game art, NOT PIXEL ART. ONE character only. Flat static uniform pale-neutral background, no environment, obstacles, extra characters, motion blur, UI or lettering, NO camera pan/zoom/orbit/cut. Keep the slightly elevated orthographic RTS camera fixed. The SW direction and sequence WALK FIRST, ATTACK SECOND are more important than cinematic flair. Motion should be useful for extracting sprite frames later.
"""

def report(message):
    print(message, flush=True)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if data.get("direction") != "SW" or data.get("duration_seconds") != 8:
        raise ValueError("This pilot is SW-only, eight seconds")
    if data.get("walk_seconds") != 4 or data.get("attack_seconds") != 4:
        raise ValueError("Sequence must be four seconds walk and four seconds attack")
    if data.get("max_accepted_jobs") != 1:
        raise ValueError("Must accept at most one paid or free video job")
    if data.get("models") != MODELS or data.get("resolution") != "480p":
        raise ValueError("Unexpected models or resolution")
    ref = ROOT / "assets/experiments/standing-turnaround/marches_hache/SW.png"
    if not ref.is_file():
        raise ValueError("Existing WarConquer SW still reference missing")
    return data, ref

def make_256_reference(source):
    im=Image.open(source).convert("RGBA")
    if im.width!=im.height:
        raise ValueError("WarConquer source direction must be square")
    resized=im.resize((256,256), Image.Resampling.LANCZOS)
    # Opaque neutral backdrop prevents source alpha from being interpreted as black.
    backdrop=Image.new("RGBA", (256,256), (246,247,246,255))
    backdrop.alpha_composite(resized,(0,0))
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/"reference-SW-256.png"
    backdrop.convert("RGB").save(target)
    return target

def request_json(path, key, method="GET", data=None, timeout=60):
    headers={"Authorization":"Bearer "+key,"Accept":"application/json"}
    if data is not None:
        headers["Content-Type"]="application/json"
    req=urllib.request.Request(
        path, headers=headers, method=method,
        data=json.dumps(data).encode("utf-8") if data is not None else None
    )
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail=""
        try:
            obj=json.loads(exc.read(4096))
            err=obj.get("error",{}) if isinstance(obj,dict) else {}
            detail=str(err.get("message",""))[:180] if isinstance(err,dict) else ""
        except (ValueError, UnicodeError, OSError): pass
        raise ProviderHTTPError(exc.code,detail) from None

class ProviderHTTPError(RuntimeError):
    def __init__(self, status, detail):
        self.status=status
        super().__init__(f"OpenRouter HTTP {status}: {detail}")

def discover(key):
    data=request_json(API+"/videos/models",key)
    return {item["id"]:item for item in data.get("data",[]) if isinstance(item,dict) and item.get("id")}

def capability(candidate):
    roles=candidate.get("supported_frame_images") or []
    durations=candidate.get("supported_durations") or []
    resolutions=candidate.get("supported_resolutions") or []
    ratios=candidate.get("supported_aspect_ratios") or []
    if "first_frame" not in roles:
        return None,"no-first-frame"
    if durations and MAX_SECONDS not in durations:
        return None,"no-eight-second"
    if resolutions and "480p" not in resolutions:
        return None,"no-480p"
    # Prefer square sprite framing; some models only support portrait/landscape.
    aspect=next((a for a in ("1:1","9:16","16:9","3:4","4:3")
                 if a in ratios), None)
    if not aspect:
        return None,"no-compatible-aspect"
    return aspect,"ok"

def dump_state(state):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"job.json").write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    report("Video state: "+state.get("status","unknown")+" / "+str(state.get("model","none")))

def submit_first_available(model_data, config, image256, key):
    image_url="data:image/png;base64,"+base64.b64encode(image256.read_bytes()).decode("ascii")
    attempted=[]
    for model in MODELS:
        info=model_data.get(model)
        if not info:
            attempted.append({"model":model,"reason":"not-listed-by-videos-models"})
            continue
        aspect,reason=capability(info)
        if not aspect:
            attempted.append({"model":model,"reason":reason})
            continue
        payload={
            "model":model, "prompt":PROMPT, "duration":MAX_SECONDS,
            "resolution":"480p", "aspect_ratio":aspect, "generate_audio":False,
            "frame_images":[
                {"type":"image_url","image_url":{"url":image_url},"frame_type":"first_frame"}
            ],
        }
        report("Submitting single video job with "+model+" at 480p / "+str(aspect)+" / 8s")
        try:
            accepted=request_json(API+"/videos",key,method="POST",data=payload,timeout=75)
        except ProviderHTTPError as e:
            attempted.append({"model":model,"reason":str(e)})
            # Only explicit client rejection means no accepted billable job.
            # Server errors / ambiguous failures MUST NOT cause second submission.
            if e.status in (400,402,403,404,422,429):
                report("Rejected before job acceptance: "+str(e))
                continue
            raise
        if not isinstance(accepted,dict) or not accepted.get("id"):
            raise RuntimeError("Ambiguous video submission response; do not submit a second job")
        state={
            "status":"submitted","approved":False,"model":model,
            "source_sha256":sha256(image256),
            "duration_seconds":MAX_SECONDS,"aspect_ratio":aspect,
            "resolution":"480p","job_id":accepted["id"],
            "polling_url":accepted.get("polling_url"),
            "prompt":PROMPT,"attempted_preflight":attempted,
            "usage":accepted.get("usage") or {},
        }
        dump_state(state)
        return state
    state={"status":"no-model-accepted","approved":False,
           "attempted_preflight":attempted,"prompt":PROMPT}
    dump_state(state)
    raise RuntimeError("No available model accepted the SW image-to-video request")

def poll(state,key):
    job_id=state["job_id"]
    # Trust only API path derived from ID, never a returned external URL.
    if not isinstance(job_id,str) or not job_id or "/" in job_id or "?" in job_id:
        raise ValueError("Invalid video job ID")
    deadline=time.monotonic()+16*60
    while True:
        job=request_json(API+"/videos/"+urllib.parse.quote(job_id,safe=""),key,timeout=45)
        status=job.get("status")
        state["status"]=str(status)
        if job.get("usage"):state["usage"]=job["usage"]
        if status=="completed":
            dump_state(state)
            return job
        if status in {"failed","cancelled","expired"}:
            state["error"]=str(job.get("error","Video generation failed"))[:350]
            dump_state(state)
            raise RuntimeError("Video job "+job_id+" ended as "+status+"; no auto resubmission")
        if status not in {"pending","in_progress"}:
            raise RuntimeError("Unexpected video job status "+str(status))
        dump_state(state)
        if time.monotonic()>=deadline:
            state["status"]="poll-timeout-job-may-still-run"
            dump_state(state)
            raise TimeoutError("Job id retained for resumption; do not resubmit a paid video job")
        time.sleep(25)

def download_video(job_id,key):
    url=API+"/videos/"+urllib.parse.quote(job_id,safe="")+"/content?index=0"
    request=urllib.request.Request(url,headers={"Authorization":"Bearer "+key})
    path=OUT/"SW-walk-then-attack.mp4"
    with urllib.request.urlopen(request,timeout=180) as res, open(path,"wb") as out:
        total=0
        while True:
            chunk=res.read(1024*1024)
            if not chunk:break
            total+=len(chunk)
            if total>MAX_VIDEO_BYTES:
                raise RuntimeError("Video exceeds 60MB safety cap")
            out.write(chunk)
    if not path.exists() or path.stat().st_size<2000:
        raise ValueError("Downloaded video missing or implausibly short")
    return path

def probe_video(path):
    cmd=["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)]
    meta=json.loads(subprocess.check_output(cmd,text=True,timeout=45))
    vids=[x for x in meta.get("streams",[]) if x.get("codec_type")=="video"]
    if not vids:
        raise ValueError("MP4 contains no video stream")
    track=vids[0]
    duration=float(meta.get("format",{}).get("duration") or track.get("duration") or 0)
    if duration<=0 or duration>MAX_SECONDS+4:
        raise ValueError("Video duration out of expected range: "+str(duration))
    return {"duration":duration,"width":track.get("width"),"height":track.get("height"),
            "fps":track.get("r_frame_rate"),"codec":track.get("codec_name"),
            "size_bytes":path.stat().st_size}

def contact_sheet(video,info):
    times=[0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5]
    w,h=320,245
    board=Image.new("RGB",(w*4,h*2+60),"#e7edf1")
    d=ImageDraw.Draw(board)
    d.rectangle((0,0,w*4,60),fill="#253747")
    d.text((15,12),"SW / WALK (0-4 s) THEN AXE ATTACK (4-8 s)",fill="white")
    d.text((15,35),"PREVIEW ONLY — visually verify movement, facing and equipment",fill="#c1d0dc")
    for i,t in enumerate(times):
        thumb=OUT/("sample-"+str(i+1).zfill(2)+".png")
        proc=subprocess.run(
            ["ffmpeg","-nostdin","-y","-loglevel","error","-ss",str(t),
             "-i",str(video),"-frames:v","1",str(thumb)],
            capture_output=True,text=True,timeout=50)
        if proc.returncode!=0 or not thumb.exists():
            raise RuntimeError(f"FFmpeg sample at {t}s failed: {proc.stderr[:250]}")
        im=Image.open(thumb).convert("RGB")
        im.thumbnail((w-12,h-38),Image.Resampling.LANCZOS)
        px=(i%4)*w+(w-im.width)//2
        py=60+(i//4)*h+27
        board.paste(im,(px,py))
        d.text(((i%4)*w+10,60+(i//4)*h+6),f"{t:.1f}s — "+("WALK" if i<4 else "ATTACK"),fill="#243a4e")
        thumb.unlink()
    path=OUT/"contact-sheet.jpg"
    board.save(path,quality=89,optimize=True)
    return path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args()
    config,source=validate()
    ref=make_256_reference(source)
    if args.dry_run:
        report(json.dumps({"valid":True,"direction":"SW","walk_seconds":4,
            "attack_seconds":4,"reference_px":[256,256],"model_priority":MODELS,
            "accepted_job_limit":1,"api_calls":0},ensure_ascii=False))
        return
    key=os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ValueError("OPENROUTER_API_KEY secret not configured")
    state_path=OUT/"job.json"
    if (OUT/"SW-walk-then-attack.mp4").exists():
        report("Output already exists; no additional generation submitted")
        return
    if state_path.exists():
        state=json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("job_id"):
            report("Resume existing accepted OpenRouter job, never resubmit")
        else:
            raise RuntimeError("Existing failed preflight: inspect job.json before any new submission")
    else:
        data=discover(key)
        state=submit_first_available(data,config,ref,key)
    try:
        completed=poll(state,key)
        video=download_video(state["job_id"],key)
        metrics=probe_video(video)
        contact_sheet(video,metrics)
        state.update(status="completed-downloaded",approved=False,
                     video_path=str(video.relative_to(ROOT)),video_sha256=sha256(video),
                     video_properties=metrics, usage=completed.get("usage") or state.get("usage"))
        dump_state(state)
        report(json.dumps({"video":str(video.relative_to(ROOT)),
            "bytes":metrics["size_bytes"],"duration_seconds":metrics["duration"],
            "model":state["model"],"reported_usage":state.get("usage"),
            "visual_approval":False},ensure_ascii=False))
    except Exception as exc:
        state["pipeline_error_type"]=type(exc).__name__
        state["pipeline_error"]=str(exc)[:500]
        dump_state(state)
        raise

if __name__=="__main__":
    main()
