#!/usr/bin/env python3
"""Prøve: virker kilde-kontakten, og er tallene til panelet de rigtige?

Kør den fra repoets rod:  python3 _redaktion/proeve-kilder.py

Læser `crawler.py`, `opsaetning/feeds.json` og `data/articles.json`, men
SKRIVER kun i en midlertidig mappe. Rører hverken `data/` eller `opsaetning/`.
Sæt PROEVE_REPO for at køre den mod en anden udgave (fx en kopi af HEAD).
"""
import datetime as _dt
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(os.environ.get("PROEVE_REPO", Path(__file__).resolve().parent.parent))
spec = importlib.util.spec_from_file_location("c", REPO / "crawler.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

UTC = _dt.timezone.utc
NU = _dt.datetime(2026, 7, 28, 16, 0, tzinfo=UTC)
groen = roed = 0


def ok(navn, betingelse, ekstra=""):
    global groen, roed
    if betingelse:
        groen += 1
    else:
        roed += 1
        print(f"  ROED  {navn} {ekstra}")


def kald(navn, *a, **kw):
    f = getattr(c, navn, None)
    return f(*a, **kw) if f else None


print("== A. kontakten: hvad bliver hentet, og hvad er slået fra ==")
alle = [
    {"navn": "Med aktiv true", "url": "https://a.dk/1", "aktiv": True},
    {"navn": "Uden feltet", "url": "https://a.dk/2"},
    {"navn": "Slået fra", "url": "https://a.dk/3", "aktiv": False},
    {"navn": "Tekst-false", "url": "https://a.dk/4", "aktiv": "false"},
    {"navn": "Nul", "url": "https://a.dk/5", "aktiv": None},
    {"navn": "Tal", "url": "https://a.dk/6", "aktiv": 0},
]
res = kald("_aktive_feeds", alle)
ok("A0 funktionen findes", res is not None, "_aktive_feeds mangler i denne udgave")
if res:
    til, fra = res
    navne = [f["navn"] for f in til]
    ok("A1 kun den, der udtrykkeligt er slået fra, bliver væk",
       fra == ["Slået fra"], fra)
    ok("A2 en kilde uden feltet bliver hentet", "Uden feltet" in navne, navne)
    ok("A3 aktiv:true bliver hentet", "Med aktiv true" in navne)
    ok("A4 teksten \"false\" slukker IKKE — det skal være en rigtig false",
       "Tekst-false" in navne, navne)
    ok("A5 null slukker ikke", "Nul" in navne, navne)
    ok("A6 0 slukker ikke", "Tal" in navne, navne)
    ok("A7 fem tændte, én slukket", len(til) == 5 and len(fra) == 1, (len(til), len(fra)))
    ok("A8 en tom liste vælter ikke noget", kald("_aktive_feeds", []) == ([], []))
    ok("A9 vrøvl i listen vælter ikke noget",
       kald("_aktive_feeds", [None, "ikke en dict", {"navn": "N"}])[0][-1] == {"navn": "N"})

print("== B. tallene til panelet ==")
midl = Path(tempfile.mkdtemp(prefix="proeve-kilder-"))
try:
    c.KILDER_FIL = midl / "kilder.json"
    c.FEEDS_FIL = REPO / "opsaetning" / "feeds.json"
    feeds = json.loads((REPO / "opsaetning" / "feeds.json").read_text(encoding="utf-8"))["feeds"]
    arts = json.loads((REPO / "data" / "articles.json").read_text(encoding="utf-8"))["artikler"]
    resultat = {f["navn"]: {"status": "ok", "hentet": 5, "fejl": ""} for f in feeds}
    # Navnene var hårdkodede ("VentureBeat AI", "MIT Tech Review AI") — og
    # væltede med IndexError, da redaktionen ændrede kildelisten i panelet.
    # En prøve må ikke afhænge af, hvilke kilder avisen har i dag. Vi bruger en
    # kilde UDEN artikler på forsiden som nul-kilden, hvis en findes, ellers
    # den første; fejl-kilden er bare den sidste i listen.
    _paa_forsiden = {a.get("kilde") for a in arts}
    _uden = [f["navn"] for f in feeds if f["navn"] not in _paa_forsiden]
    NULKILDE = _uden[0] if _uden else feeds[0]["navn"]
    FEJLKILDE = feeds[-1]["navn"] if feeds[-1]["navn"] != NULKILDE else feeds[-2]["navn"]
    resultat[NULKILDE] = {"status": "ok", "hentet": 0, "fejl": ""}
    resultat[FEJLKILDE] = {"status": "fejl", "hentet": 0, "fejl": "HTTP 503"}
    kald("skriv_kilde_status", feeds, resultat, arts, NU)

    d = json.loads((midl / "kilder.json").read_text(encoding="utf-8"))
    ok("B1 filen har de felter, panelet læser",
       set(d) >= {"opdateret", "artikler_i_alt", "kilder", "feeds_fil"}, set(d))
    ok("B2 der er en række pr. kilde", len(d["kilder"]) == len(feeds), len(d["kilder"]))

    # Summen skal passe. Ellers er der en kilde, ingen kan se.
    sum_liste = sum(k["i_listen"] for k in d["kilder"])
    ok("B3 summen af 'på forsiden' er lig antallet af artikler",
       sum_liste == len(arts), f"{sum_liste} mod {len(arts)}")
    sum_ekstra = sum(k["som_ekstra"] for k in d["kilder"])
    # En kilde under sig selv tælles IKKE med: det er samme udgiver to gange om
    # samme historie, ikke to sider der skriver det samme.
    faktisk = sum(1 for a in arts for k in (a.get("andre") or [])
                  if k.get("kilde") and k["kilde"] != a.get("kilde"))
    selv = sum(1 for a in arts for k in (a.get("andre") or [])
               if k.get("kilde") and k["kilde"] == a.get("kilde"))
    print(f"     poster under en anden kilde: {faktisk} · under sig selv: {selv}")
    ok("B4 summen af 'som ekstra' passer med data",
       sum_ekstra == faktisk, f"{sum_ekstra} mod {faktisk}")
    ok("B4b der ER mindst ét selv-par, ellers prøver B4 ingen forskel", selv > 0, selv)

    vb = [k for k in d["kilder"] if k["navn"] == NULKILDE]
    ok("B5 en kilde uden artikler står med nul, ikke uden linje",
       vb and vb[0]["hentet"] == 0, vb and vb[0])
    mit = [k for k in d["kilder"] if k["navn"] == FEJLKILDE]
    ok("B6 en fejlende kilde bærer sin fejlbesked med",
       mit and mit[0]["status"] == "fejl" and "503" in mit[0]["fejl"], mit and mit[0])

    _egne = lambda k: [r for r in k["seneste"] if r["hvor"] != "under"]
    ok("B7 ingen kilde lægger mere end 12 EGNE rubrikker i filen",
       all(len(_egne(k)) <= 12 for k in d["kilder"]),
       max(len(_egne(k)) for k in d["kilder"]))
    ok("B8 og mindst én rammer loftet, ellers prøver tallet intet",
       any(len([r for r in k["seneste"] if r["hvor"] != "under"]) == 12
           for k in d["kilder"]))
    # Rækkefølgen SKAL være nyeste først. Uden den her overlever en mutation,
    # der vender sorteringen om, og panelet ville vise de ældste 12 under
    # overskriften "Seneste 12".
    skaev = []
    for k in d["kilder"]:
        egne = [r["foerst_set"] for r in k["seneste"] if r["hvor"] != "under" and r["foerst_set"]]
        if egne != sorted(egne, reverse=True):
            skaev.append(k["navn"])
    ok("B8b nyeste står først i hver kildes liste", not skaev, skaev)
    # Dubletterne må aldrig skæres væk af loftet — det er dem, listen findes for.
    mangler = [k["navn"] for k in d["kilder"]
               if k["som_ekstra"] > 0
               and not any(r["hvor"] == "under" for r in k["seneste"])]
    ok("B8c en kilde med 'som ekstra' har også dublet-linjer at folde ud",
       not mangler, mangler)
    selv = [k["navn"] for k in d["kilder"]
            for navn, _ in k["overlap"] if navn == k["navn"]]
    ok("B8d en kilde tæller ikke som overlappende med sig selv", not selv, selv)

    # Overlappet er symmetrisk: skriver A det samme som B, gælder det begge veje.
    par = {}
    for k in d["kilder"]:
        for navn, antal in k["overlap"]:
            par[(k["navn"], navn)] = antal
    skaeve = [(a, b) for (a, b), n in par.items() if par.get((b, a)) != n]
    ok("B9 overlappet peger begge veje", not skaeve, skaeve[:3])
    # Kun hvis begge kilder stadig ER i avisen — prøven må ikke kræve en
    # bestemt kildeliste for at kunne køre.
    _navne = {k["navn"] for k in d["kilder"]}
    if {"Version2", "Ingeniøren"} <= _navne:
        ok("B10 Version2 og Ingeniøren står som overlappende",
           par.get(("Version2", "Ingeniøren"), 0) > 0, sorted(par.items())[:4])
    else:
        ok("B10 (sprunget over: en af de to kilder er ikke i listen længere)", True)

    # Fold-ud-listen: en artikel, der lå under en anden, skal sige hvem.
    under = [r for k in d["kilder"] for r in k["seneste"] if r["hvor"] == "under"]
    ok("B11 der ER artikler, der lå under en anden — ellers prøver B12 intet",
       len(under) > 0, len(under))
    ok("B12 hver af dem navngiver den historie, de lå under",
       all(r["under"] for r in under), [r for r in under if not r["under"]][:2])
    ok("B13 og har en overskrift at vise — aldrig en tom linje",
       all(r["rubrik"] for r in under), [r for r in under if not r["rubrik"]][:2])
    # Poster fra før 28.07 har ingen gemt rubrik. Crawleren henter den fra den
    # frosne side; findes den ikke, skal der stå noget, en læser forstår.
    tomme = [r for r in under if r["rubrik"] == "(overskriften er ikke gemt)"]
    print(f"     poster uden gemt rubrik: {len(tomme)} af {len(under)}")
    ok("B13b og de siger det med ord i stedet for at være tomme",
       all(r["rubrik"].strip() for r in under))

    ok("B14 feeds.json er med i sin helhed, ikke bygget om",
       d["feeds_fil"] == json.loads((REPO / "opsaetning" / "feeds.json").read_text(encoding="utf-8")))

    js = (midl / "kilder-data.js").read_text(encoding="utf-8")
    ok("B15 JS-udgaven findes og sætter den rigtige variabel",
       js.startswith("window.KILDER_STATUS = "), js[:40])
    ok("B16 og indeholder det samme",
       json.loads(js.split("=", 1)[1].rstrip().rstrip(";")) == d)
    ok("B17 filen er under 100 kB", len(js) < 100000, len(js))

    print("== C. en kilde, der er slettet, forsvinder ikke i tavshed ==")
    # Fjern en kilde, der faktisk HAR artikler på forsiden — ellers prøver
    # C1 ingenting. Hårdkodet "TechCrunch AI" før; nu findes den måske ikke.
    _med_artikler = [f["navn"] for f in feeds if f["navn"] in _paa_forsiden]
    FJERNET = _med_artikler[0] if _med_artikler else feeds[0]["navn"]
    faerre = [f for f in feeds if f["navn"] != FJERNET]
    kald("skriv_kilde_status", faerre, {}, arts, NU)
    d2 = json.loads((midl / "kilder.json").read_text(encoding="utf-8"))
    tc = [k for k in d2["kilder"] if k["navn"] == FJERNET]
    ok("C1 den slettede kilde står stadig med sine artikler",
       len(tc) == 1 and tc[0]["i_listen"] > 0, tc)
    ok("C2 og er mærket som ikke længere i listen",
       tc and tc[0]["status"] == "ikke_i_listen", tc)
    ok("C3 summen passer stadig",
       sum(k["i_listen"] for k in d2["kilder"]) == len(arts))

    print("== D. vrøvl vælter ingenting ==")
    for daarlig in ([], [{"navn": "Uden url"}], [{"url": "uden navn"}], [{}]):
        try:
            kald("skriv_kilde_status", daarlig, {}, arts, NU)
            ok(f"D {str(daarlig)[:22]:24} klarede den", True)
        except Exception as e:
            ok(f"D {str(daarlig)[:22]:24} klarede den", False, f"{type(e).__name__}: {e}")
    try:
        kald("skriv_kilde_status", feeds, {}, [], NU)
        d3 = json.loads((midl / "kilder.json").read_text(encoding="utf-8"))
        ok("D5 en tom artikelliste giver nuller, ikke et brag",
           all(k["i_listen"] == 0 for k in d3["kilder"]))
    except Exception as e:
        ok("D5 en tom artikelliste giver nuller, ikke et brag", False, str(e))
finally:
    shutil.rmtree(midl, ignore_errors=True)

print()
print(f"GROENNE {groen} · ROEDE {roed}")
sys.exit(1 if roed else 0)
