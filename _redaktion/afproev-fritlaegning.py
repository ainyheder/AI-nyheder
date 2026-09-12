"""Lokal BiRefNet-prøve på kopier; ændrer ikke artikler eller originalbilleder.

Kræver rembg[cpu]==2.0.84. Modelvægte hentes ved første kørsel.
Kør med Python fra miljøet, hvor rembg er installeret.
"""
import argparse
import html
import json
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('billeder', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from PIL import Image
    from rembg import new_session, remove
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    session = new_session('birefnet-general', providers=['CPUExecutionProvider'])
    print(f'Model klar efter {time.monotonic()-started:.1f} sek.', flush=True)
    cards, results = [], []
    for source in args.billeder:
        started = time.monotonic()
        with Image.open(source) as original:
            output = remove(original.convert('RGB'), session=session).convert('RGBA')
            original.convert('RGB').save(args.output / (source.stem+'-original.jpg'), quality=90)
        dest = args.output / (source.stem+'.webp')
        output.save(dest, 'WEBP', quality=92, method=6)
        alpha = output.getchannel('A')
        counts = alpha.histogram()
        result = {'source':source.name, 'model':'birefnet-general', 'seconds':round(time.monotonic()-started,1),
                  'transparent_percent':round(100*sum(counts[:10])/(output.width*output.height),1), 'bytes':dest.stat().st_size}
        results.append(result)
        print(json.dumps(result), flush=True)
        name = html.escape(source.stem)
        cards.append(f'<section><div class="sample"><img src="{name}-original.jpg"><p>Original</p></div><div class="sample dark"><img src="{name}.webp"><p>Fritlagt · mørkt kort</p></div><div class="sample lime"><img src="{name}.webp"><p>Fritlagt · limekort</p></div></section>')
    (args.output/'resultater.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    (args.output/'index.html').write_text('''<!doctype html><html lang="da"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BiRefNet · billedprøve</title><style>body{margin:0;padding:24px;background:#0c0e12;color:#f2f3f5;font:16px system-ui}h1{font-size:24px}section{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0}.sample{border-radius:16px;overflow:hidden;background:#242832}.dark{background:#171a21}.lime{background:#d5ff5f;color:#171a21}img{display:block;width:100%;aspect-ratio:16/9;object-fit:contain}p{padding:0 16px}@media(max-width:650px){body{padding:12px}section{grid-template-columns:1fr}}</style><h1>Samme motiv — uden billedkassen</h1><p>BiRefNet-prøve på eksisterende billeder. Originalerne er bevaret.</p>'''+''.join(cards))


if __name__ == '__main__':
    main()
