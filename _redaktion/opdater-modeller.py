"""Hent model-ID'er uden generering. Bevar sidste gode liste ved fejl."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent


def hent(udbyder, key, request=urlopen):
    models, token, seen = set(), '', set()
    while True:
        if udbyder == 'DeepSeek':
            url, headers = 'https://api.deepseek.com/models', {'Authorization': 'Bearer ' + key}
        else:
            url = 'https://generativelanguage.googleapis.com/v1beta/models?' + urlencode({'pageSize': 100, 'pageToken': token})
            headers = {'x-goog-api-key': key}
        with request(Request(url, headers=headers), timeout=30) as response:
            data = json.load(response)
        rows = data.get('data' if udbyder == 'DeepSeek' else 'models')
        if not isinstance(rows, list):
            raise ValueError('Ugyldigt modelsvar')
        for row in rows:
            name = row.get('id', '') if udbyder == 'DeepSeek' else row.get('name', '').removeprefix('models/')
            if udbyder == 'DeepSeek' and name.startswith('deepseek') or udbyder == 'Gemini' and name.startswith('gemini') and 'generateContent' in row.get('supportedGenerationMethods', []):
                models.add(name)
        token = data.get('nextPageToken') if udbyder == 'Gemini' else None
        if not token:
            break
        if token in seen:
            raise ValueError('Gentaget side')
        seen.add(token)
    if not models:
        raise ValueError('Tom modelliste')
    return sorted(models)


def main():
    target = ROOT / 'data/modeller.json'
    try:
        data = json.loads(target.read_text())
    except (OSError, ValueError):
        data = {'udbydere': {}}
    now = datetime.now(timezone.utc).isoformat()
    for name, env in [('DeepSeek', 'DEEPSEEK_API_KEY'), ('Gemini', 'GEMINI_API_KEY')]:
        previous = data['udbydere'].get(name, {})
        try:
            key = os.environ.get(env)
            if not key:
                raise ValueError('Mangler nøgle')
            data['udbydere'][name] = {'opdateret': now, 'status': 'Hentet', 'modeller': hent(name, key)}
        except Exception:
            # Ingen rå API-fejl eller credentials i offentlige filer.
            data['udbydere'][name] = {**previous, 'forsog': now, 'status': 'Kunne ikke hente; kontrollér API-adgang', 'modeller': previous.get('modeller', [])}
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
