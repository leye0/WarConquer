# Pose-guided asset animation — active SW control pilot

## Purpose

Produce a **faithful animated game asset** from an existing WarConquer illustration and a **deterministic guide of joints and a rigid weapon**. The guide is a control input, not character artwork.

The approved current control profile is `sw_walk_attack_8s` for the axeman of the Marches. **Do not revise this motion profile** without an explicit new user request.

## Canonical entry points

- Configuration: [`pose-guide-request.json`](../pose-guide-request.json)
- Renderer: [`scripts/build-pose-guide.py`](../scripts/build-pose-guide.py)
- GitHub Action: [`.github/workflows/build-pose-guide.yml`](../.github/workflows/build-pose-guide.yml)
- Approved SW outputs: [`assets/experiments/pose-guides/marches_hache/SW/`](../assets/experiments/pose-guides/marches_hache/SW/)

The workflow emits two 8-second MP4s (pose-control and debug), the original-SW alignment preview, a contact sheet, one frame-by-frame JSON file of character joints + rigid axe geometry, and a numeric validation report. Source artwork remains at `assets/experiments/standing-turnaround/marches_hache/SW.png`.

The renderer uses **Python, Pillow, FFmpeg only**. It does **not** call OpenRouter, Muse, or a video generator and costs **US$0 in generative-model calls**.

The profile is SW-only today; generic file names describe the purpose of the system, **not** universal support for other headings. Extend the profile registry deliberately rather than pretending the SW coordinates work for every direction.

## Next pipeline stage (NOT implemented yet)

1. **Asset registration:** calibrate the existing SW character silhouette against the approved joints; segment head, torso, limbs, boots, arms and the actual axe while preserving the original painting and handedness.
2. **Deterministic animation:** rig/warp the original body pieces to the guide. Treat the weapon as a separate rigid object controlled by the existing handle and blade coordinates. Correct visual overlap so hands grip the shaft. Keep the 768×768 camera entirely fixed.
3. **Appearance refinement (optional):** only if the rigged preview looks good, verify the documentation, conditioning support, credentials, and real cost of a pose/depth/video-guided model. Do not assume plain image-to-video obeys the guide. Prefer OpenRouter when a suitable **real** conditioning API exists; otherwise report the provider and tradeoff before any payment.
4. **Final rendering:** one continuous 8-second SW animation, 0–4 seconds travelling SW and 4–8 seconds planting feet and attacking; no clips, cuts, zoom, recentering or regenerated character identity. Composite the axe independently so its scale, rigid geometry and visibility are deterministic.
5. **Quality control:** compare model/rig output against guide coordinates on every frame; use FFmpeg to extract at least four image samples per second; audit camera scale, safe area, complete character/axe, SW body orientation and temporal action separation. Publish a contact sheet, machine report and cost/metadata on `main`; visual approval remains with Léon.

## Relationship to older experiments

The `character-motion-request.json` and `.github/workflows/character-motion.yml` pipeline for eight directions is **a separate historical image-to-video workflow** and remains untouched. Preserve its paid stills/videos and original standing-direction assets. The old Grok SW video tests also remain as comparison evidence, including cases where zoom, orientation or the axe failed despite a successful Action.

The obsolete `sw-motion-driver-v1` through `sw-motion-driver-v5` *implementation files and generated intermediate directories* are superseded by this single named pose-guide entry point. Their earlier versions remain recoverable through Git history; they are not production APIs. Do not reintroduce one-off workflows for each adjustment.
