"""Officielle, daterede xAI API-opdateringer. Kildetekst holdes kun i hukommelsen."""
import html
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

MATERIAL = {}
MONTHS = {name: i for i, name in enumerate(('January','February','March','April','May','June','July','August','September','October','November','December'),1)}


def er_release_url(url):
    u = urlsplit(url)
    return u.scheme == 'https' and u.hostname == 'docs.x.ai' and u.path.rstrip('/') == '/developers/release-notes'


def tekst(markup):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', markup))).strip()


def parse(data, base):
    """Årstal kommer fra dokumentets metadata og eksplicitte månedsoverskrifter."""
    if not er_release_url(base):
        raise ValueError('Ikke xAI release notes')
    page = data.decode('utf-8', errors='replace')
    modified = None
    for block in re.findall(r'<script\b[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>',page,re.I|re.S):
        try:
            metadata = json.loads(block)
            if isinstance(metadata,dict) and isinstance(metadata.get('dateModified'),str):
                modified = datetime.fromisoformat(metadata['dateModified'].replace('Z','+00:00'))
        except (ValueError,TypeError):
            pass
    if modified is None:
        raise ValueError('Releaseoversigten mangler verificerbart årstal')
    page = re.sub(r'<(script|style|noscript)\b[^>]*>.*?</\1>','',page,flags=re.I|re.S)
    start = re.search(r'<h1\b[^>]*id=[\'"]release-notes(?:-\d+)?[\'"][^>]*>',page,re.I)
    if not start:
        raise ValueError('Releaseoversigten har ændret format')
    page = page[start.end():]
    months = list(re.finditer(r'<h2\b[^>]*>.*?</h2>',page,re.I|re.S))
    year, previous_month = modified.year, modified.month
    rows = []
    for i, month in enumerate(months):
        label = tekst(month.group())
        match = re.fullmatch(r'([A-Za-z]+)(?:\s+(\d{4}))?',label)
        if not match or match[1] not in MONTHS:
            continue
        number = MONTHS[match[1]]
        year = int(match[2]) if match[2] else year - int(number > previous_month)
        previous_month = number
        body = page[month.end():months[i+1].start() if i+1<len(months) else len(page)]
        headings = list(re.finditer(r'<h3\b[^>]*id=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</h3>',body,re.I|re.S))
        current_date = None
        for j, heading in enumerate(headings):
            prefix = body[headings[j-1].end() if j else 0:heading.start()]
            dates = re.findall(r'<div\b[^>]*class=[\'"]relative[\'"][^>]*>\s*([A-Za-z]+)\s+(\d{1,2})\s*<span\b',prefix,re.I)
            if dates:
                last_date = dates[-1]
            elif current_date:
                # Flere opdateringer kan dele en enkelt synlig dato.
                last_date = current_date
            else:
                continue
            current_date = last_date
            if last_date[0] not in MONTHS or MONTHS[last_date[0]] != number:
                continue
            try:
                date = datetime(year,number,int(last_date[1]),tzinfo=timezone.utc)
            except ValueError:
                continue
            content = body[heading.end():headings[j+1].start() if j+1<len(headings) else len(body)]
            paragraphs = [tekst(p) for p in re.findall(r'<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>',content,re.I|re.S)]
            material = '\n\n'.join(p for p in paragraphs if p)
            if not material:
                continue
            title = tekst(heading[2])
            link = base.split('#')[0] + '#' + html.unescape(heading[1])
            MATERIAL[link] = title + '\n\n' + material
            rows.append({'titel':title[:200],'link':link,'resume':material[:400],'dato':date})
    if not rows:
        raise ValueError('Releaseoversigten gav ingen daterede opdateringer')
    return sorted(rows,key=lambda a:(a['dato'],a['link']),reverse=True)
