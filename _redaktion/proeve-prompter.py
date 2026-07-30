#!/usr/bin/env python3
"""Prøve: siger de 14 hjerners instrukser det SAMME om husreglerne?

Kør den fra repoets rod:  python3 _redaktion/proeve-prompter.py

Prompterne blev læst igennem i hånden 30.07, og der lå tre slags drift:
rubrik-grænsen var tre forskellige tal, "skriv AI"-reglen manglede i fem
hjerner, og der var TO art directors (briefets indbyggede billedmotiv-felt og
motiv-hjernen), som var drevet fra hinanden. Den her prøve gør, at den
gennemgang aldrig skal gentages i hånden: driver en regel igen, går den rød.

Prøver kun STANDARD-prompterne i crawler.py. Panelets overstyringer i
hjerner.json er redaktionens ansvar - dem retter maskinen ikke i.
"""
import importlib.util
import os
import re
import sys
from pathlib import Path

REPO = Path(os.environ.get("PROEVE_REPO", Path(__file__).resolve().parent.parent))
os.environ.setdefault("GEMINI_API_KEY", "x")
spec = importlib.util.spec_from_file_location("c_pr", REPO / "crawler.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

groen = roed = 0


def ok(navn, betingelse, ekstra=""):
    global groen, roed
    if betingelse:
        groen += 1
    else:
        roed += 1
        print(f"  ROED  {navn} {ekstra}")


P = c._standard_prompts()
ok("0 alle 14 hjerner har en standardprompt",
   len(P) == 14 and all(len(v) > 100 for v in P.values()),
   sorted((k, len(v)) for k, v in P.items() if len(v) <= 100))

print("== A. rubrik-grænsen er ét tal: 8 ord ==")
# Grænsen stod som 9 i omskriv og navngiv, 8 i brief og redaktoer. navngiv
# kunne altså skrive en rubrik, redaktøren ville have afvist - og ingen
# tjekkede den igen.
# youtube var glemt i første omgang - dens rubrik stod stadig på 9 ord.
RUBRIK_HJERNER = ["omskriv", "brief", "redaktoer", "navngiv", "youtube"]
for navn in RUBRIK_HJERNER:
    tekst = P[navn].lower()
    ok(f"A {navn:10} siger max 8 ord",
       re.search(r"max\s+8\s+ord", tekst) is not None)
    ok(f"A {navn:10} siger IKKE 9 ord",
       re.search(r"\b9\s+ord", tekst) is None,
       [m for m in re.findall(r".{20}9 ord.{10}", tekst)][:1])

print("== B. 'skriv AI, aldrig kunstig intelligens' står i alle læservendte hjerner ==")
# dublet, motiv og kategori skriver ikke læservendt prosa (kategori svarer
# kun med et kategorinavn og et tal) - alle andre gør. Reglen kan være ombrudt
# ("kunstig\nintelligens"), så linjeskift foldes sammen før søgningen.
LAESERVENDTE = [n for n in P if n not in ("dublet", "motiv", "kategori")]
for navn in LAESERVENDTE:
    flad = " ".join(P[navn].lower().split())
    # RETNINGEN skal med: en mutation, der vendte reglen om ("skriv altid
    # kunstig intelligens - aldrig AI"), overlevede den første udgave af
    # prøven, fordi den kun ledte efter de to ord hver for sig.
    ok(f"B {navn:15} har AI-reglen — med den rigtige vej rundt",
       re.search(r'(altid "ai"|forbudt \(skriv "ai"\)|skriv "ai"|kald teknologien "ai")', flad)
       is not None
       and re.search(r'(altid|kald teknologien)\s+"kunstig intelligens"', flad) is None,
       f"{len(P[navn])} tegn uden reglen")

print("== C. der er præcis ÉN art director ==")
# Briefets indbyggede billedmotiv-felt manglede baggrunds-reglen og ville
# aldrig få humor-instruksen fra hjerner.json. Kommer feltet tilbage i
# briefet, er der to art directors igen.
ok("C1 briefets prompt beder IKKE om billedmotiv",
   "billedmotiv" not in P["brief"].lower())
ok("C2 og koden læser ikke feltet fra brief-svaret",
   'a["billedmotiv"] = str(r.get("billedmotiv"' not in
   (REPO / "crawler.py").read_text(encoding="utf-8"))
ok("C3 motiv-hjernen findes og kræver studiebaggrund",
   "studiebaggrund" in P["motiv"].lower())
ok("C4 og forbyder mennesker og tekst i billedet",
   "ingen mennesker" in P["motiv"].lower() and "tekst" in P["motiv"].lower())

print("== D. navne-reglen står der, hvor rubrikker skrives ==")
for navn in ("omskriv", "brief", "navngiv", "redaktoer", "opslag"):
    ok(f"D {navn:10} kræver navne",
       "ved navn" in P[navn].lower() or "nævne" in P[navn].lower()
       or "navnet" in P[navn].lower())
# og forbuddet mod gigant-omskrivninger, hvor rubrikken FØDES
for navn in ("omskriv", "brief"):
    ok(f"D {navn:10} forbyder gigant-omskrivninger",
       "gigant" in P[navn].lower() and "forbudt" in P[navn].lower())

print("== E. redaktøren håndhæver det, briefet lover ==")
ok("E1 redaktøren tjekker navne i rubrikken",
   "navn" in P["redaktoer"].lower() and "gigant" in P["redaktoer"].lower())
ok("E2 redaktøren afviser vage sammenligninger uden tal",
   "markant bedre" in P["redaktoer"].lower())
ok("E3 men kun når der slet ingen tal er — ellers koster afvisninger penge",
   "er alt fint" in P["redaktoer"].lower() or "helt fint" in P["redaktoer"].lower())
ok("E4 og godkender stadig som udgangspunkt",
   "Godkend alt" in P["redaktoer"])

print("== F. småregler ==")
ok("F1 ingen stavefejlen 'heder' i nogen prompt",
   not any(" heder" in p for p in P.values()),
   [n for n, p in P.items() if " heder" in p])
ok("F2 quizzen forbyder at spørgsmålet afslører svaret",
   "indeholde svaret" in P["quiz"].lower())
ok("F3 dagens overblik må levere færre end 5 på en stille dag",
   "færre" in P["dagens_overblik"].lower())
# … og KODEN skal tillade det samme. Prompten sagde "returnér færre", mens
# koden kasserede alt under 5 - så et ærligt 3-punkts svar blev smidt væk,
# og det samme forgæves AI-kald gentaget hele skiftet.
KILDE = (REPO / "crawler.py").read_text(encoding="utf-8")
ok("F3b koden kasserer først under 3 punkter, ikke under 5",
   "if len(punkter) < 3:" in KILDE and "if len(punkter) < 5:" not in KILDE)
ok("F5b redaktøren FÅR detaljerne, som regel 5 henviser til",
   '"detaljer": a.get("detaljer")' in KILDE,
   "regel 5 nævner detaljer, men payloaden sendte dem ikke med")
ok("F5c cachen læser billedmotivet tilbage også uden brief",
   'if gammel.get("billedmotiv"):' in KILDE,
   "ellers opfinder motiv-hjernen et nyt motiv hver kørsel")
# PRÆCISE tal, ikke delstrenge: "max 2400 tegn" indeholder "240", så den
# første udgave af prøven lod en tifold-fejl slippe igennem.
ok("F4 opslag har målbare længder på alle tre varianter",
   all(re.search(rf"max\s+{tal}\s+tegn", P["opslag"]) for tal in (240, 350, 600))
   and not re.search(r"max\s+\d{4,}\s+tegn", P["opslag"]))
ok("F5 alle prompter, der svarer med JSON, siger det udtrykkeligt",
   all("JSON" in p for p in P.values()),
   [n for n, p in P.items() if "JSON" not in p])

print()
print(f"GROENNE {groen} · ROEDE {roed}")
sys.exit(1 if roed else 0)
