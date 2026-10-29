#!/usr/bin/env python3
"""Run real browser visual GO/NO-GO for all ready props, without unit adapters."""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("wc_unit_pipeline",ROOT/"scripts/unit-pipeline.py")
pipeline=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def candidates(selected=None):
    for unit in ([selected] if selected else pipeline.unit_ids()):
        doc=pipeline.manifest(unit)
        if not pipeline.safe_path(doc["body"]["playable_glb"]).is_file():
            continue
        for prop in doc["equipment"]:
            plan=pipeline.safe_path(prop["grip"])
            if not plan.is_file():continue
            data=json.loads(plan.read_text())
            if data.get("mesh_landmarks",{}).get("schema")!=1:continue
            yield unit,prop["id"],prop["grip"]


def run(selected,output,allow_paid,passes=("primary","independent")):
    if not allow_paid:raise RuntimeError("Visual model requests require --allow-paid")
    ready=list(candidates(selected))
    if not ready:
        if selected:raise RuntimeError("Selected unit has no vision-grounded 3D contact ready: "+selected)
        print("No playable humanoid with a ready vision-annotated prop")
        return
    output.mkdir(parents=True,exist_ok=True)
    qa_spec=importlib.util.spec_from_file_location("wc_visual_qa",ROOT/"scripts/verify-prop-visual-qa.py")
    qa=importlib.util.module_from_spec(qa_spec)
    qa_spec.loader.exec_module(qa)
    failures=[]
    for unit,prop,relative in ready:
        plan=pipeline.safe_path(relative)
        screenshots=output/(unit+"_"+prop)
        print("Rendering actual browser contact:",unit,prop,flush=True)
        try:
            capture=subprocess.run(["node","scripts/capture-prop-contact.mjs",
                unit,prop,str(screenshots)],cwd=ROOT,check=False,timeout=180)
            verdict_path=screenshots/"contact-numeric-verdict.json"
            if not verdict_path.exists():
                raise RuntimeError("Actual Mixamo frame capture did not complete")
            numeric=json.loads(verdict_path.read_text())
            expected={"front","side","back","walk","run"}
            contract=qa.interaction(json.loads(plan.read_text()))
            if any(m["phase"]=="use" for m in
                    contract["characterization"]["modes"]):
                expected.update({"action","action_mid","action_mid_1",
                    "action_mid_2","action_mid_3","action_mid_5",
                    "action_mid_6","action_mid_7"})
            available={p.stem for p in screenshots.glob("*.png")}
            if expected-available:
                raise RuntimeError("Real Mixamo screenshot views missing: "+
                    ", ".join(sorted(expected-available)))
            decisions=[]
            for pass_id in passes:
                # Independently challenge Gemini with native Qwen3-VL region boxes.
                # Different vision families avoid a same-model false consensus.
                model=("qwen/qwen3-vl-8b-instruct"
                    if pass_id=="independent" else qa.MODEL)
                passed=qa.review(plan,screenshots,pass_id,model=model)
                decision=json.loads(plan.read_text())["visual_qa"]
                decisions.append({"pass_id":pass_id,"go":passed,**decision})
            numeric_ok=capture.returncode==0 and numeric.get("status")=="approved"
            if not numeric_ok or not all(d["go"] for d in decisions):
                result=json.loads(plan.read_text())
                result["visual_qa"]={"status":"rejected",
                    "reason":"Independent vision or real anatomical numeric constraints rejected",
                    "numeric_issues":numeric.get("issues",[]),"reviews":decisions,
                    "checked_views":[p.name for p in screenshots.glob("*.png")]}
                plan.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
                failures.append(unit+"/"+prop+" (real pose or semantic vision disagreement)")
            else:
                result=json.loads(plan.read_text())
                result["visual_qa"]["reviews"]=decisions
                plan.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired,ValueError,
                RuntimeError) as error:
            failures.append(unit+"/"+prop+": "+str(error))
    if failures:raise RuntimeError("Visual NO-GO or blocked: "+", ".join(failures))
    print("PASS: all ready object contacts received a live vision GO")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit",help="Optional unit ID; omit for all ready units")
    parser.add_argument("--output",required=True)
    parser.add_argument("--allow-paid",action="store_true")
    parser.add_argument("--passes",default="primary,independent",
        help="Comma-separated independent vision pass IDs; never brute-force rotations")
    args=parser.parse_args()
    run(args.unit,Path(args.output).resolve(),args.allow_paid,
        tuple(p.strip() for p in args.passes.split(",") if p.strip()))
