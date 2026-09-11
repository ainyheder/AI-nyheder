# AI-nyheder

Danske AI-nyheder med en læsevenlig forside, korte overblik og permanente artikelsider. Siden bruger almindelig HTML, CSS og JavaScript og fungerer direkte på den eksisterende GitHub Pages-opsætning. Der er intet byggetrin.

## Ombygningen, september 2026

Forsiden har en tydelig hovedhistorie og to andre udvalgte historier. Under **Mere at opdage** fortsætter andre historier; de tre fra toppen gentages ikke. De tidligere blokke med “Kort fortalt” og de samme historier endnu en gang er fjernet. Topfeltet bliver til én kolonne på mobil og fungerer også uden illustrationer.

Søgning, emnefiltre og **Nyeste først** viser én samlet liste og skjuler topfeltet. Her kan også de udvalgte historier findes. Nulstilling genskaber forsiden. Artikelvisningen har større tekst og en begrænset linjebredde. Mobilmenu, tastaturbetjening, delelinks og browserens tilbage/frem understøttes. Læste artikler markeres lokalt; besøgstal ændrer ikke udvælgelsen.

Alle eksisterende sider i `artikel/` bruger det fælles læsedesign i `assets/artikel.css`. Deres artikler, kilder, permanente adresser og canonical-links er bevaret. Det store antal ændrede arkivfiler skyldes tilføjelsen af fælles CSS, en tilbagegenvej og tastaturadgang.

## AI-model

Den daglige tekstmodel er **DeepSeek V4.1 Flash**, med API-navnet `deepseek-flash`. Alle arbejdstrin uden et særskilt modelvalg følger denne standard. Billedmodellen er uændret. Ændringen træder i kraft ved næste crawlerkørsel efter upload; tidligere artikeltekster omskrives ikke automatisk.

Officielt modelnavn: https://www.deepseek.com/en/news/deepseek-v4-1-flash/

## Sådan udvælges nyhederne

`crawler.py` henter kilderne og får AI til at vurdere hver historie. Derefter holder **redaktøragenten** et redaktionsmøde med DeepSeek V4.1 Flash. Den kan vælge hovedhistorier anderledes end den gamle pointliste. Den godkendte plan styrer forsiden; `redaktion.py` er reserve og bruges fortsat til den øvrige prioritering, quiz og billedbudget.

### Redaktøragenten

- **Redaktionens retning:** Redigér `opsaetning/redaktoer.md` på almindeligt dansk. Filen læses ved hvert møde. Her står allerede præferencen for nye modeller, konkrete muligheder og variation.
- **Hukommelse:** Op til syv døgns tidligere forsider gemmes i `data/redaktoer-hukommelse.json`. Agenten får de seneste udgaver og en samlet oversigt over ugens tidligere omtaler. Mislykkede møder gemmes ikke som udgivne forsider.
- **Kildeadgang:** Agenten bruger ægte API-værktøjskald til at finde i kandidatlisten, læse kendte kilder og følge officielle henvisninger fundet i materialet. Den har ikke en generel websøgning. Kildetekster behandles som data; manglende adgang markeres som et RSS-resumé eller utilgængelig kilde.
- **Skriveopgaver:** Agenten vælger op til tre historier, bestiller en konkret vinkel og kan samle dokumenterede omtaler. Dens opgaver får plads før pointlisten i skrivebudgettet. Et ændret kildegrundlag eller en ændret opgave kan udløse omskrivning af en cached artikel.
- **Kontrol:** Skribentens udkast og hele udgaven kontrolleres mod de læste kilder. Et afvist udkast erstatter ikke en gemt artikel. Afviser slutkontrollen udgaven, gendannes også de tidligere artikeltekster. Nye kildehenvisninger følger med både i læseren og på den permanente artikelside.
- **Drift:** Højst syv modelrunder til mødet, otte kildehentninger og ét afsluttende udgavetjek. Skrive- og korrekturkald er derudover begrænset til de tre valgte historier og crawlerens eksisterende budget. Ved uændrede kandidater og instruktioner kan en kontrolleret plan genbruges i fire timer. Fejl bruger en stadig gyldig plan på højst 24 timer eller pointlisten.

`data/redaktoer-status.json` viser status, begrundelser, skriveopgaver, modelkald, kildehentninger og både agentens og pointlistens udvalg. Rå kildetekster og API-nøgler gemmes ikke i status eller hukommelse. De nye datafiler kommer automatisk med i den eksisterende GitHub-workflow.

Agenten aktiveres ved næste crawl efter upload med den eksisterende `DEEPSEEK_API_KEY`. Nøglen bliver på GitHub. En lokal kørsel uden nøgle bruger reserven. Der er ikke foretaget et betalt modelkald i udviklingstesten; testene dokumenterer funktion og integration, ikke et målt kvalitetsløft fra modellen.

En separat sammenligning kan køres uden at udgive, omskrive artikeldata eller sende noget:

```bash
# Ingen model- eller kildekald: kontrol af datakopi og pointlistens udvalg.
python3 opsaetning/proev-redaktoer.py --rapport /tmp/redaktoer-proeve.json

# Med nøgle i miljøet: afgrænset redaktionsmøde og sammenligning på samme data.
python3 opsaetning/proev-redaktoer.py --live --rapport /tmp/redaktoer-proeve.json
```

Brug `--data /sti/til/articles.json` til en anden nyhedsdag. Rapporten angiver eksplicit, om agenten faktisk blev kaldt. Den separate prøve godkender ikke en udgave til udgivelse; det gør crawlerens fulde arbejdsgang efter skrivning og kontrol.

### Reserveudvælgelsen

| Kriterium | Vægt | Spørgsmål |
|---|---:|---|
| Nyhedsværdi | 25 % | Hvad er faktisk nyt? |
| Betydning | 25 % | Hvilke konkrete følger har det for mennesker? |
| Brugbarhed | 20 % | Kan læseren bruge indsigten eller træffe et bedre valg? |
| Dokumentation | 20 % | Hvor godt understøtter det tilgængelige materiale påstanden? |
| Dansk relevans | 10 % | Er der dokumenteret relevans for Danmark, EU eller danske brugere? |

**Modellanceringer er førsteprioritet.** Bekræftede nye AI-modeller og modelversioner får 36 ekstra prioritetspoint de første 48 timer. Derefter halveres bonussen for hver yderligere 48 timer og bortfalder efter en uge. Alle historier får desuden et stærkere aktualitetsfradrag efter tre døgn. Det giver friske historier plads uden tilfældig rotation. Forskellige modellanceringer straffes mindre for at dele kategori. Almindelige produktfunktioner, plugins, kundecases, tests og rygter tæller ikke som modellanceringer. Et smalt produktfilter afviser også åbenlyse fejlvurderinger, fx ChatGPT til en bestemt branche, selv når AI har sat modelflaget forkert.

AI giver hvert kriterium 0–5 og skriver en kort begrundelse samt eventuelle forbehold. Vurderingen bygger på det medsendte kildemateriale; den er ikke en selvstændig faktakontrol. Manglende oplysninger må ikke opfindes. Resultater matches med artikel-id og valideres, før de caches.

Udvælgelsen tager derefter højde for kildens **udgivelsesdato**, og gentagelser af samme kilde, kategori eller hovedaktør får et fradrag. Flere omtaler giver ikke i sig selv flere point. En vigtig forskningshistorie kan fortsat få en hovedplads. Reklameprægede opslag, perifert AI-stof, svagt dokumenterede historier og rygter får ingen hovedplads. På stille dage vises færre udvalgte historier.

Omtaler af samme historie samles ved fælles kildelinks, ens fulde overskrifter eller en entydig navngiven modellancering inden for syv døgn, fx Suno v6. Kildelinks og originale delelinks bevares. URL-sporing ignoreres, men betydende parametre bevares. Fælles firmanavn er ikke nok. Modelvarianter, sammenligninger, API-adgang og regionsspecifikke udgivelser samles ikke på modelnavnet alene. Ukendte navnevarianter springes over frem for at gætte. Reglerne findes både i Python og JavaScript og ændrer ikke de gemte artikeltekster.

En artikel kan blive i overblikket i op til syv døgn efter udgivelsen, selv om den falder ud af kildens RSS-feed. Kilder, der er slået fra, eller har `kun_aktuel`, genindlæses ikke fra arkivet. Hvis samtlige aktive kilder fejler, stoppes kørslen, så den eksisterende udgave bevares.

### Overgang fra gamle vurderinger

Vurderinger gemmes i artiklens `redaktion`-felt med versionsnummer. Version 3 tilføjer et eksplicit `model_lancering`-felt. Version 2-vurderinger og deres forbehold bevares, indtil de kan opdateres. En konservativ tekstanalyse prioriterer eksisterende modellanceringer med det samme. Ved næste kørsel med en fungerende AI-nøgle får op til 120 artikler den nye vurdering, i portioner på 12. Resten fortsætter ved næste kørsel. Artikler helt uden delvurderinger bruger den eksisterende `prio` med den nye modelprioritet og aktualitetslogik. Der skal ikke slettes data eller indstilles nye secrets.

Normalt prioriteres de 40 vigtigste artikler til dyb behandling med redaktørens opgaver forrest. Et manglende billede giver et almindeligt tekstlayout og påvirker ikke historiens placering.

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
python3 _redaktion/proeve-redaktoer-agent.py
```

Forsidens DOM-adfærd testes med JSdom. Afhængigheden kan installeres uden for projektet:

```bash
npm install --prefix /tmp/ai-news-checks --no-audit --no-fund jsdom@26.1.0
NODE_PATH=/tmp/ai-news-checks/node_modules node _redaktion/proeve-forside.js
```

Prøven kontrollerer rigtige artikler, Python/JavaScript-enighed, unikke pladser på forsiden, samlede kilder, filtre, søgning, pagination, læser, fokus, historik, gamle links, blokeret lokal lagring og fejltilstande. Tiden er fastlåst til testdataenes udgave, så testen ikke fejler, blot fordi en artikel bliver gammel. En ekstra JSON-kopi kan kontrolleres med `AI_NEWS_DATA=/sti/til/articles.json` uden at ændre data i Git. Den tester DOM-adfærd, ikke pixel-layout i en rigtig browser.

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
