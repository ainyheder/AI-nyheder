"""Læs daterede nyhedsoversigter uden RSS, fx Anthropic og xAI.

Kun links med både overskrift og publiceringsdato på kildens eget domæne.
Ingen browser, eksterne feed-tjenester eller ekstra artikelkald er nødvendige.
"""
import html
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


class _Links(HTMLParser):
    """Bevar også en featured-artikel med indlejrede links til samme adresse."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.aktive = []
        self.links = []
        self.skjult = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skjult += 1
        if self.skjult:
            return
        for _, dele in self.aktive:
            dele.append(self.get_starttag_text())
        if tag == "a":
            self.aktive.append((dict(attrs).get("href", ""), []))

    def handle_endtag(self, tag):
        if self.skjult:
            if tag in ("script", "style", "noscript"):
                self.skjult -= 1
            return
        for _, dele in self.aktive:
            dele.append(f"</{tag}>")
        if tag == "a" and self.aktive:
            link, dele = self.aktive.pop()
            self.links.append((link, "".join(dele)))

    def handle_data(self, data):
        if not self.skjult:
            for _, dele in self.aktive:
                dele.append(html.escape(data))


def _tekst(markup, max_laengde=400):
    tekst = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()
    return tekst if len(tekst) <= max_laengde else tekst[:max_laengde].rsplit(" ", 1)[0] + "…"


_MAANEDER = {navn: n for n, navn in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
_DATO = re.compile(r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
                   r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
                   r"Dec(?:ember)?)\s+(\d{1,2}),?\s+(\d{4})\b", re.I)


def _dato(markup):
    time = re.search(r"<time\b([^>]*)>(.*?)</time>", markup, re.I | re.S)
    if time:
        attr = re.search(r"\bdatetime\s*=\s*['\"]([^'\"]+)['\"]", time[1], re.I)
        if attr:
            try:
                dato = datetime.fromisoformat(html.unescape(attr[1]).replace("Z", "+00:00"))
                return dato.replace(tzinfo=timezone.utc) if dato.tzinfo is None else dato.astimezone(timezone.utc)
            except ValueError:
                pass
    # xAI har datoen som almindelig tekst; Anthropic bruger <time> uden datetime.
    match = _DATO.search(_tekst(time[2] if time else markup, 20000))
    if match:
        try:
            return datetime(int(match[3]), _MAANEDER[match[1][:3].lower()], int(match[2]), tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def parse_nyhedsoversigt(data: bytes, base_url: str) -> list[dict]:
    parser = _Links()
    parser.feed(data.decode("utf-8", errors="replace"))
    parser.close()
    artikler = {}
    for href, markup in parser.links:
        if not href or href.startswith("#"):
            continue
        link = urljoin(base_url, href)
        url = urlsplit(link)
        if url.scheme not in ("https", "http") or url.netloc != urlsplit(base_url).netloc:
            continue
        heading = re.search(r"<h([1-6])\b[^>]*>(.*?)</h\1>", markup, re.I | re.S)
        if not heading:
            # Anthropic bruger et title-span i den kronologiske liste.
            heading = re.search(r"<(span)\b[^>]*class=['\"][^'\"]*__title\b[^'\"]*['\"][^>]*>(.*?)</span>",
                                markup, re.I | re.S)
        titel = _tekst(heading[2], 200) if heading else ""
        dato = _dato(markup)
        if not titel or dato is None:
            continue
        resume = re.search(r"<p\b[^>]*>(.*?)</p>", markup, re.I | re.S)
        artikel = {"titel": titel, "link": link, "resume": _tekst(resume[1]) if resume else "", "dato": dato}
        # Featured-kort og liste kan pege på samme artikel. Behold den fyldigste.
        if link not in artikler or len(artikel["resume"]) > len(artikler[link]["resume"]):
            artikler[link] = artikel
    return sorted(artikler.values(), key=lambda a: (a["dato"], a["link"]), reverse=True)
