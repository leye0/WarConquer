# SW gait driver v3 — knee flexion and lifted feet

Date: 26 October 2026. A no-paid-generation refinement of the original
deterministic SW motion driver. This is a kinematic skeleton prototype, not
a finished character animation or an anatomically validated motion capture.

## Change relative to v2

| Parameter | Driver v2 | Driver v3 |
| --- | --- | --- |
| Walk duration | 4 s | 4 s |
| Alternating steps | 5 | 5 |
| Root travel SW | 53.76 px | 53.76 px |
| Mean foot stride | 23.911 px | 23.911 px |
| Peak swing-foot rise | 21 px | 34 px |
| Forward knee articulation | small midpoint offset | stronger forward projection during swing |
| Minimum measured swing-knee angle (left) | not explicitly measured | 97.53 degrees |
| Minimum measured swing-knee angle (right) | not explicitly measured | 108.83 degrees |
| Torso/hip bounce | none | up to 4.5 px |
| Stance foot slip, sampled frames | 0 px | 0 px |
| Attack foot motion | frozen | frozen |

The knee angle is measured from the projected 2D skeleton. A straight knee
is near 180 degrees, smaller angles represent greater visible bend.

## Results

- The **first preflight correctly failed** when the right leg bent
  insufficiently (minimum measured knee angle about 150 degrees).
- After correcting the forward projection of the right knee, the geometric
  validation **passed** with the bilateral angles listed above.
- The foot trajectory remains the original smooth ground-anchored
  stance/swing system: no fake sliding or unrelated foot motion was added.
- Rigid axe trajectory and the locked SW heading are unchanged.
- Source-art alignment and true 3D body yaw remain separate unsolved matters.
- No image or video AI endpoint was called.

## Output

- [Revised motion debug MP4](debug-motion-8s.mp4)
- [Clean conditioning prototype MP4](pose-control-8s.mp4)
- [Eight control moments](contact-sheet.png)
- [Every frame's keypoints](keypoints.json)
- [Exact geometric checks](metrics.json)
- [Previous v2 motion debug](../sw-motion-driver-v2/debug-motion-8s.mp4)

**Verdict:** the deeper knee bend and greater leg elevation requested by the
user are present and measured. Naturalism still requires reviewing the actual
moving MP4; a successful constraint check alone cannot certify convincing
human gait.
