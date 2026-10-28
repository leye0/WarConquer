#!/usr/bin/env python3
"""Offline geometry/vision-projection regression, with no model or API calls."""
import importlib.util
import copy
import io
from pathlib import Path
import numpy as np
from PIL import Image

script = Path(__file__).with_name("prop-mesh-landmarks.py")
spec = importlib.util.spec_from_file_location("wc_prop_mesh_landmarks", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_real_glb_projection():
    source = module.ROOT / "assets/experiments/props/marches_hache/trellis-v1/axe.glb"
    parts = module.glb_geometry(source)
    assert parts and sum(len(m["local"]) for m in parts)>100
    assert any(m.get("texture") is not None and m.get("uv") is not None for m in parts), (
        "The real GLB has an embedded material; vision MUST see its actual texture")
    preview, views = module.make_views(parts)
    assert preview[:8] == b"\x89PNG\r\n\x1a\n"
    pixels=np.asarray(Image.open(io.BytesIO(preview)).convert("RGB"))
    colors=pixels[520:1000,520:1000].reshape(-1,3)
    distinct=np.unique(colors[~np.all(colors==[250,250,249],axis=1)],axis=0)
    assert len(distinct)>50, "Texture-based material identities disappeared from GLB views"
    assert len(views)==4
    assert len({tuple(np.round(v["camera"], 3)) for v in views})==4
    # An inaccurate vision answer must be rejected. Geometry may never
    # silently invent a head/edge from the shaft's longest direction.
    recorded={"view":3,"handle_butt":[.5,.95],"grip_center":[.5,.65],
        "working_head":[.75,.35],"functional_edge":[.85,.35],
        "confidence":.9,"explanation":"The sharp side faces right in view 3"}
    try:
        module.lift_landmarks(parts,views,recorded)
    except ValueError as err:
        assert "re-annotate" in str(err),str(err)
    else:
        raise AssertionError("Invented a functional landmark from an off-mesh vision point")
    collapsed=dict(recorded,functional_edge=recorded["working_head"])
    try:module.validate_answer(collapsed)
    except ValueError as error:assert "collapse" in str(error)
    else:raise AssertionError("Vision returned the same point for metal head and sharp edge")


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
    assert all(point["method"]=="vision-nearest-surface" for point in result.values())
    mirrored=dict(answer)
    other=np.array([1.0,0.0,.38])
    # The other side is actually distinct in the mesh, not an invented point.
    meshes[0]["local"]=np.vstack([points,other])
    meshes[0]["world"]=meshes[0]["local"]
    mirrored["functional_edge"]=coords(other)
    result_other=module.lift_landmarks(meshes,views,mirrored)
    assert result_other["functional_edge"]["local"][2] > 0

    # The prior vision model labels every strategic grip and its action
    # direction. The 3D model must locate THOSE IDs in its actual GLB views.
    semantic={"grips":[{"id":"lower_handle"},{"id":"upper_handle"}],
        "features":[{"id":"cutting_edge"}]}
    def region(*coords_list):
        return [max(0,min(p[0] for p in coords_list)-.1),
                max(0,min(p[1] for p in coords_list)-.1),
                min(1,max(p[0] for p in coords_list)+.1),
                min(1,max(p[1] for p in coords_list)+.1)]
    annotated={**answer,"grips":[
        {"id":"lower_handle","view":view,"point":coords(grip),
         "region":region(coords(grip)),"evidence":"Visible lower shaft contact region"},
        {"id":"upper_handle","view":view,"point":coords(np.array([.25,.035,.025])),
         "region":region(coords(np.array([.25,.035,.025]))),
         "evidence":"Visible distinct upper shaft grip"}],
        "features":[{"id":"cutting_edge","view":view,
            "origin":coords(head),"direction_tip":coords(edge),
            "region":region(coords(head),coords(edge)),
            "evidence":"Visible sharp side of working head"}]}
    expected=module.named_schema(semantic)
    assert set(expected["properties"]) == set(annotated)
    lifted=module.lift_named_landmarks(meshes,views,annotated,semantic)
    assert set(lifted["grips"])=={"lower_handle","upper_handle"}
    assert set(lifted["features"])=={"cutting_edge"}
    assert lifted["grips"]["lower_handle"]["method"]=="vision-nearest-surface"
    assert np.allclose(lifted["features"]["cutting_edge"]["direction_tip"]["local"],edge)
    assert not np.allclose(lifted["grips"]["upper_handle"]["local"],
                            lifted["grips"]["lower_handle"]["local"])

    def refuses(changed,expected_fragment):
        try:module.lift_named_landmarks(meshes,views,changed,semantic)
        except ValueError as error:assert expected_fragment in str(error),error
        else:raise AssertionError("Invented missing/uncertain 3D role landmarks")
    bad=copy.deepcopy(annotated);bad["grips"].pop()
    refuses(bad,"omit")
    bad=copy.deepcopy(annotated);bad["grips"][1]["id"]="imaginary_handle"
    refuses(bad,"invent")
    bad=copy.deepcopy(annotated);bad["features"][0]["direction_tip"]=coords(head)
    refuses(bad,"collapses")
    bad=copy.deepcopy(annotated);bad["grips"][1]["point"]=[.98,.98]
    refuses(bad,"outside its named region")
    bad=copy.deepcopy(annotated);bad["grips"][0]["region"]=[.1,.1,.1,.1]
    refuses(bad,"did not bound actual region")


if __name__=="__main__":
    test_real_glb_projection()
    test_lift_keeps_signed_functional_edge()
    print("PASS: signed real-GLB landmarks and every vision-confirmed hand/action role")
