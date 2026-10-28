#!/usr/bin/env python3
"""Offline geometry/vision-projection regression, with no model or API calls."""
import importlib.util
from pathlib import Path
import numpy as np

script = Path(__file__).with_name("prop-mesh-landmarks.py")
spec = importlib.util.spec_from_file_location("wc_prop_mesh_landmarks", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_real_glb_projection():
    source = module.ROOT / "assets/experiments/props/marches_hache/trellis-v1/axe.glb"
    parts = module.glb_geometry(source)
    assert parts and sum(len(m["local"]) for m in parts)>100
    preview, views = module.make_views(parts)
    assert preview[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(views)==4
    assert len({tuple(np.round(v["camera"], 3)) for v in views})==4


def test_lift_keeps_signed_functional_edge():
    # A generic asymmetric prop with a handle on X and a working edge on Z.
    # The edge intentionally points in the OPPOSITE direction from the other
    # side; the rig solver must preserve that sign rather than relying on PCA.
    grip = np.array([0.0, 0.0, 0.0]); head=np.array([1.0, 0.0, 0.0])
    butt=np.array([-1.0, 0.0, 0.0]); edge=np.array([1.0, 0.0, -0.38])
    points=np.array([butt,grip,head,edge]+[
        [x,y,z] for x in np.linspace(-1,1,25)
        for y in (-.035,.035) for z in (-.025,.025)],dtype=float)
    meshes=[{"local":points,"world":points,"mesh":0,"primitive":0,
        "faces":np.array([[0,1,2],[1,2,3]],dtype=int)}]
    _,views=module.make_views(meshes)
    view=next(i for i,v in enumerate(views)
        if abs(np.dot(v["camera"],np.array([0,1,0])))>.9)
    meta=views[view]
    def coords(point):
        delta=point-meta["center"]
        return [(0.5+float(delta@meta["right"])*meta["scale"]/module.VIEW_SIZE),
                (0.5-float(delta@meta["up"])*meta["scale"]/module.VIEW_SIZE)]
    answer={"view":view,"handle_butt":coords(butt),"grip_center":coords(grip),
            "working_head":coords(head),"functional_edge":coords(edge),
            "confidence":.99,"explanation":"sharp edge is on the negative Z side"}
    result=module.lift_landmarks(meshes,views,answer)
    assert np.allclose(result["functional_edge"]["local"],edge)
    assert np.allclose(result["grip_center"]["local"],grip)
    mirrored=dict(answer)
    other=np.array([1.0,0.0,.38])
    # The other side is actually distinct in the mesh, not an invented point.
    meshes[0]["local"]=np.vstack([points,other])
    meshes[0]["world"]=meshes[0]["local"]
    mirrored["functional_edge"]=coords(other)
    result_other=module.lift_landmarks(meshes,views,mirrored)
    assert result_other["functional_edge"]["local"][2] > 0


if __name__=="__main__":
    test_real_glb_projection()
    test_lift_keeps_signed_functional_edge()
    print("PASS: real GLB orthographic views and signed 3D vision landmarks")
