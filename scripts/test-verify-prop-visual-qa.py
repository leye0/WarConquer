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
