# Development agents

WebSuite is the project's reusable browser-based visual QA tool. See
[README.md](README.md#for-coding-agents-use-websuite) and
[docs/websuite.md](docs/websuite.md).

Whenever changes affect HTML/CSS/JS visuals or interactivity, run the WebSuite
GitHub Action with the relevant HTML, scenario or inline actions; then **open
and inspect the generated PNG**, not just the workflow status. Mention any
inability to view the image honestly.

Use `scripts/websuite.mjs` (zero npm dependencies) and
`.github/workflows/websuite.yml`. Prefer one run for multiple changed HTML
files to minimize Actions cost; keep the browser in one session for interactions.
WebSuite is portable and should remain independent of WarConquer game logic.
