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

## Next pipeline stage — deterministic painted-asset preview

1. **Asset registration (first SW calibration implemented):** `rigged-asset-request.json` records manually inspected original-image polygons and two-point bones for head, torso, arms, legs, boots and the actual axe. The source PNG and anatomical right-hand axe ownership remain unchanged.
2. **Deterministic animation (first preview implemented):** `scripts/build-rigged-asset.py` warps source-art layers using approved joints, independently transforms the actual axe from the guide's grip and head-center coordinates, and composites one fixed 768×768 shot. Manual review must still check limb seams, grip overlap and occulted/hidden fabric; inverse warping cannot invent unseen surfaces.
3. **Appearance refinement (optional):** only if the rigged preview looks good, verify the documentation, conditioning support, credentials, and real cost of a pose/depth/video-guided model. Do not assume plain image-to-video obeys the guide. Prefer OpenRouter when a suitable **real** conditioning API exists; otherwise report the provider and tradeoff before any payment.
4. **Rendering (candidate implemented; final approval pending):** one continuous 8-second SW animated-art preview, 0–4 seconds travelling SW and 4–8 seconds planted/attacking; no clips, cuts, zoom, recentering or regenerated identity. The painted axe is independently transformed at fixed scale and rotation according to the existing guide.
5. **Quality control (automated first pass):** validate all guide states and frame bounds; FFmpeg extracts four image samples per second (32 total); publish a contact sheet, mask-registration sheet, machine report and US$0 model cost on `main`. Machine validation is only geometric; original-art masking, occlusion, handedness, grip, temporal coherence and aesthetic quality require Léon's visual approval.

## Preview files and reproducibility

- New registration: [`rigged-asset-request.json`](../rigged-asset-request.json).
- New renderer: [`scripts/build-rigged-asset.py`](../scripts/build-rigged-asset.py).
- Reuses **the existing** [pose-guide Action](../.github/workflows/build-pose-guide.yml) after regenerating/verifying the approved guide, so no extra one-off Actions are created.
- Output directory: [`assets/experiments/asset-animations/marches_hache/SW/`](../assets/experiments/asset-animations/marches_hache/SW/), independent of approved guide outputs. Outputs include `rigged-asset-8s.mp4`, `contact-sheet-32.png`, `mask-registration.png`, `source-registration.png` and `metrics.json`.
- The cutter uses only the actual SW painting, Python, Pillow and FFmpeg; no Muse/OpenRouter/video calls. This is **a candidate cut-out animation**, not a final visually approved sprite and not a general renderer for all eight headings.
- Source art, the approved motion driver, older paid experiments, and historical material remain unchanged.

## Relationship to older experiments

The `character-motion-request.json` and `.github/workflows/character-motion.yml` pipeline for eight directions is **a separate historical image-to-video workflow** and remains untouched. Preserve its paid stills/videos and original standing-direction assets. The old Grok SW video tests also remain as comparison evidence, including cases where zoom, orientation or the axe failed despite a successful Action.

The obsolete `sw-motion-driver-v1` through `sw-motion-driver-v5` *implementation files and generated intermediate directories* are superseded by this single named pose-guide entry point. Their earlier versions remain recoverable through Git history; they are not production APIs. Do not reintroduce one-off workflows for each adjustment.

## Generative motion-transfer experiment — DreamActor M2.0 (2026-10-27)

The approved **eight-second pose-control MP4 is already the driving video**; it must not
be re-created or "converted" into another motion video. The original entire-character
SW PNG is the appearance reference. Both approved inputs are unchanged.

A **single** Replicate `bytedance/dreamactor-m2.0` prediction was run against these exact
files (prediction ID `fna0t04wp9rmw0d1fbcrhcxr1g`). It succeeded:

- Pilot request: [`motion-transfer-request.json`](../motion-transfer-request.json).
- Resumable client: [`scripts/test-motion-transfer.py`](../scripts/test-motion-transfer.py).
- Reusable, one-shot GitHub Action: [`.github/workflows/test-motion-transfer.yml`](../.github/workflows/test-motion-transfer.yml).
- Video, 4-fps / 32-frame contact sheet, payment checkpoint and machine report:
  [`assets/experiments/motion-transfer/marches_hache/SW/dreamactor-m2.0/`](../assets/experiments/motion-transfer/marches_hache/SW/dreamactor-m2.0/).
- Output: **7.96 s, 960 × 960, 25 fps**. Estimated model charge:
  **US$0.398** at US$0.05 per generated second (not an account billing receipt).
  Input control: 8 s, 768 × 768, 12 fps.
- The secret is named `REPLICATE_API_KEY` in GitHub Actions; only the runner maps it
  to the standard Replicate `REPLICATE_API_TOKEN` environment variable. Never print
  or commit it.
- The prediction ID is committed **before polling** to prevent accidental duplicate
  paid submissions during a workflow rerun. Changing the trial request should only
  be done when an additional paid generation is authorized.

**Initial visual inspection (32 sampled frames):** the full character's identity,
clothing and axe are recognisable. The character moves toward SW during 0–4 s, and
two axe windups/recoveries appear during 4–8 s, broadly following the approved
driver. This shows useful **full-body transfer from a schematic guide**. It does
*not* establish exact joint trajectories, perfect rigid-weapon geometry, or visual
sprite approval. The generated MP4 has an opaque black background, requiring a
separate matte/alpha extraction and review before use as a transparent game asset.
Do not regenerate the approved motion or revert to the earlier manual cut-out rig
as a substitute for this test.
