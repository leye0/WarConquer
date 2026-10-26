"""Reprocess downloaded original renders without any image-generation API call."""
import json, hashlib
from pathlib import Path
from PIL import Image, ImageDraw
from rembg import remove, new_session
ROOT = Path(__file__).resolve().parents[1]
session = new_session('isnet-general-use')
rows = []
for source in sorted((ROOT / 'original-runs').glob('*/image-output/raw/*.png')):
    relative = source.name.replace('__', '/')
    target = (ROOT / relative).resolve()
    if not target.is_relative_to(ROOT / 'assets/concepts') or not target.exists():
        continue
    # Later run wins when a subject was regenerated.
    result = remove(Image.open(source).convert('RGBA'), session=session, alpha_matting=True)
    result.save(target)
    meta_path = target.with_suffix('.json')
    meta = json.loads(meta_path.read_text())
    meta['cutout_model'] = 'isnet-general-use'
    meta['sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
    meta['status'] = 'generated-awaiting-visual-review'
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False)+'\n')
    rows.append(relative)
    print(relative, flush=True)
out = ROOT / 'image-output';out.mkdir(exist_ok=True)
paths = sorted(set(rows))
sheet = Image.new('RGB', (1080, 380*((len(paths)+2)//3)), '#222222')
for i, relative in enumerate(paths):
    im=Image.open(ROOT/relative).convert('RGBA');im.thumbnail((340,330))
    x=(i%3)*360; y=(i//3)*380
    sheet.paste(im,(x+(360-im.width)//2,y+5),im)
    ImageDraw.Draw(sheet).text((x+5,y+345),relative.replace('assets/concepts/',''),fill='white')
sheet.save(out/'contact-sheet.png')
