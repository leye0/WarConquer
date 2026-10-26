# SW motion-driver v2 — gait adjustment review

Date: 26 October 2026. Deterministic skeleton and rigid-axe animation only;
no character redesign, OpenRouter/Muse request, or paid video model call.

## Compared with v1

| Property | v1 | v2 |
| --- | --- | --- |
| Walk duration | 4.0 s | 4.0 s |
| Alternating swings/steps | 4 | 5 |
| Root travel during walk | 38.4 px | 53.76 px |
| Mean root speed | 9.6 px/s | 13.44 px/s (+40%) |
| Approximate mean foot stride travel | 15.696 px | 23.911 px (+52%) |
| Swing foot elevation amplitude | 15 px | 21 px |
| Movement heading | SW | SW |
| Planted foot slide (sampled frames) | 0 px | 0 px |
| Feet at rest during attacks | yes | yes |
| Entire weapon inside safe area | yes | yes |
| Brown beak on head | yes (an orientation wedge) | removed |

The first v1 stride mean is calculated from its four hard-coded foot planting
events and root speed. The v2 value is directly reported by its deterministic
foot-trajectory test. Stance foot positions are frozen while the other foot
moves; stride travel and root displacement are linked by the same trajectory.

## Visual inspection

- The head is now a plain oval. The old brown beak-like polygon was just an
  attempted lower-left-facing indicator, never anatomy.
- The SW direction indicator remains a separate green arrow in the debug
  view only. It is not part of the character or the clean pose-control video.
- The faster cadence, longer world-space steps and visibly higher swinging
  foot are present in the updated sheet/video. Root motion remains continuous
  for the four-second walking interval.
- Both attack feet retain fixed coordinates from 4 seconds onward, and the
  axe is still rigidly attached and entirely inside the central 768px canvas.
- Anatomically correct SW yaw is **not certified** by this simple 2D driver;
  boot alignment and original-hatchet registration need further calibration
  before any model-driven character rendering.

## View and compare

- [v2 revised debug animation](debug-motion-8s.mp4)
- [v2 clean control animation](pose-control-8s.mp4)
- [v2 eight-frame sheet](contact-sheet.png)
- [v2 original-character alignment preview](source-pose-alignment-preview.png)
- [v2 numeric validation](metrics.json)
- [v1 debug animation](../sw-motion-driver-v1/debug-motion-8s.mp4)
- [v1 sheet](../sw-motion-driver-v1/contact-sheet.png)

Result: geometric checks PASS. This is **not approval of any future generated
character animation**, and no paid synthesis was attempted.
