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
    import bpy
    for clip in CLIPS:
        src=directory/(clip+".fbx")
        dest=directory/(clip+".glb")
        if not src.is_file():
            raise FileNotFoundError(src)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        for action in list(bpy.data.actions):
            bpy.data.actions.remove(action)
        bpy.ops.import_scene.fbx(filepath=str(src),use_anim=True)
        armatures=[obj for obj in bpy.context.scene.objects if obj.type=="ARMATURE"]
        if not armatures:
            raise ValueError("FBX yielded no skeleton: "+clip)
        bpy.context.scene.render.fps=30
        bpy.ops.export_scene.gltf(filepath=str(dest),export_format="GLB",
            export_animations=True,export_skins=True,export_yup=True,
            export_image_format="AUTO")
        if not dest.is_file() or dest.stat().st_size<4096:
            raise ValueError("FBX to GLB failed: "+clip)
        print("CONVERTED",clip,src.stat().st_size,dest.stat().st_size,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=["download","convert"])
    p.add_argument("directory",type=Path)
    arg=p.parse_args()
    (download if arg.stage=="download" else convert)(arg.directory)
