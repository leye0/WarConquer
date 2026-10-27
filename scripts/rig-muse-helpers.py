#!/usr/bin/env python3
"""Shared OpenRouter Muse still-image primitives for 3D rig source T-poses."""
import base64
import io
import json
import os
import urllib.error
import urllib.request
import numpy as np
from PIL import Image
from scipy.ndimage import binary_closing,binary_fill_holes,gaussian_filter,label
TILE_SIZE=1024

def reference_payload(raw):
    return [{"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(raw).decode("ascii")}}]

def call_muse(prompt, refs, model):
    payload={"model":model,"prompt":prompt,"input_references":refs,
             "n":1,"output_format":"png","background":"transparent","aspect_ratio":"1:1"}
    req=urllib.request.Request(
        "https://openrouter.ai/api/v1/images",data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req,timeout=300) as response: result=json.load(response)
    except urllib.error.HTTPError as exc:
        reason=""
        try:
            error=json.loads(exc.read(4096))
            reason=str(error.get("error",{}).get("message",""))[:250]
        except (ValueError,AttributeError,TypeError): pass
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {reason}; no retry") from None
    img_bytes=base64.b64decode(result["data"][0]["b64_json"],validate=True)
    image=Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    return image,img_bytes,result.get("usage",{})

def extract_alpha(image):
    rgb=np.asarray(image.convert("RGB"),dtype=np.uint8)
    original_alpha=np.asarray(image.getchannel("A"))
    if original_alpha.min()!=255:
        return image,"native-alpha"
    corners=np.array([rgb[0,0],rgb[0,-1],rgb[-1,0],rgb[-1,-1]])
    if corners.max()<35:
        mask=rgb.max(axis=2)>23
        background="black"
    elif corners.min()>225:
        mask=rgb.min(axis=2)<236
        background="white"
    else:
        raise ValueError("Unsupported opaque Muse background; raw image preserved for review")
    mask=binary_fill_holes(binary_closing(mask,iterations=2))
    components,n=label(mask)
    if n:
        counts=np.bincount(components.ravel())
        significant=np.zeros(n+1,dtype=bool)
        significant[1:]=counts[1:]>=max(35,int(counts[1:].max()*.001))
        mask &= significant[components]
    a=(gaussian_filter(mask.astype(np.float32),.7)*255).clip(0,255).astype(np.uint8)
    data=np.dstack([rgb,a])
    if background=="black":
        denom=np.maximum(a.astype(np.float32)/255.,.33)
        data[:,:,:3]=np.minimum(255,rgb.astype(np.float32)/denom[:,:,None]).astype(np.uint8)
    return Image.fromarray(data,"RGBA"),f"{background}-background-matte"

def place_character(image):
    alpha=image.getchannel("A")
    bbox=alpha.point(lambda a:255 if a>36 else 0).getbbox()
    if not bbox:raise ValueError("No opaque foreground")
    left,top,right,bottom=bbox
    source_edge_contact=min(left,top,image.width-right,image.height-bottom)<=3
    if source_edge_contact:
        # Preserve the raw file; don't claim a complete visible character.
        raise ValueError(f"Foreground clipped by Muse source image: {bbox}")
    foreground=sum(alpha.histogram()[48:])/(image.width*image.height)
    if foreground<.018 or foreground>.85:
        raise ValueError(f"Unlikely character coverage {foreground:.4f}")
    crop=image.crop(bbox)
    scale=min(.99,(TILE_SIZE*.65)/crop.width,(TILE_SIZE*.72)/crop.height)
    new_size=(max(1,round(crop.width*scale)),max(1,round(crop.height*scale)))
    resized=crop.resize(new_size,Image.Resampling.LANCZOS)
    canvas=Image.new("RGBA",(TILE_SIZE,TILE_SIZE),(0,0,0,0))
    x=(TILE_SIZE-resized.width)//2
    y=TILE_SIZE-125-resized.height
    if x<25 or y<25:raise ValueError("Character does not fit canvas with margins")
    canvas.alpha_composite(resized,(x,y))
    return canvas,{"raw_bbox":list(bbox),"source_edge_contact":source_edge_contact,
                   "foreground_fraction":round(foreground,5),"normalization_scale":round(scale,5),
                   "feet_baseline_px":TILE_SIZE-125}

