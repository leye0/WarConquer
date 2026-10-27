#!/usr/bin/env python3
"""Read-only GLB rig/animation correspondence preflight for one WarConquer experiment."""
import json
from pathlib import Path
import re
import struct

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"assets/experiments/rig-ready-3d/marches_hache/tpose-v2"
TARGET=DIR/"rigged.glb"
SOURCE=DIR/"motion/axe-chop-v1/source-motion.glb"
REPORT=DIR/"motion/axe-chop-v1/retarget-preflight.json"

def read_glb(path):
    data=path.read_bytes()
    if len(data)<20 or data[:4]!=b"glTF":
        raise ValueError(f"Invalid GLB: {path}")
    version,length=struct.unpack_from("<II",data,4)
    if version!=2 or length!=len(data):
        raise ValueError("Bad GLB header/size")
    offset=12
    doc=None
    binary=b""
    while offset+8<=len(data):
        size,typ=struct.unpack_from("<I4s",data,offset)
        offset+=8
        part=data[offset:offset+size]
        if len(part)!=size:
            raise ValueError("Incomplete chunk")
        offset+=size
        if typ==b"JSON":
            doc=json.loads(part)
        elif typ==b"BIN\x00":
            binary=part
    if doc is None:
        raise ValueError("Missing JSON")
    return doc,binary

def simplify(name):
    name=name.lower().strip()
    name=re.sub(r"^mixamorig\d*[:_\-]?", "", name)
    name=re.sub(r"[^a-z0-9]", "", name)
    return name

def joint_table(doc):
    ids={i for skin in doc.get("skins",[]) for i in skin.get("joints",[])}
    return {simplify(doc["nodes"][i].get("name","")):i for i in ids if doc["nodes"][i].get("name")}

def parent_map(doc):
    return {child:parent for parent,node in enumerate(doc.get("nodes",[]))
            for child in node.get("children",[])}

def basic_node(doc,i):
    node=doc["nodes"][i]
    return {k:node.get(k) for k in ("name","rotation","translation","scale","matrix") if k in node}

def sample_accessor(doc,binary,index):
    accessor=doc["accessors"][index]
    view=doc["bufferViews"][accessor["bufferView"]]
    comp=accessor["componentType"]
    kind=accessor["type"]
    if comp!=5126 or kind not in ("SCALAR","VEC3","VEC4"):
        return {"unsupported_type":f"{comp}/{kind}","count":accessor["count"]}
    size={"SCALAR":1,"VEC3":3,"VEC4":4}[kind]
    stride=view.get("byteStride",size*4)
    start=view.get("byteOffset",0)+accessor.get("byteOffset",0)
    count=accessor["count"]
    indices=sorted(set((0,count//2,count-1)))
    values=[]
    for i in indices:
        at=start+i*stride
        values.append([round(x,5) for x in struct.unpack_from("<"+"f"*size,binary,at)])
    return {"count":count,"samples":values,"sample_indices":indices,
            "min":accessor.get("min"),"max":accessor.get("max")}

def main():
    target,_=read_glb(TARGET)
    source,source_bin=read_glb(SOURCE)
    t=joint_table(target)
    s=joint_table(source)
    intersection=sorted(set(t)&set(s))
    src_parent=parent_map(source)
    tgt_parent=parent_map(target)
    channel_info=[]
    sample_names={"hips","spine","spine1","spine2","leftarm","rightarm",
                  "leftforearm","rightforearm","leftupleg","rightupleg"}
    for anim in source.get("animations",[]):
        for channel in anim["channels"]:
            node_id=channel["target"].get("node")
            name=source["nodes"][node_id].get("name","") if node_id is not None else ""
            norm=simplify(name)
            entry={"bone":name,"normalized":norm,"path":channel["target"]["path"],
                   "in_target":norm in t}
            if norm in sample_names and channel["target"]["path"] in ("rotation","translation"):
                sampler=anim["samplers"][channel["sampler"]]
                entry["input"]=sample_accessor(source,source_bin,sampler["input"])
                entry["output"]=sample_accessor(source,source_bin,sampler["output"])
            channel_info.append(entry)
    roots_target=[{"node":i,**basic_node(target,i)}
                  for i,node in enumerate(target["nodes"]) if i not in tgt_parent]
    roots_source=[{"node":i,**basic_node(source,i)}
                  for i,node in enumerate(source["nodes"]) if i not in src_parent]
    highlighted={}
    for name in ("hips","spine","leftarm","rightarm","leftforearm",
                 "rightforearm","leftupleg","rightupleg"):
        highlighted[name]={
            "source":basic_node(source,s[name]) if name in s else None,
            "target":basic_node(target,t[name]) if name in t else None,
            "source_parent":source["nodes"][src_parent[s[name]]].get("name") if name in s and s[name] in src_parent else None,
            "target_parent":target["nodes"][tgt_parent[t[name]]].get("name") if name in t and t[name] in tgt_parent else None,
        }
    result={
        "purpose":"Read-only skeletal retarget compatibility, not proof of valid deformation",
        "target":{"joint_count":len(t),"joint_names":sorted(t),"root_nodes":roots_target},
        "source":{"joint_count":len(s),"joint_names":sorted(s),"root_nodes":roots_source},
        "common_joint_count":len(intersection),"common_joint_names":intersection,
        "target_joints_absent_in_source":sorted(set(t)-set(s)),
        "source_joints_absent_in_target":sorted(set(s)-set(t)),
        "highlights":highlighted,
        "animation_count":len(source.get("animations",[])),
        "animation_channel_count":len(channel_info),
        "animation_channels":channel_info,
        "requires_rest_pose_alignment":True,
        "ready_for_naive_name_mapping":len(intersection)>=30,
    }
    REPORT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:result[k] for k in ("common_joint_count","target_joints_absent_in_source",
             "animation_count","animation_channel_count","ready_for_naive_name_mapping")},indent=2))
if __name__=="__main__":
    main()
