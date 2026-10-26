# SW v3 — textured safety frame: visual QA

Execution: [GitHub Actions 40409076489](https://github.com/leye0/WarConquer/actions/runs/40409076489), 26 October 2026. **NOT APPROVED.** One accepted OpenRouter paid submission, no retry. Actual reported cost: **US$0.17**. Model: x-ai/grok-imagine-video-1.5-lite; 8s, 480p, 1:1, audio disabled. Original SW character, not regenerated.

## Deliverables

- [768×768 textured-border SW reference](reference-SW-textured-safe-768.png)
- [Generated MP4: one continuous walk + attack](SW-walk-then-attack-textured.mp4)
- [Eight-image contact sheet](contact-sheet.jpg)
- [All 32 video frames sampled with FFmpeg at 4 fps](frames-4fps/)
- [Machine metrics, comparison and additional direct visual findings](quality-report.json)
- [OpenRouter job metadata, exact prompt and actual usage](job.json)
- [Video prompt](prompt.txt)

## Comparison of three SW experiments

| Trial | Walk apparent-height ratio (last 4 samples / first 4) | Axe/camera observations | Overall |
| --- | ---: | --- | --- |
| [v1](../video-sw/) | 1.001 | Axe head disappears beyond top edge around 4.5s | Noncompliant |
| [v2, wide framing](../video-sw-v2/) | 1.487 | Axe stays within edge on reviewed poses, but character grows strongly | Noncompliant |
| **v3, textured border** | **1.031** | Stable visible border with corners (32/32 samples), no detected safe-band crossing; **axe is not visible in sampled frame at ~5.125s** | **Noncompliant; user review pending** |

Height ratios come from rough foreground bounding boxes at 4 fps; equipment and posture can influence them. They are useful indicators, not definitive zoom measurements.

## Direct visual inspection

- **Border:** appears fixed, continuous and fully present throughout the sampled frames. The pixel heuristic flags no suspect frame; maximum change from the first frame: 1.99 average RGB levels on the border region. This is a promising framing improvement over v2.
- **Scale:** no obvious progressive enlargement during the first four seconds, versus clear enlargement in v2.
- **Character travel:** too much leftward movement. Foreground bbox center shifts approximately **109 px left (20% of video width)** and 38.5 px down (7.1% of height) between 0.125s and 3.875s, against the requested ~5% total. This is a rough pose-dependent measure, but the excessive leftward translation is visible.
- **Axe preservation:** **visible failure at ~5.125s** (sample index 20): the axe appears to vanish entirely when the character bends forward, then returns by 5.375s. It is not cropped by the outside border. The prompt requirement that the entire axe be visible on every frame was not met.
- **SW orientation:** in the attacks, the chest and shoulders turn appreciably more frontal; the exact whole-body SW direction is not reliably maintained.
- **Animation timing:** the sampled images show walking first and attack poses after 4s, but do not prove walking for the full 0–4s interval, two planted feet during every strike or perfect single-shot motion continuity.
- **Safe area:** sampled poses remain well inside the off-white region and no gray-band anomaly was detected. This does not mathematically prove every weapon part is present or that no brief overlap occurred between sampled frames.

## Conclusion

**The textured safety frame materially improves the specific zoom/cadrage symptom** relative to the wide empty v2 canvas, while retaining the complete border. However, the model still has animation-synthesis failures: a momentarily absent weapon, drifting attack orientation, and too much travel. **Do not treat this as an approved sprite-source video.** The actual MP4 and 32 frames are kept for Léon's validation. No further generation was initiated.
