#!/usr/bin/env python3
"""Manifest-driven unit build: the same pipeline locally and in GitHub Actions.

A unit needs only an ID, a name and an original image. The vision stage
describes removable equipment; the remaining paths and requests are derived
from the unit identity. All paid operations are gated, cached and resumable.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNITS = ROOT / "data" / "units"
STAGES = (
    "source", "equipment_identify", "turnaround", "body", "rig", "animations",
    "object_source", "object_mesh", "object_size", "object_grip", "object_landmarks", "integrate"
)
PAID = frozenset({
    "equipment_identify", "turnaround", "body", "rig", "object_source",
    "object_mesh", "object_size", "object_grip", "object_landmarks"
})
DEPENDENCIES = {
    "turnaround": ("Pillow==11.3.0", "numpy==2.2.6", "scipy==1.16.2"),
    "body": ("fal-client==0.14.0",),
    "rig": ("replicate==1.0.7", "Pillow==11.3.0"),
    "animations": ("Pillow==11.3.0",),
    "object_source": ("Pillow==11.3.0", "rembg[cpu]==2.0.67"),
    "object_mesh": ("replicate>=1,<2", "Pillow==11.3.0"),
    "object_landmarks": ("Pillow==11.3.0", "numpy==2.2.6"),
}
STAGE_DESCRIPTION = {
    "source": "Fiche 2D originale (entrée fournie)",
    "equipment_identify": "Identification et description des équipements sur la fiche",
    "turnaround": "4 vues cohérentes du personnage",
    "body": "Personnage fal.ai texturé",
    "rig": "Squelette Uthana",
    "animations": "Mouvements Mixamo transférés",
    "object_source": "Illustration isolée de chaque objet",
    "object_mesh": "GLB indépendant TRELLIS",
    "object_size": "Estimation de longueur physique en cm",
    "object_grip": "Prise / orientation sémantique de l'objet",
    "object_landmarks": "Repères fonctionnels 3D du vrai GLB par vision, réutilisables par tout humanoïde",
    "integrate": "Assemblage et catalogue 3D de l'arène",
}

class PipelineError(Exception):
    pass

def equipment_tools():
    spec = importlib.util.spec_from_file_location("wc_unit_equipment", ROOT / "scripts/unit-equipment.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def safe_path(rel):
    if not isinstance(rel, str) or not rel or "\\" in rel or rel.startswith("/"):
        raise PipelineError("Invalid repository-relative path: " + repr(rel))
    path = (ROOT / rel).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise PipelineError("Path outside repository: " + repr(rel))
    return path

def unit_ids():
    return sorted(p.stem for p in UNITS.glob("*.json") if re.fullmatch(r"[a-z][a-z0-9_]*", p.stem))

def manifest(unit):
    if not re.fullmatch(r"[a-z][a-z0-9_]*", unit):
        raise PipelineError("Unit ID must be lowercase letters, digits or underscore")
    file = UNITS / (unit + ".json")
    if not file.is_file():
        raise PipelineError("Unknown unit " + unit + " (available: " + ", ".join(unit_ids()) + ")")
    doc = json.loads(file.read_text(encoding="utf-8"))
    if doc.get("schema") != 1 or doc.get("id") != unit:
        raise PipelineError("Invalid or mismatched unit schema: " + str(file))
    if not (doc.get("title") or doc.get("name")) or not isinstance(doc.get("source"), dict):
        raise PipelineError("An ID, name and source image are required")
    doc["title"] = doc.get("title") or doc["name"]
    src = doc["source"]
    if not src.get("character_image"):
        raise PipelineError("Missing original concept image")
    doc.setdefault("adapter", "manifest_v1")
    pose = "tpose-v1"
    source_base = f"assets/experiments/rig-source-turnaround/{unit}/{pose}"
    src.setdefault("turnaround_request", f"data/units/{unit}/turnaround-request.json")
    src.setdefault("views", {v: f"{source_base}/{v}.png" for v in ("front", "back", "left", "right")})
    if set(src["views"]) != {"front", "back", "left", "right"}:
        raise PipelineError("Four orthographic views are required")
    mesh_base = f"assets/experiments/rig-ready-3d/{unit}/{pose}"
    motion_base = mesh_base + "/motion/fal-mixamo-v1"
    body = doc.setdefault("body", {})
    for key, default in {"glb": mesh_base + "/fal-textured.glb",
       "rigged_glb": motion_base + "/fal-rigged.glb",
       "playable_glb": motion_base + "/warconquer-textured-playable.glb",
       "animations": "data/motion-library.json"}.items():
        body.setdefault(key, default)
    declared = doc.get("equipment", [])
    if not isinstance(declared, list):
        raise PipelineError("Equipment must be an array when provided")
    discovered = equipment_tools().descriptors(unit)
    if not declared and discovered:
        declared = discovered
    by_id = {p["id"]: p for p in discovered}
    normalized = []
    for initial in declared:
        if not isinstance(initial, dict) or not re.fullmatch(r"[a-z][a-z0-9_]*", initial.get("id", "")):
            raise PipelineError("Invalid equipment ID")
        prop = dict(initial)
        if prop["id"] in by_id:
            prop.setdefault("kind", by_id[prop["id"]]["kind"])
            prop.setdefault("description", by_id[prop["id"]]["description"])
        if not prop.get("kind"):
            raise PipelineError("Equipment kind missing")
        faction = src["character_image"].split("/")[2] if src["character_image"].startswith("assets/concepts/") else unit
        prop.setdefault("source_image", f"assets/concepts/{faction}/objects/{unit}_{prop['id']}.png")
        prop.setdefault("source_request", f"data/units/{unit}/{prop['id']}-image-request.json")
        prop.setdefault("glb", f"assets/experiments/props/{unit}/{prop['id']}/mesh.glb")
        prop.setdefault("trellis_request", f"data/units/{unit}/{prop['id']}-trellis-request.json")
        pbase = str(Path(prop["glb"]).parent)
        for key, default in {"physical_size_request":pbase+"/physical-size-request.json",
           "physical_size":pbase+"/physical-size.json",
           "grip_request":pbase+"/grip-request.json",
           "grip":pbase+"/grip-plan.json"}.items():
            prop.setdefault(key, default)
        normalized.append(prop)
    doc["equipment"] = normalized
    if len({p["id"] for p in normalized}) != len(normalized):
        raise PipelineError("Duplicate equipment IDs")
    values = [
        doc["source"].get("character_image"), doc["source"].get("turnaround_request"),
        *doc["source"].get("views", {}).values(),
        *(doc["body"].get(k) for k in ("glb", "rigged_glb", "playable_glb", "animations"))
    ]
    fields = (
        "source_image", "source_request", "glb", "trellis_request",
        "physical_size_request", "physical_size", "grip_request", "grip"
    )
    for prop in doc["equipment"]:
        if not isinstance(prop, dict) or not prop.get("id"):
            raise PipelineError("Invalid equipment entry")
        values.extend(prop.get(k) for k in fields)
    if any(v is None for v in values):
        raise PipelineError("Manifest missing one or more required paths")
    for v in values:
        safe_path(v)
    # Unit-scoped generated assets must never alias another character.
    for key in ("glb", "rigged_glb", "playable_glb"):
        if not safe_path(body[key]).is_relative_to(ROOT / "assets/experiments/rig-ready-3d" / unit):
            raise PipelineError("Cross-unit body path: " + body[key])
    for prop in normalized:
        if not safe_path(prop["glb"]).is_relative_to(ROOT / "assets/experiments/props" / unit):
            raise PipelineError("Cross-unit equipment GLB: " + prop["glb"])
    return doc

def assets_for(doc, stage):
    s, b, props = doc["source"], doc["body"], doc["equipment"]
    mapping = {
        "source": [s["character_image"]],
        "equipment_identify": [f"data/units/{doc['id']}/equipment-analysis.json"],
        "turnaround": list(s["views"].values()),
        "body": [b["glb"]],
        "rig": [b["rigged_glb"]],
        "animations": [b["playable_glb"]],
        "object_source": [p["source_image"] for p in props],
        "object_mesh": [p["glb"] for p in props],
        "object_size": [p["physical_size"] for p in props],
        "object_grip": [p["grip"] for p in props],
        "object_landmarks": [p["grip"] for p in props],
        "integrate": [
            b["playable_glb"],
            *(p["glb"] for p in props),
            *(p["physical_size"] for p in props),
            *(p["grip"] for p in props)
        ],
    }
    if stage == "equipment_identify" and not safe_path(mapping[stage][0]).exists():
        # A previously generated equipment image and its original brief supply
        # equivalent identity and description without another vision call.
        if props and all(safe_path(p["source_request"]).is_file() for p in props):
            return [p["source_request"] for p in props]
    if not props and stage.startswith("object_"):
        return [f"data/units/{doc['id']}/equipment-analysis.json"]
    return mapping[stage]

def inspect(rel):
    path = safe_path(rel)
    if not path.is_file() or path.stat().st_size == 0:
        return "missing"
    if path.suffix.lower() == ".glb":
        with path.open("rb") as handle:
            if handle.read(4) != b"glTF":
                return "invalid_glb"
    if path.suffix.lower() == ".png":
        with path.open("rb") as handle:
            if handle.read(8) != b"\x89PNG\r\n\x1a\n":
                return "invalid_png"
    if path.suffix.lower() == ".json":
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError):
            return "invalid_json"
        if path.name == "physical-size.json" and (
            result.get("schema") != 1 or result.get("units") != "cm"
            or not isinstance(result.get("estimated_length_cm"), (int, float))
            or isinstance(result.get("estimated_length_cm"), bool)
            or not 2 <= result["estimated_length_cm"] <= 1000
        ):
            return "invalid_physical_size"
        if path.name == "grip-plan.json" and result.get("schema") not in (2, 3):
            return "invalid_grip_plan"
    return "ready"

def state(doc, stage):
    paths = {p: inspect(p) for p in assets_for(doc, stage)}
    if stage == "object_landmarks":
        for prop in doc["equipment"]:
            grip = prop["grip"]
            if paths.get(grip) != "ready":continue
            try:
                plan = json.loads(safe_path(grip).read_text())
                landmarks = plan.get("mesh_landmarks", {})
                digest = hashlib.sha256(safe_path(prop["glb"]).read_bytes()).hexdigest()
                if (landmarks.get("schema") != 1 or
                        landmarks.get("glb_sha256") != digest or
                        not all(name in landmarks.get("points", {}) for name in
                                ("handle_butt", "grip_center", "working_head", "functional_edge"))):
                    paths[grip] = "missing_mesh_landmarks"
            except (ValueError, OSError, KeyError):
                paths[grip] = "invalid_mesh_landmarks"
    return {"stage": stage, "description": STAGE_DESCRIPTION[stage],
            "ready": all(x == "ready" for x in paths.values()),
            "paid_if_missing": stage in PAID,
            "files": paths}

def run_cmd(*args, env=None):
    print("+", " ".join(args), flush=True)
    subprocess.run(list(args), cwd=ROOT, env=env, check=True)

def py(name, *args, env=None):
    run_cmd(sys.executable, "scripts/" + name, *args, env=env)

def execute(doc, stage):
    if stage == "source":
        if not state(doc, "source")["ready"]:
            raise PipelineError("Create the original unit illustration before the 3D pipeline")
    elif stage == "equipment_identify":
        equipment_tools().describe(doc["id"], paid=True)
    elif stage == "turnaround":
        py("build-unit-3d.py", "--unit", doc["id"], "--stage", "turnaround", "--allow-paid")
    elif stage == "body":
        env = os.environ.copy()
        if not env.get("FAL_KEY") and env.get("FAL_API_KEY"):
            env["FAL_KEY"] = env["FAL_API_KEY"]
        py("build-unit-3d.py", "--unit", doc["id"], "--stage", "body", "--allow-paid", env=env)
    elif stage == "rig":
        for part in ("validate", "rig-submit", "rig-collect"):
            py("build-fal-rig-playable.py", "--unit", doc["id"], "--stage", part)
    elif stage == "animations":
        if not state(doc, "rig")["ready"]:
            raise PipelineError("Rig must be present before animation retargeting")
        with tempfile.TemporaryDirectory(prefix="wc-mixamo-") as tmp:
            env = os.environ.copy()
            env["WARCONQUER_STANDARD_IDLE"] = "1"
            env["WARCONQUER_IDLE_VARIANTS"] = "1"
            py("convert-mixamo-fbx.py", "download", tmp, env=env)
            py("convert-mixamo-fbx.py", "convert", tmp, env=env)
            env["MIXAMO_CONVERTED_DIR"] = tmp
            py("build-fal-rig-playable.py", "--unit", doc["id"], "--stage", "animate", env=env)
    elif stage == "object_source":
        for prop in doc["equipment"]:
            if state({**doc,"equipment":[prop]},stage)["ready"]:continue
            equipment_tools().prepare_requests(doc, prop)
            env = os.environ.copy()
            env["OPENROUTER_IMAGE_MODEL"] = "meta/muse-image"
            py("generate-image.py", "--request", prop["source_request"], env=env)
    elif stage == "object_mesh":
        for prop in doc["equipment"]:
            if state({**doc,"equipment":[prop]},stage)["ready"]:continue
            equipment_tools().prepare_requests(doc, prop)
            for part in ("validate", "submit", "collect"):
                py("build-prop-trellis.py", "--request", prop["trellis_request"], "--stage", part)
    elif stage == "object_size":
        for prop in doc["equipment"]:
            if state({**doc,"equipment":[prop]},stage)["ready"]:continue
            equipment_tools().prepare_requests(doc, prop)
            py("estimate-prop-physical-size.py", "--request", prop["physical_size_request"])
    elif stage == "object_grip":
        for prop in doc["equipment"]:
            if state({**doc,"equipment":[prop]},stage)["ready"]:continue
            equipment_tools().prepare_requests(doc, prop)
            py("plan-prop-attachment.py", "--request", prop["grip_request"])
    elif stage == "object_landmarks":
        for prop in doc["equipment"]:
            if state({**doc,"equipment":[prop]},stage)["ready"]:continue
            if not state({**doc,"equipment":[prop]},"object_grip")["ready"]:
                raise PipelineError("Generate the semantic grip plan before annotating its GLB")
            py("prop-mesh-landmarks.py", "--plan", prop["grip"])
    elif stage == "integrate":
        with tempfile.TemporaryDirectory(prefix="wc-character-pages-") as sandbox:
            target = str(Path(sandbox) / "pages")
            # The Pages builder deliberately rejects an *existing* target.
            run_cmd("node", "scripts/build-character-lab-pages.mjs", target)
            catalog_path = Path(target) / "api/character-lab.json"
            catalog = json.loads(catalog_path.read_text())
            character = next((c for c in catalog["characters"] if c.get("id") == doc["id"]), None)
            if not character:
                raise PipelineError("Character Lab catalog has not registered this unit")
            if not character.get("models"):
                raise PipelineError("Catalog missing this character's models")
            linked = character["props"]
            if len(linked) != len(doc["equipment"]) or not all(p.get("physicalSize") for p in linked):
                raise PipelineError("Catalog did not include source-derived physical centimetres")
            summary = {"schema": 1, "unit": doc["id"], "name": doc["title"],
                       "source_image": doc["source"]["character_image"],
                       "views": doc["source"]["views"], "body": doc["body"],
                       "equipment": doc["equipment"],
                       "stages": {s: state(doc, s) for s in STAGES if s != "integrate"},
                       "catalog": {"buildStatus": character["buildStatus"],
                                   "modelCount": len(character["models"]),
                                   "equipmentCount": len(linked)}}
            artifacts = {path for s in STAGES if s != "integrate"
                         for path in assets_for(doc, s) if inspect(path) == "ready"}
            summary["artifacts_sha256"] = {
                path: hashlib.sha256(safe_path(path).read_bytes()).hexdigest()
                for path in sorted(artifacts)}
            output = safe_path(f"assets/experiments/units/{doc['id']}/manifest.json")
            equipment_tools().save(output, summary)
            print("PASS: generated local 3D arena bundle for", doc["id"])
    else:
        raise PipelineError("Unknown stage " + stage)

def bootstrap(doc, stages, dry_run):
    missing = [s for s in stages if not state(doc, s)["ready"]]
    wanted = sorted({pkg for stage in missing for pkg in DEPENDENCIES.get(stage, ())})
    if not wanted:
        print("No extra Python dependencies needed")
    else:
        print("Python dependencies:", ", ".join(wanted))
        if not dry_run:
            run_cmd(sys.executable, "-m", "pip", "install", *wanted)
    if "animations" in missing:
        print("Animations require the fbx2gltf Node package")
        if not dry_run:
            run_cmd("npm", "install", "--no-save", "--no-audit", "--no-fund",
                    "fbx2gltf@0.9.7-p1")
            binary = ROOT / "node_modules/fbx2gltf/bin/Linux/FBX2glTF"
            if sys.platform.startswith("linux") and binary.is_file():
                binary.chmod(binary.stat().st_mode | 0o111)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "status", "run", "bootstrap"))
    parser.add_argument("--unit", default="marches_hache",
                        help="Selected unit ID in data/units/")
    parser.add_argument("--stage", choices=(*STAGES, "all"), default="all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-paid", action="store_true",
                        help="Explicit permission to submit missing paid stages; never implicit")
    parser.add_argument("--json", action="store_true", help="Machine-readable status")
    opts = parser.parse_args(argv)
    if opts.command == "list":
        print(json.dumps(unit_ids(), ensure_ascii=False) if opts.json else "\n".join(unit_ids()))
        return 0
    doc = manifest(opts.unit)
    stages = list(STAGES) if opts.stage == "all" else [opts.stage]
    if opts.command == "status":
        records = [state(doc, stage) for stage in stages]
        if opts.json:
            print(json.dumps({"unit": doc["id"], "adapter": doc.get("adapter"),
                              "stages": records}, ensure_ascii=False, indent=2))
        else:
            for entry in records:
                print(("OK" if entry["ready"] else "MISSING") + "  " + entry["stage"] +
                      " — " + entry["description"])
                if not entry["ready"]:
                    for p, status in entry["files"].items():
                        if status != "ready":
                            print("   ", status, p)
        return 0
    if opts.command == "bootstrap":
        bootstrap(doc, stages, opts.dry_run)
        return 0
    if opts.command == "run":
        for stage in stages:
            doc = manifest(opts.unit)  # equipment may have been discovered in the previous stage
            current = state(doc, stage)
            if stage != "integrate" and current["ready"]:
                print("SKIP", stage, "(existing, validated outputs)", flush=True)
                continue
            if stage.startswith("object_") and not state(doc,"equipment_identify")["ready"]:
                if opts.dry_run:
                    print("WAIT FOR equipment_identify:",stage)
                    continue
                raise PipelineError("Identify equipment from the source image first; run --stage equipment_identify --allow-paid")
            if stage in PAID and not opts.allow_paid:
                if opts.dry_run:
                    print("WOULD REQUIRE --allow-paid:", stage)
                    continue
                raise PipelineError(
                    "Missing " + stage + "; explicit --allow-paid needed to run a "
                    "potentially billable step. No external model was contacted."
                )
            if opts.dry_run:
                print("WOULD RUN", stage, "(paid)" if stage in PAID else "(local)")
                continue
            print("BUILD", doc["id"], stage, flush=True)
            try:
                execute(doc, stage)
            except subprocess.CalledProcessError as exc:
                raise PipelineError(
                    "Stage " + stage + " failed (exit code " + str(exc.returncode) + "); "
                    "existing receipts and outputs are retained for resumption."
                ) from exc
            result = state(doc, stage)
            if not result["ready"]:
                raise PipelineError("Stage returned without its required assets: " +
                                    ", ".join(p for p, v in result["files"].items() if v != "ready"))
        return 0
    raise PipelineError("Unsupported command")

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PipelineError, ValueError, OSError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise SystemExit(1)
