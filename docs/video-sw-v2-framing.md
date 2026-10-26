# SW video v2 — complete axe inside frame

The first video (see `assets/experiments/video-sw/`) visibly clips the axe near 4.5 s. **That video cannot be repaired by shrinking its rendered pixels**, because the axe head is outside the encoded frame.

This second controlled trial uses exactly the same WarConquer SW still as the first image, but positions a significantly smaller character (target height **35%**) in a **768×768 px** square first-frame input, with the character centered around 61% width and feet near 78% height.

The prompt demands **no auto-zoom, no recenter, no camera movement, and 10% safe margins around the character and full axe at every moment**. Walking 0–4 s is SW toward screen bottom-left with very little displacement. Attack 4–8 s starts at a standstill and swings in the same direction, with a compact diagonal arc to preserve the whole weapon.

Uses **one** accepted `x-ai/grok-imagine-video-1.5-lite` job via the OpenRouter async video API, at 480p / 1:1 / 8 seconds. No paid retries. Output is provisional pending user visual QA. The script examines video borders at 4 frames/sec and writes eight sample stills to `contact-sheet.jpg`; automated border contact detection is only a heuristic and cannot certify action quality.

The output is intentionally kept separate from the first experiment under `assets/experiments/video-sw-v2/` so both videos can be compared.
