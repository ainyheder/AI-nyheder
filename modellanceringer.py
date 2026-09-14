"""En kronologisk modeloversigt af redaktørens færdige artikler."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import redaktion
import udgivelse


def oversigt(artikler, nu=None):
    nu = nu or datetime.now(timezone.utc)
    graense = nu - timedelta(days=90)
    kandidater = [a for a in artikler if udgivelse.klar(a) and redaktion.model_lancering(a)
                  and redaktion.dato(a) and graense <= redaktion.dato(a) <= nu
                  and re.fullmatch(r'artikel/[a-zA-Z0-9_-]+\.html', str(a.get('side') or ''))]
    # Omtaler af samme hændelse optager kun én plads i tidslinjen.
    kandidater = redaktion.unikke_historier(kandidater)
    kandidater.sort(key=redaktion.dato, reverse=True)
    return {'opdateret': nu.isoformat(), 'lanceringer': [{
        'rubrik': a['rubrik'], 'resume': a['resume_da'], 'side': a['side'],
        'dato': redaktion.dato(a).isoformat(),
        'billede': a.get('billede') or '',
        'emne': (redaktion.vurdering(a) or {}).get('emne') or '',
    } for a in kandidater]}


def gem(path, artikler, nu=None):
    data = oversigt(artikler, nu)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)
    return data
