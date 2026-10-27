#!/usr/bin/env python3
"""One checkpointed text-to-skeletal-motion trial for WarConquer.

Generates ONE default-rig GLB motion clip. This is NOT yet retargeted to
the WarConquer rig; animation transfer has a separate geometry QA gate.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/"rig-ready-motion-request.json"
RIG=ROOT/"assets/experiments/rig-ready-3d/marches_hache/tpose-v2/rigged.glb"
OUTPUT=ROOT/"assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/axe-chop-v1"
RIG_SHA="9bb357587de46032de203abe735b3eab140d32c982066b15da55c7c339439273"
MODEL="uthana/text-to-motion-diffusion-v2"
PROMPT=("A medieval warrior holding an imaginary heavy two-handed axe in front of the body. "
        "From a stable shoulder-width stance, raise both hands together above the right shoulder, "
        "shift weight toward the left leg and perform ONE powerful controlled diagonal downward "
        "chopping swing from the right shoulder to the left hip, then recover to a balanced ready stance. "
        "One clean readable axe attack, no spinning, no repeated strikes, feet grounded, complete "
        "full-body natural human biomechanics.")
INPUTS={
    "prompt":PROMPT,
    "character":"Tar",
    "output_ext":"GLB",
    "fps":24,
    "no_mesh":False,
    "foot_ik":True,
    "internal_ik":True,
    "motion_length":4,
    "seed":20261027,
    "cfg_scale":2.5,
}
TERMINAL={"succeeded","failed","canceled"}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_suffix(".tmp")
    t.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    t.replace(path)

def legacy():
    p=ROOT/"scripts/build-rig-ready-3d.py"
    spec=importlib.util.spec_from_file_location("rig3d_existing_client",p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def request():
    cfg=json.loads(REQUEST.read_text(encoding="utf-8"))
    expected={
        "schema":1,"trial_id":"marches-axeman-one-axe-chop-motion-v1",
        "source_rigged_glb":str(RIG.relative_to(ROOT)),
        "source_rig_sha256":RIG_SHA,"model":MODEL,
        "model_input":INPUTS,"maximum_paid_predictions":1,
        "automatic_paid_retries":0,
        "output_directory":str(OUTPUT.relative_to(ROOT)),
        "retargeting":"separate_validation_required",
    }
    if cfg!=expected:
        raise ValueError("Motion request differs from pinned one-shot contract")
    if not RIG.is_file() or sha(RIG)!=RIG_SHA:
        raise ValueError("Expected already-validated rig GLB changed or missing")
    return cfg

def submit(cfg):
    checkpoint=OUTPUT/"prediction.json"
    if checkpoint.exists() or (OUTPUT/"source-motion.glb").exists():
        print("Existing accepted trial - no new paid prediction",flush=True)
        return
    api=legacy().client()
    model=api.models.get(MODEL)
    version=model.latest_version.id
    if not version:
        raise RuntimeError("No model version for Uthana diffusion motion")
    # Validate known keys against the provider schema when exposed.
    schema=getattr(model.latest_version,"openapi_schema",None)
    properties=(((schema or {}).get("components") or {}).get("schemas") or {}).get("Input",{}).get("properties",{})
    unknown=set(INPUTS)-set(properties) if properties else set()
    if unknown:
        raise ValueError("Unrecognized motion input keys: "+",".join(sorted(unknown)))
    prediction=api.predictions.create(version=version,input=INPUTS)
    if not prediction.id:
        raise RuntimeError("Prediction accepted without ID; do not retry automatically")
    save(checkpoint,{
        "trial_id":cfg["trial_id"],"model":MODEL,"model_version":version,
        "prediction_id":prediction.id,"initial_status":prediction.status,
        "rig_sha256":RIG_SHA,"prompt_sha256":hashlib.sha256(PROMPT.encode()).hexdigest(),
        "model_input":INPUTS,"paid_predictions_submitted":1
    })
    print("One paid motion prediction accepted:",prediction.id,flush=True)

def collect(cfg):
    checkpoint=OUTPUT/"prediction.json"
    if not checkpoint.exists():
        raise RuntimeError("No motion prediction checkpoint")
    rec=json.loads(checkpoint.read_text(encoding="utf-8"))
    if rec.get("trial_id")!=cfg["trial_id"] or rec.get("rig_sha256")!=RIG_SHA:
        raise ValueError("Unexpected motion checkpoint/rig fingerprint")
    dest=OUTPUT/"source-motion.glb"
    if dest.is_file():
        print("Motion output already collected, no extra generation",flush=True)
        return
    api=legacy().client()
    deadline=time.monotonic()+20*60
    prediction=None
    while time.monotonic()<deadline:
        prediction=api.predictions.get(rec["prediction_id"])
        print("motion:",prediction.status,flush=True)
        if prediction.status in TERMINAL:
            break
        time.sleep(15)
    if prediction is None or prediction.status not in TERMINAL:
        raise TimeoutError("Motion prediction pending - rerun collection, not submit")
    if prediction.status!="succeeded":
        save(OUTPUT/"error.json",{"status":prediction.status,
                                  "error":str(prediction.error)[:1000]})
        raise RuntimeError("Motion prediction failed without automatic paid retry")
    l=legacy()
    uri=l.uri_for_glb(prediction.output)
    if not uri:
        raise RuntimeError("No GLB URL returned; inspect prediction rather than retry")
    size=l.download_glb(uri,dest)
    metrics=l.inspect_glb(dest)
    passed=metrics["animations_in_file"]>0 and metrics["node_count"]>=10
    save(OUTPUT/"report.json",{
        "status":"motion-data-collected-awaiting-retarget" if passed else "motion-data-invalid",
        "rig_target_sha256":RIG_SHA,
        "source_motion_sha256":sha(dest),"source_motion_bytes":size,
        "motion_model":MODEL,"model_version":rec["model_version"],
        "prompt_sha256":rec["prompt_sha256"],"seed":INPUTS["seed"],
        "glb":metrics,"paid_predictions_submitted":1,
        "retargeted_to_warconquer":False,
        "human_visual_review_required":True,
        "note":"This is animation data on an Uthana default rig; it is not a WarConquer animation until skeleton retargeting and validation."
    })
    if not passed:
        raise RuntimeError("Output GLB has no detectable skeletal animation")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stage",required=True,choices=("validate","submit","collect"))
    args=p.parse_args()
    cfg=request()
    if args.stage=="validate":
        print(json.dumps({"ready":True,"model":MODEL,"prompt_sha256":
                          hashlib.sha256(PROMPT.encode()).hexdigest(),"seed":INPUTS["seed"]}))
    elif args.stage=="submit":
        submit(cfg)
    else:
        collect(cfg)

if __name__=="__main__":
    main()
