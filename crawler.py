#!/usr/bin/env python3
"""
AI-nyheder - crawler + AI-omskrivning
===================================
1. Henter AI-nyheder fra RSS/Atom-feeds (feeds.json)
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
FEEDS_FIL = ROOT / "feeds.json"
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
- "resume": 1-2 KORTE sætninger på hverdagsdansk. Forklar hvad der er sket,
  og hvorfor det er interessant for almindelige mennesker. Max 30 ord i alt.
  Nævn også her hvem det handler om.
  Forbudt: engelske låneord der har et dansk ord, forkortelser uden forklaring,
  og buzzwords. Skriv som til en klog nabo.
- Skriv ALTID "AI" - aldrig "kunstig intelligens" (det er for langt).
- Er et fagudtryk uundgåeligt, så forklar det med tre-fire almindelige ord
  ("en sprogmodel - den slags AI, der skriver tekst").

Svar KUN med et JSON-array, ét objekt pr. artikel, i samme rækkefølge som input:
[{"rubrik": "...", "resume": "..."}, ...]"""


def kald_ai(system: str, bruger_tekst: str, max_tokens: int) -> str:
    """Ét fælles AI-kald - taler med Claude eller Gemini alt efter hvilken
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
        resultat = parse_json_svar(kald_ai(
            SYSTEM_PROMPT,
            "Omskriv disse artikler:\n" + json.dumps(input_liste, ensure_ascii=False),
            4000))
        if isinstance(resultat, list) and len(resultat) == len(artikler):
            return resultat
        print(f"  ⚠️  AI-svar havde forkert længde ({len(resultat)} vs {len(artikler)})")
    except Exception as fejl:  # API nede, kvote opbrugt, ugyldigt JSON osv.
        print(f"  ⚠️  AI-kald fejlede: {type(fejl).__name__}: {fejl}")
    return None


SYSTEM_BRIEF = """Du er journalist på et dansk nyhedssite for almindelige mennesker
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
              Hvert afsnit 40-70 ord letlæst hverdagsdansk:
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
4. BETYDNING: skal være konkret for almindelige danskere - ikke floskler som
   "AI ændrer vores hverdag".

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
        r = parse_json_objekt(kald_ai(
            SYSTEM_REDAKTOER, json.dumps(udkast, ensure_ascii=False), 400))
        if isinstance(r, dict) and "godkendt" in r:
            return r
    except Exception as fejl:
        print(f"  ⚠️  Redaktør-tjek fejlede: {type(fejl).__name__}: {fejl}")
    return None


def kald_ai_brief(a: dict, tekst: str, billeder: list[dict],
                  redaktoer_noter: str = "") -> dict | None:
    """Laver et komplet dansk brief ud fra artiklens fulde tekst."""
    try:
        er_forskning = "arxiv" in a.get("kilde", "").lower() or a.get("kategori") == "Forskning"
        er_vigtig = (a.get("prio") or 0) >= 8 or bool(a.get("andre"))
        sys_prompt = SYSTEM_BRIEF \
            + (SYSTEM_BRIEF_FORSKNING if er_forskning else "") \
            + (SYSTEM_BRIEF_LANG if er_vigtig and not er_forskning else "")
        bruger = f"KILDE: {a['kilde']}\nTITEL: {a['titel']}\n\nARTIKELTEKST:\n{tekst}"
        if redaktoer_noter:
            bruger += ("\n\nREDAKTØRENS NOTER TIL DIT FORRIGE UDKAST - "
                       f"RET PRÆCIS DISSE PROBLEMER:\n{redaktoer_noter}")
        r = parse_json_objekt(kald_ai(
            sys_prompt, bruger, 2200 if er_vigtig else 1500))
        if r.get("rubrik") and (r.get("sektioner") or r.get("brief")):
            return r
    except Exception as fejl:
        print(f"  ⚠️  Brief-kald fejlede ({a['kilde']}): {type(fejl).__name__}: {fejl}")
    return None


def dybe_briefs(artikler: list[dict]) -> None:
    """Giver de DYBDE_ANTAL nyeste artikler et komplet dansk brief:
    henter artikelsiden, udtrækker brødteksten og lader Claude genfortælle."""
    if GENKOER_FILTER:
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
            if dom is not None and not dom.get("godkendt", True) and dom.get("problemer"):
                noter = " · ".join(str(p) for p in dom["problemer"][:4])[:400]
                print(f"   ✏️  Redaktøren kræver omskrivning: {noter[:110]}")
                r2 = kald_ai_brief(a, tekst, billeder, redaktoer_noter=noter)
                if r2:
                    _anvend_brief(a, r2, billeder)
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
            svar = parse_json_svar(kald_ai(SYSTEM_KATEGORI,
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


def saml_dublet_historier(artikler: list[dict]) -> list[dict]:
    """Finder nyheder som flere medier dækker, beholder den bedste udgave og
    gemmer de øvrige som ekstra kilder på historien ("andre")."""
    # 0) håndhæv tidligere samlinger: artikler der allerede er registreret som
    #    ekstra kilde under en anden historie, skal blive væk
    kendte_dubletter = {k["link"] for a in artikler for k in a.get("andre", [])}
    artikler = [a for a in artikler if a["link"] not in kendte_dubletter]
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
            grupper = parse_json_svar(kald_ai(SYSTEM_DUBLET, liste, 1500))
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
        # behold den med mest indhold: brief > dansk rubrik > nyeste
        primaer = next((m for m in medlemmer if m.get("brief")), None) \
               or next((m for m in medlemmer if m.get("rubrik")), None) \
               or medlemmer[0]
        andre = [m for m in medlemmer if m is not primaer]
        primaer.setdefault("andre", [])
        har = {k["link"] for k in primaer["andre"]}
        primaer["andre"] += [{"kilde": m["kilde"], "link": m["link"]}
                             for m in andre if m["link"] not in har]
        fjern.update(m["link"] for m in andre)
        samlet += len(andre)
    if samlet:
        print(f"🔗 Samlede {samlet} dublet-artikler under deres hovedhistorier")
    return [a for a in artikler if a["link"] not in fjern]


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


def _kort_artikler(artikler: list[dict]) -> set:
    """Links på de artikler, der vises som BILLEDKORT på forsiden: de 5
    vigtigste pr. opdagelsesdag (hero + 4 kort). Resten vises som tekstlinjer
    og bruger sitets genererede kunst - dem koster vi ikke AI-billeder på."""
    dage: dict = {}
    for a in artikler:
        if not a.get("rubrik") or a.get("kun_aktuel"):
            continue
        noegle = str(a.get("foerst_set") or a.get("dato") or "")[:10]
        dage.setdefault(noegle, []).append(a)
    valgte: set = set()
    for gruppe in dage.values():
        gruppe = sorted(gruppe, key=lambda a: (a.get("prio") or 5), reverse=True)
        valgte.update(a["link"] for a in gruppe[:5])
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
            svar = parse_json_svar(kald_ai(
                SYSTEM_MOTIV, json.dumps(liste, ensure_ascii=False), 2000))
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

    # ryd op: slet billeder for artikler der er røget ud af listen
    brugte = {_billed_navn(a["link"]) for a in artikler}
    for fil in BILLED_MAPPE.glob("*.jpg"):
        if fil.name not in brugte:
            fil.unlink(missing_ok=True)


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
            if gammel.get("kat_ai") and gammel.get("kategori"):
                a["kategori"] = gammel["kategori"]
                a["kat_ai"] = True
            if gammel.get("prio") is not None:
                a["prio"] = gammel["prio"]

    # 2) håndlavede omskrivninger fra seeds_da.json (matcher på titel-prefix)
    seed_fil = ROOT / "seeds_da.json"
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
            print("  ⚠️  seeds_da.json kunne ikke læses - springer over")

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
# Ellers behandles kun artikler, der aldrig er behandlet.
_GENKOER_RAW = os.environ.get("GENKOER_ALT", "").strip()
GENKOER_ALT = _GENKOER_RAW.lower() in ("ja", "1", "true")
GENKOER_FILTER = "" if _GENKOER_RAW.lower() in ("", "ja", "1", "true", "nej", "no", "false")     else _GENKOER_RAW.lower()


# ----- RSS-feed af vores egne artikler ----------------------------------------

SITE_URL = "https://ainyheder.com"


def lav_rss(artikler: list[dict]) -> None:
    """Skriver feed.xml med de nyeste artikler, så man kan abonnere på sitet."""
    from email.utils import format_datetime
    from urllib.parse import quote
    punkter = []
    for a in artikler[:40]:
        if not a.get("rubrik"):
            continue
        led = f"{SITE_URL}/#a=" + quote(a["link"], safe="")
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
    from urllib.parse import quote
    TONE = {"Lanceringer": "#e7e3f7", "Hverdags-AI": "#e2eadd",
            "Penge & marked": "#f0e4c8", "Politik & jura": "#dde5ee",
            "Samfund & etik": "#f4e0d9", "Forskning": "#e2e7ee"}
    historier = d.get("historier", [])
    forside_billede = (historier[0].get("billede") or "assets/og.png") if historier else "assets/og.png"
    stats = d.get("stats", {})

    kort = []
    for nr, h in enumerate(historier, 1):
        led = f"{SITE_URL}/#a=" + quote(h.get("link", ""), safe="")
        tone = TONE.get(h.get("kategori", ""), "#efece4")
        billede = (f'<div class="k-billede"><img src="{html.escape(h.get("billede", ""))}" alt="" '
                   'loading="lazy" onerror="this.parentNode.remove()"></div>') if h.get("billede") else ""
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
<meta name="theme-color" content="#191714">
<meta property="og:title" content="Ugens AI-overblik: {html.escape(d.get("rubrik", ""))}">
<meta property="og:description" content="{html.escape(d.get("indledning", ""))[:150]}">
<meta property="og:image" content="{SITE_URL}/{html.escape(forside_billede)}">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/favicon-192.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800;9..144,900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
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
    from urllib.parse import quote
    dele = [d.get("indledning", ""), ""]
    for nr, h in enumerate(d.get("historier", []), 1):
        led = f"{SITE_URL}/#a=" + quote(h.get("link", ""), safe="")
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
            if not h.get("billede"):
                h["billede"] = b_af.get(h.get("link", ""), "")
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
        r = parse_json_objekt(kald_ai(SYSTEM_UGE, json.dumps(payload, ensure_ascii=False), 2500))
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


def _artikel_side_html(a: dict) -> str:
    rubrik = html.escape(a.get("rubrik") or a.get("titel", ""))
    resume = html.escape(a.get("resume_da") or a.get("resume") or "")
    slug = _artikel_slug(a["link"])
    url = f"{SITE_URL}/artikel/{slug}.html"
    billede = f"{SITE_URL}/{a['billede']}" if a.get("billede") else f"{SITE_URL}/assets/og.png"
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800;9..144,900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
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
{f'<img class="top" src="/{html.escape(a["billede"])}" alt="">' if a.get("billede") else ""}
{krop}
{detaljer}
{betydning}
<p style="margin-top:24px"><strong>Kilder:</strong><br>{kilder}</p>
<a class="cta" href="/">Læs dagens AI-nyheder på letlæst dansk →</a>
<p class="note">Genfortalt i egne ord af AI-nyheder.com · AI-genereret illustration · Tjek altid originalkilden, før du handler på vigtige oplysninger.</p>
</main>
<footer>© 2026 AI-nyheder · <a href="/om.html">Om os</a> · <a href="/laer.html">Lær AI</a></footer>
<!-- Cloudflare Web Analytics (privatlivsvenlig besøgsstatistik, ingen cookies) -->
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "fda17dd7ade34a579f4ec6d615265fa6"}}'></script>
</body>
</html>"""


def lav_artikelsider(artikler: list[dict]) -> None:
    """Skriver en statisk HTML-side pr. dansk artikel (SEO) + eget sitemap.
    Gamle sider slettes ikke - de bliver stående som evigt indhold."""
    ARTIKEL_MAPPE.mkdir(exist_ok=True)
    skrevet = 0
    poster = []
    for a in artikler:
        if not a.get("rubrik"):
            continue                        # kun danske genfortællinger
        if a.get("kun_aktuel"):
            continue                        # udgiveren tillader ikke et arkiv
        slug = _artikel_slug(a["link"])
        a["side"] = f"artikel/{slug}.html"
        sti = ARTIKEL_MAPPE / f"{slug}.html"
        indhold = _artikel_side_html(a)
        if not sti.exists() or sti.read_text(encoding="utf-8") != indhold:
            sti.write_text(indhold, encoding="utf-8")
            skrevet += 1
        poster.append((slug, (a.get("foerst_set") or "")[:10]))
    # eget sitemap for artikelsiderne (alle, også de historiske)
    alle_sider = sorted(ARTIKEL_MAPPE.glob("*.html"))
    linjer = "".join(
        f"  <url><loc>{SITE_URL}/artikel/{p.name}</loc></url>\n" for p in alle_sider)
    (ROOT / "sitemap-artikler.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{linjer}</urlset>\n", encoding="utf-8")
    print(f"🔎 Artikelsider: {skrevet} skrevet/opdateret, {len(alle_sider)} i alt")


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
    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": v.get("rubrik") or v.get("titel", ""),
        "description": v.get("resume_da") or "",
        "thumbnailUrl": v.get("thumb", ""),
        "uploadDate": dato,
        "duration": v.get("varighed") or None,
        "embedUrl": f"https://www.youtube.com/embed/{vid}",
        "url": url,
        "publisher": {"@type": "Organization", "name": "AI-nyheder",
                      "url": SITE_URL},
    }, ensure_ascii=False)

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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800;9..144,900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
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
  <img src="{thumb}" alt="" loading="lazy"><span><b>▶</b></span></a>
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
- tekst: selve prompten på dansk (2-6 sætninger) med [firkantede felter] til brugerens egne oplysninger. Konkret, umiddelbart brugbar og uden teknisk snak. Brug gerne stærke greb: giv AI'en en rolle, bed den stille opklarende spørgsmål først, kræv et bestemt format.
- hvorfor: én kort sætning om, hvad der gør prompten smart.
- VIGTIGT: Lav noget nyt - undgå emner og vinkler fra titellisten, du får. Aldrig medicinsk/juridisk rådgivning som facit (kun forberedelse til fagfolk)."""


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
        r = parse_json_objekt(kald_ai(
            SYSTEM_KARTOTEK,
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
        r = parse_json_svar(kald_ai(SYSTEM_STRAM, json.dumps(payload, ensure_ascii=False), 3000))
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
}

# Formuleringer, der skjuler hvem historien handler om
_VAGE_VENDINGER = (
    "kæmpe gigant", "en gigant", "stor gigant", "stort firma", "stort selskab",
    "et firma", "et selskab", "nyt selskab", "ny virksomhed", "stor virksomhed",
    "en kendt", "kendt firma", "kendt tjeneste", "stor spiller", "en stor spiller",
    "tech-firma", "techfirma", "tech-gigant", "techgigant", "et værktøj",
    "en tjeneste", "udvikler af", "en udbyder",
)


def _har_navn(rubrik: str) -> bool:
    """Sandt hvis rubrikken nævner mindst ét rigtigt navn (firma, produkt, land)."""
    ord_ = re.findall(r"[0-9A-Za-zÆØÅÉæøåé\-\.'’]+", rubrik or "")
    for i, o in enumerate(ord_):
        ren = o.strip("-.'’").lower()
        if not ren:
            continue
        if ren.split("-")[0] in _MAERKER or ren in _MAERKER:
            return True
        if len(re.sub(r"[^A-ZÆØÅ]", "", o)) >= 2 and o == o.upper() and ren != "ai":
            return True                       # USA, EU, IBM, GPT-5
        if re.search(r"[a-zæøå][A-ZÆØÅ]", o):
            return True                       # OpenAI, DeepSeek, iPhone
        if i > 0 and o[:1].isupper():
            return True                       # stort bogstav midt i en dansk sætning
    return False


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
rubrik og resumé. Skriv dem om, så virksomheden, produktet eller modellen nævnes
ved rigtigt navn - og BEVAR ellers det enkle, folkelige sprog.

Krav:
- "rubrik": max 9 ord, navnet med, intet punktum til sidst.
- "resume": 1-2 sætninger, max 30 ord, hverdagsdansk, navnet med.
- Skriv "AI", aldrig "kunstig intelligens".
- Opdigt ALDRIG navne eller tal. Står navnet ikke i materialet, så skriv i stedet
  konkret hvem det er ("Kinesisk techgigant ...", "EU-Kommissionen ...").
- Behold gerne folkelige billeder ("digital hjerne"), men sæt navnet foran:
  "Anthropics nye digitale hjerne ...".

Svar KUN med et JSON-array: [{"nr": 1, "rubrik": "...", "resume": "..."}, ...]"""


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
        payload = [{"nr": i + 1,
                    "engelsk_titel": a.get("titel", "")[:160],
                    "engelsk_resume": (a.get("resume") or "")[:250],
                    "dansk_rubrik": a["rubrik"],
                    "dansk_resume": (a.get("resume_da") or "")[:250]}
                   for i, a in enumerate(anonyme)]
        r = parse_json_svar(kald_ai(SYSTEM_NAVNGIV,
                                    json.dumps(payload, ensure_ascii=False), 3500))
        rettede = 0
        for p in r if isinstance(r, list) else []:
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
                a["navngivet"] = True         # AI'en kunne ikke finde et navn - lad den være
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
        r = parse_json_svar(kald_ai(SYSTEM_BRIEF, json.dumps(stof, ensure_ascii=False), 800))

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
- Spred spørgsmålene over forskellige historier."""


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

        r = parse_json_svar(kald_ai(SYSTEM_QUIZ, json.dumps(stof, ensure_ascii=False), 2000))
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

YT_FIL = ROOT / "youtube.json"
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
        r = parse_json_objekt(kald_ai(
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
        r = parse_json_objekt(kald_ai(SYSTEM_OPSLAG,
                                      json.dumps(stof, ensure_ascii=False), 700))
        tekster = {n: _som_tekst(r.get(n, "")).strip() for _, n, _, _ in PLATFORME}
        if not any(tekster.values()):
            return
        url = f"{SITE_URL}/{a['side']}" if a.get("side") else SITE_URL

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
    if OUTPUT_FIL.exists():
        try:
            for a in json.loads(OUTPUT_FIL.read_text(encoding="utf-8"))["artikler"]:
                if a.get("foerst_set") or a.get("dato"):
                    foerst_set_gammel[a["link"]] = a.get("foerst_set") or a.get("dato")
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
                                        "kategori": a.get("kategori", ""),
                                        "kat_ai": a.get("kat_ai", False),
                                        "navngivet": a.get("navngivet", False),
                                        "prio": a.get("prio")}
        except (json.JSONDecodeError, KeyError):
            pass

    # "Først set": hvornår crawleren så artiklen første gang. Der sorteres efter
    # dette i stedet for kildens udgivelsestid, så nyopdagede artikler altid
    # lander øverst - i stedet for at flette sig ind langt nede i listen.
    for a in unikke:
        a["foerst_set"] = foerst_set_gammel.get(a["link"]) or nu.isoformat()
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
    try:
        lav_youtube()          # må aldrig vælte nyhedscrawlet
    except Exception as fejl:
        print(f"📺 YouTube-delen sprang over ({type(fejl).__name__}: {fejl})")


if __name__ == "__main__":
    main()
