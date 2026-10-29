#!/usr/bin/env python3
"""Offline regressions for Studio's labeled 0..1000 vision rectangle convention."""
import importlib.util
import io
import json
from pathlib import Path

from PIL import Image
import numpy as np

path=Path(__file__).with_name("audit-prop-vision-regions.py")
spec=importlib.util.spec_from_file_location("wc_studio_prop_bbox_audit",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

contract=json.loads((module.ROOT/
    "assets/experiments/props/marches_hache/trellis-v1/interaction-contract.json").read_text())
semantic=contract["characterization"]
roles=module.expected_labels(semantic)
assert set(roles)=={"handle_butt","grip_center","working_head",
    "functional_edge","grip_lower_haft","grip_upper_haft","axe_head"}
assert not any("point" in role or "origin" in role for role in roles)

answer={"objects":{label:{"visible":True,
    "box_2d":[120,200,180,265],"confidence":.94} for label in roles}}
parsed=module.parse_response("```json\n"+json.dumps(answer)+"\n```")
assert parsed==answer
boxes=module.validate_boxes(parsed,roles)
assert boxes["functional_edge"]["box_2d"]==[120,200,180,265]
assert module.native_box_order("google/gemini-2.5-flash")=="ymin_xmin_ymax_xmax"
assert module.native_box_order("qwen/qwen3-vl-235b-a22b-instruct")=="xmin_ymin_xmax_ymax"
gemini={"objects":{label:{"visible":True,"box_2d":[200,120,265,180],
    "confidence":.94} for label in roles}}
converted=module.validate_boxes(gemini,roles,module.native_box_order("google/gemini-2.5-flash"))
assert converted["functional_edge"]["box_2d"]==[120,200,180,265]
image=module.render_overlay(Image.new("RGB",(510,510),"white"),boxes,
    {"functional_edge":[150,230]})
assert Image.open(io.BytesIO(image)).size==(510,510)
focus=module.named_crops(Image.new("RGB",(510,510),"white"),roles,
    {name:[480,600] for name in roles})
assert all(Image.open(io.BytesIO(c["image"])).size==(720,720)
           for c in focus.values())
centered={name:{"visible":True,"box_2d":[400,400,600,600],"confidence":.9}
          for name in roles}
mapped=module.remap_crop_boxes(centered,focus,510)
assert all(x["box_2d"][0]<=480<=x["box_2d"][2]
    and x["box_2d"][1]<=600<=x["box_2d"][3] for x in mapped.values())

wrong=json.loads(json.dumps(answer));wrong["objects"]["axe_head"]["box_2d"]=[10,20,30]
try:module.validate_boxes(wrong,roles)
except ValueError as error:assert "box_2d" in str(error)
else:raise AssertionError("Accepted missing 4-point physical region")

wrong=json.loads(json.dumps(answer));wrong["objects"]["fictional_grip"]={"visible":True,
    "box_2d":[20,40,50,70],"confidence":.95}
try:module.validate_boxes(wrong,roles)
except ValueError as error:assert "invented" in str(error)
else:raise AssertionError("Invented semantic grip not blocked")

print("PASS: Studio 0..1000 labeled bboxes, exact IDs and visible review overlays")

# Real textured axe regression: the two independent vision passes disagreed
# about its physical BOTTOM and cutting EDGE. A disputed labeled rectangle
# cannot repair an anchor until its true triangle surface is demonstrated.
meshes=module.mesh_vision.glb_geometry(module.ROOT/
    "assets/experiments/props/marches_hache/trellis-v1/axe.glb")
_,views=module.mesh_vision.make_views(meshes)
real_points={
    "handle_butt": [0.3384636,-0.3916808,0.0331001],
    "grip_center": [0.128259,-0.1000625,-0.0007449],
    "working_head": [-0.1801326,0.3306219,0.0006004],
    "functional_edge": [-0.3051306,0.2297242,-0.0176757]}
annotated={key:{"local":value,"mesh":0,"primitive":0}
           for key,value in real_points.items()}
real_plan={"mesh_landmarks":{"points":annotated,
    "grips":{},"features":{"axe_head":{"origin":annotated["working_head"].copy(),
        "direction_tip":annotated["functional_edge"].copy()}}}}
native_regions={name:{"visible":True,"box_2d":list(box),"confidence":.9}
    for name,box in {
        "handle_butt":(443.1,925.9,500.3,945.6),
        "working_head":(374.2,206.7,608.9,450.2),
        "functional_edge":(272.2,360.8,343.1,456.1)}.items()}
# The real GLB renderer must expose its exact object-pixel depth mask,
# independently of grid, labels, material colors and the source illustration.
mask=views[2]["surface_mask"]
assert mask.shape==(module.mesh_vision.VIEW_SIZE,)*2
assert mask.any() and not mask[0,0]
ys,xs=np.nonzero(mask)
sample=len(xs)//2
x,y=int(xs[sample]),int(ys[sample])
scale=1000/module.mesh_vision.VIEW_SIZE
visible_box={"surface":{"visible":True,
    "box_2d":[x*scale,y*scale,(x+1)*scale,(y+1)*scale],
    "confidence":.99}}
assert not module.visible_glb_region_issues(visible_box,views[2])
empty_box={"empty":{"visible":True,"box_2d":[0,0,20,20],"confidence":.99}}
issues=module.visible_glb_region_issues(empty_box,views[2])
assert len(issues)==1 and "no visible GLB surface pixels" in issues[0],issues
try:module.visible_glb_region_issues(empty_box,{"surface_mask":None})
except ValueError as error:assert "mask is missing" in str(error)
else:raise AssertionError("Accepted missing depth/visibility evidence")

# Historic bbox-center/nearest-vertex snap is precisely the unsafe shortcut
# the B5 triangle patch contract forbids. Preserve rejected points and labels.
before=json.dumps(real_plan,sort_keys=True)
try:module.reconcile_physical_regions(real_plan,meshes,views[2],native_regions)
except ValueError as error:assert "disabled" in str(error)
else:raise AssertionError("Silently repaired a semantic region by vertex snapping")
assert json.dumps(real_plan,sort_keys=True)==before
_,issues=module.qa_points(real_plan,meshes,views[2],native_regions)
assert any("handle_butt" in issue for issue in issues),issues
assert any("functional_edge" in issue for issue in issues),issues
assert (real_plan["mesh_landmarks"]["features"]["axe_head"]["direction_tip"]==
    real_plan["mesh_landmarks"]["points"]["functional_edge"])
print("PASS: real GLB pixels gate 2D regions and legacy anchors are never auto-repaired")

# Schema 2: all named parts in every full view, no historic anchor/crop input.
import copy
import tempfile
labels=module.region_labels(semantic)
assert set(labels)=={'grip_lower_haft','grip_upper_haft','axe_head'}
assert 'point' not in json.dumps(labels)
prompt=module.region_prompt(labels,'xmin_ymin_xmax_ymax')
assert 'entire shared shaft' in prompt and 'origin may be outside' in prompt
synthetic_views=[{'surface_mask':np.ones((510,510),dtype=bool)} for _ in range(4)]
proposal={'views':[{'view':i,'objects':{name:{'visible':True,
    'box_2d':[100,100,300,300],'confidence':.95,
    'evidence':'Distinct visible physical surface',
    **({'origin':[80,200],'direction_tip':[200,200]} if item['role']=='functional_region' else {})}
    for name,item in labels.items()}} for i in range(4)]}
records=module.validate_multiview(proposal,labels,synthetic_views,'xmin_ymin_xmax_ymax')
assert not any(r['issues'] for r in records) # Origin outside effect region is legitimate.
assert module.validate_multiview(proposal['views'],labels,synthetic_views,
    'xmin_ymin_xmax_ymax')==records # Provider may omit the outer envelope only.
review={'views':[{'view':i,'objects':{name:{'verdict':'confirmed',
    'reason':'Visible identity and signed direction agree'} for name in labels}} for i in range(4)],
    'cross_view':{name:{'verdict':'confirmed','reason':'Same region visible from distinct cameras',
    'additional_views':[]} for name in labels}}
coverage,issues=module.reviewed_regions(records,review,labels)
assert not issues and all(len(v)==4 for v in coverage.values())

for broken in ('duplicate_view','missing_id','bad_point','missing_evidence'):
    bad=copy.deepcopy(proposal)
    if broken=='duplicate_view':bad['views'][3]['view']=0
    if broken=='missing_id':del bad['views'][2]['objects']['grip_upper_haft']
    if broken=='bad_point':bad['views'][0]['objects']['axe_head']['origin']=[True,200]
    if broken=='missing_evidence':bad['views'][0]['objects']['axe_head']['evidence']=''
    try: module.validate_multiview(bad,labels,synthetic_views,'xmin_ymin_xmax_ymax')
    except ValueError:pass
    else:raise AssertionError('Accepted '+broken)

bad_views=copy.deepcopy(synthetic_views)
bad_views[0]['surface_mask'][:]=False
bad_records=module.validate_multiview(proposal,labels,bad_views,'xmin_ymin_xmax_ymax')
_,issues=module.reviewed_regions(bad_records,review,labels)
assert any('on background' in x for x in issues)
assert any('no visible GLB surface' in x for x in issues)

hidden=copy.deepcopy(proposal)
for row in hidden['views'][1:]:
    row['objects']['grip_upper_haft']={'visible':False,'confidence':0,
        'evidence':'Occluded: another camera is necessary'}
hidden_records=module.validate_multiview(hidden,labels,synthetic_views,'xmin_ymin_xmax_ymax')
_,issues=module.reviewed_regions(hidden_records,review,labels)
assert any('fewer than two' in x for x in issues) # Optimistic reviewer cannot override missing pixels.
conflict=copy.deepcopy(review)
conflict['cross_view']['grip_upper_haft'].update(verdict='rejected',reason='IDs swapped between opposite views')
_,issues=module.reviewed_regions(records,conflict,labels)
assert any('swapped' in x for x in issues)
conflict=copy.deepcopy(review)
conflict['views'][1]['objects']['axe_head']['verdict']='rejected'
assert module.reviewed_regions(records,conflict,labels)[1] # Two good views cannot erase a rejected view.

# Malformed raw replies remain in immutable receipts and are never paid twice.
with tempfile.TemporaryDirectory() as tmp:
    folder=Path(tmp);calls=[]
    class Reply:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return json.dumps({'choices':[{'message':{'content':'not JSON'}}],
                                          'usage':{'cost':.001}}).encode()
    original_urlopen=module.urlopen
    original_key=module.os.environ.get('OPENROUTER_API_KEY')
    module.os.environ['OPENROUTER_API_KEY']='test-placeholder'
    module.urlopen=lambda *args,**kwargs:(calls.append(1) or Reply())
    try:
        for _ in range(2):
            try: module.region_request(folder,'annotation','test','prompt',[],{},True)
            except ValueError:pass
            else:raise AssertionError('Accepted malformed paid reply')
        assert len(calls)==1
        receipt=json.loads(next(folder.glob('*.json')).read_text())
        assert receipt['response']['choices'][0]['message']['content']=='not JSON'
        assert receipt['usage']['cost']==.001
    finally:
        module.urlopen=original_urlopen
        if original_key is None:module.os.environ.pop('OPENROUTER_API_KEY',None)
        else:module.os.environ['OPENROUTER_API_KEY']=original_key
print('PASS: multi-view IDs, visibility, signed directions, independent conflicts and immutable raw receipts')

# Independent requests prevent answer leakage between opposite camera views.
from unittest.mock import patch
requests=[]
def fake_region_request(folder, stage, model, prompt, images, provenance, allow_paid):
    requests.append((stage,images))
    return {'objects':proposal['views'][len(requests)-1]['objects']},stage+'.json'
images=[('VIEW '+str(i),bytes([i])) for i in range(4)]
with patch.object(module,'region_request',side_effect=fake_region_request):
    per_view,receipts=module.annotate_individual_views(Path('/tmp'), 'test', labels,
        'xmin_ymin_xmax_ymax',images,{},False)
assert [r['view'] for r in per_view['views']]==[0,1,2,3]
assert all(requests[i][1]==[images[i]] for i in range(4))
assert len(set(receipts))==4
print('PASS: each annotator receives exactly one camera image and no other view response')

requests.clear()
def unwrapped_request(folder, stage, model, prompt, images, provenance, allow_paid):
    wrapped, receipt=fake_region_request(folder,stage,model,prompt,images,provenance,allow_paid)
    return wrapped['objects'],receipt
with patch.object(module,'region_request',side_effect=unwrapped_request):
    unwrapped,_=module.annotate_individual_views(Path('/tmp'),'test',labels,
        'xmin_ymin_xmax_ymax',images,{},False)
assert unwrapped==per_view
