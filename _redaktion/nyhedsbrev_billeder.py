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


def generate_png(motif):
    import crawler
    from PIL import Image
    from _redaktion.fritlaeg_billede import kontroller_maske
    prompt = (ROOT / 'opsaetning/nyhedsbrev-billedprompt.md').read_text()
    raw = crawler.lav_flux_billede(prompt + '\n\nSUBJECT DATA:\n' + json.dumps({'motif': motif}, ensure_ascii=False))
    with tempfile.TemporaryDirectory(prefix='ai-newsletter-image-') as folder:
        original = Path(folder) / 'original.png'
        original.write_bytes(raw)
        cutout = Path(folder) / 'cutout.webp'
        subprocess.run([sys.executable, str(ROOT / '_redaktion/fritlaeg_billede.py'), str(original), str(cutout)],
                       cwd=folder, env={**os.environ, 'OMP_NUM_THREADS': '2'},
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=180)
        with Image.open(cutout) as image:
            image = image.convert('RGBA')
            kontroller_maske(image)
            image.thumbnail((560, 420), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, 'PNG', optimize=True)
    # Mailen får aldrig den mørke original som skjult fallback.
    return output.getvalue()


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
                print('Nyhedsbrevsillustration udeladt: ' + type(exc).__name__)
            save()
        if record['status'] == 'klar':
            ready.append({'placering': spec['placering'], 'url': public_image_url(record['url']), 'alt': record['alt']})
    return ready
