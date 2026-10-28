#!/usr/bin/env python3
"""Zero-network regressions for source-grounded, phase-specific grip contracts."""
import copy
import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
module_spec = importlib.util.spec_from_file_location(
    "wc_prop_interaction", root / "scripts/characterize-prop-interaction.py")
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
clips = [c for c in json.loads((root / "data/motion-library.json").read_text())["clips"]
         if c["included"]]

# Object roles are semantic, never inferred from geometry. Carrying and using
# a shaft tool may legitimately involve different hand counts.
valid = {
    "object_kind": "axe",
    "object_function": "A sharp metal blade chops into a target by swinging its wooden handle.",
    "object_evidence": "The source shows a wooden handle with one sharpened metal blade.",
    "features": [{"id": "cutting_edge", "function": "Sharp metal edge that impacts the target",
        "origin": [.51, .55], "direction_tip": [.84, .52],
        "direction_semantics": "The sharp edge points toward the chopped target on impact.",
        "evidence": "Original concept distinctly shows the sharp front of the axe head."}],
    "grips": [
        {"id": "lower_handle", "point": [.45, .74],
         "surface": "Lower wooden handle grip", "evidence": "Visible lower handle shaft."},
        {"id": "upper_handle", "point": [.60, .54],
         "surface": "Upper wooden handle grip", "evidence": "Visible upper handle shaft."}],
    "modes": [
        {"id": "passive_carry", "phase": "carry", "hands": 1,
         "primary_hand": "right", "primary_grip": "lower_handle",
         "secondary_hand": "none", "secondary_grip": "",
         "functional_feature": "", "mixamo_role": "none",
         "action_intent": "Transport the axe safely by its lower wooden handle.",
         "evidence": "Character silhouette carries the axe by its lower shaft."},
        {"id": "chop", "phase": "use", "hands": 2,
         "primary_hand": "right", "primary_grip": "lower_handle",
         "secondary_hand": "left", "secondary_grip": "upper_handle",
         "functional_feature": "cutting_edge", "mixamo_role": "axe_chop",
         "action_intent": "Swing the axe and hit the target with its sharp edge.",
         "evidence": "The action needs a supporting grip and an upper stabilizing hand."}
    ],
    "confidence": .93, "uncertainties": [],
    "explanation": "Object, actor and motion roles remain separate until clip-contact QA."
}

# A use-mode role must exist in real motion metadata, but this alone is only
# a candidate; it does NOT demonstrate that the corresponding pose works.
assert module.validate(valid, clips) is valid

def reject(change, phrase):
    broken = copy.deepcopy(valid)
    change(broken)
    try:
        module.validate(broken, clips)
    except ValueError as error:
        assert phrase in str(error), str(error)
    else:
        raise AssertionError("Accepted an invalid vision/rig/Mixamo contract")

reject(lambda p: p["modes"][1].update(secondary_grip="lower_handle"), "distinct grips")
reject(lambda p: p["modes"][0].update(secondary_hand="right"), "one-hand")
reject(lambda p: p["modes"][1].update(mixamo_role="imaginary_attack"), "Mixamo")
reject(lambda p: p["features"][0].update(direction_tip=[.51,.55]), "direction")
reject(lambda p: p.update(uncertainties=["Cannot see the functional front"]), "Uncertain")
reject(lambda p: p["modes"][1].update(primary_grip="made_up_handle"), "Invalid hands")
reject(lambda p: p["modes"][1].update(primary_hand="either"), "Invalid hands")
reject(lambda p: p["modes"].pop(), "Carry and use")
reject(lambda p: p.update(object_kind="bow"), "Mixamo")
reject(lambda p: p.update(object_kind="sword"), "Mixamo")
reject(lambda p: p.update(object_kind="hammer"), "Mixamo")

print("PASS: generic per-phase semantic roles, two hands and Mixamo candidate evidence")
