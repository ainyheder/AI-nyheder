"""FLUX → BiRefNet → gennemsigtig PNG → Buttondown. Højst to motiver pr. brev."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MODEL = '@cf/black-forest-labs/flux-2-klein-4b'


def validate_plan(draft):
    plan = draft.get('illustrationer', [])
    if not isinstance(plan, list) or len(plan) > 2:
        raise ValueError('Vælg højst to illustrationer til brevet')
    headings = re.findall(r'^## (.+)$', draft['brev_markdown'], re.M)
    positions = set()
    for item in plan:
        if not isinstance(item, dict) or set(item) != {'placering', 'motiv', 'alt'}:
            raise ValueError('Et billedmotiv skal have placering, motiv og alt-tekst')
        if any(not isinstance(item.get(k), str) or not item[k].strip() for k in item):
            raise ValueError('Ufuldstændigt billedmotiv')
        position = item['placering']
        if position not in ['intro', *headings] or position in positions or headings.count(position) > 1:
            raise ValueError('Billedet skal knyttes til intro eller én entydig mellemoverskrift')
        if len(item['motiv']) > 500 or len(item['alt']) > 180:
            raise ValueError('Billedbeskrivelsen er for lang')
        if not item['alt'].startswith('AI-illustration:'):
            raise ValueError('Alt-teksten skal angive AI-illustration')
        positions.add(position)
    return plan


def public_image_url(url):
    if not isinstance(url, str):
        raise ValueError('Billedadressen mangler')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in url):
        raise ValueError('Billedet skal have en offentlig HTTPS-adresse')
    return url


class CutoutError(RuntimeError):
    def __init__(self, stage, returncode, error_type):
        self.details = {'trin': stage, 'returkode': returncode, 'fejltype': error_type}
        super().__init__(json.dumps(self.details, ensure_ascii=False))


def cutout_png(raw):
    from PIL import Image
    from _redaktion.fritlaeg_billede import kontroller_maske
    with tempfile.TemporaryDirectory(prefix='ai-newsletter-image-') as folder:
        original = Path(folder) / 'original.png'
        original.write_bytes(raw)
        cutout = Path(folder) / 'cutout.webp'
        result = subprocess.run([sys.executable, str(ROOT / '_redaktion/fritlaeg_billede.py'), str(original), str(cutout)],
                                cwd=folder, env={**os.environ, 'OMP_NUM_THREADS': '2'},
                                capture_output=True, text=True, timeout=180)
        if result.returncode:
            stages = re.findall(r'^CUTOUT_STAGE=([a-z]+)$', result.stdout, re.M)
            errors = re.findall(r'^CUTOUT_ERROR=([A-Za-z]+)$', result.stderr, re.M)
            raise CutoutError(stages[-1] if stages else 'start', result.returncode,
                              errors[-1] if errors else 'ProcesAfbrudt')
        with Image.open(cutout) as image:
            image = image.convert('RGBA')
            kontroller_maske(image)
            image.thumbnail((560, 420), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, 'PNG', optimize=True)
    # Mailen får aldrig den mørke original som skjult fallback.
    return output.getvalue()


def generate_png(motif):
    import crawler
    prompt = (ROOT / 'opsaetning/nyhedsbrev-billedprompt.md').read_text()
    raw = crawler.lav_flux_billede(prompt + '\n\nSUBJECT DATA:\n' + json.dumps({'motif': motif}, ensure_ascii=False))
    return cutout_png(raw)


def prepare(entry, config, api, save, generator=generate_png):
    """Checkpoint før generering. Et afbrudt motiv genbetales ikke automatisk."""
    plan = validate_plan(entry['draft'])
    settings = config.get('billeder', {})
    if not settings.get('aktiv', False) or not plan:
        return []
    budget = settings.get('maks_pr_brev', 2)
    if type(budget) is not int or not 0 <= budget <= 2:
        raise ValueError('Billedbudgettet skal være 0, 1 eller 2')
    existing = entry.setdefault('billeder', {})
    ready = []
    style = (ROOT / 'opsaetning/nyhedsbrev-billedprompt.md').read_text()
    for spec in plan[:budget]:
        key = hashlib.sha256((entry['url'] + MODEL + style + json.dumps(spec, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()[:24]
        record = existing.get(key)
        if record is None:
            if len(existing) >= budget:
                continue  # Et nyt prompt eller en ændret stil må ikke nulstille brevets budget.
            record = existing[key] = {'status': 'genererer', 'placering': spec['placering']}
            save()
            try:
                png = generator(spec['motiv'])
                remote = api.upload_image(png, key)
                record.update(status='klar', url=public_image_url(remote['image']), alt=spec['alt'], image_id=remote.get('id'))
            except Exception as exc:
                # Kun fejltype: udbydernes svar kan indeholde request-data.
                record.update(status='udeladt', fejl=type(exc).__name__)
                if isinstance(exc, CutoutError):
                    record['detaljer'] = exc.details
                print('Nyhedsbrevsillustration udeladt: ' + type(exc).__name__)
                if isinstance(exc, CutoutError):
                    print(str(exc))
            save()
        if record['status'] == 'klar':
            ready.append({'placering': spec['placering'], 'url': public_image_url(record['url']), 'alt': record['alt']})
    return ready


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Kontrollér fritlægning uden billedkøb eller mail.')
    parser.add_argument('--check-engine', action='store_true', required=True)
    parser.parse_args()
    config = json.loads((ROOT / 'opsaetning/nyhedsbrev.json').read_text())
    if config.get('billeder', {}).get('aktiv', False):
        from PIL import Image, ImageDraw
        # Teknisk prøvefigur: ingen AI-generering, og filen bruges aldrig i brevet.
        sample = Image.new('RGB', (640, 480), 'white')
        ImageDraw.Draw(sample).ellipse((160, 70, 480, 410), fill='#167aa5')
        raw = io.BytesIO(); sample.save(raw, 'PNG')
        try:
            png = cutout_png(raw.getvalue())
        except CutoutError as exc:
            print('Fritlægningskontrol fejlede: ' + str(exc))
            sys.exit(1)
        print('BiRefNet-kontrol bestået: gennemsigtig PNG, ' + str(len(png)) + ' bytes. Ingen billedkøb eller mail.')
    else:
        print('Illustrationer er slået fra; fritlægningskontrol springes over.')
