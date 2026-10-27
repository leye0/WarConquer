#!/usr/bin/env python3
"""Free four-angle rendered mesh contact sheets for a completed 3D rig pilot."""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"assets/experiments/rig-ready-3d/marches_hache/tpose-v2"

def main():
    import numpy
    import trimesh
    legacy_path=ROOT/"scripts/build-multiview-3d.py"
    spec=importlib.util.spec_from_file_location("wc_multiview_mesh_visualizer",legacy_path)
    legacy=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    report={}
    for stage,filename,preview in (
        ("mesh","unrigged.glb","unrigged-four-angles.png"),
        ("rig","rigged.glb","rigged-four-angles.png")):
        path=OUT/filename
        if not path.is_file():
            report[stage]={"status":"not-collected"}
            continue
        try:
            mesh,geometry=legacy.inspect_mesh(path)
            legacy.render_contact_sheet(mesh,OUT/preview)
            report[stage]={"status":"rendered-awaiting-human-visual-qa",
                           "preview":preview,"geometry":geometry}
            print(stage,"four-angle preview saved:",preview,flush=True)
        except Exception as exc:
            report[stage]={"status":"preview-failed","error":str(exc)[:600]}
            print("::warning title=GLB preview failed::"+stage+" "+str(exc)[:300],flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"visual-qa-report.json").write_text(json.dumps(
        {"review_status":"NOT_HUMAN_APPROVED",
         "note":"Silhouette renders cannot certify skinning, textures, joint angles or sword/axe deformation.",
         "models":report},indent=2)+"\n",encoding="utf-8")
    if not any(x.get("status")=="rendered-awaiting-human-visual-qa" for x in report.values()):
        raise RuntimeError("No GLB geometry rendered")

if __name__=="__main__":
    main()
