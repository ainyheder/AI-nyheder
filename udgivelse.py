"""Udgiv kun læsbare, kontrollerede artikler; bevar resten til næste kørsel."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def tekstproblemer(a):
    problemer = []
    if not isinstance(a.get('rubrik'), str) or not a['rubrik'].strip():
        problemer.append('Mangler dansk overskrift')
    if not isinstance(a.get('resume_da'), str) or not a['resume_da'].strip():
        problemer.append('Mangler dansk indledning')
    sektioner = a.get('sektioner')
    if not isinstance(sektioner, list):
        sektioner = []
    brugbare = [s for s in sektioner if isinstance(s, dict)
                and isinstance(s.get('overskrift'), str) and s['overskrift'].strip()
                and isinstance(s.get('tekst'), str) and len(s['tekst'].strip()) >= 40]
    if len(brugbare) != len(sektioner) or len(brugbare) < 2 or sum(len(s['tekst'].split()) for s in brugbare) < 80:
        problemer.append('Mangler en færdig artikel med mindst to udfoldede afsnit')
    normal = [re.sub(r'\W+', ' ', s['tekst']).strip().casefold() for s in brugbare]
    if len(normal) != len(set(normal)):
        problemer.append('Artiklen gentager det samme afsnit')
    tekst = ' '.join(str(a.get(k) or '') for k in ('rubrik', 'resume_da', 'brief'))
    tekst += ' ' + ' '.join(s['tekst'] for s in brugbare)
    if re.search(r'(?:resum[eé](?:et)?|genfortælling(?:en)?|artikeltekst(?:en)?)\s+(?:mangler|kommer senere)|foreløbig kun et kort resum[eé]|\bTODO\b', tekst, re.I):
        problemer.append('Artiklen indeholder en ufærdig pladsholder')
    return problemer


def klar(a):
    # brief_instruks blev kun gemt efter godkendt kildekontrol i den gamle kode.
    publicering = a.get('publicering')
    if isinstance(publicering, dict) and publicering.get('status') not in (None, 'godkendt'):
        return False
    godkendt = isinstance(publicering, dict) and publicering.get('status') == 'godkendt'
    return bool(not a.get('kun_aktuel') and not tekstproblemer(a)
                and (godkendt or a.get('brief_instruks')))


def laes(path):
    path = Path(path)
    if not path.exists():
        return {'kladder': [], 'historik': []}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or any(not isinstance(data.get(k), list) for k in ('kladder', 'historik')):
        raise ValueError('Udgivelseshistorikken er ugyldig; stop før den overskrives')
    return data


def gem(path, artikler, historik, nu=None):
    nu = nu or datetime.now(timezone.utc)
    def tidspunkt(a):
        try:
            d = datetime.fromisoformat(str(a.get('dato')).replace('Z', '+00:00'))
            return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
        except (ValueError, TypeError):
            return nu
    faerdige = [a for a in artikler if klar(a)]
    arkiv = {a['link']: a for a in historik if a.get('link') and klar(a)
             and tidspunkt(a) >= nu - timedelta(days=90)}
    arkiv.update({a['link']: a for a in faerdige})
    dubletter = {k.get('link') for a in arkiv.values() for k in a.get('andre', []) if isinstance(k, dict)}
    arkiv = {k: a for k, a in arkiv.items() if k not in dubletter}
    kladder = [{**a, 'afventer': tekstproblemer(a) or ['Afventer redaktørens kildekontrol']}
               for a in artikler if not klar(a) and not a.get('kun_aktuel')]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps({'opdateret': nu.isoformat(), 'kladder': kladder,
                               'historik': list(arkiv.values())}, ensure_ascii=False, indent=2, default=str) + '\n')
    temp.replace(path)
    return faerdige
