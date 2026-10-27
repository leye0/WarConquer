#!/usr/bin/env python3
"""Retarget a seeded Uthana UE5 Manny GLB clip onto the approved Mixamo GLB.

No AI calls and no inference cost. Rest-pose-corrected world-space rotation
deltas transfer from explicit corresponding joints; root travel is intentionally
excluded for the in-place first-attack experiment. The original target mesh,
skin, bind matrices and textures remain byte-for-byte part of the new GLB.
Final acceptance also requires rendered, human visual QA.
"""
import bisect
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from inspect_rig_skeletons import read_glb, joint_table, parent_map

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"assets/experiments/rig-ready-3d/marches_hache/tpose-v2"
SOURCE=DIR/"motion/axe-chop-v1/source-motion.glb"
TARGET=DIR/"rigged.glb"
DEST=DIR/"motion/axe-chop-v1/warconquer-animated.glb"
REPORT=DIR/"motion/axe-chop-v1/retarget-report.json"
SOURCE_SHA="fbf9f2a7a934a8cef3154b47b968e06fbcc7458ac0c46cfb95c6ed06ed8f7a87"
TARGET_SHA="9bb357587de46032de203abe735b3eab140d32c982066b15da55c7c339439273"
FPS=24
Q_ID=(0.0,0.0,0.0,1.0)

def normq(q):
    m=math.sqrt(sum(x*x for x in q))
    if m<1e-8 or not math.isfinite(m):
        raise ValueError("Non-finite or zero quaternion")
    return tuple(x/m for x in q)

def qmul(a,b):
    x,y,z,w=a
    X,Y,Z,W=b
    return normq((w*X+x*W+y*Z-z*Y,
                  w*Y-x*Z+y*W+z*X,
                  w*Z+x*Y-y*X+z*W,
                  w*W-x*X-y*Y-z*Z))

def qinv(q):
    x,y,z,w=normq(q)
    return (-x,-y,-z,w)

def slerp(a,b,t):
    a=normq(a);b=normq(b)
    d=sum(x*y for x,y in zip(a,b))
    if d<0:
        b=tuple(-x for x in b)
        d=-d
    d=min(1.0,max(-1.0,d))
    if d>.9995:
        return normq(tuple(x+(y-x)*t for x,y in zip(a,b)))
    theta=math.acos(d)
    s=math.sin(theta)
    u=math.sin((1-t)*theta)/s
    v=math.sin(t*theta)/s
    return normq(tuple(u*x+v*y for x,y in zip(a,b)))

def self_test():
    q=normq((0,0,math.sin(math.pi/4),math.cos(math.pi/4)))
    assert max(abs(a-b) for a,b in zip(qmul(q,qinv(q)),Q_ID))<1e-6
    half=slerp(Q_ID,q,.5)
    assert abs(half[2]-math.sin(math.pi/8))<1e-6
    assert qmul(Q_ID,q)==q
    print("Quaternion composition, inverse and slerp: OK")

def joint_mapping():
    m={"hips":"pelvis","spine":"spine01","spine1":"spine03",
       "spine2":"spine05","neck":"neck02","head":"head"}
    for side,letter in (("left","l"),("right","r")):
        m.update({
            side+"shoulder":"clavicle"+letter,
            side+"arm":"upperarm"+letter,
            side+"forearm":"lowerarm"+letter,
            side+"hand":"hand"+letter,
            side+"upleg":"thigh"+letter,
            side+"leg":"calf"+letter,
            side+"foot":"foot"+letter,
            side+"toebase":"ball"+letter,
        })
        for digit in ("thumb","index","middle","ring","pinky"):
            for k in range(1,4):
                m[side+"hand"+digit+str(k)]=digit+"0"+str(k)+letter
    return m

def float_accessor(doc,binary,index):
    accessor=doc["accessors"][index]
    if accessor["componentType"]!=5126 or accessor.get("sparse"):
        raise ValueError("Expected dense float accessor")
    dim={"SCALAR":1,"VEC3":3,"VEC4":4}.get(accessor["type"])
    if dim is None:
        raise ValueError("Unexpected float accessor type")
    view=doc["bufferViews"][accessor["bufferView"]]
    if view["buffer"]!=0:
        raise ValueError("Expected a single embedded GLB buffer")
    stride=view.get("byteStride",dim*4)
    offset=view.get("byteOffset",0)+accessor.get("byteOffset",0)
    out=[]
    for i in range(accessor["count"]):
        out.append(struct.unpack_from("<"+"f"*dim,binary,offset+i*stride))
    return out

def motion_tracks(source,binary):
    animations=source.get("animations",[])
    if len(animations)!=1:
        raise ValueError("Expected exactly one source skeletal animation")
    animation=animations[0]
    tracks={}
    duration=0.0
    for channel in animation["channels"]:
        if channel["target"].get("path")!="rotation":
            continue
        i=channel["target"]["node"]
        sampler=animation["samplers"][channel["sampler"]]
        times=[v[0] for v in float_accessor(source,binary,sampler["input"])]
        vals=float_accessor(source,binary,sampler["output"])
        interpolation=sampler.get("interpolation","LINEAR")
        if interpolation=="CUBICSPLINE":
            if len(vals)!=3*len(times):
                raise ValueError("Invalid cubic spline accessor length")
            vals=vals[1::3]  # Key values, excluding incoming/outgoing tangents.
        elif interpolation not in ("LINEAR","STEP"):
            raise ValueError("Unsupported interpolation "+interpolation)
        if len(times)!=len(vals) or not times or sorted(times)!=times:
            raise ValueError("Malformed motion keyframes")
        duration=max(duration,times[-1])
        tracks[i]=(times,[normq(q) for q in vals],interpolation)
    if not 1.0<=duration<=9.0 or len(tracks)<40:
        raise ValueError("Generated motion too short/long or too few rotation tracks")
    return tracks,duration

def interpolate(track,when):
    times,values,method=track
    if when<=times[0]:
        return values[0]
    if when>=times[-1]:
        return values[-1]
    right=bisect.bisect_right(times,when)
    left=right-1
    if method=="STEP" or times[right]-times[left]<1e-8:
        return values[left]
    return slerp(values[left],values[right],
                 (when-times[left])/(times[right]-times[left]))

def world_orientations(nodes,parents,locals_):
    computed={}
    def calc(i):
        if i not in computed:
            parent=parents.get(i)
            computed[i]=qmul(calc(parent),locals_[i]) if parent is not None else locals_[i]
        return computed[i]
    for i in range(len(nodes)):
        calc(i)
    return computed

def add_floats(document,binary,values,kind,minmax=False):
    dim={"SCALAR":1,"VEC4":4}[kind]
    if len(values)%dim:
        raise ValueError("Misaligned float accessor")
    while len(binary)%4:
        binary.append(0)
    offset=len(binary)
    binary.extend(struct.pack("<"+"f"*len(values),*values))
    view=len(document.setdefault("bufferViews",[]))
    document["bufferViews"].append({
        "buffer":0,"byteOffset":offset,"byteLength":len(values)*4})
    accessor=len(document.setdefault("accessors",[]))
    item={"bufferView":view,"componentType":5126,
          "count":len(values)//dim,"type":kind}
    if minmax:
        item["min"]=[min(values)]
        item["max"]=[max(values)]
    document["accessors"].append(item)
    return accessor

def write_glb(doc,binary,path):
    while len(binary)%4:
        binary.append(0)
    doc["buffers"][0]["byteLength"]=len(binary)
    j=json.dumps(doc,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    j+=b" " * ((-len(j))%4)
    total=12+8+len(j)+8+len(binary)
    with path.open("wb") as f:
        f.write(struct.pack("<4sII",b"glTF",2,total))
        f.write(struct.pack("<I4s",len(j),b"JSON"))
        f.write(j)
        f.write(struct.pack("<I4s",len(binary),b"BIN\x00"))
        f.write(binary)

def run():
    for path,expected in ((SOURCE,SOURCE_SHA),(TARGET,TARGET_SHA)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError("Pinned animation or character input changed: "+str(path))
    source,source_binary=read_glb(SOURCE)
    target,target_binary=read_glb(TARGET)
    src_joints=joint_table(source)
    tgt_joints=joint_table(target)
    names=joint_mapping()
    missing_src=[key for key,v in names.items() if v not in src_joints]
    missing_tgt=[key for key in names if key not in tgt_joints]
    if missing_src or missing_tgt or len(names)!=52:
        raise ValueError(f"Noncanonical UE5-to-Mixamo rig: missing source={missing_src}; target={missing_tgt}")
    source_parent=parent_map(source)
    target_parent=parent_map(target)
    sr=source["nodes"]
    tr=target["nodes"]
    source_rest=[normq(n.get("rotation",Q_ID)) for n in sr]
    target_rest=[normq(n.get("rotation",Q_ID)) for n in tr]
    source_rest_world=world_orientations(sr,source_parent,source_rest)
    target_rest_world=world_orientations(tr,target_parent,target_rest)
    tracks,duration=motion_tracks(source,source_binary)
    frames=int(round(duration*FPS))+1
    if frames<48 or frames>220:
        raise ValueError("Unsupported number of resampled frames")
    times=[duration*i/(frames-1) for i in range(frames)]
    animated={i:[] for i in tgt_joints.values()}
    moved={}
    pairs={tgt_joints[k]:src_joints[v] for k,v in names.items()}
    for frame,time in enumerate(times):
        slocal=[interpolate(tracks[i],time) if i in tracks else q
                for i,q in enumerate(source_rest)]
        sworld=world_orientations(sr,source_parent,slocal)
        tlocal={}
        tworld={}
        def calc_target(i):
            if i in tworld:
                return tworld[i]
            parent=target_parent.get(i)
            pw=calc_target(parent) if parent is not None else Q_ID
            if i in pairs:
                source_i=pairs[i]
                world_delta=qmul(sworld[source_i],qinv(source_rest_world[source_i]))
                desired=qmul(world_delta,target_rest_world[i])
                local=qmul(qinv(pw),desired)
            else:
                local=target_rest[i]
            tlocal[i]=local
            tworld[i]=qmul(pw,local)
            return tworld[i]
        for i in range(len(tr)):
            calc_target(i)
        for i in animated:
            animated[i].append(tlocal[i])
    # This trial is intentionally in-place: do not transfer UE5 pelvis translations,
    # which use a different body scale and reference pivot than the Mixamo mesh.
    appended=bytearray(target_binary)
    time_accessor=add_floats(target,appended,times,"SCALAR",minmax=True)
    channels=[]
    samplers=[]
    for i in sorted(animated):
        flat=[x for q in animated[i] for x in q]
        accessor=add_floats(target,appended,flat,"VEC4")
        sampler=len(samplers)
        samplers.append({"input":time_accessor,"output":accessor,
                         "interpolation":"LINEAR"})
        channels.append({"sampler":sampler,
                         "target":{"node":i,"path":"rotation"}})
        first=animated[i][0]
        max_angle=2*math.degrees(math.acos(min(1.0,abs(
            sum(a*b for a,b in zip(q,first))))))
        for q in animated[i][1:]:
            max_angle=max(max_angle,2*math.degrees(math.acos(min(1.0,abs(
                sum(a*b for a,b in zip(q,first)))))))
        moved[tr[i]["name"]]=round(max_angle,3)
    if max(moved.values())<5:
        raise ValueError("No meaningful skeletal movement was transferred")
    target["animations"]=[{
        "name":"WarConquer_Marches_Axeman_AxeChop_Seed20261027",
        "samplers":samplers,"channels":channels,
        "extras":{"source_model":"uthana/text-to-motion-diffusion-v2",
                  "retargeting":"UE5 Manny to Mixamo; corrected world rest orientation; in-place"}
    }]
    write_glb(target,appended,DEST)
    report={
        "status":"retargeted-awaiting-visual-animation-qa",
        "strategy":"world-rest-relative quaternion transfer with explicit UE5 Manny to Mixamo bone map",
        "source_motion_sha256":SOURCE_SHA,
        "target_rig_sha256":TARGET_SHA,
        "output_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
        "output_bytes":DEST.stat().st_size,
        "mapped_joints":len(pairs),"mapping":names,
        "frame_count":frames,"fps":FPS,"duration_seconds":round(duration,5),
        "rotation_channels":len(channels),
        "max_rotation_change_degrees_by_joint":moved,
        "in_place_motion":True,
        "physical_prop_generated":False,
        "manual_visual_review_required":True,
        "notes":"No foot or prop collision simulation. Skeletal track integrity does not certify realistic axe-chop motion."
    }
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:report[k] for k in
          ("status","mapped_joints","rotation_channels","frame_count",
           "duration_seconds","output_bytes")},indent=2))

if __name__=="__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        run()
