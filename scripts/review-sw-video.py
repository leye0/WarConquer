#!/usr/bin/env python3
"""Build visual evidence from a *previously completed* OpenRouter MP4.

Uses imageio-ffmpeg's bundled FFmpeg binary; does NOT call OpenRouter,
does NOT submit a new job, and needs no apt or system ffprobe.
"""
import hashlib
import json
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"assets/experiments/video-sw"
MP4=OUT/"SW-walk-then-attack.mp4"
JOB=OUT/"job.json"
TIMES=[.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5]

def main():
    if not MP4.is_file() or MP4.stat().st_size<2000:
        raise ValueError("Previously generated MP4 missing; do not generate a new video")
    state=json.loads(JOB.read_text(encoding="utf-8"))
    if state.get("model")!="x-ai/grok-imagine-video-1.5-lite" or not state.get("job_id"):
        raise ValueError("Missing verified successful OpenRouter job ID")
    width,height=310,247
    canvas=Image.new("RGB",(width*4,height*2+63),"#e4eaf0")
    painter=ImageDraw.Draw(canvas)
    painter.rectangle((0,0,width*4,62),fill="#1e3447")
    painter.text((18,13),"SW VIDEO / 0-4s WALK SOUTHWEST / 4-8s AXE ATTACK SOUTHWEST",fill="#ffffff")
    painter.text((18,38),"One existing OpenRouter video. Inspect facing and both timed phases.",fill="#c4d3df")
    frames=imageio_ffmpeg.read_frames(str(MP4),pix_fmt="rgb24",output_params=["-vf","fps=1"])
    try:
        metadata=next(frames)
        dims=metadata["size"]
        count=0
        for i,frame in enumerate(frames):
            if i>=8:break
            picture=Image.frombytes("RGB",dims,frame)
            picture.thumbnail((width-12,height-34),Image.Resampling.LANCZOS)
            x=(i%4)*width+(width-picture.width)//2
            y=63+(i//4)*height+29
            canvas.paste(picture,(x,y))
            text="WALK" if i<4 else "ATTACK"
            painter.text(((i%4)*width+12,63+(i//4)*height+8),f"{TIMES[i]:.1f}s   {text}",fill="#273f53")
            count+=1
    finally:
        try: frames.close()
        except Exception:pass
    if count!=8:
        raise ValueError(f"Decoded only {count} of 8 required video review frames")
    overview=OUT/"contact-sheet.jpg"
    canvas.save(overview,quality=90,optimize=True)
    state.update({
        "status":"completed-downloaded","approved":False,
        "video_path":str(MP4.relative_to(ROOT)),
        "video_sha256":hashlib.sha256(MP4.read_bytes()).hexdigest(),
        "video_properties":{
            "width":dims[0],"height":dims[1],
            "duration_seconds":metadata.get("duration"),
            "source_fps":metadata.get("fps"),
            "bytes":MP4.stat().st_size,
        },
        "visual_review_path":str(overview.relative_to(ROOT)),
        "review_status":"eight-sampled-frames-require-human-inspection",
    })
    state.pop("pipeline_error",None)
    state.pop("pipeline_error_type",None)
    JOB.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "video":str(MP4.relative_to(ROOT)),
        "sampled_frames":count,
        "review":str(overview.relative_to(ROOT)),
        "model":state["model"],
        "usage":state.get("usage"),
        "new_video_jobs":0,
    }))

if __name__=="__main__":
    main()
