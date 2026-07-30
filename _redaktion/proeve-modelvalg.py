#!/usr/bin/env python3
"""Prøve: havner et valgt modelnavn hos den RIGTIGE udbyder?

Kør den fra repoets rod:  python3 _redaktion/proeve-modelvalg.py

Rører ingen rigtige filer og laver ingen netværkskald: alle udgående kald
bliver byttet ud med attrapper, der bare skriver ned, hvem der blev ringet til.
Sæt PROEVE_REPO for at køre den mod en anden udgave (fx en kopi af HEAD).
"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(os.environ.get("PROEVE_REPO", Path(__file__).resolve().parent.parent))
groen = roed = 0


def indlaes(gemini="G-NOEGLE", deepseek="D-NOEGLE", udbyder=""):
    """Frisk crawler-modul med de nøgler, prøven har brug for.

    Nøglerne læses i modulets top, så de SKAL sættes før import."""
    for navn, vaerdi in (("GEMINI_API_KEY", gemini),
                         ("DEEPSEEK_API_KEY", deepseek),
                         ("AI_UDBYDER", udbyder)):
        if vaerdi:
            os.environ[navn] = vaerdi
        else:
            os.environ.pop(navn, None)
    spec = importlib.util.spec_from_file_location("c_mv", REPO / "crawler.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def ok(navn, betingelse, ekstra=""):
    global groen, roed
    if betingelse:
        groen += 1
    else:
        roed += 1
        print(f"  ROED  {navn} {ekstra}")


def spor(m, monkey=True):
    """Byt de tre udgående kald ud med attrapper. Returnerer en log-liste."""
    log = []
    if monkey:
        m.kald_gemini_model = lambda s, b, t, mo: (log.append(("gemini", mo)), "svar")[1]
        m.kald_deepseek_model = lambda s, b, t, mo: (log.append(("deepseek", mo)), "svar")[1]
        m.kald_ai = lambda s, b, t: (log.append(("daglig", None)), "svar")[1]
    return log


print("== A. navnet afgør udbyderen ==")
c = indlaes()
f = getattr(c, "model_udbyder", None)
ok("A0 model_udbyder findes", f is not None, "funktionen mangler i denne udgave")
if f:
    ok("A1 deepseek-v4-flash → deepseek", f("deepseek-v4-flash") == "deepseek", f("deepseek-v4-flash"))
    ok("A2 deepseek-v4-pro → deepseek", f("deepseek-v4-pro") == "deepseek")
    ok("A3 gemini-3.6-flash → gemini", f("gemini-3.6-flash") == "gemini", f("gemini-3.6-flash"))
    ok("A4 gemini-3.5-flash-lite → gemini", f("gemini-3.5-flash-lite") == "gemini")
    # Et ukendt navn må ALDRIG gætte. Gættede den på gemini, ville et DeepSeek-
    # navn med stavefejl ryge til Google og koste penge på en fejl.
    ok("A5 et ukendt navn giver tom streng", f("llama-4-scout") == "", f("llama-4-scout"))
    ok("A6 tom streng giver tom streng", f("") == "")
    ok("A7 None vælter ikke noget", f(None) == "")
    ok("A8 store bogstaver tæller ikke", f("DeepSeek-V4-Pro") == "deepseek", f("DeepSeek-V4-Pro"))
    ok("A9 mellemrum omkring navnet tæller ikke", f("  gemini-3.6-flash  ") == "gemini")
    # Præfiks, ikke delstreng: en model der bare NÆVNER en udbyder midt i
    # navnet, er ikke den udbyders model.
    ok("A10 udbyderen skal stå FORREST", f("min-gemini-klon") == "", f("min-gemini-klon"))

print("== B. hjerne_kald sender til den rigtige adresse ==")
c = indlaes()
log = spor(c)
c.hjerne_kald("omskriv", "std", "tekst", 100, "deepseek-v4-pro")
ok("B1 et DeepSeek-navn går til DeepSeek", log == [("deepseek", "deepseek-v4-pro")], log)

log = spor(c)
c.hjerne_kald("omskriv", "std", "tekst", 100, "gemini-3.6-flash")
ok("B2 et Gemini-navn går til Google", log == [("gemini", "gemini-3.6-flash")], log)

log = spor(c)
c.hjerne_kald("omskriv", "std", "tekst", 100, None)
ok("B3 uden valgt model køres den daglige", log == [("daglig", None)], log)

log = spor(c)
c.hjerne_kald("omskriv", "std", "tekst", 100, "llama-4-scout")
ok("B4 et ukendt navn falder til den daglige — og IKKE til Google",
   log == [("daglig", None)], log)

print("== C. manglende nøgle rammer kun sin egen udbyder ==")
c = indlaes(deepseek="")          # kun Google-nøgle
log = spor(c)
c.hjerne_kald("omskriv", "std", "tekst", 100, "deepseek-v4-pro")
ok("C1 uden DeepSeek-nøgle falder et DeepSeek-valg til den daglige",
   log == [("daglig", None)], log)
log = spor(c)
c.hjerne_kald("omskriv", "std", "tekst", 100, "gemini-3.6-flash")
ok("C2 … men Gemini-valget virker stadig", log == [("gemini", "gemini-3.6-flash")], log)

c = indlaes(gemini="")            # kun DeepSeek-nøgle
log = spor(c)
c.hjerne_kald("omskriv", "std", "tekst", 100, "gemini-3.6-flash")
ok("C3 uden Google-nøgle falder et Gemini-valg til den daglige",
   log == [("daglig", None)], log)
log = spor(c)
c.hjerne_kald("omskriv", "std", "tekst", 100, "deepseek-v4-pro")
ok("C4 … og DeepSeek-valget virker",
   log == [("deepseek", "deepseek-v4-pro")], log)

print("== D. et fald tilbage skal kunne ses i loggen ==")
import io
import contextlib

for navn, model, ord_i_linjen in (
        ("ukendt model", "llama-4-scout", "udbyderen"),
        ("manglende nøgle", "deepseek-v4-pro", "nøgle"),
        ("modellen svarer ikke", "gemini-3.6-flash", "svarede ikke")):
    c = indlaes(deepseek="" if navn == "manglende nøgle" else "D-NOEGLE")
    log = spor(c)
    if navn == "modellen svarer ikke":
        def sprael(*a, **k):
            raise RuntimeError("nej")
        c.kald_gemini_model = sprael
    baand = io.StringIO()
    with contextlib.redirect_stdout(baand):
        c.hjerne_kald("omskriv", "std", "tekst", 100, model)
    tekst = baand.getvalue()
    ok(f"D {navn:22} siger det højt",
       ord_i_linjen in tekst and "omskriv" in tekst, repr(tekst[:90]))

print("== E. DeepSeek-kaldet bruger DeepSeeks egen nøgle ==")
# Kører siden til daglig på Gemini, er API_KEY Googles nøgle. Bruger
# kald_deepseek_model den, sender vi Googles nøgle til et kinesisk endpoint.
c = indlaes(udbyder="gemini")
ok("E0 opsætningen er den farlige: daglig udbyder er Gemini",
   c.UDBYDER == "gemini" and c.API_KEY == "G-NOEGLE", (c.UDBYDER, c.API_KEY))
sendt = {}


def falsk_hent(url, data=None, headers=None, **kw):
    sendt["url"] = url
    sendt["headers"] = headers or {}
    sendt["body"] = json.loads(data.decode()) if data else None
    return json.dumps({"choices": [{"message": {"content": "svar"}}]}).encode()


c.hent_url = falsk_hent
c.kald_deepseek_model("system", "bruger", 50, "deepseek-v4-pro")
ok("E1 kaldet går til DeepSeeks adresse", "deepseek.com" in sendt["url"], sendt["url"])
ok("E2 og bærer DeepSeeks nøgle, ikke Googles",
   sendt["headers"].get("Authorization") == "Bearer D-NOEGLE",
   sendt["headers"].get("Authorization"))
ok("E3 modelnavnet kommer udefra, ikke fra konstanten",
   sendt["body"]["model"] == "deepseek-v4-pro", sendt["body"]["model"])
ok("E4 tænkning er slået fra — ellers afregnes tankerne som udskrift",
   sendt["body"].get("thinking") == {"type": "disabled"}, sendt["body"].get("thinking"))
c2 = indlaes(deepseek="")
try:
    c2.kald_deepseek_model("s", "b", 10, "deepseek-v4-pro")
    ok("E5 uden nøgle kastes en fejl i stedet for et kald", False, "ingen fejl")
except RuntimeError:
    ok("E5 uden nøgle kastes en fejl i stedet for et kald", True)

print("== G. den rigtige vej: hjerner.json fra panelet ==")
# B-C kørte gennem `standard_model`, og INGEN af de 14 kaldesteder bruger den.
# Produktionens vej er panelets fil -> hjerne_model() -> hjerne_kald(). Uden
# afsnittet her kunne man slette `hjerne_model(navn) or` og se 35 grønne,
# mens hvert eneste valg i panelet stille holdt op med at virke.
midl_h = Path(tempfile.mkdtemp(prefix="proeve-hjerner-"))
try:
    def med_fil(indhold, **kw):
        c = indlaes(**kw)
        sti = midl_h / "hjerner.json"
        sti.write_text(json.dumps(indhold, ensure_ascii=False), encoding="utf-8")
        c.HJERNER_FIL = sti
        c._hjerner_cache = None                      # cachen er læst i importen
        for felt in ("_hjerner_cache", "_HJERNER", "_hjerner_laest"):
            if hasattr(c, felt):
                setattr(c, felt, None)
        return c

    c = med_fil({"hjerner": {"omskriv": {"model": "deepseek-v4-pro"}}})
    ok("G0 crawleren læser modellen fra filen",
       c.hjerne_model("omskriv") == "deepseek-v4-pro", c.hjerne_model("omskriv"))
    log = spor(c)
    c.hjerne_kald("omskriv", "std", "tekst", 100)     # ingen standard_model
    ok("G1 et valg i filen sender trinnet til DeepSeek",
       log == [("deepseek", "deepseek-v4-pro")], log)
    log = spor(c)
    c.hjerne_kald("kategori", "std", "tekst", 100)    # et andet trin
    ok("G2 et trin UDEN valg kører videre på den daglige model",
       log == [("daglig", None)], log)

    c = med_fil({"hjerner": {"omskriv": {"model": "gemini-3.6-flash"}}})
    log = spor(c)
    c.hjerne_kald("omskriv", "std", "tekst", 100)
    ok("G3 et Gemini-valg i filen går til Google",
       log == [("gemini", "gemini-3.6-flash")], log)

    # Et trin med sin EGEN udbyder, forskellig fra den daglige. Det er hele
    # grunden til, at feltet `udbyder` findes pr. trin.
    c = med_fil({"hjerner": {"omskriv": {"model": "gemini-3.6-flash"}}})
    c.HJERNER_STATUS = midl_h / "status.json"
    c.skriv_hjerne_status()
    d = json.loads((midl_h / "status.json").read_text(encoding="utf-8"))
    ok("G4 det trin står som gemini, mens resten står som deepseek",
       d["hjerner"]["omskriv"]["udbyder"] == "gemini"
       and d["hjerner"]["kategori"]["udbyder"] == "deepseek",
       (d["hjerner"]["omskriv"]["udbyder"], d["hjerner"]["kategori"]["udbyder"]))
    ok("G5 og det er mærket som en egen model",
       d["hjerner"]["omskriv"]["egen_model"] is True
       and d["hjerner"]["kategori"]["egen_model"] is False)

    # En død model må siges ÉN gang, ikke 500. brief-trinnet kaldes én gang pr.
    # artikel, og en gang mere når redaktøren kræver omskrivning.
    c = med_fil({"hjerner": {"brief": {"model": "gemini-3.6-flash"}}})
    log = spor(c)

    def sprael(*a, **k):
        raise RuntimeError("nej")
    c.kald_gemini_model = sprael
    baand = io.StringIO()
    with contextlib.redirect_stdout(baand):
        for _ in range(20):
            c.hjerne_kald("brief", "std", "tekst", 100)
    ud = baand.getvalue()
    # En forbigående fejl må ikke smide redaktionens valg væk med det samme -
    # men den må heller ikke give 500 forsøg. Grænsen er tre.
    ok("G6 en forbigående fejl prøves højst tre gange, ikke 20",
       ud.count("RuntimeError") == c.MODEL_FEJL_GRAENSE == 3,
       f"{ud.count('RuntimeError')} forsøg, grænse {c.MODEL_FEJL_GRAENSE}")
    ok("G6b og den siger klart, hvornår den giver op for resten af kørslen",
       ud.count("RESTEN AF KØRSLEN") == 1, ud.count("RESTEN AF KØRSLEN"))
    ok("G7 de følgende 17 kald går direkte til den daglige model",
       log == [("daglig", None)] * 20, len(log))

    # Et 404 betyder "den model findes ikke for dig". Der er ingen grund til at
    # prøve igen - og ingen grund til at bruge tre kald på at finde ud af det.
    c = med_fil({"hjerner": {"brief": {"model": "gemini-3.6-flash"}}})
    log = spor(c)
    import urllib.error as _ue

    def afvis(*a, **k):
        raise _ue.HTTPError("u", 404, "Not Found", None, None)
    c.kald_gemini_model = afvis
    baand = io.StringIO()
    with contextlib.redirect_stdout(baand):
        for _ in range(4):
            c.hjerne_kald("brief", "std", "tekst", 100)
    ud = baand.getvalue()
    ok("G8 en afvisning (404) opgives med det samme, ikke efter tre forsøg",
       ud.count("HTTPError") == 1, ud.count("HTTPError"))
    ok("G8b og den siger, at modellen afviste os",
       "afviste os" in ud, repr(ud[:120]))
    # To trin med SAMME model. Én forbigående fejl i det første må ikke kaste
    # valget væk for det andet - det var det, den første udgave gjorde.
    c = med_fil({"hjerner": {"brief": {"model": "gemini-3.6-flash"},
                             "omskriv": {"model": "gemini-3.6-flash"}}})
    log = spor(c)
    kald = {"n": 0}

    def fejl_foerste_gang(s, b, t, mo):
        kald["n"] += 1
        if kald["n"] == 1:
            raise RuntimeError("hikke")
        log.append(("gemini", mo))
        return "svar"
    c.kald_gemini_model = fejl_foerste_gang
    with contextlib.redirect_stdout(io.StringIO()):
        c.hjerne_kald("brief", "std", "tekst", 100)      # fejler
        c.hjerne_kald("omskriv", "std", "tekst", 100)    # skal stadig prøve
    ok("G9 én forbigående fejl i ét trin kaster ikke valget væk for et andet",
       log == [("daglig", None), ("gemini", "gemini-3.6-flash")], log)

    # Fejl i TRÆK, ikke fejl i alt. Tre spredte hikke blandt hundrede lykkede
    # kald må ikke kassere redaktionens valg — og loggen må ikke påstå
    # "fejlede 3 gange i træk", når den ikke gjorde.
    c = med_fil({"hjerner": {"brief": {"model": "gemini-3.6-flash"}}})
    log = spor(c)
    tur = {"n": 0}

    def hikke_hver_tredje(s, b, t, mo):
        tur["n"] += 1
        if tur["n"] % 3 == 1:            # fejler kald 1, 4, 7, 10 …
            raise RuntimeError("hikke")
        log.append(("gemini", mo))
        return "svar"
    c.kald_gemini_model = hikke_hver_tredje
    baand = io.StringIO()
    with contextlib.redirect_stdout(baand):
        for _ in range(30):
            c.hjerne_kald("brief", "std", "tekst", 100)
    ud = baand.getvalue()
    ok("G10 spredte fejl opgiver ikke modellen",
       "RESTEN AF KØRSLEN" not in ud, ud[-140:])
    ok("G10b og de lykkede kald bruger stadig den valgte model",
       log.count(("gemini", "gemini-3.6-flash")) == 20,
       log.count(("gemini", "gemini-3.6-flash")))

    for daarlig in ({"hjerner": {"omskriv": {"model": 5}}},
                    {"hjerner": {"omskriv": {"model": "   "}}},
                    {"hjerner": {"omskriv": {}}},
                    {"hjerner": {}},
                    {}):
        c = med_fil(daarlig)
        log = spor(c)
        try:
            c.hjerne_kald("omskriv", "std", "tekst", 100)
            ok(f"G vrøvl {str(daarlig)[:26]:28} falder til den daglige",
               log == [("daglig", None)], log)
        except Exception as e:
            ok(f"G vrøvl {str(daarlig)[:26]:28} falder til den daglige",
               False, f"{type(e).__name__}: {e}")
finally:
    import shutil as _sh
    _sh.rmtree(midl_h, ignore_errors=True)

print("== H. status-skrivning må ikke kunne vælte et crawl ==")
c = indlaes()
midl_x = Path(tempfile.mkdtemp(prefix="proeve-vaelt-"))
try:
    # En enkelt latin-1-apostrof i et af arbejdsloopets dokumenter gav før
    # UnicodeDecodeError - og den er en ValueError, ikke en OSError.
    (midl_x / "_redaktion").mkdir()
    (midl_x / "_redaktion" / "opgavekoe.md").write_bytes(b"Overskrift med \xe9\n")
    (midl_x / "data").mkdir()
    c.ROOT = midl_x
    c.HJERNER_STATUS = midl_x / "data" / "status.json"
    baand = io.StringIO()
    with contextlib.redirect_stdout(baand):
        c.skriv_hjerne_status()
    # Ikke "den kastede ikke" — den skal også have SKREVET filen. Fangede vi
    # kun OSError, ville UnicodeDecodeError ryge op i det ydre værn, og
    # statusfilen ville aldrig blive skrevet. Panelet ville stå med gamle tal.
    ok("H1 en ulæselig .md-fil stopper ikke resten af filen",
       (midl_x / "data" / "status.json").exists(), repr(baand.getvalue()[:120]))
    ok("H2 og den siger hvilken fil det var",
       "opgavekoe.md" in baand.getvalue(), repr(baand.getvalue()[:120]))
    # Kan filen slet ikke skrives, skal kørslen stadig fortsætte. `skriv_...`
    # er noget af det FØRSTE main() gør, så en fejl her ville betyde: ingen
    # feeds hentet, ingen artikler, intet commit — for et panel-felt.
    c2 = indlaes()
    c2.HJERNER_STATUS = Path("/proc/kan-ikke-skrives/status.json")
    baand = io.StringIO()
    try:
        with contextlib.redirect_stdout(baand):
            c2.skriv_hjerne_status()
        sprang = False
    except Exception as fejl:
        sprang = f"{type(fejl).__name__}: {fejl}"
    ok("H3 en umulig skrivesti vælter ikke kørslen",
       sprang is False and "kunne ikke skrive hjerne-status" in baand.getvalue(),
       sprang or repr(baand.getvalue()[:120]))
finally:
    import shutil as _sh2
    _sh2.rmtree(midl_x, ignore_errors=True)

print("== I. arbejdsloopets tekst må ikke gå tabt ==")
# Panelet er eneste sted, de seks dokumenter kan læses og redigeres, og et tryk
# på Gem skriver textarea-indholdet ned på disken. Skriver crawleren tomme
# felter, fordi den ikke kunne læse en fil, står redaktionen med et tomt vindue
# og kan slette 62 kB opgavekø med ét klik.
midl_i = Path(tempfile.mkdtemp(prefix="proeve-loop-"))
try:
    (midl_i / "_redaktion").mkdir()
    (midl_i / "data").mkdir()

    def kør(filer):
        """filer: navn -> bytes (eller None for 'findes ikke'). Returnerer JS-data."""
        for _, fil, *_r in c.ARBEJDS_DOKUMENTER:
            sti = midl_i / "_redaktion" / fil
            if fil in filer and filer[fil] is not None:
                sti.write_bytes(filer[fil])
            elif sti.exists():
                sti.unlink()
        cc = indlaes()
        cc.ROOT = midl_i
        cc.HJERNER_STATUS = midl_i / "data" / "hjerner-status.json"
        cc._gammel_loop_cache = None
        baand = io.StringIO()
        with contextlib.redirect_stdout(baand):
            cc.skriv_hjerne_status()
        js = midl_i / "data" / "hjerne-data.js"
        d = None
        if js.exists():
            d = json.loads(js.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";"))
        return d, baand.getvalue()

    c = indlaes()
    ALLE = {fil: f"tekst i {fil}\n".encode() for _, fil, *_ in c.ARBEJDS_DOKUMENTER}
    d, _ = kør(ALLE)
    ok("I1 med alle seks filer står teksten i JS-filen",
       d and all(x["indhold"] for x in d["arbejdsloop"]),
       d and [x["noegle"] for x in d["arbejdsloop"] if not x["indhold"]])
    # Værnet læser data/hjerne-data.js. Den SKAL findes i repoet, for det er
    # den, workflow'en committer og panelet læser. (hjerner-status.json viste
    # sig også at ligge i git — de to skrives altid sammen, så det er fint;
    # men JS-filen er den, alle læser, og derfor den, værnet skal stole på.)
    ok("I2 filen, værnet læser, findes i repoet",
       (REPO / "data" / "hjerne-data.js").exists(),
       "uden data/hjerne-data.js kan intet bæres frem")

    # Nu bliver ÉN fil ulæselig. De fem andre kan læses, så det gamle
    # alt-eller-intet-værn ville have skrevet den ene tom.
    daarlig = dict(ALLE)
    daarlig["opgavekoe.md"] = b"Overskrift med \xe9\n"
    d2, log2 = kør(daarlig)
    kø = [x for x in (d2 or {}).get("arbejdsloop", []) if x["fil"] == "opgavekoe.md"]
    ok("I3 én ulæselig fil får den forrige udgaves tekst, ikke et tomt felt",
       kø and kø[0]["indhold"] == "tekst i opgavekoe.md\n", kø and repr(kø[0]["indhold"]))
    ok("I4 og loggen siger, at den forrige udgave blev brugt",
       "bruger den forrige udgave af opgavekoe.md" in log2, repr(log2[-200:]))
    # Og den skal LÅSES. Vi ved ikke, hvad der står i filen nu — kunne
    # redaktionen redigere den fremførte tekst og trykke Gem, ville panelet
    # skrive en gammel udgave oven i en fil, der måske bare var låst et øjeblik.
    ok("I3b den fremførte tekst kan ikke redigeres i panelet",
       kø and kø[0]["kan_rettes"] is False, kø and kø[0]["kan_rettes"])
    ok("I3c og beskrivelsen siger hvorfor",
       kø and "KAN IKKE RETTES NU" in kø[0]["beskrivelse"], kø and kø[0]["beskrivelse"][:80])
    andre = [x for x in (d2 or {}).get("arbejdsloop", []) if x["fil"] != "opgavekoe.md"]
    ok("I3d de læselige dokumenter er stadig redigerbare",
       any(x["kan_rettes"] for x in andre),
       [(x["fil"], x["kan_rettes"]) for x in andre])

    # Et fremført, redigerbart dokument må IKKE klippes ved 30 kB. Det er den
    # eneste udgave, systemet har — er filen rigtigt tabt, ville alt over
    # grænsen være væk for altid. Lås ja, klip nej.
    stor = ("## Kø\n\n" + ("- punkt\n" * 3000) + "\n---\n" + "x" * 20000)
    (midl_i / "data" / "hjerne-data.js").write_text(
        "window.HJERNE_STATUS = " + json.dumps(
            {"arbejdsloop": [{"noegle": "opgavekoe", "indhold": stor,
                              "findes": True}]}, ensure_ascii=False) + ";\n",
        encoding="utf-8")
    d_stor, _ = kør({**ALLE, "opgavekoe.md": b"\xe9"})
    koe_stor = [x for x in d_stor["arbejdsloop"] if x["noegle"] == "opgavekoe"][0]
    ok("I3e den fremførte kø er hel, ikke klippet ved 30 kB",
       len(koe_stor["indhold"]) == len(stor),
       f"{len(koe_stor['indhold'])} af {len(stor)} tegn")
    ok("I5 de fem andre er uberørte",
       d2 and all(x["indhold"] for x in d2["arbejdsloop"]),
       d2 and [x["noegle"] for x in d2["arbejdsloop"] if not x["indhold"]])

    # Forsvinder ALLE seks, bærer værnet dem alle frem. Teksten må ikke gå tabt,
    # heller ikke når hele mappen er væk.
    d3, log3 = kør({fil: None for fil in ALLE})
    ok("I6 forsvinder alle seks, bæres al teksten frem",
       d3 and all(x["indhold"] for x in d3["arbejdsloop"]),
       d3 and [x["noegle"] for x in d3["arbejdsloop"] if not x["indhold"]])
    ok("I7 og hver enkelt siges højt", log3.count("bruger den forrige udgave") == 6,
       log3.count("bruger den forrige udgave"))

    # Sidste net: en forrige status med tekst, men under NAVNE vi ikke kender
    # længere (fx et omdøbt dokument). Så er der ingenting at bære frem, og
    # filen skal blive, som den er, i stedet for at blive tømt.
    (midl_i / "data" / "hjerne-data.js").write_text(
        'window.HJERNE_STATUS = {"arbejdsloop": [{"noegle": "gammelt_navn", '
        '"indhold": "vigtig tekst", "findes": true}]};\n', encoding="utf-8")
    foer = (midl_i / "data" / "hjerne-data.js").read_text(encoding="utf-8")
    d4, log4 = kør({fil: None for fil in ALLE})
    ok("I8 kan intet bæres frem, bliver filen ikke skrevet om",
       (midl_i / "data" / "hjerne-data.js").read_text(encoding="utf-8") == foer,
       "filen blev tømt")
    ok("I9 og det siges højt", "beholder den forrige hjerne-status" in log4,
       repr(log4[-160:]))

    # Et frisk repo UDEN nogen tidligere status skal stadig skrives - værnet må
    # ikke spærre for den allerførste kørsel.
    (midl_i / "data" / "hjerne-data.js").unlink()
    (midl_i / "data" / "hjerner-status.json").unlink(missing_ok=True)
    d5, _ = kør({fil: None for fil in ALLE})
    ok("I10 et frisk repo uden tidligere status bliver stadig skrevet",
       d5 is not None and all(not x["indhold"] for x in d5["arbejdsloop"]),
       "den allerførste kørsel skal kunne skrive filen")

    # Klip-beskeden skal navngive den fil, der blev klippet — ikke altid
    # arbejdslog.md. En henvisning til den forkerte fil sender redaktionen ud
    # at lede det forkerte sted.
    lang = "start\n" + ("- linje\n" * 6000) + "\n---\nrest"
    cK = indlaes()
    k1 = cK._klip_ved_sektion(lang, fil="analyse-seneste.md")
    ok("I11 klip-beskeden navngiver den klippede fil",
       "analyse-seneste.md" in k1 and "arbejdslog.md" not in k1, k1[-90:])
    k2 = cK._klip_ved_sektion(lang)
    ok("I12 og uden argument peger den stadig på loggen",
       "arbejdslog.md" in k2, k2[-90:])
finally:
    import shutil as _sh3
    _sh3.rmtree(midl_i, ignore_errors=True)

print("== F. status-filen skrives også på GitHubs servere ==")
c = indlaes()
midl = Path(tempfile.mkdtemp(prefix="proeve-modelvalg-"))
try:
    c.HJERNER_STATUS = midl / "hjerner-status.json"
    os.environ["GITHUB_ACTIONS"] = "true"
    c.skriv_hjerne_status()
    ok("F1 JSON-filen bliver skrevet på Actions", c.HJERNER_STATUS.exists())
    js = midl / "hjerne-data.js"
    ok("F2 JS-filen bliver skrevet på Actions", js.exists())
    if c.HJERNER_STATUS.exists():
        d = json.loads(c.HJERNER_STATUS.read_text(encoding="utf-8"))
        ok("F3 filen siger hvilke nøgler der findes",
           d.get("gemini_tilgaengelig") is True and d.get("deepseek_tilgaengelig") is True, d.get("udbyder"))
        ok("F4 den daglige udbyder er DeepSeek, når begge nøgler er sat",
           d.get("udbyder") == "deepseek" and d.get("daglig_model") == c.DEEPSEEK_MODEL,
           (d.get("udbyder"), d.get("daglig_model")))
        ok("F5 hvert trin siger hvem det kalder",
           all(h.get("udbyder") == "deepseek" for h in d["hjerner"].values()),
           [n for n, h in d["hjerner"].items() if h.get("udbyder") != "deepseek"][:3])
        ok("F6 alle 14 trin er med", len(d["hjerner"]) == 14, len(d["hjerner"]))
    # Og uden nøgler skal den sige "ingen" — ikke lade som om Gemini kører.
    os.environ.pop("GITHUB_ACTIONS", None)
    c3 = indlaes(gemini="", deepseek="")
    c3.HJERNER_STATUS = midl / "tom.json"
    c3.skriv_hjerne_status()
    d3 = json.loads((midl / "tom.json").read_text(encoding="utf-8"))
    ok("F7 uden nøgler står der ingen udbyder",
       d3.get("udbyder") == "ingen" and d3.get("deepseek_tilgaengelig") is False, d3.get("udbyder"))
    # Dette er fejlen fra før, spejlet: `daglig` falder tilbage til Gemini-navnet,
    # når der ikke er nogen udbyder. Skrev vi model_udbyder(daglig) pr. trin,
    # ville alle 14 kort påstå "gemini" på en maskine uden en Google-nøgle.
    ok("F8 og ingen af de 14 trin påstår at køre på Google",
       all(h.get("udbyder") == "" for h in d3["hjerner"].values()),
       sorted({h.get("udbyder") for h in d3["hjerner"].values()}))
finally:
    os.environ.pop("GITHUB_ACTIONS", None)
    import shutil
    shutil.rmtree(midl, ignore_errors=True)

print()
print(f"GROENNE {groen} · ROEDE {roed}")
sys.exit(1 if roed else 0)
