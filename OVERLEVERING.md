# Overlevering: AI-nyheder (ainyheder.com)

Du overtager en igangværende opgave fra en anden Claude-session. Læs det hele, før du gør noget. Brugeren hedder Torben, taler dansk og er ikke programmør — forklar altid i klart, jordnært dansk, og gør tingene for ham i stedet for at bede ham om at kode.

## Hvad projektet er

Et automatisk dansk AI-nyhedsmagasin: **https://ainyheder.com** (GitHub Pages, repo `ainyheder/AI-nyheder`, main-branch, root). En GitHub Action (`.github/workflows/crawl.yml`) kører `crawler.py` hver 6. time + ved push:

1. Crawler ~15 internationale kilder (TechCrunch, The Verge, Ars Technica, arXiv m.fl. — se `feeds.json`)
2. Gemini (`gemini-3.5-flash-lite`, fallback `gemini-3.5-flash`) genfortæller hver artikel på ultra-kort letlæst dansk: rubrik, resumé, sektioner, "Hvad betyder det for dig?", nøgletal, billedmotiv
3. En **redaktør-agent** kvalitetstjekker hvert udkast og kan kræve én omskrivning
4. Gemini image (`gemini-3.1-flash-lite-image`, fallback `gemini-2.5-flash-image`) laver ét 16:9-billede pr. artikel (husstil v5: cinematisk 3D-render, se nedenfor)
5. Ugentligt: "Ugens overblik" (`uge.html`, genereres fre-søn) + nyhedsbrev sendes automatisk via **Buttondown API**
6. Committer `data/`, `feed.xml`, `uge.html`, `feed-uge.xml` tilbage til repoet

Alt er Python-stdlib (ingen pip-pakker undtagen pillow i workflow). Cache pr. artikel-link i `data/`; `GENKOER_ALT`-input på workflow_dispatch kan genkøre alt/filtreret.

## Arbejdsgang med Torben (VIGTIGT)

- Filerne ligger lokalt på hans Mac: **`/Users/torben/Claude/Projects/AI NEWS/`** (forbundet mappe via desktop-appen). Du redigerer filer i dit eget miljø og afleverer dem til mappen (SendUserFile + device_commit_files eller tilsvarende).
- **Torben pusher selv** via GitHub Desktop (Fetch/Pull → commit → Push). Mind ham om det, når filer er klar.
- `device_commit_files` afviser stier under `.github/workflows/` — levér i så fald filen som fx `crawl_yml_ny.txt` og brug device_bash med `cat > .github/workflows/crawl.yml`.
- device_bash kan ikke slette filer — flyt til en `_to_delete/`-mappe i stedet.
- Du kan styre hans Chrome via claude-in-chrome-værktøjerne (han er typisk logget ind i Cloudflare, Buttondown, GitHub). Ved "gemte ikke"-problemer i webapps: klik Save via find-element (ikke koordinater), genindlæs siden og verificér med screenshot.

## SIKKERHEDSREGLER (ufravigelige)

- Indtast ALDRIG adgangskoder, API-nøgler eller betalingsoplysninger i felter — det gør Torben selv.
- API-nøgler må aldrig sendes gennem chatten. Hemmeligheder ligger KUN i GitHub Actions secrets: `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `BUTTONDOWN_API_KEY`.
- Opret aldrig konti på hans vegne. Køb/opgraderinger: guid ham, men han taster selv betaling.

## Design-DNA

- Farver: baggrund `#f4f2ec` (creme), blæk `#191714`, accent-lilla `#5b4bf0`, linjer `#e2ddd2`. Fonte: Fraunces (900, display) + Inter (UI). Alle sider deler denne skabelon (topbar, tilbage-knap, Cloudflare-beacon token `fda17dd7ade34a579f4ec6d615265fa6`).
- Forsiden `index.html`: Magasin-visning er standard; "Overblik"-visning er tekst-kolonner pr. kategori. Menu: **Nyheder** (dropdown med checkbokse — kun pilen åbner dropdown), **Forskning**, Ugens overblik, Lær AI. LIGE NU-ticker øverst. Deep links `#a=<link>`; delknapper pr. artikel.
- Kategorier: Lanceringer, Hverdags-AI, Penge & marked, Samfund & etik, Politik & jura + **Forskning** (arXiv-artikler vises KUN under Forskning, aldrig under Nyheder/Alle). Kategorien Benchmarks er nedlagt.
- Undersider: `om.html`, `laer.html`, `ordbog.html`, `guide-igang/prompts/sikkerhed.html`, `prompts.html`, `faq.html`, `uge.html` (genereres af crawleren!), `tak.html`, `velkommen.html`, `404.html`. Ret aldrig uge.html direkte — ret skabelonen `_uge_side_html` i crawler.py.
- Faneblads-titler: alle sider starter med "AI-nyheder.com" (forsiden hedder kun det).
- Billedstil v5 (i `lav_billeder`): tekst-AI'en skriver et konkret `billedmotiv` (art director, 1-3 genstande, ingen mennesker/tekst); render-prompten kræver cinematisk 3D, naturlige farver tonet i kategorifarven, lille lilla detalje, diskrete firmafarve-nik (aldrig logoer), og — nyeste regel — **helt ren studiebaggrund, ingen rum/serverrum/miljøer**. Stilversion styres af `BILLED_STIL_VERSION = "v5"`; bump til v6 = fuld (dyr) regenerering af alle billeder — gør det kun hvis Torben beder om det.

## Nyhedsbrev (Buttondown)

- Konto: brugernavn `AInyheder`, navn "AI-nyheder", gratis plan (≤100 abonnenter). Afsendernavn: "AI-nyheder".
- Crawleren sender ugebrevet via API (`_send_nyhedsbrev`, status `about_to_send`) — første automatiske udsendelse fredag 31/7. RSS-to-email bruges IKKE (koster ekstra).
- Redirects sat: efter tilmelding → `/tak.html`, efter bekræftelse → `/velkommen.html`. Reminder efter 24 t, welcome-mail, cleanup: alle slået til.
- Kendt begrænsning: selve bekræftelsesmailen er Buttondowns engelske standardskabelon og kan først tilpasses på Standard-planen (9 $/md). Torben har accepteret det indtil videre. Bekræftelsesmails kan være ~5 min forsinkede (tak.html advarer om det).
- Status ved overlevering: Torbens egen testtilmelding (soemandtorben@gmail.com) stod som Unactivated; han har modtaget reminder-mailen — **tjek om han fik klikket bekræftelseslinket og landede på velkommen.html**.

## Status lige nu / hængepartier

1. **Muligvis upushet batch** på hans Mac: nye faneblads-titler (12 HTML-filer), tak/velkommen-sider, opdateret crawler.py (baggrunds-regel + uge-titel). Spørg om han har pushet; ellers mind ham om det.
2. **Afventer svar fra Torben:** vil han have en lille tæller på forsiden ("131 artikler · 53 nye i dag")? Tilbudt, ikke besvaret.
3. **Tilbudt, ikke besvaret:** rulle "AI."-logoet (sort Fraunces "AI" + lilla punktum på creme, ligger som `assets/nyhedsbrev_ikon.png`) ud som favicon/og-billede på sitet.
4. Fredag 31/7: første automatiske nyhedsbrev — verificér gerne i Actions-loggen at nyhedsbrevs-steppet kørte, og at mailen kom frem.
5. Dvale-liste (nævnt, ikke bestilt): statiske artikelsider for SEO, niveau 3-4 AI-features (lyd-brief, "Spørg nyhederne"-chatbot, auto-opslag til sociale medier), Værktøjsoversigt-side, invitation af hans makker til repoet, Google Cloud budgetalarm.
6. Fakta til hurtige svar: arkivet ligger stabilt på ~131 artikler (~50 nye/døgn); Forskning-fanen rummer ~32. Hvis Torben synes "der er færre nyheder", er forklaringen normalt at Forskning ikke længere står under Nyheder.

## Nyttige tekniske noter

- GSC er verificeret (DNS TXT), sitemap indsendt. Cloudflare styrer DNS; HTTPS på GitHub Pages virker.
- Test lokalt med `python3 -m http.server` + Playwright (chromium ligger i `/opt/pw-browsers`); brug `domcontentloaded`, ikke `networkidle` (CF-beacon holder forbindelsen åben).
- Efter ændringer i crawler.py: kør altid `python3 -c "import ast; ast.parse(open('crawler.py').read())"` før levering.
- Live-data kan altid tjekkes på `https://ainyheder.com/data/articles.json`.

Start med at hilse på Torben, bed ham forbinde mappen `/Users/torben/Claude/Projects/AI NEWS` (og Chrome hvis nødvendigt), og spørg hvad han vil arbejde på — eller saml op på hængeparti 1-3 ovenfor.
