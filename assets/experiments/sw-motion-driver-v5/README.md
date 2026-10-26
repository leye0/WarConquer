# SW deterministic 8-second motion driver (no paid generation)

This v5 preserves the three-times-larger v4 strides and all fixed ground contacts while reducing excessive forward-knee projection so the gait reads as upright and purposeful instead of seated. The 34-px foot lift remains unchanged. It remains a geometry-only control prototype for the existing man-of-the-Marches SW character. It is not a replacement character illustration, production sprite, or confirmed compatible OpenPose video.

- [Motion debug MP4](debug-motion-8s.mp4) — 0–4s SW steps, 4–8s planted axe attacks.
- [Clean pose-control MP4](pose-control-8s.mp4) — prospective source for pose/depth conditioned video systems.
- [Eight-frame storyboard](contact-sheet.png)
- [SW appearance plus skeleton alignment preview](source-pose-alignment-preview.png)
- [Exact joints, root, feet, full rigid axe polygons for every 1/12-second frame](keypoints.json)
- [Deterministic validation report](metrics.json)

Image identity remains linked to the original existing SW.png. The driving geometry is deliberately simplified and should be visually aligned/validated before any model-conditioning expense. No OpenRouter API call or video generation cost is incurred.
