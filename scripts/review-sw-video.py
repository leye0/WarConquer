#!/usr/bin/env python3
"""Review an already generated MP4: no API calls, no video generation credits."""
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/experiments/video-sw"
source = OUT / "SW-walk-then-attack.mp4"
statefile = OUT / "job.json"

def main():
    if not source.is_file() or source.stat().st_size < 2000:
        raise RuntimeError("Expected existing SW MP4 in main, refusing to generate anything")
    if not statefile.is_file():
        raise RuntimeError("Missing pre-existing video job metadata")
    state = json.loads(statefile.read_text(encoding="utf-8"))
    if state.get("model") != "x-ai/grok-imagine-video-1.5-lite" or not state.get("job_id"):
        raise RuntimeError("No verified previous accepted video job")
    module = runpy.run_path(str(ROOT / "scripts/generate-sw-video.py"))
    metrics = module["probe_video"](source)
    overview = module["contact_sheet"](source, metrics)
    state.update({
        "status":"completed-downloaded", "approved":False,
        "video_path":str(source.relative_to(ROOT)),
        "video_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "video_properties":metrics,
        "visual_review_path":str(overview.relative_to(ROOT)),
        "review_status":"contact-sheet-ready-requires-human-review",
    })
    state.pop("pipeline_error",None)
    state.pop("pipeline_error_type",None)
    statefile.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"video":str(source.relative_to(ROOT)),
        "contact_sheet":str(overview.relative_to(ROOT)),
        "duration":metrics["duration"],
        "size_bytes":metrics["size_bytes"],
        "model":state["model"],
        "cost_reported":state.get("usage",{}).get("cost"),
        "video_generation_calls":0},ensure_ascii=False))

if __name__=="__main__":main()
