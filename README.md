# AI-nyheder

Danske AI-nyheder med en læsevenlig forside, korte overblik og permanente artikelsider. Siden bruger almindelig HTML, CSS og JavaScript og fungerer direkte på den eksisterende GitHub Pages-opsætning. Der er intet byggetrin.

## Ombygningen, september 2026

Forsiden har en hovedhistorie, et kort overblik, synlig søgning, emnefiltre og valg mellem **Vigtigst først** og **Nyeste først**. Artikelvisningen har større tekst og en begrænset linjebredde. Mobilmenu, tastaturbetjening, delelinks og browserens tilbage/frem understøttes. Læste artikler markeres lokalt; besøgstal ændrer ikke længere udvælgelsen.

Alle eksisterende sider i `artikel/` bruger det fælles læsedesign i `assets/artikel.css`. Deres artikler, kilder, permanente adresser og canonical-links er bevaret. Det store antal ændrede arkivfiler skyldes tilføjelsen af fælles CSS, en tilbagegenvej og tastaturadgang.

## Sådan udvælges nyhederne

`crawler.py` henter kilderne og får AI til at vurdere hver historie. `redaktion.py` validerer vurderingerne og beregner rækkefølgen. Den samme logik bruges til forsiden, brief-kandidater, ugens quiz og billedprioritering.

| Kriterium | Vægt | Spørgsmål |
|---|---:|---|
| Nyhedsværdi | 25 % | Hvad er faktisk nyt? |
| Betydning | 25 % | Hvilke konkrete følger har det for mennesker? |
| Brugbarhed | 20 % | Kan læseren bruge indsigten eller træffe et bedre valg? |
| Dokumentation | 20 % | Hvor godt understøtter det tilgængelige materiale påstanden? |
| Dansk relevans | 10 % | Er der dokumenteret relevans for Danmark, EU eller danske brugere? |

**Modellanceringer er førsteprioritet.** Bekræftede nye AI-modeller og modelversioner får 36 ekstra prioritetspoint og beholder deres nyhedsværdi gennem den første uge. Forskellige modellanceringer straffes mindre for at dele kategori. Almindelige produktfunktioner, plugins, kundecases, tests og rygter tæller ikke som modellanceringer. Det nye filter **Modellanceringer** viser denne forskel.

AI giver hvert kriterium 0–5 og skriver en kort begrundelse samt eventuelle forbehold. Vurderingen bygger på det medsendte kildemateriale; den er ikke en selvstændig faktakontrol. Manglende oplysninger må ikke opfindes. Resultater matches med artikel-id og valideres, før de caches.

Udvælgelsen tager derefter højde for kildens **udgivelsesdato**, og gentagelser af samme kilde, kategori eller hovedaktør får et fradrag. Flere omtaler giver ikke i sig selv flere point. En vigtig forskningshistorie kan fortsat få en hovedplads. Reklameprægede opslag, perifert AI-stof, svagt dokumenterede historier og rygter får ingen hovedplads. På stille dage vises færre udvalgte historier.

En artikel kan blive i overblikket i op til syv døgn efter udgivelsen, selv om den falder ud af kildens RSS-feed. Kilder, der er slået fra, eller har `kun_aktuel`, genindlæses ikke fra arkivet. Hvis samtlige aktive kilder fejler, stoppes kørslen, så den eksisterende udgave bevares.

### Overgang fra gamle vurderinger

Vurderinger gemmes i artiklens `redaktion`-felt med versionsnummer. Version 3 tilføjer et eksplicit `model_lancering`-felt. Version 2-vurderinger og deres forbehold bevares, indtil de kan opdateres. En konservativ tekstanalyse prioriterer eksisterende modellanceringer med det samme. Ved næste kørsel med en fungerende AI-nøgle får op til 120 artikler den nye vurdering, i portioner på 12. Resten fortsætter ved næste kørsel. Artikler helt uden delvurderinger bruger den eksisterende `prio` med den nye modelprioritet og aktualitetslogik. Der skal ikke slettes data eller indstilles nye secrets.

Normalt prioriteres de 40 vigtigste artikler til dyb behandling, og billedbudgettet går til seks udvalgte historier. Et manglende billede giver et almindeligt tekstlayout og påvirker ikke historiens placering.

## Se siden lokalt

Fra projektmappen:

```bash
python3 -m http.server 8000
```

Åbn `http://localhost:8000`. Brug en webserver; dobbeltklik på HTML-filen kan ikke hente JSON-data.

Genberegn forsiden på eksisterende artikler, uden netværk, AI-kald eller udsendelser:

```bash
python3 crawler.py --opdater-forside
```

Kommandoen opdaterer kun `forside`-metadata i `data/articles.json`. Artikeltekster og deres opdateringsdato ændres ikke.

Et fuldt crawl startes med `python3 crawler.py`. Det bruger de konfigurerede API-nøgler og den eksisterende automatisering, herunder eventuelle aktiverede nyhedsbreve og sociale opslag. Til almindelig lokal designkontrol er et fuldt crawl unødvendigt.

## GitHub og automatisk opdatering

Den eksisterende `.github/workflows/crawl.yml` bruges fortsat. Den kører ved push til `main`, manuelt og efter sin tidsplan. Den kører først test af udvælgelsen og derefter crawleren. GitHub Pages serverer filerne fra repoet som hidtil; `CNAME` er bevaret.

Secrets: `DEEPSEEK_API_KEY` eller `GEMINI_API_KEY` til teksten. Billeder kræver `GEMINI_API_KEY`. Eksisterende udbydervalg via `AI_UDBYDER` og individuelle instrukser i `_redaktion/hjerner.json` er bevaret. Ingen API-nøgler må lægges i kildekoden.

Ved upload skal de nye filer også med: især **`redaktion.py`, `assets/nyheder.css`, `assets/nyheder.js` og `assets/artikel.css`**. Ombygningen er lavet i det eksisterende projekt; den kræver hverken ny hosting eller et nyt repository.

## Filer

| Fil | Ansvar |
|---|---|
| `index.html` | Forsidens struktur og navigation |
| `assets/nyheder.css` | Forside og læsevisning på mobil og pc |
| `assets/nyheder.js` | Data, filtre, søgning, artikelvisning og fallback-sortering |
| `assets/artikel.css` | Læsedesign for permanente artikelsider |
| `crawler.py` | Kilder, AI-kald, cache, artikler og øvrig automatisering |
| `redaktion.py` | Vurderingsprompt, validering, aktualitet og udvælgelse |
| `opsaetning/feeds.json` | Nyhedskilder og deres indstillinger |
| `data/articles.json` | Genererede artikler og fælles forsidevalg |
| `opsaetning/opgrader-gamle-artikelsider.py` | Opgraderer gamle artikelsider uden at omskrive teksterne |

## Kontroller

Udvælgelse, cache, id-matching, datoer, kilderegler og offline-opdatering:

```bash
python3 _redaktion/proeve-redaktion.py
```

Forsidens DOM-adfærd testes med JSdom. Afhængigheden kan installeres uden for projektet:

```bash
npm install --prefix /tmp/ai-news-checks --no-audit --no-fund jsdom@26.1.0
NODE_PATH=/tmp/ai-news-checks/node_modules node _redaktion/proeve-forside.js
```

Prøven kontrollerer rigtige artikler, Python/JavaScript-enighed, filtre, søgning, pagination, læser, fokus, historik, gamle links, blokeret lokal lagring og fejltilstande. Den tester DOM-adfærd, ikke pixel-layout i en rigtig browser.

Eksisterende crawlerregressioner:

```bash
PYTHONPATH=. python3 _redaktion/proeve-arv.py
PYTHONPATH=. python3 _redaktion/proeve-tid.py
PYTHONPATH=. python3 _redaktion/proeve-modelvalg.py
PYTHONPATH=. python3 _redaktion/proeve-kilder.py
```

Opgradering af ældre artikelsider kan kontrolleres uden at skrive:

```bash
python3 opsaetning/opgrader-gamle-artikelsider.py --toerloeb
```
