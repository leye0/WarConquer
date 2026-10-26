# SW v5 — upright, triple-stride gait QA

This version addresses the review that the v4 axeman walked like he was **sitting on a chair**. It remains a deterministic **2D skeleton/rigid-axe motion prototype**, not a production sprite or generative video.

## Geometric change (one isolated gait adjustment)

In v4 the animated knees travelled too far ahead of each ankle in screen-space during foot swing. Combined with very acute knees (about 80–85°), this produced an artificial crouched/seated silhouette.

- Forward swing-knee displacement coefficient: **32 px → 14 px**.
- Extra upward swing-knee displacement coefficient: **17 px → 12 px**.
- Minimum sampled knee flexion angles: **left 79.58° → 112.71°; right 85.51° → 121.15°**.
- Keeps some visible knee flexion (test enforces a 105–135° target window for the deepest swing bend) while allowing longer leg extension.

**Deliberately unchanged from v4:**

- The five foot landing displacements: **79.136, 107.763, 57.254, 57.254, 57.254 px**. Each is still 3× its corresponding v3 displacement.
- Total SW root motion in 0–4s: **161.28 px**.
- Swing-foot clearance arc amplitude: **34 px**, hip bob amplitude **4.5 px**.
- Root direction, gait timings, 4–8s two-strike rigid axe sequence and attack foot positions.
- Safe area, reference character and all previous video files.

## Actual output and checks

Generated through the dedicated GitHub Action on `main` and inspected the resulting eight-frame PNG (walk frames sampled at ~0.5, 1.17, 1.83 and 2.58 seconds, plus four attack moments). The v5 thighs no longer project as sharply forward at peak swing. Compared with the v4 contact sheet, the foot trajectory remains long but the legs look more upright.

- `metrics.json` status: **PASS**
- **96** rendered frames, **12 fps**, **8 sec**, **768 × 768**
- Ground-contact foot displacement (consecutive sampled stance frames): **0 px**
- Both feet stay planted during attacks: **PASS**
- Complete body and axe inside the central safety area: **PASS**, minimum clearance **89.07 px** vs required 20 px
- Existing original SW sprite remains intact; no new character art
- Generative video calls: **0**; model cost: **US$0**
- Verified both published MP4s and PNG sheets in GitHub.

## Remaining uncertainties

The thumbnails support the postural improvement but **do not prove natural human biomechanics**. This code still uses projected 2D knees rather than a 3D kinematic skeleton with fixed femur/shin lengths. The torso/pelvis angle remains schematic, and the skeleton-to-existing-SW-art alignment is still approximate. The user should inspect the full video before accepting this gait, and no paid OpenRouter model was invoked.

## Files

- [Inspect the full debug video](debug-motion-8s.mp4)
- [Inspect the pose-control video](pose-control-8s.mp4)
- [Eight-moment sheet](contact-sheet.png)
- [Original SW art with skeleton overlay](source-pose-alignment-preview.png)
- [Frame-by-frame pose and axe coordinates](keypoints.json)
- [Machine checks](metrics.json)
- [Previous v4 visual sheet](../sw-motion-driver-v4/contact-sheet.png)
