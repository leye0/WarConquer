#!/usr/bin/env python3
"""Validate the no-API skeletal transfer artifact before publication."""
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/axe-chop-v1"
OUT=DIR/"warconquer-animated.glb"
REPORT=DIR/"retarget-report.json"

def main():
    info=json.loads(REPORT.read_text())
    data=OUT.read_bytes()
    assert len(data)>4096 and data[:4]==b"glTF"
    assert struct.unpack_from("<I",data,8)[0]==len(data)
    n,typ=struct.unpack_from("<I4s",data,12)
    assert typ==b"JSON"
    gltf=json.loads(data[20:20+n])
    assert gltf.get("skins") and len(gltf["skins"][0]["joints"])>=45
    assert len(gltf.get("animations",[]))==1
    anim=gltf["animations"][0]
    assert len(anim["channels"])>=45
    assert len(anim["samplers"])==len(anim["channels"])
    assert any(c["target"]["path"]=="rotation" for c in anim["channels"])
    assert all(c["target"]["node"] in gltf["skins"][0]["joints"]
               for c in anim["channels"])
    assert any("JOINTS_0" in p.get("attributes",{}) and
               "WEIGHTS_0" in p.get("attributes",{})
               for mesh in gltf["meshes"] for p in mesh["primitives"])
    assert info["mapped_joints"]>=45
    assert info["frame_count"]>=48
    assert 3.0<=info["duration_seconds"]<=5.0
    assert info["in_place_motion"] is True
    assert info["source_motion_sha256"]=="fbf9f2a7a934a8cef3154b47b968e06fbcc7458ac0c46cfb95c6ed06ed8f7a87"
    assert hashlib.sha256(data).hexdigest()==info["output_sha256"]
    print(json.dumps({"validated":True,"nodes":len(gltf["nodes"]),
                      "joints":len(gltf["skins"][0]["joints"]),
                      "channels":len(anim["channels"]),
                      "frames":info["frame_count"],
                      "duration":info["duration_seconds"]},indent=2))
if __name__=="__main__":
    main()
