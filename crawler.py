#!/usr/bin/env python3
"""
AI-nyheder - crawler + AI-omskrivning
===================================
1. Henter AI-nyheder fra RSS/Atom-feeds (opsaetning/feeds.json)
2. Omskriver hver artikel til ULTRAKORT, letlæst dansk med DeepSeek eller Gemini
   (springes over hvis ingen API-nøgle er sat - så vises originalen)
3. Gemmer alt i data/articles.json, som hjemmesiden læser

Kør:  python3 crawler.py
Kræver kun Pythons standardbibliotek - ingen pip install.

Omskrivninger CACHES: en artikel der én gang er omskrevet, omskrives
aldrig igen (nøglen er artiklens link). Det holder prisen på få øre.
"""

import json
import os
import time
import re
import html
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ----- Indstillinger ---------------------------------------------------------

ROOT = Path(__file__).parent
OPSAETNING = ROOT / "opsaetning"      # det, DU redigerer. data/ er maskinens
FEEDS_FIL = OPSAETNING / "feeds.json"
OUTPUT_FIL = ROOT / "data" / "articles.json"
MAX_PER_FEED = 25            # max artikler pr. feed
MAX_DAGE_GAMMEL = 30         # smid artikler ældre end 30 dage væk
TIMEOUT_SEK = 20

# --- AI-omskrivning (Claude ELLER Gemini - crawleren bruger den nøgle der findes) ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
GEMINI_MODEL = "gemini-3.5-flash-lite"     # $0.30/$2.50 - billigst hos Google
GEMINI_FALLBACK = "gemini-3.5-flash"       # bruges automatisk hvis Lite ikke svarer
DEEPSEEK_MODEL = "deepseek-v4-flash"       # $0.14/$0.28 - billigst af alle
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# Er begge nøgler sat, vinder AI_UDBYDER ("deepseek" eller "gemini").
# Ellers vælges den billigste tilgængelige: DeepSeek → Gemini.
# (Gemini-nøglen bruges under alle omstændigheder til artikelbillederne.)
UDBYDER = os.environ.get("AI_UDBYDER", "").strip().lower() \
    or ("deepseek" if DEEPSEEK_KEY else "gemini" if GEMINI_KEY else "")
API_KEY = {"gemini": GEMINI_KEY, "deepseek": DEEPSEEK_KEY}.get(UDBYDER, "")

BATCH_STR = 10                   # artikler pr. API-kald (korte resuméer)
MAX_OMSKRIV_PR_KOERSEL = 200     # loft over API-forbrug pr. kørsel
GEMINI_PAUSE_SEK = 2             # pause mellem Gemini-kald (værn mod fartgrænsen)

# --- Dybe briefs (hele artiklen hentes og genfortælles) ---
DYBDE_ANTAL = 250                # ALLE artikler får komplet brief (loft som sikkerhed)
BILLED_ANTAL = 250               # ALLE artikler får AI-billede (bagkatalog indhentes
                                 # gradvist pga. MAX_BILLEDER_PR_KOERSEL)
MIN_TEKST = 400                  # mindste brugbare artikeltekst (tegn)
MAX_TEKST = 7000                 # så meget af artiklen sender vi til Claude

# --- AI-billeder til tophistorierne (kræver GEMINI_API_KEY + betaling slået til) ---
BILLED_MODEL = "gemini-3.1-flash-lite-image"   # ca. $0.034 pr. billede
BILLED_FALLBACK = "gemini-2.5-flash-image"     # bruges hvis Lite-billedmodellen afvises
BILLED_MAPPE = ROOT / "data" / "img"
# Bruges af oprydningen til at spørge siderne, hvilke billeder de peger på,
# før noget slettes. Kun filnavnet fanges.
#
# Skråstregen foran er valgfri med vilje: artikelsiderne skriver den absolutte
# sti (`src="/data/img/…"`), men `uge.html` skriver den relative
# (`src="data/img/…"`). Krævede mønstret skråstregen, ville ugesidens billeder
# ikke være fredet - og det var netop dem, oprydningen havde slettet.
_BILLED_I_HTML = re.compile(r"\bdata/img/([0-9a-f]{16}\.jpg)")
MAX_BILLEDER_PR_KOERSEL = 35     # loft pr. kørsel (værn mod løbske omkostninger)
BILLED_BREDDE = 1280             # nedskaleres til denne bredde (kræver pillow, ellers fuld str.)

_gemini_model = GEMINI_MODEL     # den model vi aktuelt bruger (kan falde tilbage)
_billed_model = BILLED_MODEL     # billedmodellen (kan også falde tilbage)

USER_AGENT = "Mozilla/5.0 (compatible; AInyhederCrawler/2.0; +https://github.com)"
NS = {"atom": "http://www.w3.org/2005/Atom"}


# ----- Hjælpefunktioner (crawl) ----------------------------------------------

def hent_url(url: str, data: bytes | None = None, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, data=data,
                                 headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60 if data else TIMEOUT_SEK) as svar:
        return svar.read()


def rens_tekst(raa: str | None, max_laengde: int = 400) -> str:
    if not raa:
        return ""
    tekst = re.sub(r"<[^>]+>", " ", raa)
    tekst = html.unescape(tekst)
    tekst = re.sub(r"\s+", " ", tekst).strip()
    tekst = re.sub(r"^arXiv:\S+\s+Announce Type:\s*\S+\s+Abstract:\s*", "", tekst)
    if len(tekst) > max_laengde:
        tekst = tekst[:max_laengde].rsplit(" ", 1)[0] + "…"
    return tekst


def parse_dato(dato_str: str | None) -> datetime | None:
    if not dato_str:
        return None
    dato_str = dato_str.strip()
    try:
        return parsedate_to_datetime(dato_str)
    except (ValueError, TypeError):
        pass
    try:
        return datetime.fromisoformat(dato_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_rss(rod: ET.Element) -> list[dict]:
    artikler = []
    for item in rod.iter("item"):
        artikler.append({
            "titel": rens_tekst(item.findtext("title"), 200),
            "link": (item.findtext("link") or "").strip(),
            "resume": rens_tekst(item.findtext("description")),
            "dato": parse_dato(item.findtext("pubDate")),
        })
    return artikler


def parse_atom(rod: ET.Element) -> list[dict]:
    artikler = []
    for entry in rod.findall("atom:entry", NS):
        link = ""
        for l in entry.findall("atom:link", NS):
            if l.get("rel") in (None, "alternate"):
                link = l.get("href", "")
                break
        resume = entry.findtext("atom:summary", default="", namespaces=NS) \
              or entry.findtext("atom:content", default="", namespaces=NS)
        dato_str = entry.findtext("atom:published", default="", namespaces=NS) \
                or entry.findtext("atom:updated", default="", namespaces=NS)
        artikler.append({
            "titel": rens_tekst(entry.findtext("atom:title", default="", namespaces=NS), 200),
            "link": link.strip(),
            "resume": rens_tekst(resume),
            "dato": parse_dato(dato_str),
        })
    return artikler


def crawl_feed(feed: dict) -> tuple[dict, list[dict], str | None]:
    try:
        data = hent_url(feed["url"])
        rod = ET.fromstring(data)
    except (urllib.error.URLError, ET.ParseError, TimeoutError, OSError) as fejl:
        return feed, [], f"{type(fejl).__name__}: {fejl}"

    artikler = parse_rss(rod) if (rod.tag == "rss" or rod.find("channel") is not None) \
        else parse_atom(rod)

    rensede = []
    for a in artikler[:feed.get("max", MAX_PER_FEED)]:
        if not a["titel"] or not a["link"]:
            continue
        a["kilde"] = feed["navn"]
        a["kategori"] = feed.get("kategori", "Andet")
        # Nogle udgivere tillader kun, at DET AKTUELLE feed vises - ikke at vi
        # bygger et arkiv af deres overskrifter. Mærkes her og respekteres
        # både i arkivet, i artikelsiderne og i sitemap.
        if feed.get("kun_aktuel"):
            a["kun_aktuel"] = True
        rensede.append(a)
    return feed, rensede, None


# ----- Artikeltekst-udtræk ----------------------------------------------------

def udtraek_tekst(html_raa: str) -> str:
    """Trækker brødteksten ud af en artikelside: alle <p>-afsnit af rimelig
    længde (frasorterer menuer, cookiebokse osv.). Simpelt men effektivt."""
    # væk med script/style/noscript
    html_raa = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ",
                      html_raa, flags=re.S | re.I)
    # hold os til <article>-blokken hvis den findes
    m = re.search(r"<article[^>]*>(.*?)</article>", html_raa, flags=re.S | re.I)
    if m:
        html_raa = m.group(1)
    afsnit = re.findall(r"<p[^>]*>(.*?)</p>", html_raa, flags=re.S | re.I)
    tekst_afsnit = []
    for p in afsnit:
        t = html.unescape(re.sub(r"<[^>]+>", " ", p))
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 60:                      # korte stumper er sjældent brødtekst
            tekst_afsnit.append(t)
    return "\n\n".join(tekst_afsnit)[:MAX_TEKST]


BILLED_STOPORD = ("logo", "avatar", "author", "icon", "badge", "headshot",
                  "profile", "gravatar", "sprite", ".svg")


def udtraek_billeder(html_raa: str, base_url: str) -> list[dict]:
    """Finder artiklens billeder med alt-tekst/billedtekst, så AI'en kan
    udvælge dem der viser benchmarks, grafer og tabeller."""
    from urllib.parse import urljoin
    kandidater = []
    # <figure> med billedtekst først - det er typisk grafikkerne
    for fig in re.findall(r"<figure[^>]*>(.*?)</figure>", html_raa, flags=re.S | re.I):
        m = re.search(r"<img[^>]+src=[\'\"]([^\'\"]+)", fig, flags=re.I)
        if not m:
            continue
        alt = re.search(r"alt=[\'\"]([^\'\"]*)", fig, flags=re.I)
        cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", fig, flags=re.S | re.I)
        tekst = rens_tekst((cap.group(1) if cap else "") or (alt.group(1) if alt else ""), 150)
        kandidater.append({"url": urljoin(base_url, m.group(1)), "tekst": tekst})
    # løse <img> med beskrivende alt-tekst som supplement
    for m in re.finditer(r"<img[^>]+src=[\'\"]([^\'\"]+)[\'\"][^>]*alt=[\'\"]([^\'\"]{15,})", html_raa, flags=re.I):
        kandidater.append({"url": urljoin(base_url, m.group(1)), "tekst": rens_tekst(m.group(2), 150)})
    # frasortér logoer, ikoner osv. og dubletter
    rene, set_urls = [], set()
    for k in kandidater:
        u = k["url"].split("?")[0].lower()
        if k["url"] in set_urls or any(o in u or o in k["tekst"].lower() for o in BILLED_STOPORD):
            continue
        set_urls.add(k["url"])
        rene.append(k)
    return rene[:8]


def hent_artikeltekst(a: dict) -> tuple[dict, str, list[dict]]:
    """Henter artiklens egen side og returnerer (artikel, brødtekst, billeder).
    Billeder hentes OGSÅ fra historiens øvrige kilder ("+kilder") - det er tit
    dér, benchmark-graferne ligger."""
    try:
        raa = hent_url(a["link"]).decode("utf-8", errors="replace")
        tekst, billeder = udtraek_tekst(raa), udtraek_billeder(raa, a["link"])
    except Exception:                        # paywall, botblokering, timeout …
        tekst, billeder = "", []             # … men prøv stadig de andre kilder
    for b in billeder:
        b["kilde"] = a["kilde"]
    for kilde in a.get("andre", [])[:2]:     # samme historie hos andre medier
        try:
            raa2 = hent_url(kilde["link"]).decode("utf-8", errors="replace")
            ekstra = udtraek_tekst(raa2)[:3000]
            if len(ekstra) > 300:
                tekst += f"\n\n--- SUPPLERENDE KILDE ({kilde['kilde']}) ---\n{ekstra}"
            for b2 in udtraek_billeder(raa2, kilde["link"]):
                b2["kilde"] = kilde["kilde"]
                billeder.append(b2)
        except Exception:
            pass
    return a, tekst[:MAX_TEKST + 6000], billeder[:10]


# ----- AI-omskrivning til letlæst dansk --------------------------------------

SYSTEM_PROMPT = """Du omskriver tech-nyheder til danskere HELT uden teknisk baggrund.

VIGTIGSTE REGEL - NÆVN ALTID NAVNENE:
Rubrikken SKAL nævne, hvem historien handler om: virksomheden, produktet eller
modellen ved rigtigt navn (Google, OpenAI, Oracle, Midjourney, ChatGPT, Gemini,
Claude, EU, Folketinget ...). Navne er ikke jargon - de er dét, læseren
genkender, googler og husker.
FORBUDT i rubrikker: "en kæmpe gigant", "et stort firma", "et selskab",
"en kendt tjeneste", "et nyt værktøj" - når kilden nævner navnet.
  DÅRLIGT: "Kæmpe gigant fyrer 21.000 medarbejdere"
  GODT:    "Oracle fyrer 21.000 medarbejdere efter AI-satsning"
  DÅRLIGT: "Ny digital hjerne er billigere og bedre"
  GODT:    "Anthropics nye Opus 5 er billigere og bedre"
Står navnet ikke i materialet, opfinder du det ALDRIG - så beskriver du i stedet
konkret hvem (fx "Kinesisk techgigant ..." eller "EU-Kommissionen ...").

For hver artikel laver du:
- "rubrik": fængende dansk overskrift på MAX 9 ord, med navn (se ovenfor).
  Ingen jargon udover selve navnene. Ingen punktum til sidst.
- "resume": 1-2 KORTE sætninger på hverdagsdansk. Max 30 ord i alt.
  Resuméet må ALDRIG bare gentage rubrikken med andre ord. Rubrikken siger
  HVAD der skete; resuméet tilføjer det, læseren ikke kunne gætte - tallet,
  konsekvensen, modparten, hvad der nu sker.
    RUBRIK:  "Oracle fyrer 21.000 medarbejdere efter AI-satsning"
    DÅRLIGT: "Oracle har afskediget 21.000 ansatte på grund af en AI-satsning."
    GODT:    "Fyringerne rammer især salg og support. Oracle vil bruge pengene
              på datacentre i stedet."
  Forbudt: engelske låneord der har et dansk ord, forkortelser uden forklaring,
  og buzzwords. Skriv som til en klog nabo.
- Skriv ALTID "AI" - aldrig "kunstig intelligens" (det er for langt).
- Er et fagudtryk uundgåeligt, så forklar det med tre-fire almindelige ord
  ("en sprogmodel - den slags AI, der skriver tekst").

Svar KUN med et JSON-array, ét objekt pr. artikel, i samme rækkefølge som input:
[{"rubrik": "...", "resume": "..."}, ...]"""


# ----- Hjernerne: model og prompt pr. arbejdstrin ----------------------------
#
# Alt herunder kan overstyres i _redaktion/hjerner.json uden at røre koden.
# Filen behøver kun at indeholde dét, der er ændret - resten kører videre på
# det indbyggede. Er filen væk eller i stykker, sker der ingenting.

HJERNER_FIL = ROOT / "_redaktion" / "hjerner.json"
HJERNER_STATUS = ROOT / "data" / "hjerner-status.json"

# navn -> hvad trinnet laver (vises i kontrolpanelet)
HJERNE_BESKRIVELSE = {
    "omskriv": "Skriver rubrik og resumé på dansk for hver ny artikel",
    "kategori": "Sætter kategori og prioritet 1-10 på hver artikel",
    "dublet": "Finder artikler fra flere medier om samme begivenhed",
    "brief": "Skriver den fulde danske genfortælling af en artikel",
    "redaktoer": "Læser genfortællingen igennem og kræver omskrivning ved fejl",
    "stram": "Strammer for lange 'Hvad betyder det for dig'-tekster",
    "navngiv": "Sætter navne på gamle, anonyme overskrifter",
    "motiv": "Finder billedmotivet til artikelillustrationerne",
    "kartotek": "Skriver dagens prompt til prompt-kartoteket",
    "quiz": "Laver ugens nyhedsquiz",
    "dagens_overblik": "Skriver de fem punkter i Dagens overblik på forsiden",
    "ugens_overblik": "Skriver ugens digest og nyhedsbrevet",
    "youtube": "Opsummerer YouTube-videoer på dansk med tidsstempler",
    "opslag": "Skriver opslag til de sociale platforme",
}

_hjerner_cache: dict | None = None


def _hjerner() -> dict:
    global _hjerner_cache
    if _hjerner_cache is None:
        _hjerner_cache = {}
        if HJERNER_FIL.exists():
            try:
                d = json.loads(HJERNER_FIL.read_text(encoding="utf-8"))
                if isinstance(d.get("hjerner"), dict):
                    _hjerner_cache = d["hjerner"]
            except (json.JSONDecodeError, OSError) as fejl:
                print(f"🧠 ⚠️ hjerner.json kunne ikke læses ({fejl}) "
                      "- kører videre på de indbyggede prompts")
    return _hjerner_cache


def hjerne_prompt(navn: str, standard: str) -> str:
    """Systemprompten for et arbejdstrin - overstyret eller indbygget."""
    p = (_hjerner().get(navn) or {}).get("prompt")
    return p.strip() if isinstance(p, str) and p.strip() else standard


def hjerne_model(navn: str) -> str | None:
    """Gemini-model for et trin, hvis panelet har valgt en bestemt."""
    mo = (_hjerner().get(navn) or {}).get("model")
    return mo.strip() if isinstance(mo, str) and mo.strip() else None


def hjerne_kald(navn: str, standard_prompt: str, bruger: str,
                max_tokens: int, standard_model: str | None = None) -> str:
    """Kalder AI'en for ét arbejdstrin. Er der valgt en bestemt Gemini-model
    til trinnet, bruges den - ellers den daglige udbyder."""
    system = hjerne_prompt(navn, standard_prompt)
    model = hjerne_model(navn) or standard_model
    if model and GEMINI_KEY:
        try:
            return kald_gemini_model(system, bruger, max_tokens, model)
        except Exception as fejl:
            print(f"🧠 ⚠️ {navn}: {model} svarede ikke "
                  f"({type(fejl).__name__}) - bruger den daglige model")
    return kald_ai(system, bruger, max_tokens)


# Arbejdsloopets dokumenter. De styrer, hvad sessionen laver - og kan redigeres
# i kontrolpanelet ligesom prompterne. Loopet er ikke bundet til noget tidspunkt.
ARBEJDS_DOKUMENTER = [
    ("oensker", "oensker.md", "Ønskelisten",
     "Skriv her, hvad du vil have lavet — i almindeligt dansk. Sessionen læser "
     "den før alt andet og oversætter ønskerne til punkter i køen.", True),
    ("maalestok", "redaktionens-oejne.md", "Målestokken",
     "Ti punkter der definerer 'godt'. Afgør alt, hvad sessionen laver.", True),
    ("instruks", "arbejdsinstruks.md", "Arbejdsinstruksen",
     "Hele arbejdsgangen: de fire faser, hvordan der testes, hvornår der "
     "stoppes. Læses forfra ved hver kørsel.", True),
    ("opgavekoe", "opgavekoe.md", "Opgavekøen",
     "Det, der bliver lavet — oppefra og ned. Flyt en linje op for at "
     "prioritere den frem.", True),
    ("analyse", "analyse-seneste.md", "Sessionens egen analyse",
     "Sessionens gennemgang af siden, skrevet FØR den gik i gang. "
     "Kun til at læse.", False),
    ("log", "arbejdslog.md", "Arbejdsloggen",
     "Hvad kørslerne har lavet, og hvad du skal vide. Kun til at læse.", False),
]


def _klip_ved_sektion(tekst: str, maks: int = 30000) -> str:
    """Klipper en lang log, uden at efterlade en halv indgang.

    Nat-loggen vokser med en nat om dagen og er allerede over 50 KB. Panelet
    skal kunne vise de seneste nætter uden at hele historikken indlejres i
    `hjerne-data.js`, som ligger i data/ og committes. Nyeste står øverst, så
    vi tager toppen - men klipper ved en `---`-grænse, så en indgang aldrig
    ender midt i en sætning.
    """
    if len(tekst) <= maks:
        return tekst
    # Regnskabet skal ALTID med - panelets etape hedder "Du læser regnskabet",
    # så det er selve pointen. Ligger det efter grænsen, flyttes grænsen ud til
    # efter det i stedet for omvendt.
    # Der ledes efter BEGGE overskrifter: de gamle poster hedder "Nattens
    # regnskab", de nye "Sessionens". Leder man kun efter den ene, findes i
    # stedet en flere uger gammel post langt nede i filen, og så flyttes
    # grænsen dertil - dvs. hele loggen ryger med ind i data/hjerne-data.js.
    slut = maks
    start = min([i for i in (tekst.find("### Nattens regnskab"),
                             tekst.find("### Sessionens regnskab")) if i >= 0],
                default=-1)
    if start >= 0:
        efter = tekst.find("\n---\n", start)
        slut = max(slut, len(tekst) if efter < 0 else efter + 5)
    if slut >= len(tekst):
        return tekst
    skaaret = tekst[:slut]
    graense = skaaret.rfind("\n---\n")
    if graense > slut // 3:
        skaaret = skaaret[:graense]
    return (skaaret.rstrip() + "\n\n---\n\n*Ældre indgange er klippet fra her. "
            "Hele historikken står i `_redaktion/arbejdslog.md`.*\n")


def _arbejdsloop_status() -> list:
    ud = []
    for noegle, fil, navn, besk, kan_rettes in ARBEJDS_DOKUMENTER:
        sti = ROOT / "_redaktion" / fil
        try:
            indhold = sti.read_text(encoding="utf-8")
        except OSError:
            indhold = ""
        ud.append({"noegle": noegle, "fil": fil, "navn": navn,
                   "beskrivelse": besk, "kan_rettes": kan_rettes,
                   "findes": bool(indhold),
                   # loggen kan blive lang - panelet skal kun vise de nyeste
                   "indhold": indhold if kan_rettes else _klip_ved_sektion(indhold)})
    return ud


def _standard_prompts() -> dict:
    """De indbyggede prompts, så kontrolpanelet kan vise dem og lade redaktionen
    starte fra dem i stedet for fra et tomt felt."""
    return {
        "omskriv": SYSTEM_PROMPT, "kategori": SYSTEM_KATEGORI,
        "dublet": SYSTEM_DUBLET, "brief": SYSTEM_BRIEF_ARTIKEL,
        "redaktoer": SYSTEM_REDAKTOER, "stram": SYSTEM_STRAM,
        "navngiv": SYSTEM_NAVNGIV, "motiv": SYSTEM_MOTIV,
        "kartotek": SYSTEM_KARTOTEK, "quiz": SYSTEM_QUIZ,
        "dagens_overblik": SYSTEM_BRIEF, "ugens_overblik": SYSTEM_UGE,
        "youtube": SYSTEM_YT, "opslag": SYSTEM_OPSLAG,
    }


def skriv_hjerne_status() -> None:
    """Data til kontrolpanelet: hvilke modeller og instrukser der er i brug,
    og arbejdsloopets dokumenter. Skrives både som JSON og som en JS-fil, så
    panelet kan åbnes direkte fra mappen uden en webserver.

    KUN LOKALT. På GitHubs servere springes det over med vilje: filerne
    genskrives ved hver kørsel, og skriver både robotten og os i dem, giver
    det en merge-konflikt hver gang. Én skribent, ingen konflikter. Indholdet
    ændrer sig alligevel kun, når VI ændrer en prompt eller en model."""
    if os.environ.get("GITHUB_ACTIONS"):
        return
    daglig = DEEPSEEK_MODEL if UDBYDER == "deepseek" else GEMINI_MODEL
    std = _standard_prompts()
    status = {
        "opdateret": datetime.now(timezone.utc).isoformat(),
        "daglig_model": daglig,
        "udbyder": UDBYDER or "ingen",
        "billedmodel": BILLED_MODEL if GEMINI_KEY else "ingen",
        "gemini_tilgaengelig": bool(GEMINI_KEY),
        "hjerner": {
            navn: {
                "beskrivelse": besk,
                "model": hjerne_model(navn) or daglig,
                "egen_model": bool(hjerne_model(navn)),
                "egen_prompt": bool((_hjerner().get(navn) or {}).get("prompt")),
                "standard_prompt": std.get(navn, ""),
                "aktiv_prompt": hjerne_prompt(navn, std.get(navn, "")),
            } for navn, besk in HJERNE_BESKRIVELSE.items()
        },
        "arbejdsloop": _arbejdsloop_status(),
    }
    HJERNER_STATUS.parent.mkdir(exist_ok=True)
    HJERNER_STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    # Samme data som JavaScript - så kontrolpanelet virker fra file://.
    # Ligger i data/, fordi det er dén mappe, workflow'en committer.
    (HJERNER_STATUS.parent / "hjerne-data.js").write_text(
        "window.HJERNE_STATUS = "
        + json.dumps(status, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8")


def kald_gemini_model(system: str, bruger_tekst: str, max_tokens: int,
                      model: str) -> str:
    """Kalder en BESTEMT Gemini-model. Bruges til den natlige gennemgang, hvor
    vi vil have den kloge model uanset hvem der skriver artiklerne til daglig.
    Ingen fallback: virker modellen ikke, skal vi vide det."""
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY mangler")
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": bruger_tekst}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }).encode()
    svar = hent_url(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=body, headers={"x-goog-api-key": GEMINI_KEY,
                            "content-type": "application/json"})
    return json.loads(svar)["candidates"][0]["content"]["parts"][0]["text"]


def kald_ai(system: str, bruger_tekst: str, max_tokens: int) -> str:
    """Ét fælles AI-kald - taler med DeepSeek eller Gemini alt efter hvilken
    nøgle der er sat. Returnerer modellens rå tekstsvar."""
    if UDBYDER == "deepseek":
        # OpenAI-formatet. VIGTIGT: "thinking" er slået TIL som standard hos
        # DeepSeek, og tankerne afregnes som udskrift. Til omskrivning af
        # nyheder har vi ikke brug for dem - så de slås fra her.
        body = json.dumps({
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": bruger_tekst}],
            "max_tokens": max_tokens,
            "thinking": {"type": "disabled"},
            "stream": False,
        }).encode()
        svar = hent_url(DEEPSEEK_URL, data=body, headers={
            "Authorization": f"Bearer {API_KEY}",
            "content-type": "application/json",
        })
        return json.loads(svar)["choices"][0]["message"]["content"]

    # Gemini - prøv den billige Lite-model først, fald tilbage hvis den afvises
    global _gemini_model
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": bruger_tekst}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }).encode()
    try:
        svar = hent_url(
            f"https://generativelanguage.googleapis.com/v1beta/models/{_gemini_model}:generateContent",
            data=body, headers={"x-goog-api-key": API_KEY, "content-type": "application/json"})
    except urllib.error.HTTPError as fejl:
        if fejl.code in (400, 404) and _gemini_model != GEMINI_FALLBACK:
            print(f"  ⚠️  MODELSKIFT: {_gemini_model} blev afvist ({fejl.code}) "
                  f"- resten af kørslen bruger den DYRERE {GEMINI_FALLBACK}")
            _gemini_model = GEMINI_FALLBACK
            svar = hent_url(
                f"https://generativelanguage.googleapis.com/v1beta/models/{_gemini_model}:generateContent",
                data=body, headers={"x-goog-api-key": API_KEY, "content-type": "application/json"})
        else:
            raise
    tekst = json.loads(svar)["candidates"][0]["content"]["parts"][0]["text"]
    time.sleep(GEMINI_PAUSE_SEK)             # bliv under gratis-niveauets fartgrænse
    return tekst


def parse_json_svar(raa: str):
    """Fjerner evt. kodehegn og parser modellens JSON-svar."""
    raa = re.sub(r"^```(json)?\s*|\s*```$", "", raa.strip())
    return json.loads(raa)


def parse_json_objekt(raa: str) -> dict:
    """Som parse_json_svar, men garanterer en dict.

    Modellerne er ikke enige med sig selv: nogle svarer {...}, andre pakker
    det samme objekt i et array, [{...}]. Uden denne udpakning fejler hvert
    eneste kald med AttributeError ('list' har ingen .get) - og fejlen er
    stille, så artiklerne bare står uden brief."""
    r = parse_json_svar(raa)
    if isinstance(r, list):
        r = next((x for x in r if isinstance(x, dict)), None)
    return r if isinstance(r, dict) else {}


def kald_ai_batch(artikler: list[dict]) -> list[dict] | None:
    """Sender en batch artikler til AI'en og får danske omskrivninger tilbage."""
    input_liste = [{"nr": i + 1, "titel": a["titel"], "tekst": a["resume"][:350],
                    "kilde": a["kilde"]} for i, a in enumerate(artikler)]
    try:
        resultat = parse_json_svar(hjerne_kald("omskriv", SYSTEM_PROMPT,
            "Omskriv disse artikler:\n" + json.dumps(input_liste, ensure_ascii=False),
            4000))
        if isinstance(resultat, list) and len(resultat) == len(artikler):
            return resultat
        print(f"  ⚠️  AI-svar havde forkert længde ({len(resultat)} vs {len(artikler)})")
    except Exception as fejl:  # API nede, kvote opbrugt, ugyldigt JSON osv.
        print(f"  ⚠️  AI-kald fejlede: {type(fejl).__name__}: {fejl}")
    return None


SYSTEM_BRIEF_ARTIKEL = """Du er journalist på et dansk nyhedssite for almindelige mennesker
uden teknisk baggrund. Ud fra artikelteksten skriver du en SELVSTÆNDIG dansk
genfortælling i dine helt egne ord - oversæt ALDRIG sætninger direkte, og citér
ikke fra kilden. Kald teknologien "AI" - skriv ALDRIG "kunstig intelligens"
og opfind ALDRIG omskrivninger som "computerhjerner" eller "tænksom software".
Modelnavne (Gemini, GPT, Claude osv.) skrives præcis som i kilden.

Fremhæv de 1-2 vigtigste tal eller navne i hver sektion med **dobbelt-stjerner**.
Skriv levende og varieret - ALDRIG tre ens grå afsnit i træk.

UFRAVIGELIGT KRAV: Indeholder artiklen benchmarks, scores, procenter, priser
eller sammenligningstal, SKAL de konkrete tal med i genfortællingen - i
nøgletal-fliserne, detaljerne og/eller sektionerne. Tal må ALDRIG koges væk
til vage ord som "markant bedre".

Nøgletal-fliserne er KUN til tal med reel nyhedsværdi: benchmark-scores,
priser, hastigheder, procenter, brugertal og beløb. Brug ALDRIG fyldtal som
antal forfattere, filstørrelser, sidetal, årstal eller versionsnumre.
Er der ingen meningsfulde tal, SKAL listen være tom.

Svar KUN med ét JSON-objekt:
{
 "rubrik":    fængende dansk overskrift, max 8 ord, ingen jargon. Den skal
              vække ægte nysgerrighed - lov læseren en indsigt, de ikke kan
              regne ud selv - men ALDRIG clickbait, der oversælger,
 "resume":    1-2 korte sætninger (max 30 ord) til oversigten,
 "sektioner": 2-4 afsnit med hver sin KORTE, konkrete mini-overskrift (2-4 ord,
              fx "Det er sket", "Pengene bag", "Kritikerne siger", "Hvad nu?" -
              ALDRIG **fremhævning** i selve overskriften).
              Hvert afsnit 40-70 ord letlæst hverdagsdansk.
              PRØVEN: hvert afsnit skal svare på et NYT spørgsmål. Kan afsnit 2
              slettes, uden at læseren mister noget, har du skrevet det samme
              to gange - og så skal der stå noget andet. Har artiklen kun stof
              til to afsnit, så skriv to. To skarpe slår fire tynde:
              [{"overskrift": "...", "tekst": "..."}, ...],
 "noegletal": KUN til tal hvor TALLET I SIG SELV er nyheden: benchmark-scores,
              priser, hastigheder, investeringsbeløb, brugertal i millioner.
              Testen er: Ville en avis sætte tallet med kæmpe typer på
              forsiden? [{"tal": "17 %", "label": "billigere end forgængeren"}].
              ALDRIG trivia som spilletid, antal medvirkende, sidetal eller
              udgivelsesår. Langt de fleste artikler skal have TOM liste her -
              det er kun benchmark- og pengehistorier, der har ægte nøgletal,
 "detaljer":  4-7 punkter med de vigtigste fakta, tal og detaljer fra artiklen
              (hvert punkt én sætning, max 20 ord),
 "betydning": 1-2 sætninger (maks 35 ord): den ENE konsekvens, der rammer
              læserens hverdag, penge eller fremtid. Skriv direkte til "du",
              start aldrig med "Det betyder" eller "Denne nyhed" - lige på
              pointen. Skarp og konkret slår lang og forsigtig,
 "pointer":   3-4 ultrakorte hovedpointer (hver max 12 ord),
 "figurer":   Fra listen KANDIDAT-BILLEDER udvælger du 0-3, der viser
              benchmarks, grafer, tabeller eller andre data - IKKE almindelige
              pressefotos. Returnér dem med en kort dansk billedtekst:
              [{"url": "...", "tekst": "..."}]. Tom liste hvis ingen er relevante,
 "billedmotiv": Du er også art director: Beskriv i max 25 ord ÉN konkret scene
              med 1-3 genkendelige genstande, som fortæller PRÆCIS denne
              histories pointe - så en læser der ser billedet, kan gætte
              historien. Ingen mennesker, ingen tekst i billedet. Vær specifik
              ("en flyttekasse fuld af robotarme med prisskilt"), aldrig
              generisk ("abstrakte former der symboliserer AI").
}"""


# Ekstra instruks til dagens vigtigste historier: mere dybde, ikke mere fyld.
SYSTEM_BRIEF_LANG = """

DENNE HISTORIE ER EN AF DAGENS VIGTIGSTE - GIV DEN MERE DYBDE:
- 4-6 sektioner (stadig 40-80 ord pr. sektion) i stedet for de normale 2-4.
- 5-7 detaljer. "betydning" forbliver kort og skarp (maks 35 ord) - dybden
  skal i sektionerne, ikke i betydningen.
- Mere dybde betyder FLERE konkrete fakta, tal, reaktioner og perspektiver
  fra kilderne - ALDRIG længere omskrivninger af det samme."""


# Ekstra instruks når artiklen er en forskningsartikel (arXiv m.fl.):
# formidling frem for akademiske fyldtal.
SYSTEM_BRIEF_FORSKNING = """

SÆRLIGT FOR DENNE ARTIKEL - DET ER EN VIDENSKABELIG FORSKNINGSARTIKEL:
- Fortæl som en begejstret formidler: Hvad har forskerne opdaget, hvad er
  det NYE, og hvad kan det bruges til ude i virkeligheden?
- Nævn ALDRIG antal forfattere, dokumentstørrelse, sidetal eller udgivelsesdato.
- "noegletal" skal som regel være en TOM liste. Kun hvis artiklen rapporterer
  konkrete resultater (fx "3x hurtigere" eller "92 % nøjagtighed"), må de med.
- "betydning" er den vigtigste del: Gør opdagelsen jordnær og konkret.
- Er indholdet så smalt, at det ikke kan gøres relevant for almindelige
  mennesker, så skriv kort og nøgternt - pust det ALDRIG kunstigt op."""


# Ord der afslører, at et billede er en graf/benchmark - bruges som
# deterministisk sikkerhedsnet, hvis AI'en ikke selv vælger nogen figurer.
FIGUR_ORD = re.compile(
    r"eval|benchmark|chart|graph|figure|figur|score|leaderboard|compar|"
    r"result|table|tabel|graf|maaling|diagram", re.I)


# ----- Redaktør-agenten: kvalitetstjek FØR udgivelse ---------------------------

SYSTEM_REDAKTOER = """Du er en benhård, men fair redaktionschef på et dansk
AI-nyhedssite for almindelige mennesker. Du får et artikel-brief og afgør, om
det må udgives. Du tjekker KUN disse regler:

1. RUBRIK: max 8 ord, letlæst dansk, vækker ægte nysgerrighed uden clickbait.
   Ordene "kunstig intelligens" er FORBUDT (skriv "AI").
2. SPROG: hverdagsdansk uden jargon og fyld. Sektionerne skal sige noget
   FORSKELLIGT - ikke gentage hinanden med nye ord. Ingen **stjerner** i
   mini-overskrifterne.
3. NØGLETAL: kun tal med forside-værdi (scores, priser, beløb, hastigheder).
   Årstal, antal forfattere, spilletid og lignende trivia er FORBUDT som
   nøgletal. En tom liste er helt fint.
4. BETYDNING: står under overskriften "Hvad betyder det for DIG?", så den skal
   svare læseren direkte. Afvis hvis den (a) ikke tiltaler læseren med
   "du/dig/din", (b) er længere end 35 ord, eller (c) taler OM en tredje part
   i stedet for TIL læseren - "For almindelige mennesker betyder det …", "For
   forbrugerne …", "Historien viser …". Ingen floskler som "AI ændrer vores
   hverdag". Én konsekvens, ikke fem.

VIGTIGT: Godkend alt, der overholder reglerne - omskrivninger koster penge.
Afvis KUN ved klare regelbrud, og vær så konkret i dine noter, at skribenten
kan rette det i ét forsøg.

Svar KUN med JSON: {"godkendt": true/false, "problemer": ["kort, konkret note", ...]}"""


def redaktoer_tjek(a: dict) -> dict | None:
    """Lader redaktør-agenten vurdere et netop skrevet brief. None ved fejl."""
    try:
        udkast = {"rubrik": a.get("rubrik"), "resume": a.get("resume_da"),
                  "sektioner": a.get("sektioner"), "noegletal": a.get("noegletal"),
                  "betydning": a.get("betydning"), "kategori": a.get("kategori")}
        r = parse_json_objekt(hjerne_kald("redaktoer", SYSTEM_REDAKTOER, json.dumps(udkast, ensure_ascii=False), 400))
        if isinstance(r, dict) and "godkendt" in r:
            return r
    except Exception as fejl:
        print(f"  ⚠️  Redaktør-tjek fejlede: {type(fejl).__name__}: {fejl}")
    return None


# Vendinger, der taler OM en tredje part i stedet for TIL læseren. Boksen
# hedder "Hvad betyder det for dig?", så de svarer på et andet spørgsmål end
# det, der står over dem. Målt 26.07: de 6 betydninger, der brugte en af dem,
# manglede ALLE "du" og havde median 42 ord mod 20 i resten - det er den
# formulering, modellen glider over i, når den ikke har en konkret konsekvens.
BETYDNING_TREDJEPERSON = re.compile(
    r"\bfor (helt )?almindelige (mennesker|danskere|familier|forbrugere|brugere)\b"
    r"|\bfor forbrugerne\b|\bfor danskerne\b|\bfor os alle\b|\bfor samfundet\b"
    r"|\bhistorien viser\b", re.I)

BETYDNING_MAX_ORD = 35          # samme grænse som SYSTEM_BRIEF_ARTIKEL lover
_BETYDNING_DU = re.compile(r"\b(du|dig|din|dit|dine)\b", re.I)


def _betydning_problemer(tekst: str) -> list[str]:
    """Deterministisk tjek af "Hvad betyder det for dig?" - de krav i
    brief-prompten, der kan måles med en lineal frem for et skøn.

    Redaktør-agenten er et AI-kald og fanger dem ikke pålideligt; dens egen
    regel var oven i købet formuleret i tredjeperson ("konkret for almindelige
    danskere"), så den godkendte netop den fejl, den skulle fange. Noterne her
    fodres ind i den omskrivning, redaktøren allerede kan bestille, så der kun
    bruges et ekstra kald, når noget faktisk er galt.
    """
    t = (tekst or "").strip()
    if not t:
        return []
    problemer = []
    antal_ord = len(t.split())
    if antal_ord > BETYDNING_MAX_ORD:
        problemer.append(
            f'"betydning" fylder {antal_ord} ord - skær ned til højst '
            f'{BETYDNING_MAX_ORD} og behold kun den ENE vigtigste konsekvens')
    if not _BETYDNING_DU.search(t):
        problemer.append(
            '"betydning" tiltaler ikke læseren - skriv direkte til "du", '
            'fx "Du kan fremover …" i stedet for at beskrive hvad der sker')
    fund = BETYDNING_TREDJEPERSON.search(t)
    if fund:
        problemer.append(
            f'"betydning" taler om en tredje part ("{fund.group(0)}") i stedet '
            'for til læseren - boksen hedder "Hvad betyder det for DIG?"')
    return problemer


def kald_ai_brief(a: dict, tekst: str, billeder: list[dict],
                  redaktoer_noter: str = "") -> dict | None:
    """Laver et komplet dansk brief ud fra artiklens fulde tekst."""
    try:
        er_forskning = "arxiv" in a.get("kilde", "").lower() or a.get("kategori") == "Forskning"
        er_vigtig = (a.get("prio") or 0) >= 8 or bool(a.get("andre"))
        sys_prompt = SYSTEM_BRIEF_ARTIKEL \
            + (SYSTEM_BRIEF_FORSKNING if er_forskning else "") \
            + (SYSTEM_BRIEF_LANG if er_vigtig and not er_forskning else "")
        bruger = f"KILDE: {a['kilde']}\nTITEL: {a['titel']}\n\nARTIKELTEKST:\n{tekst}"
        if redaktoer_noter:
            bruger += ("\n\nREDAKTØRENS NOTER TIL DIT FORRIGE UDKAST - "
                       f"RET PRÆCIS DISSE PROBLEMER:\n{redaktoer_noter}")
        r = parse_json_objekt(hjerne_kald("brief", sys_prompt, bruger, 2200 if er_vigtig else 1500))
        if r.get("rubrik") and (r.get("sektioner") or r.get("brief")):
            return r
    except Exception as fejl:
        print(f"  ⚠️  Brief-kald fejlede ({a['kilde']}): {type(fejl).__name__}: {fejl}")
    return None


def dybe_briefs(artikler: list[dict]) -> None:
    """Giver de DYBDE_ANTAL nyeste artikler et komplet dansk brief:
    henter artikelsiden, udtrækker brødteksten og lader Claude genfortælle."""
    if GENKOER_FILTER == "betydning":
        # Målrettet genkørsel: kun de artikler, hvis "Hvad betyder det for dig?"
        # bryder de målbare krav. Strammes kravene til feltet, koster det så
        # nogle få kald i stedet for at genskrive hele arkivet.
        kandidater = [a for a in artikler[:DYBDE_ANTAL]
                      if not a.get("kun_aktuel")
                      and _betydning_problemer(a.get("betydning", ""))]
        print(f'📰 Genkører {len(kandidater)} artikler med en svag "betydning"')
    elif GENKOER_FILTER:
        kandidater = [a for a in artikler[:DYBDE_ANTAL]
                      if GENKOER_FILTER in (a.get("rubrik", "") + " " + a["titel"]
                                            + " " + a["kilde"]).lower()]
        print(f"📰 Genkører {len(kandidater)} artikler der matcher '{GENKOER_FILTER}'")
    else:
        kandidater = [a for a in artikler[:DYBDE_ANTAL]
                      if (GENKOER_ALT or not a.get("sektioner"))
                      and not a.get("kun_aktuel")]   # ingen fuld genfortælling
                                                     # af kilder med arkivforbud
    if not kandidater:
        print("📰 Alle topartikler har allerede et brief (cache)")
        return
    if not API_KEY:
        print("📰 Ingen AI-nøgle sat (DEEPSEEK_API_KEY/GEMINI_API_KEY) - springer dybe briefs over")
        return

    print(f"📰 Henter og genfortæller {len(kandidater)} artikler i fuld længde …")
    med_tekst = []
    with ThreadPoolExecutor(max_workers=6) as pool:      # hent siderne parallelt
        for job in as_completed([pool.submit(hent_artikeltekst, a) for a in kandidater]):
            a, tekst, billeder = job.result()
            if len(tekst) >= MIN_TEKST:
                med_tekst.append((a, tekst, billeder))
            else:
                # Nødplan: kan artiklen ikke hentes (paywall/bot-værn), skriver
                # vi et kortere brief ud fra RSS-resuméet, så INGEN artikel
                # står helt uden tekst.
                nod = (a.get("resume") or "").strip()
                if tekst.strip() or len(nod) >= 80:
                    nodtekst = ("OBS: Artiklens fulde tekst kunne ikke hentes. Skriv en "
                                "KORTERE genfortælling (2 sektioner er fint) KUN ud fra "
                                "materialet herunder - opdigt ALDRIG tal eller detaljer, "
                                "der ikke står der.\n\n"
                                f"{a['titel']}\n\n{nod}{tekst}")
                    med_tekst.append((a, nodtekst, billeder))
                else:
                    print(f"   ⚠️  {a['kilde']}: hverken brødtekst eller resumé - beholder kort resumé")

    rettet = 0
    for i, (a, tekst, billeder) in enumerate(med_tekst, 1):
        r = kald_ai_brief(a, tekst, billeder)
        if r:
            _anvend_brief(a, r, billeder)
            # Redaktør-agenten læser med, FØR briefet udgives.
            dom = redaktoer_tjek(a)
            problemer = []
            if dom is not None and not dom.get("godkendt", True) and dom.get("problemer"):
                problemer += [str(p) for p in dom["problemer"]]
            # … og oven i skønnet et deterministisk tjek af "betydning", som
            # redaktøren erfaringsmæssigt lader slippe igennem.
            problemer += _betydning_problemer(a.get("betydning", ""))
            if problemer:
                noter = " · ".join(problemer[:4])[:400]
                print(f"   ✏️  Redaktøren kræver omskrivning: {noter[:110]}")
                betydning_foer = a.get("betydning", "")
                r2 = kald_ai_brief(a, tekst, billeder, redaktoer_noter=noter)
                if r2:
                    _anvend_brief(a, r2, billeder)
                    # En omskrivning må ikke gøre betydningen dårligere end
                    # den, den erstattede - ellers ville det nye tjek kunne
                    # forværre præcis det felt, det skulle beskytte.
                    if len(_betydning_problemer(a.get("betydning", ""))) > \
                            len(_betydning_problemer(betydning_foer)):
                        a["betydning"] = betydning_foer
                    rettet += 1
        print(f"   … {i}/{len(med_tekst)}")
    if rettet:
        print(f"✏️  Redaktøren fik omskrevet {rettet} af {len(med_tekst)} briefs")


def _som_tekst(v) -> str:
    """Gør et element fra et AI-svar til ren tekst. Modellerne leverer af og
    til liste-punkter som objekter ({'tal': ..., 'sætning': ...}) i stedet for
    strenge - uden dette værn ender Python-krøller som rå tekst på sitet."""
    if isinstance(v, dict):
        for noegle in ("sætning", "saetning", "tekst", "punkt", "detalje", "label"):
            if v.get(noegle):
                return str(v[noegle]).strip()
        return " - ".join(str(x).strip() for x in v.values() if str(x).strip())
    s = str(v).strip()
    if s.startswith("{") and s.endswith("}"):
        try:
            import ast
            return _som_tekst(ast.literal_eval(s))
        except (ValueError, SyntaxError):
            pass
    return s


def _anvend_brief(a: dict, r: dict, billeder: list[dict]) -> None:
    """Lægger et AI-brief ind på artiklen (bruges både til første udkast
    og til redaktørens omskrivninger)."""
    if True:
            a["rubrik"] = str(r["rubrik"]).strip()
            a["resume_da"] = str(r.get("resume", "")).strip() or a.get("resume_da", "")
            a["sektioner"] = [{"overskrift": str(x.get("overskrift", "")).strip(),
                               "tekst": str(x.get("tekst", "")).strip()}
                              for x in r.get("sektioner", []) if x.get("tekst")][:6]
            a["brief"] = str(r.get("brief", "")).strip()
            def _noegle(u): return str(u or "").split("?")[0].strip()
            kilde_af = {_noegle(b["url"]): (b["url"], b.get("kilde", a["kilde"])) for b in billeder}
            a["figurer"] = []
            for f in r.get("figurer", []):
                match = kilde_af.get(_noegle(f.get("url")))
                if match:
                    a["figurer"].append({"url": match[0],
                                         "tekst": str(f.get("tekst", "")).strip(),
                                         "kilde": match[1]})
            a["figurer"] = a["figurer"][:3]
            # Sikkerhedsnet: vælger AI'en ingen figurer, tager vi selv dem,
            # hvis URL eller billedtekst tydeligt lugter af benchmark/graf.
            if not a["figurer"]:
                for b in billeder:
                    if FIGUR_ORD.search(b["url"]) or FIGUR_ORD.search(b.get("tekst", "")):
                        a["figurer"].append({
                            "url": b["url"],
                            "tekst": b.get("tekst", "").strip() or "Figur fra artiklen",
                            "kilde": b.get("kilde", a["kilde"])})
                        if len(a["figurer"]) == 3:
                            break
            a["noegletal"] = [{"tal": str(n.get("tal", "")).strip(),
                               "label": str(n.get("label", "")).strip()}
                              for n in r.get("noegletal", []) if n.get("tal")][:5]
            a["detaljer"] = [t for t in (_som_tekst(d) for d in r.get("detaljer", [])) if t][:7]
            a["betydning"] = str(r.get("betydning", "")).strip()
            a["pointer"] = [t for t in (_som_tekst(p) for p in r.get("pointer", [])) if t][:4]
            a["billedmotiv"] = str(r.get("billedmotiv", "")).strip()


# ----- Indholdskategorier (AI vælger kategori ud fra indholdet) ----------------

KATEGORIER = ["Lanceringer", "Hverdags-AI", "Penge & marked",
              "Politik & jura", "Samfund & etik", "Forskning"]

SYSTEM_KATEGORI = f"""Du analyserer AI-nyheder for en almindelig dansker, der vil
opdage muligheder for at tjene penge og være forberedt på fremtiden.

For hver artikel giver du:

1) "kategori" - PRÆCIS ÉN fra denne liste (skriv navnet nøjagtigt):
- Lanceringer: nye modeller, produkter og funktioner - inkl. tests,
  benchmarks og sammenligninger af modellers ydeevne
- Hverdags-AI: værktøjer og funktioner almindelige mennesker selv kan bruge
- Penge & marked: investeringer, opkøb, økonomi, aktier, forretning
- Politik & jura: lovgivning, retssager, ophavsret, sanktioner, regulering
- Samfund & etik: jobs, deepfakes, sikkerhed, strømforbrug, AI's påvirkning af samfundet
- Forskning: videnskabelige artikler, metoder og gennembrud

2) "prio" - vigtighed 1-10 for læseren:
- 9-10: store modellanceringer, ægte gennembrud, nye muligheder man selv kan
  udnytte NU, store markedsskift der påvirker almindelige menneskers økonomi
- 6-8: væsentlige produktnyheder, vigtige benchmarks, betydelig regulering,
  tendenser der er værd at forberede sig på
- 3-5: almindelige branchenyheder, mindre opdateringer
- 1-2: inkrementel/niche-forskning, akademiske detaljer, smalle tekniske emner

VÆR NÆRIG MED DE HØJE TAL. Prioriteten styrer, hvad der kommer øverst på
forsiden, og hvad der bliver delt - så inflation ødelægger den. Retningslinje
for en normal dag: de FLESTE artikler ligger på 3-6. Kun ganske få når 7-8.
9-10 er en historie, en dansk avis ville skrive om - typisk én om ugen, ikke
én om dagen. Er du i tvivl mellem to tal, så vælg det laveste.

Svar KUN med et JSON-array i samme rækkefølge som input:
[{{"kategori": "Lanceringer", "prio": 9}}, ...]"""


def klassificer(artikler: list[dict]) -> None:
    """Giver hver artikel indholdskategori + vigtighedsscore via AI (én gang pr. artikel)."""
    mangler = [a for a in artikler if not a.get("kat_ai") or "prio" not in a]
    if not mangler:
        return
    if not API_KEY:
        print("🏷️  Ingen AI-nøgle - beholder kilde-kategorierne")
        return
    print(f"🏷️  Kategoriserer og prioriterer {len(mangler)} artikler …")
    for i in range(0, len(mangler), 30):
        batch = mangler[i:i + 30]
        liste = [{"nr": j + 1, "titel": a["titel"], "tekst": a["resume"][:200]}
                 for j, a in enumerate(batch)]
        try:
            svar = parse_json_svar(hjerne_kald("kategori", SYSTEM_KATEGORI,
                                           json.dumps(liste, ensure_ascii=False), 2500))
            if isinstance(svar, list) and len(svar) == len(batch):
                for a, r in zip(batch, svar):
                    k = str(r.get("kategori", "")).strip()
                    if k in KATEGORIER:
                        a["kategori"] = k
                        a["kat_ai"] = True
                    try:
                        a["prio"] = max(1, min(10, int(r.get("prio", 5))))
                    except (ValueError, TypeError):
                        a["prio"] = 5
        except Exception as fejl:
            print(f"  ⚠️  Kategorisering fejlede: {type(fejl).__name__}")


# ----- Dublet-historier (samme nyhed fra flere medier) -------------------------

SYSTEM_DUBLET = """Du får en nummereret liste af nyhedsartikler (kilde, overskrift og kort resumé) fra forskellige medier.
Find grupper af artikler der dækker PRÆCIS SAMME nyhedsbegivenhed (fx samme
produktlancering, samme retssag, samme opkøb, samme regnskab - omtalt af flere medier).

HUSK: Medierne vinkler den samme begivenhed vidt forskelligt, så overskrifterne
kan se helt forskellige ud. Brug RESUMÉERNE til at afgøre, om kernen er den samme
begivenhed: samme aktør + samme handling + samme tidspunkt.

VIGTIGT: Kun artikler om den samme konkrete begivenhed må grupperes.
Artikler der blot handler om samme emne, firma eller tema, er IKKE dubletter.
To forskellige nyheder om samme firma samme uge er IKKE dubletter.
Er du i tvivl, så lad være med at gruppere.

Svar KUN med et JSON-array af grupper, hver gruppe et array af numre, fx:
[[3, 17, 41], [8, 22]]
Ingen grupper? Svar: []"""


# Ord der er for almindelige til at sige noget om, hvilken historie det er
_DUBLET_STOP = set("""og i at en et den det der som til af for på med om er var blev fra kan
skal vil har have hvis når man sig sin sit sine deres nye ny stor store mere mest end også kun
bare over under mod ved efter før nu ind ud op ned alle andre samme egen selv the a an and of
to in for on with is are was were be been by from that this it its new now more most""".split())


def _dublet_ord(a: dict) -> set:
    """Betydningsbærende ord i en artikel, klippet til seks tegn så dansk
    bøjning ikke spænder ben ('hackede' og 'hacked' bliver til 'hacked')."""
    # `or ""` og `str()` er ikke pynt: et felt kan stå som `null` i cachen, og
    # `.get(f, "")` giver da None, ikke "". Før `_samme_sag` kaldte den her, var
    # det uden konsekvens; nu afgør den, om en artikel bliver slået sammen, og
    # en TypeError her ville vælte hele dublet-fasen for alle artikler.
    t = " ".join(str(a.get(f) or "") for f in ("rubrik", "titel", "resume_da")).lower()
    return {o[:6] for o in re.findall(r"[a-zæøå0-9]+", t)
            if len(o) > 2 and o not in _DUBLET_STOP}


def _samme_historie(a: dict, b: dict) -> bool:
    """Er de to artikler ÅBENLYST den samme historie?

    Bevidst striks: kun når over halvdelen af ordene er fælles OG der er mindst
    fem af dem. Målt på det rigtige arkiv rammer det kun ægte dubletter - fx
    Version2 og Ingeniøren, der deler 83 % af deres ord om den samme historie
    og alligevel stod som to nyheder. De tvivlsomme tilfælde overlades til AI'en."""
    A, B = _dublet_ord(a), _dublet_ord(b)
    if not A or not B:
        return False
    faelles = A & B
    return len(faelles) >= 5 and len(faelles) / min(len(A), len(B)) >= 0.50


def _navne_i(a: dict) -> set:
    """Hvilke navne nævner denne artikel? Rubrik, original titel og resumé.

    Kun de stærke — se `kun_staerke` i `_navne_i_tekst` om hvorfor.
    """
    return _navne_i_tekst(" ".join(str(a.get(f) or "")
                                   for f in ("rubrik", "titel", "resume_da")),
                          kun_staerke=True)


# Hvor lidt må to udgaver af "samme historie" have til fælles? Målt på arkivet
# 27.07 på de 40 sammenlægninger, hvor begge udgaver havde en side at læse:
# 9 var ægte dubletter, 31 var ikke. Ved 15 % står alle 9 ægte tilbage, og 28 af
# de 31 falske bliver frigivet igen. Sættes grænsen til 20 %, ryger en ægte med.
_SAMME_SAG_ANDEL = 0.15


def _samme_sag(primaer: dict, anden: dict) -> bool:
    """Må de to artikler overhovedet være samme historie?

    En vagt, ikke en detektor. `SYSTEM_DUBLET` beder udtrykkeligt modellen om
    IKKE at gruppere to nyheder om samme firma — men den gør det alligevel, og
    før den her fandtes, blev svaret brugt som det kom, med datoerne som eneste
    kontrol. Målt 27.07: 17 grupper havde slugt 49 artikler, og af de 40 par jeg
    kunne læse teksten på, delte 31 næsten ingen ord med den historie, de var
    lagt ind under. "Monday.com fyrer 600" lå under "Anthropic sender billigere
    AI-model på gaden".

    To krav, begge gratis og deterministiske:
      1. **Mindst ét fælles navn.** Handler de om samme begivenhed, nævner de
         samme aktør. Alene er kravet for løst — på et AI-nyhedssite deler tre
         urelaterede historier gerne "Anthropic" — derfor også:
      2. **Mindst 15 % fælles betydningsbærende ord**, målt med `_dublet_ord`,
         altså samme ordsammenligning som den gratis lex-fase bruger.

    Bemærk, at kravene er svagere end `_samme_historie` (50 % og fem ord). Det
    er med vilje: den finder dubletter af sig selv, den her siger kun nej til de
    værste af AI'ens gæt. Bliver den strammere, taber vi ægte sammenlægninger.
    """
    A, B = _dublet_ord(primaer), _dublet_ord(anden)
    if not A or not B:
        return False
    if len(A & B) / min(len(A), len(B)) < _SAMME_SAG_ANDEL:
        return False
    return bool(_navne_i(primaer) & _navne_i(anden))


def _klynger(artikler: list[dict]) -> list[list[dict]]:
    """Samler artikler i klynger, hvor alle hænger sammen med mindst én anden."""
    forael = list(range(len(artikler)))

    def rod(i):
        while forael[i] != i:
            forael[i] = forael[forael[i]]
            i = forael[i]
        return i

    for i in range(len(artikler)):
        for j in range(i + 1, len(artikler)):
            if rod(i) != rod(j) and _samme_historie(artikler[i], artikler[j]):
                forael[rod(j)] = rod(i)
    grupper: dict = {}
    for i, a in enumerate(artikler):
        grupper.setdefault(rod(i), []).append(a)
    return [g for g in grupper.values() if len(g) > 1]


# Hvor meget af taberens tekst gemmer vi med sammenlægningen? Kort med vilje:
# `andre` ligger i articles.json og arves videre kørsel efter kørsel, og
# `_dublet_ord` klipper alligevel hvert ord til seks tegn.
_GEMT_TEKST_MAX = 400

# Slugs på artikler, trin 0 har sluppet løs, mens de IKKE var i dagens feed.
# `_giv_frigivne_deres_canonical_tilbage` kan ikke selv finde dem: deres side
# peger stadig på vinderen, og de står ikke i dagens liste, så funktionens
# normale krav ("levende og selvstændig") kan aldrig blive opfyldt for dem.
_FRIGIVNE_UDEN_FEED: set = set()


def _tekst_fra_artikelside(slug: str) -> dict | None:
    """Rubrik og resumé læst ud af en frossen artikelside.

    Siden blev skrevet dengang, artiklen var sin egen historie, og de to felter
    står stadig i `og:title` og `og:description`. Det er den samme tekst,
    `_dublet_ord` og `_navne_i` ellers ville have fået fra dagens liste.
    """
    try:
        raa = (ARTIKEL_MAPPE / f"{slug}.html").read_text(encoding="utf-8")
    except (OSError, ValueError):
        # ValueError dækker UnicodeDecodeError på en halvskrevet fil. Trin 0 var
        # før et rent opslag i en dict og kunne ikke fejle; nu rører det disken,
        # og en enkelt beskadiget side må ikke vælte dublet-fasen for alle.
        return None

    def _felt(navn: str) -> str:
        fundet = re.search(rf'<meta property="og:{navn}" content="([^"]*)"', raa)
        return html.unescape(fundet.group(1)) if fundet else ""

    rubrik = _felt("title")
    if not rubrik:
        return None
    return {"rubrik": rubrik, "titel": rubrik, "resume_da": _felt("description")}


def _taberens_udgave(kilde: dict, pr_link: dict) -> dict | None:
    """Skaf taberens tekst, så en gammel sammenlægning kan efterprøves.

    Frigivelsen i trin 0 kræver et BEVIS: to tekster, der kan holdes op mod
    hinanden. Før den her fandtes, var dagens liste den eneste kilde til
    taberens tekst — og `articles.json` bygges forfra af feedsene hver kørsel,
    mens `andre` arves videre fra sidste fil. Taberen forsvinder altså ud af
    listen efter få dage, mens sammenlægningen bliver stående for evigt. Målt
    27.07: **0 af 16 tabere var i dagens liste**, så frigivelsen kunne fyre for
    ingen af dem, uanset hvor forkerte de var.

    Tre steder at hente teksten, i faldende troværdighed:
      1. dagens liste — hele artiklen,
      2. `rubrik`/`resume_da` gemt i selve `andre`-posten (gemmes herfra),
      3. den frosne side i `artikel/`.

    Findes teksten ingen af stederne, returneres None, og der sker ingenting.
    Et fravær er stadig ikke et bevis.
    """
    link = kilde.get("link")
    if not isinstance(link, str) or not link:
        return None                      # `andre` kommer fra en fil, ikke fra os
    if link in pr_link:
        return pr_link[link]
    if kilde.get("rubrik"):
        return {"rubrik": kilde["rubrik"], "titel": kilde["rubrik"],
                "resume_da": kilde.get("resume_da") or ""}
    return _tekst_fra_artikelside(_artikel_slug(link))


def _deler_intet(vinder: dict, taber: dict) -> bool:
    """Deler de to udgaver så lidt, at ingen kan påstå, de er samme historie?

    `_samme_sag` står på to ben — fælles ord OG fælles navn — og siger nej, så
    snart ét af dem falder. Her skal BEGGE falde. Forskellen er ikke teoretisk:
    23 % af siderne i arkivet nævner slet intet stærkt navn, og for dem kan
    `_samme_sag` aldrig sige ja, uanset hvor ens teksterne er. Brugte
    frigivelsen `_samme_sag` alene, ville en ægte dublet uden navn i rubrikken
    blive splittet op i to sider, der konkurrerer om den samme søgning.
    """
    A, B = _dublet_ord(vinder), _dublet_ord(taber)
    if not A or not B:
        return False                     # ingen tekst er ikke et bevis
    if len(A & B) / min(len(A), len(B)) >= _SAMME_SAG_ANDEL:
        return False
    return not (_navne_i(vinder) & _navne_i(taber))


def _skal_frigives(vinder: dict, kilde: dict, pr_link: dict) -> bool:
    """Skal den her `andre`-post slippes løs igen?

    Er taberen i dagens liste, er svaret som hidtil: vagten siger nej. En
    fejlagtig frigivelse er ufarlig dér, for begge udgaver er levende, og
    lex-fasen eller AI-fasen samler dem bare igen længere nede i samme kørsel.

    Er taberen VÆK fra feedet, findes den korrektion ikke — der er ingen anden
    udgave at samle med, hverken i dag eller i morgen. Derfor et strengere
    bevis: `_deler_intet`, altså at de to udgaver hverken deler ord eller navne.
    Det er strengere end `_samme_historie`, som lex-fasen samler på, og det
    koster: målt 27.07 frigiver den strenge regel 2 af 16 par i stedet for 4.
    De to par, der bliver liggende, er «Er åben AI virkelig farligt?», som
    deler 28 % af sine ord med vinderen, og «Claude taler nu ud med tre
    stærke hjerner», som deler navnet "anthropic" med sin vinder. En
    frigivelse, vi ikke kan fortryde, skal ikke bygge på så tyndt et grundlag.
    """
    if not isinstance(kilde, dict):
        return False
    taber = _taberens_udgave(kilde, pr_link)
    if taber is None or _samme_sag(vinder, taber):
        return False
    if kilde.get("link") in pr_link:
        return True
    if not _deler_intet(vinder, taber):
        return False
    _FRIGIVNE_UDEN_FEED.add(_artikel_slug(kilde["link"]))
    return True


def _rul_arven_tilbage(vinder: dict, beholdt: list, frigivne: list) -> None:
    """Giv vinderen sit eget tidspunkt og sit eget billede tilbage.

    Frigivelsen fjernede taberen fra `andre` og standsede dér. Men en
    sammenlægning giver også vinderen det TIDLIGSTE `foerst_set` blandt
    medlemmerne og lader den arve taberens billede, hvis den selv mangler et —
    og de to ting blev stående. Målt 28.07: begge de to artikler, der blev
    frigivet 27.07, står stadig med et `foerst_set`, der er næsten to døgn
    tidligere end deres egen udgivelsestid, fordi tiden kom fra den historie,
    de ikke længere er samlet med. Forsiden grupperer efter `foerst_set`, så
    de ligger under 23. juli, selvom de udkom 25.

    Bliver der kilder tilbage, er svaret ikke vinderens eget tidspunkt, men det
    tidligste af vinderens eget og de tilbageværendes — sammenlægningen gælder
    jo stadig for dem.

    Kan tiden ikke gives tilbage, sker der INGENTING. `eget_foerst_set`
    skrives først fra i dag, så sammenlægninger fra før i dag har den ikke, og
    et gæt ville flytte en historie på forsiden uden dækning. De to artikler i
    docstringen ovenfor er derfor IKKE rettet af den her funktion — de blev
    frigivet i går, og deres eget tidspunkt findes ikke længere nogen steder.
    De ruller ud af feedet af sig selv. Se arbejdsloggen 28.07.
    """
    eget = vinder.get("eget_foerst_set")
    if eget:
        tider = [eget] + [str(k.get("foerst_set") or "")
                          for k in beholdt if isinstance(k, dict)]
        # `eget_foerst_set` bliver stående, også når den sidste kilde er væk.
        # Det er ikke et arbejdsfelt, men en permanent oplysning om artiklen:
        # hvornår vi så den. Ryddes den op, står historien uden dækning næste
        # gang den bliver sammenlagt, og så kan tiden aldrig gives tilbage igen.
        vinder["foerst_set"] = min(t for t in tider if t)

    laant = vinder.get("laant_billede")
    if not isinstance(laant, dict):
        return
    if not any(isinstance(k, dict) and k.get("link") == laant.get("fra")
               for k in frigivne):
        return

    # Billedet blev tegnet til taberens historie. Bliver det stående,
    # illustrerer vinderen sig selv med en anden nyhed — punkt 5. Filen
    # slettes ikke: taberens frosne side i `artikel/` peger stadig på den,
    # og `_BILLED_I_HTML` holder oprydningen fra den. Vinderen får sit eget
    # billede ved næste kørsel (~$0,03 under loftet i `lav_billeder`).
    #
    # Kun hvis værdien stadig ER den lånte. Står der noget andet, har
    # oprydningen eller `lav_billeder` allerede givet vinderen sit eget, og
    # dét må en frigivelse ikke rive af. Samme prøve på motivet for sig:
    # `udfyld_billedmotiver` kan have skrevet et nyt motiv til det gamle
    # billede, og de to felter kan derfor godt være ude af trit.
    if vinder.get("billede") == laant.get("billede"):
        vinder.pop("billede", None)
    if laant.get("motiv") and vinder.get("billedmotiv") == laant["motiv"]:
        vinder.pop("billedmotiv", None)
    vinder.pop("laant_billede", None)


def _saet_foerst_set(artikler: list[dict], kendte: dict, nu: datetime,
                     eget_kendt: dict | None = None) -> None:
    """Sæt "hvornår så vi den" — og gem én gang for alle, at tiden er dens egen.

    `eget_foerst_set` sættes PRÆCIS her og kun her, i det øjeblik artiklen ses
    for første gang. Det er det eneste sted i hele kørslen, hvor tiden med
    sikkerhed er artiklens egen: ingen sammenlægning har rørt den endnu.

    Feltet er hele grundlaget for, at en frigivelse kan give tiden tilbage (se
    `_rul_arven_tilbage`). Det blev først forsøgt sat inde i `_slaa_sammen`, og
    det holdt ikke: dér er `foerst_set` allerede lånt, hvis historien var
    sammenlagt i forvejen, og de vagter, man kan opfinde imod det ("har den
    `andre`?"), falder alle sammen — trin 0 tømmer selv `andre` få linjer før,
    og `omskriv_nye` genskaber kun `andre` bag sektioner-porten. Ved fødslen
    kan spørgsmålet ikke stilles forkert.

    `eget_kendt` bærer feltet videre fra sidste fil. Den læses samme sted som
    `kendte` og med samme port — ikke gennem `cache`, som kræver en `rubrik`.
    Ellers ville én kørsel uden AI-nøgle slette feltet permanent for alt, der
    blev født den dag.

    Prisen er ét felt pr. artikel i `articles.json` — målt 28.07: 145 artikler
    × ~45 tegn ≈ 6,5 kB rå af en fil på 419 kB, altså 1,6 %.
    """
    eget_kendt = eget_kendt or {}
    for a in artikler:
        kendt = kendte.get(a["link"])
        a["foerst_set"] = kendt or nu.isoformat()
        if not kendt:
            a["eget_foerst_set"] = a["foerst_set"]
        elif eget_kendt.get(a["link"]):
            a["eget_foerst_set"] = eget_kendt[a["link"]]


# Hvor langt FØR sin egen udgivelsestid en artikel må være set, før tallet
# ikke længere kan være sandt. Målt 28.07 på 163 udgaver af `articles.json`
# (hele historikken): kun FIRE artikler uden `andre` har nogensinde haft
# `foerst_set` før `dato`. To er lovlige og ligger på 5,54 t og 0,55 t — et
# feed, der serverer en artikel lidt før udgivelsestidspunktet. De to andre er
# de kendte fejl på 40,5 t og 47,0 t. Grænsen er sat midt i det hul, med over
# fire gange luft til begge sider.
LAANT_TID_GRAENSE_TIMER = 24


def _gulv_paa_laante_tider(artikler: list[dict]) -> int:
    """Ret et lånt tidsstempel, som ingen frigivelse kan give tilbage.

    `_rul_arven_tilbage` kan kun hjælpe de historier, der har et
    `eget_foerst_set`. To artikler blev frigivet 27.07, FØR det felt fandtes,
    og står derfor med et tidspunkt, de arvede af en historie, de ikke længere
    hører sammen med. Målt i git 28.07 — det er ikke et skøn:

      «Strømsvigt i Washington» havde selv 2026-07-25T16:26:44 (commit
      05ce75b) og bærer i dag 2026-07-23T20:37:15.313153, som er PRÆCIS
      `foerst_set` på «Eks-googlere bag AegisAI» (commit c137a3d), den kilde,
      den var sammenlagt med. Samme mønster for «Biblioteker afholder
      'Avoiding AI'-workshops».

    Forsiden dag-grupperer efter `foerst_set` (`index.html` linje 1517-1522),
    så begge ligger under 23. juli, selvom de udkom 25. `dato` rammer den
    rigtige dag for dem begge.

    Vagterne er der, fordi rettelsen ikke må blive et gæt: kun artikler UDEN
    kilder (så `_rul_arven_tilbage` ikke er det rigtige svar), UDEN
    `eget_foerst_set` (så vi ikke har sandheden i forvejen) og med et
    forspring over grænsen. Kaldes EFTER frigivelses-løkken, ikke før: en
    gammel historie, hvis sidste kilde slippes fri i dag, har hverken `andre`
    eller `eget_foerst_set`, og skal rettes i samme kørsel.

    Selvoprydende, men ikke i dag: hver artikel, der fødes fra 28.07, får et
    `eget_foerst_set` og er dermed uden for funktionens rækkevidde for altid.
    Tilbage står den bestand, der lå i `articles.json` før den dato — den
    ruller ud af feedet i løbet af dage. Så længe den findes, er der ét kendt
    hul: retter en udgiver sin `pubDate` mere end et døgn frem for en af de
    gamle artikler, flytter gulvet dens `foerst_set` med op én gang. De 25
    arXiv-artikler er de mest udsatte, fordi de er undtaget fra AI-dubletfasen
    og derfor aldrig har `andre`. Prisen er, at én historie kan hoppe én dag
    på forsiden; det er mindre end de to, der ligger forkert i dag.
    """
    graense = timedelta(hours=LAANT_TID_GRAENSE_TIMER)
    rettet = 0
    for a in artikler:
        if a.get("andre") or a.get("eget_foerst_set"):
            continue
        fs, da = a.get("foerst_set"), a.get("dato")
        if not fs or not da:
            continue
        try:
            set_tid = datetime.fromisoformat(str(fs).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        ud_tid = da if isinstance(da, datetime) else None
        if ud_tid is None:
            try:
                ud_tid = datetime.fromisoformat(str(da).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
        if set_tid.tzinfo is None:
            set_tid = set_tid.replace(tzinfo=timezone.utc)
        if ud_tid.tzinfo is None:
            ud_tid = ud_tid.replace(tzinfo=timezone.utc)
        if ud_tid - set_tid <= graense:
            continue
        a["foerst_set"] = ud_tid.isoformat()
        rettet += 1
        print(f"  🕒 «{(a.get('rubrik') or a.get('titel') or '')[:52]}» blev sat til"
              f" {str(a['foerst_set'])[:10]} — tidspunktet var lånt af en"
              f" sammenlægning, der er fortrudt")
    if rettet:
        print(f"🕒 {rettet} artikler fik en dato, forsiden kan gruppere rigtigt efter")
    return rettet


def saml_dublet_historier(artikler: list[dict]) -> list[dict]:
    """Finder nyheder som flere medier dækker, beholder den bedste udgave og
    gemmer de øvrige som ekstra kilder på historien ("andre")."""
    # 0) håndhæv tidligere samlinger: artikler der allerede er registreret som
    #    ekstra kilde under en anden historie, skal blive væk.
    #
    #    MEN først: slip dem løs, der aldrig burde have været samlet. Uden det
    #    her er en fejlsammenlægning permanent — den står i `andre` og bliver
    #    håndhævet hver kørsel, også efter `_samme_sag` er kommet til. Målt
    #    27.07: 40 af de 49 samlede par kunne læses, og 31 af dem delte næsten
    #    ingen ord med den historie, de lå under. De var låst for evigt.
    #
    #    Frigivelsen kræver et BEVIS, ikke et fravær: begge udgaver skal kunne
    #    LÆSES, og vagten skal sige nej. Teksten må gerne komme fra det, vi
    #    gemte ved sammenlægningen, eller fra taberens frosne side — se
    #    `_taberens_udgave`. Kravet om at begge stod i dagens liste var i
    #    praksis et krav om, at fejlen blev opdaget inden for få dage: målt
    #    27.07 var 0 af 16 tabere tilbage i feedet. Kan teksten ikke skaffes,
    #    sker der stadig ingenting — se `_dubletsider_paa_disk` om hvorfor det er
    #    vigtigt, at en enkelt kørsel ikke kan vende et valg.
    pr_link = {a["link"]: a for a in artikler if a.get("link")}
    _FRIGIVNE_UDEN_FEED.clear()
    frigivet = 0
    for a in artikler:
        kilder = a.get("andre")
        if not isinstance(kilder, list) or not kilder:
            continue
        beholdt = [k for k in kilder if not _skal_frigives(a, k, pr_link)]
        if len(beholdt) == len(kilder):
            continue
        for k in kilder:
            if k in beholdt:
                continue
            taber = _taberens_udgave(k, pr_link) or {}
            print(f"  ↩️  Frigivet: «{(taber.get('rubrik') or k.get('kilde') or '')[:52]}»"
                  f" var lagt under «{(a.get('rubrik') or a['titel'])[:52]}»")
        frigivet += len(kilder) - len(beholdt)
        if beholdt:
            a["andre"] = beholdt
        else:
            a.pop("andre", None)
        _rul_arven_tilbage(a, beholdt, [k for k in kilder if k not in beholdt])
    if frigivet:
        print(f"↩️  {frigivet} artikler var samlet under en historie, de ikke handler om")

    _gulv_paa_laante_tider(artikler)

    kendte_dubletter = {k["link"] for a in artikler for k in a.get("andre", [])}
    artikler = [a for a in artikler if a["link"] not in kendte_dubletter]

    # 1) Tag de ÅBENLYSE først, uden at spørge nogen. En model, der skal
    #    sammenligne 130 artikler i ét hug, overser det indlysende: Version2 og
    #    Ingeniøren stod som to nyheder om den samme historie, selvom de delte
    #    83 % af deres ord. Det er ikke en svær vurdering - det er en, ingen
    #    havde stillet. Gratis, øjeblikkeligt og uden risiko for at gætte.
    fjern_lex: set = set()
    for gruppe in _klynger([a for a in artikler if a.get("rubrik")]):
        datoer = [m["dato"] for m in gruppe if m.get("dato")]
        if datoer and (max(datoer) - min(datoer)) > timedelta(days=3):
            continue
        fjern_lex |= _slaa_sammen(gruppe)
    if fjern_lex:
        artikler = [a for a in artikler if a["link"] not in fjern_lex]
        print(f"🔗 Ordsammenligning samlede {len(fjern_lex)} åbenlyse dubletter")

    if not API_KEY:
        return artikler
    # forskningsartikler (arXiv) dublerer aldrig nyhedsmedierne - spring dem over.
    # Dubletter opstår inden for få dage, så vi sammenligner de sidste 5 dages
    # artikler (op til 130) i stedet for blot de 90 nyeste i arkivet.
    graense = datetime.now(timezone.utc) - timedelta(days=5)
    kandidater = [a for a in artikler
                  if a["kilde"] != "arXiv cs.AI"
                  and (a.get("dato") is None or a["dato"] >= graense)][:130]
    if len(kandidater) < 2:
        return artikler

    def _linje(i: int, a: dict) -> str:
        # dansk rubrik + resumé gør det muligt at genkende samme historie
        # bag vidt forskellige overskrifter
        resume = (a.get("resume_da") or a.get("resume") or "").replace("\n", " ").strip()[:150]
        rubrik = (a.get("rubrik") or "").strip()
        tekst = f"{i+1}. [{a['kilde']}] {a['titel']}"
        if rubrik:
            tekst += f" / {rubrik}"
        if resume:
            tekst += f" — {resume}"
        return tekst

    liste = "\n".join(_linje(i, a) for i, a in enumerate(kandidater))
    grupper = None
    for forsoeg in (1, 2):
        try:
            grupper = parse_json_svar(hjerne_kald("dublet", SYSTEM_DUBLET, liste, 1500))
            assert isinstance(grupper, list)
            break
        except Exception as fejl:
            print(f"  ⚠️  Dublet-tjek fejlede (forsøg {forsoeg}): {type(fejl).__name__}")
            grupper = None
    if grupper is None:
        return artikler

    fjern: set[str] = set()
    samlet = 0
    for gruppe in grupper:
        try:
            medlemmer = [kandidater[int(n) - 1] for n in gruppe
                         if 1 <= int(n) <= len(kandidater)]
        except (ValueError, TypeError):
            continue
        if len(medlemmer) < 2:
            continue
        # sikkerhedsregel: samme begivenhed udgives inden for få dage - er
        # spredningen større, er det næsten sikkert en fejlgruppering
        datoer = [m["dato"] for m in medlemmer if m.get("dato")]
        if datoer and (max(datoer) - min(datoer)) > timedelta(days=3):
            continue
        fjernet = _slaa_sammen(medlemmer, vagt=_samme_sag)
        fjern.update(fjernet)
        samlet += len(fjernet)
    if samlet:
        print(f"🔗 AI'en samlede {samlet} dublet-artikler under deres hovedhistorier")
    return [a for a in artikler if a["link"] not in fjern]


def _indholdsvaegt(m: dict) -> int:
    """Hvor meget genfortalt indhold har vi faktisk om denne udgave?

    Bruges til at vælge hovedhistorie, når flere medier har dækket det samme.
    Målt på arkivet: uden det her vandt OpenAI Blogs egen pressemeddelelse over
    to Ars Technica-udgaver af samme historie - 1.417 tegn diplomatisk tekst
    frem for 2.798 tegn med de konkrete detaljer. Pressemeddelelser er næsten
    altid tyndere end uafhængig dækning, og de stod bare først i listen.
    """
    vaegt = 0
    for felt in ("resume_da", "betydning"):
        vaegt += len(str(m.get(felt) or ""))
    for felt in ("sektioner", "detaljer", "pointer", "noegletal", "figurer"):
        v = m.get(felt)
        if isinstance(v, (list, tuple, dict)):
            vaegt += len(str(v))
        elif v:
            vaegt += len(str(v))
    return vaegt


def _slaa_sammen(medlemmer: list[dict], vagt=None) -> set:
    """Gør én gruppe til én historie. Returnerer de links, der skal væk.

    `vagt` er en funktion `(primaer, anden) -> bool`, der kan sige nej til et
    enkelt medlem, efter hovedhistorien er valgt. Den bruges kun på AI'ens
    grupper (se `_samme_sag`); den gratis ordsammenligning i `_klynger` har
    allerede sit eget, strengere krav og sendes ind uden vagt.
    """
    # Behold den med mest indhold: brief > dansk rubrik > nyeste.
    # MEN aldrig en kilde med arkivforbud, hvis vi har et alternativ: bliver
    # Version2 hovedhistorie, mister historien sin artikelside og sin
    # genfortælling - selvom Ars Technica også dækkede den og gerne må arkiveres.
    frie = [m for m in medlemmer if not m.get("kun_aktuel")] or medlemmer
    # Inden for hvert trin: den med MEST indhold, ikke den der tilfældigvis stod
    # først. Det var dét, kommentaren ovenfor lovede - men next() tog den første.
    #
    # Trin 1 var før `m.get("brief")`, og dét felt er dødt: SYSTEM_BRIEF_ARTIKEL
    # beder om "sektioner", aldrig om "brief", så `r.get("brief", "")` er altid
    # tom. Målt på arkivet: 0 af 105 artikler har brief, 78 har sektioner.
    # Trinnet kunne altså aldrig ramme, og prioriteringen var i praksis kun
    # ét trin. `sektioner` er det felt, der faktisk betyder "fuld genfortælling".
    # Bemærk: porten skal spørge til REELT indhold, ikke bare til at feltet
    # findes. En liste med tolv tomme sektioner er sand, og ville ellers slå en
    # udgave med 800 tegn rigtig tekst - den anden ville aldrig komme i puljen,
    # så vægten blev aldrig sammenlignet.
    def _har_tekst(m: dict) -> bool:
        sek = m.get("sektioner")
        if not isinstance(sek, (list, tuple)):
            return bool(sek)
        return any(isinstance(s, dict) and str(s.get("tekst") or "").strip()
                   for s in sek)

    pulje = [m for m in frie if _har_tekst(m)] \
         or [m for m in frie if m.get("rubrik")] \
         or frie
    primaer = max(pulje, key=_indholdsvaegt)
    andre = [m for m in medlemmer if m is not primaer]

    # Vagten kører HER — efter hovedhistorien er valgt, men før noget arves.
    # Rækkefølgen er ikke tilfældig: nedenfor overtager primæren taberens
    # tidspunkt og hans billede, og et medlem, vi er ved at afvise, skal ikke
    # have lov at flytte hovedhistoriens dato eller forære sit billede væk.
    if vagt is not None:
        afvist = [m for m in andre if not vagt(primaer, m)]
        andre = [m for m in andre if vagt(primaer, m)]
        for m in afvist:
            print(f"  ⛔ Ikke samme historie som «{(primaer.get('rubrik') or primaer['titel'])[:48]}»"
                  f" — beholdt: «{(m.get('rubrik') or m['titel'])[:48]}»")
        if not andre:
            return set()

    # Kun de medlemmer, der faktisk BLIVER i historien, må aflevere noget til
    # den. `medlemmer` er hele gruppen, som AI'en foreslog den — også dem,
    # vagten lige har afvist ovenfor. Bruges den liste, forærer en afvist
    # artikel både sit tidspunkt og sit billede væk til en historie, den
    # hverken hører til eller står opført under, og ingen kan siden se hvorfra.
    # Kommentaren over vagten lovede allerede det her; koden gjorde det ikke.
    bidragydere = [primaer] + andre

    # En historie bliver ikke NY igen, bare fordi et nyt medie skriver om den
    # i dag. Arv det TIDLIGSTE tidspunkt, nogen af udgaverne blev set - ellers
    # hopper gårsdagens historie op på forsiden med et NY-mærke, og læseren
    # bliver præsenteret for det samme to dage i træk.
    #
    # Men gem vinderens EGET tidspunkt først. Frigivelsen i trin 0 fjerner
    # taberen fra `andre` og standser dér: uden det her bliver vinderen stående
    # med en fortid, der stammer fra en historie, den ikke længere er samlet
    # med. Forsiden sorterer og dag-grupperer efter `foerst_set`, så en
    # historie fra i går kan ligge under forgårs dato uden NY-mærke.
    # Vinderens eget tidspunkt gemmes IKKE her — det gøres ved fødslen i
    # `main()`, hvor tiden med sikkerhed er artiklens egen. Se kommentaren dér.
    tider = [m.get("foerst_set") for m in bidragydere if m.get("foerst_set")]
    if tider:
        primaer["foerst_set"] = min(tider)

    # Arv billedet, hvis vi allerede har betalt for et. Uden det her laves der
    # et nyt billede, hver gang en historie får en ekstra kilde - og det gamle
    # slettes bagefter som forældreløst. Dobbelt spild.
    #
    # `laant_billede` husker både HVEM der lånte ud og HVAD der blev lånt.
    # Kilden alene er ikke nok: billedfilen kan nå at blive skiftet ud, før en
    # frigivelse kommer — oprydningen nulstiller `billede`, når filen er væk,
    # og `lav_billeder` tegner så vinderens eget. Uden den gemte værdi ville
    # frigivelsen rive dét nye, betalte billede af igen.
    if not primaer.get("billede"):
        for m in andre:
            if m.get("billede"):
                primaer["billede"] = m["billede"]
                laant = {"fra": m.get("link") or "", "billede": m["billede"]}
                if not primaer.get("billedmotiv") and m.get("billedmotiv"):
                    primaer["billedmotiv"] = m["billedmotiv"]
                    laant["motiv"] = m["billedmotiv"]
                primaer["laant_billede"] = laant
                break

    primaer.setdefault("andre", [])
    har = {k["link"] for k in primaer["andre"]}
    # Gem taberens tekst med, ikke bare hans adresse. Uden den kan en forkert
    # sammenlægning aldrig fortrydes: `articles.json` bygges forfra af feedsene
    # hver kørsel, mens `andre` arves videre, så taberen er væk om få dage — og
    # frigivelsen i trin 0 kræver to tekster at måle på. Se `_taberens_udgave`.
    # `foerst_set` gemmes med af samme grund: frigives én af tre kilder, skal
    # tiden regnes om af dem, der bliver — ikke sættes tilbage til nul.
    primaer["andre"] += [{"kilde": m["kilde"], "link": m["link"],
                          "rubrik": str(m.get("rubrik") or m.get("titel") or "")[:_GEMT_TEKST_MAX],
                          "resume_da": str(m.get("resume_da") or "")[:_GEMT_TEKST_MAX],
                          "foerst_set": str(m.get("foerst_set") or "")}
                         for m in andre if m["link"] not in har]
    return {m["link"] for m in andre}


# ----- AI-billeder til tophistorierne -----------------------------------------

BILLED_STIL_VERSION = "v5"   # bump denne for at få ALLE billeder lavet om i ny stil


def _billed_navn(link: str) -> str:
    import hashlib
    return hashlib.md5((link + BILLED_STIL_VERSION).encode()).hexdigest()[:16] + ".jpg"


# Scenetone pr. kategori - seks SARTE toner i samme lyse familie, så forsiden
# får rytme uden at blive kaotisk, når kategorierne blandes. Det fælles lys,
# materialerne og den lilla accent binder det hele sammen.
KATEGORI_FARVER = {
    "Lanceringer":    "sart lilla-tonet (#e7e3f7)",
    "Hverdags-AI":    "sart salviegrøn (#e2eadd)",
    "Penge & marked": "sart varm sandfarvet (#f0e4c8)",
    "Politik & jura": "sart støvet dueblå (#dde5ee)",
    "Samfund & etik": "sart rosa-terracotta (#f4e0d9)",
    "Forskning":      "sart kølig gråblå (#e2e7ee)",
}


def _gem_billede(raa: bytes, sti: Path) -> None:
    """Gemmer billedet - nedskaleret til web-størrelse hvis pillow findes."""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(raa)).convert("RGB")
        if img.width > BILLED_BREDDE:                 # nedskalér kun - opskalér aldrig
            h = int(img.height * BILLED_BREDDE / img.width)
            img = img.resize((BILLED_BREDDE, h), Image.LANCZOS)
        img.save(sti, "JPEG", quality=86)
    except ImportError:
        sti.write_bytes(raa)


SYSTEM_MOTIV = """Du er art director på et dansk nyhedssite. For hver artikel
beskriver du i max 25 ord ÉN konkret scene med 1-3 genkendelige genstande, der
fortæller PRÆCIS artiklens pointe - så en læser kan gætte historien ud fra
billedet alene. Ingen mennesker, ingen tekst i billedet. Vær specifik
("en flyttekasse fuld af robotarme med prisskilt på"), aldrig generisk
("abstrakte former der symboliserer AI").
Beskriv KUN genstandene - ALDRIG omgivelser, rum eller baggrund (ingen
serverrum, kontorer, værksteder eller gader). Genstandene står altid på en
ren, enkel studiebaggrund.
Svar KUN med et JSON-array i samme rækkefølge som input:
[{"motiv": "..."}, ...]"""


KORT_PR_DAG = 5     # hero + 4 store kort - skal følge index.html


def _kort_vaegt(a: dict) -> int:
    """Samme vægt som forsidens prioAf() i index.html. Afviger den, vælger
    crawleren ét sæt kort og forsiden et andet - og forskellen bliver til
    kort med tomt billedfelt."""
    return (a.get("prio") if a.get("prio") is not None else 5) + (1 if a.get("andre") else 0)


def _kort_artikler(artikler: list[dict]) -> set:
    """Links på de artikler, der vises som BILLEDKORT på forsiden: de 5
    vigtigste pr. opdagelsesdag PR. FANE (hero + 4 kort). Resten vises som
    tekstlinjer og bruger sitets genererede kunst - dem koster vi ikke
    AI-billeder på.

    Funktionen er en spejling af index.html. Hver gang de to er uenige om,
    hvad der er et kort, står der et stort kort på forsiden med et tomt
    billedfelt. Tre ting holder dem sammen:

    1. **Fanerne deler ikke artikler.** "Nyheder" viser alt UNDTAGEN Forskning,
       "Forskning" viser kun Forskning, og hver fane tegner sine egne 5 kort.
       Blandede vi dem her, ville en forskningsartikel bruge en billedplads,
       ingen ser på nyhedsfanen, mens kortet, der faktisk tog pladsen dér,
       stod uden billede.
    2. **Vægten er den samme** som forsidens - inkl. flerkilde-bonussen.
    3. **`kun_aktuel` udelades IKKE.** Arkivforbuddet gælder udgiverens tekst:
       vi gemmer ikke artiklen og bygger ingen artikelside. Men billedet er
       vores eget, og rubrik/resume_da er vores egen omskrivning, så et kort
       med arkivforbud må gerne illustreres. Forsiden viser dem som helt
       almindelige kort - udelod vi dem, stod prio 7-historier med tomt
       billedfelt (målt 26.07: to gjorde).
    """
    dage: dict = {}
    for a in artikler:
        if not a.get("rubrik"):
            continue
        dag = str(a.get("foerst_set") or a.get("dato") or "")[:10]
        fane = "forskning" if a.get("kategori") == "Forskning" else "nyheder"
        dage.setdefault((dag, fane), []).append(a)
    valgte: set = set()
    for gruppe in dage.values():
        gruppe = sorted(gruppe, key=_kort_vaegt, reverse=True)
        valgte.update(a["link"] for a in gruppe[:KORT_PR_DAG])
    return valgte


def udfyld_billedmotiver(artikler: list[dict]) -> None:
    """Sørger for at billedkandidaterne har et konkret art director-motiv,
    før der genereres billeder."""
    kandidater = _kort_artikler(artikler)
    top = [a for a in artikler[:BILLED_ANTAL]
           if a.get("rubrik") and not a.get("billedmotiv")
           and a["link"] in kandidater]
    if not top or not API_KEY:
        return
    print(f"🎬 Finder billedmotiver til {len(top)} artikler …")
    for i in range(0, len(top), 15):
        batch = top[i:i + 15]
        liste = [{"nr": j + 1, "rubrik": a["rubrik"],
                  "resume": a.get("resume_da", ""),
                  "detaljer": a.get("detaljer", [])[:4]}
                 for j, a in enumerate(batch)]
        try:
            svar = parse_json_svar(hjerne_kald("motiv", SYSTEM_MOTIV, json.dumps(liste, ensure_ascii=False), 2000))
            if isinstance(svar, list) and len(svar) == len(batch):
                for a, r in zip(batch, svar):
                    a["billedmotiv"] = str(r.get("motiv", "")).strip()
        except Exception as fejl:
            print(f"  ⚠️  Motiv-kald fejlede: {type(fejl).__name__}")


def _for_lille(sti: Path) -> bool:
    """True hvis et gemt billede er fra dengang vi nedskalerede til 640px."""
    try:
        from PIL import Image
        with Image.open(sti) as img:
            return img.width < 800
    except Exception:
        return False


def lav_billeder(artikler: list[dict]) -> None:
    """Genererer ét AI-billede pr. tophistorie. Billedet laves kun én gang
    (filnavn = hash af linket) og bruges for altid. Kræver GEMINI_API_KEY,
    og at betaling er slået til - ellers springes trinnet bare over."""
    global _billed_model
    if not GEMINI_KEY:
        print("🎨 GEMINI_API_KEY ikke sat - springer AI-billeder over")
        return
    BILLED_MAPPE.mkdir(parents=True, exist_ok=True)

    kandidater = _kort_artikler(artikler)
    top = [a for a in artikler[:BILLED_ANTAL] if a.get("rubrik")]
    lavet, fejl_i_traek = 0, 0
    for a in top:
        navn = _billed_navn(a["link"])
        sti = BILLED_MAPPE / navn
        # Et arvet billede hedder ikke det samme som hash af DETTE link: slår
        # saml_dublet_historier to udgaver sammen, peger den primære artikel på
        # en anden kildes fil. Kiggede vi kun efter vores eget hashnavn, betalte
        # vi for et nyt billede til en historie, der allerede havde et - præcis
        # den dobbelte udgift, arven skulle spare.
        if not sti.exists() and a.get("billede"):
            arvet = BILLED_MAPPE / Path(a["billede"]).name
            if arvet.is_file():
                navn, sti = arvet.name, arvet
        if sti.exists():
            # Gamle billeder i lav opløsning (640px-æraen) laves om én gang -
            # men kun for kort-artikler; tekstlinjer beholder det, de har
            if a["link"] in kandidater and _for_lille(sti):
                sti.unlink()
            else:                                         # allerede lavet - brug det
                a["billede"] = f"data/img/{navn}"
                continue
        if a["link"] not in kandidater:
            continue     # tekstlinje-artikel: genereret kunst er rigeligt
        if lavet >= MAX_BILLEDER_PR_KOERSEL or fejl_i_traek >= 2:
            continue
        farve = KATEGORI_FARVER.get(a.get("kategori"), "varm cremehvid (#f7f3ec)")
        # Art director-motivet fra tekst-AI'en (har læst hele artiklen).
        # Fallback: byg scenen ud fra rubrik + resumé.
        motiv = a.get("billedmotiv") or (
            f"én konkret scene med 1-3 genkendelige genstande, der fortæller "
            f"historien '{a['rubrik']}' ({a.get('resume_da', '')[:120]})")
        prompt = (
            f"SCENEN DER SKAL BYGGES: {motiv}. "
            "Genstandene skal være genkendelige og fortælle netop denne historie - "
            "ikke abstrakt pynt. "
            "STIL: Eksklusiv redaktionel 3D-render i cinematisk stil, som "
            "marketing-art fra et førende tech-brand. Materialerne følger "
            "genstandene (metal ligner metal, papir ligner papir, glas ligner glas) "
            "i en blød, mat, eksklusiv finish - aldrig billig plastik-glans. "
            "BAGGRUND: Altid helt enkel og rolig - en ren, sømløs "
            "studiebaggrund som i eksklusiv produktfotografering. INGEN rum, "
            "interiører, serverrum, reoler, vægge med detaljer eller gade- og "
            "værkstedsmiljøer. Kun en jævn flade med blød farvegradient og "
            "genstandenes egne skygger, så al opmærksomhed samles om "
            "hovedmotivet. "
            "FARVER: Genstandene bruger deres naturlige farver - rige, men let "
            f"afdæmpede. Hele scenen er tonet af sit lys: baggrund og "
            f"lysstemning i {farve}, så billedet hænger sammen med resten af "
            "avisen. Den lilla signaturfarve (#5b4bf0) optræder som én lille, "
            "elegant detalje et sted i scenen. Handler historien om ét bestemt "
            "firma, må genstandenes farver gerne nikke diskret til firmaets "
            "kendte farver (fx Googles fire farver, Metas blå, OpenAIs sorte/hvide) "
            "- men ALDRIG deres logo, navnetræk eller bogstaver. "
            "LYS OG KAMERA: Fotorealistisk studielys med bløde skygger, let "
            "dybdeskarphed, komponeret som eksklusiv produktfotografering med "
            "85 mm-objektiv i tre-kvart vinkel. Ét stort hovedmotiv, elegant "
            "komposition med luft omkring - aldrig en collage. "
            "UNDGÅ ALTID: mennesker, ansigter, hænder, tekst, bogstaver, tal og logoer. "
            "Undgå klichéer som generiske robotter, kredsløb og lysende hjerner - "
            "MEDMINDRE historien konkret handler om dem.")
        body = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"aspectRatio": "16:9"}},
        }).encode()
        try:
            try:
                svar = hent_url(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{_billed_model}:generateContent",
                    data=body, headers={"x-goog-api-key": GEMINI_KEY, "content-type": "application/json"})
            except urllib.error.HTTPError as f:
                if f.code in (400, 404) and _billed_model != BILLED_FALLBACK:
                    print(f"  ℹ️  {_billed_model} ikke tilgængelig - prøver {BILLED_FALLBACK}")
                    _billed_model = BILLED_FALLBACK
                    svar = hent_url(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{_billed_model}:generateContent",
                        data=body, headers={"x-goog-api-key": GEMINI_KEY, "content-type": "application/json"})
                else:
                    raise
            import base64
            for del_ in json.loads(svar)["candidates"][0]["content"]["parts"]:
                data64 = del_.get("inlineData", del_.get("inline_data", {})).get("data")
                if data64:
                    _gem_billede(base64.b64decode(data64), sti)
                    a["billede"] = f"data/img/{navn}"
                    lavet += 1
                    fejl_i_traek = 0
                    break
            time.sleep(GEMINI_PAUSE_SEK)
        except Exception as f:
            fejl_i_traek += 1
            print(f"  ⚠️  Billede fejlede ({a['kilde']}): {type(f).__name__} "
                  f"{'- er betaling slået til på Google-kontoen?' if fejl_i_traek >= 2 else ''}")
    if lavet:
        print(f"🎨 Genererede {lavet} nye artikelbilleder")

    # ryd op: slet billeder for artikler, der er røget ud af listen - men kun
    # dem, ingen side på disken stadig peger på.
    #
    # De to regler trak i hver sin retning: artikelsiderne bliver med vilje
    # stående for evigt (se lav_artikelsider), mens artiklen forsvinder ud af
    # articles.json, så snart kildens RSS-feed holder op med at nævne den -
    # dage, ikke de 30 MAX_DAGE_GAMMEL antyder. Ryddede vi blot efter listen,
    # stod siden tilbage med et brudt billede, et dødt og:image (ødelagt
    # delevisning) og "Image not found" i structured data. Målt 26.07: 25 af 87
    # sider med billede var i præcis den tilstand.
    #
    # Filnavnet er hash af ET link, men en artikel kan pege på et billede, der
    # er hashet ud fra et ANDET: samler saml_dublet_historier to udgaver af
    # samme historie, arver den primære artikel billedet fra en af de andre
    # kilder (se kommentaren dér). Whitelistede vi kun det primære link, slettede
    # oprydningen præcis det billede, artiklen selv peger på - og har historien
    # arkivforbud, findes der ingen artikelside til at redde filen. Derfor tæller
    # både `billede`-feltet og de sammenlagte kilders links med.
    # Målt 27.07: 1 af 81 artikler stod med en billedsti til en slettet fil.
    brugte = set()
    for a in artikler:
        brugte.add(_billed_navn(a["link"]))
        for k in a.get("andre") or []:
            brugte.add(_billed_navn(k["link"]))
        if a.get("billede"):
            brugte.add(Path(a["billede"]).name)
    for mappe, moenster in ((ARTIKEL_MAPPE, "*.html"), (ROOT, "*.html")):
        if not mappe.is_dir():
            continue
        for p in mappe.glob(moenster):
            try:
                brugte |= set(_BILLED_I_HTML.findall(p.read_text(encoding="utf-8")))
            except OSError:
                continue        # en ulæselig side må ikke koste os billederne
    slettet = 0
    for fil in BILLED_MAPPE.glob("*.jpg"):
        if fil.name not in brugte:
            fil.unlink(missing_ok=True)
            slettet += 1
    if slettet:
        print(f"🧹 Slettede {slettet} billeder, ingen side peger på")


def omskriv_nye(artikler: list[dict], cache: dict) -> None:
    """Sætter rubrik/resume_da på artiklerne - fra cache, seed-fil eller Claude."""
    for a in artikler:                       # 1) genbrug alt vi allerede har betalt for
        gammel = cache.get(a["link"])
        if gammel:
            a["rubrik"] = gammel.get("rubrik", "")
            a["resume_da"] = gammel.get("resume_da", "")
            if gammel.get("brief") or gammel.get("sektioner"):
                a["brief"] = gammel.get("brief", "")
                a["sektioner"] = gammel.get("sektioner", [])
                if gammel.get("noegletal") is not None:
                    a["noegletal"] = gammel["noegletal"]
                if gammel.get("figurer") is not None:
                    a["figurer"] = gammel["figurer"]
                if gammel.get("andre"):
                    a["andre"] = gammel["andre"]
                a["detaljer"] = gammel.get("detaljer", [])
                a["betydning"] = gammel.get("betydning", "")
                a["pointer"] = gammel.get("pointer", [])
                a["billedmotiv"] = gammel.get("billedmotiv", "")
            if gammel.get("billede"):
                a["billede"] = gammel["billede"]
                # `laant_billede` følger billedet og kun billedet: forsvinder
                # filen en nat, nulstiller oprydningen `billede`, og så er
                # lånemærket heller ikke sandt længere. Feltet fortæller altså
                # noget om det billede, der ligger der NU — ikke om historien.
                if isinstance(gammel.get("laant_billede"), dict):
                    a["laant_billede"] = gammel["laant_billede"]
            if gammel.get("kat_ai") and gammel.get("kategori"):
                a["kategori"] = gammel["kategori"]
                a["kat_ai"] = True
            if gammel.get("prio") is not None:
                a["prio"] = gammel["prio"]

    # 2) håndlavede omskrivninger fra opsaetning/seeds_da.json (matcher på titel-prefix)
    seed_fil = OPSAETNING / "seeds_da.json"
    if seed_fil.exists():
        try:
            seeds = json.loads(seed_fil.read_text(encoding="utf-8"))
            for a in artikler:
                if a.get("rubrik"):
                    continue
                for s in seeds:
                    if a["titel"].startswith(s["titel_prefix"]):
                        a["rubrik"] = s["rubrik"]
                        a["resume_da"] = s["resume"]
                        break
        except (json.JSONDecodeError, KeyError):
            print("  ⚠️  opsaetning/seeds_da.json kunne ikke læses - springer over")

    mangler = [a for a in artikler if not a.get("rubrik")]
    if not mangler:
        print("✍️  Alle artikler er allerede omskrevet (cache)")
        return
    if not API_KEY:
        print(f"✍️  Ingen AI-nøgle sat (DEEPSEEK_API_KEY/GEMINI_API_KEY) - springer omskrivning over "
              f"({len(mangler)} artikler vises på engelsk)")
        return

    mangler = mangler[:MAX_OMSKRIV_PR_KOERSEL]
    print(f"✍️  Omskriver {len(mangler)} nye artikler til letlæst dansk …")
    for i in range(0, len(mangler), BATCH_STR):
        batch = mangler[i:i + BATCH_STR]
        resultat = kald_ai_batch(batch)
        if not resultat:
            continue
        for a, r in zip(batch, resultat):
            rubrik = str(r.get("rubrik", "")).strip()
            resume = str(r.get("resume", "")).strip()
            if rubrik and resume:
                a["rubrik"] = rubrik
                a["resume_da"] = resume
        print(f"   … {min(i + BATCH_STR, len(mangler))}/{len(mangler)}")


# ----- Manuel genkørsel ------------------------------------------------------

# Manuel genkørsel (workflow-input): "ja" = genskriv HELE arkivet i nyeste format,
# et søgeord (fx "computerhjerner") = genskriv kun artikler hvis rubrik/titel matcher.
# Ordet "betydning" er reserveret: det genskriver kun de artikler, hvis
# "Hvad betyder det for dig?" ikke lever op til kravene (se _betydning_problemer).
# Ellers behandles kun artikler, der aldrig er behandlet.
_GENKOER_RAW = os.environ.get("GENKOER_ALT", "").strip()
GENKOER_ALT = _GENKOER_RAW.lower() in ("ja", "1", "true")
GENKOER_FILTER = "" if _GENKOER_RAW.lower() in ("", "ja", "1", "true", "nej", "no", "false")     else _GENKOER_RAW.lower()


# ----- RSS-feed af vores egne artikler ----------------------------------------

SITE_URL = "https://ainyheder.com"


def _dele_link(link: str) -> str:
    """Adressen vi sender folk til UDEFRA - fra feedet, ugesiden, nyhedsbrevet.

    Førstevalget er den permanente artikelside. `#a=` peger nemlig på KILDENS
    adresse og slås op i `articles.json`, som bygges forfra af feedene hver
    kørsel - så et sådant link lever dage, ikke evigt. Siderne under `artikel/`
    slettes derimod aldrig.

    Slugget er en ren md5 af linket, så opslaget virker også for historier, der
    for længst er ude af `articles.json` - præcis dem, `#a=` ikke kan finde. Vi
    spørger disken frem for `a["side"]`, netop for at ramme dem, og for aldrig
    at love en side, der ikke er skrevet endnu.

    Findes filen ikke, falder vi tilbage til `#a=`. Det er ikke en fejl: 25 af
    84 artikler er `kun_aktuel`, hvor udgiveren forbyder et arkiv, og de SKAL
    ikke have en permanent side. Målt 27.07: 20 af feedets 40 punkter får en
    permanent adresse, og de øvrige 20 er alle `kun_aktuel`.

    Vi følger med vilje IKKE sidens canonical hjem til hovedhistorien, selvom
    46 af 112 sider er dubletter, der peger videre. Målt 27.07: 8 af dem står i
    en kæde (A → B → C), fordi vinderen selv blev slået sammen bagefter, og
    kæderne ender på urelaterede historier - en side om en gratis videoeditor
    peger via to led på "AI Kill Switch Act". At følge dem ville sende læseren
    et forkert sted hen. En dubletside har fuld tekst og er den rigtige
    historie; det er kun dens canonical, der er gal. Kæderne har deres eget
    punkt i køen.
    """
    from urllib.parse import quote
    if link:
        side = f"artikel/{_artikel_slug(link)}.html"
        if (ROOT / side).is_file():
            return f"{SITE_URL}/{side}"
    return f"{SITE_URL}/#a=" + quote(link or "", safe="")


def lav_rss(artikler: list[dict]) -> None:
    """Skriver feed.xml med de nyeste artikler, så man kan abonnere på sitet."""
    from email.utils import format_datetime
    punkter = []
    for a in artikler[:40]:
        if not a.get("rubrik"):
            continue
        led = _dele_link(a["link"])
        try:
            dato = format_datetime(datetime.fromisoformat(a["dato"]))
        except (TypeError, ValueError):
            dato = ""
        punkter.append(
            "<item>"
            f"<title>{html.escape(a['rubrik'])}</title>"
            f"<link>{html.escape(led)}</link>"
            f"<guid isPermaLink=\"false\">{html.escape(a['link'])}</guid>"
            + (f"<pubDate>{dato}</pubDate>" if dato else "")
            + f"<category>{html.escape(a.get('kategori', ''))}</category>"
            f"<description>{html.escape(a.get('resume_da') or a.get('resume', ''))}</description>"
            "</item>")
    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
           "<rss version=\"2.0\"><channel>"
           "<title>AI-nyheder</title>"
           f"<link>{SITE_URL}/</link>"
           "<description>Dagens AI-nyheder på letlæst dansk</description>"
           "<language>da</language>"
           + "".join(punkter) + "</channel></rss>")
    (ROOT / "feed.xml").write_text(xml, encoding="utf-8")
    print(f"📡 Skrev feed.xml med {len(punkter)} artikler")




# ----- Ugens overblik (fredags-digest + nyhedsbrevs-feed) ----------------------

UGE_JSON = ROOT / "data" / "uge.json"
UGE_HTML = ROOT / "uge.html"
UGE_FEED = ROOT / "feed-uge.xml"

SYSTEM_UGE = """Du skriver 'Ugens AI-overblik' for et dansk nyhedssite for
almindelige mennesker. Du får ugens vigtigste artikler og koger dem ned til
ét overblik, man kan læse på fem minutter og føle sig HELT opdateret af.
Skriv levende, letlæst hverdagsdansk. Skriv ALTID "AI" - aldrig "kunstig
intelligens". Ingen clickbait, ingen floskler.

Svar KUN med ét JSON-objekt:
{
 "rubrik": fængende overskrift for ugen, max 10 ord,
 "indledning": 2-3 sætninger der fanger ugens store linje (max 50 ord),
 "historier": de 5 vigtigste historier, hver med:
   [{"overskrift": max 8 ord, "tekst": 50-80 ord om hvad der skete og hvorfor
     det betyder noget, "link": KOPIÉR artiklens link-felt PRÆCIST}, ...],
 "tendens": 40-70 ord: Hvad er ugens røde tråd, og hvad skal man holde øje
   med i næste uge?
}"""


def _uge_side_html(d: dict) -> str:
    """Ugemagasinet: mørk forside, nedtælling og kategorifarvede kort."""
    TONE = {"Lanceringer": "#e7e3f7", "Hverdags-AI": "#e2eadd",
            "Penge & marked": "#f0e4c8", "Politik & jura": "#dde5ee",
            "Samfund & etik": "#f4e0d9", "Forskning": "#e2e7ee"}
    historier = d.get("historier", [])
    # Samme diskopslag som artikelsiderne får af _billedfil: uge.json bærer en
    # billedsti videre i en uge, og filen kan være ryddet imens. Slår vi den
    # ikke op, står ugesiden med brudte billeder og et dødt og:image.
    forside_billede = (_billedfil(historier[0]) if historier else "") or "assets/og.png"
    stats = d.get("stats", {})

    kort = []
    for nr, h in enumerate(historier, 1):
        # uge.json lever en hel uge, og efter få dage er historien ude af
        # articles.json - så et #a=-link her er dødt, længe før ugen er omme.
        led = _dele_link(h.get("link", ""))
        tone = TONE.get(h.get("kategori", ""), "#efece4")
        # uge.json gemmer ikke billedmotivet, så overskriften er alt-teksten
        h_alt = html.escape(str(h.get("overskrift") or "")[:180])
        h_bil = _billedfil(h)
        billede = (f'<div class="k-billede"><img src="{html.escape(h_bil)}" '
                   f'alt="{h_alt}" '
                   'loading="lazy" onerror="this.parentNode.remove()"></div>') if h_bil else ""
        kort.append(f"""<a class="k {'k-flip' if nr % 2 == 0 else ''}" href="{led}" style="--tone:{tone}">
<span class="k-nr">{nr}</span>
{billede}
<div class="k-tekst">
<span class="k-kat">{html.escape(h.get("kategori", ""))}</span>
<h3>{html.escape(h.get("overskrift", ""))}</h3>
<p>{html.escape(h.get("tekst", ""))}</p>
<span class="k-laes">Læs hele historien →</span>
</div></a>""")
    kort_html = "".join(kort)
    dato = datetime.fromisoformat(d["dato"]).strftime("%d.%m.%Y")
    return f"""<!DOCTYPE html>
<html lang="da">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI-nyheder.com · Ugens overblik uge {d.get("uge_nr", "")}</title>
<meta name="description" content="{html.escape(d.get("indledning", ""))[:150]}">
<link rel="canonical" href="{SITE_URL}/uge.html">
<meta name="theme-color" content="#191714">
<meta property="og:title" content="Ugens AI-overblik: {html.escape(d.get("rubrik", ""))}">
<meta property="og:description" content="{html.escape(d.get("indledning", ""))[:150]}">
<meta property="og:image" content="{SITE_URL}/{html.escape(forside_billede)}">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/favicon-192.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/fonts/skrifter.css">
<style>
:root {{ --bg:#f4f2ec; --bg-kort:#fff; --blaek:#191714; --blaek-svag:#6d675d; --linje:#e2ddd2;
--accent:#5b4bf0; --accent-svag:#ecebfd; --radius:20px;
--skygge:0 2px 4px rgba(25,23,20,.05), 0 16px 44px rgba(25,23,20,.10);
--font-ui:"Inter",sans-serif; --font-display:"Fraunces",Georgia,serif; }}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--font-ui);background:var(--bg);color:var(--blaek);line-height:1.6}}
a{{color:inherit;text-decoration:none}}

/* ---- Magasinforsiden ---- */
.omslag{{position:relative;min-height:72vh;display:flex;align-items:flex-end;color:#fff;overflow:hidden;background:#191714}}
.omslag img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.55}}
.omslag::after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(25,23,20,.25) 0%,rgba(25,23,20,.05) 35%,rgba(25,23,20,.88) 100%)}}
.omslag-top{{position:absolute;top:0;left:0;right:0;z-index:3;display:flex;align-items:center;gap:14px;padding:18px 28px}}
.o-brand{{font-family:var(--font-display);font-weight:900;font-size:22px;letter-spacing:-.03em;color:#fff}}
.o-brand em{{font-style:normal;color:#b3aaff}}
.o-tilbage{{margin-left:auto;font-size:13px;font-weight:700;color:#fff;border:1px solid rgba(255,255,255,.4);padding:8px 16px;border-radius:999px;backdrop-filter:blur(6px)}}
.o-tilbage:hover{{background:rgba(255,255,255,.15)}}
.omslag-indhold{{position:relative;z-index:2;padding:0 28px 54px;max-width:900px;margin:0 auto;width:100%}}
.o-kicker{{display:inline-block;background:var(--accent);color:#fff;font-size:11px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;padding:6px 14px;border-radius:999px;margin-bottom:16px}}
.omslag h1{{font-family:var(--font-display);font-weight:900;letter-spacing:-.02em;font-size:clamp(34px,6vw,60px);line-height:1.04;margin-bottom:14px;text-shadow:0 2px 24px rgba(0,0,0,.35)}}
.o-manchet{{font-size:17px;line-height:1.6;max-width:56ch;color:rgba(255,255,255,.92)}}
.o-stats{{display:flex;gap:26px;margin-top:22px;flex-wrap:wrap}}
.o-stat b{{display:block;font-family:var(--font-display);font-size:26px;font-weight:900;line-height:1}}
.o-stat span{{font-size:11.5px;text-transform:uppercase;letter-spacing:.1em;color:rgba(255,255,255,.75)}}

/* ---- Nedtællingen ---- */
main{{max-width:900px;margin:0 auto;padding:54px 24px 80px}}
.ned-titel{{font-family:var(--font-display);font-weight:900;font-size:clamp(22px,3.5vw,30px);letter-spacing:-.01em;margin-bottom:22px}}
.ned-titel em{{font-style:normal;color:var(--accent)}}
.k{{position:relative;display:flex;background:var(--tone,#fff);border:1px solid var(--linje);border-radius:var(--radius);overflow:hidden;box-shadow:var(--skygge);margin-bottom:22px;transition:transform .16s}}
.k:hover{{transform:translateY(-4px) rotate(-.3deg)}}
.k-flip{{flex-direction:row-reverse}}
.k-flip:hover{{transform:translateY(-4px) rotate(.3deg)}}
.k-billede{{flex:0 0 42%;min-height:230px}}
.k-billede img{{width:100%;height:100%;object-fit:cover;display:block}}
.k-tekst{{flex:1;padding:26px 30px;display:flex;flex-direction:column;justify-content:center}}
.k-nr{{position:absolute;top:10px;left:18px;z-index:2;font-family:var(--font-display);font-weight:900;font-size:92px;line-height:1;color:var(--accent);opacity:.16;pointer-events:none}}
.k-flip .k-nr{{left:auto;right:18px}}
.k-kat{{font-size:10.5px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:8px}}
.k h3{{font-family:var(--font-display);font-weight:900;font-size:clamp(20px,3vw,26px);line-height:1.12;margin-bottom:10px}}
.k p{{font-size:15px;line-height:1.7}}
.k-laes{{margin-top:12px;font-size:13px;font-weight:700;color:var(--accent)}}

/* ---- Rød tråd + mail ---- */
.tendens{{background:var(--blaek);color:#fff;border-radius:var(--radius);padding:34px 38px;margin:40px 0 0}}
.tendens b{{display:block;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#b3aaff;margin-bottom:12px}}
.tendens p{{font-family:var(--font-display);font-size:clamp(18px,2.6vw,23px);font-weight:600;line-height:1.45}}
.mail-boks{{background:var(--bg-kort);border:1px solid var(--linje);border-radius:var(--radius);padding:26px 28px;margin-top:22px;text-align:center;font-size:14.5px}}
.mail-titel{{display:block;font-family:var(--font-display);font-weight:800;font-size:19px;margin-bottom:14px}}
.tilmeld{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}}
.tilmeld input{{font:inherit;font-size:15px;padding:12px 18px;border:1px solid var(--linje);border-radius:999px;background:var(--bg);min-width:260px}}
.tilmeld input:focus{{outline:2px solid var(--accent);border-color:transparent}}
.tilmeld button{{font:inherit;font-size:14px;font-weight:800;padding:12px 26px;border:0;border-radius:999px;background:var(--accent);color:#fff;cursor:pointer}}
.tilmeld button:hover{{background:#4a3bd6}}
.mail-note{{display:block;margin-top:10px;font-size:12px;color:var(--blaek-svag)}}
footer{{border-top:1px solid var(--linje);padding:30px;text-align:center;font-size:12px;color:var(--blaek-svag)}}
footer a{{color:var(--accent)}}
@media (max-width:680px){{.k,.k-flip{{flex-direction:column}}.k-billede{{flex:none;height:190px}}.omslag{{min-height:64vh}}}}
</style>
</head>
<body>
<header class="omslag">
<img src="{html.escape(forside_billede)}" alt="" onerror="this.remove()">
<div class="omslag-top">
<a class="o-brand" href="./">AI<em>-nyheder</em></a>
<a class="o-tilbage" href="./">← Dagens nyheder</a>
</div>
<div class="omslag-indhold">
<span class="o-kicker">Ugens AI-overblik · uge {d.get("uge_nr", "")} · {dato}</span>
<h1>{html.escape(d.get("rubrik", ""))}</h1>
<p class="o-manchet">{html.escape(d.get("indledning", ""))}</p>
<div class="o-stats">
<div class="o-stat"><b>{stats.get("historier", "")}</b><span>historier fulgt</span></div>
<div class="o-stat"><b>{stats.get("kilder", "")}</b><span>kilder</span></div>
<div class="o-stat"><b>5</b><span>du SKAL kende</span></div>
</div>
</div>
</header>
<main>
<h2 class="ned-titel">Ugens <em>5 vigtigste</em> historier</h2>
{kort_html}
<div class="tendens"><b>Ugens røde tråd</b><p>{html.escape(d.get("tendens", ""))}</p></div>
<div class="mail-boks">
<b class="mail-titel">Få ugens AI-overblik på mail — hver fredag, helt gratis</b>
<form class="tilmeld" action="https://buttondown.com/api/emails/embed-subscribe/AInyheder" method="post" target="_blank">
<input type="email" name="email" placeholder="din@email.dk" required>
<button type="submit">Tilmeld</button>
</form>
<span class="mail-note">Én mail om ugen. Ingen spam. Afmeld med ét klik.</span>
</div>
</main>
<footer>Opdateres hver fredag · © 2026 AI-nyheder · <a href="./">Forsiden</a> · <a href="laer.html">Lær AI</a></footer>
<!-- Cloudflare Web Analytics -->
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{{"token": "fda17dd7ade34a579f4ec6d615265fa6"}}\'></script>
</body>
</html>"""


def _uge_feed_xml(d: dict) -> str:
    from email.utils import format_datetime
    tekst = html.escape(d.get("indledning", "") + "\n\n" + "\n\n".join(
        f"{h.get(chr(39)+chr(39), '') if False else h.get('overskrift','')}: {h.get('tekst','')}"
        for h in d.get("historier", [])))
    dato = format_datetime(datetime.fromisoformat(d["dato"]))
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<rss version=\"2.0\"><channel>"
            "<title>Ugens AI-overblik · AI-nyheder</title>"
            f"<link>{SITE_URL}/uge.html</link>"
            "<description>Ugens vigtigste AI-nyheder samlet i ét overblik hver fredag</description>"
            "<language>da</language>"
            "<item>"
            f"<title>{html.escape(d.get('rubrik', ''))}</title>"
            f"<link>{SITE_URL}/uge.html</link>"
            f"<guid isPermaLink=\"false\">uge-{d.get('uge', '')}</guid>"
            f"<pubDate>{dato}</pubDate>"
            f"<description>{tekst}</description>"
            "</item></channel></rss>")




def _send_nyhedsbrev(d: dict) -> None:
    """Sender ugens overblik som nyhedsbrev via Buttondowns API (gratis plan).
    Kræver secret'en BUTTONDOWN_API_KEY - ellers springes trinnet bare over."""
    noegle = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if not noegle:
        print("💌 BUTTONDOWN_API_KEY ikke sat - springer nyhedsbrevs-udsendelse over")
        return
    dele = [d.get("indledning", ""), ""]
    for nr, h in enumerate(d.get("historier", []), 1):
        # En sendt mail kan ikke rettes. Derfor er det HER, det betyder mest,
        # at linket peger på en side, der bliver ved med at findes.
        led = _dele_link(h.get("link", ""))
        dele += [f"## {nr}. {h.get('overskrift', '')}", "",
                 h.get("tekst", ""), "", f"[Læs hele historien →]({led})", ""]
    dele += ["---", "", f"**Ugens røde tråd:** {d.get('tendens', '')}", "",
             f"God weekend! Læs mere på [ainyheder.com]({SITE_URL}) — "
             f"og del gerne ugens overblik: {SITE_URL}/uge.html", "",
             "*Du får denne mail, fordi du har tilmeldt dig Ugens AI-overblik.*"]
    body = json.dumps({
        "subject": f"Ugens AI-overblik: {d.get('rubrik', '')}",
        "body": "\n".join(dele),
        "status": "about_to_send",
    }).encode()
    try:
        hent_url("https://api.buttondown.com/v1/emails", data=body,
                 headers={"Authorization": f"Token {noegle}",
                          "Content-Type": "application/json"})
        print("💌 Nyhedsbrevet er sendt til abonnenterne")
    except Exception as fejl:
        print(f"💌 ⚠️ Nyhedsbrev fejlede: {type(fejl).__name__} - overblikket er stadig på sitet")


def lav_ugens_overblik(artikler: list[dict]) -> None:
    """Skriver ugens digest fredag-søndag (én gang pr. uge) - eller første
    gang overhovedet, så siden aldrig står tom."""
    if not API_KEY:
        return
    nu = datetime.now(timezone.utc)
    aar, uge_nr, ugedag = nu.isocalendar()
    noegle = f"{aar}-{uge_nr}"
    try:
        gammel = json.loads(UGE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        gammel = {}

    # ugens kandidater: nyeste 7 dage, vigtigst først
    friske = []
    for a in artikler:
        try:
            alder = (nu - datetime.fromisoformat(a["dato"])).days
        except (TypeError, ValueError):
            continue
        if alder <= 7 and a.get("rubrik") and a.get("kategori") != "Forskning":
            friske.append(a)
    friske.sort(key=lambda a: ((a.get("prio") or 5) + (1 if a.get("andre") else 0)), reverse=True)

    if gammel.get("uge") == noegle:
        # Indholdet er allerede skrevet i denne uge. Men siden GEN-RENDERES
        # gratis ved hver kørsel, så designændringer og nye billeder slår
        # igennem med det samme - uden nye AI-kald.
        b_af = {a["link"]: a.get("billede", "") for a in artikler}
        k_af = {a["link"]: a.get("kategori", "") for a in artikler}
        for h in gammel.get("historier", []):
            # Ugens overblik skrives én gang om ugen og gen-renderes hver kørsel,
            # men billedstien blev gemt i uge.json og aldrig efterprøvet. Var
            # filen slettet imens, stod ugesiden med brudte billeder og et dødt
            # og:image - altså sort delevisning på Facebook og LinkedIn. Samme
            # opslag som _billedfil laver for artikelsiderne.
            if h.get("billede") and not (ROOT / h["billede"]).is_file():
                h["billede"] = ""
            if not h.get("billede"):
                h["billede"] = b_af.get(h.get("link", ""), "")
            if h.get("billede") and not (ROOT / h["billede"]).is_file():
                h["billede"] = ""
            if not h.get("kategori"):
                h["kategori"] = k_af.get(h.get("link", ""), "")
        gammel.setdefault("stats", {"historier": len(friske),
                                    "kilder": len({a["kilde"] for a in friske})})
        UGE_JSON.write_text(json.dumps(gammel, ensure_ascii=False, indent=1), encoding="utf-8")
        UGE_HTML.write_text(_uge_side_html(gammel), encoding="utf-8")
        UGE_FEED.write_text(_uge_feed_xml(gammel), encoding="utf-8")
        return
    if ugedag < 5 and gammel:
        return                                    # vent til fredag (5)
    if len(friske) < 5:
        return
    billede_af = {a["link"]: a.get("billede", "") for a in friske}
    kategori_af = {a["link"]: a.get("kategori", "") for a in friske}
    payload = [{"rubrik": a["rubrik"], "resume": a.get("resume_da", ""),
                "betydning": a.get("betydning", "")[:200], "kategori": a.get("kategori"),
                "link": a["link"]} for a in friske[:8]]
    try:
        r = parse_json_objekt(hjerne_kald("ugens_overblik", SYSTEM_UGE, json.dumps(payload, ensure_ascii=False), 2500))
        if not (r.get("rubrik") and len(r.get("historier", [])) >= 3):
            raise ValueError("ufuldstændigt uge-svar")
    except Exception as fejl:
        print(f"🗞️ ⚠️ Ugens overblik fejlede: {type(fejl).__name__}")
        return
    data = {"uge": noegle, "uge_nr": uge_nr, "dato": nu.isoformat(),
            "rubrik": str(r["rubrik"]).strip(),
            "indledning": str(r.get("indledning", "")).strip(),
            "historier": [{"overskrift": str(h.get("overskrift", "")).strip(),
                           "tekst": str(h.get("tekst", "")).strip(),
                           "link": str(h.get("link", "")).strip(),
                           "billede": billede_af.get(str(h.get("link", "")).strip(), ""),
                           "kategori": kategori_af.get(str(h.get("link", "")).strip(), "")}
                          for h in r["historier"][:5]],
            "stats": {"historier": len(friske),
                      "kilder": len({a["kilde"] for a in friske})},
            "tendens": str(r.get("tendens", "")).strip()}
    UGE_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    UGE_HTML.write_text(_uge_side_html(data), encoding="utf-8")
    UGE_FEED.write_text(_uge_feed_xml(data), encoding="utf-8")
    print(f"🗞️ Skrev Ugens overblik (uge {uge_nr}): {data['rubrik']}")
    _send_nyhedsbrev(data)


# ----- Statiske artikelsider (SEO) --------------------------------------------

ARTIKEL_MAPPE = ROOT / "artikel"


def _artikel_slug(link: str) -> str:
    import hashlib
    return hashlib.md5(link.encode()).hexdigest()[:16]


def _fed_html(tekst: str) -> str:
    """Escaper HTML og omsætter **fremhævning** til <strong>."""
    t = html.escape(str(tekst or ""))
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)


def _jsonld(data: dict) -> str:
    """JSON til et <script type="application/ld+json">-element.

    Indholdet kommer fra fremmede feeds, og et script-element er rå tekst -
    så visse tegnfølger i en rubrik kan slippe ud af blokken:

      "</script>"     lukker tagget for tidligt, så resten af JSON-LD'en
                      havner som synlig tekst på siden.
      "<!--<script"   er værre: den sætter HTML-parseren i en tilstand, hvor
                      det følgende "</script>" IKKE afslutter blokken, og så
                      bliver resten af dokumentet slugt som scriptindhold -
                      siden ender helt blank. De to dele kan endda ligge i
                      hver sit felt, så ingen enkelt streng ser mistænkelig ud.

    Derfor escapes < > og & som JSON-unicode i stedet for at lappe på "</".
    \\u003c er gyldig JSON og læses ens af enhver parser, Googles med, men
    ingen af de farlige tegnfølger kan opstå i det, browseren ser.
    """
    return (json.dumps(data, ensure_ascii=False)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def _billedfil(a: dict) -> str:
    """Artiklens billede, men kun hvis filen faktisk ligger der. Ellers "".

    Feltet "billede" bliver sat, den kørsel billedet laves, og bliver stående
    bagefter. Er filen siden røget - ryddet op, mislykket overførsel - må
    skabelonen ikke pege på den alligevel: så får læseren et brudt billede,
    delevisningen på sociale medier går i sort, og Search Console svarer
    "Image not found" på den structured data. Ét opslag på disken lukker alle
    tre huller på én gang.
    """
    sti = a.get("billede")
    if not sti:
        return ""
    try:
        return sti if (ROOT / sti).is_file() else ""
    except OSError:
        return ""


def _artikel_side_html(a: dict) -> str:
    rubrik = html.escape(str(a.get("rubrik") or a.get("titel") or ""))
    resume = html.escape(str(a.get("resume_da") or a.get("resume") or ""))
    slug = _artikel_slug(a["link"])
    url = f"{SITE_URL}/artikel/{slug}.html"
    billedfil = _billedfil(a)
    billede = f"{SITE_URL}/{billedfil}" if billedfil else f"{SITE_URL}/assets/og.png"
    dato_vis = (a.get("dato") or "")[:10]

    krop = ""
    for s in a.get("sektioner", []):
        krop += f'<h2>{_fed_html(s.get("overskrift", ""))}</h2>\n<p>{_fed_html(s.get("tekst", ""))}</p>\n'
    if not krop and a.get("brief"):
        krop = f"<p>{_fed_html(a['brief'])}</p>\n"

    detaljer = ""
    if a.get("detaljer"):
        punkter = "".join(f"<li>{_fed_html(d)}</li>" for d in a["detaljer"])
        detaljer = f'<div class="boks"><strong>Detaljerne</strong><ul>{punkter}</ul></div>'

    betydning = ""
    if a.get("betydning"):
        betydning = (f'<div class="boks" style="border-left-color:#2e9e5b;">'
                     f'<strong>Hvad betyder det for dig?</strong><br>{_fed_html(a["betydning"])}</div>')

    kilder = f'<a class="kilde" href="{html.escape(a["link"])}" rel="noopener">{html.escape(a["kilde"])} →</a>'
    for k in a.get("andre") or []:
        kilder += f' <a class="kilde" href="{html.escape(k["link"])}" rel="noopener">{html.escape(k["kilde"])} →</a>'

    # Alt-tekst: billedmotivet er art direction-beskrivelsen af præcis den
    # scene, billedet viser - altså den bedste alt-tekst vi har. Falder tilbage
    # på rubrikken. Uden den er billedet usynligt for skærmlæsere og for
    # Google Billeder.
    alt_tekst = html.escape(
        str(a.get("billedmotiv") or a.get("rubrik") or a.get("titel") or "")[:180])
    billed_html = (f'<img class="top" src="/{html.escape(billedfil)}" '
                   f'alt="{alt_tekst}">') if billedfil else ""

    # Varedeklarationen nederst må kun nævne illustrationen, når der ER en.
    # Billedet laves først en senere kørsel (MAX_BILLEDER_PR_KOERSEL), og nogle
    # sider får aldrig et - så stod der "AI-genereret illustration" på en side
    # helt uden billede. Punkt 5 i redaktionens øjne: ærlighed frem for
    # markedsføring, også når det er os selv, teksten smigrer.
    note_dele = ["Genfortalt i egne ord af AI-nyheder.com"]
    if billedfil:
        note_dele.append("AI-genereret illustration")
    note_dele.append("Tjek altid originalkilden, før du handler på vigtige oplysninger.")
    note = " · ".join(note_dele)

    # Struktureret data, så Google kan vise siden som nyhedsresultat med dato
    # og billede. Videosiderne har haft det hele tiden; artikelsiderne ikke.
    # isBasedOn peger på originalkilden - vi genfortæller, og det skal stå der.
    ld: dict = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": str(a.get("rubrik") or a.get("titel") or "")[:110],
        "description": str(a.get("resume_da") or a.get("resume") or ""),
        "url": url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "inLanguage": "da-DK",
        "isAccessibleForFree": True,
        "author": {"@type": "Organization", "name": "AI-nyheder", "url": SITE_URL},
        "publisher": {"@type": "Organization", "name": "AI-nyheder", "url": SITE_URL},
    }
    if billedfil:
        ld["image"] = billede
    if a.get("dato"):
        ld["datePublished"] = a["dato"]
        # Bevidst ikke dateModified: "foerst_set" er hvornår crawleren så
        # artiklen, ikke hvornår siden sidst blev ændret, og et ærligt
        # dateModified=nu ville få hver kørsel til at genskrive alle sider,
        # fordi indholdet så ville se ændret ud. Feltet er valgfrit hos Google.
    if a.get("kategori"):
        ld["articleSection"] = a["kategori"]
    if a.get("link"):
        ld["isBasedOn"] = a["link"]
    jsonld = _jsonld(ld)

    return f"""<!DOCTYPE html>
<html lang="da">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI-nyheder.com · {rubrik}</title>
<meta name="description" content="{resume}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#f4f2ec">
<meta property="og:type" content="article">
<meta property="og:site_name" content="AI-nyheder">
<meta property="og:title" content="{rubrik}">
<meta property="og:description" content="{resume}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{billede}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/favicon-192.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/fonts/skrifter.css">
<script type="application/ld+json">{jsonld}</script>
<style>
:root {{ --bg:#f4f2ec; --bg-kort:#ffffff; --blaek:#191714; --blaek-svag:#6d675d;
  --linje:#e2ddd2; --accent:#5b4bf0; --accent-svag:#ecebfd; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:"Inter",-apple-system,sans-serif; background:var(--bg); color:var(--blaek); line-height:1.6; }}
.topbar {{ position:sticky; top:0; background:color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter:blur(14px); border-bottom:1px solid var(--linje); padding:14px 28px; }}
.brand {{ font-family:"Fraunces",Georgia,serif; font-weight:900; font-size:24px; letter-spacing:-.03em; text-decoration:none; color:inherit; }}
.brand em {{ font-style:normal; color:var(--accent); }}
main {{ max-width:720px; margin:0 auto; padding:44px 24px 80px; }}
.kicker {{ font-size:12px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); margin-bottom:12px; }}
h1 {{ font-family:"Fraunces",Georgia,serif; font-weight:900; letter-spacing:-.02em;
  font-size:clamp(28px,5vw,40px); line-height:1.12; margin-bottom:14px; }}
.manchet {{ font-size:17px; line-height:1.65; color:var(--blaek-svag); margin-bottom:22px; }}
img.top {{ width:100%; border-radius:16px; margin-bottom:24px; }}
h2 {{ font-family:"Fraunces",Georgia,serif; font-weight:800; font-size:21px; margin:28px 0 8px; }}
p {{ font-size:15.5px; line-height:1.75; margin-bottom:13px; }}
li {{ font-size:14.5px; line-height:1.7; margin:6px 0 6px 20px; }}
.boks {{ background:var(--accent-svag); border-left:3px solid var(--accent); border-radius:0 12px 12px 0;
  padding:14px 18px; margin:20px 0; font-size:15px; }}
.kilde {{ display:inline-block; font-size:13px; font-weight:700; text-decoration:none; color:inherit;
  border:1px solid var(--linje); background:var(--bg-kort); padding:8px 16px; border-radius:999px; margin:4px 6px 0 0; }}
.kilde:hover {{ border-color:var(--accent); color:var(--accent); }}
.cta {{ display:inline-block; font-size:14px; font-weight:700; text-decoration:none; color:#fff;
  background:var(--accent); padding:12px 24px; border-radius:999px; margin-top:26px; }}
.note {{ font-size:12.5px; color:var(--blaek-svag); margin-top:22px; }}
footer {{ border-top:1px solid var(--linje); padding:30px 26px; text-align:center; font-size:12px; color:var(--blaek-svag); }}
footer a {{ color:var(--accent); }}
</style>
</head>
<body>
<div class="topbar"><a class="brand" href="/">AI<em>-nyheder</em></a></div>
<main>
<div class="kicker">{html.escape(a.get("kategori") or "AI-nyt")} · {html.escape(a.get("kilde", ""))} · {dato_vis}</div>
<h1>{rubrik}</h1>
<p class="manchet">{resume}</p>
{billed_html}
{krop}
{detaljer}
{betydning}
<p style="margin-top:24px"><strong>Kilder:</strong><br>{kilder}</p>
<a class="cta" href="/">Læs dagens AI-nyheder på letlæst dansk →</a>
<p class="note">{note}</p>
</main>
<footer>© 2026 AI-nyheder · <a href="/om.html">Om os</a> · <a href="/laer.html">Lær AI</a></footer>
<!-- Cloudflare Web Analytics (privatlivsvenlig besøgsstatistik, ingen cookies) -->
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "fda17dd7ade34a579f4ec6d615265fa6"}}'></script>
</body>
</html>"""


def _peg_dubletsider_mod_hovedhistorien(artikler: list[dict]) -> set[str]:
    """Når to medier dækkede samme historie, står den tabende udgaves side
    stadig på disk med sin egen canonical, der peger på sig selv.

    Siden må ikke slettes - nogen kan have linket til den, og en 404 er værre
    end en dublet. Men Google skal vide, hvilken af dem der er den rigtige,
    ellers konkurrerer vores egne sider med hinanden om den samme søgning.
    Vi retter derfor canonical til at pege på hovedhistorien og holder siden
    ude af sitemappet - et sitemap bør kun indeholde canonical-URL'er.

    Retter kun canonical. Hvilke sider der ER dubletter, læses bagefter af
    disken - se `_dubletsider_paa_disk`.
    """
    rettet = 0
    for a in artikler:
        if not a.get("andre") or not a.get("rubrik") or a.get("kun_aktuel"):
            continue
        eget = _artikel_slug(a["link"])
        maal = f"{SITE_URL}/artikel/{eget}.html"
        for kilde in a["andre"]:
            link = kilde.get("link")
            if not link:
                continue
            slug = _artikel_slug(link)
            if slug == eget:
                continue            # en historie kan ikke være dublet af sig selv
            sti = ARTIKEL_MAPPE / f"{slug}.html"
            if not sti.exists():
                continue
            try:
                gammel = sti.read_text(encoding="utf-8")
            except OSError:
                continue
            ny, antal = re.subn(
                r'(<link rel="canonical" href=")[^"]*(")',
                lambda m: m.group(1) + html.escape(maal, quote=True) + m.group(2),
                gammel, count=1)
            if antal and ny != gammel:
                try:
                    sti.write_text(ny, encoding="utf-8")
                except OSError:
                    continue
                rettet += 1
    if rettet:
        print(f"🔗 {rettet} dubletsider peger nu på deres hovedhistorie")


def _bryd_canonical_kaeder(artikler: list[dict]) -> int:
    """Retter de sider, hvis hovedhistorie SELV blev slået sammen bagefter.

    `_peg_dubletsider_mod_hovedhistorien` peger en tabers side mod vinderen og
    ser aldrig på den igen. Bliver vinderen senere selv slået sammen, står der
    en kæde: A → B → C. Google følger ikke canonical-kæder - den behandler dem
    som et brudt signal.

    Målt 27.07: 8 af 112 sider stod i en kæde, og de var ikke tilfældige.
    **7 af de 8 var levende, selvstændige artikler** med egen rubrik i
    `articles.json`; forsidens deleknapper og `_dele_link` sender folk til dem.
    Alligevel sagde deres side til Google, at den rigtige udgave var en helt
    anden historie - "Ny gratis AI-videoredigering til din Mac" pegede via to
    led på "AI Kill Switch Act" - og fordi `_dubletsider_paa_disk` læser netop
    den canonical, stod **0 af de 7 i sitemappet**. Indhold, vi selv
    promoverer, var usynligt for Google. Punkt 10, og punkt 5: siden påstod
    noget om sig selv, der ikke var sandt.

    **Vi rører kun kædehoveder.** En side, hvis mål selv er hovedhistorie, er
    en almindelig dublet og bliver stående urørt - det er dét,
    `_dubletsider_paa_disk` kalder permanent hukommelse, og en enkelt kørsel,
    hvor vinderen mangler i feedet, må ikke kunne vælte den. En kæde er
    derimod aldrig rigtig, uanset hvad dagens liste siger, og derfor er det
    forsvarligt at træffe valget om igen netop dér.
    """
    forstavelse = f"{SITE_URL}/artikel/"
    peger: dict[str, str] = {}
    for p in ARTIKEL_MAPPE.glob("*.html"):
        try:
            tekst = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fundet = re.search(r'<link rel="canonical" href="([^"]*)"', tekst)
        if not fundet:
            continue
        maal = html.unescape(fundet.group(1))
        if maal.startswith(forstavelse) and maal.endswith(".html"):
            peger[p.stem] = maal[len(forstavelse):-len(".html")]

    # Tåler en artikel uden `link` og et `andre`, der ikke er en liste. Vi
    # skriver til disken her, så et enkelt skævt element må ikke vælte
    # oprydningen for de øvrige 111 sider.
    tabere: set[str] = set()
    for a in artikler:
        if not a.get("rubrik") or a.get("kun_aktuel"):
            continue
        for kilde in (a.get("andre") if isinstance(a.get("andre"), list) else []):
            if isinstance(kilde, dict) and kilde.get("link"):
                tabere.add(_artikel_slug(kilde["link"]))
    selvstaendige = {_artikel_slug(a["link"]) for a in artikler
                     if a.get("link") and a.get("rubrik")
                     and not a.get("kun_aktuel")} - tabere

    rettet = 0
    for slug, maal in sorted(peger.items()):
        if maal == slug or peger.get(maal, maal) == maal:
            continue                    # ikke en kæde - lad den stå
        ende, sete = maal, {slug, maal}
        while peger.get(ende, ende) != ende and peger[ende] not in sete:
            ende = peger[ende]
            sete.add(ende)
        # Er artiklen levende og selvstændig i dag, er den sin egen
        # hovedhistorie. Ellers kan vi kun folde kæden ud til dens ende.
        nyt = slug if slug in selvstaendige else ende
        if nyt != slug and not (ARTIKEL_MAPPE / f"{nyt}.html").is_file():
            continue                    # intet bedre at pege på
        sti = ARTIKEL_MAPPE / f"{slug}.html"
        try:
            gammel = sti.read_text(encoding="utf-8")
        except OSError:
            continue
        adresse = html.escape(f"{forstavelse}{nyt}.html", quote=True)
        ny, antal = re.subn(r'(<link rel="canonical" href=")[^"]*(")',
                            lambda mm: mm.group(1) + adresse + mm.group(2),
                            gammel, count=1)
        if not antal or ny == gammel:
            continue
        try:
            sti.write_text(ny, encoding="utf-8")
        except OSError:
            continue
        peger[slug] = nyt
        rettet += 1
    if rettet:
        print(f"🔗 {rettet} canonical-kæder brudt")
    return rettet


def _giv_frigivne_deres_canonical_tilbage(artikler: list[dict]) -> int:
    """Retter siderne for de artikler, `_samme_sag` har sluppet løs igen.

    Frigivelsen i `saml_dublet_historier` fjerner artiklen fra vinderens
    `andre`, men det gør ikke siden synlig: `_dubletsider_paa_disk` læser
    canonical af DISKEN, og der står stadig vinderens adresse. Uden den her
    ville en frigivet artikel blive frigivet igen og igen, uden nogensinde at
    komme tilbage i sitemappet — årsagen rettet, symptomet ikke.

    Samme bevisbyrde som frigivelsen selv, og den er hele grunden til, at den
    her funktion kan tillade sig at overskrive et valg, disken har husket:

      * siden peger på en anden artikelside,
      * artiklen er levende og selvstændig i dagens liste (ingen har den i sit
        `andre`), og
      * **den, den peger på, er også i dagens liste, og vagten siger nej.**

    Én undtagelse: er siden noteret i `_FRIGIVNE_UDEN_FEED`, er beviset ført i
    trin 0 med `_deler_intet`, som er strengere end vagten her — og taberen er
    slet ikke i dagens liste, så det tredje krav kan aldrig opfyldes for den.
    Se kommentaren nede i løkken.

    Det tredje krav er det vigtige. `_dubletsider_paa_disk` beskriver, hvorfor
    en manglende hovedhistorie ikke må kunne vælte en dublet: en enkelt kørsel
    med timeout på et feed ville ellers få canonical til at svinge frem og
    tilbage. Her sker der intet, når vinderen mangler — der rettes kun, når vi
    kan holde de to tekster op mod hinanden og måle, at de ikke hører sammen.
    """
    forstavelse = f"{SITE_URL}/artikel/"
    tabere: set[str] = set()
    for a in artikler:
        for kilde in (a.get("andre") if isinstance(a.get("andre"), list) else []):
            if isinstance(kilde, dict) and kilde.get("link"):
                tabere.add(_artikel_slug(kilde["link"]))
    levende = {_artikel_slug(a["link"]): a for a in artikler
               if a.get("link") and a.get("rubrik") and not a.get("kun_aktuel")}

    rettet = 0
    for p in sorted(ARTIKEL_MAPPE.glob("*.html")):
        if p.stem in tabere:
            continue                       # stadig dublet
        denne = levende.get(p.stem)
        frigivet_uden_feed = denne is None and p.stem in _FRIGIVNE_UDEN_FEED
        if denne is None and not frigivet_uden_feed:
            continue                       # ikke i listen
        try:
            gammel = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fundet = re.search(r'<link rel="canonical" href="([^"]*)"', gammel)
        if not fundet:
            continue
        maal = html.unescape(fundet.group(1))
        if maal == f"{SITE_URL}/artikel/{p.name}" or not maal.startswith(forstavelse):
            continue                       # peger på sig selv, eller uden for arkivet
        if not frigivet_uden_feed:
            vinder = levende.get(maal[len(forstavelse):-len(".html")])
            if vinder is None or _samme_sag(vinder, denne):
                continue                   # intet bevis for at pegningen er forkert
        # Er siden frigivet uden feed, er beviset allerede ført i trin 0 — med
        # `_deler_intet`, der er strengere end tjekket her. Vi må ikke føre det
        # igen: den her funktion har kun ÉT forsøg. `_FRIGIVNE_UDEN_FEED` ryddes
        # hver kørsel, og artiklen står ikke længere i nogens `andre`, så
        # springer vi siden over nu, bliver den aldrig besøgt igen — frigivet i
        # data og usynlig på disken for evigt.
        adresse = html.escape(f"{SITE_URL}/artikel/{p.name}", quote=True)
        ny, antal = re.subn(r'(<link rel="canonical" href=")[^"]*(")',
                            lambda mm: mm.group(1) + adresse + mm.group(2),
                            gammel, count=1)
        if not antal or ny == gammel:
            continue
        try:
            p.write_text(ny, encoding="utf-8")
        except OSError:
            continue
        rettet += 1
    if rettet:
        print(f"↩️  {rettet} frigivne artikelsider peger nu på sig selv igen")
    return rettet


def _dubletsider_paa_disk() -> set[str]:
    """Hvilke artikelsider er sammenlagt under en anden historie?

    Svaret læses af DISKEN - af sidernes egen canonical - og ikke af dagens
    artikelliste. Grunden er målt: en hovedhistorie kan forsvinde ud af feedet
    i en enkelt kørsel (den ene af vores egne dubletgrupper manglede i 6 af 14
    kørsler, fordi `crawl_feed` returnerer en tom liste ved timeout). Udledte
    vi dubletterne af `artikler`, ville siden dén kørsel ikke være kendt som
    dublet: hovedløkken ville skrive den om med en canonical til sig selv og
    lægge den tilbage i sitemappet - og næste kørsel ville vende det tilbage
    igen. Canonical på disken er permanent hukommelse; artikellisten er ikke.
    """
    ude: set[str] = set()
    for p in ARTIKEL_MAPPE.glob("*.html"):
        try:
            tekst = p.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r'<link rel="canonical" href="([^"]*)"', tekst)
        if m and m.group(1) != f"{SITE_URL}/artikel/{p.name}":
            ude.add(p.stem)
    return ude


def _har_noget_at_vise(a: dict) -> bool:
    """Er der andet på siden end rubrikken og den ene resumésætning?

    En artikel har kun en rubrik, indtil genfortællingen er skrevet, og
    rubrikken alene er ikke en artikel: siden bliver en overskrift, én sætning
    og et link ud af huset. Bygger vi den alligevel, står den der for evigt.
    Artiklen forsvinder nemlig ud af articles.json, så snart kildens RSS-feed
    holder op med at nævne den - dage, ikke de 30 dage MAX_DAGE_GAMMEL
    antyder, for arkivet bliver bygget forfra af feedene hver kørsel og bruger
    kun den gamle fil som cache pr. link. Derefter kan ingen kørsel røre siden
    igen. Så vi venter. Er genfortællingen der næste kørsel, bygges siden da.
    """
    # "brief" står med vilje ikke her: feltet udfyldes aldrig (prompten beder om
    # "sektioner"), og en side bygget på brief alene ville få en <p> uden <h2> og
    # uden boks - altså blive kaldt tom af _side_har_indhold og holdt ude af
    # sitemappet for evigt. To vagter, der er uenige, er værre end én, der er
    # streng.
    return bool(a.get("sektioner") or a.get("detaljer") or a.get("betydning"))


def _side_har_indhold(h: str) -> bool:
    """Samme spørgsmål, stillet til en side på disken.

    Bruges til sitemappet, hvor de ældste siders artikel ikke længere står i
    articles.json, så vi kun har siden selv at spørge. Ingen <h2> og ingen
    boks betyder hverken sektioner, detaljer eller "Hvad betyder det for dig".
    """
    return "<h2>" in h or 'class="boks"' in h


def lav_artikelsider(artikler: list[dict]) -> None:
    """Skriver en statisk HTML-side pr. dansk artikel (SEO) + eget sitemap.
    Gamle sider slettes ikke - de bliver stående som evigt indhold."""
    ARTIKEL_MAPPE.mkdir(exist_ok=True)
    # 1) nye sammenlægninger: peg de tabende udgavers sider mod hovedhistorien
    _peg_dubletsider_mod_hovedhistorien(artikler)
    # 1b) og ryd op efter dem, hvis hovedhistorie selv blev slået sammen siden.
    #     SKAL køre før punkt 2, ellers når de rettede sider ikke i sitemappet
    #     før i overmorgen.
    _bryd_canonical_kaeder(artikler)
    # 1c) og giv de frigivne deres egen canonical tilbage, så de kommer med i
    #     sitemappet i denne kørsel og ikke først i overmorgen.
    _giv_frigivne_deres_canonical_tilbage(artikler)
    # 2) spørg disken, hvilke sider der er dubletter - både nattens og alle
    #    tidligere. Se forklaringen i _dubletsider_paa_disk.
    dubletter = _dubletsider_paa_disk()
    skrevet = 0
    poster = []
    for a in artikler:
        if not a.get("rubrik"):
            continue                        # kun danske genfortællinger
        if a.get("kun_aktuel"):
            continue                        # udgiveren tillader ikke et arkiv
        if not _har_noget_at_vise(a):
            continue        # kun en rubrik endnu - se _har_noget_at_vise
        slug = _artikel_slug(a["link"])
        a["side"] = f"artikel/{slug}.html"
        if slug in dubletter:
            continue    # sammenlagt under en anden historie - lad siden stå
        sti = ARTIKEL_MAPPE / f"{slug}.html"
        indhold = _artikel_side_html(a)
        if not sti.exists() or sti.read_text(encoding="utf-8") != indhold:
            sti.write_text(indhold, encoding="utf-8")
            skrevet += 1
        poster.append((slug, (a.get("foerst_set") or "")[:10]))
    # eget sitemap for artikelsiderne (alle, også de historiske - men ikke
    # dubletsider, som peger et andet sted hen med deres canonical, og ikke
    # sider uden genfortælling: et sitemap er en invitation, og en side med
    # rubrik + én sætning giver læseren ingenting at blive for. De ældste af
    # dem kan ikke længere udfyldes - kilden er ude af feedet, og teksten har
    # vi ikke gemt - så de holdes ude i stedet.
    tomme = 0
    alle_sider = []
    for p in sorted(ARTIKEL_MAPPE.glob("*.html")):
        if p.stem in dubletter:
            continue
        try:
            indhold = p.read_text(encoding="utf-8")
        except OSError:
            alle_sider.append(p)   # kan ikke læses: behold den, frem for at
            continue               # vælte hele kørslen på én ulæselig fil
        if not _side_har_indhold(indhold):
            tomme += 1
            continue
        alle_sider.append(p)
    linjer = "".join(
        f"  <url><loc>{SITE_URL}/artikel/{p.name}</loc></url>\n" for p in alle_sider)
    (ROOT / "sitemap-artikler.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{linjer}</urlset>\n", encoding="utf-8")
    print(f"🔎 Artikelsider: {skrevet} skrevet/opdateret, {len(alle_sider)} i sitemap"
          + (f", {len(dubletter)} dubletter udeladt" if dubletter else "")
          + (f", {tomme} uden genfortælling udeladt" if tomme else ""))


# ----- Statiske videosider (SEO) ---------------------------------------------

VIDEO_MAPPE = ROOT / "video"


def _video_side_html(v: dict) -> str:
    """Én statisk side pr. YouTube-video med det danske resumé.
    Værdien for læseren - og for Google - er den danske genfortælling;
    selve videoen ligger stadig hos YouTube."""
    rubrik = html.escape(v.get("rubrik") or v.get("titel", ""))
    resume = html.escape(v.get("resume_da") or "")
    vid = re.sub(r"[^A-Za-z0-9_-]", "", str(v.get("id", "")))
    url = f"{SITE_URL}/video/{vid}.html"
    thumb = html.escape(v.get("thumb") or f"{SITE_URL}/assets/og.png")
    dato = str(v.get("dato") or "")
    dato_vis = dato[:10]

    hp = ""
    if v.get("hoejdepunkter"):
        raekker = "".join(
            f'<li><a href="{html.escape(v["link"])}&t={int(h.get("sek", 0))}s" rel="noopener">'
            f'<strong>{html.escape(str(h.get("tid", "")))}</strong></a> '
            f'{_fed_html(h.get("titel", ""))}</li>'
            for h in v["hoejdepunkter"])
        hp = f"<h2>Højdepunkter — hop direkte til stedet</h2>\n<ul>{raekker}</ul>"

    pointer = ""
    if v.get("pointer"):
        punkter = "".join(f"<li>{_fed_html(p)}</li>" for p in v["pointer"])
        pointer = f'<div class="boks"><strong>Kort fortalt</strong><ul>{punkter}</ul></div>'

    betydning = ""
    if v.get("betydning"):
        betydning = ('<div class="boks" style="border-left-color:#2e9e5b;">'
                     f'<strong>Hvad betyder det for dig?</strong><br>{_fed_html(v["betydning"])}</div>')

    # Struktureret data, så Google kan vise siden som videoresultat
    jsonld = _jsonld({
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": str(v.get("rubrik") or v.get("titel") or ""),
        "description": str(v.get("resume_da") or ""),
        "thumbnailUrl": v.get("thumb", ""),
        "uploadDate": dato,
        "duration": v.get("varighed") or None,
        "embedUrl": f"https://www.youtube.com/embed/{vid}",
        "url": url,
        "publisher": {"@type": "Organization", "name": "AI-nyheder",
                      "url": SITE_URL},
    })

    return f"""<!DOCTYPE html>
<html lang="da">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI-nyheder.com · {rubrik}</title>
<meta name="description" content="{resume}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#f4f2ec">
<meta property="og:type" content="video.other">
<meta property="og:site_name" content="AI-nyheder">
<meta property="og:title" content="{rubrik}">
<meta property="og:description" content="{resume}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{thumb}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/favicon-192.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/fonts/skrifter.css">
<script type="application/ld+json">{jsonld}</script>
<style>
:root {{ --bg:#f4f2ec; --bg-kort:#ffffff; --blaek:#191714; --blaek-svag:#6d675d;
  --linje:#e2ddd2; --accent:#5b4bf0; --accent-svag:#ecebfd; --yt:#cc2b2b; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:"Inter",-apple-system,sans-serif; background:var(--bg); color:var(--blaek); line-height:1.6; }}
.topbar {{ position:sticky; top:0; background:color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter:blur(14px); border-bottom:1px solid var(--linje); padding:14px 28px; }}
.brand {{ font-family:"Fraunces",Georgia,serif; font-weight:900; font-size:24px; letter-spacing:-.03em; text-decoration:none; color:inherit; }}
.brand em {{ font-style:normal; color:var(--accent); }}
main {{ max-width:720px; margin:0 auto; padding:44px 24px 80px; }}
.kicker {{ font-size:12px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--yt); margin-bottom:12px; }}
h1 {{ font-family:"Fraunces",Georgia,serif; font-weight:900; letter-spacing:-.02em;
  font-size:clamp(28px,5vw,40px); line-height:1.12; margin-bottom:14px; }}
.manchet {{ font-size:17px; line-height:1.65; color:var(--blaek-svag); margin-bottom:22px; }}
.afspil {{ display:block; position:relative; margin-bottom:24px; border-radius:16px; overflow:hidden; background:#000; }}
.afspil img {{ width:100%; display:block; }}
.afspil span {{ position:absolute; inset:0; display:grid; place-items:center; }}
.afspil b {{ width:64px; height:45px; border-radius:12px; background:rgba(204,43,43,.94); display:grid; place-items:center; color:#fff; font-size:20px; }}
h2 {{ font-family:"Fraunces",Georgia,serif; font-weight:800; font-size:21px; margin:28px 0 8px; }}
p {{ font-size:15.5px; line-height:1.75; margin-bottom:13px; }}
li {{ font-size:14.5px; line-height:1.7; margin:6px 0 6px 20px; }}
li a {{ color:var(--accent); text-decoration:none; font-variant-numeric:tabular-nums; }}
li a:hover {{ text-decoration:underline; }}
.boks {{ background:var(--accent-svag); border-left:3px solid var(--accent); border-radius:0 12px 12px 0;
  padding:14px 18px; margin:20px 0; font-size:15px; }}
.kilde {{ display:inline-block; font-size:13px; font-weight:700; text-decoration:none; color:inherit;
  border:1px solid var(--linje); background:var(--bg-kort); padding:8px 16px; border-radius:999px; margin:4px 6px 0 0; }}
.kilde:hover {{ border-color:var(--yt); color:var(--yt); }}
.cta {{ display:inline-block; font-size:14px; font-weight:700; text-decoration:none; color:#fff;
  background:var(--accent); padding:12px 24px; border-radius:999px; margin-top:26px; }}
.note {{ font-size:12.5px; color:var(--blaek-svag); margin-top:22px; }}
footer {{ border-top:1px solid var(--linje); padding:30px 26px; text-align:center; font-size:12px; color:var(--blaek-svag); }}
footer a {{ color:var(--accent); }}
</style>
</head>
<body>
<div class="topbar"><a class="brand" href="/">AI<em>-nyheder</em></a></div>
<main>
<div class="kicker">AI på YouTube · {html.escape(v.get("kanal", ""))} · {dato_vis}</div>
<h1>{rubrik}</h1>
<p class="manchet">{resume}</p>
<a class="afspil" href="{html.escape(v.get("link", ""))}" rel="noopener">
  <img src="{thumb}" alt="Se videoen på YouTube: {rubrik[:160]}" loading="lazy"><span><b>▶</b></span></a>
{pointer}
{hp}
{betydning}
<p style="margin-top:24px"><strong>Se videoen:</strong><br>
  <a class="kilde" href="{html.escape(v.get("link", ""))}" rel="noopener">Åbn på YouTube →</a>
  <a class="kilde" href="{html.escape(v.get("kanal_url", "") or v.get("link", ""))}" rel="noopener">{html.escape(v.get("kanal", ""))} →</a></p>
<a class="cta" href="/youtube.html">Flere AI-videoer opsummeret på dansk →</a>
<p class="note">Resuméet er skrevet af AI-nyheder.com ud fra videoen · Vi ejer ikke videoen, og den ligger fortsat hos {html.escape(v.get("kanal", "kanalen"))} · Tjek altid originalen, hvis noget er vigtigt for dig.</p>
</main>
<footer>© 2026 AI-nyheder · <a href="/om.html">Om os</a> · <a href="/laer.html">Lær AI</a></footer>
<!-- Cloudflare Web Analytics (privatlivsvenlig besøgsstatistik, ingen cookies) -->
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "fda17dd7ade34a579f4ec6d615265fa6"}}'></script>
</body>
</html>"""


def lav_videosider(videoer: list[dict]) -> None:
    """Statisk side pr. video med dansk resumé + eget sitemap.
    Kun videoer med dansk rubrik - resten har intet at tilbyde en læser."""
    VIDEO_MAPPE.mkdir(exist_ok=True)
    skrevet = 0
    for v in videoer:
        if not (v.get("rubrik") and v.get("id")):
            continue
        vid = re.sub(r"[^A-Za-z0-9_-]", "", str(v["id"]))
        if not vid:
            continue
        v["side"] = f"video/{vid}.html"
        sti = VIDEO_MAPPE / f"{vid}.html"
        indhold = _video_side_html(v)
        if not sti.exists() or sti.read_text(encoding="utf-8") != indhold:
            sti.write_text(indhold, encoding="utf-8")
            skrevet += 1
    alle = sorted(VIDEO_MAPPE.glob("*.html"))
    (ROOT / "sitemap-videoer.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE_URL}/video/{p.name}</loc></url>\n" for p in alle)
        + "</urlset>\n", encoding="utf-8")
    print(f"🔎 Videosider: {skrevet} skrevet/opdateret, {len(alle)} i alt")


# ----- Dagens prompt (prompt-kartoteket) -------------------------------------

PROMPT_ARKIV = ROOT / "data" / "prompts.json"
PROMPT_KATEGORIER = ["Hverdag", "Job", "Økonomi", "Skole", "Tekst", "Kreativt", "Sundhed & livet"]

SYSTEM_KARTOTEK = """Du skriver dagens prompt til ainyheder.com - et dansk site, der lærer helt almindelige danskere at bruge AI.
Svar KUN med ét JSON-objekt: {"titel": "...", "kategori": "...", "tekst": "...", "hvorfor": "..."}
Krav:
- titel: fængende, højst 5 ord, på dansk.
- kategori: præcis én af: Hverdag, Job, Økonomi, Skole, Tekst, Kreativt, Sundhed & livet.
- tekst: selve prompten på dansk (2-6 sætninger) med [firkantede felter] til brugerens egne oplysninger.
- hvorfor: én kort sætning om, hvad der gør prompten smart.
- VIGTIGT: Lav noget nyt - undgå emner og vinkler fra titellisten, du får. Aldrig medicinsk/juridisk rådgivning som facit (kun forberedelse til fagfolk).

TÆNK PÅ HVEM DER SKAL BRUGE DEN. En dansker der aldrig har brugt AI før, skal
kunne kopiere prompten, udfylde felterne og få noget brugbart i FØRSTE forsøg -
uden at vide noget om prompts. Det udelukker alt, der kræver opfølgning eller
teknisk forståelse.

TRE KRAV, DER SKILLER EN GOD PROMPT FRA EN KEDELIG:
1. Den løser en opgave, folk faktisk har - ikke en, der lyder smart.
   Ja: klage over en regning, forstå et brev fra kommunen, planlægge en fest
   for 12, forberede en lønsamtale. Nej: "brainstorm idéer til mit brand".
2. Den giver AI'en noget at arbejde MED: en rolle, en modtager, en tone, et
   format - så svaret bliver skræddersyet i stedet for generisk.
3. Resultatet skal kunne bruges direkte. Ikke et oplæg til mere arbejde.

EKSEMPEL PÅ NIVEAUET:
titel: "Forstå brevet fra kommunen"
tekst: "Du er en tålmodig sagsbehandler, der er god til at forklare.
Her er et brev, jeg har fået: [indsæt brevet uden navn og CPR].
Svar med tre ting: 1) Hvad vil de have af mig, i én sætning.
2) Hvad skal jeg gøre, og hvornår er fristen. 3) Er der noget, jeg skal
være opmærksom på? Skriv i punktform og undgå fagudtryk."
hvorfor: "Rollen og de tre faste punkter gør, at du får det samme brugbare
svar hver gang - uanset hvor rodet brevet er."
"""


def lav_dagens_prompt() -> None:
    """Skriver ét nyt AI-forfattet prompt i kartoteket pr. dag (dansk tid).
    Fejler stille - kartoteket må aldrig vælte selve crawlet."""
    if not API_KEY:
        return
    try:
        try:
            from zoneinfo import ZoneInfo
            dag = datetime.now(ZoneInfo("Europe/Copenhagen")).date().isoformat()
        except Exception:
            dag = datetime.now(timezone.utc).date().isoformat()

        arkiv = {"prompts": []}
        if PROMPT_ARKIV.exists():
            try:
                arkiv = json.loads(PROMPT_ARKIV.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        if any(p.get("dato") == dag for p in arkiv.get("prompts", [])):
            return  # dagens prompt findes allerede

        titler = [p.get("titel", "") for p in arkiv.get("prompts", [])][:60]
        r = parse_json_objekt(hjerne_kald(
            "kartotek", SYSTEM_KARTOTEK,
            "Dags dato: " + dag + ". Tidligere titler (undgå gentagelser): "
            + json.dumps(titler, ensure_ascii=False),
            600))
        titel = str(r.get("titel", "")).strip()
        tekst = str(r.get("tekst", "")).strip()
        hvorfor = str(r.get("hvorfor", "")).strip()
        kategori = str(r.get("kategori", "")).strip()
        if kategori not in PROMPT_KATEGORIER:
            kategori = "Hverdag"
        if not titel or len(tekst) < 40:
            print("✨ Dagens prompt: svaret var for tyndt - springer over i dag")
            return
        arkiv.setdefault("prompts", []).insert(0, {
            "dato": dag, "titel": titel, "kategori": kategori,
            "tekst": tekst, "hvorfor": hvorfor,
        })
        PROMPT_ARKIV.parent.mkdir(exist_ok=True)
        PROMPT_ARKIV.write_text(json.dumps(arkiv, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        print(f"✨ Dagens prompt skrevet: \"{titel}\" ({kategori})")
    except Exception as e:
        print(f"✨ Dagens prompt sprang over ({e})")


# ----- Stram gamle "Hvad betyder det for dig?"-tekster --------------------------

SYSTEM_STRAM = """Du strammer "Hvad betyder det for dig?"-tekster til ainyheder.com.
Du får en nummereret liste af tekster, der er for lange.
Skriv hver enkelt om til 1-2 sætninger (maks 35 ord): den ENE konsekvens, der
rammer læserens hverdag, penge eller fremtid. Direkte "du"-sprog. Start aldrig
med "Det betyder" eller "Denne nyhed". Bevar fakta og tal - opdigt intet.

FØR: "Denne udvikling betyder, at der i fremtiden potentielt kan opstå
      situationer, hvor forbrugere oplever ændrede vilkår for de digitale
      tjenester, de bruger i hverdagen, hvilket kan få betydning for økonomien."
EFTER: "Bliver modellerne dyrere at drive, ender regningen hos dig - de gratis
      versioner er som regel de første, der bliver skåret ned."

Bemærk: det er ikke bare kortere. Det er konkret, hvor originalen var vag.
Kan du ikke pege på ÉN konsekvens i materialet, så skriv den ene ting, der
faktisk står der - hellere beskedent og sandt end stort og tomt.

Svar KUN med et JSON-array: [{"nr": 1, "tekst": "..."}, ...] - ét objekt pr. input."""


def stram_betydninger(artikler: list[dict]) -> None:
    """Selvhelende: gamle, lange betydninger skrives om i klumper af 40 pr.
    kørsel, til alle er korte og skarpe. Fejler stille."""
    if not API_KEY:
        return
    lange = [a for a in artikler
             if a.get("betydning") and len(a["betydning"].split()) > 45][:40]
    if not lange:
        return
    try:
        payload = [{"nr": i + 1, "tekst": a["betydning"]} for i, a in enumerate(lange)]
        r = parse_json_svar(hjerne_kald("stram", SYSTEM_STRAM, json.dumps(payload, ensure_ascii=False), 3000))
        rettede = 0
        for p in r if isinstance(r, list) else []:
            try:
                a = lange[int(p.get("nr", 0)) - 1]
            except (ValueError, TypeError, IndexError):
                continue
            tekst = str(p.get("tekst", "")).strip()
            if 15 <= len(tekst) < len(a["betydning"]):
                a["betydning"] = tekst
                rettede += 1
        if rettede:
            print(f"✂️  Strammede {rettede} \"Hvad betyder det for dig?\"-tekster")
    except Exception as e:
        print(f"✂️  Stramning sprang over ({e})")


# ----- Navne tilbage i overskrifterne (selvhelende reparation) ----------------

# Mærker vi genkender som "rigtige navne" - også når de står først i rubrikken,
# hvor stort begyndelsesbogstav ellers ikke afslører et egennavn.
_MAERKER = {
    "google", "alphabet", "deepmind", "openai", "anthropic", "meta", "facebook",
    "instagram", "whatsapp", "apple", "amazon", "aws", "microsoft", "nvidia",
    "oracle", "intel", "amd", "ibm", "tesla", "xai", "spacex", "adobe", "salesforce",
    "samsung", "huawei", "alibaba", "bytedance", "baidu", "tencent", "deepseek",
    "mistral", "midjourney", "perplexity", "stability", "runway", "figma", "canva",
    "github", "linkedin", "tiktok", "youtube", "netflix", "spotify", "reddit",
    "snapchat", "uber", "airbnb", "shopify", "stripe", "zoom", "slack", "notion",
    "chatgpt", "gemini", "claude", "copilot", "llama", "grok", "sora", "veo",
    "alexa", "siri", "cursor", "gpt", "opus", "sonnet", "haiku", "qwen", "kimi",
    "eu", "usa", "kina", "danmark", "norge", "sverige", "tyskland", "storbritannien",
    "folketinget", "regeringen", "kommissionen", "nato", "fn", "trump", "biden",
    # lande og regioner: et stednavn fortæller læseren, hvem det handler om
    "frankrig", "italien", "spanien", "holland", "belgien", "schweiz", "østrig",
    "polen", "finland", "island", "irland", "portugal", "grækenland", "tyrkiet",
    "rusland", "ukraine", "israel", "indien", "japan", "sydkorea", "taiwan",
    "australien", "canada", "brasilien", "mexico", "sydafrika", "egypten",
    "saudi-arabien", "californien", "texas", "georgia", "washington",
    # danske institutioner og medier, der går igen i feedene
    "skat", "politiet", "forsvaret", "dsb", "novo", "mærsk", "pfa", "atp",
    "ingeniøren", "version2", "datamuseum", "systematic", "trackman",
    "bluesky", "codeberg", "hugging", "xprize", "monday",
}

# Formuleringer, der skjuler hvem historien handler om
_VAGE_VENDINGER = (
    "kæmpe gigant", "en gigant", "stor gigant", "stort firma", "stort selskab",
    "et firma", "et selskab", "nyt selskab", "ny virksomhed", "stor virksomhed",
    "en kendt", "kendt firma", "kendt tjeneste", "stor spiller", "en stor spiller",
    "tech-firma", "techfirma", "tech-gigant", "techgigant", "et værktøj",
    "en tjeneste", "udvikler af", "en udbyder",
    # "Gigantens milliard-regnskab" er præcis det eksempel, målestokken forbyder.
    # Kun bestemt form og faste vendinger — "gigantisk" alene er tit bare et
    # tillægsord om noget andet ("bygger gigantisk infrastruktur i Georgia").
    "giganten", "gigantens", "gigantisk firma", "gigantisk selskab",
    "gigantisk virksomhed", "gigantisk ai-firma", "gigantiske firma",
)

# Ord, der ligner et navn (stort begyndelsesbogstav), men kun beskriver en rolle.
# De må aldrig alene tælle som "rubrikken nævner, hvem det handler om".
_GENERISKE_AKTOERER = {
    "gigant", "giganten", "gigantens", "firma", "firmaet", "selskab", "selskabet",
    "virksomhed", "virksomheden", "virksomheder", "koncern", "koncernen",
    "producent", "producenten", "leverandør", "udbyder", "tjeneste", "tjenesten",
    "værktøj", "værktøjet", "app", "appen", "platform", "platformen",
    "forsker", "forskere", "forskerne", "ekspert", "eksperter", "specialist",
    "specialister", "politiker", "politikere", "minister", "ministeren",
    "advokat", "advokaten", "kommune", "kommunen", "kommuner", "myndighed",
    "myndigheder", "styrelse", "regering", "hospital", "hospitalet", "bank",
    "banken", "skole", "skoler", "bibliotek", "biblioteker", "bilfabrik",
    "fabrik", "medarbejder", "medarbejdere", "chef", "chefen", "topchef",
    "stjerner", "stjernerne", "computer", "computere", "computeren",
    "teleselskab", "mediet", "medier", "medierne", "avis", "aviser",
    "brugere", "kunder", "borgere", "eksperten", "analytiker", "analytikere",
}

# "AI" står i næsten hver eneste rubrik på et AI-nyhedssite og fortæller derfor
# ikke læseren, HVEM historien handler om. Samme for de rene AI-sammensætninger.
_IKKE_ET_NAVN = {"ai", "ki"}

# Tegn, der starter en ny sætning. Ordet lige efter har stort bogstav af
# grammatiske grunde ("Nu kan du...", "Det handler om løn") — ikke fordi det er et navn.
_SAETNINGSSTART = set(":;–—.!?")


def _kendt_maerke(ren: str) -> bool:
    """Slår op i _MAERKER — også i ejefald ("Blueskys", "Østrigs", "Trumps")."""
    for form in (ren, ren.split("-")[0]):
        if form in _MAERKER:
            return True
        if form.endswith("s") and form[:-1] in _MAERKER:
            return True
    return False


def _stærkt_navnesignal(o: str, ren: str) -> bool:
    """Signaler, der holder også som FØRSTE ord i en rubrik."""
    if _kendt_maerke(ren):
        return True                           # Google, Trump, Danmark, Blueskys
    if len(re.sub(r"[^A-ZÆØÅ]", "", o)) >= 2 and o == o.upper():
        return True                           # USA, EU, IBM, GPT-5
    if re.search(r"[a-zæøå][A-ZÆØÅ]", o):
        return True                           # OpenAI, DeepSeek, iPhone
    if o[:1].isupper() and (re.search(r"\d", o) or "." in o.strip(".")):
        return True                           # Datamuseum.dk, Monday.com, GPT-5.6
    return False


def _navne_i_tekst(tekst: str, kun_staerke: bool = False) -> set:
    """Hvilke navne (firma, produkt, land, person) nævner denne tekst?

    Det er den samme vurdering som `_har_navn`, men den svarer HVILKE i stedet
    for ja/nej. To ting bruger svaret: `_har_navn` (findes der bare ét?) og
    `_samme_sag`, der skal vide, om to artikler handler om de samme aktører.

    Tre ting gør den strengere, end den ser ud:
      1. "AI" tæller ikke. Det står i næsten hver rubrik og siger intet om hvem.
      2. Et stort bogstav lige efter kolon eller tankestreg tæller ikke — det er
         grammatik ("Nu kan du...", "Det handler om løn"), ikke et navn.
      3. Rolleord som "Gigant", "Kommune", "Forskere" tæller ikke, uanset hvor
         de står. Det er dem, målestokkens punkt 1 handler om.

    Navnet slås ned til én form, så "OpenAI", "OpenAIs" og "OpenAI's" bliver
    det samme navn. Uden det ville sammenligningen i `_samme_sag` sige nej til
    to udgaver af samme historie, blot fordi den ene skrev det i ejefald.

    `kun_staerke` udelader den svageste af de to slags fund: et ord med stort
    begyndelsesbogstav midt i en dansk sætning. Til `_har_navn` er det signal
    rigeligt — står der "Ted Lieu" i en rubrik, nævner den nogen. Men det er
    for løst til at SAMMENLIGNE to artikler med: målt 27.07 gav det "Flere" og
    "Den" som fælles navne og holdt dermed to fejlsammenlægninger i live.
    """
    tekst = tekst or ""
    ord_ = re.findall(r"[0-9A-Za-zÆØÅÉæøåé\-\.'’]+", tekst)
    # hvilke ord står lige efter et sætningsskel?
    efter_skel = set()
    forrige_var_skel = False
    for stykke in re.finditer(r"[0-9A-Za-zÆØÅÉæøåé\-\.'’]+|[^\sA-Za-z0-9ÆØÅæøåé]", tekst):
        s = stykke.group()
        if re.match(r"[0-9A-Za-zÆØÅÉæøåé]", s):
            if forrige_var_skel:
                efter_skel.add(stykke.start())
            forrige_var_skel = False
        elif s in _SAETNINGSSTART:
            forrige_var_skel = True
    pladser = [mo.start() for mo in re.finditer(r"[0-9A-Za-zÆØÅÉæøåé\-\.'’]+", tekst)]

    fundne: set = set()
    for i, o in enumerate(ord_):
        ren = o.strip("-.'’").lower()
        stamme = ren.split("-")[0]
        if not ren:
            continue
        if stamme in _IKKE_ET_NAVN or ren in _IKKE_ET_NAVN:
            continue                          # AI, AI-model, AI-firma
        if (stamme in _GENERISKE_AKTOERER or ren in _GENERISKE_AKTOERER) \
                and not _kendt_maerke(ren):
            continue                          # Gigantens, Kommune, Forskere
        if _stærkt_navnesignal(o, ren):
            fundne.add(_navneform(ren))
        elif not kun_staerke and i > 0 and o[:1].isupper() \
                and pladser[i] not in efter_skel:
            fundne.add(_navneform(ren))       # stort bogstav midt i en dansk sætning
    return fundne


def _navneform(ren: str) -> str:
    """Én fast form pr. navn: kendt mærke slår igennem, ejefald skæres væk."""
    uden_ejefald = re.sub(r"['’]s$", "", ren)
    for form in (uden_ejefald, uden_ejefald.split("-")[0]):
        if form in _MAERKER:
            return form
        if form.endswith("s") and form[:-1] in _MAERKER:
            return form[:-1]
    return uden_ejefald.rstrip("s")


def _har_navn(rubrik: str) -> bool:
    """Sandt hvis rubrikken nævner mindst ét rigtigt navn (firma, produkt, land).
    Reglerne står i `_navne_i_tekst` — den her spørger bare, om der er nogen."""
    return bool(_navne_i_tekst(rubrik))


def _mangler_navn(rubrik: str) -> bool:
    lav = (rubrik or "").lower()
    if any(v in lav for v in _VAGE_VENDINGER):
        return True
    return not _har_navn(rubrik)


SYSTEM_NAVNGIV = """Du retter anonyme overskrifter på ainyheder.com - et dansk
nyhedssite for folk uden teknisk baggrund.

Problemet: overskrifterne har fjernet navnene, så læseren ikke kan se, hvem
historien handler om ("Kæmpe gigant fyrer 21.000" i stedet for "Oracle fyrer 21.000").

Du får den originale engelske titel og resuméet plus vores nuværende danske
rubrik og resumé. Har vi selv skrevet en genfortælling af artiklen, får du et
uddrag af den i "dansk_uddrag" - og **navnet står ofte KUN dér**. Læs altid
uddraget igennem for firma-, produkt- eller landenavne, før du konkluderer, at
materialet ikke nævner nogen.

Skriv rubrik og resumé om, så virksomheden, produktet eller modellen nævnes
ved rigtigt navn - og BEVAR ellers det enkle, folkelige sprog.

Krav:
- "rubrik": max 9 ord, navnet med, intet punktum til sidst.
- "resume": 1-2 sætninger, max 30 ord, hverdagsdansk, navnet med.
- Skriv "AI", aldrig "kunstig intelligens".
- Opdigt ALDRIG navne eller tal. Står navnet ikke i materialet, så find det
  mest konkrete, der ER der: et land, en myndighed, et produkt ("EU-Kommissionen ...",
  "Sydkoreas regering ...", "Alexa Plus ..."). Skriv ALDRIG "techgigant",
  "et stort selskab", "giganten" eller lignende omskrivninger - de bliver afvist,
  og så beholder vi den gamle rubrik.
- Ordet "AI" er IKKE et navn. Det står i næsten hver rubrik på siden og siger
  intet om, hvem historien handler om. At sætte "AI" ind i rubrikken tæller ikke
  som en løsning, og svaret bliver afvist.
- Kan du IKKE finde et navn i materialet, så skriv "rubrik": "" for det nummer.
  Så beholder vi den gamle rubrik. Det er et rigtigt svar, ikke en fejl.
- Behold gerne folkelige billeder ("digital hjerne"), men sæt navnet foran:
  "Anthropics nye digitale hjerne ...".

Svar KUN med et JSON-array: [{"nr": 1, "rubrik": "...", "resume": "..."}, ...]"""


def _dansk_uddrag(a: dict, graense: int = 700) -> str:
    """Crawlerens EGEN danske genfortælling - dér, hvor navnene faktisk står.

    `dybe_briefs()` skriver `sektioner`, `detaljer` og `pointer` ét kald før
    navngivningen i `main()`, men payloaden nedenfor viste dem aldrig til
    modellen: den fik kun den engelske titel (160 tegn), det engelske RSS-resumé
    (250 tegn) og vores egen navnløse rubrik. Målt 26.07 på de 12 låste
    rubrikker stod navnet for tre af dem i netop disse felter og INTET andet
    sted i posten - Microsoft i én, og ChatGPT, Claude og Gemini i en anden.
    Modellen blev altså bedt om at finde navne i materiale, navnene var pillet
    ud af.

    Stumperne MED et navn kommer først. Det er ikke pynt: genfortællingen fylder
    typisk 1.100 tegn alene i `sektioner`, så en simpel klipning ved 700 nåede
    aldrig frem til navnet - Microsoft stod sent i sektionerne, og ChatGPT,
    Claude og Gemini stod i `detaljer`, som slet ikke kom med. Feltet findes for
    at levere navne, så det er navnene, der får pladsen.

    Artikler med `kun_aktuel` (arkivforbud) har ingen genfortælling og får
    tom streng - for dem er der reelt intet mere at vise.
    """
    dele: list[str] = []
    for sek in a.get("sektioner") or []:
        if isinstance(sek, dict):
            dele.append(" ".join(str(sek.get(n) or "")
                                 for n in ("overskrift", "tekst")))
    for felt in ("detaljer", "pointer"):
        for d in a.get(felt) or []:
            dele.append(d if isinstance(d, str)
                        else " ".join(str(v) for v in d.values())
                        if isinstance(d, dict) else str(d))
    rene = [t.strip() for t in dele if t and t.strip()]
    rene.sort(key=_uddrag_vaegt)
    return " ".join(rene)[:graense]


def _uddrag_vaegt(stump: str) -> tuple[int, int]:
    """Sorteringsnøgle: stumper med et sikkert navn først, korteste først.

    Rangen er nødvendig, fordi `sektioner` fylder hele budgettet, hvis den får
    lov. Længden er nødvendig, fordi navnene sidder tættest i `detaljer`, hvor
    én linje på 60 tegn kan rumme tre ("ChatGPT, Claude og Gemini") - mens et
    sektionsafsnit på 300 tegn ofte kun rummer ét. Korteste først giver derfor
    flest navne pr. tegn.

    Rang 0: et navn vi er sikre på - kendt mærke, ORD I STORE BOGSTAVER,
            camelCase. Rang 1: et muligt navn (stort bogstav midt i en sætning,
            fx "Princeton"). Rang 2: ingen navne.
    """
    sikker = any(
        _stærkt_navnesignal(o, o.strip("-.'’").lower())
        for o in re.findall(r"[0-9A-Za-zÆØÅÉæøåé\-\.'’]+", stump)
        if o.strip("-.'’").lower() not in _IKKE_ET_NAVN
        and o.strip("-.'’").lower().split("-")[0] not in _IKKE_ET_NAVN
        and o.strip("-.'’").lower() not in _GENERISKE_AKTOERER
    )
    rang = 0 if sikker else (1 if _har_navn(stump) else 2)
    return (rang, len(stump))


def navngiv_rubrikker(artikler: list[dict], portion: int = 25) -> None:
    """Selvhelende: finder rubrikker uden navne og skriver dem om i klumper,
    så arkivet gradvist bliver konkret. Fejler stille."""
    if not API_KEY:
        return
    anonyme = [a for a in artikler
               if a.get("rubrik") and not a.get("navngivet")
               and _mangler_navn(a["rubrik"])][:portion]
    if not anonyme:
        return
    try:
        payload = []
        for i, a in enumerate(anonyme):
            post = {"nr": i + 1,
                    "engelsk_titel": a.get("titel", "")[:160],
                    "engelsk_resume": (a.get("resume") or "")[:250],
                    "dansk_rubrik": a["rubrik"],
                    "dansk_resume": (a.get("resume_da") or "")[:250]}
            uddrag = _dansk_uddrag(a)
            if uddrag:                        # udelad feltet frem for at sende ""
                post["dansk_uddrag"] = uddrag
            payload.append(post)
        r = parse_json_svar(hjerne_kald("navngiv", SYSTEM_NAVNGIV,
                                    json.dumps(payload, ensure_ascii=False), 3500))
        rettede = 0
        for p in r if isinstance(r, list) else []:
            if not isinstance(p, dict):
                continue          # ét vrøvl-element må ikke tabe hele klumpen:
                                  # p.get() på en streng kaster AttributeError,
                                  # som kun den ydre except fanger.
            try:
                a = anonyme[int(p.get("nr", 0)) - 1]
            except (ValueError, TypeError, IndexError):
                continue
            ny = _som_tekst(p.get("rubrik", "")).strip().rstrip(".")
            nyt_res = _som_tekst(p.get("resume", "")).strip()
            if 10 <= len(ny) <= 90 and len(ny.split()) <= 11 and _har_navn(ny):
                a["rubrik"] = ny
                a["navngivet"] = True         # prøv kun én gang pr. artikel
                if 20 <= len(nyt_res) <= 400:
                    a["resume_da"] = nyt_res
                rettede += 1
            else:
                a["navngivet"] = True         # intet navn i materialet (eller et
                                              # svar, porten afviste) - lad den være
        if rettede:
            print(f"🏷️  Satte navn på {rettede} overskrifter")
    except Exception as e:
        print(f"🏷️  Navngivning sprang over ({e})")


# ----- Dagens overblik (60-sekunders brief på forsiden) ------------------------

BRIEF_FIL = ROOT / "data" / "brief.json"

SYSTEM_BRIEF = """Du skriver "Dagens overblik" til ainyheder.com - fem punkter, der giver en travl dansker hele AI-døgnet på 60 sekunder.
Du får en nummereret liste over døgnets vigtigste historier (rubrik + resumé).
Svar KUN med et JSON-array med PRÆCIS 5 objekter: [{"nr": <historiens nummer>, "tekst": "..."}]
Krav til tekst: én sætning på letlæst dansk (maks 25 ord), konkret, med tal hvor de findes.
Ingen indledninger som "I dag" i hvert punkt - lige på sagen.
Vælg de 5 vigtigste og mest FORSKELLIGE historier - aldrig to punkter om samme begivenhed."""


def lav_dagens_brief(artikler: list[dict]) -> None:
    """Ét nyt 5-punkts overblik pr. dag (dansk tid) til forsiden.
    Fejler stille - briefet må aldrig vælte crawlet."""
    if not API_KEY:
        return
    try:
        try:
            from zoneinfo import ZoneInfo
            dag = datetime.now(ZoneInfo("Europe/Copenhagen")).date().isoformat()
        except Exception:
            dag = datetime.now(timezone.utc).date().isoformat()
        if BRIEF_FIL.exists():
            try:
                if json.loads(BRIEF_FIL.read_text(encoding="utf-8")).get("dato") == dag:
                    return   # dagens brief findes allerede
            except json.JSONDecodeError:
                pass

        graense = (datetime.now(timezone.utc) - timedelta(hours=26)).isoformat()
        kandidater = [a for a in artikler
                      if a.get("rubrik")
                      and (a.get("foerst_set") or a.get("dato") or "") >= graense]
        kandidater.sort(key=lambda a: a.get("prio") or 5, reverse=True)
        kandidater = kandidater[:12]
        if len(kandidater) < 5:
            return   # for stille et døgn til et overblik

        stof = [{"nr": i + 1, "rubrik": a["rubrik"],
                 "resume": (a.get("resume_da") or "")[:200]}
                for i, a in enumerate(kandidater)]
        r = parse_json_svar(hjerne_kald("dagens_overblik", SYSTEM_BRIEF, json.dumps(stof, ensure_ascii=False), 800))

        punkter = []
        for p in r if isinstance(r, list) else []:
            tekst = str(p.get("tekst", "")).strip()
            try:
                link = kandidater[int(p.get("nr", 0)) - 1]["link"]
            except (ValueError, TypeError, IndexError):
                link = ""
            if len(tekst) >= 20:
                punkter.append({"tekst": tekst, "link": link})
        if len(punkter) < 5:
            print("☀️ Dagens brief: svaret var for tyndt - prøver igen næste kørsel")
            return
        BRIEF_FIL.write_text(json.dumps(
            {"dato": dag, "punkter": punkter[:5]}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"☀️ Dagens overblik skrevet ({dag})")
    except Exception as e:
        print(f"☀️ Dagens brief sprang over ({e})")


# ----- Ugens nyhedsquiz --------------------------------------------------------

QUIZ_FIL = ROOT / "data" / "quiz.json"

SYSTEM_QUIZ = """Du laver ugens nyhedsquiz til ainyheder.com ud fra ugens vigtigste AI-historier.
Svar KUN med et JSON-array med præcis 5 objekter: [{"sp": "...", "svar": [["tekst", true/false], ["tekst", false], ["tekst", false]], "fork": "..."}]
Krav:
- sp: et klart spørgsmål på letlæst dansk om noget fra materialet ("Hvilket firma...", "Hvor mange...").
- svar: præcis 3 muligheder, hvor NETOP ÉN er sand (true). De forkerte skal være plausible, ikke fjollede.
- fork: én sætning, der forklarer det rigtige svar.
- Byg KUN på det materiale, du får - opdigt aldrig tal eller navne.
- Spred spørgsmålene over forskellige historier.

FORRÅD IKKE SVARET. En quiz er ligegyldig, hvis man kan gætte uden at have
læst med. Derfor:
- De tre svarmuligheder skal være omtrent lige lange. Det rigtige svar må
  ALDRIG være det længste eller det mest detaljerede.
- De forkerte svar skal være ting, der kunne have været sande - andre rigtige
  firmaer, realistiske tal, plausible årstal. Ikke tydeligt forkerte.
- Undgå "alle ovenstående", "ingen af delene" og absolutter som "aldrig".
- Er tallet i det rigtige svar fx 21.000, så lad de forkerte være 14.000 og
  35.000 - ikke 3 og 900.000."""


def lav_ugens_quiz(artikler: list[dict]) -> None:
    """Én quiz pr. ISO-uge, genereret af AI ud fra ugens tophistorier.
    Fejler stille - quizzen må aldrig vælte crawlet."""
    if not API_KEY:
        return
    try:
        try:
            from zoneinfo import ZoneInfo
            nu_dk = datetime.now(ZoneInfo("Europe/Copenhagen"))
        except Exception:
            nu_dk = datetime.now(timezone.utc)
        iso = nu_dk.isocalendar()
        uge_noegle = f"{iso[0]}-U{iso[1]:02d}"

        if QUIZ_FIL.exists():
            try:
                if json.loads(QUIZ_FIL.read_text(encoding="utf-8")).get("uge") == uge_noegle:
                    return   # ugens quiz findes allerede
            except json.JSONDecodeError:
                pass

        graense = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        kandidater = [a for a in artikler
                      if a.get("rubrik") and (a.get("dato") or "") >= graense]
        kandidater.sort(key=lambda a: a.get("prio") or 5, reverse=True)
        stof = [{"rubrik": a["rubrik"], "resume": a.get("resume_da", ""),
                 "detaljer": (a.get("detaljer") or [])[:3]} for a in kandidater[:10]]
        if len(stof) < 5:
            return

        r = parse_json_svar(hjerne_kald("quiz", SYSTEM_QUIZ, json.dumps(stof, ensure_ascii=False), 2000))
        gyldige = []
        for q in r if isinstance(r, list) else []:
            svar = q.get("svar") or []
            if (q.get("sp") and len(svar) == 3
                    and sum(1 for s in svar if s[1] is True) == 1):
                gyldige.append({"sp": str(q["sp"]).strip(),
                                "svar": [[str(s[0]).strip(), bool(s[1])] for s in svar],
                                "fork": str(q.get("fork", "")).strip()})
        if len(gyldige) < 5:
            print("🎯 Ugens quiz: for få gyldige spørgsmål - prøver igen næste kørsel")
            return
        QUIZ_FIL.write_text(json.dumps(
            {"uge": uge_noegle, "genereret": nu_dk.date().isoformat(),
             "spoergsmaal": gyldige[:5]}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"🎯 Ugens quiz skrevet ({uge_noegle})")
    except Exception as e:
        print(f"🎯 Ugens quiz sprang over ({e})")


# ============================================================================
#  YOUTUBE - hvad rører sig hos de største AI-kanaler
# ----------------------------------------------------------------------------
#  1. Henter hver kanals RSS-feed (titel, dato, thumbnail, visninger, beskrivelse)
#  2. Henter videoens undertekster MED tidskoder (YouTubes eget timedtext-API)
#  3. Lader AI'en skrive et dansk resumé + højdepunkter, hvor HVERT højdepunkt
#     har et tidsstempel, så læseren kan springe direkte til stedet i videoen
#  4. Gemmer alt i data/youtube.json (cache pr. video-ID - hver video koster
#     kun ét AI-kald i hele videoens levetid)
# ============================================================================

YT_FIL = OPSAETNING / "youtube-kanaler.json"
YT_OUTPUT = ROOT / "data" / "youtube.json"
YT_MAX_DAGE = 45             # så langt tilbage vi kigger. Skal være rundeligt:
                             # kanaler som Lex Fridman udgiver kun en gang om
                             # måneden, og de skal stadig være med
YT_MAX_PR_KANAL = 6          # max videoer pr. kanal pr. kørsel
YT_MIN_LAENGDE = 180         # spring Shorts og små klip over (sekunder)
YT_MAX_AI_PR_KOERSEL = 14    # loft over AI-kald pr. kørsel (holder prisen nede)
YT_MAX_FORSOEG = 3           # så mange gange prøver vi at få dansk tekst på en video
YT_MAX_TRANSKRIPT = 42000    # så mange tegn transkript sender vi til AI'en
YT_BLOK_SEK = 40             # undertekster samles i blokke af 40 sekunder

# YouTubes interne app-API. Web-klienten kræver i dag et "proof of origin"-token
# for at udlevere undertekster, men iOS-klienten gør ikke - derfor bruger vi den.
YT_INNERTUBE = "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
YT_UA_IOS = ("com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3_2 "
             "like Mac OS X)")
YT_UA_ANDROID = "com.google.android.youtube/20.10.38 (Linux; U; Android 11) gzip"
YT_KLIENTER = [
    ("IOS", {"clientName": "IOS", "clientVersion": "20.10.4",
             "deviceModel": "iPhone16,2", "hl": "en", "gl": "US"}, YT_UA_IOS),
    ("ANDROID", {"clientName": "ANDROID", "clientVersion": "20.10.38",
                 "androidSdkVersion": 30, "hl": "en", "gl": "US"}, YT_UA_ANDROID),
]

YT_NS = {"a": "http://www.w3.org/2005/Atom",
         "yt": "http://www.youtube.com/xml/schemas/2015",
         "media": "http://search.yahoo.com/mrss/"}

# Kapitler i videoens beskrivelse ("0:00 Intro", "01:23 - Kimi K3"). Bruges som
# ekstra hjælp til AI'en - og som reserve-højdepunkter hvis underteksterne
# ikke kan hentes.
YT_KAPITEL = re.compile(
    r"^[\s>*•-]*\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?\s*[-–—:.)|]*\s+(\S.{2,88})$", re.M)

# Reklameindslag skal aldrig ende som et højdepunkt
YT_REKLAME = re.compile(r"sponsor|ad break|\bads?\b|promo|rabat|discount|"
                        r"use code|abonner|subscribe|giveaway|affiliate", re.I)

YT_EMNER = ["Nye modeller", "Værktøjer & apps", "Kode & agenter", "Forskning",
            "Penge & marked", "Politik & samfund", "Robotter & hardware",
            "Billede & video", "Fremtid & visioner"]


def _yt_hent(url: str, data: bytes | None = None, ua: str = USER_AGENT) -> bytes:
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": ua, "Accept-Language": "en-US,en;q=0.9",
        **({"content-type": "application/json"} if data else {})})
    with urllib.request.urlopen(req, timeout=40 if data else TIMEOUT_SEK) as svar:
        return svar.read()


def _mmss(sek: float) -> str:
    """Sekunder -> "7:04" eller "1:07:04" (som YouTube selv skriver det)."""
    sek = max(0, int(sek))
    t, rest = divmod(sek, 3600)
    m, s = divmod(rest, 60)
    return f"{t}:{m:02d}:{s:02d}" if t else f"{m}:{s:02d}"


def _sek_af_tid(tid: str) -> int | None:
    """"1:07:04" / "7:04" -> sekunder. None hvis det ikke er en tidsangivelse."""
    dele = str(tid or "").strip().split(":")
    if not 2 <= len(dele) <= 3 or not all(d.strip().isdigit() for d in dele):
        return None
    tal = [int(d) for d in dele]
    return tal[0] * 3600 + tal[1] * 60 + tal[2] if len(tal) == 3 else tal[0] * 60 + tal[1]


def yt_crawl_kanal(kanal: dict) -> tuple[dict, list[dict], str | None]:
    """Henter kanalens RSS-feed og returnerer de nyeste videoer."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={kanal['kanal_id']}"
    try:
        rod = ET.fromstring(_yt_hent(url))
    except (urllib.error.URLError, ET.ParseError, TimeoutError, OSError) as fejl:
        return kanal, [], f"{type(fejl).__name__}: {fejl}"

    videoer = []
    for e in rod.findall("a:entry", YT_NS)[:kanal.get("max", YT_MAX_PR_KANAL)]:
        vid = (e.findtext("yt:videoId", namespaces=YT_NS) or "").strip()
        titel = rens_tekst(e.findtext("a:title", default="", namespaces=YT_NS), 200)
        if not vid or not titel:
            continue
        grp = e.find("media:group", YT_NS)
        beskrivelse = (grp.findtext("media:description", default="", namespaces=YT_NS)
                       if grp is not None else "") or ""
        thumb = ""
        stat = None
        if grp is not None:
            t = grp.find("media:thumbnail", YT_NS)
            thumb = t.get("url", "") if t is not None else ""
            stat = grp.find("media:community/media:statistics", YT_NS)
        videoer.append({
            "id": vid,
            "titel": titel,
            "link": f"https://www.youtube.com/watch?v={vid}",
            "kanal": kanal["navn"],
            "gruppe": kanal.get("gruppe", "Andet"),
            "kanal_url": f"https://www.youtube.com/@{kanal['handle']}"
                         if kanal.get("handle") else
                         f"https://www.youtube.com/channel/{kanal['kanal_id']}",
            "dato": parse_dato(e.findtext("a:published", namespaces=YT_NS)),
            "thumb": thumb or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "visninger": int(stat.get("views") or 0) if stat is not None else 0,
            "_beskrivelse": beskrivelse,
        })
    return kanal, videoer, None


def yt_undertekster(vid: str) -> tuple[list[tuple[float, str]], str, int]:
    """Henter videoens undertekster med tidskoder.
    Returnerer (liste af (sekund, tekst), spor-type, videolængde i sekunder)."""
    for navn, klient, ua in YT_KLIENTER:
        try:
            body = json.dumps({"context": {"client": klient}, "videoId": vid,
                               "contentCheckOk": True, "racyCheckOk": True}).encode()
            svar = json.loads(_yt_hent(YT_INNERTUBE, data=body, ua=ua))
        except Exception:
            continue
        varighed = int(svar.get("videoDetails", {}).get("lengthSeconds") or 0)
        spor = ((svar.get("captions") or {}).get("playerCaptionsTracklistRenderer")
                or {}).get("captionTracks") or []
        if not spor:
            if svar.get("playabilityStatus", {}).get("status") == "OK":
                return [], "ingen", varighed      # videoen findes, men har ingen tekst
            continue
        # Manuelle engelske undertekster er bedre end maskingenererede
        spor.sort(key=lambda s: (s.get("kind") == "asr",
                                 not str(s.get("languageCode", "")).startswith("en")))
        try:
            rod = ET.fromstring(_yt_hent(spor[0]["baseUrl"] + "&fmt=srv1", ua=ua))
        except Exception:
            continue
        cues = []
        for t in rod.findall("text"):
            tekst = html.unescape(re.sub(r"\s+", " ", t.text or "")).strip()
            if tekst:
                cues.append((float(t.get("start") or 0), tekst))
        if cues:
            art = "manuelle undertekster" if spor[0].get("kind") != "asr" \
                  else "automatiske undertekster"
            return cues, art, varighed or int(cues[-1][0]) + 10
    return [], "ingen", 0


def yt_kapitler(beskrivelse: str, varighed: int) -> list[dict]:
    """Trækker YouTube-kapitler ud af videoens beskrivelse."""
    kapitler = []
    for tid, tekst in YT_KAPITEL.findall(beskrivelse or ""):
        sek = _sek_af_tid(tid)
        if sek is None or (varighed and sek > varighed):
            continue
        tekst = re.sub(r"\s+", " ", tekst).strip(" -–—:|·")
        if not tekst or len(tekst) < 3 or YT_REKLAME.search(tekst):
            continue
        kapitler.append({"sek": sek, "tid": _mmss(sek), "titel": tekst[:88]})
    # kapitler skal være i stigende rækkefølge - ellers er det tilfældige tal
    i_orden = [k for i, k in enumerate(kapitler)
               if i == 0 or k["sek"] > kapitler[i - 1]["sek"]]
    return i_orden[:14] if len(i_orden) >= 3 else []


def yt_transkript_tekst(cues: list[tuple[float, str]]) -> str:
    """Samler underteksterne i blokke med tidsstempel foran, så AI'en kan
    henvise til et konkret sted i videoen. Er transkriptet for langt (lange
    podcasts kan være 40.000 ord), tyndes blokkene JÆVNT ud - så beholder vi
    dækning over hele videoen i stedet for kun de første minutter."""
    blokke: list[list] = []
    for start, tekst in cues:
        if blokke and start - blokke[-1][0] < YT_BLOK_SEK:
            blokke[-1][1].append(tekst)
        else:
            blokke.append([start, [tekst]])
    samlet = [(b[0], " ".join(b[1])) for b in blokke]
    while True:
        tekst = "\n".join(f"[{_mmss(s)}] {t}" for s, t in samlet)
        if len(tekst) <= YT_MAX_TRANSKRIPT or len(samlet) <= 30:
            return tekst[:YT_MAX_TRANSKRIPT]
        samlet = samlet[::2]


SYSTEM_YT = f"""Du er redaktør på et dansk AI-nyhedssite for almindelige
mennesker uden teknisk baggrund. Du får en YouTube-videos transkript med
tidsstempler i formen [MM:SS] foran hvert afsnit. Du skriver en dansk
opsummering, så læseren på 30 sekunder ved, om videoen er værd at se - og
præcis hvor i videoen det interessante ligger.

REGLER FOR SPROGET
- Skriv ultrakort, letlæst hverdagsdansk. Ingen jargon, ingen buzzwords.
- Skriv ALTID "AI" - aldrig "kunstig intelligens".
- Modelnavne (Gemini, GPT, Claude, Llama osv.) skrives præcis som i videoen.
- Genfortæl i DINE EGNE ord. Oversæt aldrig sætninger direkte fra transkriptet.
- Fremhæv de 1-2 vigtigste tal eller navne pr. afsnit med **dobbelt-stjerner**.

REGLER FOR HØJDEPUNKTER (det vigtigste)
- Tidsstemplet SKAL komme fra transkriptet - find det [MM:SS], hvor emnet
  faktisk starter. Gæt ALDRIG et tidspunkt, og opfind ALDRIG et emne.
- Vælg de steder, en travl dansker ville spole hen til: nye modeller,
  konkrete demoer, tal og benchmarks, skarpe holdninger, overraskelser.
- Spring reklamer, sponsorater, intro-jingler og "husk at abonnere" over.
- Skriv hvad der SKER på stedet - ikke "her taler han om X".

Svar KUN med ét JSON-objekt:
{{
 "rubrik":   dansk overskrift til videoen, max 9 ord, ingen clickbait.
             Sig hvad videoen HANDLER om, ikke hvad kanalen heder,
 "resume":   2-3 sætninger (max 45 ord): hvad handler videoen om, og hvorfor
             er den værd at bruge tid på,
 "hoejdepunkter": 3-6 punkter, i tidsrækkefølge:
             [{{"tid": "12:34", "titel": "kort dansk overskrift, max 6 ord",
               "tekst": "1-2 sætninger om hvad der sker her, max 30 ord"}}],
 "pointer":  3-4 ultrakorte hovedpointer fra videoen (hver max 12 ord),
 "betydning": 1-2 sætninger (max 35 ord) skrevet direkte til "du": hvad kan
             DU bruge det til, eller hvorfor bør du holde øje. Start aldrig
             med "Det betyder" - lige på pointen,
 "emner":    1-3 emner fra PRÆCIS denne liste: {", ".join(YT_EMNER)},
 "prio":     1-10. Hvor vigtig er videoen for en dansker, der vil følge med i
             AI? 9-10 = stor nyhed alle bør kende. 5 = fin, men smal.
             1-3 = reklametung, gentagelse eller uden reelt nyt indhold,
 "om_ai":    true/false. Handler videoen i det hele taget om AI eller teknologi?
             Flere af kanalerne laver også videoer om helt andre emner
             (historie, sundhed, politik) - dem har siden ikke brug for.
             Sæt false, hvis AI kun nævnes i forbifarten
}}"""


# Nødplan: kan underteksterne ikke hentes (YouTube afviser af og til kald fra
# servere), skriver vi resuméet ud fra beskrivelsen og kapitlerne i stedet.
SYSTEM_YT_UDEN_TRANSKRIPT = """

VIGTIG UNDTAGELSE FOR DENNE VIDEO: Underteksterne kunne IKKE hentes. Du får i
stedet kanalens egen beskrivelse og kapitelliste.
- Skriv KUN det, materialet dækker. Opdigt ALDRIG detaljer, tal eller udtalelser.
- Hold resuméet kortere og mere forsigtigt - beskriv hvad videoen handler om,
  ikke hvad der konkret bliver sagt.
- "hoejdepunkter" SKAL bruge kapitlernes tidsstempler præcis som de står.
  Er der ingen kapitler, skal listen være TOM.
- "pointer" må være en tom liste, hvis beskrivelsen ikke rummer nok."""


def yt_kald_ai(v: dict, transkript: str, kapitler: list[dict],
               beskrivelse: str = "") -> dict | None:
    """Får AI'en til at skrive dansk resumé + højdepunkter for én video."""
    try:
        bruger = (f"KANAL: {v['kanal']}\nVIDEOENS TITEL: {v['titel']}\n"
                  f"LÆNGDE: {_mmss(v.get('varighed') or 0)}\n")
        if kapitler:
            bruger += ("\nKANALENS EGNE KAPITLER"
                       + (":\n" if not transkript else
                          " (vejledende - brug dem kun hvis transkriptet bekræfter dem):\n")
                       + "\n".join(f"[{k['tid']}] {k['titel']}" for k in kapitler))
        if transkript:
            bruger += f"\n\nTRANSKRIPT MED TIDSSTEMPLER:\n{transkript}"
        else:
            bruger += f"\n\nKANALENS BESKRIVELSE AF VIDEOEN:\n{beskrivelse[:4000]}"
        r = parse_json_objekt(hjerne_kald("youtube",
            SYSTEM_YT + ("" if transkript else SYSTEM_YT_UDEN_TRANSKRIPT),
            bruger, 1800))
        # Uden transkript er højdepunkter valgfrie - resuméet er stadig værdifuldt
        return r if r.get("rubrik") and (r.get("hoejdepunkter") or not transkript) else None
    except Exception as fejl:
        print(f"  ⚠️  YouTube-resumé fejlede ({v['kanal']}): {type(fejl).__name__}: {fejl}")
    return None


def _yt_anvend(v: dict, r: dict, cues: list[tuple[float, str]],
               kapitler: list[dict] | None = None) -> None:
    """Lægger AI-svaret ind på videoen - og VERIFICERER hvert tidsstempel mod
    de rigtige undertekster, så et link aldrig peger et sted, der ikke findes.
    Findes der ingen undertekster, holdes tidsstemplerne op mod kapitlerne."""
    v["rubrik"] = str(r["rubrik"]).strip()
    v["resume_da"] = str(r.get("resume", "")).strip()
    v["betydning"] = str(r.get("betydning", "")).strip()
    v["pointer"] = [t for t in (_som_tekst(p) for p in r.get("pointer", [])) if t][:4]
    v["emner"] = [e for e in (str(x).strip() for x in r.get("emner", []))
                  if e in YT_EMNER][:3]
    try:
        v["prio"] = max(1, min(10, int(float(r.get("prio") or 5))))
    except (TypeError, ValueError):
        v["prio"] = 5

    # Hvad holder vi tidsstemplerne op mod? Underteksterne er bedst; ellers
    # kapitlerne. Har vi hverken det ene eller det andet, kan vi ikke
    # kontrollere et enkelt tidsstempel - og så udgiver vi ingen.
    if cues:
        starter, slip_paa = sorted(c[0] for c in cues), 90
    elif kapitler:
        starter, slip_paa = sorted(float(k["sek"]) for k in kapitler), 5
    else:
        v["hoejdepunkter"] = []
        return

    varighed = v.get("varighed") or 0
    punkter = []
    for h in r.get("hoejdepunkter", []) or []:
        if not isinstance(h, dict):
            continue
        sek = _sek_af_tid(h.get("tid"))
        if sek is None and str(h.get("sek") or "").strip().isdigit():
            sek = int(h["sek"])
        titel = re.sub(r"\s+", " ", str(h.get("titel", "")).strip())
        tekst = re.sub(r"\s+", " ", str(h.get("tekst", "")).strip())
        if sek is None or not titel or (varighed and sek > varighed + 5):
            continue
        # Sæt tidsstemplet på det nærmeste sted, hvor der faktisk bliver sagt
        # noget. Ligger AI'ens gæt for langt fra alt, vi kan bekræfte,
        # er det opdigtet - så ryger punktet ud.
        naermest = min(starter, key=lambda s: abs(s - sek))
        if abs(naermest - sek) > slip_paa:
            continue
        sek = int(naermest)
        punkter.append({"sek": max(0, sek), "tid": _mmss(sek),
                        "titel": titel[:70], "tekst": tekst[:220]})
    punkter.sort(key=lambda p: p["sek"])
    v["hoejdepunkter"] = punkter[:6]


def lav_youtube() -> None:
    """Crawler AI-kanalerne på YouTube og skriver data/youtube.json."""
    if not YT_FIL.exists():
        return
    try:
        opsaet = json.loads(YT_FIL.read_text(encoding="utf-8"))
        kanaler = opsaet["kanaler"]
    except (json.JSONDecodeError, KeyError) as fejl:
        print(f"📺 youtube.json kunne ikke læses ({fejl}) - springer YouTube over")
        return

    print(f"\n📺 Crawler {len(kanaler)} YouTube-kanaler …")
    nu = datetime.now(timezone.utc)

    # Cache: en video, der én gang er opsummeret, opsummeres aldrig igen.
    # "afvist" husker de videoer, vi har set på og sagt nej til (Shorts og
    # videoer uden med AI at gøre) - så vi aldrig betaler for dem to gange.
    cache: dict = {}
    afvist: list = []
    if YT_OUTPUT.exists():
        try:
            gemt = json.loads(YT_OUTPUT.read_text(encoding="utf-8"))
            for g in gemt.get("videoer", []):
                if g.get("rubrik") or g.get("hoejdepunkter"):
                    cache[g["id"]] = g
            afvist = [str(i) for i in gemt.get("afvist", [])][:400]
        except (json.JSONDecodeError, KeyError):
            pass
    afvist_set = set(afvist)     # slå hurtigt op
    nye_afvist: list = []        # afvist i DENNE kørsel (kommer forrest i filen)

    alle: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = [pool.submit(yt_crawl_kanal, k) for k in kanaler]
        for job in as_completed(jobs):
            kanal, videoer, fejl = job.result()
            print(f"  {'⚠️ ' if fejl else '✅'} {kanal['navn']}: "
                  f"{fejl if fejl else str(len(videoer)) + ' videoer'}")
            alle.extend(videoer)

    # For gamle væk + nyeste først
    friske = [v for v in alle
              if v["dato"] is None or (nu - v["dato"]).days <= YT_MAX_DAGE]
    friske.sort(key=lambda v: v["dato"] or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True)

    # En video regnes FÆRDIG når den har et dansk resumé - ikke bare fordi den
    # ligger i cachen. Ellers låser en video sig fast for evigt: kapitlerne
    # gemmes nemlig FØR AI-kaldet, så et mislykket kald efterlod den i cachen
    # uden dansk tekst og uden nogensinde at blive prøvet igen.
    def _skal_proeves(v: dict) -> bool:
        g = cache.get(v["id"])
        if g is None:
            return True                                   # aldrig set før
        return (not g.get("rubrik")
                and int(g.get("forsoeg") or 0) < YT_MAX_FORSOEG)

    nye = [v for v in friske if v["id"] not in afvist_set and _skal_proeves(v)]
    if GENKOER_ALT:
        nye = friske
        afvist, afvist_set, nye_afvist = [], set(), []
    print(f"📺 {len(friske)} videoer inden for {YT_MAX_DAGE} dage "
          f"({len(nye)} skal behandles, resten ligger i cache)")

    brugt = 0
    for v in nye:
        if brugt >= YT_MAX_AI_PR_KOERSEL:
            print(f"📺 Nåede loftet på {YT_MAX_AI_PR_KOERSEL} videoer - "
                  "resten tages næste kørsel")
            break
        cues, sportype, varighed = yt_undertekster(v["id"])
        v["varighed"] = varighed
        if varighed and varighed < YT_MIN_LAENGDE:
            afvist_set.add(v["id"]); nye_afvist.append(v["id"])   # Shorts/små klip
            continue
        kapitler = yt_kapitler(v.get("_beskrivelse", ""), varighed)
        if kapitler:
            v["hoejdepunkter"] = kapitler        # reserve indtil AI'en har været her
            v["hp_kilde"] = "kapitler"
        if cues:
            v["kilde_type"] = sportype
        if not API_KEY:
            continue                             # ingen nøgle: kun kapitler og titel
        beskrivelse = v.get("_beskrivelse", "")
        if not cues and len(beskrivelse) < 200 and not kapitler:
            print(f"   ⚠️  {v['kanal']}: hverken undertekster, kapitler eller "
                  f"beskrivelse ({v['titel'][:36]}) - springer resumé over")
            continue
        if not cues:
            print(f"   ℹ️  {v['kanal']}: ingen undertekster - skriver resumé ud "
                  "fra beskrivelsen i stedet")
        # Tæl forsøget FØR kaldet - så en video, der bliver ved med at fejle,
        # giver op efter YT_MAX_FORSOEG i stedet for at koste penge hver time.
        v["forsoeg"] = int(cache.get(v["id"], {}).get("forsoeg") or 0) + 1
        r = yt_kald_ai(v, yt_transkript_tekst(cues) if cues else "",
                       kapitler, beskrivelse)
        brugt += 1
        if r and r.get("om_ai") is False:
            afvist_set.add(v["id"]); nye_afvist.append(v["id"])   # ikke om AI
            print(f"   ⤫ {v['kanal']}: handler ikke om AI - {v['titel'][:44]}")
            continue
        if r:
            _yt_anvend(v, r, cues, kapitler)
            v["hp_kilde"] = "undertekster" if cues else "kapitler"
            if not v.get("hoejdepunkter") and kapitler:
                # AI'ens punkter faldt for tidstjekket - brug kanalens kapitler
                v["hoejdepunkter"], v["hp_kilde"] = kapitler, "kapitler"
        print(f"   … {brugt}/{min(len(nye), YT_MAX_AI_PR_KOERSEL)} "
              f"{v['kanal']}: {v.get('rubrik') or v['titel'][:48]}")

    # Byg den endelige liste: cache-værdier bevares, nye lægges oveni
    resultat = []
    for v in friske:
        if v["id"] in afvist_set:
            continue
        gammel = cache.get(v["id"], {})
        if gammel.get("varighed", 0) and gammel["varighed"] < YT_MIN_LAENGDE:
            continue
        ny = {**gammel, **{k: x for k, x in v.items()
                           if not k.startswith("_") and x not in (None, "", 0, [])}}
        ny["dato"] = v["dato"].isoformat() if v["dato"] else gammel.get("dato")
        ny["foerst_set"] = gammel.get("foerst_set") or nu.isoformat()
        ny["visninger"] = v.get("visninger") or gammel.get("visninger", 0)
        ny.pop("_beskrivelse", None)
        ny.pop("_spring", None)
        if ny.get("rubrik"):
            ny.pop("forsoeg", None)        # lykkedes - nulstil tælleren
        resultat.append(ny)

    # Nyeste først (efter hvornår VI så videoen, som på forsiden)
    resultat.sort(key=lambda v: (v.get("foerst_set") or "", v.get("dato") or ""),
                  reverse=True)

    lav_videosider(resultat)     # statiske SEO-sider + "side"-felt til links

    YT_OUTPUT.parent.mkdir(exist_ok=True)
    YT_OUTPUT.write_text(json.dumps({
        "opdateret": nu.isoformat(),
        "antal": len(resultat),
        "grupper": opsaet.get("grupper", []),
        "emner": YT_EMNER,
        "kanaler": [{"navn": k["navn"], "gruppe": k.get("gruppe", "Andet"),
                     "url": f"https://www.youtube.com/@{k['handle']}"
                            if k.get("handle") else
                            f"https://www.youtube.com/channel/{k['kanal_id']}"}
                    for k in kanaler],
        "videoer": resultat,
        # Huskeliste over videoer vi har sagt nej til - så de aldrig koster igen
        "afvist": (nye_afvist
                   + [i for i in afvist if i not in set(nye_afvist)])[:400],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    paa_dansk = sum(1 for v in resultat if v.get("rubrik"))
    print(f"💾 Gemte {len(resultat)} YouTube-videoer ({paa_dansk} med dansk resumé) "
          f"i {YT_OUTPUT.relative_to(ROOT)}")


# ----- Hovedprogram ----------------------------------------------------------

# ----- Læsertal fra Cloudflare Web Analytics ---------------------------------
#
# Uden de her tal kan loopet kun se, om siden er PÆN - ikke om nogen læser den.
# Kræver secrets CLOUDFLARE_API_TOKEN og CLOUDFLARE_ACCOUNT_ID. Mangler de,
# springes trinnet stille over, og gennemgangen kører videre uden læsertal.

LAESERTAL_FIL = ROOT / "data" / "laesertal.json"
CF_GRAPHQL = "https://api.cloudflare.com/client/v4/graphql"
# Web Analytics' site-tag. Det er IKKE det samme som "token" i beacon-koden på
# siderne (den er fda17dd7…) - de to er forskellige felter med hver sin værdi,
# og netop dén forveksling gav nul besøg uden en eneste fejlbesked: kontoen
# fandtes, godkendelsen virkede, og forespørgslen spurgte bare om et site, der
# ikke eksisterede. Tag'et står i adressen, når sitet vises i Cloudflare:
#   dash.cloudflare.com/<konto>/web-analytics/overview?siteTag~in=<DET HER>
CF_SITE_TAG = "7abf4e75cf4e48bda49ad354e8cd6f27"
LAESERTAL_DAGE = 7
# Kurverne skal kunne vise en udvikling, og det kan syv dage ikke. De første
# uger står der nuller i venstre side - beacon'en kom på siden 22.07.2026 -
# og det er ærligere end at klippe aksen til, så det ligner mere, end det er.
LAESERTAL_SERIE_DAGE = 30

# Bliver vi fundet i AI-chats? Cloudflare fortæller kun, HVILKEN vært folk kom
# fra. Listen her oversætter de værter, vi kender, til læselige navne. Ukendte
# værter tælles ikke med: hellere et lavt tal, vi kan stole på, end et højt,
# der er gættet. Søgemaskiner hører ikke til her - kun chats.
AI_CHAT_KILDER = [
    ("chatgpt.com", "ChatGPT"),
    ("chat.openai.com", "ChatGPT"),
    ("perplexity.ai", "Perplexity"),
    ("claude.ai", "Claude"),
    ("copilot.microsoft.com", "Microsoft Copilot"),
    ("gemini.google.com", "Gemini"),
    ("bard.google.com", "Gemini"),
    ("chat.deepseek.com", "DeepSeek"),
    ("chat.mistral.ai", "Le Chat"),
    ("grok.com", "Grok"),
    ("x.ai", "Grok"),
    ("you.com", "You.com"),
    ("poe.com", "Poe"),
    ("phind.com", "Phind"),
]


# De sider, vi selv har besluttet skal findes. Får en af dem nul besøg på en
# uge, er det den interessante oplysning - ikke at forsiden klarer sig fint.
# Står her ét sted, fordi både gennemgangen og kontrolpanelet spørger om den.
FASTE_SIDER = [
    "/", "/laer.html", "/koerekort.html", "/erhverv.html", "/prompts.html",
    "/prompt-arkiv.html", "/ordbog.html", "/quiz.html", "/uge.html",
    "/youtube.html", "/vaerktoejer.html", "/faq.html", "/om.html",
    "/guide-igang.html", "/guide-prompts.html", "/guide-sikkerhed.html",
]


def _ai_chat_navn(vaert: str) -> str | None:
    """Navnet på den AI-chat, en henviser-vært hører til - ellers None.
    Matcher på endelsen, så www. og andre underdomæner også fanges."""
    v = (vaert or "").lower().lstrip(".")
    for endelse, navn in AI_CHAT_KILDER:
        if v == endelse or v.endswith("." + endelse):
            return navn
    return None


def _faste_uden_besoeg(sider: list) -> list:
    """De faste sider, som slet ingen har åbnet i perioden.

    Tæller SIDEVISNINGER, ikke besøg. "Besøg" er kun dem, der landede på siden
    udefra - så en side kan have nul besøg og alligevel være læst af mange, der
    klikkede sig derind fra forsiden. Målt 26.07.2026 havde /prompts.html nul
    besøg og fjorten visninger; kaldte vi den ulæst, ville gennemgangen gå i
    gang med at rette noget, der ikke fejlede. Cloudflare nævner slet ikke en
    side uden trafik, så fraværet fra listen ER svaret."""
    set_ = {s["sti"].rstrip("/") or "/": s["visninger"] for s in sider}
    return [p for p in FASTE_SIDER if set_.get(p, 0) == 0]


def _hent_dagsserie(token: str, konto_tag: str, dage: int) -> list:
    """Besøg og sidevisninger pr. dag - kurven, der viser om det går frem.

    Egen forespørgsel med vilje. Grupperingen på dato er den eneste del, jeg
    ikke har set svare endnu, og fejler den, skal vi kun miste kurven - ikke
    de tal, der allerede virker."""
    nu = datetime.now(timezone.utc)
    query = """
query ($konto: String!, $tag: String!, $fra: Time!, $til: Time!) {
  viewer { accounts(filter: {accountTag: $konto}) {
    dage: rumPageloadEventsAdaptiveGroups(
      limit: 400,
      filter: {siteTag: $tag, datetime_geq: $fra, datetime_leq: $til, bot: 0}
    ) { sum { visits } count dimensions { date } }
  } }
}"""
    try:
        svar = json.loads(hent_url(CF_GRAPHQL, data=json.dumps({
            "query": query,
            "variables": {
                "konto": konto_tag, "tag": CF_SITE_TAG,
                "fra": (nu - timedelta(days=dage)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "til": nu.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }).encode(), headers={"Authorization": f"Bearer {token}",
                              "Content-Type": "application/json"}))
        if svar.get("errors"):
            print(f"📈 ⚠️ Dagskurven sprang over: {str(svar['errors'])[:120]}")
            return []
        konti = (svar.get("data") or {}).get("viewer", {}).get("accounts") or []
        raekker = (konti[0].get("dage") if konti else []) or []
        maalt = {(r.get("dimensions") or {}).get("date"): r for r in raekker}
        # Fyld hullerne ud: en dag uden besøg nævner Cloudflare slet ikke, og
        # uden nulpunkterne ville kurven springe hen over de stille dage.
        ud, idag = [], nu.date()
        for i in range(dage - 1, -1, -1):
            d = (idag - timedelta(days=i)).isoformat()
            r = maalt.get(d)
            ud.append({"dato": d,
                       "besoeg": ((r or {}).get("sum") or {}).get("visits", 0),
                       "visninger": (r or {}).get("count", 0)})
        return ud
    except Exception as fejl:
        print(f"📈 ⚠️ Dagskurven sprang over ({type(fejl).__name__}: {fejl})")
        return []


def _hent_sidehenvisere(token: str, konto_tag: str, dage: int) -> dict:
    """Hvor læserne kom fra - opdelt PR. SIDE, ikke for hele sitet under ét.

    Samme datasæt som de øvrige tal, men grupperet på to dimensioner på én
    gang (sti × henviser). Det er dét, der gør det muligt at klikke ind på en
    artikel og se, om folk kom fra Facebook eller fra Google. Egen forespørgsel
    med vilje: fejler den, mister vi kun opdelingen."""
    nu = datetime.now(timezone.utc)
    query = """
query ($konto: String!, $tag: String!, $fra: Time!, $til: Time!) {
  viewer { accounts(filter: {accountTag: $konto}) {
    par: rumPageloadEventsAdaptiveGroups(
      limit: 500, orderBy: [sum_visits_DESC],
      filter: {siteTag: $tag, datetime_geq: $fra, datetime_leq: $til, bot: 0}
    ) { sum { visits } count dimensions { requestPath refererHost } }
  } }
}"""
    try:
        svar = json.loads(hent_url(CF_GRAPHQL, data=json.dumps({
            "query": query,
            "variables": {
                "konto": konto_tag, "tag": CF_SITE_TAG,
                "fra": (nu - timedelta(days=dage)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "til": nu.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }).encode(), headers={"Authorization": f"Bearer {token}",
                              "Content-Type": "application/json"}))
        if svar.get("errors"):
            print(f"📈 ⚠️ Henvisere pr. side sprang over: {str(svar['errors'])[:120]}")
            return {}
        konti = (svar.get("data") or {}).get("viewer", {}).get("accounts") or []
        pr_sti: dict = {}
        for r in ((konti[0].get("par") if konti else []) or []):
            dim = r.get("dimensions") or {}
            sti = dim.get("requestPath") or ""
            if not sti:
                continue
            vaert = dim.get("refererHost") or "direkte"
            if vaert == "ainyheder.com":
                vaert = "herfra selv"     # klik videre inde på siden
            pr_sti.setdefault(sti, []).append(
                {"fra": vaert, "besoeg": (r.get("sum") or {}).get("visits", 0),
                 "visninger": r.get("count", 0)})
        for liste in pr_sti.values():
            liste.sort(key=lambda h: -h["visninger"])
        return pr_sti
    except Exception as fejl:
        print(f"📈 ⚠️ Henvisere pr. side sprang over ({type(fejl).__name__}: {fejl})")
        return {}


def _artikel_kartotek() -> dict:
    """Sti -> {rubrik, kategori, dato} for hver artikelside, vi kan finde.

    Cloudflare kender kun stien "/artikel/c13d67…html". Skal panelet vise en
    rubrik i stedet for en hash, skal de to kobles her. articles.json har det
    seneste vindue med de pæneste data; de statiske sider dækker resten, fordi
    de overlever, når artiklen falder ud af arkivfilen."""
    kartotek: dict = {}
    for p in sorted(ARTIKEL_MAPPE.glob("*.html")):
        h = p.read_text(encoding="utf-8", errors="ignore")
        def felt(navn: str) -> str:
            m = re.search(r'"%s":\s*"((?:[^"\\]|\\.)*)"' % navn, h)
            # JSON-LD'en er escapet ("Samfund & etik"), så den skal tilbage
            return json.loads('"%s"' % m.group(1)) if m else ""
        kartotek["/" + p.relative_to(ROOT).as_posix()] = {
            "rubrik": felt("headline"),
            "kategori": felt("articleSection"),
            "dato": felt("datePublished")[:10],
        }
    try:
        arkiv = json.loads(OUTPUT_FIL.read_text(encoding="utf-8"))
        for a in arkiv.get("artikler", []):
            if a.get("side"):
                kartotek["/" + a["side"]] = {
                    "rubrik": a.get("rubrik") or a.get("titel", ""),
                    "kategori": a.get("kategori", ""),
                    "dato": (a.get("dato") or "")[:10],
                }
    except (OSError, json.JSONDecodeError):
        pass
    return kartotek


def _tema_serie(kartotek: dict, dage: int) -> dict:
    """Hvor mange artikler vi UDGAV pr. kategori pr. dag.

    Det er vores egen produktion, ikke hvad folk læste - to forskellige ting,
    og panelet siger hvilken er hvilken. Den her kan regnes ud lokalt og har
    hele arkivet bag sig, mens læsetallene kun kender de sidste dage."""
    idag = datetime.now(timezone.utc).date()
    datoer = [(idag - timedelta(days=i)).isoformat() for i in range(dage - 1, -1, -1)]
    plads = {d: i for i, d in enumerate(datoer)}
    pr_kat: dict = {}
    for v in kartotek.values():
        kat, d = v.get("kategori"), v.get("dato")
        if not kat or d not in plads:
            continue
        pr_kat.setdefault(kat, [0] * len(datoer))[plads[d]] += 1
    serier = sorted(({"navn": k, "tal": v} for k, v in pr_kat.items()),
                    key=lambda s: -sum(s["tal"]))
    return {"datoer": datoer, "serier": serier}


def _skriv_laesertal(tal: dict) -> None:
    """Skriver begge udgaver af datafilen: JSON til mennesker og maskiner, og
    en .js-udgave, fordi kontrolpanelet åbnes fra file://, hvor browseren ikke
    må hente JSON. Ligger i data/, fordi det er dén mappe, workflow'en
    committer."""
    LAESERTAL_FIL.parent.mkdir(exist_ok=True)
    LAESERTAL_FIL.write_text(json.dumps(tal, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    (LAESERTAL_FIL.parent / "laesertal-data.js").write_text(
        "window.LAESERTAL = " + json.dumps(tal, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8")


def hent_laesertal() -> dict | None:
    """Skriver ALTID datafilen - også når Cloudflare ikke kan svare.

    Temaerne regnes ud af vores egne artikelsider og har intet med Cloudflare
    at gøre. Lå de inde i det svar, så et udløbet token også ville tage
    temagrafen med sig, og det ville se ud som om arkivet var forsvundet.
    Læsertallene er den valgfri del; temaerne er der altid."""
    kartotek = _artikel_kartotek()
    tal = {
        "opdateret": datetime.now(timezone.utc).isoformat(),
        "dage": LAESERTAL_DAGE,
        "serie_dage": LAESERTAL_SERIE_DAGE,
        "udgivne_temaer": _tema_serie(kartotek, LAESERTAL_SERIE_DAGE),
        "maaling": "mangler_token",
        "besoeg_i_alt": 0, "sidevisninger_i_alt": 0, "ai_chat_besoeg": 0,
        "sider": [], "henvisere": [], "ai_chats": [], "sidehenvisere": {},
        "faste_uden_besoeg": [], "serie": [], "artikler": [], "laeste_temaer": [],
    }
    if os.environ.get("CLOUDFLARE_API_TOKEN", "").strip():
        maalt = _hent_cloudflare_tal(kartotek)
        tal["maaling"] = "ok" if maalt else "fejl"
        if maalt:
            tal.update(maalt)
    _skriv_laesertal(tal)
    return tal


def _hent_cloudflare_tal(kartotek: dict) -> dict | None:
    """Henter de seneste dages besøg pr. side fra Cloudflare Web Analytics.
    Fejler stille - læsertal er en gave, ikke en forudsætning."""
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    konto = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not token:
        return None
    nu = datetime.now(timezone.utc)
    fra = (nu - timedelta(days=LAESERTAL_DAGE)).strftime("%Y-%m-%dT%H:%M:%SZ")
    til = nu.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Konto-id er valgfrit. Er det ikke sat, spørger vi ALLE de konti, tokenet
    # har adgang til, og vælger bagefter den, der faktisk har tal for vores
    # site-tag. Før tog vi bare den første (limit: 1) - og havde man mere end
    # én konto, skrev vi tavst nuller fra den forkerte. Det ligner til
    # forveksling "ingen har besøgt siden", og det er en dyr forveksling.
    variabler = {"tag": CF_SITE_TAG, "fra": fra, "til": til}
    if konto:
        variabler["konto"] = konto
    query = ("""
query (%s$tag: String!, $fra: Time!, $til: Time!) {
  viewer { accounts%s {
    accountTag""" % (
        "$konto: String!, " if konto else "",
        "(filter: {accountTag: $konto})" if konto else "")) + """
    sider: rumPageloadEventsAdaptiveGroups(
      limit: 60, orderBy: [sum_visits_DESC],
      filter: {siteTag: $tag, datetime_geq: $fra, datetime_leq: $til, bot: 0}
    ) { sum { visits } count dimensions { requestPath } }
    henvisere: rumPageloadEventsAdaptiveGroups(
      limit: 50, orderBy: [sum_visits_DESC],
      filter: {siteTag: $tag, datetime_geq: $fra, datetime_leq: $til, bot: 0,
               refererHost_neq: "ainyheder.com"}
    ) { sum { visits } dimensions { refererHost } }
  } }
}"""
    try:
        svar = json.loads(hent_url(CF_GRAPHQL, data=json.dumps({
            "query": query,
            "variables": variabler,
        }).encode(), headers={"Authorization": f"Bearer {token}",
                              "Content-Type": "application/json"}))
        if svar.get("errors"):
            print(f"📈 ⚠️ Cloudflare svarede med fejl: "
                  f"{str(svar['errors'])[:140]}")
            return None
        konti = (svar.get("data") or {}).get("viewer", {}).get("accounts") or []
        if not konti:
            print("📈 ⚠️ Cloudflare gav ingen konti tilbage - har tokenet "
                  "rettigheden Account Analytics · Read?")
            return None
        # Vælg den konto, der rent faktisk har tal for vores site-tag. Har man
        # kun én, er det den. Har man flere, er det den rigtige - i stedet for
        # den første, der tilfældigvis kom retur.
        med_data = [k for k in konti if (k.get("sider") or [])]
        if len(konti) > 1:
            print(f"📈 Tokenet ser {len(konti)} Cloudflare-konti; "
                  f"{len(med_data)} har data for site-tag {CF_SITE_TAG[:8]}…")
        d = med_data[0] if med_data else konti[0]
        sider = [{"sti": (r.get("dimensions") or {}).get("requestPath", ""),
                  "besoeg": (r.get("sum") or {}).get("visits", 0),
                  "visninger": r.get("count", 0)}
                 for r in d.get("sider") or []]
        sider = [s for s in sider if s["sti"]]
        if not sider:
            print(f"📈 ⚠️ Nul sidevisninger for site-tag {CF_SITE_TAG[:8]}… på "
                  f"{len(konti)} konto(er). Enten er der reelt ingen besøg, "
                  f"eller også hører beacon'en på siden til et andet site i "
                  f"Web Analytics - sammenlign tag'et med snippet'en derinde.")
        henvisere = [{"fra": (r.get("dimensions") or {}).get("refererHost") or "direkte",
                      "besoeg": (r.get("sum") or {}).get("visits", 0)}
                     for r in d.get("henvisere") or []]
        # Læg AI-chatterne sammen pr. tjeneste: to værter kan pege på det samme
        # (chatgpt.com og chat.openai.com), og delt op ligner det ingenting.
        pr_chat: dict[str, int] = {}
        for h in henvisere:
            navn = _ai_chat_navn(h["fra"])
            if navn:
                pr_chat[navn] = pr_chat.get(navn, 0) + h["besoeg"]
        ai_chats = sorted(({"navn": n, "besoeg": b} for n, b in pr_chat.items()),
                          key=lambda a: -a["besoeg"])
        # Artikelsiderne med rubrik og kategori på, så panelet kan vise, HVILKE
        # nyheder der blev læst - ikke en liste af hashede filnavne. Kartoteket
        # kommer udefra: det er allerede læst én gang, og de 110 filer skal
        # ikke åbnes to gange pr. kørsel.
        pr_sti = _hent_sidehenvisere(token, d.get("accountTag") or konto,
                                     LAESERTAL_DAGE)
        artikler = []
        for s in sider:
            if not s["sti"].startswith("/artikel/"):
                continue
            k = kartotek.get(s["sti"], {})
            artikler.append({
                "sti": s["sti"], "besoeg": s["besoeg"], "visninger": s["visninger"],
                "rubrik": k.get("rubrik") or s["sti"].rsplit("/", 1)[-1],
                "kategori": k.get("kategori", ""), "dato": k.get("dato", ""),
                "henvisere": pr_sti.get(s["sti"], []),
            })
        artikler.sort(key=lambda a: (-a["visninger"], -a["besoeg"]))
        # Samme opdeling for de faste sider, så man også kan klikke ind på dem
        sidehenvisere = {s["sti"]: pr_sti.get(s["sti"], []) for s in sider}
        # Hvilke temaer bliver rent faktisk LÆST. Tomt i begyndelsen, fordi
        # artikeltrafikken skal komme først - og det er i sig selv svaret.
        pr_tema: dict[str, int] = {}
        for a in artikler:
            if a["kategori"]:
                pr_tema[a["kategori"]] = pr_tema.get(a["kategori"], 0) + a["visninger"]
        laeste_temaer = sorted(({"navn": k, "visninger": v} for k, v in pr_tema.items()),
                               key=lambda t: -t["visninger"])
        tal = {
            "opdateret": nu.isoformat(),
            "dage": LAESERTAL_DAGE,
            "besoeg_i_alt": sum(s["besoeg"] for s in sider),
            "sidevisninger_i_alt": sum(s["visninger"] for s in sider),
            "sider": sider,
            "henvisere": henvisere,
            "ai_chats": ai_chats,
            "ai_chat_besoeg": sum(a["besoeg"] for a in ai_chats),
            "faste_uden_besoeg": _faste_uden_besoeg(sider),
            "serie_dage": LAESERTAL_SERIE_DAGE,
            "serie": _hent_dagsserie(token, d.get("accountTag") or konto,
                                     LAESERTAL_SERIE_DAGE),
            "artikler": artikler,
            "laeste_temaer": laeste_temaer,
            "sidehenvisere": sidehenvisere,
        }
        print(f"📈 Læsertal: {tal['besoeg_i_alt']} besøg på "
              f"{len(sider)} sider de seneste {LAESERTAL_DAGE} dage"
              + (f" · {tal['ai_chat_besoeg']} fra AI-chats" if ai_chats else ""))
        return tal
    except Exception as fejl:
        print(f"📈 Læsertal sprang over ({type(fejl).__name__}: {fejl})")
        return None


def _laeser_afsnit() -> dict:
    """Læsertallene sat op, så en model kan se hvad der IKKE bliver læst -
    det er som regel det interessante."""
    tal = None
    if LAESERTAL_FIL.exists():
        try:
            tal = json.loads(LAESERTAL_FIL.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    if not tal or not tal.get("sider"):
        return {"status": "ingen læsertal - CLOUDFLARE_API_TOKEN er ikke sat"}

    besoegt = {s["sti"].rstrip("/") or "/": s["besoeg"] for s in tal["sider"]}
    artikelbesoeg = sum(v for k, v in besoegt.items() if k.startswith("/artikel"))
    videobesoeg = sum(v for k, v in besoegt.items() if k.startswith("/video"))
    return {
        "periode_dage": tal.get("dage"),
        "besoeg_i_alt": tal.get("besoeg_i_alt"),
        "sidevisninger_i_alt": tal.get("sidevisninger_i_alt"),
        "mest_laeste": [f'{s["sti"]} ({s["besoeg"]})' for s in tal["sider"][:10]],
        # Gamle filer fra før feltet fandtes har det ikke - så regn det ud.
        "faste_sider_uden_besoeg": (tal.get("faste_uden_besoeg")
                                    if "faste_uden_besoeg" in tal
                                    else _faste_uden_besoeg(tal["sider"])),
        "besoeg_paa_artikelsider": artikelbesoeg,
        "besoeg_paa_videosider": videobesoeg,
        "kommer_fra": [f'{h["fra"]} ({h["besoeg"]})' for h in tal.get("henvisere", [])[:8]],
        "fra_ai_chats": ([f'{a["navn"]} ({a["besoeg"]})' for a in tal.get("ai_chats", [])]
                         or "ingen besøg fra AI-chats i perioden"),
    }


# ----- Den natlige gennemgang ("redaktionens øjne") --------------------------
#
# Én gang i døgnet standser crawleren op og ser på sit eget arbejde med
# redaktionens målestok i hånden (_redaktion/redaktionens-oejne.md). Den ændrer
# ingenting - den skriver en prioriteret liste og åbner et GitHub-issue.

OEJNE_FIL = ROOT / "_redaktion" / "redaktionens-oejne.md"

# ----- Opslag på sociale platforme -------------------------------------------
#
# TØRKØRSEL ER STANDARD. Uden secret'en OPSLAG_LIVE=ja skriver crawleren kun
# udkastet i loggen og rører aldrig en platform. Det er med vilje: et opslag
# kan ikke trækkes tilbage, og et forkert et koster mere end et udeblevet.

OPSLAG_FIL = ROOT / "data" / "opslag.json"
OPSLAG_MAX_PR_DAG = 2        # loft, så en fejl aldrig bliver til spam
OPSLAG_MIN_PRIO = 7          # kun historier redaktionen selv ville fremhæve

SYSTEM_OPSLAG = """Du skriver opslag til sociale medier for ainyheder.com -
et dansk nyhedssite, der forklarer AI for helt almindelige mennesker.

Du får én historie (rubrik, resumé og "hvad betyder det for dig"). Skriv opslag,
der får en travl dansker til at standse op - uden clickbait og uden at love mere,
end historien holder.

Krav til alle varianter:
- Dansk, letlæst, konkret. Nævn virksomheden eller produktet ved navn.
- Ingen hashtag-tæpper, ingen "🚀 Wow!", ingen "Du vil ikke tro ...".
- Skriv aldrig at læseren SKAL noget. Fortæl hvad der er sket, og hvorfor det rager dem.
- Linket sættes på automatisk bagefter - skriv det ikke selv.

Svar KUN med JSON:
{"kort": "...", "facebook": "...", "linkedin": "..."}
- "kort": max 240 tegn (Bluesky). Én pointe, skarpt sat.
- "facebook": 2-4 linjer i hverdagssprog. Må slutte med et ægte spørgsmål.
- "linkedin": 3-5 linjer, saglig og fagligt nysgerrig tone, til folk der møder AI på jobbet."""


def _opslag_log() -> dict:
    if OPSLAG_FIL.exists():
        try:
            return json.loads(OPSLAG_FIL.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"sendt": [], "udkast": []}


def _opslag_dag() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Copenhagen")).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def _bluesky_post(tekst: str, url: str) -> None:
    """Bluesky: log ind med app-adgangskode og skriv ét indlæg med link."""
    bruger = os.environ.get("BLUESKY_BRUGER", "").strip()
    kode = os.environ.get("BLUESKY_KODE", "").strip()
    if not (bruger and kode):
        raise RuntimeError("BLUESKY_BRUGER/BLUESKY_KODE mangler")
    svar = json.loads(hent_url(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        data=json.dumps({"identifier": bruger, "password": kode}).encode(),
        headers={"content-type": "application/json"}))
    jwt, did = svar["accessJwt"], svar["did"]
    fuld = f"{tekst}\n\n{url}"
    b = fuld.encode("utf-8")
    start = b.find(url.encode("utf-8"))
    indlaeg = {
        "$type": "app.bsky.feed.post", "text": fuld,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "langs": ["da"],
        "facets": [{"index": {"byteStart": start, "byteEnd": start + len(url.encode())},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]}],
    }
    hent_url("https://bsky.social/xrpc/com.atproto.repo.createRecord",
             data=json.dumps({"repo": did, "collection": "app.bsky.feed.post",
                              "record": indlaeg}).encode(),
             headers={"content-type": "application/json",
                      "Authorization": f"Bearer {jwt}"})


def _facebook_post(tekst: str, url: str) -> None:
    """Facebook-side: kræver side-ID og et langtidsholdbart side-token."""
    side = os.environ.get("FACEBOOK_SIDE_ID", "").strip()
    token = os.environ.get("FACEBOOK_TOKEN", "").strip()
    if not (side and token):
        raise RuntimeError("FACEBOOK_SIDE_ID/FACEBOOK_TOKEN mangler")
    from urllib.parse import urlencode
    hent_url(f"https://graph.facebook.com/v21.0/{side}/feed",
             data=urlencode({"message": tekst, "link": url,
                             "access_token": token}).encode(),
             headers={"content-type": "application/x-www-form-urlencoded"})


def _linkedin_post(tekst: str, url: str) -> None:
    """LinkedIn-virksomhedsside: kræver organisations-ID og godkendt token."""
    org = os.environ.get("LINKEDIN_ORG_ID", "").strip()
    token = os.environ.get("LINKEDIN_TOKEN", "").strip()
    if not (org and token):
        raise RuntimeError("LINKEDIN_ORG_ID/LINKEDIN_TOKEN mangler")
    krop = {
        "author": f"urn:li:organization:{org}",
        "commentary": f"{tekst}\n\n{url}",
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED",
                         "targetEntities": [], "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    hent_url("https://api.linkedin.com/rest/posts",
             data=json.dumps(krop).encode(),
             headers={"Authorization": f"Bearer {token}",
                      "Content-Type": "application/json",
                      "LinkedIn-Version": "202601",
                      "X-Restli-Protocol-Version": "2.0.0"})


PLATFORME = [
    ("Bluesky",  "kort",     _bluesky_post,  ("BLUESKY_BRUGER", "BLUESKY_KODE")),
    ("Facebook", "facebook", _facebook_post, ("FACEBOOK_SIDE_ID", "FACEBOOK_TOKEN")),
    ("LinkedIn", "linkedin", _linkedin_post, ("LINKEDIN_ORG_ID", "LINKEDIN_TOKEN")),
]


def del_paa_platforme(artikler: list[dict]) -> None:
    """Vælger dagens bedste historie, får AI'en til at skrive opslag og deler
    dem - men KUN hvis OPSLAG_LIVE=ja. Ellers logges udkastet.
    Fejler altid stille: et mislykket opslag må aldrig vælte crawlet."""
    if not API_KEY:
        return
    try:
        log = _opslag_log()
        dag = _opslag_dag()
        sendt = log.get("sendt", [])
        i_dag = [s for s in sendt if s.get("dag") == dag]
        if len(i_dag) >= OPSLAG_MAX_PR_DAG:
            return
        delt = {s.get("link") for s in sendt}

        graense = (datetime.now(timezone.utc) - timedelta(hours=20)).isoformat()
        kandidater = [a for a in artikler
                      if a.get("rubrik") and a.get("betydning")
                      and not a.get("kun_aktuel")
                      and a["link"] not in delt
                      and (a.get("prio") or 0) >= OPSLAG_MIN_PRIO
                      and (a.get("foerst_set") or "") >= graense]
        if not kandidater:
            return
        a = max(kandidater, key=lambda x: (x.get("prio") or 0,
                                           len(x.get("andre") or [])))

        stof = {"rubrik": a["rubrik"], "resume": a.get("resume_da", ""),
                "betydning": a.get("betydning", "")}
        r = parse_json_objekt(hjerne_kald("opslag", SYSTEM_OPSLAG,
                                      json.dumps(stof, ensure_ascii=False), 700))
        tekster = {n: _som_tekst(r.get(n, "")).strip() for _, n, _, _ in PLATFORME}
        if not any(tekster.values()):
            return
        # Samme regel som feed, ugeside og nyhedsbrev: et opslag kan heller
        # ikke kaldes tilbage. Før pegede vi bare på forsiden, når artiklen
        # ingen side havde - nu på #a=, så læseren i det mindste lander i
        # historien, så længe den er på forsiden.
        url = _dele_link(a["link"])

        live = os.environ.get("OPSLAG_LIVE", "").strip().lower() in ("ja", "true", "1")
        resultat = []
        for navn, noegle, sender, kraev in PLATFORME:
            tekst = tekster.get(noegle) or tekster.get("kort") or ""
            if not tekst:
                continue
            if not all(os.environ.get(k, "").strip() for k in kraev):
                continue                          # platformen er ikke sat op endnu
            if not live:
                print(f"📣 [TØRKØRSEL] {navn}: {tekst[:110]}")
                resultat.append(navn + " (tørkørsel)")
                continue
            try:
                sender(tekst, url)
                print(f"📣 Delt på {navn}: {a['rubrik'][:60]}")
                resultat.append(navn)
            except Exception as fejl:
                print(f"📣 ⚠️ {navn} fejlede: {type(fejl).__name__}: {fejl}")

        if not live:
            log.setdefault("udkast", []).insert(
                0, {"dag": dag, "link": a["link"], "rubrik": a["rubrik"],
                    "url": url, "tekster": tekster})
            log["udkast"] = log["udkast"][:60]
            if not resultat:
                print(f"📣 [TØRKØRSEL] Udkast klar til: {a['rubrik'][:60]} "
                      "(ingen platform sat op endnu)")
        elif resultat:
            sendt.insert(0, {"dag": dag, "link": a["link"], "rubrik": a["rubrik"],
                             "platforme": resultat,
                             "tid": datetime.now(timezone.utc).isoformat()})
            log["sendt"] = sendt[:400]
        OPSLAG_FIL.parent.mkdir(exist_ok=True)
        OPSLAG_FIL.write_text(json.dumps(log, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    except Exception as fejl:
        print(f"📣 Opslag sprang over ({type(fejl).__name__}: {fejl})")


def tjek_statisk_sitemap() -> list[str]:
    """Siger til, hvis sitemap.xml er faldet bagud for filerne i roden.

    sitemap.xml vedligeholdes i hånden (i modsætning til sitemap-artikler.xml
    og sitemap-videoer.xml, som skrives her i filen). Derfor falder den bagud,
    hver gang der kommer en ny side til - og ingen opdager det, fordi
    ingenting går i stykker. Det skete med undervisning.html: 6.232 tegn
    færdig side, som hverken var linket eller stod i sitemappet, altså
    usynlig for Google i dagevis.

    Skriver ikke noget. Retter ikke noget. Returnerer listen af klager, så
    den kan testes, og printer dem, så de står i Actions-loggen.
    """
    klager: list[str] = []
    try:
        sti = ROOT / "sitemap.xml"
        if not sti.exists():
            print("🗺️  sitemap.xml findes ikke")
            return ["sitemap.xml findes ikke"]
        xml = sti.read_text(encoding="utf-8")
        # Kommentarer ud først, så en side nævnt i en forklaring ikke tæller med
        uden_kommentar = re.sub(r"<!--.*?-->", "", xml, flags=re.S)
        i_sitemap = set()
        for adresse in re.findall(r"<loc>(.*?)</loc>", uden_kommentar):
            navn = adresse.rstrip("/").rsplit("/", 1)[-1]
            i_sitemap.add(navn if navn.endswith(".html") else "index.html")

        for fil in sorted(ROOT.glob("*.html")):
            if fil.name == "404.html":          # fejlside, aldrig i et sitemap
                continue
            tekst = fil.read_text(encoding="utf-8", errors="ignore")
            noindex = "noindex" in tekst.lower()
            staar = fil.name in i_sitemap
            if noindex and staar:
                klager.append(f"{fil.name} siger noindex, men står i sitemap.xml")
            elif not noindex and not staar:
                klager.append(f"{fil.name} mangler i sitemap.xml")

        for navn in sorted(i_sitemap):
            if not (ROOT / navn).exists():
                klager.append(f"sitemap.xml peger på {navn}, som ikke findes")

        if klager:
            print(f"🗺️  sitemap.xml passer ikke med filerne ({len(klager)}):")
            for k in klager:
                print(f"    - {k}")
        else:
            print(f"🗺️  sitemap.xml passer: {len(i_sitemap)} sider, ingen glemte")
    except Exception as fejl:
        # Må aldrig vælte et crawl for en oprydningsdetalje
        print(f"🗺️  Sitemap-tjekket sprang over ({type(fejl).__name__}: {fejl})")
    return klager


def main() -> None:
    # Skriv ALTID hvilken model der skriver teksten - så det kan ses i
    # Actions-loggen, uden at gætte ud fra hvilke nøgler der er sat.
    if not API_KEY:
        print("🤖 Tekstmodel: INGEN (ingen API-nøgle) - artiklerne forbliver på engelsk")
    elif UDBYDER == "deepseek":
        print(f"🤖 Tekstmodel: DeepSeek · {DEEPSEEK_MODEL} (tænkning slået fra)")
    else:
        print(f"🤖 Tekstmodel: Gemini · {GEMINI_MODEL} (falder tilbage til {GEMINI_FALLBACK} hvis afvist)")
    if GEMINI_KEY:
        print(f"🎨 Billedmodel: {BILLED_MODEL}")
    egne = [n for n in HJERNE_BESKRIVELSE
            if hjerne_model(n) or (_hjerner().get(n) or {}).get("prompt")]
    if egne:
        print(f"🧠 Overstyret i kontrolpanelet: {', '.join(egne)}")
    skriv_hjerne_status()
    print()

    feeds = json.loads(FEEDS_FIL.read_text(encoding="utf-8"))["feeds"]
    print(f"Crawler {len(feeds)} feeds …\n")

    alle: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [pool.submit(crawl_feed, feed) for feed in feeds]
        for job in as_completed(jobs):
            feed, artikler, fejl = job.result()
            print(f"  {'⚠️ ' if fejl else '✅'} {feed['navn']}: "
                  f"{fejl if fejl else str(len(artikler)) + ' artikler'}")
            alle.extend(artikler)

    # Dubletter væk (samme link)
    set_links: set[str] = set()
    unikke = []
    for a in alle:
        if a["link"] in set_links:
            continue
        set_links.add(a["link"])
        unikke.append(a)

    # For gamle væk + nyeste først
    nu = datetime.now(timezone.utc)
    unikke = [a for a in unikke
              if a["dato"] is None or (nu - a["dato"]).days <= MAX_DAGE_GAMMEL]
    unikke.sort(key=lambda a: a["dato"] or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True)

    # Cache af tidligere omskrivninger (nøgle = link)
    cache: dict = {}
    foerst_set_gammel: dict = {}
    # `eget_foerst_set` hentes HER og ikke gennem `cache`. Cachen kræver en
    # `rubrik`, og den port er en anden end den, `foerst_set` går igennem: én
    # kørsel uden AI-nøgle giver artikler uden rubrik, og så ville feltet
    # forsvinde permanent for alt, der blev født den dag — uden at nogen kunne
    # se det. De to tal hører sammen og skal læses samme sted.
    eget_gammel: dict = {}
    if OUTPUT_FIL.exists():
        try:
            for a in json.loads(OUTPUT_FIL.read_text(encoding="utf-8"))["artikler"]:
                if a.get("foerst_set") or a.get("dato"):
                    foerst_set_gammel[a["link"]] = a.get("foerst_set") or a.get("dato")
                if a.get("eget_foerst_set"):
                    eget_gammel[a["link"]] = a["eget_foerst_set"]
                if a.get("rubrik"):
                    cache[a["link"]] = {"rubrik": a["rubrik"],
                                        "resume_da": a.get("resume_da", ""),
                                        "brief": a.get("brief", ""),
                                        "sektioner": a.get("sektioner", []),
                                        "noegletal": a.get("noegletal"),
                                        "figurer": a.get("figurer"),
                                        "andre": a.get("andre"),
                                        "detaljer": a.get("detaljer", []),
                                        "betydning": a.get("betydning", ""),
                                        "pointer": a.get("pointer", []),
                                        "billedmotiv": a.get("billedmotiv", ""),
                                        "billede": a.get("billede", ""),
                                        # Uden de to her overlever "hvad var
                                        # vinderens eget" ikke natten: cachen
                                        # er en hvidliste, og alt udenfor
                                        # findes ikke i morgen.
                                        "laant_billede": a.get("laant_billede"),
                                        "kategori": a.get("kategori", ""),
                                        "kat_ai": a.get("kat_ai", False),
                                        "navngivet": a.get("navngivet", False),
                                        "prio": a.get("prio")}
        except (json.JSONDecodeError, KeyError):
            pass

    # "Først set": hvornår crawleren så artiklen første gang. Der sorteres efter
    # dette i stedet for kildens udgivelsestid, så nyopdagede artikler altid
    # lander øverst - i stedet for at flette sig ind langt nede i listen.
    # Se `_saet_foerst_set` for hvorfor `eget_foerst_set` sættes netop her.
    _saet_foerst_set(unikke, foerst_set_gammel, nu, eget_gammel)
    unikke.sort(key=lambda a: (a["foerst_set"],
                               a["dato"].isoformat() if a["dato"] else ""),
                reverse=True)

    print()
    # Kategorien "Benchmarks" er nedlagt - gamle artikler flyttes til Lanceringer.
    # Og alt fra arXiv ER forskning, uanset hvad AI-kategoriseringen siger.
    for a in unikke:
        if a.get("kategori") == "Benchmarks":
            a["kategori"] = "Lanceringer"
        if "arxiv" in a.get("kilde", "").lower():
            a["kategori"] = "Forskning"

    omskriv_nye(unikke, cache)
    klassificer(unikke)
    for a in unikke:                         # arXiv-reglen igen EFTER klassificering
        if "arxiv" in a.get("kilde", "").lower():
            a["kategori"] = "Forskning"
    unikke = saml_dublet_historier(unikke)
    dybe_briefs(unikke)
    navngiv_rubrikker(unikke)   # sætter navn på gamle, anonyme overskrifter i klumper
    stram_betydninger(unikke)   # skriver gamle, for lange betydninger om i klumper
    udfyld_billedmotiver(unikke)
    # Glem billeder, hvis fil ikke er der længere, FØR vi prøver at lave nye.
    # "billede" bliver båret videre af cachen (nøgle = link), så en artikel, der
    # forsvandt ud af feedet én kørsel og kom tilbage den næste, kunne stå med
    # en sti til en fil, oprydningen havde slettet imens. Så viste forsiden et
    # brudt billede i stedet for at falde tilbage på den tegnede grafik.
    # Ryddes feltet, kan billedet laves igen ad den normale vej.
    glemt = 0
    for a in unikke:
        if a.get("billede") and not (ROOT / a["billede"]).is_file():
            a["billede"] = ""
            glemt += 1
    if glemt:
        print(f"🖼️  Glemte {glemt} billedstier, hvis fil var væk")
    lav_billeder(unikke)

    # "kunstig intelligens" -> "AI" i alle tekster (også gamle, cachede)
    def kort_ai(t: str) -> str:
        t = re.sub(r"[Dd]en kunstige intelligens", "AI'en", t)
        t = re.sub(r"[Kk]unstige intelligenser", "AI'er", t)
        t = re.sub(r"[Kk]unstig(?:e)? intelligens", "AI", t)
        return t
    for a in unikke:
        for felt in ("rubrik", "resume_da", "brief", "betydning"):
            if a.get(felt):
                a[felt] = kort_ai(a[felt])
        for felt in ("pointer", "detaljer"):
            if a.get(felt):
                # _som_tekst reparerer også gamle cachede punkter, der ligger som dict-tekst
                a[felt] = [kort_ai(_som_tekst(p)) for p in a[felt] if _som_tekst(p)]
        if a.get("sektioner"):
            for sek in a["sektioner"]:
                sek["overskrift"] = kort_ai(sek["overskrift"])
                sek["tekst"] = kort_ai(sek["tekst"])
        if a.get("noegletal"):
            for n in a["noegletal"]:
                n["label"] = kort_ai(n["label"])
        if a.get("figurer"):
            for f in a["figurer"]:
                f["tekst"] = kort_ai(f["tekst"])

    for a in unikke:
        a["dato"] = a["dato"].isoformat() if a["dato"] else None

    lav_artikelsider(unikke)   # statiske SEO-sider + "side"-felt til delelinks

    resultat = {
        "opdateret": nu.isoformat(),
        "antal": len(unikke),
        "artikler": unikke,
    }
    OUTPUT_FIL.parent.mkdir(exist_ok=True)
    OUTPUT_FIL.write_text(json.dumps(resultat, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    omskrevet = sum(1 for a in unikke if a.get("rubrik"))
    print(f"\n💾 Gemte {len(unikke)} artikler ({omskrevet} på dansk) i "
          f"{OUTPUT_FIL.relative_to(ROOT)}")
    lav_rss(unikke)
    lav_ugens_overblik(unikke)
    lav_dagens_prompt()
    lav_ugens_quiz(unikke)
    lav_dagens_brief(unikke)
    del_paa_platforme(unikke)  # tørkørsel indtil OPSLAG_LIVE=ja
    hent_laesertal()           # så gennemgangen kan se, hvad folk faktisk læser
    try:
        lav_youtube()          # må aldrig vælte nyhedscrawlet
    except Exception as fejl:
        print(f"📺 YouTube-delen sprang over ({type(fejl).__name__}: {fejl})")
    tjek_statisk_sitemap()     # siger til, hvis en ny side er glemt i sitemap.xml


if __name__ == "__main__":
    main()
