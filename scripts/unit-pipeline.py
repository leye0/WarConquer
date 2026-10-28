#!/usr/bin/env python3
"""WarConquer unit build entry point — works without GitHub Actions.

Select a unit by data/units/<unit>.json, audit its inputs and outputs, and
run the existing repository tools in a reproducible order. GitHub Actions is
a thin optional wrapper; it never defines pipeline decisions.

The original Marches toolchain still contains hard-coded paths. A generic
manifest-driven turnaround and textured-body builder is now available for
additional units; rigging and weapon-specific stages remain staged adapters.
No step may silently substitute another unit's assets.
"""
from __future__ import annotations

import argparse
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
    "source", "turnaround", "body", "rig", "animations",
    "object_source", "object_mesh", "object_size", "object_grip", "integrate"
)
PAID = frozenset({
    "turnaround", "body", "rig", "object_source",
    "object_mesh", "object_size", "object_grip"
})
DEPENDENCIES = {
    "turnaround": ("Pillow==11.3.0", "numpy==2.2.6", "scipy==1.16.2"),
    "body": ("fal-client==0.14.0",),
    "rig": ("replicate==1.0.7", "Pillow==11.3.0"),
    "animations": ("Pillow==11.3.0",),
    "object_source": ("Pillow==11.3.0", "rembg[cpu]==2.0.67"),
    "object_mesh": ("replicate>=1,<2", "Pillow==11.3.0"),
}
STAGE_DESCRIPTION = {
    "source": "Fiche 2D originale (entrée fournie)",
    "turnaround": "4 vues cohérentes du personnage",
    "body": "Personnage fal.ai texturé",
    "rig": "Squelette Uthana",
    "animations": "Mouvements Mixamo transférés",
    "object_source": "Illustration isolée de chaque objet",
    "object_mesh": "GLB indépendant TRELLIS",
    "object_size": "Estimation de longueur physique en cm",
    "object_grip": "Prise / orientation sémantique de l'objet",
    "integrate": "Assemblage et catalogue 3D de l'arène",
}

class PipelineError(Exception):
    pass

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
    if not isinstance(doc.get("source"), dict) or not isinstance(doc.get("body"), dict):
        raise PipelineError("Missing source/body descriptor")
    if not isinstance(doc.get("equipment"), list) or not doc["equipment"]:
        raise PipelineError("A unit must declare at least one equipment record for this adapter")
    if len({p.get("id") for p in doc["equipment"]}) != len(doc["equipment"]):
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
    return doc

def assets_for(doc, stage):
    s, b, props = doc["source"], doc["body"], doc["equipment"]
    mapping = {
        "source": [s["character_image"]],
        "turnaround": list(s["views"].values()),
        "body": [b["glb"]],
        "rig": [b["rigged_glb"]],
        "animations": [b["playable_glb"]],
        "object_source": [p["source_image"] for p in props],
        "object_mesh": [p["glb"] for p in props],
        "object_size": [p["physical_size"] for p in props],
        "object_grip": [p["grip"] for p in props],
        "integrate": [
            b["playable_glb"],
            *(p["glb"] for p in props),
            *(p["physical_size"] for p in props),
            *(p["grip"] for p in props)
        ],
    }
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
    return {"stage": stage, "description": STAGE_DESCRIPTION[stage],
            "ready": all(x == "ready" for x in paths.values()),
            "paid_if_missing": stage in PAID,
            "files": paths}

def run_cmd(*args, env=None):
    print("+", " ".join(args), flush=True)
    subprocess.run(list(args), cwd=ROOT, env=env, check=True)

def py(name, *args, env=None):
    run_cmd(sys.executable, "scripts/" + name, *args, env=env)

def ensure_adapter(doc):
    if doc.get("id") != "marches_hache" or doc.get("adapter") != "legacy_marches_hache":
        raise PipelineError(
            "This unit can be selected and inspected, but paid/3D generators "
            "still use Marches-specific file paths. Implement a parameterized "
            "generator adapter before running this unit; never silently "
            "build Marches assets for another unit."
        )
    if len(doc["equipment"]) != 1 or doc["equipment"][0]["id"] != "axe":
        raise PipelineError("The current generator adapter only supports the Marches axe")

def execute(doc, stage):
    # Generic Muse and fal.ai body construction are selected by the unit
    # manifest, not by a GitHub Actions workflow.
    if doc.get("adapter") == "manifest_v1" and stage in ("turnaround","body"):
        py("build-unit-3d.py","--unit",doc["id"],"--stage",stage,"--allow-paid")
        return
    if stage != "source":
        ensure_adapter(doc)
    prop = doc["equipment"][0]
    if stage == "source":
        if not state(doc, "source")["ready"]:
            raise PipelineError("Create the original unit illustration before the 3D pipeline")
    elif stage == "turnaround":
        py("generate-rig-profiles-v2.py")
    elif stage == "body":
        env = os.environ.copy()
        if not env.get("FAL_KEY") and env.get("FAL_API_KEY"):
            env["FAL_KEY"] = env["FAL_API_KEY"]
        py("generate-fal-textured-pilot.py", env=env)
    elif stage == "rig":
        py("build-fal-rig-playable.py", "--stage", "validate")
        py("build-fal-rig-playable.py", "--stage", "rig-submit")
        py("build-fal-rig-playable.py", "--stage", "rig-collect")
    elif stage == "animations":
        if not state(doc, "rig")["ready"]:
            raise PipelineError("Rig must be present before animation retargeting")
        with tempfile.TemporaryDirectory(prefix="wc-mixamo-") as tmp:
            py("convert-mixamo-fbx.py", "download", tmp)
            py("convert-mixamo-fbx.py", "convert", tmp)
            env = os.environ.copy()
            env["MIXAMO_CONVERTED_DIR"] = tmp
            env["WARCONQUER_STANDARD_IDLE"] = "1"
            env["WARCONQUER_IDLE_VARIANTS"] = "1"
            py("build-fal-rig-playable.py", "--stage", "animate", env=env)
    elif stage == "object_source":
        py("generate-image.py", "--request", prop["source_request"])
    elif stage == "object_mesh":
        py("build-trellis-axe.py", "--stage", "validate")
        py("build-trellis-axe.py", "--stage", "submit")
        py("build-trellis-axe.py", "--stage", "collect")
    elif stage == "object_size":
        py("estimate-prop-physical-size.py", "--request", prop["physical_size_request"])
    elif stage == "object_grip":
        py("plan-prop-attachment.py", "--request", prop["grip_request"])
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
            if not character.get("props") or not character.get("models"):
                raise PipelineError("Catalog missing this character's equipment or models")
            linked = character["props"]
            if not all(p.get("physicalSize") for p in linked):
                raise PipelineError("Catalog did not include source-derived physical centimetres")
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
        if not opts.dry_run:
            ensure_adapter(doc)
        bootstrap(doc, stages, opts.dry_run)
        return 0
    if opts.command == "run":
        for stage in stages:
            current = state(doc, stage)
            if stage != "integrate" and current["ready"]:
                print("SKIP", stage, "(existing, validated outputs)", flush=True)
                continue
            if (stage != "source" and doc.get("adapter") != "legacy_marches_hache"
                and not (doc.get("adapter") == "manifest_v1" and stage in ("turnaround","body"))):
                if opts.dry_run:
                    print("ADAPTER REQUIRED", stage, "(unit-specific generator not yet implemented)")
                    continue
                raise PipelineError("Missing parameterized 3D adapter for " + doc["id"] +
                                    " at stage " + stage + "; refusing to build the wrong unit")
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
