# SW v4 — triple-stride gait visual and geometric QA

Reference: `assets/experiments/sw-motion-driver-v3/`. This v4 is a **deterministic pose blueprint**, not a newly synthesized character animation.

## What changed

- Tripled **all five foot-landing displacement lengths** relative to their v3 counterparts, keeping the five-step schedule unchanged (walking 0–4s).
- Matched total root travel to stride scale: 53.76 px → **161.28 px** in four seconds, directed down/left (SW).
- Moved the initial root to (536, 480) so the longer SW trajectory fits within the same 768×768 safe area.
- Kept the 34-px swing-foot lift, deeper knee projection, 4.5-px gait bob, fixed stance-foot world positions, and two planted axe strikes from 4–8s.
- No OpenRouter/video-model call; **$0 USD** generative cost. Original reference art and previous experiments are untouched.

## Measured results

| Check | v3 | v4 | Verdict |
|---|---:|---:|---|
| Five stride distances, px | 26.379, 35.921, 19.085, 19.085, 19.085 | 79.136, 107.763, 57.254, 57.254, 57.254 | Each **3.000×** |
| Mean stride length | 23.911 px | **71.732 px** | 3.000× |
| Four-second root travel | 53.76 px | **161.28 px** | 3.000× |
| Foot sliding during stance (sampled frames) | 0 px | **0 px** | PASS |
| Minimum sampled swing-knee angle | L 97.53° / R 108.83° | L **79.58°** / R **85.51°** | Deep bend |
| Swing-foot lift profile | 34 px | **34 px** | Preserved |
| Full posed body and rigid axe safe-zone minimum clearance | 111.11 px | **89.07 px** | PASS (threshold 20 px) |
| Walking/attacking temporal separation | 0–4 / 4–8s | **0–4 / 4–8s** | PASS |
| Attack feet fixed | Yes | **Yes** | PASS |

The first two strides are longer than the following three because this driver starts from an initial planted-foot position. This is **not** proof of uniform step cadence or game-ready gait.

## Visual inspection

Opened the GitHub-generated `contact-sheet.png` after the v4 workflow had published it, and compared it with the v3 sheet. The four walking thumbnails now sample approximately **0.5, 1.17, 1.83, 2.58 seconds** (near alternating foot-swing periods) rather than mostly heel-down instants. The greater foot reach and more obvious knee projection are visually apparent. The two attack cycles remain visible in the second row.

Verified both `debug-motion-8s.mp4` and `pose-control-8s.mp4` exist in GitHub and that `metrics.json` reports PASS.

## What PASS does not mean

- This schematic is still **2D pose geometry**. It does not ensure 3D SW torso/pelvis orientation, constant real-world bone lengths, natural joint forces, or correct sprite deformation.
- The skeleton and axe are approximately placed over the original SW character. The overlay is not a calibrated rig, and the weapon is not yet aligned exactly with the source illustration.
- This does not certify future video-model tracking, identity preservation or sprite-production quality.
- The user should judge the resulting movement visually before it becomes a production gait.

## Artifacts

- [Debug motion video](debug-motion-8s.mp4)
- [Clean pose control video](pose-control-8s.mp4)
- [Four walking + four attacking frames](contact-sheet.png)
- [Existing character / pose overlay](source-pose-alignment-preview.png)
- [Pose keypoints and rigid axe trajectory](keypoints.json)
- [Numerical validation](metrics.json)
