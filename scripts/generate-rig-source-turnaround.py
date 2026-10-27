#!/usr/bin/env python3
"""Build four rig-friendly orthographic T-pose references with OpenRouter Muse.

One billed request per missing view. No paid retries or automatic approval.
The supplied medieval character is an appearance reference, not a pose guide.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "rig-source-turnaround-request.json"
SOURCE = ROOT / "assets/concepts/marches/units/hache.png"
OUTPUT = ROOT / "assets/experiments/rig-source-turnaround/marches_hache/tpose-v1"
RAW = ROOT / "rig-source-output/raw"
ORDER = ("front", "back", "left", "right")
VIEWS = {
    "front": "FRONT: person faces camera, complete face and chest visible, perfectly symmetrical elevation, no three-quarter angle",
    "back": "BACK: person faces straight away from camera, back of head, back of torso and boots visible, face never visible",
    "left": "LEFT SIDE: true 90 degree orthographic profile, face and toes point toward the LEFT edge of the image, no three-quarter view",
    "right": "RIGHT SIDE: true 90 degree orthographic profile, face and toes point toward the RIGHT edge of the image, no three-quarter view",
}
COMMON = """Reconstruct the SAME adult male medieval-fantasy Marches axeman from the WarConquer original reference as a high-fidelity FULL-BODY CHARACTER MODEL TURNAROUND REFERENCE for 3D automatic rigging. Preserve the exact identity, head, hair, tunic, leather, fabric, armor shape, muted oxblood-red/charcoal/aged-copper materials, repair seams and garment placement. The reference is for APPEARANCE ONLY: deliberately CHANGE the original action/idle pose into the neutral rigging pose defined below. Same anatomy, unchanged clothing and proportions in every view, no redesign.

MANDATORY EXACT STRICT T-POSE: head centered above spine, back and torso vertical, pelvis neutral, shoulders at equal height, BOTH arms extended straight outward from shoulders at 90 degrees from torso, forming a single horizontal line from LEFT fingertips through shoulders to RIGHT fingertips. Both elbows straight, wrists straight, hands OPEN, fingers together, palms facing downward, two arms distinct and visibly separate from torso. Both legs straight and apart at hip width, knees straight but relaxed, each complete boot separate and touching the same invisible floor level. NO A-pose; arms must NOT slope down. NO bent elbows, NO hands on hips, NO crossed legs, NO walking, NO jumping, NO lean, NO attack or motion.

NO axe, NO sword, NO shield, NO handheld prop, NO long rigid object, NO backpack, NO loose dangling accessories between arms and torso, NO cloak or flowing cape that joins the hands to the hips. Equipment will be modeled separately after rigging. Keep close-fitting garments so that shoulder, elbow, hip and knee boundaries remain clear. This clean character must have exactly two hands and two boots.

CAMERA: one single isolated character, straight-on orthographic camera at the midpoint of the body, no elevated RTS camera, no perspective, no tilt, roll or isometric angle, uniform scale and body proportions. REQUIRED VIEW: {view}. Keep the entire head, ALL fingertips, both separated legs and both complete boots in frame with generous blank padding. Reference image proportions 1024 by 1024, upright vertical character, centered, same common feet baseline. Sharp detailed painterly WarConquer design, realistic contours and anatomically coherent clothing, neutral diffuse lighting. Transparent background; failing alpha, solid PURE WHITE backdrop. No scenery, no floor, no shadow, no ground plane, no text, no layout, no multiple views, no labels, no border, no guides, no extra figures.
"""

def load_muse():
    script = ROOT / "scripts/rig-muse-helpers.py"
    spec = importlib.util.spec_from_file_location("warconquer_muse_stills", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def request_config():
    actual = json.loads(REQUEST.read_text(encoding="utf-8"))
    expected = {
        "schema": 1,
        "trial_id": "marches-axeman-strict-tpose-v1-2026-10-27",
        "character": "marches_hache",
        "reference": str(SOURCE.relative_to(ROOT)),
        "pose": "strict_t_pose",
        "camera": "eye_level_orthographic",
        "views": list(ORDER),
        "hands": "empty_open",
        "weapons": "separate_after_rigging",
        "output_directory": str(OUTPUT.relative_to(ROOT)),
        "image_provider": "OpenRouter",
        "image_model": "meta/muse-image",
        "maximum_paid_images": 4,
        "automatic_paid_retries": 0,
        "reconstruction_requires_visual_approval": True,
    }
    if actual != expected:
        raise ValueError("Rig-source trial differs from the locked one-shot request")
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    return actual

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pose_checks(image, direction):
    """Conservative pixel checks; never mistake these for visual pose approval."""
    alpha = np.asarray(image.getchannel("A"), dtype=np.uint8) > 48
    yy, xx = np.where(alpha)
    if len(xx) < 18000:
        return ["too_few_foreground_pixels"], {}
    l, r, t, b = int(xx.min()), int(xx.max()) + 1, int(yy.min()), int(yy.max()) + 1
    width, height = r - l, b - t
    bounds = [l, t, r, b]
    warnings = []
    if min(l, t, 1024-r, 1024-b) < 40:
        warnings.append("weak_safety_margins")
    if height < 460 or height > 850:
        warnings.append("unexpected_character_height")
    if direction in ("front", "back"):
        # Horizontal T-pose arms give a near human-height-wide silhouette.
        if width / max(height, 1) < .67:
            warnings.append("narrow_silhouette_arms_may_not_be_horizontal")
        # Long horizontal stroke should be in the upper third of the figure.
        upper = alpha[t + round(height * .17):t + round(height * .41), l:r]
        broad = max((np.ptp(np.flatnonzero(row)) + 1 for row in upper if row.any()), default=0)
        if broad / max(width, 1) < .83:
            warnings.append("missing_full_width_shoulder_arm_stroke")
    return warnings, {"foreground_bbox": bounds, "width_height_ratio": round(width / height, 3),
                      "foreground_pixels": len(xx)}

def contact_sheet(rows):
    tile, gap, header = 440, 12, 86
    board = Image.new("RGB", (tile * 4 + gap * 5, tile + header + gap * 2), "#e2e8ec")
    draw = ImageDraw.Draw(board)
    draw.rectangle((0, 0, board.width, header), fill="#1f3446")
    draw.text((20, 15), "WARCONQUER / RIG SOURCES / STRICT T-POSE / MUSE", fill="white")
    draw.text((20, 44), "ORTHOGRAPHIC FRONT / BACK / LEFT / RIGHT - HUMAN VISUAL REVIEW REQUIRED", fill="#c6d9e5")
    results = {r["view"]: r for r in rows}
    for idx, direction in enumerate(ORDER):
        x = gap + idx * (tile + gap)
        y = header + gap
        draw.rectangle((x, y, x + tile, y + tile), fill="#f8fafb", outline="#bac8d1", width=2)
        p = OUTPUT / (direction + ".png")
        if p.is_file():
            with Image.open(p) as pic:
                image = pic.convert("RGBA")
                image.thumbnail((tile - 10, tile - 28), Image.Resampling.LANCZOS)
                board.paste(image, (x + (tile - image.width) // 2, y + 26), image)
        else:
            draw.text((x + 110, y + 200), "NOT GENERATED", fill="#b23a32")
        status = results.get(direction, {}).get("status", "not-started")
        draw.text((x + 12, y + 10), direction.upper() + " / " + status[:32], fill="#233a4e")
    board.save(OUTPUT / "review-four-tpose-views.png", optimize=True)

def run():
    request = request_config()
    source_sha = digest(SOURCE)
    model = os.environ.get("OPENROUTER_IMAGE_MODEL", "").strip()
    if model != request["image_model"]:
        raise ValueError("Expected configured OpenRouter Muse model; refusing alternate model")
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise ValueError("Missing OpenRouter key")
    muse = load_muse()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    blocked = False
    for direction in ORDER:
        target = OUTPUT / (direction + ".png")
        record_path = OUTPUT / (direction + ".json")
        if target.is_file():
            with Image.open(target) as opened:
                warnings, geometry = pose_checks(opened.convert("RGBA"), direction)
            row = {"view": direction, "status": "existing-unapproved", "warnings": warnings,
                   "geometry": geometry, "source_sha256": source_sha, "sha256": digest(target)}
            print("REUSE", direction, "without a paid call", flush=True)
        elif record_path.is_file():
            row = {"view": direction, "status": "blocked-existing-submission-record",
                   "note": "Previous generation outcome uncertain or failed; no automatic paid retry."}
            blocked = True
        elif blocked:
            row = {"view": direction, "status": "blocked-after-front-pose-failure"}
        else:
            refs = [muse.reference_payload(SOURCE.read_bytes())[0]]
            if direction != "front":
                front = OUTPUT / "front.png"
                if not front.is_file():
                    raise RuntimeError("A validated front image is required before other views")
                refs.append(muse.reference_payload(front.read_bytes())[0])
            prompt = COMMON.format(view=VIEWS[direction])
            row = {"view": direction, "view_definition": VIEWS[direction],
                   "status": "paid-request-submitted-result-uncertain",
                   "prompt": prompt, "reference_sha256": source_sha,
                   "reference_views": ["original"] + (["front"] if direction != "front" else []),
                   "model": model}
            # An uncertain API response cannot be retried automatically.
            record_path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
            try:
                pic, raw, usage = muse.call_muse(prompt, refs, model)
                raw_path = RAW / (direction + ".png")
                raw_path.write_bytes(raw)
                cut, matte = muse.extract_alpha(pic)
                normalized, placement = muse.place_character(cut)
                normalized.save(target)
                warnings, geometry = pose_checks(normalized, direction)
                row.update(status="generated-needs-visual-approval", warnings=warnings,
                           geometry=geometry, placement=placement,
                           source_image_size=list(pic.size), matte=matte,
                           sha256=digest(target), usage=usage)
                print("GENERATED", direction, "warnings:", warnings, flush=True)
                if direction == "front" and any(w in warnings for w in
                    ("narrow_silhouette_arms_may_not_be_horizontal",
                     "missing_full_width_shoulder_arm_stroke")):
                    blocked = True
                    print("Front T-pose silhouette doubtful. Halting paid view generation.", flush=True)
            except Exception as exc:
                row.update(status="failed-no-automatic-retry",
                           error_type=type(exc).__name__, error=str(exc)[:400])
                blocked = True
                print("::error title=Rig source failure::" + direction + " " + str(exc)[:250], flush=True)
        record_path.write_text(json.dumps(row, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        rows.append(row)
    contact_sheet(rows)
    generated = sum((OUTPUT / (name + ".png")).is_file() for name in ORDER)
    warnings = {r["view"]: r.get("warnings", []) for r in rows}
    report = {"trial_id": request["trial_id"], "reference_sha256": source_sha,
              "model": model, "expected_views": list(ORDER), "present_views": generated,
              "maximum_paid_images": 4, "no_paid_retry": True, "warnings": warnings,
              "human_pose_orientation_identity_review": "REQUIRED",
              "ready_for_reconstruction": False,
              "note": "The four images must be visually inspected for a strict, consistent T-pose before the one-shot paid 3D reconstruction.",
              "results": [{"view": r["view"], "status": r["status"]} for r in rows]}
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"present_views": generated, "requires_review": True, "warnings": warnings}), flush=True)
    if generated != 4 or any(warnings.values()):
        raise SystemExit("Rig-source turnaround incomplete or automatic pose concerns; review outputs.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args()
    r = request_config()
    if opts.dry_run:
        print(json.dumps({"trial": r["trial_id"], "views": list(ORDER), "max_paid_calls": 4,
                          "source_sha256": digest(SOURCE), "pose": "strict_t_pose"}))
        return
    run()

if __name__ == "__main__":
    main()
