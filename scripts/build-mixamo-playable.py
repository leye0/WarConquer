#!/usr/bin/env python3
"""Compose a UV-textured playable GLB with authentic archived Mixamo FBX clips.

Source is the already-rigged, already-animated Hunyuan/Uthana character.
No inference or paid calls; original skin joints and bind matrices remain.
Four archived axe animations are retargeted after offline FBX2glTF FBX to GLB
conversion; the experimental 4-view atlas is distinct from AI texture baking.
"""
from __future__ import annotations
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import struct

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"assets/experiments/rig-ready-3d/marches_hache/tpose-v2"
SRC=BASE/"motion/axe-chop-v1/warconquer-animated.glb"
OUT=BASE/"motion/mixamo-axe-v1/warconquer-playable.glb"
REPORT=BASE/"motion/mixamo-axe-v1/report.json"
VIEWS=ROOT/"assets/experiments/rig-source-turnaround/marches_hache/tpose-v2"
ORDER=("front","back","left","right")
AXES={"front":(0,0,1),"back":(0,0,-1),"left":(-1,0,0),"right":(1,0,0)}
COMPONENT={5120:("b",1),5121:("B",1),5122:("h",2),5123:("H",2),5125:("I",4),5126:("f",4)}
DIM={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}

def load_glb(path):
    raw=path.read_bytes()
    magic,version,total=struct.unpack_from("<4sII",raw,0)
    if (magic,version,total)!=(b"glTF",2,len(raw)):
        raise ValueError("Source GLB header invalid")
    n,jtyp=struct.unpack_from("<I4s",raw,12)
    if jtyp!=b"JSON":
        raise ValueError("Source GLB JSON chunk missing")
    doc=json.loads(raw[20:20+n])
    p=20+n
    m,btyp=struct.unpack_from("<I4s",raw,p)
    if btyp!=b"BIN\x00":
        raise ValueError("Expected embedded GLB BIN")
    return doc,bytearray(raw[p+8:p+8+m])

def align(buf):
    buf.extend(b"\0"*((-len(buf))%4))

def write_glb(doc,buf,path):
    align(buf)
    doc["buffers"][0]["byteLength"]=len(buf)
    j=json.dumps(doc,separators=(",",":"),ensure_ascii=True).encode()
    j+=b" "*((-len(j))%4)
    total=12+8+len(j)+8+len(buf)
    data=struct.pack("<4sII",b"glTF",2,total)+struct.pack("<I4s",len(j),b"JSON")+j+struct.pack("<I4s",len(buf),b"BIN\x00")+buf
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)

def accessor(doc,buf,idx):
    a=doc["accessors"][idx]
    if a.get("sparse") or "bufferView" not in a:
        raise ValueError("Unsupported accessor")
    bv=doc["bufferViews"][a["bufferView"]]
    fmt,unit=COMPONENT[a["componentType"]]
    nc=DIM[a["type"]]
    step=bv.get("byteStride",nc*unit)
    off=bv.get("byteOffset",0)+a.get("byteOffset",0)
    return [struct.unpack_from("<"+str(nc)+fmt,buf,off+i*step) for i in range(a["count"])]

def add_accessor(doc,buf,values,typ,component=5126,normalized=False,bounds=False):
    nc=DIM[typ]
    fmt,_=COMPONENT[component]
    align(buf)
    pos=len(buf)
    for v in values:
        if len(v)!=nc:
            raise ValueError("Accessor vector dimension mismatch")
        buf.extend(struct.pack("<"+str(nc)+fmt,*v))
    bv=len(doc["bufferViews"])
    doc["bufferViews"].append({"buffer":0,"byteOffset":pos,"byteLength":len(buf)-pos})
    a={"bufferView":bv,"componentType":component,"count":len(values),"type":typ}
    if normalized:
        a["normalized"]=True
    if bounds:
        a["min"]=[min(v[j] for v in values) for j in range(nc)]
        a["max"]=[max(v[j] for v in values) for j in range(nc)]
    doc["accessors"].append(a)
    return len(doc["accessors"])-1

def bbox_alpha(path):
    img=Image.open(path).convert("RGBA")
    alpha=img.getchannel("A")
    mask=alpha.point(lambda a:255 if a>32 else 0)
    bb=mask.getbbox()
    if not bb:
        raise ValueError("Transparent source image: "+str(path))
    if bb[2]-bb[0]<80 or bb[3]-bb[1]<200:
        raise ValueError("Too small source silhouette: "+str(path))
    return img,bb

def atlas_and_uv(doc,buf):
    if len(doc["meshes"])!=1 or len(doc["meshes"][0]["primitives"])!=1:
        raise ValueError("Expected approved single-mesh pilot")
    prim=doc["meshes"][0]["primitives"][0]
    if prim.get("mode",4)!=4:
        raise ValueError("Expected GLB triangle primitive")
    orig=prim["attributes"]
    for k in ("POSITION","NORMAL","JOINTS_0","WEIGHTS_0"):
        if k not in orig:
            raise ValueError("Required rig attribute missing: "+k)
    positions=accessor(doc,buf,orig["POSITION"])
    normals=accessor(doc,buf,orig["NORMAL"])
    ids=[x[0] for x in accessor(doc,buf,prim["indices"])]
    if len(ids)%3:
        raise ValueError("Triangle index count invalid")
    attrvals={k:accessor(doc,buf,ai) for k,ai in orig.items() if k!="COLOR_0"}
    xs=[p[0] for p in positions]
    ys=[p[1] for p in positions]
    zs=[p[2] for p in positions]
    model_limits={"front":(min(xs),max(xs)), "back":(-max(xs),-min(xs)),
                  "left":(min(zs),max(zs)), "right":(-max(zs),-min(zs))}
    atlas=Image.new("RGB",(2048,2048))
    bounds={}
    for i,name in enumerate(ORDER):
        image,bb=bbox_alpha(VIEWS/(name+".png"))
        bounds[name]=bb
        # Flatten transparency only in the atlas; the geometry remains opaque.
        tile=Image.new("RGBA",image.size,(55,52,49,255))
        tile.alpha_composite(image)
        atlas.paste(tile.convert("RGB"),((i%2)*1024,(i//2)*1024))
    uv=[]
    rewritten={k:[] for k in attrvals}
    by_view={name:0 for name in ORDER}
    for t in range(0,len(ids),3):
        triangle=ids[t:t+3]
        a,b,c=(positions[q] for q in triangle)
        u=[b[k]-a[k] for k in range(3)]
        v=[c[k]-a[k] for k in range(3)]
        n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        # Some source triangle winding may be reversed. Use averaged supplied
        # glTF vertex normals, which reflect the intended outward surface.
        n=tuple(sum(normals[q][j] for q in triangle) for j in range(3))
        if max(abs(n[0]),abs(n[2]))<1e-8:
            name="front"
        elif abs(n[0])>abs(n[2])*1.1:
            name="right" if n[0]>0 else "left"
        else:
            name="front" if n[2]>0 else "back"
        by_view[name]+=1
        left,right=model_limits[name]
        top,bottom=max(ys),min(ys)
        ib=bounds[name]
        for q in triangle:
            for key,values in attrvals.items():
                rewritten[key].append(values[q])
            x,y,z=positions[q]
            horizontal={"front":x,"back":-x,"left":z,"right":-z}[name]
            fx=(horizontal-left)/max(1e-9,right-left)
            fy=(top-y)/max(1e-9,top-bottom)
            fx=max(0,min(1,fx))
            fy=max(0,min(1,fy))
            px=ib[0]+fx*(ib[2]-ib[0])
            py=ib[1]+fy*(ib[3]-ib[1])
            quadrant=ORDER.index(name)
            uv.append(((px+(quadrant%2)*1024)/2048,
                       (py+(quadrant//2)*1024)/2048))
    newattrs={}
    for key,values in rewritten.items():
        old=doc["accessors"][orig[key]]
        newattrs[key]=add_accessor(doc,buf,values,old["type"],
                        old["componentType"],bool(old.get("normalized")),
                        key=="POSITION")
    newattrs["TEXCOORD_0"]=add_accessor(doc,buf,uv,"VEC2")
    prim["attributes"]=newattrs
    prim["indices"]=add_accessor(doc,buf,[(i,) for i in range(len(ids))],"SCALAR",5125,bounds=True)
    atlasbuf=io.BytesIO()
    atlas.save(atlasbuf,format="PNG",optimize=True)
    payload=atlasbuf.getvalue()
    align(buf)
    pos=len(buf)
    buf.extend(payload)
    image_view=len(doc["bufferViews"])
    doc["bufferViews"].append({"buffer":0,"byteOffset":pos,"byteLength":len(payload)})
    doc.setdefault("images",[]).append({"name":"Marches four-view reference atlas v1",
                                         "mimeType":"image/png","bufferView":image_view})
    image_id=len(doc["images"])-1
    doc.setdefault("samplers",[]).append({"magFilter":9729,"minFilter":9987,"wrapS":33071,"wrapT":33071})
    sampler_id=len(doc["samplers"])-1
    doc.setdefault("textures",[]).append({"source":image_id,"sampler":sampler_id})
    texture_id=len(doc["textures"])-1
    doc.setdefault("materials",[]).append({"name":"Marches · 4-view projected preview",
       "pbrMetallicRoughness":{"baseColorTexture":{"index":texture_id},
                               "metallicFactor":0.0,"roughnessFactor":0.9},
       "alphaMode":"OPAQUE","doubleSided":True})
    prim["material"]=len(doc["materials"])-1
    return {"triangle_count":len(ids)//3,"new_vertex_count":len(ids),
            "atlas_bytes":len(payload),"triangles_by_projection":by_view,
            "source_silhouette_bboxes":bounds}

def qnorm(q):
    s=math.sqrt(sum(x*x for x in q))
    return tuple(x/s for x in q)
def qmul(a,b):
    x,y,z,w=a; X,Y,Z,W=b
    return qnorm((w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,
                  w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z))
def qinv(q):
    return (-q[0],-q[1],-q[2],q[3])
def qaxis(axis,degrees):
    s=math.sin(math.radians(degrees)/2)
    return tuple(v*s for v in axis)+(math.cos(math.radians(degrees)/2),)
Q=(0.,0.,0.,1.)


def mixamo_animation(doc,binary):
    import importlib.util
    support=ROOT/"scripts/retarget-rig-ready-motion.py"
    spec=importlib.util.spec_from_file_location("warconquer_retarget_support",support)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    candidates=[]
    for anim in doc.get("animations",[]):
        tracks={}
        length=0
        for channel in anim.get("channels",[]):
            if channel["target"]["path"]!="rotation":
                continue
            sampler=anim["samplers"][channel["sampler"]]
            times=[row[0] for row in m.float_accessor(doc,binary,sampler["input"])]
            rots=m.float_accessor(doc,binary,sampler["output"])
            method=sampler.get("interpolation","LINEAR")
            if method=="CUBICSPLINE":
                rots=rots[1::3]
            elif method not in ("LINEAR","STEP"):
                raise ValueError("Unexpected interpolation method")
            if not times or len(times)!=len(rots):
                raise ValueError("Bad animation rotation sampler")
            length=max(length,times[-1])
            tracks[channel["target"]["node"]]=(times,[m.normq(q) for q in rots],
                                               "LINEAR" if method=="CUBICSPLINE" else method)
        if tracks:
            candidates.append((len(tracks),length,tracks,m))
    if not candidates:
        raise ValueError("FBX converted GLB has no keyed rotations")
    candidates.sort(key=lambda x:(x[0],x[1]),reverse=True)
    _,duration,tracks,m=candidates[0]
    if not .2<duration<12:
        raise ValueError("Motion duration implausible")
    return tracks,duration,m

def transfer_clips(target,buf,source_directory):
    from importlib import util
    spec=util.spec_from_file_location("wc_skeleton",ROOT/"scripts/inspect-rig-skeletons.py")
    sk=util.module_from_spec(spec)
    spec.loader.exec_module(sk)
    target_joints=sk.joint_table(target)
    if len(target_joints)!=52:
        raise ValueError("Unexpected approved target skeleton")
    tp=sk.parent_map(target)
    tn=target["nodes"]
    Q=(0.,0.,0.,1.)
    required=["hips","leftupleg","rightupleg","leftleg","rightleg",
              "leftarm","rightarm","leftforearm","rightforearm"]
    if any(k not in target_joints for k in required):
        raise ValueError("Target legs or arms missing")
    clips=[
      ("Idle","2hand_Idle"),
      ("Walk","Walking_21"),
      ("Run","Run_With_Sword"),
      ("Attack","Standing_Melee_Attack_Downward")
    ]
    target["animations"]=[]
    reports=[]
    for name,stem in clips:
        src=source_directory/(stem+".glb")
        source,raw=load_glb(src)
        tracks,duration,m=mixamo_animation(source,raw)
        sn=source["nodes"]
        source_joints={sk.simplify(n.get("name","")):i for i,n in enumerate(sn)
                       if n.get("name")}
        common={ti:source_joints[key] for key,ti in target_joints.items()
                if key in source_joints}
        if len(common)<37:
            raise ValueError(stem+" has fewer than 37 mapped Mixamo bones: "+str(len(common)))
        sp=sk.parent_map(source)
        sr=[m.normq(node.get("rotation",Q)) for node in sn]
        tr=[m.normq(node.get("rotation",Q)) for node in tn]
        srw=m.world_orientations(sn,sp,sr)
        trw=m.world_orientations(tn,tp,tr)
        frames=max(8,int(round(duration*30))+1)
        times=[duration*i/(frames-1) for i in range(frames)]
        samples={i:[] for i in common}
        for t in times:
            slocal=[m.interpolate(tracks[i],t) if i in tracks else q
                    for i,q in enumerate(sr)]
            sworld=m.world_orientations(sn,sp,slocal)
            cache={}
            def solve(i):
                if i in cache:return cache[i]
                pw=solve(tp[i]) if i in tp else Q
                if i in common:
                    si=common[i]
                    delta=m.qmul(sworld[si],m.qinv(srw[si]))
                    desired=m.qmul(delta,trw[i])
                    local=m.qmul(m.qinv(pw),desired)
                else:
                    local=tr[i]
                result=m.qmul(pw,local)
                cache[i]=result
                if i in samples:
                    samples[i].append(local)
                return result
            for i in range(len(tn)):
                solve(i)
        when=add_accessor(target,buf,[(t,) for t in times],"SCALAR",bounds=True)
        samplers=[]
        channels=[]
        angles=[]
        for bone,poses in sorted(samples.items()):
            if len(poses)!=frames:
                raise ValueError("Frame channel count mismatch")
            item=add_accessor(target,buf,poses,"VEC4")
            idx=len(samplers)
            samplers.append({"input":when,"output":item,"interpolation":"LINEAR"})
            channels.append({"sampler":idx,"target":{"node":bone,"path":"rotation"}})
            first=poses[0]
            angles.append(max(2*math.degrees(math.acos(min(1,abs(sum(x*y for x,y in zip(first,v))))))
                              for v in poses))
        if max(angles)<5:
            raise ValueError(stem+" produces no meaningful skeletal movement")
        upper_arms={}
        for shoulder in ("leftarm","rightarm"):
            idx=target_joints[shoulder]
            q0=samples[idx][0]
            qrest=tr[idx]
            dot=min(1,abs(sum(x*y for x,y in zip(q0,qrest))))
            upper_arms[shoulder]=round(2*math.degrees(math.acos(dot)),2)
        # Reject candidate walks that leave either arm in its original T-pose.
        if name in ("Idle","Walk","Run") and min(upper_arms.values())<13:
            raise ValueError(stem+" still has T-pose upper arm at frame 0: "+str(upper_arms))
        target["animations"].append({"name":name+"_Mixamo_WithAxe",
           "samplers":samplers,"channels":channels,
           "extras":{"source":"Mixamo archived FBX, with axe",
                     "file":stem+".fbx",
                     "retargeting":"rest-world delta to 52-joint WarConquer rig; root travel excluded"}})
        reports.append({"name":name,"fbx":stem+".fbx","source_glb_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
                        "duration":round(duration,3),"frames":frames,
                        "mapped_joints":len(common),"rotation_channels":len(channels),
                        "largest_rotation_degrees":round(max(angles),2),
                        "initial_upper_arm_offset_degrees":upper_arms})
    return reports

def main():
    import os
    folder=os.environ.get("MIXAMO_CONVERTED_DIR")
    if not folder:
        raise ValueError("Set MIXAMO_CONVERTED_DIR to offline FBX2glTF-converted clips")
    doc,buf=load_glb(SRC)
    saved=copy.deepcopy(doc.get("skins"))
    if len(saved or [])!=1 or len(saved[0].get("joints",[]))!=52:
        raise ValueError("Character is not the approved 52 joint rig")
    tex=atlas_and_uv(doc,buf)
    clips=transfer_clips(doc,buf,Path(folder))
    if doc.get("skins")!=saved:
        raise ValueError("Skin joint or inverse bind matrix changed")
    write_glb(doc,buf,OUT)
    result,_=load_glb(OUT)
    assert len(result.get("animations",[]))==4
    assert len(result.get("images",[]))>=1
    assert result.get("skins")==saved
    report={"status":"converted-awaiting-visual-QA",
            "source_mesh_and_rig":str(SRC.relative_to(ROOT)),
            "output":str(OUT.relative_to(ROOT)),
            "output_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
            "rig_joint_count":52,
            "motion_origin":"real archived Adobe Mixamo FBX, not procedural or AI-generated",
            "motion_conversion":"FBX2glTF binary FBX to GLB + world-rest-rotation retarget; local WASD handles translation",
            "animation_clips":clips,
            "texture_origin":"4 approved source images, orthographic UV projection, glTF upper-left UV convention",
            "texture_QA":"not artist-approved; may have seams/misalignment",
            "physical_weapon_attached":False,**tex}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
