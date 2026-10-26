# WarConquer — conception du jeu

**WarConquer** est un projet de jeu de stratégie en temps réel médiéval-fantastique, avec une boucle de conquête classique et un univers original où les royaumes se disputent le pouvoir de réécrire l'histoire.

## Bibles de conception (documents littéraires et métier)

- **[Bible du jeu](docs/game-bible.md)** — vision, règles, économie, unités, bâtiments, technologie, magie, modes et structure des campagnes.
- **[Univers et personnages](docs/world-lore.md)** — Trame, Corrections, régions, sociétés, chronologie, personnages et révélations.
- **[Campagne de la Couronne](docs/campaign-crown.md)** — traitement narratif et objectifs jouables des dix missions C1 à C10.
- **[Campagne des Marches](docs/campaign-marches.md)** — traitement narratif et objectifs jouables des dix missions M1 à M10.
- **[Codex des unités et bâtiments](docs/unit-building-codex.md)** — identité de chaque famille militaire, bâtiments, évolutions, sorts et descriptions en jeu.

Ces documents constituent une **proposition de conception en cours de discussion** ; ils ne définissent pas encore une implémentation technique. Le gameplay et les contenus originaux seront développés ensuite.

## Guides de pose pour les assets animés

Le pilote de contrôle de mouvement SW approuvé est maintenant accessible depuis [le pipeline de guides de pose](docs/pose-guided-asset-animation.md). Un seul script, une seule GitHub Action et une seule requête servent d'entrée : `scripts/build-pose-guide.py`, `.github/workflows/build-pose-guide.yml`, `pose-guide-request.json`.

Ces guides contiennent des articulations et une trajectoire d'arme rigide; **ils ne sont pas encore les sprites animés du jeu**. Les vidéos OpenRouter précédentes et le pipeline historique des huit directions sont conservés à des fins de comparaison.

---

# WebSuite — visual browser automation for development agents

This repository is the initial demonstration of **WebSuite**: a lightweight,
portable tool that lets AI agents **see what their HTML actually renders** and
interact with it (mouse, keyboard, text entry) through GitHub Actions.

**WebSuite is not tied to WarConquer.** Copy its script and workflow into any
HTML-based project. No Playwright, browser installation, web hosting or
permanent server is required on GitHub's Ubuntu runner.

## For coding agents: use WebSuite

When you change HTML, CSS, or JavaScript that affects the visible interface:

1. **Render the page:** run the [WebSuite GitHub Action](.github/workflows/websuite.yml)
   on `main` with the affected `html_path`. Pushing changed HTML to `main`
   also triggers a render automatically.
2. **Test interactions when relevant:** pass `actions_json` (a JSON array) or a
   repository-relative `scenario_path` to click, type, press keys, assert text,
   and take multiple screenshots.
3. **Actually inspect the image:** download the `websuite` Actions artifact,
   extract its PNGs, and open the images with a vision-capable tool. Read
   `manifest.json` to match images to pages and actions.
4. **Report only what you verified:** if an agent cannot access or open a PNG,
   say so. A green workflow or artifact alone does not count as visual review.

**Example prompt to an AI agent:**

> Use WebSuite on `patate-radar.html`, click `#dispatch-fleet`, type
> `orion-7` into `#fleet-code`, press Enter, inspect the final screenshot
> and report any visual issues.

## Quick start

From **GitHub → Actions → WebSuite · Visual browser automation → Run workflow**:

- `html_path`: HTML file to capture (demo default: `patate.html`).
- `actions_json`: optional JSON array of actions on that file.
- `scenario_path`: optional path to a committed JSON test scenario; takes
  precedence over `actions_json`.

Example `actions_json`:

```json
[
  {"action": "click", "selector": "#dispatch-fleet"},
  {"action": "type", "selector": "#fleet-code", "text": "orion-7"},
  {"action": "press", "key": "Enter"},
  {"action": "assertText", "selector": "#fleet-status", "includes": "CONFIRMED: ORION-7"},
  {"action": "screenshot", "name": "after-enter"}
]
```

The same browser session handles all commands. Supported actions: `click`,
`type`, `press`, `wait`, `assertText` and `screenshot`.

## CLI, outputs and portability

```bash
node scripts/websuite.mjs --help
node scripts/websuite.mjs patate.html render.png
node scripts/websuite.mjs --scenario examples/render-interaction.json renders
```

- Engine: Node.js + preinstalled headless Chrome via native CDP.
- Captures: full-page PNGs; scenario mode also creates before/after screenshots
  and `manifest.json` with timing and action data.
- Artifact: **`websuite`**, GitHub Actions retention **1 day**.
- Cost: no external paid dependencies. The Chrome work took **2.856 seconds**
  in one measured demo (four screenshots plus interactions), but GitHub runner
  scheduling adds variable overhead; **3 seconds end-to-end is not guaranteed**.
- Portability: copy `scripts/websuite.mjs` and
  `.github/workflows/websuite.yml` to another repository; adjust the default
  `html_path` for that project.

Full reference: **[docs/websuite.md](docs/websuite.md)** ·
Demonstration scenario: **[examples/render-interaction.json](examples/render-interaction.json)**.

## Demonstration files

- `patate.html`: static landing/dashboard page.
- `patate-radar.html`: interactive dashboard used to validate CDP mouse,
  typing, Enter and screenshots.
