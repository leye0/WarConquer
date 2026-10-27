#!/usr/bin/env python3
"""Software-skin a retargeted GLB at 5 times to expose actual mesh deformation.

No Blender, GPU or AI calls. The contact sheet shows front/side silhouettes,
not a substitute for approving the human realism of an attack motion.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/axe-chop-v1"
INPUT=OUT/"warconquer-animated.glb"
PREVIEW=OUT/"animated-five-frames-front-side.png"
REPORT=OUT/"animation-visual-qa.json"
helper_path=ROOT/"scripts/inspect-rig-skeletons.py"
spec=importlib.util.spec_from_file_location("rig_inspection_preview",helper_path)
helper=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

def accessor(doc,binary,i):
    a=doc["accessors"][i]
    v=doc["bufferViews"][a["bufferView"]]
    component={5121:np.uint8,5123:np.uint16,5125:np.uint32,5126:np.float32}[a["componentType"]]
    dims={"SCALAR":1,"VEC3":3,"VEC4":4,"MAT4":16}[a["type"]]
    dtype=np.dtype(component).newbyteorder("<")
    stride=v.get("byteStride",dtype.itemsize*dims)
    offset=v.get("byteOffset",0)+a.get("byteOffset",0)
    if stride==dtype.itemsize*dims:
        result=np.frombuffer(binary,dtype=dtype,count=a["count"]*dims,offset=offset)
        return result.reshape(a["count"],dims).copy()
    return np.stack([np.frombuffer(binary,dtype=dtype,count=dims,
                    offset=offset+k*stride) for k in range(a["count"])])

def transform(node,rotation=None):
    if "matrix" in node:
        if rotation is not None:
            raise ValueError("Animation targets a node with matrix transform")
        return np.array(node["matrix"],dtype=np.float64).reshape(4,4,order="F")
    x,y,z,w=rotation if rotation is not None else node.get("rotation",(0,0,0,1))
    norm=(x*x+y*y+z*z+w*w)**.5
    x,y,z,w=x/norm,y/norm,z/norm,w/norm
    r=np.array([
        [1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
        [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
        [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]
    ],dtype=np.float64)
    scale=np.array(node.get("scale",(1,1,1)),dtype=np.float64)
    m=np.eye(4,dtype=np.float64)
    m[:3,:3]=r@np.diag(scale)
    m[:3,3]=node.get("translation",(0,0,0))
    return m

def worlds(doc,rotations):
    nodes=doc["nodes"]
    parents=helper.parent_map(doc)
    found={}
    def calc(i):
        if i not in found:
            p=parents.get(i)
            local=transform(nodes[i],rotations.get(i))
            found[i]=calc(p)@local if p is not None else local
        return found[i]
    for i in range(len(nodes)):
        calc(i)
    return found

def skinned(doc,base,weights,joints,inv_bind,mesh_idx,world):
    mesh_node=doc["nodes"][mesh_idx]
    skin=doc["skins"][mesh_node["skin"]]
    # Per Khronos glTF 2.0, the transform of the skinned mesh node is
    # ignored by skinning; joint world matrices already give world positions.
    palette=np.array([world[j]@inv_bind[k]
                      for k,j in enumerate(skin["joints"])])
    verts4=np.column_stack((base,np.ones(len(base))))
    wsum=weights.sum(axis=1)
    if np.any(wsum<=0):
        raise ValueError("Some mesh vertices have no skin weights")
    weights=weights/wsum[:,None]
    out=np.zeros((len(base),4),dtype=np.float64)
    for k in range(4):
        transforms=palette[joints[:,k]]
        transformed=np.einsum("nij,nj->ni",transforms,verts4)
        out+=transformed*weights[:,k,None]
    if np.max(np.abs(out[:,3]-1))>1e-3:
        raise ValueError("Nonaffine skinning output")
    return out[:,:3]

def panel(vertices,faces,center,scale,angle,up,side,depth_axis):
    theta=np.deg2rad(angle)
    pts=(vertices-center)/scale
    h=pts[:,side]*np.cos(theta)+pts[:,depth_axis]*np.sin(theta)
    depth=-pts[:,side]*np.sin(theta)+pts[:,depth_axis]*np.cos(theta)
    vert=pts[:,up]
    px=h*315+180
    py=180-vert*315
    centroid_depth=depth[faces].mean(axis=1)
    order=np.argsort(centroid_depth)
    canvas=Image.new("RGB",(360,360),"#202329")
    drawer=ImageDraw.Draw(canvas)
    for idx in order:
        a,b,c=map(int,faces[idx])
        ux,uy=px[b]-px[a],py[b]-py[a]
        vx,vy=px[c]-px[a],py[c]-py[a]
        shade=int(np.clip(136+55*np.tanh((ux*vy-uy*vx)/4000),75,195))
        drawer.polygon([(float(px[t]),float(py[t])) for t in (a,b,c)],
                       fill=(shade,shade+7,shade+13))
    return canvas

def main():
    report=json.loads((OUT/"retarget-report.json").read_text())
    digest=hashlib.sha256(INPUT.read_bytes()).hexdigest()
    if digest!=report["output_sha256"]:
        raise ValueError("Animated GLB fingerprint changed")
    doc,binary=helper.read_glb(INPUT)
    mesh_idx=next(i for i,n in enumerate(doc["nodes"]) if "mesh" in n and "skin" in n)
    primitive=doc["meshes"][doc["nodes"][mesh_idx]["mesh"]]["primitives"][0]
    attrs=primitive["attributes"]
    base=accessor(doc,binary,attrs["POSITION"]).astype(np.float64)
    weights=accessor(doc,binary,attrs["WEIGHTS_0"]).astype(np.float64)
    joints=accessor(doc,binary,attrs["JOINTS_0"]).astype(np.int64)
    faces=accessor(doc,binary,primitive["indices"]).reshape(-1,3)
    inv_bind_raw=accessor(doc,binary,doc["skins"][0]["inverseBindMatrices"])
    inv_bind=np.array([v.reshape(4,4,order="F") for v in inv_bind_raw],dtype=np.float64)
    if len(faces)>12500:
        faces=faces[::2]
    anim=doc["animations"][0]
    rotations={}
    times=None
    for channel in anim["channels"]:
        if channel["target"]["path"]!="rotation":
            continue
        sampler=anim["samplers"][channel["sampler"]]
        track_time=accessor(doc,binary,sampler["input"])[:,0]
        if times is None:
            times=track_time
        elif len(times)!=len(track_time) or np.max(abs(times-track_time))>1e-5:
            raise ValueError("Different timeline for retarget channels")
        rotations[channel["target"]["node"]]=accessor(doc,binary,sampler["output"])
    rest_world=worlds(doc,{})
    rest=skinned(doc,base,weights,joints,inv_bind,mesh_idx,rest_world)
    rest_mismatch=float(np.max(np.linalg.norm(rest-base,axis=1)))
    original_extent=float(np.max(base.max(axis=0)-base.min(axis=0)))
    if rest_mismatch>original_extent*0.08:
        raise ValueError(f"Skin bind/rest mismatch: {rest_mismatch:.5f} exceeds 8% of character size")
    lo=rest.min(axis=0);hi=rest.max(axis=0)
    center=(lo+hi)/2
    extent=hi-lo
    size=max(float(extent.max()),1e-6)
    up=int(np.argmax(extent))
    other=[i for i in range(3) if i!=up]
    side,depth_axis=other
    labels=("start","wind-up","strike","follow-through","recovery")
    frame_idxs=np.round(np.linspace(0,len(times)-1,5)).astype(int)
    image=Image.new("RGB",(5*360,2*400),"#17191d")
    writer=ImageDraw.Draw(image)
    records=[]
    for k,frame in enumerate(frame_idxs):
        posed_world=worlds(doc,{i:q[frame] for i,q in rotations.items()})
        vertices=skinned(doc,base,weights,joints,inv_bind,mesh_idx,posed_world)
        if not np.isfinite(vertices).all():
            raise ValueError("Non-finite skinned vertices")
        bounds=np.array([vertices.min(axis=0),vertices.max(axis=0)])
        max_shift=float(np.max(np.linalg.norm(vertices-rest,axis=1)))
        for row,angle in enumerate((0,90)):
            img=panel(vertices,faces,center,size,angle,up,side,depth_axis)
            image.paste(img,(k*360,row*400))
            writer.text((k*360+12,row*400+368),
                        f"{labels[k]} | {float(times[frame]):.2f}s | {'front' if row==0 else 'side'}",
                        fill="#eeeeee")
        records.append({"stage":labels[k],"time_seconds":round(float(times[frame]),3),
                        "bounds":bounds.round(4).tolist(),
                        "max_vertex_shift_rest":round(max_shift,4)})
    image.save(PREVIEW,optimize=True)
    suspicious=any(max((np.array(r["bounds"])[1]-np.array(r["bounds"])[0]))>size*3
                   for r in records)
    result={"status":"software-skin-rendered-awaiting-human-motion-qa",
            "mesh_vertices":len(base),"faces_rendered":len(faces),
            "rest_skinning_max_vertex_mismatch":round(rest_mismatch,6),
            "skin_joint_count":len(doc["skins"][0]["joints"]),
            "samples":records,"rest_bounds":np.array([lo,hi]).round(4).tolist(),
            "axis_vertical":up,"deformation_explosion_detected":bool(suspicious),
            "preview":PREVIEW.name,"photo_realism_or_motion_quality_approved":False}
    REPORT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"rendered":True,"deformation_explosion_detected":suspicious,
                      "max_shifts":[r["max_vertex_shift_rest"] for r in records]}))
    if suspicious:
        raise ValueError("Animated pose bounds exceeded 3x character size")

if __name__=="__main__":
    main()
