#!/usr/bin/env python3
"""No-network checks of the cheap vision GO/NO-GO decision contract."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location("visual_qa",Path(__file__).with_name("verify-prop-visual-qa.py"))
qa=importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)

frame={"id":"action","hands_contact":True,"action_feature_correct":True,
    "orientation_constraints_met":True,"collision_free":True,
    "confidence":.95,"issues":[],"regions":[]}
valid={"go":True,"confidence":.94,"issues":[],"explanation":"proper two-hand contact",
    "frames":[frame]}
assert qa.check_response(valid,["action"])
assert not qa.check_response({**valid,"go":False},["action"])
assert not qa.check_response({**valid,"confidence":.6},["action"])
assert not qa.check_response({**valid,"issues":["floating"]},["action"])
assert not qa.check_response({**valid,"frames":[{**frame,"hands_contact":False}]},["action"])
boxes=[{"label":label,"ymin":120,"xmin":200,"ymax":260,"xmax":310}
       for label in ("held_object","primary_hand","secondary_hand")]
close={**frame,"id":"front_grip","regions":boxes}
assert qa.check_response({**valid,"frames":[close]},["front_grip"])
assert not qa.check_response({**valid,"frames":[{**close,"regions":boxes[:2]}]},
                             ["front_grip"]),"Missing detected hand cannot yield vision GO"
try:qa.check_response({**valid,"frames":[{**close,"regions":[
    {**boxes[0],"ymax":110},*boxes[1:]]}]},["front_grip"])
except ValueError:pass
else:raise AssertionError("Empty hallucinated detector box accepted")
try:qa.check_response({**valid,"explanation":""},["action"])
except ValueError:pass
else:raise AssertionError("Empty reasoning accepted as visual GO")
print("PASS: vision GO is gated on high confidence, actual physical hold and zero objections")

selection_spec=importlib.util.spec_from_file_location("selection",Path(__file__).with_name("select-prop-contact-orientation.py"))
selection=importlib.util.module_from_spec(selection_spec)
selection_spec.loader.exec_module(selection)
assert set(selection.CHOICES)=={"forward","backward","inward","outward"}
assert set(selection.choices_for("head_direction"))=={
    "toward_elbow","toward_fingers","up","down","forward","backward"}
assert selection.choices_for("edge_direction")==selection.CHOICES
assert not any("axe" in candidate or "bow" in candidate for candidate in selection.CHOICES)
print("PASS: alternative orientations come from anatomy, not a named weapon")
