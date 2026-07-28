#!/usr/bin/env python3
"""Prøve: rykker `foerst_set` aldrig frem, og siger kortet det rigtige?

Kør den fra repoets rod:  python3 _redaktion/proeve-tid.py

Læser `crawler.py`, `data/articles.json` og `data/foerst_set.json`, men SKRIVER
kun i en midlertidig mappe. Rører hverken `data/`, `artikel/` eller `video/`.
Sæt PROEVE_REPO for at køre den mod en anden udgave (fx en kopi af HEAD).
"""
import copy
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
groen = roed = 0
fejl = []


def ok(navn, betingelse, ekstra=""):
    global groen, roed
    if betingelse:
        groen += 1
    else:
        roed += 1
        fejl.append(f"{navn} {ekstra}")
        print(f"  ROED  {navn} {ekstra}")


def kald(navn, *a, **kw):
    f = getattr(c, navn, None)
    return f(*a, **kw) if f else None


def saet(artikler, kendte=None, nu=None, eget=None, butik=None):
    """Kald _saet_foerst_set uanset hvor mange parametre udgaven har."""
    f = getattr(c, "_saet_foerst_set", None)
    if not f:
        return
    import inspect
    n = len(inspect.signature(f).parameters)
    args = [artikler, kendte or {}, nu or _dt.datetime(2026, 7, 28, 15, tzinfo=UTC),
            eget or {}, butik if butik is not None else {}]
    f(*args[:n])


NU = _dt.datetime(2026, 7, 28, 15, 0, tzinfo=UTC)

print("== A. foerst_set må ALDRIG rykke frem ==")
# Kernen i fejlen: artiklen falder ud af listen én kørsel og kommer tilbage.
# `kendte` (gårsdagens fil) kender den ikke længere — butikken gør.
butik = {"https://a.dk/1": "2026-07-23T14:45:00+00:00"}
a1 = {"link": "https://a.dk/1"}
saet([a1], kendte={}, nu=NU, eget={}, butik=butik)
ok("A1 den faldt ud af listen, men tiden holdt",
   a1.get("foerst_set") == "2026-07-23T14:45:00+00:00", a1.get("foerst_set"))
ok("A2 eget_foerst_set fulgte med",
   a1.get("eget_foerst_set") == "2026-07-23T14:45:00+00:00", a1.get("eget_foerst_set"))

# Selv hvis gårsdagens fil siger noget SENERE, vinder det tidligste.
a2 = {"link": "https://a.dk/2"}
saet([a2], kendte={"https://a.dk/2": "2026-07-27T18:05:00+00:00"}, nu=NU,
     eget={}, butik={"https://a.dk/2": "2026-07-23T14:45:00+00:00"})
ok("A3 et senere tidspunkt i filen kan ikke overskrive butikken",
   a2.get("foerst_set") == "2026-07-23T14:45:00+00:00", a2.get("foerst_set"))

# Og omvendt: er filen TIDLIGERE end butikken, vinder filen.
a3 = {"link": "https://a.dk/3"}
saet([a3], kendte={"https://a.dk/3": "2026-07-20T08:00:00+00:00"}, nu=NU,
     eget={}, butik={"https://a.dk/3": "2026-07-24T08:00:00+00:00"})
ok("A4 det tidligste vinder for foerst_set, uanset hvor det kommer fra",
   a3.get("foerst_set") == "2026-07-20T08:00:00+00:00", a3.get("foerst_set"))
ok("A4b men 'eget' kommer KUN fra butikken — gårsdagens fil kan være lånt",
   a3.get("eget_foerst_set") == "2026-07-24T08:00:00+00:00", a3.get("eget_foerst_set"))

# Den vigtigste vagt: en KENDT artikel uden noget eget tidspunkt nogen steder
# må ikke få `kendte` skrevet ind som sit eget. Værdien kan være lånt af en
# sammenlægning, og så ville en frigivelse give tiden tilbage til den forkerte
# dag for altid. Se `_rul_arven_tilbage`.
a5 = {"link": "https://a.dk/kendt-uden-eget"}
b5 = {}
saet([a5], kendte={"https://a.dk/kendt-uden-eget": "2026-07-23T20:37:00+00:00"},
     nu=NU, eget={}, butik=b5)
ok("A4c en kendt artikel uden eget tidspunkt får IKKE et gættet 'eget'",
   "eget_foerst_set" not in a5, a5)
ok("A4d og den kommer ikke i butikken på et gæt", b5 == {}, b5)
ok("A4e men dens foerst_set holder", a5.get("foerst_set") == "2026-07-23T20:37:00+00:00", a5)

# En helt ny artikel får nu.
a4 = {"link": "https://a.dk/ny"}
b4 = {}
saet([a4], kendte={}, nu=NU, eget={}, butik=b4)
ok("A5 en ægte ny artikel får nu", a4.get("foerst_set") == NU.isoformat(), a4.get("foerst_set"))
ok("A6 og bliver husket i butikken", b4.get("https://a.dk/ny") == NU.isoformat(), b4)

print("== A2. butikken kan hele sig selv, hvis den bærer noget for sent ==")
# Uden det her overlever `butik.setdefault(link, eget)` prøven — og så kan et
# for sent tal i butikken aldrig rettes af noget som helst.
b6 = {"https://a.dk/skaev": "2026-07-27T18:00:00+00:00"}
a6 = {"link": "https://a.dk/skaev"}
saet([a6], kendte={}, nu=NU, eget={"https://a.dk/skaev": "2026-07-23T09:00:00+00:00"}, butik=b6)
ok("A7 det tidligste af butik og fil vinder",
   a6.get("eget_foerst_set") == "2026-07-23T09:00:00+00:00", a6.get("eget_foerst_set"))
ok("A8 og butikken bliver RETTET, ikke bare ladt i fred",
   b6["https://a.dk/skaev"] == "2026-07-23T09:00:00+00:00", b6)

print("== A3. tidszoner: butikken skal være ren UTC, ellers lyver min() ==")
midl2 = Path(tempfile.mkdtemp(prefix="proeve-tz-"))
try:
    _gemt = getattr(c, "FOERST_SET_FIL", None)
    if _gemt is not None:
        c.FOERST_SET_FIL = midl2 / "f.json"
        (midl2 / "f.json").write_text(json.dumps({"tider": {
            "https://a.dk/arxiv": "2026-07-23T00:00:00-04:00",   # = 04:00 UTC
            "https://a.dk/utc":   "2026-07-23T02:00:00+00:00",
            "https://a.dk/vroevl": "ikke en dato"}}), encoding="utf-8")
        _b = kald("_laes_foerst_set_butik") or {}
        ok("A9 alt kommer ind som UTC",
           all(v.endswith("+00:00") for v in _b.values()), _b)
        ok("A10 og -04:00 er regnet om, ikke bare klippet",
           _b.get("https://a.dk/arxiv", "").startswith("2026-07-23T04:00"), _b.get("https://a.dk/arxiv"))
        ok("A11 så tekst-min giver det rigtige svar",
           min(_b["https://a.dk/arxiv"], _b["https://a.dk/utc"]) == _b["https://a.dk/utc"])
        ok("A12 vrøvl smides væk i stedet for at ryge med", "https://a.dk/vroevl" not in _b, _b)
        c.FOERST_SET_FIL = _gemt
finally:
    shutil.rmtree(midl2, ignore_errors=True)

print("== B. butikken læses og skrives, og den holder sig i skak ==")
midl = Path(tempfile.mkdtemp(prefix="proeve-tid-"))
try:
    gemt_fil = getattr(c, "FOERST_SET_FIL", None)
    if gemt_fil is not None:
        c.FOERST_SET_FIL = midl / "foerst_set.json"
        b = {"https://a.dk/gammel": (NU - _dt.timedelta(days=120)).isoformat(),
             "https://a.dk/frisk": (NU - _dt.timedelta(days=3)).isoformat()}
        kald("_skriv_foerst_set_butik", b, NU)
        igen = kald("_laes_foerst_set_butik")
        ok("B1 det friske link overlevede", "https://a.dk/frisk" in (igen or {}), igen)
        ok("B2 et link på 120 dage blev glemt", "https://a.dk/gammel" not in (igen or {}), igen)
        ok("B3 filen er gyldig JSON med de rigtige felter",
           set(json.loads((midl / "foerst_set.json").read_text(encoding="utf-8")))
           >= {"opdateret", "antal", "tider"})
        # vrøvl må ikke vælte noget
        (midl / "foerst_set.json").write_text("{ dette er ikke json", encoding="utf-8")
        ok("B4 en ulæselig fil giver en tom butik, ikke et brag",
           kald("_laes_foerst_set_butik") == {})
        (midl / "foerst_set.json").write_text('{"tider": "ikke en dict"}', encoding="utf-8")
        ok("B5 forkert form giver også en tom butik", kald("_laes_foerst_set_butik") == {})
        c.FOERST_SET_FIL = gemt_fil
    else:
        ok("B1 butikken findes", False, "FOERST_SET_FIL findes ikke i denne udgave")
finally:
    shutil.rmtree(midl, ignore_errors=True)

print("== B2. main() bruger faktisk butikken — og i den rigtige rækkefølge ==")
import ast as _ast
_t = _ast.parse((REPO / "crawler.py").read_text(encoding="utf-8"))
_main = next((n for n in _t.body if isinstance(n, _ast.FunctionDef) and n.name == "main"), None)
ok("B6 main() findes", _main is not None)
_kald = [n.func.id for n in _ast.walk(_main) if isinstance(n, _ast.Call)
         and isinstance(n.func, _ast.Name)] if _main else []
_vil = ["_laes_foerst_set_butik", "_saet_foerst_set", "_skriv_foerst_set_butik"]
for _f in _vil:
    ok(f"B7 main() kalder {_f}", _f in _kald, _kald[:0])
_pos = [_kald.index(f) for f in _vil if f in _kald]
ok("B8 og i rækkefølgen læs -> sæt -> skriv",
   len(_pos) == 3 and _pos == sorted(_pos), _pos)

print("== C. de rigtige data: hvor mange bærer et tidspunkt, der er rykket frem? ==")
raa = json.loads((REPO / "data" / "articles.json").read_text(encoding="utf-8"))
arts = raa["artikler"]
try:
    butik_fil = json.loads((REPO / "data" / "foerst_set.json").read_text(encoding="utf-8"))["tider"]
except Exception:
    butik_fil = {}
ok("C0 butikken findes og har links", len(butik_fil) > 100, len(butik_fil))

foer = [a for a in arts if a.get("foerst_set") and butik_fil.get(a["link"])
        and a["foerst_set"] > butik_fil[a["link"]]]
print(f"     før rettelsen: {len(foer)} af {len(arts)} bærer et for sent tidspunkt")

kopi = copy.deepcopy(arts)
b = dict(butik_fil)
saet(kopi, kendte={a["link"]: a["foerst_set"] for a in arts if a.get("foerst_set")},
     nu=NU, eget={}, butik=b)
efter = [a for a in kopi if a.get("foerst_set") and butik_fil.get(a["link"])
         and a["foerst_set"] > butik_fil[a["link"]]]
print(f"     efter rettelsen: {len(efter)}")
ok("C1 ingen artikel bærer længere et tidspunkt senere end hukommelsen",
   len(efter) == 0, [a["link"] for a in efter][:3])
# Tallet må IKKE stå fast. Da prøven blev skrevet, bar 48 af 147 artikler et
# for sent tidspunkt; efter første kørsel med rettelsen var det 0. En påstand
# om "mindst 10" ville derfor gå rød af, at fejlen ER rettet. At mekanismen
# virker, måles i afsnit A på opdigtede data — dét er stedet, den skal prøves.
print(f"     (0 her betyder, at hukommelsen har gjort sit arbejde — ikke at prøven sover;"
      f" mekanismen prøves i afsnit A)")
ok("C2 og ingen af dem er blevet VÆRRE af rettelsen",
   not [a for a, b_ in zip(kopi, arts)
        if a.get("foerst_set") and b_.get("foerst_set")
        and a["foerst_set"] > b_["foerst_set"]],
   [a["link"] for a, b_ in zip(kopi, arts)
    if a.get("foerst_set") and b_.get("foerst_set")
    and a["foerst_set"] > b_["foerst_set"]][:3])
ok("C3 intet eget_foerst_set ligger senere end butikkens tal",
   all(not a.get("eget_foerst_set") or a["eget_foerst_set"] <= butik_fil.get(a["link"], "9")
       for a in kopi))
_uden = [a for a in kopi if not a.get("eget_foerst_set")]
print(f"     artikler uden eget_foerst_set (aldrig set usammenlagt): {len(_uden)}")
ok("C3b de fleste HAR et eget tidspunkt", len(_uden) < 20, len(_uden))
flyttet = [(a, b_) for a, b_ in zip(kopi, arts) if a.get("foerst_set") != b_.get("foerst_set")]
print(f"     tidspunkter flyttet tilbage: {len(flyttet)}")
ok("C4 alle flytninger går BAGUD, aldrig frem",
   all(a["foerst_set"] < b_["foerst_set"] for a, b_ in flyttet), len(flyttet))

print("== D. hvad kortet så viser ==")
def kort_tekst(pub, set_, nu=NU):
    """Samme regel som tidsTekst() i index.html — holdt op mod den i jsdom."""
    gap = (set_ - pub).total_seconds() * 1000 if (pub and set_) else 0
    return ("udgivelse", gap > 36 * 3600 * 1000)
gamle_men_friske = 0
for a in kopi:
    try:
        pub = _dt.datetime.fromisoformat(str(a["dato"]).replace("Z", "+00:00"))
        st = _dt.datetime.fromisoformat(str(a["foerst_set"]).replace("Z", "+00:00"))
    except Exception:
        continue
    if pub.tzinfo is None: pub = pub.replace(tzinfo=UTC)
    if st.tzinfo is None: st = st.replace(tzinfo=UTC)
    if (st - pub).total_seconds() > 36 * 3600 and (NU - st).total_seconds() < 36 * 3600:
        gamle_men_friske += 1
print(f"     artikler der stadig ser 'nye' ud, men er dage gamle: {gamle_men_friske}")
ok("D1 tallet er faldet markant (var 36 målt på de rå data)",
   gamle_men_friske <= 5, gamle_men_friske)

print("== E. gulvet er nu uden virkning — og det skal siges højt ==")
# `_gulv_paa_laante_tider` springer alt over, der har `eget_foerst_set`. Efter
# butikken er sået, har næsten alle det, så gulvet retter 0. Det er meningen —
# butikken er den rigtige hukommelse, gulvet var broen. Men det skal MÅLES, så
# ingen tror, gulvet stadig passer på noget.
_kopi2 = copy.deepcopy(kopi)
for _a in _kopi2:
    _d = _a.get("dato")
    if isinstance(_d, str):
        try: _a["dato"] = _dt.datetime.fromisoformat(_d.replace("Z", "+00:00"))
        except ValueError: _a["dato"] = None
_n = kald("_gulv_paa_laante_tider", _kopi2)
print(f"     gulvet retter nu {_n} artikler (var 2, før butikken fandtes)")
ok("E1 gulvet har intet at rette, når hukommelsen er på plads", _n == 0, _n)
# men det skal stadig virke, hvis en artikel mangler hukommelse
_legacy = [{"link": "https://a.dk/legacy", "kilde": "K", "titel": "T", "rubrik": "Gammel",
            "foerst_set": "2026-07-23T20:37:00+00:00",
            "dato": _dt.datetime(2026, 7, 25, 13, 5, tzinfo=UTC)}]
ok("E2 men det virker stadig for en artikel uden hukommelse",
   kald("_gulv_paa_laante_tider", _legacy) == 1, _legacy)

print("== F. dag-gruppen på forsiden må ikke ligge langt før udgivelsen ==")
# Forsiden grupperer efter foerst_set; kortet viser dato. De to må ikke skride
# fra hinanden. Før rettelsen sad tre kort under en overskrift 2-3 dage FØR den
# dato, kortets egen tekst nævnte.
_skred = []
for a in kopi:
    _f = _dt.datetime.fromisoformat(str(a["foerst_set"]).replace("Z", "+00:00"))
    _d = a.get("dato")
    _d = _d if isinstance(_d, _dt.datetime) else None
    if _d is None:
        try: _d = _dt.datetime.fromisoformat(str(a.get("dato")).replace("Z", "+00:00"))
        except Exception: continue
    if _f.tzinfo is None: _f = _f.replace(tzinfo=UTC)
    if _d.tzinfo is None: _d = _d.replace(tzinfo=UTC)
    if (_d.date() - _f.date()).days > 1:
        _skred.append((a.get("rubrik") or a["titel"], _f.date(), _d.date()))
print(f"     kort hvis dag-gruppe ligger mere end ét døgn før udgivelsen: {len(_skred)}")
for r, f_, d_ in _skred[:5]:
    print(f"       gruppe {f_}  udgivet {d_}  «{r[:42]}»")
ok("F1 ingen kort sidder mere end ét døgn før sin egen udgivelsesdag",
   len(_skred) == 0, _skred[:3])

print()
print(f"GROENNE {groen} · ROEDE {roed}")
sys.exit(1 if roed else 0)
