#!/usr/bin/env python3
"""Compose a UV-textured playable GLB with deterministic in-place gait trials.

Source is the already-rigged, already-animated Hunyuan/Uthana character.
No inference or paid calls; original skin joints, bind matrices and axe clip
are retained. A simple orthographic 4-view texture projection is an experiment,
not AI mesh painting; Walk/Run/Idle are procedural reference motions, not Mixamo.
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
OUT=BASE/"motion/playable-v1/warconquer-playable.glb"
REPORT=BASE/"motion/playable-v1/report.json"
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
                       1-(py+(quadrant//2)*1024)/2048))
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

def motions(doc,buf):
    names={n.get("name","").replace("mixamorig:",""):i for i,n in enumerate(doc["nodes"])}
    mapping={}
    for label in ("Hips","Spine","Spine1","Spine2",
                  "LeftUpLeg","RightUpLeg","LeftLeg","RightLeg",
                  "LeftFoot","RightFoot","LeftArm","RightArm",
                  "LeftForeArm","RightForeArm"):
        if label not in names:
            raise ValueError("Rig missing "+label)
        mapping[label]=names[label]
    parent={}
    for i,node in enumerate(doc["nodes"]):
        for c in node.get("children",[]):
            parent[c]=i
    def local(i):
        return qnorm(doc["nodes"][i].get("rotation",Q))
    cache={}
    def rest(i):
        if i not in cache:
            cache[i]=qmul(rest(parent[i]),local(i)) if i in parent else local(i)
        return cache[i]
    def desired(label,phase,kind):
        s=math.sin(phase)
        left=s;right=-s
        if kind=="Idle":
            breathing=1.5*math.sin(phase)
            if label in ("LeftArm","RightArm"):
                return qaxis((0,0,1),70 if label=="LeftArm" else -70)
            if label=="Spine2":
                return qaxis((1,0,0),breathing)
            return Q
        scale=1 if kind=="Walk" else 1.6
        hip=27 if kind=="Walk" else 40
        arm=19 if kind=="Walk" else 32
        bend=30 if kind=="Walk" else 52
        if label.endswith("UpLeg"):
            sign=left if label.startswith("Left") else right
            return qaxis((1,0,0),hip*scale/1.6*sign)
        if label.endswith("Leg"):
            sign=left if label.startswith("Left") else right
            a=hip*scale/1.6*sign+max(0,sign)*bend
            return qaxis((1,0,0),a)
        if label.endswith("Foot"):
            sign=left if label.startswith("Left") else right
            return qaxis((1,0,0),-12*sign)
        if label.endswith("Arm"):
            sign=left if label.startswith("Left") else right
            return qmul(qaxis((0,0,1),70 if label.startswith("Left") else -70),
                        qaxis((1,0,0),-arm*sign))
        if label.endswith("ForeArm"):
            sign=left if label.startswith("Left") else right
            return qaxis((1,0,0),10+6*sign)
        if label=="Hips":
            return qaxis((0,0,1),3.0*math.sin(phase))
        if label.startswith("Spine"):
            return qaxis((0,0,1),-2.5*math.sin(phase))
        return Q

    for kind,secs in (("Idle",2.0),("Walk",1.08),("Run",0.70)):
        frames=49 if kind=="Idle" else (33 if kind=="Walk" else 29)
        times=[round(secs*i/(frames-1),6) for i in range(frames)]
        when=add_accessor(doc,buf,[(v,) for v in times],"SCALAR",bounds=True)
        tracks={i:[] for i in mapping.values()}
        for frame in range(frames):
            phase=2*math.pi*frame/(frames-1)
            target={idx:desired(name,phase,kind) for name,idx in mapping.items()}
            current_world={}
            def w(i):
                if i in current_world:
                    return current_world[i]
                pw=w(parent[i]) if i in parent else Q
                if i in target:
                    expected=qmul(target[i],rest(i))
                    actual=qmul(qinv(pw),expected)
                    tracks[i].append(actual)
                    current_world[i]=expected
                else:
                    current_world[i]=qmul(pw,local(i))
                return current_world[i]
            for idx in mapping.values():
                w(idx)
        samplers=[];channels=[]
        for idx,rotations in tracks.items():
            if len(rotations)!=frames:
                raise ValueError("Gait channel lost frames")
            out=add_accessor(doc,buf,rotations,"VEC4")
            sample=len(samplers)
            samplers.append({"input":when,"output":out,"interpolation":"LINEAR"})
            channels.append({"sampler":sample,"target":{"node":idx,"path":"rotation"}})
        doc.setdefault("animations",[]).append({
            "name":kind+"_procedural_preview_v1",
            "samplers":samplers,"channels":channels,
            "extras":{"origin":"local parametric in-place gait, not a downloaded Mixamo clip",
                      "status":"prototype - visual quality not certified"}})
    return [a["name"] for a in doc["animations"]]

def main():
    doc,buf=load_glb(SRC)
    original_skin=copy.deepcopy(doc.get("skins"))
    original_count=len(doc.get("animations",[]))
    if len(original_skin or [])!=1 or len(original_skin[0].get("joints",[]))!=52 or original_count!=1:
        raise ValueError("Input differs from approved 52-joint one-attack rig")
    texture=atlas_and_uv(doc,buf)
    animations=motions(doc,buf)
    if doc.get("skins")!=original_skin or len(animations)!=4:
        raise ValueError("Skin or animation invariant broken")
    write_glb(doc,buf,OUT)
    check,_=load_glb(OUT)
    assert len(check["skins"][0]["joints"])==52
    assert len(check["animations"])==4
    assert "TEXCOORD_0" in check["meshes"][0]["primitives"][0]["attributes"]
    assert len(check["images"])>=1
    report={"status":"generated-awaiting-visual-QA",
            "source":str(SRC.relative_to(ROOT)),
            "output":str(OUT.relative_to(ROOT)),
            "source_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
            "output_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
            "texture_method":"orthographic face-normal projection from four existing 1024 RGBA images",
            "texture_quality":"experimental; UV seams, texture alignment and fingers require visual review",
            "motion_source":"deterministic procedural prototypes, NOT Mixamo or mocap",
            "animation_names":animations,"rig_joints":52,
            "axe_attack_preserved":True,"actual_weapon_attached":False,
            **texture}
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
