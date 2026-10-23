# HTML screenshots and UI interaction (Chrome CDP)

This is a reusable, zero-dependency browser tool for WarConquer. GitHub Actions
uses the Chrome already installed on `ubuntu-24.04`; neither Playwright nor a
web server is required. Every run starts one headless Chrome process and uses a
direct DevTools Protocol (CDP) WebSocket connection.

## From ChatGPT / GitHub Actions

Open **Actions → Render HTML and UI interactions → Run workflow** on `main`.

- **html_path**: a repository-relative HTML path (default: `patate.html`).
  Produces one full-page `render.png`.
- **actions_json**: an optional JSON array of actions to execute directly against
  `html_path`, without adding a scenario file or commit.
- **scenario_path**: a repository-relative JSON file; if set, overrides
  `html_path` and `actions_json` and executes its interactive steps. Produces initial and final
  screenshots plus optional intermediate captures, and `manifest.json`.

Pushes to `main` automatically render **all changed HTML files** with a single
Chrome instance (one PNG per source and a manifest). PNG files are published
as the `html-render` artifact, retained for **one day**.

## Interactive scenario

See [examples/render-interaction.json](../examples/render-interaction.json).

```json
{
  "html": "patate-radar.html",
  "steps": [
    {"action": "click", "selector": "#dispatch-fleet"},
    {"action": "assertText", "selector": "#fleet-status", "includes": "FLEET DISPATCHED"},
    {"action": "screenshot", "name": "after-click"},
    {"action": "type", "selector": "#fleet-code", "text": "orion-7"},
    {"action": "press", "key": "Enter"},
    {"action": "assertText", "selector": "#fleet-status", "includes": "CONFIRMED: ORION-7"}
  ]
}
```

Commands are executed **in order**, in the same page/browser session:

| Action | Required fields | Effect |
| --- | --- | --- |
| `click` | `selector` | Finds CSS element, scrolls into view and sends real CDP mouse press/release. |
| `type` | `selector`, `text` | Clicks field, selects all existing text with Ctrl+A, inserts text through CDP. |
| `press` | `key` | Sends real CDP key-down/key-up. Supports Enter, Escape, Tab, Backspace, and four arrow keys. |
| `assertText` | `selector`, `includes` | Fails the run if the element is missing or lacks the required text. |
| `screenshot` | `name` | Captures a full-page PNG; name must contain only letters, digits, hyphen and underscore. |
| `wait` | `ms` | Waits 0–5000 ms for asynchronous page updates. |

Scenario captures `00-initial.png` and `99-final.png` automatically.
Named screenshots are placed between them. The artifact manifest lists
the images, action timings and startup time.

## Direct CLI on an equivalent Linux machine

```bash
node scripts/render-html.mjs patate.html render.png
node scripts/render-html.mjs --scenario examples/render-interaction.json renders
RENDER_ACTIONS_JSON='[{"action":"click","selector":"#dispatch-fleet"}]' \\
  node scripts/render-html.mjs --interactive patate-radar.html renders
```

The script assumes `/usr/bin/google-chrome` exists. Override with
`CHROME_BIN=/path/to/chrome` if needed.

For multi-page rendering, pass a file containing NUL-separated paths:

```bash
node scripts/render-html.mjs --nul-list /tmp/html-files.bin renders
```

## Development loop with GPT

1. Add or modify an HTML file or a scenario JSON in the repo on `main`.
2. Ask GPT to run the workflow with the appropriate HTML, inline actions or scenario path.
3. Inspect the run's `html-render` artifact and `manifest.json`.
4. Download the ZIP and open its PNG files with a vision-capable tool; **an
   artifact existing by itself is not proof that GPT has seen the image**.

The headless browser starts fresh for each GitHub-hosted run. The interactions
themselves are inexpensive, but scheduling and starting a hosted runner plus
Chrome can take multiple seconds; end-to-end latency of 3 seconds is not
guaranteed.

**Security / limitations:** input files must remain in the repository; no
external hosting is required, but an HTML page may request external resources.
Do not place secrets in scenario JSON: screenshots, source and artifact logs
can expose them. Screenshots use a 1280px viewport and capture the page's full
height. For slow asynchronous UI updates, add an explicit `wait` or assertion.
