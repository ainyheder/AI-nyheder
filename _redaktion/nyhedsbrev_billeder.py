"""FLUX → BiRefNet → gennemsigtig PNG → Buttondown. Højst tre motiver pr. brev."""
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
MAX_IMAGES = 3


def validate_plan(draft):
    plan = draft.get('illustrationer', [])
    if not isinstance(plan, list) or len(plan) > MAX_IMAGES:
        raise ValueError('Vælg højst tre illustrationer til brevet')
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
    def __init__(self, stage, returncode, error_type, diagnostics=None):
        self.details = {'trin': stage, 'returkode': returncode, 'fejltype': error_type}
        for key in ('http_status', 'errno'):
            value = (diagnostics or {}).get(key)
            if type(value) is int:
                self.details[key] = value
        super().__init__(json.dumps(self.details, ensure_ascii=False))


def cutout_failure(status_file, returncode, stdout='', stderr='', timed_out=False):
    """Læs kun kontrollerede metadata; send aldrig hele underprocessens log videre."""
    try:
        status = json.loads(status_file.read_text())
        if not isinstance(status, dict):
            status = {}
    except (OSError, ValueError):
        status = {}
    stdout = stdout.decode('utf-8', errors='replace') if isinstance(stdout, bytes) else (stdout or '')
    stderr = stderr.decode('utf-8', errors='replace') if isinstance(stderr, bytes) else (stderr or '')
    stages = re.findall(r'CUTOUT_STAGE=([a-z]+)\b', stdout)
    errors = re.findall(r'CUTOUT_ERROR=([A-Za-z_][A-Za-z0-9_]{0,79})\b', stderr)
    stage = status.get('trin', '')
    if not isinstance(stage, str) or not re.fullmatch(r'[a-z]{1,40}', stage):
        stage = stages[-1] if stages else 'start'
    error_type = status.get('fejltype', '')
    if not isinstance(error_type, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}', error_type):
        error_type = errors[-1] if errors else 'ProcesAfbrudt'
    return CutoutError(stage, returncode, 'TimeoutExpired' if timed_out else error_type, status)


def cutout_png(raw, timeout=180):
    from PIL import Image
    from _redaktion.fritlaeg_billede import kontroller_maske
    with tempfile.TemporaryDirectory(prefix='ai-newsletter-image-') as folder:
        original = Path(folder) / 'original.png'
        original.write_bytes(raw)
        cutout = Path(folder) / 'cutout.webp'
        status_file = Path(folder) / 'status.json'
        try:
            result = subprocess.run([sys.executable, str(ROOT / '_redaktion/fritlaeg_billede.py'),
                                     str(original), str(cutout), '--status-fil', str(status_file)],
                                    cwd=folder, env={**os.environ, 'OMP_NUM_THREADS': '2'},
                                    capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise cutout_failure(status_file, None, exc.stdout, exc.stderr, timed_out=True) from None
        if result.returncode:
            raise cutout_failure(status_file, result.returncode, result.stdout, result.stderr)
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
    raw = crawler.lav_flux_billede(crawler.billedprompt(motif, prompt))
    return cutout_png(raw)


def prepare(entry, config, api, save, generator=generate_png):
    """Checkpoint før generering. Et afbrudt motiv genbetales ikke automatisk."""
    plan = validate_plan(entry['draft'])
    settings = config.get('billeder', {})
    if not settings.get('aktiv', False) or not plan:
        return []
    budget = settings.get('maks_pr_brev', MAX_IMAGES)
    if type(budget) is not int or not 0 <= budget <= MAX_IMAGES:
        raise ValueError('Billedbudgettet skal være 0, 1, 2 eller 3')
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
        from importlib.metadata import version
        from PIL import Image, ImageDraw
        print('BiRefNet-værktøjer: ' + ', '.join(
            name + '=' + version(name) for name in ('rembg', 'onnxruntime', 'pooch', 'numpy')), flush=True)
        # Teknisk prøvefigur: ingen AI-generering, og filen bruges aldrig i brevet.
        sample = Image.new('RGB', (640, 480), 'white')
        ImageDraw.Draw(sample).ellipse((160, 70, 480, 410), fill='#167aa5')
        raw = io.BytesIO(); sample.save(raw, 'PNG')
        try:
            # En kold cache kan kræve næsten 1 GB download. Betalte billeder
            # bruger bagefter den kontrollerede cache og det normale 180s-loft.
            png = cutout_png(raw.getvalue(), timeout=600)
        except CutoutError as exc:
            print('Fritlægningskontrol fejlede: ' + str(exc))
            sys.exit(1)
        print('BiRefNet-kontrol bestået: gennemsigtig PNG, ' + str(len(png)) + ' bytes. Ingen billedkøb eller mail.')
    else:
        print('Illustrationer er slået fra; fritlægningskontrol springes over.')
