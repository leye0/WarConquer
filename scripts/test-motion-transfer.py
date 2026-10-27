#!/usr/bin/env python3
"""One-shot Replicate motion-transfer pilot; never edits the approved driver."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import urlopen

from PIL import Image, ImageDraw
import imageio_ffmpeg

REQUEST = Path("motion-transfer-request.json")
MODEL = "bytedance/dreamactor-m2.0"
SOURCE = "assets/experiments/standing-turnaround/marches_hache/SW.png"
DRIVER = "assets/experiments/pose-guides/marches_hache/SW/pose-control-8s.mp4"
OUTPUT = "assets/experiments/motion-transfer/marches_hache/SW/dreamactor-m2.0"
PRICE_PER_SECOND = 0.05
TERMINAL = {"succeeded", "failed", "canceled"}


def load_request():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    expected = {
        "schema": 1,
        "trial_id": "sw-approved-driver-dreamactor-m2-2026-10-27",
        "model": MODEL,
        "source_image": SOURCE,
        "driving_video": DRIVER,
        "output_dir": OUTPUT,
        "duration_seconds": 8,
        "cut_first_second": True,
        "maximum_generations": 1,
        "maximum_estimated_cost_usd": 0.45,
    }
    if request != expected:
        raise ValueError("Trial request differs from the reviewed, one-call SW pilot.")
    return request


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(path):
    # imageio-ffmpeg bundles FFmpeg on GitHub runners; no system ffprobe is needed.
    frames = imageio_ffmpeg.read_frames(str(path))
    try:
        metadata = next(frames)
    finally:
        frames.close()
    width, height = metadata["size"]
    return {
        "duration_seconds": round(float(metadata["duration"]), 3),
        "width": width,
        "height": height,
        "frame_rate": metadata.get("fps"),
    }

def verified_inputs(request):
    source, driver = Path(SOURCE), Path(DRIVER)
    if not source.is_file() or not driver.is_file():
        raise FileNotFoundError("The approved SW image or motion video is missing.")
    if source.stat().st_size > 4_700_000:
        raise ValueError("SW artwork exceeds DreamActor input limit.")
    with Image.open(source) as im:
        if im.format != "PNG" or im.size != (1024, 1024):
            raise ValueError("Unexpected approved SW source dimensions or format.")
        im.verify()
    driving = probe(driver)
    if abs(driving["duration_seconds"] - request["duration_seconds"]) > 0.2:
        raise ValueError("Approved driver is not 8 seconds long.")
    if (driving["width"], driving["height"]) != (768, 768):
        raise ValueError("Unexpected pose-driver canvas size.")
    return {
        "source_image_sha256": digest(source),
        "driving_video_sha256": digest(driver),
        "driving_video": driving,
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def client():
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("REPLICATE_API_KEY GitHub secret is not available.")
    import replicate
    return replicate.Client(api_token=token)


def submit(request, fingerprints, output_dir):
    checkpoint = output_dir / "prediction.json"
    result = output_dir / "report.json"
    if result.exists():
        print("Trial already completed; zero new Replicate calls.")
        return
    if checkpoint.exists():
        prior = json.loads(checkpoint.read_text())
        if prior.get("trial_id") != request["trial_id"] or prior.get("inputs") != fingerprints:
            raise ValueError("Existing prediction belongs to different inputs; refusing new call.")
        print("Existing prediction:", prior["prediction_id"], "- zero new Replicate calls.")
        return

    api = client()
    # The Python SDK uploads local files; the secret never enters the input payload.
    with Path(SOURCE).open("rb") as image_file, Path(DRIVER).open("rb") as video_file:
        prediction = api.models.predictions.create(
            model=("bytedance", "dreamactor-m2.0"),
            input={
                "image": image_file,
                "video": video_file,
                "cut_first_second": request["cut_first_second"],
            },
        )
    if not prediction.id:
        raise RuntimeError("Replicate did not return a prediction ID; do not auto-retry.")
    write_json(checkpoint, {
        "schema": 1,
        "trial_id": request["trial_id"],
        "model": MODEL,
        "prediction_id": prediction.id,
        "initial_status": prediction.status,
        "inputs": fingerprints,
        "generative_calls_submitted": 1,
        "expected_cost_usd": round(request["duration_seconds"] * PRICE_PER_SECOND, 2),
        "note": "Paid prediction checkpoint. Never submit another for this trial ID.",
    })
    print("Submitted exactly one Replicate prediction:", prediction.id)


def create_contact_sheet(video_path, sheet_path):
    with tempfile.TemporaryDirectory(prefix="dreamactor-frames-") as folder:
        subprocess.run([
            imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(video_path), "-vf", "fps=4,scale=192:192:flags=lanczos",
            str(Path(folder) / "frame-%03d.png"),
        ], check=True)
        frames = sorted(Path(folder).glob("frame-*.png"))
        if not frames:
            raise RuntimeError("No video frames extracted for visual inspection.")
        cell_w, cell_h = 192, 218
        sheet = Image.new("RGB", (cell_w * 8, cell_h * 4), "#1d1e22")
        draw = ImageDraw.Draw(sheet)
        for i, frame_path in enumerate(frames[:32]):
            x = (i % 8) * cell_w
            y = (i // 8) * cell_h
            with Image.open(frame_path) as frame:
                sheet.paste(frame.convert("RGB"), (x, y))
            draw.text((x + 6, y + 195), f"{i / 4:.2f} s", fill="#ffffff")
        sheet.save(sheet_path, optimize=True)
        return len(frames)


def download_video(url, path):
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if parsed.scheme != "https" or not (
        hostname == "replicate.delivery" or hostname.endswith(".replicate.delivery")
    ):
        raise ValueError("Unexpected Replicate output host.")
    maximum_bytes = 80 * 1024 * 1024
    written = 0
    with urlopen(url, timeout=120) as response, path.open("wb") as f:
        while chunk := response.read(1024 * 1024):
            written += len(chunk)
            if written > maximum_bytes:
                raise ValueError("Generated output exceeds 80 MiB safety limit.")
            f.write(chunk)
    if written < 10_000:
        raise ValueError("Output video is unexpectedly small.")
    return written


def collect(request, fingerprints, output_dir):
    checkpoint_path = output_dir / "prediction.json"
    if not checkpoint_path.exists():
        raise RuntimeError("No submitted prediction to collect; refusing to create one.")
    checkpoint = json.loads(checkpoint_path.read_text())
    if checkpoint.get("trial_id") != request["trial_id"] or checkpoint.get("inputs") != fingerprints:
        raise ValueError("Prediction fingerprint mismatch; refusing to collect.")
    report_path = output_dir / "report.json"
    if report_path.exists():
        print("Existing completion report; nothing to regenerate.")
        return
    api = client()
    prediction_id = checkpoint["prediction_id"]
    deadline = time.monotonic() + 18 * 60
    prediction = None
    while time.monotonic() < deadline:
        prediction = api.predictions.get(prediction_id)
        print("Replicate prediction:", prediction_id, prediction.status, flush=True)
        if prediction.status in TERMINAL:
            break
        time.sleep(20)
    if prediction is None or prediction.status not in TERMINAL:
        raise TimeoutError(f"Prediction {prediction_id} still pending; resume collection, do not resubmit.")
    if prediction.status != "succeeded":
        write_json(report_path, {
            "status": prediction.status,
            "trial_id": request["trial_id"],
            "prediction_id": prediction_id,
            "error": str(prediction.error or "No video produced.")[:2000],
            "generative_calls_submitted": 1,
            "actual_cost_usd": None,
        })
        raise RuntimeError(f"Replicate prediction {prediction_id}: {prediction.status}")
    output_url = prediction.output
    if not isinstance(output_url, str):
        raise TypeError("Model output is not a video URL.")
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / "dreamactor-motion-transfer.mp4"
    byte_count = download_video(output_url, video_path)
    generated = probe(video_path)
    frames = create_contact_sheet(video_path, output_dir / "contact-sheet-4fps.png")
    duration = generated["duration_seconds"]
    report = {
        "status": "generated_not_visually_approved",
        "trial_id": request["trial_id"],
        "model": MODEL,
        "prediction_id": prediction_id,
        "source_image": SOURCE,
        "driving_video": DRIVER,
        "source_image_sha256": fingerprints["source_image_sha256"],
        "driving_video_sha256": fingerprints["driving_video_sha256"],
        "cut_first_second": request["cut_first_second"],
        "generative_calls_submitted": 1,
        "price_usd_per_output_second": PRICE_PER_SECOND,
        "estimated_cost_usd": round(duration * PRICE_PER_SECOND, 3),
        "video": "dreamactor-motion-transfer.mp4",
        "video_bytes": byte_count,
        "video_sha256": digest(video_path),
        "output_video": generated,
        "contact_sheet": "contact-sheet-4fps.png",
        "sampled_frames": frames,
        "visual_review_required": [
            "Does the model follow the skeletal driver rather than invent motion?",
            "Is the full-body Marches axeman faithful to SW.png?",
            "Is the axe rigid and correctly held throughout?",
            "Are walking and attacking phases intact without cuts or zoom?",
            "Is the character usable as a sprite with clean background?",
        ],
    }
    write_json(report_path, report)
    print("Generated", generated, "estimated USD", report["estimated_cost_usd"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["validate", "submit", "collect"])
    args = parser.parse_args()
    request = load_request()
    fingerprints = verified_inputs(request)
    out = Path(OUTPUT)
    if args.stage == "validate":
        print("Approved source & 8s motion intact. Cost estimate: USD 0.40. No API call.")
    elif args.stage == "submit":
        submit(request, fingerprints, out)
    else:
        collect(request, fingerprints, out)


if __name__ == "__main__":
    main()
