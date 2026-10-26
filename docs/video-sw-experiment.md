# SW walking then attacking video proof of concept

This is **video**, not a sprite-sheet generator. Use the approved source still `assets/experiments/standing-turnaround/marches_hache/SW.png`, rendered to **256×256** against a clean light background, as the first frame in an OpenRouter image-to-video job.

- Exactly 8 seconds, 480p, audio disabled.
- **0–4 s:** walk toward the bottom-left of the screen (southwest / SW), only a short distance.
- **4–8 s:** stop, plant both feet, then swing axe toward the same bottom-left direction. Never rotate.
- Camera fixed, full figure in frame, exactly the existing WarConquer axeman.
- Try free Seedance 1.5 Pro first, then inexpensive Seedance 1.5 Pro, then Grok Imagine Video Lite if the model isn't available / submission is explicitly rejected.
- **Safety:** at most **one accepted OpenRouter video job** per request. No automatic second paid job after an accepted job fails, times out or an ambiguous network error. The `job_id` is saved to `job.json` for possible safe resumption. OpenRouter's documented `/api/v1/videos` async flow is used, not `/api/v1/images`.
- Output: `assets/experiments/video-sw/SW-walk-then-attack.mp4`, `contact-sheet.jpg`, `reference-SW-256.png` and `job.json` on `main`.
- Frame samples are visual inspection aids, **not automatically approved** as accurate SW motion. The clip must be opened for human QA.
- No Warcraft II asset is used or stored in this video experiment.
