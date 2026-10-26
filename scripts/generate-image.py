#!/usr/bin/env python3
"""OpenRouter image generation, with mandatory style references and resumable batches."""
import argparse, base64, concurrent.futures, hashlib, io, json, os, re, threading, traceback
from pathlib import Path
import urllib.request, urllib.error
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
_cutout_lock = threading.Lock()
_cutout_session = None

def cutout_session():
    global _cutout_session
    with _cutout_lock:
        if _cutout_session is None:
            from rembg import new_session
            _cutout_session = new_session('u2netp')
        return _cutout_session

STYLE = '''Original medieval fantasy RTS concept, hand-painted 2D with credible material details and readable silhouette. Match the supplied style references: brushwork, proportions, lighting, detail density, camera and faction palette. References show OTHER subjects: do not reproduce their identity, equipment or add them to the image. Exactly one complete centered subject, slightly elevated three-quarter view, ample empty margin around all extremities. Transparent background, no ground, scenery, base, interface, typography, logos or watermark. Never draw a checkerboard. If native transparency is impossible use a plain white background for extraction.'''

def safe_path(value):
    p = (ROOT / value).resolve()
    if not p.is_relative_to(ROOT / 'assets/concepts') or p.suffix != '.png':
        raise ValueError('Output must be a PNG under assets/concepts/')
    return p

def catalog():
    rows = []
    for line in (ROOT / 'docs/visual-asset-catalog.md').read_text().splitlines():
        m = re.match(r'\| ([^|]+) \| ([^|]+) \| `(assets/concepts/[^`]+)` \|', line)
        if m:
            name, desc, path = m.groups()
            faction = path.split('/')[2]
            palette = ('midnight blue, ivory, bronze, pale limestone, structured maintained materials' if faction == 'couronne' else 'oxblood red, soot black, patinated copper, repaired leather, blackened timber, memory ribbons')
            extra = 'One isolated ship, diagonal overhead view, no water, no crew.' if '/ships/' in path else ('Complete isolated building, readable function, no terrain tile.' if '/buildings/' in path else '')
            rows.append(dict(name=name, output=path, prompt=f'{STYLE}\nFaction palette: {palette}.\nSubject: {desc}. {extra}', references=[f'assets/concepts/{faction}/units/archer.png', f'assets/concepts/{faction}/units/garde_lourd.png']))
    if len(rows) != 68:
        raise ValueError('Expected exactly 68 original catalog entries')
    objects = []
    for line in (ROOT / 'docs/object-asset-catalog.md').read_text().splitlines():
        m = re.match(r'\| ([^|]+) \| ([^|]+) \| `(assets/concepts/[^`]+)` \|', line)
        if not m:
            continue
        name, desc, path = m.groups()
        faction = path.split('/')[2]
        palette = {
            'couronne': 'midnight blue, ivory, bronze, pale limestone, precise maintained craftsmanship',
            'marches': 'oxblood red, soot-black oak, patinated copper, repaired linen, memory threads',
            'neutral': 'aged ivory stone, old bronze, weathered oak, parchment, midnight blue ink, restrained oxblood accents'
        }[faction]
        refs_faction = faction if faction != 'neutral' else 'couronne'
        if path.endswith('/masque_signataire.png') or path.endswith('/eclat_echo.png'):
            refs = ['assets/concepts/neutral/objects/cloche_demain.png', 'assets/concepts/neutral/objects/pierre_temoignage.png']
        else:
            refs = [f'assets/concepts/{refs_faction}/units/archer.png', f'assets/concepts/{refs_faction}/buildings/sanctuaire.png']
        objects.append(dict(name=name, output=path, prompt=f'{STYLE}\nFaction/material palette: {palette}.\nSubject: {desc}. This is ONE small narrative prop, not a building, scene or environment. No readable text, no floor, no surrounding scenery.', references=refs))
    if len(objects) != 10:
        raise ValueError('Expected exactly 10 narrative object entries')
    narrative = []
    for line in (ROOT / 'docs/narrative-asset-catalog.md').read_text().splitlines():
        m = re.match(r'\| ([^|]+) \| ([^|]+) \| `(assets/concepts/[^`]+)` \|', line)
        if not m:
            continue
        name, desc, path = m.groups()
        faction = path.split('/')[2]
        if path.endswith('/autel_coeur_cousu.png'):
            # The old monument reference encouraged Muse to draw a sealed stone chest.
            # Use an actual open table for structural silhouette and a memory relay for materials.
            refs = ['assets/concepts/marches/objects/table_places_vides.png', 'assets/concepts/neutral/sites/relais_intact.png']
            palette = 'pale Crown limestone and bronze on the left, dark Marches slate and black oak with red memory cords on the right, restrained ivory-blue Echo stitching'
        elif '/huissiers/' in path:
            refs = ['assets/concepts/neutral/objects/masque_signataire.png', 'assets/concepts/couronne/units/garde_lourd.png']
            palette = 'charcoal forged iron, weathered dark steel and restrained aged bronze, neutral to the two factions'
        elif '/sites/' in path:
            refs = ['assets/concepts/neutral/objects/pierre_temoignage.png', 'assets/concepts/couronne/buildings/observatoire.png']
            palette = 'aged ivory limestone, weathered bronze, pale white-blue Echo, small touches of old dark wood and red memory thread'
        elif faction == 'couronne':
            refs = ['assets/concepts/couronne/units/archiviste.png', 'assets/concepts/couronne/units/garde_lourd.png']
            palette = 'midnight blue, ivory, bronze, practical medieval tailoring and maintained materials'
        elif faction == 'marches':
            refs = ['assets/concepts/marches/units/paysan.png', 'assets/concepts/marches/units/ravaudeuse.png']
            palette = 'oxblood red, charcoal wool, weathered leather, patinated copper and memory ribbons'
        else:
            refs = ['assets/concepts/couronne/units/paysan.png', 'assets/concepts/marches/units/paysan.png']
            palette = 'weathered medieval linen, leather, muted slate blue and oxblood, maritime brass, faction-neutral'
        kind = 'ONE isolated full-body humanoid with feet, hands and any props fully in frame' if '/characters/' in path or '/huissiers/' in path else 'ONE isolated physical stone-and-metal site structure; no terrain or environment'
        narrative.append(dict(name=name, output=path, prompt=f'{STYLE}\nMaterial palette: {palette}.\nSubject: {desc}. {kind}. Match style references for brushwork and MATERIAL ONLY, never copy their subject. No readable text, no added people, no painted ground.', references=refs))
    if len(narrative) != 18:
        raise ValueError('Expected exactly 18 narrative character, Huissier and site entries')
    return rows + objects + narrative

def api(payload):
    req = urllib.request.Request('https://openrouter.ai/api/v1/images', data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Preserve status and safe provider error fields, never raw payloads or image data.
        detail = ''
        try:
            body = json.loads(error.read(8192).decode('utf-8', errors='replace'))
            info = body.get('error', {}) if isinstance(body, dict) else {}
            if isinstance(info, dict):
                detail = str(info.get('message', ''))[:500]
                code = str(info.get('code', ''))[:80]
                detail = f' code={code}; message={detail}'
        except (ValueError, UnicodeError, OSError):
            pass
        raise RuntimeError(f'OpenRouter HTTP {error.code}{detail}; no automatic paid retry') from None

def generate(job):
    target = safe_path(job['output'])
    replacing = target.exists()
    if replacing and not job.get('replace_existing', False):
        return dict(output=job['output'], status='skipped-existing')
    refs, hashes = [], {}
    for value in job['references']:
        p = safe_path(value)
        raw = p.read_bytes()
        hashes[value] = hashlib.sha256(raw).hexdigest()
        refs.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(raw).decode()}})
    if not refs:
        raise ValueError('At least one reference is required for visual consistency')
    job = dict(job, prompt=job['prompt'] + '\nCRITICAL FRAMING: show the ENTIRE isolated subject, 15 percent empty margin on all four sides, about 65 percent of square canvas occupied. Preserve the exact SUBJECT SHAPE specified above, use references for PAINTING STYLE only and do NOT imitate their geometry. No atmospheric haze. Background must be uniform white if alpha unavailable.')
    result = api(dict(model=os.environ['OPENROUTER_IMAGE_MODEL'], prompt=job['prompt'], input_references=refs, n=1, output_format='png', background='transparent', aspect_ratio='1:1'))
    raw = base64.b64decode(result['data'][0]['b64_json'], validate=True)
    im = Image.open(io.BytesIO(raw)).convert('RGBA')
    raw_dir = ROOT / 'image-output/raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / (job['output'].replace('/', '__'))
    im.save(raw_file)
    removed = False
    if im.getchannel('A').getextrema()[0] == 255:
        from rembg import remove
        # A shared session prevents concurrent downloads and repeated model initialization.
        im = remove(im, session=cutout_session(), alpha_matting=True)
        removed = True
    alpha = im.getchannel('A')
    hist = alpha.histogram()
    transparent = sum(hist[:16]) / (im.width * im.height)
    opaque = sum(hist[240:]) / (im.width * im.height)
    if transparent < .05 or opaque < .02:
        raise ValueError('Invalid alpha/empty foreground; raw retained for review')
    # Enforce alpha-safe margins on the actual pixels, not just via a prompt.
    margin = .15
    fg = alpha.point(lambda value: 255 if value > 32 else 0).getbbox()
    if not fg:
        raise ValueError('No visible alpha foreground after background extraction')
    w, h = im.size
    l, t, r, b = fg
    source_edge_contact = l <= 2 or t <= 2 or r >= w-2 or b >= h-2
    scale = min(1., (1-2*margin)*w/(r-l), (1-2*margin)*h/(b-t))
    if scale < .999 or not (l >= margin*w-2 and t >= margin*h-2 and r <= (1-margin)*w+2 and b <= (1-margin)*h+2):
        resized = im.resize((round(w*scale), round(h*scale)), Image.Resampling.LANCZOS) if scale < 1 else im
        canvas = Image.new('RGBA', (w,h), (0,0,0,0))
        x = round(w/2 - (l+r)*scale/2)
        y = round(h/2 - (t+b)*scale/2)
        canvas.alpha_composite(resized,(x,y))
        im = canvas
    new_box = im.getchannel('A').point(lambda value: 255 if value > 32 else 0).getbbox()
    if not new_box or new_box[0] < margin*w-3 or new_box[1] < margin*h-3 or new_box[2] > (1-margin)*w+3 or new_box[3] > (1-margin)*h+3:
        raise ValueError(f'Foreground outside safe margins: {new_box}')
    target.parent.mkdir(parents=True, exist_ok=True)
    im.save(target)
    meta = dict(job, replaced_previous=replacing, status='generated-awaiting-visual-review', model=os.environ['OPENROUTER_IMAGE_MODEL'], reference_sha256=hashes, background_removed=removed, framing_adjustment={'scale':round(scale,5),'margin':margin,'original_bbox':list(fg),'final_bbox':list(new_box),'source_edge_contact':source_edge_contact}, size=list(im.size), transparent_fraction=transparent, sha256=hashlib.sha256(target.read_bytes()).hexdigest(), usage=result.get('usage', {}))
    target.with_suffix('.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False) + '\n')
    return meta

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', default='image-request.json')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    request = json.loads((ROOT / args.request).read_text()) if not os.environ.get('IMAGE_PROMPT') else dict(prompt=os.environ['IMAGE_PROMPT'], output=os.environ['IMAGE_OUTPUT'], references=json.loads(os.environ['IMAGE_REFERENCES']))
    if 'prompt' in request:
        jobs = [dict(request, prompt=STYLE + '\nSubject: ' + request['prompt'])]
    else:
        jobs = [dict(r, replace_existing=r['output'] in request.get('replace_existing', [])) for r in catalog() if r['output'] in request['targets']]
        if len(jobs) != len(set(request['targets'])):
            raise ValueError('Unknown catalog target')
    if not set(request.get('replace_existing', [])).issubset({j['output'] for j in jobs}):
        raise ValueError('replace_existing must be a subset of the selected target paths')
    if not 1 <= len(jobs) <= 96:
        raise ValueError('Expected 1..96 jobs')
    workers = int(request.get('concurrency', 3))
    if not 1 <= workers <= 4:
        raise ValueError('Concurrency must be 1..4')
    for job in jobs:
        safe_path(job['output'])
        for ref in job['references']:
            safe_path(ref)
    if args.dry_run:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))
        return
    for key in ('OPENROUTER_API_KEY', 'OPENROUTER_IMAGE_MODEL'):
        if not os.environ.get(key):
            raise ValueError(f'Missing required secret: {key}')
    report = []
    def redact(value):
        for secret in (os.environ.get('OPENROUTER_API_KEY'), os.environ.get('OPENROUTER_IMAGE_MODEL')):
            if secret:
                value = value.replace(secret, '[REDACTED]')
        value = re.sub(r'(?i)Bearer\\s+[A-Za-z0-9._-]+', 'Bearer [REDACTED]', value)
        value = re.sub(r'data:image/[^\\s]+', '[IMAGE DATA REDACTED]', value)
        return value[:6000]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(generate, job): job for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            job = futures[future]
            try:
                report.append(future.result())
                print(job['output'] + ': ' + report[-1]['status'], flush=True)
            except Exception as error:
                detail = redact(''.join(traceback.format_exception(type(error), error, error.__traceback__)))
                report.append(dict(output=job['output'], status='failed', error_type=type(error).__name__, error=redact(str(error)), traceback=detail))
                print(f"::error title=Image generation failed::{job['output']}: {redact(str(error))}", flush=True)
                print(detail, flush=True)
    out = ROOT / 'image-output'
    out.mkdir(exist_ok=True)
    (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    tiles = []
    for item in report:
        p = safe_path(item['output'])
        if p.exists():
            im = Image.open(p).convert('RGBA'); im.thumbnail((320, 320))
            tile = Image.new('RGB', (360, 380), '#bbbbbb')
            tile.paste(im, ((360-im.width)//2, 10), im)
            ImageDraw.Draw(tile).text((8, 340), '/'.join(item['output'].split('/')[2:]), fill='black')
            tiles.append(tile)
    if tiles:
        sheet = Image.new('RGB', (360 * min(3, len(tiles)), 380 * ((len(tiles)+2)//3)), 'white')
        for i, tile in enumerate(tiles): sheet.paste(tile, ((i%3)*360, (i//3)*380))
        sheet.save(out / 'contact-sheet.png')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
            f.write('## Image generation\n' + '\n'.join('- ' + r['output'] + ': ' + r['status'] + ((' — ' + r['error']) if r['status'] == 'failed' else '') for r in report) + '\n\nVisual review required; these are candidates, not approved references.\n')
    if any(r['status'] == 'failed' for r in report):
        raise SystemExit(1)

if __name__ == '__main__': main()
