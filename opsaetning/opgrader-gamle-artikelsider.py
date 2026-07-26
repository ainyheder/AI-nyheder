#!/usr/bin/env python3
"""Efterudfylder struktureret data på artikelsider, crawleren ikke rører mere.

BAGGRUNDEN
Crawleren genskriver kun sider for artikler, der stadig ligger i
data/articles.json — og den beholder kun 30 dage (MAX_DAGE_GAMMEL). Sider for
ældre artikler bliver stående som "evigt indhold", men de fryses samtidig fast
på den skabelon, de havde den dag de faldt ud af vinduet. Enhver senere
forbedring af artikelskabelonen rammer altså kun de nyeste sider.

Da NewsArticle-schema blev tilføjet 25.07.2026, stod 23 af 102 sider uden.

Da NewsArticle-schema blev tilføjet 25.07.2026, manglede det på alle 102 sider.
De 79, der stadig lå i articles.json, ville crawleren selv have rettet ved næste
kørsel; de 23 øvrige ville aldrig få det.

HVAD DEN GØR
Læser hver side i artikel/, og hvis den mangler JSON-LD, bygges den ud fra de
oplysninger, siden selv bærer: og:title, meta description, og:image, canonical,
kickeren (kategori · kilde · dato) og det første kildelink. Er artikelbilledets
alt-tekst tom, udfyldes den med rubrikken — det oprindelige billedmotiv findes
ikke længere, men rubrikken er bedre end ingenting for en skærmlæser.

Rører kun artikelbilledet (<img class="top">), aldrig andre billeder: et
dekorativt billede SKAL have tomt alt efter WCAG, så en blind udfyldning af
alle alt="" ville være forkert, hvis skabelonen senere får et logo eller en
pynteillustration.

Rører ikke sider, der allerede har JSON-LD. Kan køres igen uden skade.

    python3 opsaetning/opgrader-gamle-artikelsider.py --toerloeb   # vis kun
    python3 opsaetning/opgrader-gamle-artikelsider.py              # skriv
"""
from __future__ import annotations

import html as html_mod
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROD = Path(__file__).resolve().parent.parent
ARTIKEL_MAPPE = ROD / "artikel"
SITE_URL = "https://ainyheder.com"


def _meta(h: str, attr: str, navn: str) -> str:
    """Henter indholdet af et meta-tag, uanset attributrækkefølge."""
    m = re.search(
        rf'<meta[^>]+{attr}=["\']{re.escape(navn)}["\'][^>]*content=["\']([^"\']*)',
        h, flags=re.I)
    if not m:
        m = re.search(
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*{attr}=["\']{re.escape(navn)}["\']',
            h, flags=re.I)
    return html_mod.unescape(m.group(1)) if m else ""


def _canonical(h: str) -> str:
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', h, flags=re.I)
    return m.group(1) if m else ""


def _titel(h: str) -> str:
    t = _meta(h, "property", "og:title")
    if t:
        return t
    m = re.search(r"<title>(.*?)</title>", h, flags=re.S | re.I)
    if not m:
        return ""
    # "AI-nyheder.com · Rubrikken" -> "Rubrikken"
    return html_mod.unescape(m.group(1)).split("·", 1)[-1].strip()


def _kicker(h: str) -> tuple[str, str, str]:
    """(kategori, kilde, dato) fra <div class="kicker">A · B · 2026-07-23</div>."""
    m = re.search(r'<div class="kicker">(.*?)</div>', h, flags=re.S)
    if not m:
        return "", "", ""
    dele = [html_mod.unescape(d).strip() for d in m.group(1).split("·")]
    dato = next((d for d in dele if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)), "")
    rest = [d for d in dele if d != dato]
    kategori = rest[0] if rest else ""
    kilde = rest[1] if len(rest) > 1 else ""
    return kategori, kilde, dato


def _kildelink(h: str) -> str:
    m = re.search(r'<a class="kilde" href="([^"]+)"', h)
    return html_mod.unescape(m.group(1)) if m else ""


def byg_jsonld(h: str) -> str | None:
    """JSON-LD udledt af sidens egne oplysninger. None hvis der er for lidt."""
    rubrik = _titel(h)
    url = _canonical(h)
    if not rubrik or not url:
        return None

    kategori, kilde, dato = _kicker(h)
    ld: dict = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": rubrik[:110],
        "description": _meta(h, "name", "description"),
        "url": url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "inLanguage": "da-DK",
        "isAccessibleForFree": True,
        "author": {"@type": "Organization", "name": "AI-nyheder", "url": SITE_URL},
        "publisher": {"@type": "Organization", "name": "AI-nyheder", "url": SITE_URL},
    }
    billede = _meta(h, "property", "og:image")
    # Billeder ryddes op efter 30 dage, mens siderne står. Peger og:image på en
    # fil, der ikke findes længere, skal den ikke gentages i structured data —
    # der giver den en "Image not found" i Search Console.
    if billede and "assets/og.png" not in billede:
        lokal = ROD / billede.split("ainyheder.com/", 1)[-1]
        if lokal.is_file():
            ld["image"] = billede
    if dato:
        # Kun datoen er bevaret på siden, ikke klokkeslættet. Middag dansk tid
        # er et neutralt gæt; offset udledes af datoen, så en genkørsel i
        # vinterhalvåret ikke skriver sommertid.
        try:
            from zoneinfo import ZoneInfo
            lokal_tid = datetime.fromisoformat(f"{dato}T12:00:00").replace(
                tzinfo=ZoneInfo("Europe/Copenhagen"))
            ld["datePublished"] = lokal_tid.isoformat()
        except Exception:
            ld["datePublished"] = f"{dato}T12:00:00+00:00"
    if kategori:
        ld["articleSection"] = kategori
    kilde_url = _kildelink(h)
    if kilde_url:
        ld["isBasedOn"] = kilde_url
    # < > & som JSON-unicode, så hverken "</script>" eller "<!--<script" i en
    # rubrik kan slippe ud af script-blokken. Samme greb som _jsonld() i
    # crawler.py — se begrundelsen dér.
    return (json.dumps(ld, ensure_ascii=False)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def opgrader(h: str) -> tuple[str, list[str]]:
    """Returnerer (ny html, liste over hvad der blev ændret)."""
    aendret: list[str] = []

    if "application/ld+json" not in h:
        jsonld = byg_jsonld(h)
        if jsonld:
            # samme placering som i crawlerens skabelon: lige før <style>
            ny = h.replace(
                "<style>",
                f'<script type="application/ld+json">{jsonld}</script>\n<style>',
                1)
            if ny != h:
                h = ny
                aendret.append("JSON-LD")

    # Kun artikelbilledet. Andre billeder kan være dekorative, og der er tomt
    # alt det rigtige efter WCAG.
    rubrik = html_mod.escape(_titel(h)[:180])
    if rubrik:
        # Erstatning som funktion, ikke som streng: en rubrik med "\" eller
        # "\g" ville ellers blive læst som en regex-backreference.
        ny, n = re.subn(r'(<img class="top"[^>]*?)alt=""',
                        lambda m: f'{m.group(1)}alt="{rubrik}"', h)
        if n:
            h = ny
            aendret.append(f"alt-tekst x{n}")

    return h, aendret


def main() -> int:
    toerloeb = "--toerloeb" in sys.argv or "--dry-run" in sys.argv
    if not ARTIKEL_MAPPE.is_dir():
        print(f"Fandt ikke {ARTIKEL_MAPPE}")
        return 1

    filer = sorted(ARTIKEL_MAPPE.glob("*.html"))
    rort = sprunget = mislykket = 0

    for f in filer:
        gammel = f.read_text(encoding="utf-8")
        ny, aendret = opgrader(gammel)
        if not aendret:
            sprunget += 1
            continue
        if "application/ld+json" not in ny:
            # For lidt på siden til at udlede JSON-LD. En alt-tekst-rettelse i
            # samme kørsel skal stadig gemmes, så den ikke tabes i stilhed.
            print(f"  ! {f.name}: JSON-LD kunne ikke udledes ({', '.join(aendret)})")
            mislykket += 1
        else:
            print(f"  {'(tørløb) ' if toerloeb else ''}{f.name}: {', '.join(aendret)}")
        if not toerloeb:
            f.write_text(ny, encoding="utf-8")
        rort += 1

    print(f"\n{len(filer)} sider: {rort} opgraderet, {sprunget} var i orden, "
          f"{mislykket} kunne ikke udledes")
    if toerloeb and rort:
        print("Tørløb — intet skrevet. Kør uden --toerloeb for at gemme.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
