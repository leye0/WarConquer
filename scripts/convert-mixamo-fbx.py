#!/usr/bin/env python3
"""Acquire selected existing Mixamo 'with axe' research clips or Blender-convert them.

No generative models. Never commit standalone licensed FBX files; the raw
source directory is a temporary runner location. Distribution/use is subject
to the Adobe Mixamo terms.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
import urllib.request

CLIPS={
    "Standing_Idle_3":"standing with axe",
    "Standing_Walk_Forward_3":"walking forward with axe",
    "Standing_Run_Forward_3":"running forward with axe",
    "Standing_Melee_Attack_Downward":"downward attack with axe",
}
PREFIX="https://huggingface.co/datasets/Linzhan/Mixamo-Animations-Characters/resolve/main/animation_motion_ybot/"
def download(directory):
    directory.mkdir(parents=True,exist_ok=True)
    report=[]
    for clip in CLIPS:
        destination=directory/(clip+".fbx")
        if not destination.is_file():
            url=PREFIX+clip+".fbx"
            request=urllib.request.Request(url,headers={"User-Agent":"WarConquer-Mixamo-Research-Pipeline/1.0"})
            with urllib.request.urlopen(request,timeout=150) as response:
                data=response.read(25*1024*1024+1)
            if len(data)>25*1024*1024 or len(data)<4096:
                raise ValueError("Unreasonable downloaded FBX size: "+clip)
            destination.write_bytes(data)
        data=destination.read_bytes()
        if not data.startswith(b"Kaydara FBX Binary"):
            raise ValueError("Downloaded nonbinary/non-FBX: "+clip)
        report.append({"clip":clip,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
    print(json.dumps(report,indent=2))

def convert(directory):
    """Use pinned precompiled FBX2glTF, no Blender or GPU required."""
    import subprocess
    binary=Path(os.environ.get("FBX2GLTF_BIN","node_modules/fbx2gltf/bin/Linux/FBX2glTF"))
    if not binary.is_file():
        raise FileNotFoundError("FBX2glTF precompiled executable not installed: "+str(binary))
    for clip in CLIPS:
        src=directory/(clip+".fbx")
        dest=directory/(clip+".glb")
        if not src.is_file():
            raise FileNotFoundError(src)
        command=[str(binary),"--binary","--anim-framerate","bake30",
                 "--input",str(src),"--output",str(dest.with_suffix(""))]
        subprocess.run(command,check=True,timeout=110)
        if not dest.is_file() or dest.stat().st_size<4096:
            raise ValueError("FBX2glTF failed: "+clip)
        with dest.open("rb") as source:
            if source.read(4)!=b"glTF":
                raise ValueError("Invalid converted GLB: "+clip)
        print("CONVERTED",clip,src.stat().st_size,dest.stat().st_size,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=["download","convert"])
    p.add_argument("directory",type=Path)
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None
    arg=p.parse_args(argv)
    (download if arg.stage=="download" else convert)(arg.directory)
