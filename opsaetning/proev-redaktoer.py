#!/usr/bin/env python3
"""Sammenlign et redaktionsmøde med pointlisten uden at udgive eller sende noget."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import redaktion
import redaktoer_agent as agent
from crawler import DEEPSEEK_MODEL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/articles.json")
    parser.add_argument("--rapport", type=Path, required=True, help="Gem kun prøverapporten her")
    parser.add_argument("--live", action="store_true", help="Tillad afgrænsede model- og kildekald med DEEPSEEK_API_KEY")
    args = parser.parse_args()
    data = json.loads(args.data.read_text())
    nu = redaktion.dato({"dato": data.get("opdateret")}) or datetime.now(timezone.utc)
    artikler = data["artikler"]
    report = {"type": "proeve_uden_udgivelse", "datatid": agent.iso(nu), "model": DEEPSEEK_MODEL,
              "regelbaseret": [{"link": a["link"], "rubrik": a["rubrik"]} for a in redaktion.udvaelg(artikler, antal=3, nu=nu)],
              "status": "uden_modelkald", "bemærkning": "Der er ikke målt redaktionel kvalitet uden en modelkørsel."}
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if args.live and not key:
        report.update(status="mangler_noegle", bemærkning="DEEPSEEK_API_KEY mangler. Ingen model- eller kildekald udført.")
    elif args.live:
        e = agent.Redaktion(artikler, agent.laes_json(ROOT / "data/redaktoer-hukommelse.json", {}),
            (ROOT / "opsaetning/redaktoer.md").read_text(), nu,
            lambda messages, tools: agent.deepseek_kald(key, DEEPSEEK_MODEL, messages, tools))
        try:
            p = e.koer()
            report.update(status="agentplan", agentplan=p, agentvalg=[{"link": e.artikler[s["id"]]["link"],
                "rubrik": e.artikler[s["id"]]["rubrik"], "begrundelse": s["begrundelse"],
                "nyt_siden_sidst": s["nyt_siden_sidst"], "skriveopgave": s["skriveopgave"]} for s in p["udvalgte"]],
                bemærkning="Kun redaktionsmødet er kørt. Artikler er ikke omskrevet, slutkontrolleret eller udgivet.")
        except Exception as error:
            report.update(status="fejl", bemærkning=type(error).__name__)
        report.update(modelkald=e.antal_kald, kildehentninger=len(e.laeste), vaerktoejer=e.log)
    agent.gem_json(args.rapport, report)
    print(f"{report['status']}: {args.rapport}")
    print(report["bemærkning"])
    return 2 if report["status"] in ("mangler_noegle", "fejl") else 0


if __name__ == "__main__":
    sys.exit(main())
