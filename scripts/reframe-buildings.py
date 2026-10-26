#!/usr/bin/env python3
"""Non-generative framing correction for transparent WarConquer concepts."""
from pathlib import Path
from PIL import Image
import json

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    'assets/concepts/couronne/buildings/centre_iii.png',
    'assets/concepts/marches/buildings/centre_ii.png',
    'assets/concepts/marches/buildings/maison.png',
    'assets/concepts/marches/buildings/tour.png',
    'assets/concepts/neutral/objects/masque_signataire.png',
    'assets/concepts/neutral/objects/eclat_echo.png',
]

def reframe(path, margin=.12):
    import hashlib
    original_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    im = Image.open(path).convert('RGBA')
    alpha = im.getchannel('A')
    mask = alpha.point(lambda value: 255 if value > 32 else 0)
    bounds = mask.getbbox()
    if not bounds:
        raise ValueError(f'No foreground in {path}')
    width, height = im.size
    left, top, right, bottom = bounds
    box_width, box_height = right-left, bottom-top
    available = 1 - 2 * margin
    scale = min(1., width * available / box_width, height * available / box_height)
    if scale >= .999 and all((left >= margin*width, top >= margin*height, right <= (1-margin)*width, bottom <= (1-margin)*height)):
        return None
    # Transform the entire original RGBA image, preserving soft alpha edges.
    scaled = im.resize((round(width*scale), round(height*scale)), Image.Resampling.LANCZOS)
    x = round(width/2 - (left+right)*scale/2)
    y = round(height/2 - (top+bottom)*scale/2)
    canvas = Image.new('RGBA', im.size, (0,0,0,0))
    canvas.alpha_composite(scaled, (x,y))
    new_box = canvas.getchannel('A').point(lambda value: 255 if value > 32 else 0).getbbox()
    if not new_box or any((new_box[0] < width*margin-3, new_box[1] < height*margin-3, new_box[2] > width*(1-margin)+3, new_box[3] > height*(1-margin)+3)):
        raise ValueError(f'Unsafe framing result for {path}: {new_box}')
    canvas.save(path, optimize=True)
    metadata = path.with_suffix('.json')
    if metadata.exists():
        info = json.loads(metadata.read_text())
        info['framing_adjustment'] = {'method':'RGBA Lanczos rescale and recenter, no generative edit','source_sha256':original_sha256,'margin':margin,'scale':round(scale,5),'original_bbox':list(bounds),'new_bbox':list(new_box)}
        info['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        metadata.write_text(json.dumps(info, ensure_ascii=False, indent=2)+'\n')
    return {'path':str(path.relative_to(ROOT)), 'scale':round(scale,4), 'bbox_before':bounds, 'bbox_after':new_box}

def main():
    results=[]
    for name in TARGETS:
        path=ROOT/name
        if not path.is_file():
            raise FileNotFoundError(path)
        result=reframe(path, margin=.15 if '/objects/' in name else .12)
        if result:
            results.append(result)
            print(json.dumps(result))
    print(f'Corrected {len(results)} concept images')
    if __import__('os').environ.get('GITHUB_STEP_SUMMARY'):
        with open(__import__('os').environ['GITHUB_STEP_SUMMARY'],'a') as out:
            out.write('## Framing corrections\n'+''.join('- '+r['path']+' (scale '+str(r['scale'])+')\n' for r in results))
if __name__=='__main__':
    main()
