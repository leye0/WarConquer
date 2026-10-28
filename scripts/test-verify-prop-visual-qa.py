#!/usr/bin/env python3
"""No-network checks of the cheap vision GO/NO-GO decision contract."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location("visual_qa",Path(__file__).with_name("verify-prop-visual-qa.py"))
qa=importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)

assert qa.check_response({"go":True,"confidence":.94,"issues":[],"explanation":"proper grip"})
assert not qa.check_response({"go":False,"confidence":.94,"issues":["cutting edge reversed"],"explanation":"backwards blade"})
assert not qa.check_response({"go":True,"confidence":.6,"issues":[],"explanation":"not visible"})
assert not qa.check_response({"go":True,"confidence":.95,"issues":["floating"],"explanation":"misaligned"})
try:qa.check_response({"go":True,"confidence":1,"issues":[],"explanation":""})
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
