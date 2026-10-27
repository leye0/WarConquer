#!/usr/bin/env python3
"""One targeted, non-retrying Muse correction of a rejected right-side T-pose."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "rig-source-turnaround-right-fix-request.json"
OUT = ROOT / "assets/experiments/rig-source-turnaround/marches_hache/tpose-v1"
RAW = ROOT / "rig-source-output/raw"
SHA = {
    "front": "ddaf1862304adc05d01157bda8caae57b8a549ade83ce70e3ace9638a8997d87",
    "back": "c7d3a260fd9fddcdf8da5cb8551bedb971452fcff6abda8308dfbd1fb193dce3",
    "left": "466d72dad88b8bd4da82c26da760e58b9450cbe457745497f446c3a5f2219c28",
    "right": "c014122823cc8ba9a5cfee864151faf4bb0a5580db8812f988ddc99b6d71b6f7",
}
PROMPT = """STRICT EXACT 90-DEGREE RIGHT PROFILE OF THE SAME WARCONQUER MALE AXEMAN IN T-POSE.

FIRST PROVIDED IMAGE is a MIRRORED LEFT SIDE silhouette; it is the *mandatory exact camera and bodily pose geometry* reference. Generate the physical opposite side, without duplicating asymmetrical decorations blindly. The other references identify the same person's hair, beard, body proportions, dark red ragged Marches warrior costume, black leather armor, belt and boots. Keep the same identity and exact scale.

REQUIRED CAMERA: pure orthographic EXACT RIGHT SIDE PROFILE, directly perpendicular to sagittal plane, 90 degrees from front. The man must look toward the RIGHT edge; only his ONE RIGHT SIDE eye and the nose profile visible. Torso must be SIDE-ON, an extremely NARROW silhouette like the first provided mirrored side-view silhouette. ZERO front chest surface, ZERO two-eyes face, ZERO three-quarter twist, ZERO diagonal pose. Strictly do not reproduce a frontal T-pose picture. Both arms fully outstretched sideways in world-space 3D T-pose at shoulder height: their projection overlaps along camera depth, NOT as two arms forming a horizontal line across the image. Hands EMPTY and OPEN. No weapon, axe, sword, shield or scenery. Spine and head vertical; knees straight; two boots on same baseline and in side-profile. Preserve anatomy and articulated-friendly gaps. No pixel art, no labels, no extra figure.

1024 square, isolated full body, feet/head in frame, generous safety margins, neutral diffuse lighting, detailed WarConquer hand-painted material fidelity, transparent background, otherwise absolutely uniform white. No perspective, no elevated RTS camera, no yaw offset, no camera tilt.
"""

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_muse():
    src=ROOT / "scripts/generate-standing-directions.py"
    spec=importlib.util.spec_from_file_location("warconquer_muse_repair",src)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def verify():
    cfg=json.loads(REQUEST.read_text(encoding="utf-8"))
    expected={
        "schema":1,"trial_id":"marches-axeman-tpose-right-profile-correction-v1",
        "reason":"right view was three-quarter, not orthographic side profile",
        "original_view_sha256":SHA,"maximum_new_paid_images":1,
        "automatic_paid_retries":0,
    }
    if cfg!=expected:
        raise ValueError("Mismatch with approved targeted right-profile correction")
    for name in ("front","back","left"):
        if digest(OUT/(name+".png"))!=SHA[name]:
            raise ValueError("Source changed since right-profile diagnosis: "+name)
    right=OUT/"right.png"
    if right.exists() and digest(right) not in (SHA["right"],):
        return False
    if not right.is_file():
        raise FileNotFoundError(right)
    if digest(right)!=SHA["right"]:
        raise ValueError("Original rejected right image changed")
    return True

def main():
    if not verify():
        print("Already repaired right profile: no paid retry.")
        return
    record=OUT/"right-fix-v1.json"
    if record.exists():
        print("Prior right fix submission exists. No automatic retry.")
        return
    if os.environ.get("OPENROUTER_IMAGE_MODEL")!="meta/muse-image" or not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("Expected OpenRouter Muse and configured API key")
    muse=load_muse()
    original=OUT/"right.png"
    shutil.copyfile(original, OUT/"right-rejected-threequarter.png")
    if (OUT/"right.json").is_file():
        shutil.copyfile(OUT/"right.json", OUT/"right-rejected-threequarter.json")
    with Image.open(OUT/"left.png") as opened:
        mirror=opened.convert("RGBA").transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    bio=io.BytesIO()
    mirror.save(bio,format="PNG")
    refs=[muse.reference_payload(bio.getvalue())[0],
          muse.reference_payload((OUT/"front.png").read_bytes())[0],
          muse.reference_payload((OUT/"back.png").read_bytes())[0]]
    marker={"trial_id":"marches-axeman-tpose-right-profile-correction-v1",
            "original_right_sha256":SHA["right"],"model":"meta/muse-image",
            "status":"paid-request-submitted-result-uncertain",
            "prompt":PROMPT}
    record.write_text(json.dumps(marker,indent=2)+"\n",encoding="utf-8")
    try:
        image,raw,usage=muse.call_muse(PROMPT,refs,"meta/muse-image")
        RAW.mkdir(parents=True,exist_ok=True)
        (RAW/"right-profile-fix-v1.png").write_bytes(raw)
        separated,matte=muse.extract_alpha(image)
        normalized,placement=muse.place_character(separated)
        candidate=OUT/"right-profile-candidate-v1.png"
        normalized.save(candidate)
        with Image.open(OUT/"left.png") as left:
            leftbbox=left.getchannel("A").point(lambda x: 255 if x>48 else 0).getbbox()
        candidatebbox=normalized.getchannel("A").point(lambda x: 255 if x>48 else 0).getbbox()
        lw=leftbbox[2]-leftbbox[0]
        rw=candidatebbox[2]-candidatebbox[0]
        ratio=rw/max(lw,1)
        too_broad=ratio>1.35 or ratio<.65
        marker.update(status="candidate-needs-visual-review" if too_broad else "geometric-profile-pass-needs-visual-review",
                      candidate_sha256=digest(candidate),profile_width_ratio_to_left=round(ratio,3),
                      profile_width_gate_passed=not too_broad,matte=matte,
                      normalized=placement,usage=usage)
        if not too_broad:
            shutil.copyfile(candidate,original)
            marker["accepted_as_current_right_source"]=True
            right_json=OUT/"right.json"
            right_json.write_text(json.dumps({
                "view":"right","status":"generated-needs-visual-approval",
                "source":"right-profile-correction-v1","sha256":digest(original),
                "profile_width_ratio_to_left":round(ratio,3),
                "warnings":[],"human_review_required":True,
                "original_right_sha256":SHA["right"]},indent=2)+"\n")
        else:
            marker["accepted_as_current_right_source"]=False
        report_path=OUT/"report.json"
        report=json.loads(report_path.read_text(encoding="utf-8"))
        report["right_profile_repair"]={k:marker[k] for k in ("status","profile_width_ratio_to_left",
                "profile_width_gate_passed","accepted_as_current_right_source")}
        report["ready_for_reconstruction"]=False
        report["warnings"]["right"]=[] if not too_broad else ["right_profile_not_narrow_enough"]
        report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
        sheet_script=ROOT/"scripts/generate-rig-source-turnaround.py"
        spec=importlib.util.spec_from_file_location("warconquer_tpose_sheet",sheet_script)
        sheet_module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sheet_module)
        sheet_module.contact_sheet([{"view":name,"status":"generated-needs-visual-approval"}
                                    for name in ("front","back","left","right")])
        if too_broad:
            raise RuntimeError("Candidate side profile remains too broad; source preserved for review")
    except Exception as exc:
        marker["error"]=str(exc)[:500]
        marker["failure_without_automatic_retry"]=True
        raise
    finally:
        record.write_text(json.dumps(marker,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
