# SW textured frame experiment — draft for user validation

One continuous 8-second video: walk SW for 0-4 seconds, plant feet, then attack SW for 4-8 seconds. No Muse image generation, no audio, and no automatic paid retries.

- [Original-character textured reference](reference-SW-textured-safe-768.png)
- [MP4](SW-walk-then-attack-textured.mp4)
- [Eight-frame contact sheet](contact-sheet.jpg)
- [32 frames sampled at 4 fps](frames-4fps/)
- [Quantitative and uncertain-quality report](quality-report.json)
- [Exact prompt](prompt.txt)
- [OpenRouter job metadata and billed usage](job.json)

OpenRouter model: x-ai/grok-imagine-video-1.5-lite; 480p square, 8s, no audio. Usage: {"cost": 0.17, "is_byok": false}.

Border heuristic consistent: True; warning-band anomaly frames: []; subject walking bbox height end/start: 1.031; old v2: 1.487.

**PENDING USER VISUAL APPROVAL.** Pixel and bbox heuristics cannot conclusively detect cropped axe tips, warning-band intersection, anatomical SW orientation, a continuous shot or correct walk-then-attack timing. Inspect the actual MP4. Previously generated videos remain intact under [SW v1](../video-sw/) and [SW v2](../video-sw-v2/).
