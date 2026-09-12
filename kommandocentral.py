"""Lille, offentlig statuspakke til Indstillinger.html — også via file://.

Læser kun de udtrykkeligt nævnte konfigurations- og statusfiler. Importerer
ikke crawleren, læser ikke miljøvariabler og foretager ingen netværkskald.
Kør manuelt med: python3 kommandocentral.py
"""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re


_HEMMELIGT_FELT = re.compile(
    r"(?:api[_-]?key|token|secret|password|passwd|authorization|api[_-]?noegle)",
    re.IGNORECASE,
)


def _offentligt(data):
    """Bevar konfigurationens udvidelser, men aldrig credential-felter."""
    if isinstance(data, dict):
        return {k: _offentligt(v) for k, v in data.items()
                if not _HEMMELIGT_FELT.search(str(k))}
    if isinstance(data, list):
        return [_offentligt(v) for v in data]
    return data


def _felter(data, navne):
    if not isinstance(data, dict):
        return {}
    return {k: data[k] for k in navne if k in data}


def _liste(data, loft):
    return data[:loft] if isinstance(data, list) else []


def _artikel(a, root):
    kort = _felter(a, ("titel", "rubrik", "link", "side", "kategori", "kilde", "dato"))
    # Et gemt filnavn er ikke i sig selv bevis på, at billedet findes.
    billede = a.get("billede")
    kort["billede"] = ""
    if isinstance(billede, str) and billede:
        try:
            sti = (root / billede.lstrip("/")).resolve()
            if sti.is_relative_to(root.resolve()) and sti.is_file():
                kort["billede"] = billede
        except (OSError, ValueError):
            pass
    return kort


def _artikelstatus(data, root):
    artikler = [a for a in _liste(data.get("artikler"), 10000) if isinstance(a, dict)]
    indeks = {a.get("link"): a for a in artikler if a.get("link")}
    plan = data.get("forside")
    plan = plan if isinstance(plan, dict) else {}
    udvalgte, set_links = [], set()
    # Følg den udgivne forsideplan. Opfind ikke et redaktionelt udvalg,
    # hvis en gammel eller manglende datafil ikke har en plan.
    for link in _liste(plan.get("udvalgte"), 12):
        if isinstance(link, str) and link in indeks and link not in set_links:
            udvalgte.append(_artikel(indeks[link], root))
            set_links.add(link)
    kort = [_artikel(a, root) for a in artikler]
    seneste = sorted(
        artikler, key=lambda a: str(a.get("eget_foerst_set") or a.get("foerst_set")
                                  or a.get("dato") or ""), reverse=True,
    )[:12]
    return {
        "opdateret": data.get("opdateret"),
        "antal": len(artikler),
        "med_billede": sum(bool(a["billede"]) for a in kort),
        "paa_dansk": sum(bool(a.get("rubrik")) for a in artikler),
        "kategorier": dict(Counter(str(a.get("kategori") or "Ukendt") for a in artikler)),
        "kilder": dict(Counter(str(a.get("kilde") or "Ukendt") for a in artikler)),
        "udvalgte": udvalgte,
        "seneste": [_artikel(a, root) for a in seneste],
    }


def _hjernerstatus(data):
    status = _felter(data, ("opdateret", "daglig_model", "udbyder", "billedmodel", "billed_standard", "forside_standard", "billed_standard_prompt",
                           "gemini_tilgaengelig", "deepseek_tilgaengelig", "cloudflare_tilgaengelig"))
    hjerner = data.get("hjerner")
    status["hjerner"] = {
        k: _felter(v, ("beskrivelse", "model", "udbyder", "egen_model", "egen_prompt",
                       "standard_prompt", "aktiv_prompt"))
        for k, v in (hjerner.items() if isinstance(hjerner, dict) else [])
        if isinstance(v, dict)
    }
    return status


def _redaktoerstatus(data):
    status = _felter(data, ("opdateret", "status", "model", "forklaring", "modelkald",
                           "kildehentninger"))
    for navn in ("regelbaseret_udvalg", "udgivet_udvalg"):
        status[navn] = _liste(data.get(navn), 12)
    status["vaerktoejer"] = [
        _felter(v, ("vaerktoej", "fejl"))
        for v in _liste(data.get("vaerktoejer"), 40) if isinstance(v, dict)
    ]
    status["kildegrundlag"] = [
        _felter(v, ("link", "grundlag"))
        for v in _liste(data.get("kildegrundlag"), 20) if isinstance(v, dict)
    ]
    return status


def _kildestatus(data):
    status = _felter(data, ("opdateret", "artikler_i_alt"))
    status["kilder"] = []
    for kilde in _liste(data.get("kilder"), 200):
        if not isinstance(kilde, dict):
            continue
        kort = _felter(kilde, ("navn", "url", "kategori", "kun_aktuel", "max", "aktiv",
                               "status", "fejl", "hentet", "i_listen", "som_ekstra"))
        kort["seneste"] = [
            _felter(a, ("rubrik", "dato", "foerst_set", "link", "side", "hvor", "under"))
            for a in _liste(kilde.get("seneste"), 12) if isinstance(a, dict)
        ]
        status["kilder"].append(kort)
    return status


def _laeserstatus(data):
    status = _felter(data, ("opdateret", "dage", "serie_dage", "maaling",
                           "besoeg_i_alt", "sidevisninger_i_alt", "ai_chat_besoeg"))
    for navn, felter, loft in (
        ("serie", ("dato", "besoeg", "visninger"), 30),
        ("sider", ("sti", "besoeg", "visninger"), 10),
        ("artikler", ("sti", "besoeg", "visninger", "rubrik", "kategori", "dato"), 10),
        ("henvisere", ("fra", "besoeg"), 10),
        ("laeste_temaer", ("navn", "visninger"), 10),
    ):
        poster = data.get(navn)
        poster = poster[-loft:] if navn == "serie" and isinstance(poster, list) else _liste(poster, loft)
        status[navn] = [_felter(v, felter) for v in poster
                        if isinstance(v, dict)]
    return status


def skriv_kommando_data(root):
    """Skriv et snapshot af eksisterende filer; returnér stien til JS-filen.

    `genereret` er pakkens tidspunkt, ikke tidspunktet for seneste crawl.
    Sektionernes `opdateret` kommer uændret fra de oprindelige statusfiler.
    Manglende/ødelagte kilder bliver markeret, aldrig præsenteret som succes.
    """
    root = Path(root)
    tilgaengelige, fejl = {}, []

    def laes(noegle, fil, standard, felt=None, felttype=None):
        tilgaengelige[noegle] = False
        try:
            tekst = (root / fil).read_text(encoding="utf-8")
            data = json.loads(tekst) if fil.endswith(".json") else tekst
            if not isinstance(data, type(standard)):
                raise ValueError("Forkert datatype")
            if felt is not None and not isinstance(data.get(felt), felttype):
                raise ValueError("Forkert indhold")
            tilgaengelige[noegle] = True
            return data
        except FileNotFoundError:
            fejl.append({"fil": fil, "grund": "Filen mangler"})
        except (OSError, UnicodeError, ValueError):
            # Ingen rå exceptiontekst: den kan indeholde filindhold.
            fejl.append({"fil": fil, "grund": "Filen kunne ikke læses"})
        return standard

    feeds = laes("feeds", "opsaetning/feeds.json", {}, "feeds", list)
    hjerner = laes("hjerner", "_redaktion/hjerner.json", {}, "hjerner", dict)
    instruks = laes("redaktoer", "opsaetning/redaktoer.md", "")
    artikler = laes("artikler", "data/articles.json", {}, "artikler", list)
    redaktoer = laes("redaktoer_status", "data/redaktoer-status.json", {})
    hjerne_status = laes("hjerner_status", "data/hjerner-status.json", {})
    kilder = laes("kilder", "data/kilder.json", {})
    laesertal = laes("laesertal", "data/laesertal.json", {})
    data = _offentligt({
        "version": 1,
        "genereret": datetime.now(timezone.utc).isoformat(),
        "tilgaengelige": tilgaengelige,
        "fejl": fejl,
        "feeds_fil": feeds if isinstance(feeds.get("feeds"), list) else {"feeds": []},
        "hjerner_fil": hjerner if isinstance(hjerner.get("hjerner"), dict) else {"hjerner": {}},
        "redaktoer_instruks": instruks,
        "artikler": _artikelstatus(artikler, root),
        "redaktoer_status": _redaktoerstatus(redaktoer),
        "hjerner_status": _hjernerstatus(hjerne_status),
        "modelkatalog": laes("modelkatalog", "data/modeller.json", {}),
        "kilder": _kildestatus(kilder),
        "laesertal": _laeserstatus(laesertal),
    })
    # Beskyt både almindelig script src og en eventuel senere inlineudgave.
    # Tegnene bliver gendannet af JS/JSON-parseren, så redigering er tabsfri.
    tekst = json.dumps(data, ensure_ascii=False, indent=1, allow_nan=False)
    for tegn, escape in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                         ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        tekst = tekst.replace(tegn, escape)
    ud = root / "data" / "kommando-data.js"
    ud.parent.mkdir(parents=True, exist_ok=True)
    midl = ud.with_suffix(".js.tmp")
    midl.write_text("window.KOMMANDO_DATA = " + tekst + ";\n", encoding="utf-8")
    midl.replace(ud)
    return ud


if __name__ == "__main__":
    print(skriv_kommando_data(Path(__file__).resolve().parent))
