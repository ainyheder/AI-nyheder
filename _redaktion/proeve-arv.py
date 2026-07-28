#!/usr/bin/env python3
"""Prøve: ruller frigivelsen vinderens lånte tidspunkt og billede tilbage?

Kør den fra repoets rod:  python3 _redaktion/proeve-arv.py

Den læser `crawler.py` og `data/articles.json`, men SKRIVER intet — hverken i
`data/`, i `artikel/` eller i `articles.json`. Alt arbejde sker på kopier i
hukommelsen, og `ARTIKEL_MAPPE` peges bevidst mod en mappe, der ikke findes.

Sæt PROEVE_REPO for at køre den mod en anden udgave af filen (fx en kopi af HEAD).
"""
import ast as _ast
import copy
import datetime as _dt
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO = Path(os.environ.get("PROEVE_REPO", Path(__file__).resolve().parent.parent))
spec = importlib.util.spec_from_file_location("c", REPO / "crawler.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

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
    """Kald en funktion, der måske ikke findes i den udgave, vi prøver."""
    f = getattr(c, navn, None)
    return f(*a, **kw) if f else None


def art(link, **kw):
    a = {"link": link, "kilde": kw.pop("kilde", "Kilde " + link[-1]),
         "titel": kw.pop("titel", "Titel " + link[-1])}
    a.update(kw)
    return a


UTC = _dt.timezone.utc

print("== A. eget_foerst_set sættes ved FØDSLEN, ikke ved sammenlægningen ==")
nu = _dt.datetime(2026, 7, 28, 6, 0, tzinfo=UTC)
ny_art = {"link": "https://a.dk/ny"}
kendt_art = {"link": "https://a.dk/kendt"}
kald("_saet_foerst_set", [ny_art, kendt_art],
     {"https://a.dk/kendt": "2026-07-20T09:00:00+00:00"}, nu)
ok("A1 ny artikel får sit eget tidspunkt registreret",
   ny_art.get("eget_foerst_set") == nu.isoformat() == ny_art.get("foerst_set"), ny_art)
ok("A2 en kendt artikel får IKKE et gættet 'eget'",
   "eget_foerst_set" not in kendt_art, kendt_art)
ok("A3 den kendtes tid er uændret",
   kendt_art.get("foerst_set") == "2026-07-20T09:00:00+00:00", kendt_art)
# Feltet må IKKE hentes gennem `cache` — den kræver en rubrik, og en kørsel
# uden AI-nøgle giver artikler uden rubrik. Så ville feltet forsvinde for evigt.
baaret = {"link": "https://a.dk/baaret"}
kald("_saet_foerst_set", [baaret], {"https://a.dk/baaret": "2026-07-21T00:00:00+00:00"},
     nu, {"https://a.dk/baaret": "2026-07-21T00:00:00+00:00"})
ok("A4 eget_foerst_set bæres videre uden om rubrik-porten",
   baaret.get("eget_foerst_set") == "2026-07-21T00:00:00+00:00", baaret)
uden_rubrik = {"link": "https://a.dk/urub", "kilde": "K", "titel": "T"}
c.omskriv_nye([uden_rubrik], {})
ok("A5 en artikel uden rubrik i cachen mister ikke feltet undervejs",
   "eget_foerst_set" not in uden_rubrik, uden_rubrik)

print("== B. _slaa_sammen låner tiden, men skriver ikke 'eget' ==")
v = art("https://a.dk/1", rubrik="Vinder om Oracle", sektioner=[{"tekst": "x" * 900}],
        foerst_set="2026-07-25T10:00:00+00:00", eget_foerst_set="2026-07-25T10:00:00+00:00",
        dato="2026-07-25T09:00:00+00:00")
t = art("https://b.dk/2", rubrik="Taber om Oracle", foerst_set="2026-07-23T20:00:00+00:00")
c._slaa_sammen([v, t])
ok("B1 eget_foerst_set uændret af sammenlægningen",
   v.get("eget_foerst_set") == "2026-07-25T10:00:00+00:00", v.get("eget_foerst_set"))
ok("B2 foerst_set er nu det tidligste", v["foerst_set"] == "2026-07-23T20:00:00+00:00", v["foerst_set"])
ok("B3 andre bærer taberens foerst_set",
   v["andre"][0].get("foerst_set") == "2026-07-23T20:00:00+00:00", v["andre"][0])
ok("B4 andre bærer taberens rubrik", v["andre"][0].get("rubrik") == "Taber om Oracle")

t2 = art("https://d.dk/3", rubrik="Endnu en om Oracle", foerst_set="2026-07-22T08:00:00+00:00")
c._slaa_sammen([v, t2])
ok("B5 anden sammenlægning rører ikke 'eget'",
   v.get("eget_foerst_set") == "2026-07-25T10:00:00+00:00", v.get("eget_foerst_set"))
ok("B6 to kilder i andre", len(v.get("andre") or []) == 2, len(v.get("andre") or []))

print("== C. frigivelse af ALLE kilder giver tiden tilbage ==")
w = copy.deepcopy(v)
kald("_rul_arven_tilbage", w, [], w["andre"])
ok("C1 foerst_set tilbage til vinderens eget",
   w["foerst_set"] == "2026-07-25T10:00:00+00:00", w["foerst_set"])
ok("C2 eget_foerst_set beholdes — det er en permanent sandhed",
   w.get("eget_foerst_set") == "2026-07-25T10:00:00+00:00", w.get("eget_foerst_set"))

print("== D. delvis frigivelse regner om, i stedet for at nulstille ==")
w = copy.deepcopy(v)
beholdt = [k for k in w["andre"] if k["link"] == "https://b.dk/2"]
frigivne = [k for k in w["andre"] if k["link"] != "https://b.dk/2"]
kald("_rul_arven_tilbage", w, beholdt, frigivne)
ok("D1 tiden er den tilbageværendes, ikke vinderens",
   w["foerst_set"] == "2026-07-23T20:00:00+00:00", w["foerst_set"])

print("== E. en AFVIST artikel afleverer hverken tid eller billede ==")
# Den afviste står FØRST med vilje: står den sidst, finder billed-løkken den
# beholdte først, og prøven ville gå grøn uanset hvad.
v2 = art("https://a.dk/9", rubrik="Microsoft køber noget", sektioner=[{"tekst": "y" * 900}],
         foerst_set="2026-07-26T12:00:00+00:00", eget_foerst_set="2026-07-26T12:00:00+00:00")
slem = art("https://x.dk/9", rubrik="Helt anden historie om katte",
           foerst_set="2026-07-20T01:00:00+00:00", billede="data/img/slem.jpg",
           billedmotiv="en kat")
god = art("https://b.dk/9", rubrik="Microsoft køber noget andet",
          foerst_set="2026-07-26T11:00:00+00:00", billede="data/img/god.jpg",
          billedmotiv="et kontor")
c._slaa_sammen([v2, slem, god], vagt=lambda p, m: m["link"] != "https://x.dk/9")
ok("E1 afvist medlem er ikke i andre",
   all(k["link"] != "https://x.dk/9" for k in v2.get("andre") or []), v2.get("andre"))
ok("E2 afvist medlems TID blev ikke arvet",
   v2["foerst_set"] == "2026-07-26T11:00:00+00:00", v2["foerst_set"])
ok("E3 afvist medlems BILLEDE blev ikke arvet",
   v2.get("billede") == "data/img/god.jpg", v2.get("billede"))
ok("E4 långiveren står i andre, så lånet kan gives tilbage",
   (v2.get("laant_billede") or {}).get("fra") in
   [k["link"] for k in v2.get("andre") or []], v2.get("laant_billede"))

print("== F. lånt billede og lånt motiv ryger, når långiveren frigives ==")
w = copy.deepcopy(v2)
kald("_rul_arven_tilbage", w, [], w["andre"])
ok("F1 billede fjernet", "billede" not in w, w.get("billede"))
ok("F2 lånemærket fjernet", "laant_billede" not in w)
ok("F3 lånt motiv fjernet", "billedmotiv" not in w, w.get("billedmotiv"))
ok("F4 tiden tilbage", w["foerst_set"] == "2026-07-26T12:00:00+00:00", w["foerst_set"])

print("== G. lånt billede bliver, når långiveren bliver ==")
v3 = art("https://a.dk/8", rubrik="Google gør noget", sektioner=[{"tekst": "z" * 900}],
         foerst_set="2026-07-26T12:00:00+00:00", eget_foerst_set="2026-07-26T12:00:00+00:00")
laaner = art("https://b.dk/8", rubrik="Google gjorde noget",
             foerst_set="2026-07-26T11:00:00+00:00", billede="data/img/b.jpg")
tredje = art("https://c.dk/8", rubrik="Google gør endnu mere",
             foerst_set="2026-07-26T10:00:00+00:00")
c._slaa_sammen([v3, laaner, tredje])
beholdt = [k for k in v3["andre"] if k["link"] == "https://b.dk/8"]
frigivne = [k for k in v3["andre"] if k["link"] != "https://b.dk/8"]
kald("_rul_arven_tilbage", v3, beholdt, frigivne)
ok("G1 billedet blev", v3.get("billede") == "data/img/b.jpg", v3.get("billede"))
ok("G2 tid = den beholdtes", v3["foerst_set"] == "2026-07-26T11:00:00+00:00", v3["foerst_set"])

print("== H. lånemærket må ikke rive et NYT, betalt billede af ==")
skiftet = {"link": "https://a.dk/skift", "kilde": "K", "titel": "T",
           "foerst_set": "2026-07-20T00:00:00+00:00",
           "eget_foerst_set": "2026-07-24T00:00:00+00:00",
           "billede": "data/img/mit-eget-nye.jpg",
           "billedmotiv": "tomt kontorlandskab i morgenlys",
           "laant_billede": {"fra": "https://b.dk/skift",
                             "billede": "data/img/gammelt-laant.jpg",
                             "motiv": "en kat paa et bibliotek"}}
kald("_rul_arven_tilbage", skiftet, [], [{"kilde": "B", "link": "https://b.dk/skift"}])
ok("H1 det nye, betalte billede står tilbage",
   skiftet.get("billede") == "data/img/mit-eget-nye.jpg", skiftet.get("billede"))
ok("H2 vinderens eget motiv står tilbage",
   skiftet.get("billedmotiv") == "tomt kontorlandskab i morgenlys", skiftet.get("billedmotiv"))
ok("H3 lånemærket er ryddet op", "laant_billede" not in skiftet)
ok("H4 tiden blev alligevel rullet tilbage",
   skiftet["foerst_set"] == "2026-07-24T00:00:00+00:00", skiftet["foerst_set"])

print("== I. vrøvl vælter ingenting ==")
for vroevl in ([None], ["ikke en dict"], [{}], [{"link": None}], [{"foerst_set": None}], []):
    w = {"link": "https://a.dk/6", "kilde": "K", "titel": "T",
         "foerst_set": "2026-07-20T00:00:00+00:00",
         "eget_foerst_set": "2026-07-24T00:00:00+00:00",
         "laant_billede": "ikke en dict", "billede": "x.jpg"}
    try:
        kald("_rul_arven_tilbage", w, list(vroevl), list(vroevl))
        ok(f"I {vroevl!r:24} klarede den",
           w["foerst_set"] == "2026-07-24T00:00:00+00:00", w["foerst_set"])
    except Exception as e:
        ok(f"I {vroevl!r:24} klarede den", False, f"{type(e).__name__}: {e}")

print("== J. vinder helt uden foerst_set får ikke en None-nøgle ==")
v4 = art("https://a.dk/5", rubrik="Uden tid", sektioner=[{"tekst": "q" * 900}])
t4 = art("https://b.dk/5", rubrik="Uden tid også")
c._slaa_sammen([v4, t4])
ok("J1 ingen eget_foerst_set-nøgle", "eget_foerst_set" not in v4, v4.get("eget_foerst_set"))
ok("J2 kan serialiseres", bool(json.dumps(v4)))

print("== K. felterne overlever natten — hvidliste OG genskabelse ==")
_traeet = _ast.parse((REPO / "crawler.py").read_text(encoding="utf-8"))
_hvidlister = [n for n in _ast.walk(_traeet)
               if isinstance(n, _ast.Dict)
               and any(isinstance(k, _ast.Constant) and k.value == "navngivet" for k in n.keys)
               and any(isinstance(k, _ast.Constant) and k.value == "sektioner" for k in n.keys)]
_noegler = {k.value for d in _hvidlister for k in d.keys if isinstance(k, _ast.Constant)}
ok("K0 præcis én cache-hvidliste i crawler.py", len(_hvidlister) == 1, len(_hvidlister))
ok("K1 hvidlisten bærer laant_billede", "laant_billede" in _noegler, sorted(_noegler))
ok("K1b eget_foerst_set går IKKE gennem den rubrik-gatede cache",
   "eget_foerst_set" not in _noegler, sorted(_noegler))

# Genskabelsen prøves med den RIGTIGE feltliste — læst ud af hvidlisten selv,
# så prøven ikke kan gå grøn på en liste, jeg har skrevet af i hånden.
kilde_art = {"link": "https://a.dk/4", "rubrik": "R", "resume_da": "r",
             "brief": "", "sektioner": [{"tekst": "t"}], "noegletal": None,
             "figurer": None, "andre": [{"kilde": "K", "link": "https://b.dk/4"}],
             "detaljer": [], "betydning": "", "pointer": [], "billedmotiv": "et motiv",
             "billede": "data/img/k.jpg", "kategori": "", "kat_ai": False,
             "navngivet": False, "prio": 5,
             "eget_foerst_set": "2026-07-25T10:00:00+00:00",
             "laant_billede": {"fra": "https://b.dk/4", "billede": "data/img/k.jpg",
                               "motiv": "et motiv"}}
cache = {kilde_art["link"]: {k: kilde_art.get(k) for k in _noegler}}
i_morgen = {"link": "https://a.dk/4", "kilde": "K", "titel": "T"}
c.omskriv_nye([i_morgen], cache)
ok("K3 laant_billede genskabt HELT",
   i_morgen.get("laant_billede") == kilde_art["laant_billede"], i_morgen.get("laant_billede"))
i_morgen.pop("andre", None)
kald("_rul_arven_tilbage", i_morgen, [], [{"kilde": "K", "link": "https://b.dk/4"}])
ok("K4 og lånet kan gives tilbage dagen efter",
   "billede" not in i_morgen and "billedmotiv" not in i_morgen, i_morgen)

# 27 af 145 artikler har hverken brief eller sektioner. Genskabes lånemærket
# bag sektioner-porten, mister netop de deres lån — prøv det udtrykkeligt.
tynd = {k: kilde_art.get(k) for k in _noegler}
tynd["brief"] = ""
tynd["sektioner"] = []
tynd_ny = {"link": "https://a.dk/4", "kilde": "K", "titel": "T"}
c.omskriv_nye([tynd_ny], {"https://a.dk/4": tynd})
ok("K5 lånemærket genskabes også uden sektioner",
   tynd_ny.get("laant_billede") == kilde_art["laant_billede"], tynd_ny.get("laant_billede"))

print("== L. hele trin 0 på de RIGTIGE data (kopi) ==")
raa = json.loads((REPO / "data" / "articles.json").read_text(encoding="utf-8"))


def rigtige_data():
    a = copy.deepcopy(raa["artikler"])
    for x in a:                      # main() har datetime her, ikke tekst
        d = x.get("dato")
        if isinstance(d, str):
            try:
                x["dato"] = _dt.datetime.fromisoformat(d.replace("Z", "+00:00"))
            except ValueError:
                x["dato"] = None
    return a


arts = rigtige_data()
foer_tider = {a["link"]: a.get("foerst_set") for a in arts}
foer_billeder = {a["link"]: a.get("billede") for a in arts}
c.ARTIKEL_MAPPE = Path("/tmp/findes-ikke-med-vilje")   # ingen frosne sider at læse
c.API_KEY = ""                                          # ingen AI-fase, ingen penge
resultat = c.saml_dublet_historier(rigtige_data())
ok("L1 ingen artikler tabt", len(resultat) == len(arts), f"{len(resultat)} af {len(arts)}")
flyttede = {a["link"]: (foer_tider[a["link"]], a.get("foerst_set")) for a in resultat
            if foer_tider.get(a["link"]) and a.get("foerst_set") != foer_tider[a["link"]]}
mistede = [a["link"] for a in resultat if foer_billeder.get(a["link"]) and not a.get("billede")]
print(f"     tider flyttet: {len(flyttede)} · billeder fjernet: {len(mistede)}")
for l, (f, n) in flyttede.items():
    rub = next((a.get("rubrik") for a in resultat if a["link"] == l), "")
    print(f"       «{(rub or '')[:44]}»  {str(f)[:16]} -> {str(n)[:16]}")
ok("L2 præcis de to kendte fejl blev rettet, ikke flere", len(flyttede) == 2, sorted(flyttede))
ok("L3 begge landede på deres egen udgivelsesdag",
   all(str(n)[:10] == str(next(a["dato"] for a in resultat if a["link"] == l))[:10]
       for l, (f, n) in flyttede.items()), list(flyttede.values()))
ok("L4 ingen billeder revet af", len(mistede) == 0, mistede[:4])
ok("L5 resultatet kan serialiseres",
   bool(json.dumps({"artikler": resultat}, ensure_ascii=False, default=str)))

print("== M. gulvet rører kun det, det skal ==")
lovlig = {"link": "https://a.dk/lov", "kilde": "K", "titel": "T", "rubrik": "Lovlig",
          "foerst_set": "2026-07-26T18:46:35+00:00",
          "dato": _dt.datetime(2026, 7, 27, 0, 19, tzinfo=UTC)}       # 5,5 t — lovligt
har_eget = {"link": "https://a.dk/eget", "kilde": "K", "titel": "T", "rubrik": "Har eget",
            "foerst_set": "2026-07-20T00:00:00+00:00",
            "eget_foerst_set": "2026-07-20T00:00:00+00:00",
            "dato": _dt.datetime(2026, 7, 25, tzinfo=UTC)}
har_andre = {"link": "https://a.dk/andre", "kilde": "K", "titel": "T", "rubrik": "Har kilder",
             "foerst_set": "2026-07-20T00:00:00+00:00",
             "andre": [{"kilde": "X", "link": "https://x.dk/1"}],
             "dato": _dt.datetime(2026, 7, 25, tzinfo=UTC)}
skal_rettes = {"link": "https://a.dk/fejl", "kilde": "K", "titel": "T", "rubrik": "Lånt tid",
               "foerst_set": "2026-07-23T20:37:15.313153+00:00",
               "dato": _dt.datetime(2026, 7, 25, 13, 5, tzinfo=UTC)}
uden_dato = {"link": "https://a.dk/udato", "kilde": "K", "titel": "T", "rubrik": "Uden dato",
             "foerst_set": "2026-07-20T00:00:00+00:00", "dato": None}
vroevl_dato = {"link": "https://a.dk/vroevl", "kilde": "K", "titel": "T", "rubrik": "Vrøvl",
               "foerst_set": "ikke en dato", "dato": "heller ikke"}
raekke = [lovlig, har_eget, har_andre, skal_rettes, uden_dato, vroevl_dato]
antal = kald("_gulv_paa_laante_tider", raekke)
ok("M1 præcis én rettet", antal == 1, antal)
ok("M2 den lånte tid fik sin udgivelsesdag",
   skal_rettes["foerst_set"][:10] == "2026-07-25", skal_rettes["foerst_set"])
ok("M2b og PRÆCIS udgivelsestidspunktet, i ISO-form med T",
   skal_rettes["foerst_set"] == "2026-07-25T13:05:00+00:00", skal_rettes["foerst_set"])
ok("M3 lovligt forspring på 5,5 t urørt",
   lovlig["foerst_set"] == "2026-07-26T18:46:35+00:00", lovlig["foerst_set"])
ok("M4 en med eget_foerst_set urørt", har_eget["foerst_set"] == "2026-07-20T00:00:00+00:00")
ok("M5 en med kilder urørt", har_andre["foerst_set"] == "2026-07-20T00:00:00+00:00")
ok("M6 uden dato urørt", uden_dato["foerst_set"] == "2026-07-20T00:00:00+00:00")
ok("M7 vrøvl urørt og uden brag", vroevl_dato["foerst_set"] == "ikke en dato")
ok("M8 gulvet er stabilt — anden kørsel retter intet",
   kald("_gulv_paa_laante_tider", raekke) == 0)

# Grænsen skal være pinnet, ellers kan tallet 24 skiftes til hvad som helst.
def _kandidat(timer):
    return {"link": f"https://a.dk/t{timer}", "kilde": "K", "titel": "T", "rubrik": "T",
            "foerst_set": (_dt.datetime(2026, 7, 25, 12, tzinfo=UTC)
                           - _dt.timedelta(hours=timer)).isoformat(),
            "dato": _dt.datetime(2026, 7, 25, 12, tzinfo=UTC)}
under, over = _kandidat(23), _kandidat(25)
kald("_gulv_paa_laante_tider", [under, over])
ok("M9 23 timers forspring er under grænsen og røres ikke",
   under["foerst_set"].startswith("2026-07-24T13"), under["foerst_set"])
ok("M10 25 timers forspring er over grænsen og rettes",
   over["foerst_set"] == "2026-07-25T12:00:00+00:00", over["foerst_set"])

print("== M2. gulvet kører EFTER frigivelsen, ikke før ==")
# En gammel historie (uden eget_foerst_set), hvis sidste kilde frigives i DAG.
# Køres gulvet før løkken, står den med sin lånte tid et døgn mere.
gl = {"link": "https://medie-a.dk/gl", "kilde": "A", "titel": "Oracle lays off 21,000",
      "rubrik": "Oracle fyrer 21.000 ansatte",
      "resume_da": "Oracle skærer 21.000 stillinger væk efter AI-satsning.",
      "sektioner": [{"tekst": "Oracle " * 200}],
      "dato": _dt.datetime(2026, 7, 25, 13, 5, tzinfo=UTC),
      "foerst_set": "2026-07-23T16:57:00+00:00",
      "andre": [{"kilde": "B", "link": "https://medie-b.dk/gl",
                 "rubrik": "Biblioteker holder kursus i kattepasning",
                 "resume_da": "Kurserne handler om pasning af killinger og huskatte.",
                 "foerst_set": "2026-07-23T16:57:00+00:00"}]}
ud2 = c.saml_dublet_historier([gl] + [dict(n, link=n["link"] + "b") for n in naboer]
                              if False else [gl] + [{"link": f"https://c.dk/g{i}", "kilde": "C",
                                                     "titel": f"Andet {i}", "rubrik": f"Vejret i uge {i}",
                                                     "resume_da": "Sol og sommer.",
                                                     "dato": _dt.datetime(2026, 7, 25, tzinfo=UTC),
                                                     "foerst_set": "2026-07-25T00:00:00+00:00"}
                                                    for i in range(3)])
efter2 = next(a for a in ud2 if a["link"] == gl["link"])
ok("M11 gammel historie frigivet OG gulv-rettet i samme kørsel",
   not efter2.get("andre") and efter2["foerst_set"] == "2026-07-25T13:05:00+00:00",
   (efter2.get("andre"), efter2["foerst_set"]))

print("== N. saml_dublet_historier FRIGIVER og ruller tilbage af sig selv ==")
vinder_o = {"link": "https://medie-a.dk/oracle-o", "kilde": "A",
            "titel": "Oracle lays off 21,000",
            "rubrik": "Oracle fyrer 21.000 ansatte",
            "resume_da": "Oracle skærer 21.000 stillinger væk efter AI-satsning.",
            "sektioner": [{"tekst": "Oracle " * 200}],
            "dato": _dt.datetime(2026, 7, 25, 13, 5, tzinfo=UTC),
            "foerst_set": "2026-07-23T16:57:00+00:00",
            "eget_foerst_set": "2026-07-25T13:05:00+00:00",
            "billede": "data/img/katte.jpg",
            "billedmotiv": "en kat paa et bibliotek",
            "laant_billede": {"fra": "https://medie-b.dk/katte-o",
                              "billede": "data/img/katte.jpg",
                              "motiv": "en kat paa et bibliotek"},
            "andre": [{"kilde": "B", "link": "https://medie-b.dk/katte-o",
                       "rubrik": "Biblioteker holder kursus i kattepasning",
                       "resume_da": "Kurserne handler om pasning af killinger og huskatte.",
                       "foerst_set": "2026-07-23T16:57:00+00:00"}]}
naboer = [{"link": f"https://c.dk/fyld{i}", "kilde": "C", "titel": f"Andet emne {i}",
           "rubrik": f"Vejret bliver bedre i uge {i}", "resume_da": "Sol og sommer.",
           "dato": _dt.datetime(2026, 7, 25, tzinfo=UTC),
           "foerst_set": "2026-07-25T00:00:00+00:00"} for i in range(3)]
ud = c.saml_dublet_historier([vinder_o] + naboer)
efter = next(a for a in ud if a["link"] == vinder_o["link"])
ok("N1 kilden blev frigivet af funktionen selv", not efter.get("andre"), efter.get("andre"))
ok("N2 tiden blev rullet tilbage af funktionen selv",
   efter["foerst_set"] == "2026-07-25T13:05:00+00:00", efter["foerst_set"])
ok("N3 dag-gruppen på forsiden er 25., ikke 23.", str(efter["foerst_set"])[:10] == "2026-07-25")
ok("N4 kattebilledet er væk", "billede" not in efter, efter.get("billede"))
ok("N5 kattemotivet er væk", "billedmotiv" not in efter, efter.get("billedmotiv"))

print("== O. alle foerst_set i de rigtige data er UTC, så streng-min er sikker ==")
skaeve = [(a["link"], a["foerst_set"]) for a in raa["artikler"]
          if (a.get("foerst_set") or "") and not a["foerst_set"].endswith("+00:00")]
ok("O1 ingen blandede tidszoner", len(skaeve) == 0, skaeve[:3])

print()
print(f"GROENNE {groen} · ROEDE {roed}")
sys.exit(1 if roed else 0)
