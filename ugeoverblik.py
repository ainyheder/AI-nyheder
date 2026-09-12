"""Ugens udvalg og visning. Ingen netværkskald eller udsendelser."""
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from string import Template
from zoneinfo import ZoneInfo
import re
import json
import hashlib
import redaktion

VERSION = 3
MAANEDER = ('jan.', 'feb.', 'mar.', 'apr.', 'maj', 'jun.', 'jul.', 'aug.', 'sep.', 'okt.', 'nov.', 'dec.')


def kandidater(artikler, nu, antal=None):
    """Alle læsbare kandidater fra de syv afsluttede dage; dagens stof er udeladt."""
    start, slut = redaktion.ugeperiode(nu)
    friske = [a for a in artikler if a.get('rubrik') and redaktion.dato(a)
              and start <= redaktion.dato(a) < slut
              and not redaktion.reklame(a) and redaktion.grundscore(a) >= 32
              and not (redaktion.vurdering(a) and (redaktion.vurdering(a)['dokumentation'] <= 1
                                                   or redaktion.vurdering(a).get('type') == 'rygte'))]
    def vaegt(a):
        return redaktion.grundscore(a) + (22 if redaktion.model_lancering(a) else 0)
    unikke = redaktion.unikke_historier(sorted(friske, key=lambda a: (vaegt(a), a["link"]), reverse=True))
    # Et bredt beslutningsgrundlag; AI'en bestemmer det endelige udvalg og rækkefølge.
    return unikke[:antal]


def materiale(artikler):
    return [{'link': a['link'], 'rubrik': a['rubrik'], 'dato': a.get('dato', ''),
             'resume': a.get('resume_da', ''), 'kategori': a.get('kategori', ''),
             'model_lancering': redaktion.model_lancering(a),
             'artikeltekst': ('\n'.join(str(s.get('tekst', '')) for s in (a.get('sektioner') or [])
                                        if isinstance(s, dict)) or (a.get('brief') or ''))[:3600],
             'betydning': a.get('betydning', ''), 'detaljer': (a.get('detaljer') or [])[:6],
             'andre_kilder': a.get('andre', [])} for a in artikler]


def kontroller_svar(svar, artikler):
    if not isinstance(svar, dict):
        raise ValueError('Svaret skal være ét JSON-objekt')
    for navn, minimum, maksimum in [('rubrik', 5, 120), ('indledning', 15, 500), ('tendens', 0, 800)]:
        value = svar.get(navn, '')
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maksimum:
            raise ValueError(f'{navn} skal være tekst på {minimum}-{maksimum} tegn')
    historier = svar.get('historier')
    minimum = min(3, len(artikler))
    if not isinstance(historier, list) or not historier or not minimum <= len(historier) <= 6:
        raise ValueError(f'Vælg {minimum}-6 forskellige historier')
    opslag = {a['link']: a for a in artikler}
    valgte, resultater = [], []
    for h in historier:
        if not isinstance(h, dict) or not isinstance(h.get('link'), str) or h['link'] not in opslag:
            raise ValueError('Hver historie skal bruge et præcist link fra kandidatlisten')
        for felt, minimum, maksimum in [('overskrift', 5, 130), ('tekst', 40, 900)]:
            if not isinstance(h.get(felt), str) or not minimum <= len(h[felt].strip()) <= maksimum:
                raise ValueError(f'Historiens {felt} skal være {minimum}-{maksimum} tegn')
        a = opslag[h['link']]
        valgte.append(a)
        resultater.append({**h, 'link': a['link'], 'kategori': a.get('kategori', ''),
                           'billede': a.get('billede', ''), 'dato': a.get('dato', ''),
                           'andre': a.get('andre', []), 'titel': a.get('titel', ''),
                           'rubrik': a.get('rubrik', ''), 'resume_da': a.get('resume_da', ''),
                           'artikel_signatur': signatur([a])})
    if len(redaktion.unikke_historier(valgte)) != len(valgte):
        raise ValueError('Samme historie er valgt flere gange; saml omtalerne i ét punkt')
    overblik = svar.get('overblik')
    if not isinstance(overblik, list) or not 2 <= len(overblik) <= 4:
        raise ValueError('Skriv den overordnede historie i 2-4 sammenhængende afsnit')
    valgte_links = {a['link'] for a in valgte}
    brugte_links = set()
    for afsnit in overblik:
        if not isinstance(afsnit, dict) or not isinstance(afsnit.get('tekst'), str) or not 80 <= len(afsnit['tekst'].strip()) <= 1500:
            raise ValueError('Hvert overbliksafsnit skal have 80-1500 tegn')
        links = afsnit.get('links')
        if not isinstance(links, list) or not links or any(not isinstance(k, str) or k not in valgte_links for k in links):
            raise ValueError('Overblikkets afsnit skal bygge på links til de valgte historier')
        brugte_links.update(links)
    if brugte_links != valgte_links:
        raise ValueError('Alle valgte historier skal have en rolle i det overordnede overblik')
    return {**svar, 'historier': resultater, 'version': VERSION}


def opfrisk(d, artikler):
    """Bevar ugens tekst, men følg sammenlagte kilder og nyeste illustration."""
    opslag = {}
    for a in artikler:
        for k in [a] + (a.get('andre') or []):
            if isinstance(k, dict) and k.get('link'):
                opslag.setdefault(k['link'], a)
    historier = []
    for h in d.get('historier', []):
        if not isinstance(h, dict) or not h.get('link'):
            continue
        a = opslag.get(h['link'])
        ny = dict(h)
        if a:
            for felt in ('link', 'dato', 'kategori', 'billede', 'andre', 'titel', 'rubrik', 'resume_da'):
                ny[felt] = a.get(felt, '' if felt != 'andre' else [])
        ny.setdefault('rubrik', ny.get('overskrift', ''))
        historier.append(ny)
    unikke = redaktion.unikke_historier(historier)
    # En gammel indledning kan beskrive et udvalg, der ikke længere findes.
    aendret = len(unikke) != len(historier)
    return {**d, 'version': VERSION, 'historier': unikke,
            **({'rubrik': 'Ugens vigtigste AI-nyheder',
                'indledning': 'Her er ugens udvalgte historier samlet på ét sted.',
                'tendens': '', 'overblik': []} if aendret else {})}


def signatur(artikler, prompt=''):
    # Billedændringer og klokkeslættet udløser ikke en ny redaktionel tekst.
    data = {'version': VERSION, 'prompt': prompt, 'artikler': materiale(artikler)}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def reserve(artikler, gammel=None):
    """Vis aktuelle kilder ved AI-fejl; opfind aldrig en erstatning for fortællingen."""
    gammel = gammel or {}
    gamle = {h.get('link'): h for h in gammel.get('historier', []) if isinstance(h, dict)}
    opslag = {a['link']: a for a in artikler}
    bevarede = []
    for link, h in gamle.items():
        a = opslag.get(link)
        if a and h.get('artikel_signatur') == signatur([a]):
            bevarede.append(h)
    # Bevar et tidligere godkendt valg, hvis alle kilder stadig er inden for perioden.
    if bevarede and len(bevarede) == len(gamle) and gammel.get('overblik'):
        return opfrisk(gammel, artikler)
    raekke = [opslag[h['link']] for h in bevarede]
    raekke += [a for a in artikler if a['link'] not in {b['link'] for b in raekke}]
    historier = [{**a, 'overskrift': a['rubrik'],
                  'tekst': a.get('resume_da') or a.get('resume') or '',
                  'artikel_signatur': signatur([a])} for a in raekke[:5]]
    return {'version': VERSION, 'metode': 'reserve',
            'rubrik': 'De seneste syv dages AI-nyheder',
            'indledning': ('Det samlede overblik er på vej. Her er historier fra perioden.' if historier
                           else 'Der er ingen tilgængelige historier fra de syv afsluttede dage før i dag.'),
            'historier': historier, 'overblik': [], 'tendens': ''}


def billede(h, root):
    sti = h.get('billede', '')
    if not isinstance(sti, str) or not re.fullmatch(r'data/img/[a-zA-Z0-9_.-]+\.(?:jpg|png|webp)', sti):
        return ''
    # Foretræk den fritlagte version, også for en ældre gemt JPG-sti.
    fritlagt = str(Path(sti).with_suffix('.webp'))
    if (root / fritlagt).is_file():
        return fritlagt
    return sti if (root / sti).is_file() else ''


def render(d, root, link_for):
    root = Path(root)
    dato = redaktion.dato({'dato': d.get('dato')}) or datetime.now(timezone.utc)
    start = redaktion.dato({'dato': d.get('periode_fra')}) or dato-timedelta(days=7)
    slut = redaktion.dato({'dato': d.get('periode_til')}) or dato
    # Den øvre grænse er eksklusiv: etiketten slutter i går, ikke i dag.
    zone = ZoneInfo('Europe/Copenhagen')
    start = start.astimezone(zone)
    slut = (slut-timedelta(microseconds=1)).astimezone(zone)
    def kortdato(dt): return f'{dt.day}. {MAANEDER[dt.month-1]}'
    periode = f'{kortdato(start)} – {kortdato(slut)} {slut.year}'
    historier = d.get('historier', [])
    overblik = ''.join('<p>'+escape(str(a.get('tekst', '')))+'</p>' for a in d.get('overblik', []) if isinstance(a, dict))
    fortaelling = ('<section class="week-narrative" aria-label="Det samlede overblik">'+overblik+'</section>') if overblik else ''
    kort = []
    for nr, h in enumerate(historier, 1):
        illustration = billede(h, root)
        img = (f'<img class="week-image" src="{escape(illustration)}" alt="" width="160" height="120" loading="lazy">'
               if illustration else '')
        led = link_for(h.get('link', ''))
        if led.startswith('https://ainyheder.com/'):
            led = led.removeprefix('https://ainyheder.com')
        kort.append(f'''<article class="week-story{' week-lead' if nr == 1 else ''}">
<div class="week-meta"><span>{escape(str(h.get('kategori') or 'AI-nyheder'))}</span><span class="week-number">{nr:02}</span></div>
<h2><a href="{escape(led, quote=True)}">{escape(str(h.get('overskrift', '')))}</a></h2>
<div class="week-summary">{img}<p>{escape(str(h.get('tekst', '')))}</p></div>
</article>''')
    tendens = str(d.get('tendens') or '').strip()
    afslutning = (f'<section class="week-outlook"><p class="eyebrow">Det er værd at følge</p><h2>Hvad sker der nu?</h2><p>{escape(tendens)}</p></section>' if tendens else '')
    share_img = billede(historier[0], root) if historier else ''
    if share_img.endswith('.webp') and (root / Path(share_img).with_suffix('.jpg')).is_file():
        share_img = str(Path(share_img).with_suffix('.jpg'))
    template = Template((root / '_redaktion/uge-skabelon.html').read_text(encoding='utf-8'))
    return template.substitute(title=escape(str(d.get('rubrik') or 'Ugens AI-overblik')),
                               intro=escape(str(d.get('indledning') or '')),
                               uge=escape(str(d.get('uge_nr', dato.isocalendar().week))),
                               periode=escape(periode),dato=escape(str(d.get('opdateret') or dato.isoformat())),
                               fortaelling=fortaelling,
                               dato_vis=escape(kortdato((redaktion.dato({'dato': d.get('opdateret')}) or dato).astimezone(zone))),kort='\n'.join(kort),tendens=afslutning,
                               share_image='https://ainyheder.com/'+(share_img or 'assets/og.png'))
