#!/usr/bin/env python3
"""Run real browser visual GO/NO-GO for all ready props, without unit adapters."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
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


def run(selected,output,allow_paid):
    if not allow_paid:raise RuntimeError("Visual model requests require --allow-paid")
    ready=list(candidates(selected))
    if not ready:
        print("No playable humanoid with a ready vision-annotated prop")
        return
    output.mkdir(parents=True,exist_ok=True)
    qa_spec=importlib.util.spec_from_file_location("wc_visual_qa",ROOT/"scripts/verify-prop-visual-qa.py")
    qa=importlib.util.module_from_spec(qa_spec)
    qa_spec.loader.exec_module(qa)
    select_spec=importlib.util.spec_from_file_location("wc_vision_pose_selection",
        ROOT/"scripts/select-prop-contact-orientation.py")
    selector=importlib.util.module_from_spec(select_spec)
    select_spec.loader.exec_module(selector)
    failures=[]
    for unit,prop,relative in ready:
        plan=pipeline.safe_path(relative)
        record=json.loads(plan.read_text())
        existing=record.get("visual_qa",{})
        if (existing.get("signature")==qa.signature(record) and
                existing.get("status")=="approved"):
            print("VISUAL_GO_CACHED",unit,prop)
            continue
        screenshots=output/(unit+"_"+prop)
        print("Rendering actual browser contact:",unit,prop,flush=True)
        try:
            subprocess.run(["node","scripts/capture-prop-contact.mjs",unit,prop,str(screenshots)],
                cwd=ROOT,check=True,timeout=180)
            if not qa.review(plan,screenshots):
                old_doc=json.loads(plan.read_text())
                previous_search=old_doc.get("automatic_orientation_selection",{})
                if previous_search.get("selected_head_direction"):
                    failures.append(unit+"/"+prop+" (visual NO-GO after both anatomical axis searches)")
                    continue
                # Instead of a weapon-specific angle fix, render the SAME GLB
                # with every valid anatomical working-face direction. Vision
                # sees the candidates together and picks the physically valid
                # one; the regular GO gate then checks it independently.
                original=plan.read_text()
                source=json.loads(original)
                edge_already_selected=(previous_search.get("selected_edge_direction")
                                      or previous_search.get("selected_direction"))
                axis="head_direction" if edge_already_selected else "edge_direction"
                state_file=screenshots/"contact-state.json"
                state=json.loads(state_file.read_text()) if state_file.is_file() else {}
                if axis=="head_direction" and state.get("carry")=="mass-below-hand":
                    # Head direction is intentionally overridden by physical
                    # gravity in this carry state: trying six identical
                    # rotations would waste renders/model calls.
                    failures.append(unit+"/"+prop+" (gravity-balanced carry still rejected visually)")
                    continue
                previous=source["specifications"][axis]
                alternatives=output/(unit+"_"+prop+"_"+axis+"_alternatives")
                try:
                    for direction in selector.choices_for(axis):
                        target=alternatives/direction
                        if direction==previous:
                            shutil.copytree(screenshots,target,dirs_exist_ok=True)
                            continue
                        candidate=json.loads(original)
                        candidate["specifications"][axis]=direction
                        plan.write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+"\n")
                        subprocess.run(["node","scripts/capture-prop-contact.mjs",unit,prop,str(target)],
                            cwd=ROOT,check=True,timeout=180)
                finally:
                    plan.write_text(original)
                direction=selector.choose(plan,alternatives,previous,axis)
                updated=json.loads(original)
                updated["specifications"][axis]=direction
                updated.pop("vision_review",None)
                updated["visual_qa"]={"status":"candidate",
                    "reason":"Real-browser alternatives ranked by low-cost vision"}
                updated["automatic_orientation_selection"]={**previous_search,
                    "method":"real-3d-vision-candidate-search",
                    "previous_"+axis:previous,"selected_"+axis:direction,
                    "candidates_"+axis:list(selector.choices_for(axis))}
                plan.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+"\n")
                if not qa.review(plan,alternatives/direction):
                    failures.append(unit+"/"+prop+" (no GO after visual candidate selection)")
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired,ValueError) as error:
            failures.append(unit+"/"+prop+": "+str(error))
    if failures:raise RuntimeError("Visual NO-GO or blocked: "+", ".join(failures))
    print("PASS: all ready object contacts received a live vision GO")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit",help="Optional unit ID; omit for all ready units")
    parser.add_argument("--output",required=True)
    parser.add_argument("--allow-paid",action="store_true")
    args=parser.parse_args()
    run(args.unit,Path(args.output).resolve(),args.allow_paid)
