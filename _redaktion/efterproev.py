#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hvilket klaret punkt skal efterprøves i dag?

Loopet retter, logger og går videre. Ingen kommer tilbage bagefter og måler,
om rettelsen holdt — og de gange, nogen har gjort det manuelt, viste det sig
flere gange, at rettelsen løste symptomet og lod årsagen stå.

Den her vælger ÉT punkt fra `## Klaret` i opgavekøen. Valget skal være
deterministisk. Er det et skøn, tager sessionen det, der er nemmest at give
et grønt svar, og efterprøvningen bliver til selvros.

Kør fra repoets rod:  python3 _redaktion/efterproev.py

Udfaldskoder: 0 = normalt (uanset om der blev fundet en kandidat),
2 = filen kunne ikke læses. Et "ingen kandidat i dag" er ikke en fejl.
"""
from __future__ import annotations

import datetime
import pathlib
import re
import sys

# Hvorfor to døgn og ikke en uge: crawleren kører nitten gange i døgnet, så en
# rettelse i koden er prøvet af virkeligheden inden for et døgn. Målt 27.07 var
# HELE `## Klaret` under tre døgn gammel (36 punkter, ældste fra 25.07) — en
# uge-grænse ville ikke have udløst noget som helst før om fem dage, og en
# regel, ingen har prøvet, virker ikke. Bliver listen gammel nok til, at der
# altid er kandidater, må tallet gerne sættes op.
MINDST_DAGE = 2

# Et mærke er ikke en fritagelse på livstid. En uafhængig gennemgang 27.07
# pegede på, at "kan ikke måles herfra" ellers ville være den billigste udvej
# OG den endelige — punktet ville aldrig komme tilbage. Derfor får hvert udfald
# en karenstid, hvorefter punktet er kandidat igen.
KARENS_DAGE = {
    "holder": 21,             # holdt sidst; se efter igen om tre uger
    "gik i stykker": 7,       # skrøbeligt sted, kig tit
    "kan ikke måles": 7,      # måske kan det måles næste gang
    "?": 14,                  # et mærke vi ikke kunne tyde
}

# Råber op, når efterslæbet vokser. Én efterprøvning pr. kørsel mod ~12 nye
# klarede punkter i døgnet betyder, at andelen falder stille, hvis ingen ser
# efter. Tællingen er MODNE punkter, der aldrig er efterprøvet — ikke hele
# listen. Ellers ville advarslen lyde hver eneste dag alene fordi køen er ny,
# og en advarsel, der altid lyder, er tapet. Målt 27.07: 2 modne, 34 for nye.
EFTERSLAEB_GRAENSE = 10

ROD = pathlib.Path(__file__).resolve().parent.parent
KOE = ROD / "_redaktion" / "opgavekoe.md"

# Mærket skrives på sin egen linje til sidst i punktet, se arbejdsinstruksen.
# Tolerant med vilje: bliver det skrevet en anelse anderledes i hånden, skal
# punktet stadig genkendes — ellers vælges det igen dagen efter.
# Delt i to led om kolonet: datoen står før, udfaldet efter. Et forsøg på at
# gøre det i ét regulært udtryk fangede aldrig datoen — den var valgfri, og et
# dovent udtryk springer det valgfrie over. Prøven fandt det.
_MAERKE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?\*{0,2}Efterprøvet\b(?P<hoved>[^\n:]*):(?P<hale>[^\n]*)",
    re.M | re.I,
)
_DATO_DK = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")
_DATO_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
# Uden årstal — "målt 26.07 kl. 23:40" er den normale skrivemåde i køen, og to
# punkter var usynlige for efterprøvningen, fordi de kun havde den form.
# Klokkeslæt (15.30 → dag 15, måned 30) og tal som 2.861 falder selv fra:
# de bliver ikke til en gyldig dato.
_DATO_KORT = re.compile(r"(?<![\d.])(\d{2})\.(\d{2})(?![\d.])")


def _i_dag() -> datetime.date:
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Copenhagen")).date()
    except Exception:
        return datetime.date.today()


def _dato(aar: int, maaned: int, dag: int) -> datetime.date | None:
    try:
        return datetime.date(aar, maaned, dag)
    except ValueError:
        return None                      # 31.02 er ikke en dato, bare tal


def _dato_i(tekst: str, i_dag: datetime.date | None = None) -> datetime.date | None:
    """Første dato i punktet. Den står i parentesen lige efter titlen."""
    i_dag = i_dag or _i_dag()
    m = _DATO_DK.search(tekst)
    if m:
        dag, maaned, aar = (int(x) for x in m.groups())
        return _dato(aar, maaned, dag)
    m = _DATO_ISO.search(tekst)
    if m:
        aar, maaned, dag = (int(x) for x in m.groups())
        return _dato(aar, maaned, dag)
    for m in _DATO_KORT.finditer(tekst):
        dag, maaned = (int(x) for x in m.groups())
        d = _dato(i_dag.year, maaned, dag)
        if d is None:
            continue                     # klokkeslæt eller tal, prøv næste
        # En dato i fremtiden uden årstal er sidste år, ikke næste.
        return d if d <= i_dag else _dato(i_dag.year - 1, maaned, dag)
    return None


def maerke_i(punkt: str, i_dag: datetime.date | None = None):
    """(udfald, dato) fra punktets efterprøvningsmærke, eller (None, None)."""
    m = _MAERKE.search(punkt)
    if not m:
        return None, None
    hale = m.group("hale").replace("*", " ").strip().lower()
    udfald = next((n for n in ("gik i stykker", "kan ikke måles", "holder") if n in hale), "?")
    return udfald, _dato_i(m.group("hoved"), i_dag)


def klarede_punkter(raa: str) -> list[str]:
    """Punkterne under `## Klaret`, i den rækkefølge de står i filen."""
    start = re.search(r"^## Klaret\s*$", raa, re.M)
    if not start:
        return []
    resten = raa[start.end():]
    naeste = re.search(r"^## ", resten, re.M)
    blok = resten[:naeste.start()] if naeste else resten
    return [p.strip() for p in re.split(r"\n(?=- \[x\])", blok) if p.strip().startswith("- [x]")]


def titel(punkt: str) -> str:
    m = re.search(r"\*\*(.+?)\*\*", punkt, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else re.sub(r"\s+", " ", punkt[:70])


def vaelg(punkter: list[str], i_dag: datetime.date) -> tuple[str | None, dict]:
    """Ældste punkt, der er modent og ikke i karens. Plus regnskabet."""
    tal = {"i_alt": len(punkter), "i_karens": 0, "uden_dato": 0, "for_ny": 0,
           "kandidater": 0, "modne_uden_maerke": 0, "uden_dato_titler": []}
    kandidater: list[tuple[datetime.date, int, str]] = []
    for nr, p in enumerate(punkter):
        udfald, maerkedato = maerke_i(p, i_dag)
        if udfald is None:
            pass
        elif maerkedato is None:
            tal["i_karens"] += 1         # mærket, men uden læselig dato: lad det ligge
            continue
        elif (i_dag - maerkedato).days < KARENS_DAGE.get(udfald, KARENS_DAGE["?"]):
            tal["i_karens"] += 1
            continue
        d = _dato_i(p, i_dag)
        if d is None:
            tal["uden_dato"] += 1
            tal["uden_dato_titler"].append(titel(p))
            continue
        if (i_dag - d).days < MINDST_DAGE:
            tal["for_ny"] += 1
            continue
        kandidater.append((d, nr, p))
        if udfald is None:
            tal["modne_uden_maerke"] += 1
    tal["kandidater"] = len(kandidater)
    if not kandidater:
        return None, tal
    # Ældste først; ved samme dato den, der står nederst i filen (ældst skrevet).
    kandidater.sort(key=lambda k: (k[0], -k[1]))
    return kandidater[0][2], tal


def main() -> int:
    if not KOE.exists():
        print(f"Fandt ikke {KOE}", file=sys.stderr)
        return 2
    i_dag = _i_dag()
    punkter = klarede_punkter(KOE.read_text(encoding="utf-8"))
    valgt, tal = vaelg(punkter, i_dag)
    print(f"## Klaret: {tal['i_alt']} punkter — {tal['kandidater']} modne, "
          f"{tal['i_karens']} i karens, {tal['for_ny']} under {MINDST_DAGE} døgn, "
          f"{tal['uden_dato']} uden læselig dato")
    for t in tal["uden_dato_titler"]:
        print(f"    uden dato, ses aldrig: «{t}»")
    if tal["modne_uden_maerke"] > EFTERSLAEB_GRAENSE:
        print(f"\n⚠️  {tal['modne_uden_maerke']} punkter er gamle nok til at blive "
              f"efterprøvet og er aldrig blevet det (grænsen er {EFTERSLAEB_GRAENSE}). "
              f"Efterslæbet vokser hurtigere, end én efterprøvning pr. kørsel kan "
              f"indhente. Skriv det i loggen — det er ikke en fejl, du kan rette i dag.")
    if valgt is None:
        print("\nIngen kandidat i dag. Spring efterprøvningen over — det er et "
              "gyldigt svar og skal ikke erstattes af et punkt, du selv finder på.")
        return 0
    d = _dato_i(valgt, i_dag)
    udfald, maerkedato = maerke_i(valgt, i_dag)
    print(f"\nEfterprøv: «{titel(valgt)}»")
    print(f"Klaret {d.strftime('%d.%m.%Y')} — {(i_dag - d).days} døgn siden")
    if udfald:
        print(f"Efterprøvet før ({maerkedato}): {udfald} — karensen er udløbet.")
    print()
    print(valgt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
