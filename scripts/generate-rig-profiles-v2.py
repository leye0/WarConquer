#!/usr/bin/env python3
"""V2 orthographic side views with one invariant world-space T-pose.

The original front/back source images remain frozen, old v1 profiles remain
recoverable, and each new side view is generated at most once via Muse.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "rig-source-profiles-v2-request.json"
SRC = ROOT / "assets/experiments/rig-source-turnaround/marches_hache/tpose-v1"
OUT = ROOT / "assets/experiments/rig-source-turnaround/marches_hache/tpose-v2"
RAW = ROOT / "rig-source-output/raw-v2"
FRONT_SHA = "ddaf1862304adc05d01157bda8caae57b8a549ade83ce70e3ace9638a8997d87"
BACK_SHA = "c7d3a260fd9fddcdf8da5cb8551bedb971452fcff6abda8308dfbd1fb193dce3"
ORDER = ("front","back","left","right")
FROZEN_PROMPT_SHA256 = {
    "left": "49745dbdeb16cd98a2a76040b28af6e8191dd5e20ba7de76488713023d3b4e2e",
    "right": "49208793d48c9d9dc263639f564ae8c0fda269c74ded2a3be80e70df927c07ed",
}
POSE = """ONE SAME WarConquer adult male Marches axeman. Copy his identity, face, beard, long dark-red tied hair, leather-and-dark-red-cloth outfit, patched fabric, charcoal armor, boots and proportions from the supplied character paintings. The prior images are appearance references, not invitations to change camera position.

IMMUTABLE WORLD-SPACE 3D SKELETON: +Z vertical head-up; +Y body forward (nose); +X anatomically left; -X anatomically right. The head, neck, spine, pelvis are vertical; shoulders same height. The arms are physically extended from the shoulders along world axes +X and -X, elbows and wrists straight, hands OPEN and EMPTY. This is a true standard 3D T-pose, not a gesture toward the screen. Both legs straight, slight hip-width separation, feet flat at Z=0. NO altered arm rotation in any view. No axe, weapons, shield, held props or cape bridging limbs. Same body proportions in every view.

ORTHOGRAPHIC CAMERA at shoulder height, horizontal, no elevated/isometric RTS angle, no perspective distortion. The CAMERA ROTATES around the stationary body; the BODY NEVER TURNS or changes its skeletal pose. Full person alone centered on 1024 square frame, 12 percent margins, shared boot baseline, transparent background (else uniform pure white), neutral lighting. Detailed hand-painted WarConquer materials, not a stylized diagram. No scenery, ground shadow, labels, extra arms, text, collage, mirror duplicates.
"""
SIDE = {
    "left": """CAMERA AT THE CHARACTER'S EXACT LEFT SIDE: pure 90-degree orthographic profile; nose and toes point toward image LEFT. Only one side of the face and narrow side of chest is visible. Crucial 3D projection: BOTH ARMS ARE STILL EXTENDED SIDEWAYS ALONG THE CHARACTER'S X AXIS INTO/OUT OF THE CAMERA, so the image-side projection of these arms is strongly FORESHORTENED, largely OVERLAPPING the shoulder and upper torso, NOT a long arm sticking out in front of the person's nose or pointing toward image left/right. Shoulder armor and gloved hand may be partly occluded at shoulder level. Both elbows stay straight in 3D. Absolutely no long horizontal arm pointing toward the profile nose; no three-quarter chest, no two visible eyes, no diagonal body.""",
    "right": """CAMERA AT THE CHARACTER'S EXACT RIGHT SIDE: pure 270-degree orthographic profile; nose and toes point toward image RIGHT. Only the opposite face profile and the narrow side of chest is visible. Crucial 3D projection: BOTH ARMS ARE STILL EXTENDED SIDEWAYS ALONG THE CHARACTER'S X AXIS INTO/OUT OF THE CAMERA, so the image-side projection is strongly FORESHORTENED and both arms mostly OVERLAP the shoulders in the image, NOT projected as arms reaching toward the nose or screen-right. Hands may overlap shoulder silhouettes. Both elbows remain straight in 3D. Absolutely no arm pointing toward screen right, no two eyes, no frontal chest, no three-quarter pose, no torso yaw."""
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_muse():
    src=ROOT/"scripts/generate-standing-directions.py"
    spec=importlib.util.spec_from_file_location("muse_rig_profile_v2",src)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def check():
    cfg=json.loads(REQUEST.read_text(encoding="utf-8"))
    expected={
        "schema":2, "trial_id":"marches-axeman-orthographic-tpose-profiles-v2",
        "pose_contract":"docs/rig-pose-contract.md",
        "front_sha256":FRONT_SHA,"back_sha256":BACK_SHA,
        "preserve_original_front_back":True,
        "regenerate_only":["left","right"],
        "image_model":"meta/muse-image",
        "maximum_new_paid_images":2,"automatic_paid_retries":0,
        "output_directory":str(OUT.relative_to(ROOT)),
    }
    if cfg!=expected:
        raise ValueError("Unexpected v2 rig-source request")
    if sha(SRC/"front.png")!=FRONT_SHA or sha(SRC/"back.png")!=BACK_SHA:
        raise ValueError("Original accepted front/back have been altered")
    if not (ROOT/"docs/rig-pose-contract.md").is_file():
        raise FileNotFoundError("Frozen rig pose contract")
    return cfg

def stats(image):
    bbox=image.getchannel("A").point(lambda x:255 if x>48 else 0).getbbox()
    if bbox is None:
        raise ValueError("Image has no usable silhouette")
    w,h=bbox[2]-bbox[0],bbox[3]-bbox[1]
    return {"bbox":list(bbox),"width_height_ratio":round(w/h,3),
            "width_px":w, "height_px":h,
            "profile_narrow_enough":w/h<.58,
            "safe_margins":min(bbox[0],bbox[1],1024-bbox[2],1024-bbox[3])>=30}

def sheet(rows):
    unit,gap=430,12
    board=Image.new("RGB",(unit*4+gap*5,unit+90+gap*2),"#e0e9ef")
    d=ImageDraw.Draw(board)
    d.rectangle((0,0,board.width,90),fill="#263949")
    d.text((20,18),"WARCONQUER / V2 CANONICAL WORLD-SPACE T-POSE",fill="white")
    d.text((20,50),"FRONT + BACK FROZEN; LEFT + RIGHT ORTHOGRAPHIC PROFILE TRIAL",fill="#d0e1eb")
    for k,direction in enumerate(ORDER):
        x=gap+k*(unit+gap)
        y=90+gap
        d.rectangle((x,y,x+unit,y+unit),fill="#f9fafb",outline="#c2cbd1")
        path=OUT/(direction+".png")
        if path.exists():
            with Image.open(path) as src:
                im=src.convert("RGBA")
                im.thumbnail((unit-12,unit-34),Image.Resampling.LANCZOS)
                board.paste(im,(x+(unit-im.width)//2,y+28),im)
        d.text((x+12,y+8),direction.upper(),fill="#29465b")
    board.save(OUT/"review-v2.png",optimize=True)

def run():
    cfg=check()
    if os.environ.get("OPENROUTER_IMAGE_MODEL")!=cfg["image_model"] or not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("Muse model/key mismatch")
    OUT.mkdir(parents=True,exist_ok=True)
    RAW.mkdir(parents=True,exist_ok=True)
    for d in ("front","back"):
        target=OUT/(d+".png")
        if not target.exists():
            shutil.copyfile(SRC/(d+".png"),target)
        if sha(target)!= (FRONT_SHA if d=="front" else BACK_SHA):
            raise ValueError("V2 immutable reference drift")
    muse=load_muse()
    results=[]
    for direction in ("left","right"):
        target=OUT/(direction+".png")
        record=OUT/(direction+".json")
        if target.is_file():
            with Image.open(target) as check_image:
                metrics=stats(check_image.convert("RGBA"))
            results.append({"view":direction,"status":"already-generated-unapproved",
                            "sha256":sha(target),"geometry":metrics})
            continue
        if record.is_file():
            results.append({"view":direction,"status":"blocked-existing-paid-request"})
            break
        prompt=POSE+"\n\n"+SIDE[direction]
        if hashlib.sha256(prompt.encode()).hexdigest()!=FROZEN_PROMPT_SHA256[direction]:
            raise ValueError("Canonical pose prompt drift: new trial/version required")
        refs=[
            muse.reference_payload((OUT/"front.png").read_bytes())[0],
            muse.reference_payload((OUT/"back.png").read_bytes())[0],
        ]
        if direction=="right":
            if not (OUT/"left.png").exists():
                raise RuntimeError("Left profile must exist before right")
            refs.insert(0,muse.reference_payload((OUT/"left.png").read_bytes())[0])
        rec={"view":direction,"status":"paid-request-submitted-result-uncertain",
             "model":"meta/muse-image","prompt_revision":"canonical-worldspace-tpose-v2",
             "prompt":prompt,"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
             "input_sha256":{x:sha(OUT/(x+".png")) for x in
                 (("front","back","left") if direction=="right" else ("front","back"))},
             "seed":"not supplied: Muse provider-specific seed support unverified",
             "maximum_new_paid_images":2}
        record.write_text(json.dumps(rec,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        try:
            image,raw,usage=muse.call_muse(prompt,refs,"meta/muse-image")
            (RAW/(direction+".png")).write_bytes(raw)
            cut,matte=muse.extract_alpha(image)
            normalized,placement=muse.place_character(cut)
            normalized.save(target)
            metrics=stats(normalized)
            rec.update(status="generated-needs-visual-review",
                       image_sha256=sha(target),geometry=metrics,
                       alpha_processing=matte,placement=placement,usage=usage)
            results.append({"view":direction,"status":rec["status"],
                            "sha256":rec["image_sha256"],"geometry":metrics})
            print(direction,metrics,flush=True)
        except Exception as exc:
            rec.update(status="failed-no-automatic-retry",error_type=type(exc).__name__,
                       error=str(exc)[:500])
            results.append({"view":direction,"status":rec["status"],"error":rec["error"]})
            raise
        finally:
            record.write_text(json.dumps(rec,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    sheet(results)
    report={"trial_id":cfg["trial_id"],"prompt_contract":cfg["pose_contract"],
            "prompt_revision":"canonical-worldspace-tpose-v2","new_paid_image_limit":2,
            "human_review_required":True,"source_views":list(ORDER),
            "ready_for_mesh":False,"results":results,
            "warning":"A prompt cannot guarantee anatomical 3D consistency; manually inspect side projections and all four silhouettes."}
    (OUT/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if len(results)!=2 or not all(r.get("geometry",{}).get("profile_narrow_enough") and
                                    r.get("geometry",{}).get("safe_margins") for r in results):
        raise SystemExit("Automatic side-profile QA has concerns; do not proceed to Hunyuan")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--dry-run",action="store_true")
    opts=p.parse_args()
    cfg=check()
    if opts.dry_run:
        print(json.dumps({"validated":True,"trial":cfg["trial_id"],"max_paid_images":2,
                          "views":["left","right"]}))
    else:
        run()
