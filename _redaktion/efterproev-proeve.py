#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prøve af _redaktion/efterproev.py.

Kører mod opdigtede køer i hukommelsen, så den rigtige opgavekø aldrig røres.
Til sidst nogle få prøver mod den ægte kø, der kun ser, om den kan læses uden
at gå ned, og om regnskabet går op.

Kør fra repoets rod:  python3 _redaktion/efterproev-proeve.py
Udfaldskode 0 = alt grønt, 1 = mindst én rød.
"""
import datetime, pathlib, sys, importlib.util

ROD = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("efterproev", ROD / "_redaktion" / "efterproev.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

I_DAG = datetime.date(2026, 7, 27)
groenne, roede = [], []

def proev(navn, faktisk, ventet):
    if faktisk == ventet:
        groenne.append(navn); print(f"  ✅ {navn}")
    else:
        roede.append(navn); print(f"  ❌ {navn}\n       fik:      {faktisk!r}\n       ventede:  {ventet!r}")

def punkt(titel, dato="20.07.2026", hale=""):
    return f"- [x] **{titel}** *({dato}, kørsel)*\n  Resultat: noget.{hale}"

def koe(*punkter, overskrift="## Klaret"):
    return "# Kø\n\n## Kø\n\n- [ ] **Et åbent punkt.** *(27.07.2026)*\n\n" + overskrift + "\n\n" + "\n".join(punkter) + "\n\n## Ting kun Torben kan gøre\n\n- noget\n"

print("\n— valget —")
p1, p2 = punkt("Ældst", "18.07.2026"), punkt("Yngst", "22.07.2026")
valgt, tal = e.vaelg(e.klarede_punkter(koe(p1, p2)), I_DAG)
proev("det ældste punkt vælges", e.titel(valgt), "Ældst")
proev("regnskabet tæller begge", tal["i_alt"], 2)

valgt, _ = e.vaelg(e.klarede_punkter(koe(punkt("Yngst", "22.07.2026"), punkt("Ældst", "18.07.2026"))), I_DAG)
proev("rækkefølgen i filen er ligegyldig", e.titel(valgt), "Ældst")

# Samme dato: den nederste (ældst skrevet) vinder.
valgt, _ = e.vaelg(e.klarede_punkter(koe(punkt("Øverst", "18.07.2026"), punkt("Nederst", "18.07.2026"))), I_DAG)
proev("samme dato: den nederste vælges", e.titel(valgt), "Nederst")

print("\n— hvad springes over —")
maerket = punkt("Allerede set", "18.07.2026", hale="\n  **Efterprøvet 26.07.2026: holder.** 3 af 4.")
valgt, tal = e.vaelg(e.klarede_punkter(koe(maerket, punkt("Ikke set", "20.07.2026"))), I_DAG)
proev("et mærket punkt vælges ikke igen", e.titel(valgt), "Ikke set")
proev("mærket tælles som i karens", tal["i_karens"], 1)

for variant in ("- **Efterprøvet 26.07.2026: holder.**",
                "**efterprøvet 26.07.2026: holder.**",
                "  Efterprøvet 26.07.2026: gik i stykker igen."):
    v, t = e.vaelg(e.klarede_punkter(koe(punkt("X", "18.07.2026", hale="\n" + variant))), I_DAG)
    proev(f"mærket genkendes: {variant.strip()[:34]}…", (v, t["i_karens"]), (None, 1))

igaar = punkt("For ny", (I_DAG - datetime.timedelta(days=1)).strftime("%d.%m.%Y"))
valgt, tal = e.vaelg(e.klarede_punkter(koe(igaar)), I_DAG)
proev("under to døgn springes over", (valgt, tal["for_ny"]), (None, 1))

praecis = punkt("Præcis to døgn", (I_DAG - datetime.timedelta(days=2)).strftime("%d.%m.%Y"))
valgt, _ = e.vaelg(e.klarede_punkter(koe(praecis)), I_DAG)
proev("præcis to døgn er gammelt nok", e.titel(valgt) if valgt else None, "Præcis to døgn")

uden = "- [x] **Ingen dato her.**\n  Resultat: ingen tal."
valgt, tal = e.vaelg(e.klarede_punkter(koe(uden)), I_DAG)
proev("punkt uden dato springes over", (valgt, tal["uden_dato"]), (None, 1))

umulig = punkt("Umulig dato", "31.02.2026")
valgt, tal = e.vaelg(e.klarede_punkter(koe(umulig)), I_DAG)
proev("31.02 er ikke en dato", (valgt, tal["uden_dato"]), (None, 1))

fremtid = punkt("Fremtid", "01.09.2026")
valgt, _ = e.vaelg(e.klarede_punkter(koe(fremtid)), I_DAG)
proev("en dato i fremtiden vælges ikke", valgt, None)

print("\n— tomme og skæve køer —")
proev("ingen ## Klaret giver tom liste", e.klarede_punkter("# Kø\n\n## Kø\n\n- [ ] noget\n"), [])
proev("tom ## Klaret giver tom liste", e.klarede_punkter("## Klaret\n\n## Andet\n"), [])
proev("tom liste giver intet valg", e.vaelg([], I_DAG)[0], None)
proev("åbne punkter tælles ikke med",
      len(e.klarede_punkter("## Klaret\n\n- [ ] **Åbent.**\n- [x] **Lukket.** *(18.07.2026)*\n")), 1)
proev("næste ## stopper blokken",
      len(e.klarede_punkter("## Klaret\n\n- [x] **A.** *(18.07.2026)*\n\n## Mistanker\n\n- [x] **B.** *(18.07.2026)*\n")), 1)
proev("ISO-dato læses også", e.\
      _dato_i("- [x] **A.** *(2026-07-18)*"), datetime.date(2026, 7, 18))
proev("flerlinjet titel klippes sammen",
      e.titel("- [x] **En titel\n  over to linjer.** *(18.07.2026)*"), "En titel over to linjer.")

print("\n— karens: et mærke er ikke evig fritagelse —")
def maerket(titel, dato, udfald, maerkedato):
    return punkt(titel, dato, hale=f"\n  **Efterprøvet {maerkedato}: {udfald}.** noget.")

# "holder" har 21 døgns karens, de to andre 7.
tilfaelde = [
    ("holder", 5, None),            ("holder", 25, "H"),
    ("gik i stykker", 3, None),     ("gik i stykker", 9, "H"),
    ("kan ikke måles", 3, None),    ("kan ikke måles", 9, "H"),
]
for udfald, siden, ventet in tilfaelde:
    md = (I_DAG - datetime.timedelta(days=siden)).strftime("%d.%m.%Y")
    v, t = e.vaelg(e.klarede_punkter(koe(maerket("H", "10.07.2026", udfald, md))), I_DAG)
    proev(f"«{udfald}» for {siden} døgn siden", e.titel(v) if v else None, ventet)

proev("karens tælles i regnskabet",
      e.vaelg(e.klarede_punkter(koe(maerket("H", "10.07.2026", "holder",
              (I_DAG - datetime.timedelta(days=5)).strftime("%d.%m.%Y")))), I_DAG)[1]["i_karens"], 1)

# Et mærke uden læselig dato må ikke give evig fritagelse OG må ikke vælges blindt.
v, t = e.vaelg(e.klarede_punkter(koe(punkt("H", "10.07.2026", hale="\n  **Efterprøvet: holder.**"))), I_DAG)
proev("mærke uden dato lades ligge", (v, t["i_karens"]), (None, 1))

print("\n— udfaldet læses rigtigt —")
for tekst, ventet in [
    ("**Efterprøvet 25.07.2026: holder.** 3 af 4.", "holder"),
    ("**Efterprøvet 25.07.2026: gik i stykker igen.** nu 9.", "gik i stykker"),
    ("**Efterprøvet 25.07.2026: kan ikke måles herfra.** kun i GSC.", "kan ikke måles"),
    ("**Efterprøvet 25.07.2026: noget helt andet.**", "?"),
]:
    u, d = e.maerke_i("- [x] **T.** *(10.07.2026)*\n  " + tekst, I_DAG)
    proev(f"udfald: {ventet}", (u, d), (ventet, datetime.date(2026, 7, 25)))
proev("intet mærke giver (None, None)", e.maerke_i(punkt("T"), I_DAG), (None, None))

print("\n— datoer uden årstal —")
proev("26.07 læses som i år", e._dato_i("*(målt 26.07 kl. 23:40)*", I_DAG), datetime.date(2026, 7, 26))
proev("en kort dato i fremtiden er sidste år", e._dato_i("*(målt 01.09)*", I_DAG), datetime.date(2025, 9, 1))
proev("klokkeslæt er ikke en dato", e._dato_i("kl. 23:40 og 15.30 minutter", I_DAG), None)
proev("2.861 er ikke en dato", e._dato_i("2.861 interne referencer", I_DAG), None)
proev("fuld dato slår kort dato", e._dato_i("*(18.07.2026, målt 26.07)*", I_DAG), datetime.date(2026, 7, 18))
v, t = e.vaelg(e.klarede_punkter(koe("- [x] **Kort dato.** *(målt 20.07 kl. 11)* noget.")), I_DAG)
proev("punkt med kort dato er nu synligt", e.titel(v) if v else None, "Kort dato.")

print("\n— efterslæbet —")
mange = [punkt(f"P{i}", "18.07.2026") for i in range(e.EFTERSLAEB_GRAENSE + 1)]
proev("modne uden mærke tælles", e.vaelg(e.klarede_punkter(koe(*mange)), I_DAG)[1]["modne_uden_maerke"],
      e.EFTERSLAEB_GRAENSE + 1)
nye = [punkt(f"N{i}", I_DAG.strftime("%d.%m.%Y")) for i in range(20)]
proev("for nye punkter tæller ikke som efterslæb",
      e.vaelg(e.klarede_punkter(koe(*nye)), I_DAG)[1]["modne_uden_maerke"], 0)

print("\n— den ægte kø —")
ae = e.klarede_punkter((ROD / "_redaktion" / "opgavekoe.md").read_text(encoding="utf-8"))
proev("den ægte kø har klarede punkter", len(ae) > 0, True)
v, t = e.vaelg(ae, e._i_dag())
proev("regnskabet går op", t["i_alt"], t["i_karens"] + t["uden_dato"] + t["for_ny"] + t["kandidater"])
proev("alle klarede punkter starter med - [x]", all(p.startswith("- [x]") for p in ae), True)
print(f"     (valgt i dag: {e.titel(v) if v else 'ingen'})")

print(f"\n{len(groenne)} grønne, {len(roede)} røde")
sys.exit(1 if roede else 0)
