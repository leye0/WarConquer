#!/usr/bin/env python3
"""Animate the existing SW painted sprite using the *approved* deterministic guide.

This is a reproducible articulated cut-out preview, not a generative video or
human-approved final sprite. It never changes the motion driver or source PNG.
The manual segmentation is intentionally local to the single calibrated SW art.
"""
import hashlib
import importlib.util
import json
import math
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "rigged-asset-request.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
GUIDE_CONFIG = json.loads((ROOT / CONFIG["guide_request"]).read_text(encoding="utf-8"))
if (CONFIG.get("direction"), CONFIG.get("asset_id"), GUIDE_CONFIG.get("profile")) != (
        "SW", "marches_hache", "sw_walk_attack_8s"):
    raise ValueError("This registration is calibrated for marches_hache SW only")
if CONFIG.get("generative_model_calls_allowed") != 0:
    raise ValueError("Generative calls are not part of this stage")
SRC = (ROOT / CONFIG["source_image"]).resolve()
OUT = (ROOT / CONFIG["output_dir"]).resolve()
if not SRC.is_relative_to(ROOT) or not OUT.is_relative_to(
        (ROOT / "assets/experiments/asset-animations").resolve()):
    raise ValueError("Paths must stay within their designated repository folders")

spec = importlib.util.spec_from_file_location("approved_motion", ROOT / "scripts/build-pose-guide.py")
motion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(motion)
WIDTH = motion.SIZE
FPS = motion.FPS
FRAMES = motion.FRAMES
SAFE = motion.SAFE
REG = CONFIG["manual_registration"]
PARTS = ("left_thigh", "right_thigh", "left_shin", "right_shin", "torso",
         "head", "left_upper_arm", "right_upper_arm", "axe",
         "left_forearm", "right_forearm")
COLORS = {
    "head": "#ead784", "left_thigh": "#e68d81", "left_shin": "#e65b83",
    "right_thigh": "#6da6ee", "right_shin": "#3b75b1",
    "left_upper_arm": "#edb867", "left_forearm": "#ef894b",
    "right_upper_arm": "#98c99d", "right_forearm": "#58b5a2",
    "axe": "#75d8d6", "torso": "#cc92cf"
}
TARGET_BONES = {
    "torso": ("chest", "pelvis"),
    "head": ("neck", "head"),
    "left_thigh": ("left_hip", "left_knee"),
    "left_shin": ("left_knee", "left_ankle"),
    "right_thigh": ("right_hip", "right_knee"),
    "right_shin": ("right_knee", "right_ankle"),
    "left_upper_arm": ("left_shoulder", "left_elbow"),
    "left_forearm": ("left_elbow", "left_hand"),
    "right_upper_arm": ("right_shoulder", "right_elbow"),
    "right_forearm": ("right_elbow", "right_hand"),
    "axe": ("handle_grip", "head_center")
}


def segments(source):
    if source.size != tuple(REG["image_size_px"]):
        raise ValueError(f"Registration expects {REG['image_size_px']}, got {source.size}")
    alpha = source.getchannel("A")
    bbox = alpha.point(lambda v: 255 if v >= 30 else 0).getbbox()
    if bbox is None:
        raise ValueError("Empty source alpha")
    crop = source.crop(bbox)
    # Identical source-to-guide placement used by build-pose-guide.py.
    ratio = min(269 / crop.height, 207 / crop.width)
    scaled_size = (round(crop.width * ratio), round(crop.height * ratio))
    left = round(motion.START_ROOT[0] - 28) - scaled_size[0] // 2
    top = round(motion.START_ROOT[1]) - scaled_size[1]
    origin = (left, top)

    def point_from_source(pt):
        return (left + (pt[0] - bbox[0]) * scaled_size[0] / crop.width,
                top + (pt[1] - bbox[1]) * scaled_size[1] / crop.height)

    polygons = {}
    occupied = Image.new("L", source.size)
    coverage = {}
    for key, points in REG["polygons"].items():
        if key not in TARGET_BONES:
            raise ValueError(f"Unknown region {key}")
        mask = Image.new("L", source.size)
        ImageDraw.Draw(mask).polygon([tuple(p) for p in points], fill=255)
        polygons[key] = mask
        occupied = ImageChops.lighter(occupied, mask)
        coverage[key] = ImageChops.multiply(alpha, mask).getbbox()
        if coverage[key] is None:
            raise ValueError(f"Segment '{key}' contains no source pixels")

    base_mask = ImageChops.invert(occupied)
    polygons["torso"] = base_mask
    images = {}
    for key, mask in polygons.items():
        layer = source.copy()
        layer.putalpha(ImageChops.multiply(alpha, mask))
        tile = layer.crop(bbox).resize(scaled_size, Image.Resampling.LANCZOS)
        aligned = Image.new("RGBA", (WIDTH, WIDTH))
        aligned.alpha_composite(tile, origin)
        images[key] = aligned

    anchors = {
        key: tuple(point_from_source(pt) for pt in REG["anchors"][key])
        for key in TARGET_BONES
    }
    return images, anchors, {
        "alpha_bbox": list(bbox), "rect": [left, top, left + scaled_size[0], top + scaled_size[1]],
        "mask_regions": {key: list(box) for key, box in coverage.items()},
        "source_dimensions": list(source.size),
        "moving_source_coverage_percent": round(
            100 * sum(ImageChops.multiply(alpha, occupied).histogram()[1:]) /
            max(1, sum(alpha.histogram()[1:])), 2),
    }


def transform_for_two_points(src_a, src_b, dst_a, dst_b):
    sx, sy = (src_b[0] - src_a[0], src_b[1] - src_a[1])
    tx, ty = (dst_b[0] - dst_a[0], dst_b[1] - dst_a[1])
    sl = math.hypot(sx, sy)
    tl = math.hypot(tx, ty)
    if sl < 1 or tl < 1:
        raise ValueError("Invalid source or target bone")
    scale = tl / sl
    theta = math.atan2(ty, tx) - math.atan2(sy, sx)
    cs, sn = math.cos(theta), math.sin(theta)
    # PIL requires inverse mapping: output -> original source coordinates.
    a, b, d, e = cs / scale, sn / scale, -sn / scale, cs / scale
    c = src_a[0] - a * dst_a[0] - b * dst_a[1]
    f = src_a[1] - d * dst_a[0] - e * dst_a[1]
    return (a, b, c, d, e, f), scale, math.degrees(theta)


def target_ends(state, key):
    name_a, name_b = TARGET_BONES[key]
    values = state["axe"] if key == "axe" else state["joints"]
    return tuple(values[name_a]), tuple(values[name_b])


def draw_frame(state, images, anchors):
    frame = Image.new("RGBA", (WIDTH, WIDTH))
    stats = {}
    for key in PARTS:
        a, b = target_ends(state, key)
        affine, scale, angle = transform_for_two_points(
            *anchors[key], a, b)
        part = images[key].transform(
            (WIDTH, WIDTH), Image.Transform.AFFINE, affine,
            resample=Image.Resampling.BICUBIC,
            fillcolor=(0, 0, 0, 0))
        frame.alpha_composite(part)
        stats[key] = {"scale": scale, "angle_deg": angle}
    return frame, stats


def register_sheet(images, anchors, meta):
    base = Image.new("RGBA", (WIDTH, WIDTH))
    for key in PARTS:
        base.alpha_composite(images[key])
    neutral = Image.new("RGBA", (WIDTH, WIDTH), "#f4f1e9")
    neutral.alpha_composite(base)
    guide = motion.get_pose(0)
    overlay = neutral.convert("RGB")
    motion.draw_pose(overlay, guide, debug=True)
    overlay.save(OUT / "source-registration.png", optimize=True)

    tinted = Image.new("RGBA", (WIDTH, WIDTH), "#f4f1e9")
    for key in PARTS:
        alpha = images[key].getchannel("A").point(lambda v: round(v * .75))
        swatch = Image.new("RGBA", (WIDTH, WIDTH), COLORS[key])
        swatch.putalpha(alpha)
        tinted.alpha_composite(swatch)
    d = ImageDraw.Draw(tinted)
    for key in PARTS:
        pt = anchors[key][0]
        d.ellipse((pt[0] - 3, pt[1] - 3, pt[0] + 3, pt[1] + 3), fill="white")
    d.text((22, 24), "SW SOURCE MASK REGISTRATION - NOT A SPRITE", fill="#25394b")
    d.text((22, 46), "axe / arm / legs / head / rigid torso", fill="#25394b")
    tinted.convert("RGB").save(OUT / "mask-registration.png", optimize=True)


def encode_video(frames, path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
               f"{WIDTH}x{WIDTH}", "-r", str(FPS), "-i", "-",
               "-an", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "19", "-pix_fmt", "yuv420p", str(path)]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in frames:
            bg = Image.new("RGB", (WIDTH, WIDTH), "#f4f1e9")
            bg.paste(frame, (0, 0), frame.getchannel("A"))
            proc.stdin.write(bg.tobytes())
        proc.stdin.close()
        error = proc.stderr.read().decode("utf-8", "replace")
        code = proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    if code or path.stat().st_size < 1000:
        raise RuntimeError(f"FFmpeg encode failed: {code}: {error[-1500:]}")


def contact_sheet_from_ffmpeg(video_path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="wc-rig-samples-") as folder:
        pattern = str(Path(folder) / "sample-%03d.png")
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(video_path), "-vf", "fps=4",
                        "-vsync", "vfr", pattern], check=True)
        samples = sorted(Path(folder).glob("sample-*.png"))
        if len(samples) != 32:
            raise RuntimeError(f"4/s inspection expected 32 samples, got {len(samples)}")
        w, h = 250, 282
        sheet = Image.new("RGB", (4 * w, 8 * h + 56), "#e5ebed")
        d = ImageDraw.Draw(sheet)
        d.rectangle((0, 0, sheet.width, 55), fill="#25394b")
        d.text((16, 20), "WARCONQUER / SW CUT-OUT RIG / 4 SAMPLES PER SECOND", fill="white")
        for i, sample in enumerate(samples):
            with Image.open(sample) as thumb:
                img = thumb.convert("RGB").resize((w - 8, w - 26), Image.Resampling.LANCZOS)
                x, y = (i % 4) * w + 4, (i // 4) * h + 60
                sheet.paste(img, (x, y + 20))
                d.text((x + 2, y + 3), f"{i / 4:.2f}s " +
                       ("WALK" if i < 16 else "ATTACK"), fill="#263948")
        sheet.save(OUT / "contact-sheet-32.png", optimize=True)
        return len(samples)


def main():
    if not SRC.is_file():
        raise FileNotFoundError(SRC)
    OUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SRC).convert("RGBA")
    images, anchors, calibration = segments(source)
    states = [motion.get_pose(i / FPS) for i in range(FRAMES)]
    prior = motion.check(states)
    if prior["status"] != "PASS":
        raise RuntimeError("Approved guide failed validation - refusing to render")
    register_sheet(images, anchors, calibration)
    rendered = []
    scale_ranges = {key: [] for key in PARTS}
    safe_distances = []
    frames_with_empty_subject = []
    for idx, state in enumerate(states):
        frame, stats = draw_frame(state, images, anchors)
        rendered.append(frame)
        for key in PARTS:
            scale_ranges[key].append(stats[key]["scale"])
        bbox = frame.getchannel("A").getbbox()
        if bbox is None:
            frames_with_empty_subject.append(idx)
            continue
        safe_distances.append(min(bbox[0] - SAFE, bbox[1] - SAFE,
                                  WIDTH - SAFE - bbox[2], WIDTH - SAFE - bbox[3]))
    if frames_with_empty_subject or min(safe_distances) < 0:
        raise RuntimeError(f"Frame outside safe area or empty: {frames_with_empty_subject}; "
                           f"clearance={min(safe_distances, default=-1):.2f}")

    video_path = OUT / "rigged-asset-8s.mp4"
    encode_video(rendered, video_path)
    inspected = contact_sheet_from_ffmpeg(video_path)
    report = {
        "status": "REVIEW_REQUIRED", "technical_checks": "PASS",
        "preview_only": True, "not_human_approved": True,
        "source": CONFIG["source_image"], "source_sha256":
            hashlib.sha256(SRC.read_bytes()).hexdigest(),
        "guide": CONFIG["guide_request"],
        "profile": GUIDE_CONFIG["profile"], "guide_profile_changed": False,
        "source_registration": calibration,
        "frames": len(rendered), "duration_seconds": FRAMES / FPS, "fps": FPS,
        "canvas_px": [WIDTH, WIDTH], "phase_boundaries_seconds": [0, 4, 8],
        "full_frame_fixed_camera": True,
        "frame_samples_extracted_by_ffmpeg": inspected,
        "minimum_silhouette_safe_area_clearance_px": round(min(safe_distances), 2),
        "segment_scale_range": {
            key: [round(min(values), 3), round(max(values), 3)]
            for key, values in scale_ranges.items()},
        "rigid_axe": True, "axe_hand": "anatomical RIGHT, screen-left in SW source",
        "axe_joint_control": ["handle_grip", "head_center"],
        "cost_usd": 0, "model_calls": 0,
        "limitations": [
            "This is an explicitly manually masked 2D cut-out prototype, not inferred anatomy.",
            "Rigid bone transforms may expose joint seams and cannot synthesize hidden garment surfaces.",
            "The decorative painted axe head is rigid and its visible silhouette may exceed the schematic blade polygon.",
            "Human review of mask coverage, hand grip, silhouette continuity, anatomy and action legibility is required."
        ]
    }
    (OUT / "metrics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# WarConquer · first painted SW rig preview\n\n"
        "This renders the **existing WarConquer SW PNG**, with calibrated "
        "part masks and the approved `sw_walk_attack_8s` guide. "
        "**Not an approved final animation.** No generative calls/cost.\n\n"
        "- [8-second continuous painted-asset preview](rigged-asset-8s.mp4)\n"
        "- [32 FFmpeg-extracted samples, four per second](contact-sheet-32.png)\n"
        "- [Manual segmentation colors](mask-registration.png)\n"
        "- [Source / guide registration](source-registration.png)\n"
        "- [Validation and limitations](metrics.json)\n\n"
        "Motion profile and source are unchanged. Human visual approval is required "
        "before any appearance-refinement model or downstream sprite export.\n",
        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
