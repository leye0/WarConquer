# Visual review — SW motion-driver v1

Date: 26 October 2026. The driver is a deterministic, zero-OpenRouter-cost
geometry prototype, not an approved sprite or a model-ready motion-transfer video.

## Verified from generated outputs

- Output exists: two 768×768 MP4s, 8.0 seconds at 12 fps (96 frames each).
- The four alternating foot-swing windows are encoded in keypoints.json.
- Root moves southwest by 38.4 px overall (27.153 px left and down), exactly 5% of the frame width in Euclidean distance, and stops at t=4s.
- Both foot coordinates and root remain fixed for all sampled frames from 4s onward.
- The axe is an actual rigid polygon attached to its grip, never a synthesised/deleted image element.
- Joint and axe coordinates stay at least 124.61 px from the inner safe-area boundary according to the deterministic test.
- One video holds clean pose graphics; the other includes debug geometry. No Muse, Grok, or other generative video call was made.

## Visible limitations to address before paid conditioning

1. The skeleton is deliberately basic and the video primarily reads as a 2D front/three-quarter pose. An asserted SW orientation in JSON is **not proof of an anatomically convincing SW torso and pelvis**. Use a 3D proxy or calibrated depth/pose driver before evaluating body-facing fidelity.
2. In the source-alignment PNG, the left foot landmark is lower than the visible corresponding boot, and the modelled axe does not perfectly overlay the original weapon. Calibrate joints and prop grip against the SW alpha image.
3. The simple vector colours and joint labels are not yet a certified OpenPose/DWPose encoding. Convert/test the exact requirements of the selected control model.
4. The debug source overlay shows the original standing warrior, not a deforming illustrated character. Do not confuse this guide with a completed textured animation.
5. Arms and attacks are kinematic sketches; contact/occlusion, cloth, muscle motion and true 3D yaw still require a well-controlled appearance stage.

## Model compatibility research (not yet invoked)

- Wan2.2 Animate moves character appearance from a reference image toward movement in a driver video, but its best results need a recognizable humanoid driving performance.
- LTX Union Control and Wan2.2 Fun Control support structural guidance such as pose/depth/edges, subject to the actual deployed API/model configuration.
- OpenRouter's generic video input references are not equivalent to guaranteed frame-by-frame pose control. Do not send a paid job on that assumption.
- A dedicated hosted motion-transfer API such as fal Wan Motion currently advertises about US$0.06/second (US$0.48 for 8s at 720p), but it would require a separately configured provider, and has not been called.

## Decision

**Motion constraints pass geometrically, but this is not yet ready for a paid motion-transfer evaluation.**

Next: calibrate a 3D/SW-aware pose/depth driver, align weapon and boots to the original artwork, and confirm model input compatibility and budget before any single paid attempt. Preserve this output as the v1 control baseline.
