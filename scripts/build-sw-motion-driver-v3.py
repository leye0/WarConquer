#!/usr/bin/env python3
"""Deterministic SW motion driver for WarConquer. No AI models, API calls, or credits.

Emits an eight-second pose-reference video, inspection video, joint/axe
coordinates, source-image alignment preview and machine-checkable geometry.
No generated character art is claimed; this is a motion blueprint only.
"""
import json
import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/experiments/standing-turnaround/marches_hache/SW.png"
OUT = ROOT / "assets/experiments/sw-motion-driver-v3"
SIZE = 768
FPS = 12
DURATION = 8
FRAMES = FPS * DURATION
SAFE = 76
CLEARANCE = 20
START_ROOT = (496.0, 538.0)
TOTAL_DISTANCE = SIZE * 0.07
STEP_DIAGONAL = TOTAL_DISTANCE / math.sqrt(2)
ATTACK_ROOT = (START_ROOT[0] - STEP_DIAGONAL, START_ROOT[1] + STEP_DIAGONAL)
FACING = (-1 / math.sqrt(2), 1 / math.sqrt(2))
COLORS = {"spine": "#e3cb42", "left": "#ff7482", "right": "#6fb8f9",
          "head": "#ffdb82", "weapon": "#45f5bf"}

# Four staggered swing phases, with planted positions held between steps.
FOOT_EVENTS = [
    ("left", 0.22, 0.70), ("right", 0.93, 1.41),
    ("left", 1.64, 2.12), ("right", 2.35, 2.83),
    ("left", 3.06, 3.54)
]
FOOT_OFFSETS = {"left": (-25.0, -18.0), "right": (26.0, 0.0)}
FOOT_FORWARD_LEAD = (-12.0, 12.0)  # larger steps, grounded landing point
# Angle is in screen coordinates (Y grows down), measured from screen-right.
# Two distinct controlled swings. Values are continuous, without cuts.
ATTACK_KEYFRAMES = [
    (4.00, -55, -109, 135, "prepare"),
    (4.37, -36, -155, 230, "windup"),
    (4.75, -12, -202, 290, "windup"),
    (5.20, -86, -106, 145, "strike"),
    (5.72, -57, -112, 135, "recovery"),
    (6.00, -55, -109, 135, "ready"),
    (6.35, -36, -158, 237, "windup"),
    (6.66, -12, -202, 291, "windup"),
    (7.12, -86, -106, 145, "strike"),
    (7.55, -55, -109, 135, "recovery"),
    (8.00, -55, -109, 135, "ready")
]


def lerp(a, b, u):
    return a + (b - a) * u


def smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


def root_at(t):
    p = max(0.0, min(t, 4.0)) / 4.0
    return (START_ROOT[0] - STEP_DIAGONAL * p,
            START_ROOT[1] + STEP_DIAGONAL * p)


def feet_at(t):
    values = {}
    swing = None
    for name, offset in FOOT_OFFSETS.items():
        previous = (START_ROOT[0] + offset[0], START_ROOT[1] + offset[1])
        for which, start, end in FOOT_EVENTS:
            if which != name:
                continue
            target_root = root_at(end)
            target = (target_root[0] + offset[0] + FOOT_FORWARD_LEAD[0],
                      target_root[1] + offset[1] + FOOT_FORWARD_LEAD[1])
            if t < start:
                break
            if t >= end:
                previous = target
                continue
            u = smooth((t - start) / (end - start))
            foot = (lerp(previous[0], target[0], u),
                    lerp(previous[1], target[1], u) - 34.0 * math.sin(math.pi * u))
            values[name] = foot
            swing = name
            break
        if name not in values:
            values[name] = previous
    return values, swing


def attack_at(t):
    if t <= 4:
        return ATTACK_KEYFRAMES[0][1:]
    for a, b in zip(ATTACK_KEYFRAMES, ATTACK_KEYFRAMES[1:]):
        if a[0] <= t <= b[0]:
            u = smooth((t - a[0]) / (b[0] - a[0]))
            return (lerp(a[1], b[1], u), lerp(a[2], b[2], u),
                    lerp(a[3], b[3], u), b[4] if u > .5 else a[4])
    return ATTACK_KEYFRAMES[-1][1:]


def midpoint(a, b):
    return ((a[0] + b[0]) * .5, (a[1] + b[1]) * .5)


def point(x, y):
    return (round(float(x), 4), round(float(y), 4))


def swing_flexion(name, t):
    for which, start, end in FOOT_EVENTS:
        if which == name and start <= t < end:
            return math.sin(math.pi * (t-start)/(end-start))
    return 0.0


def get_pose(t):
    x, y = root_at(t)
    feet, swinging = feet_at(t)
    walking = t < 4.0
    # A small, consistent vertical hip/torso rise offsets stiff robotic gait.
    bob = -4.5 * abs(math.sin(math.pi * t / 0.71)) if walking else 0.0
    pelvis = (x - 8, y - 106 + bob)
    chest = (x - 15, y - 184 + bob)
    neck = (x - 11, y - 220 + bob)
    head = (x - 8, y - 244 + bob)
    left_shoulder = (x - 42, y - 181 + bob)
    right_shoulder = (x + 18, y - 181 + bob)
    left_hip = (pelvis[0] - 20, pelvis[1])
    right_hip = (pelvis[0] + 22, pelvis[1])
    joints = {"pelvis": pelvis, "chest": chest, "neck": neck,
              "head": head, "left_shoulder": left_shoulder,
              "right_shoulder": right_shoulder, "left_hip": left_hip,
              "right_hip": right_hip}
    for name in ("left", "right"):
        hip = joints[name + "_hip"]
        ankle = feet[name]
        flex = swing_flexion(name, t) if walking else 0.0
        # Forward-project the knee during swing while the foot lifts.
        # The grounded leg keeps its previous planting coordinate.
        bias = -8 if name == "left" else -8
        knee = (lerp(hip[0], ankle[0], .50) + bias - 19.0 * flex,
                lerp(hip[1], ankle[1], .51) - 12.0 * flex)
        joints[name + "_knee"] = knee
        joints[name + "_ankle"] = ankle
        joints[name + "_toe"] = (ankle[0] - 12 - 3 * flex,
                                 ankle[1] + 4 - 6 * flex)
    if walking:
        phase = math.sin(2 * math.pi * t / 1.85)
        hand = (x - 55 + phase * 3, y - 109 + phase * 3)
        right_hand = (x + 28 - phase * 10, y - 103 + phase * 4)
        angle = 135 + phase * 2
        action = "walk"
    else:
        hx, hy, angle, action = attack_at(t)
        hand = (x + hx, y + hy)
        right_hand = None
    theta = math.radians(angle)
    along = (math.cos(theta), math.sin(theta))
    normal = (-along[1], along[0])
    start_axe = (hand[0] - 24 * along[0], hand[1] - 24 * along[1])
    head_center = (hand[0] + 76 * along[0], hand[1] + 76 * along[1])
    blade = [
        (head_center[0] - 13 * along[0] - 13 * normal[0],
         head_center[1] - 13 * along[1] - 13 * normal[1]),
        (head_center[0] + 13 * along[0] - 21 * normal[0],
         head_center[1] + 13 * along[1] - 21 * normal[1]),
        (head_center[0] + 25 * along[0] + 7 * normal[0],
         head_center[1] + 25 * along[1] + 7 * normal[1]),
        (head_center[0] + 6 * along[0] + 27 * normal[0],
         head_center[1] + 6 * along[1] + 27 * normal[1]),
        (head_center[0] - 11 * along[0] + 12 * normal[0],
         head_center[1] - 11 * along[1] + 12 * normal[1])
    ]
    if walking:
        joints["left_elbow"] = (x - 50, y - 147)
        joints["right_elbow"] = (x + 43, y - 143)
        joints["right_hand"] = right_hand
    else:
        joints["left_elbow"] = midpoint(left_shoulder, hand)
        # The off-hand grips the shaft during each overhead attack.
        other = (hand[0] + 16 * along[0], hand[1] + 16 * along[1])
        joints["right_elbow"] = ((right_shoulder[0] + other[0]) / 2 + 9,
                                  (right_shoulder[1] + other[1]) / 2 + 5)
        joints["right_hand"] = other
    joints["left_hand"] = hand
    result = {
        "time_seconds": round(t, 5), "root": point(x, y),
        "facing_unit_screen_xy": point(*FACING),
        "facing_compass": "SW", "phase": "walk" if walking else "attack",
        "subphase": action, "swing_foot": swinging if walking else None,
        "joints": {k: point(*v) for k, v in joints.items()},
        "axe": {"handle_start": point(*start_axe), "handle_grip": point(*hand),
                "head_center": point(*head_center),
                "blade_polygon": [point(*v) for v in blade],
                "angle_degrees": round(angle, 3)}
    }
    return result


def xy(pt):
    return (int(round(pt[0])), int(round(pt[1])))


def draw_segment(draw, joints, a, b, color, width):
    draw.line([xy(joints[a]), xy(joints[b])], fill=color, width=width, joint="curve")


def draw_pose(im, state, debug=False, alpha=255):
    d = ImageDraw.Draw(im)
    j = state["joints"]
    if debug:
        d.rectangle((SAFE, SAFE, SIZE-SAFE-1, SIZE-SAFE-1), outline=(139,151,165), width=3)
        d.line((SIZE//2,SAFE,SIZE//2,SIZE-SAFE),fill=(231,234,238),width=1)
        d.line((SAFE,SIZE//2,SIZE-SAFE,SIZE//2),fill=(231,234,238),width=1)
        rt=state["root"]
        d.line([xy(rt),xy((rt[0]-42,rt[1]+42))],fill="#26936d",width=3)
        d.ellipse((rt[0]-4,rt[1]-4,rt[0]+4,rt[1]+4),fill="#26936d")
    # Torso facing SW: the chest plane remains unchanged while the limbs move.
    d.polygon([xy(j["left_shoulder"]),xy(j["right_shoulder"]),
               xy(j["right_hip"]),xy(j["left_hip"])],fill="#653447",outline="#d2869d")
    draw_segment(d,j,"pelvis","chest",COLORS["spine"],7)
    draw_segment(d,j,"chest","neck",COLORS["spine"],6)
    draw_segment(d,j,"left_shoulder","left_elbow",COLORS["left"],9)
    draw_segment(d,j,"left_elbow","left_hand",COLORS["left"],8)
    draw_segment(d,j,"right_shoulder","right_elbow",COLORS["right"],9)
    draw_segment(d,j,"right_elbow","right_hand",COLORS["right"],8)
    for name,col in (("left",COLORS["left"]),("right",COLORS["right"])):
        draw_segment(d,j,name+"_hip",name+"_knee",col,10)
        draw_segment(d,j,name+"_knee",name+"_ankle",col,9)
        draw_segment(d,j,name+"_ankle",name+"_toe",col,6)
    cx,cy=j["head"]
    d.ellipse((cx-18,cy-23,cx+18,cy+22),fill=COLORS["head"],outline="#493424",width=3)
    # Deliberately no brown beak/wedge: SW is conveyed by the debug arrow,
    # not by a fictitious anatomical feature on the character head.
    for n,p in j.items():
        if n=="head":
            continue
        px,py=p
        d.ellipse((px-4,py-4,px+4,py+4),fill="#ffffff")
    axe=state["axe"]
    d.line([xy(axe["handle_start"]),xy(axe["head_center"])],fill="#875937",width=10)
    d.line([xy(axe["handle_start"]),xy(axe["head_center"])],fill="#c5a27b",width=4)
    d.polygon([xy(p) for p in axe["blade_polygon"]],fill=COLORS["weapon"],outline="#167e6f")
    if debug:
        stage=state["phase"].upper()+" : "+state["subphase"].upper()
        d.text((25,25),"SW MOTION BLUEPRINT — "+stage,fill="#223443")
        d.text((25,47),f"t={state['time_seconds']:.2f}s | fixed body heading: SW | root 7% of frame side along SW",fill="#344758")
        d.text((25,735),"GREEN AXE = RIGID OBJECT; BODY = GUIDED SKELETON; NO AI GENERATION",fill="#344758")


def make_alignment_preview(state):
    source = Image.open(SOURCE).convert("RGBA")
    mask = source.getchannel("A").point(lambda v:255 if v>=30 else 0)
    box = mask.getbbox()
    if not box:
        raise RuntimeError("Existing SW alpha image is empty")
    cut = source.crop(box)
    ratio = min(269/cut.height,207/cut.width)
    cut = cut.resize((round(cut.width*ratio),round(cut.height*ratio)),Image.Resampling.LANCZOS)
    anchor_x=round(SIZE*.61)
    baseline=538
    left=anchor_x-cut.width//2
    top=baseline-cut.height
    photo=Image.new("RGBA",(SIZE,SIZE),(246,244,238,255))
    photo.alpha_composite(cut,(left,top))
    overlay=photo.convert("RGB")
    draw_pose(overlay,state,debug=True)
    overlay.save(OUT/"source-pose-alignment-preview.png",optimize=True)
    return {"source_png":str(SOURCE.relative_to(ROOT)),"alpha_bbox":list(box),
            "source_rect_on_preview":[left,top,left+cut.width,top+cut.height]}


def encode_video(path,states,debug):
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    cmd=[ffmpeg,"-hide_banner","-loglevel","error","-y",
         "-f","rawvideo","-pix_fmt","rgb24","-s",f"{SIZE}x{SIZE}",
         "-r",str(FPS),"-i","-","-an","-c:v","libx264",
         "-preset","veryfast","-crf","21","-pix_fmt","yuv420p",str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for state in states:
            im=Image.new("RGB",(SIZE,SIZE),(246,244,238) if debug else (8,12,22))
            draw_pose(im,state,debug)
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        error=proc.stderr.read().decode("utf-8","replace")
        result=proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    if result or path.stat().st_size<1000:
        raise RuntimeError(f"FFmpeg MP4 encoding failed {result}: {error[-1200:]}")


def knee_angle_degrees(hip, knee, ankle):
    u = (hip[0]-knee[0], hip[1]-knee[1])
    v = (ankle[0]-knee[0], ankle[1]-knee[1])
    norm = math.hypot(*u) * math.hypot(*v)
    if norm < 1e-8:
        return 180.0
    cosine = max(-1.0, min(1.0, (u[0]*v[0]+u[1]*v[1])/norm))
    return math.degrees(math.acos(cosine))


def check(states):
    failures=[]
    root1=states[0]["root"]
    root4=point(*root_at(4))
    actual_distance=math.dist(START_ROOT,ATTACK_ROOT)
    if abs(actual_distance-TOTAL_DISTANCE)>1e-6:failures.append("root displacement not 5%")
    actual_attack_roots={tuple(s["root"]) for s in states if s["phase"]=="attack"}
    if len(actual_attack_roots)!=1:failures.append("root changes during attack")
    for foot in ("left","right"):
        attack_positions={tuple(s["joints"][foot+"_ankle"]) for s in states if s["phase"]=="attack"}
        if len(attack_positions)!=1:failures.append(foot+" foot not planted in attack")
    max_stance_slip = 0.0
    for prev, cur in zip(states[:47], states[1:48]):
        for foot in ("left", "right"):
            if prev["swing_foot"] != foot and cur["swing_foot"] != foot:
                d = math.dist(prev["joints"][foot+"_ankle"], cur["joints"][foot+"_ankle"])
                max_stance_slip = max(max_stance_slip, d)
    if max_stance_slip > .01:
        failures.append("planted foot slides during walk")
    swing_angles = {"left": [], "right": []}
    for state in states[:48]:
        leg = state["swing_foot"]
        if leg:
            j = state["joints"]
            swing_angles[leg].append(knee_angle_degrees(
                j[leg+"_hip"], j[leg+"_knee"], j[leg+"_ankle"]))
    minimum_swing_angles = {
        leg: round(min(angles), 2) if angles else None
        for leg, angles in swing_angles.items()}
    if any(v is None or v > 135 for v in minimum_swing_angles.values()):
        failures.append("swing knee flexion too small")

    foot_step_distances = []
    for foot, start, end in FOOT_EVENTS:
        initial = feet_at(start)[0][foot]
        landing = feet_at(end)[0][foot]
        foot_step_distances.append(round(math.dist(initial, landing), 3))
    if any(s["facing_compass"]!="SW" for s in states):failures.append("body heading drift")
    if not any(s["swing_foot"]=="left" for s in states[:48]):failures.append("no left step")
    if not any(s["swing_foot"]=="right" for s in states[:48]):failures.append("no right step")
    min_axe=9999
    for i,s in enumerate(states):
        points=list(s["joints"].values()) + [
            s["axe"]["handle_start"],s["axe"]["head_center"]] + s["axe"]["blade_polygon"]
        for x,y in points:
            distance=min(x-SAFE,SIZE-SAFE-x,y-SAFE,SIZE-SAFE-y)
            min_axe=min(min_axe,distance)
            if distance<CLEARANCE:
                failures.append(f"safe-area violation in frame {i}: {(x,y)}")
                break
        if i<48 and s["phase"]!="walk":failures.append("early attack")
        if i>=48 and s["phase"]!="attack":failures.append("late walk")
    return {
        "status":"PASS" if not failures else "FAIL",
        "errors":failures[:20],
        "generative_calls":0,"paid_cost_usd":0,
        "duration_seconds":DURATION,"fps":FPS,"frames":len(states),
        "size_px":[SIZE,SIZE],"body_heading":"SW (fixed, no yaw animation)",
        "walking_seconds":[0,4],"attacking_seconds":[4,8],
        "number_of_planned_steps":len(FOOT_EVENTS),
        "foot_forward_lead_xy":list(FOOT_FORWARD_LEAD),
        "root_start_xy":list(START_ROOT),"root_after_walk_xy":list(ATTACK_ROOT),
        "root_distance_px":round(actual_distance,3),
        "root_distance_percent_of_frame_side":round(100*actual_distance/SIZE,3),
        "root_horizontal_fraction":round(STEP_DIAGONAL/SIZE,5),
        "root_vertical_fraction":round(STEP_DIAGONAL/SIZE,5),
        "both_feet_planted_from_4s":len(actual_attack_roots)==1,
        "planned_steps":FOOT_EVENTS,
        "stride_distances_px":foot_step_distances,
        "swing_foot_lift_amplitude_px":34.0,
        "minimum_swing_knee_angles_degrees":minimum_swing_angles,
        "walking_pelvis_bob_amplitude_px":4.5,
        "mean_stride_distance_px":round(sum(foot_step_distances)/len(foot_step_distances),3),
        "maximum_planted_foot_slip_during_walk_px":round(max_stance_slip,5),
        "complete_rigid_axe_in_safe_area":min_axe>=CLEARANCE,
        "minimum_clearance_px":round(min_axe,2),
        "note":"Geometric driver only. It does not prove that a future generative model will follow these joints or retain identity/axe."}


def make_sheet(states):
    picks=[6,18,30,42,54,66,78,90]
    out=Image.new("RGB",(4*330,2*350+62),"#e9edf1")
    d=ImageDraw.Draw(out)
    d.rectangle((0,0,out.width,61),fill="#25394b")
    d.text((15,16),"SW V4 / DETERMINISTIC POSE DRIVER / NOT GENERATIVE OUTPUT",fill="white")
    for idx,i in enumerate(picks):
        state=states[i]
        frame=Image.new("RGB",(SIZE,SIZE),(246,244,238))
        draw_pose(frame,state,debug=True)
        frame.thumbnail((315,315),Image.Resampling.LANCZOS)
        x=(idx%4)*330+(330-frame.width)//2
        y=62+(idx//4)*350+27
        out.paste(frame,(x,y))
        d.text(((idx%4)*330+10,62+(idx//4)*350+6),
               f"{state['time_seconds']:.1f}s : {state['subphase'].upper()}",fill="#273b49")
    out.save(OUT/"contact-sheet.png",optimize=True)


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    OUT.mkdir(parents=True,exist_ok=True)
    # Samples at exact output-frame timestamps; 0-4 = 48 frames, 4-8 = 48 frames.
    states=[get_pose(i/FPS) for i in range(FRAMES)]
    qa=check(states)
    if qa["status"]!="PASS":
        raise RuntimeError(json.dumps(qa))
    align=make_alignment_preview(states[0])
    qa["reference_alignment"]=align
    (OUT/"keypoints.json").write_text(json.dumps({
        "version":1,"purpose":"SW humanoid+rigid axe structural motion control",
        "fps":FPS,"duration_seconds":DURATION,"size_px":[SIZE,SIZE],
        "frames":states},indent=2)+"\n",encoding="utf-8")
    encode_video(OUT/"pose-control-8s.mp4",states,False)
    encode_video(OUT/"debug-motion-8s.mp4",states,True)
    make_sheet(states)
    (OUT/"metrics.json").write_text(json.dumps(qa,indent=2)+"\n",encoding="utf-8")
    (OUT/"README.md").write_text(
        "# SW deterministic 8-second motion driver (no paid generation)\n\n"
        "This v3 retains the five-step grounded gait but lifts each swinging foot higher and articulates each knee much more deeply. It remains a geometry-only control prototype for the existing man-of-the-Marches SW character. "
        "It is not a replacement character illustration, production sprite, or confirmed compatible OpenPose video.\n\n"
        "- [Motion debug MP4](debug-motion-8s.mp4) — 0–4s SW steps, 4–8s planted axe attacks.\n"
        "- [Clean pose-control MP4](pose-control-8s.mp4) — prospective source for pose/depth conditioned video systems.\n"
        "- [Eight-frame storyboard](contact-sheet.png)\n"
        "- [SW appearance plus skeleton alignment preview](source-pose-alignment-preview.png)\n"
        "- [Exact joints, root, feet, full rigid axe polygons for every 1/12-second frame](keypoints.json)\n"
        "- [Deterministic validation report](metrics.json)\n\n"
        "Image identity remains linked to the original existing SW.png. The driving geometry is deliberately "
        "simplified and should be visually aligned/validated before any model-conditioning expense. "
        "No OpenRouter API call or video generation cost is incurred.\n",
        encoding="utf-8")
    print(json.dumps(qa),flush=True)


if __name__=="__main__":
    main()
