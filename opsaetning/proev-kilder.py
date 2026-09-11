#!/usr/bin/env python3
"""Kontrollér aktive offentlige kilder. Ingen AI-kald, filændringer eller udsendelser."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crawler


def main():
    alle = json.loads(crawler.FEEDS_FIL.read_text(encoding='utf-8'))['feeds']
    feeds, slukkede = crawler._aktive_feeds(alle)
    fejl_antal = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        for feed, artikler, fejl in pool.map(crawler.crawl_feed, feeds):
            datoer = [a['dato'] for a in artikler if a.get('dato')]
            seneste = max(datoer).isoformat() if datoer else 'ingen udgivelsesdato'
            if fejl:
                fejl_antal += 1
                print(f"FEJL  {feed['navn']}: {fejl}", flush=True)
            else:
                print(f"OK    {feed['navn']}: {len(artikler)} kandidater · seneste {seneste}", flush=True)
    print(f"\n{len(feeds)-fejl_antal}/{len(feeds)} aktive kilder læst. Pauset: {', '.join(slukkede)}.")
    return 1 if fejl_antal else 0


if __name__ == '__main__':
    sys.exit(main())
