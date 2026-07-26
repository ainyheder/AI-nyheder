# Opgavekø

Natsessionen arbejder oppefra og ned. Ét punkt ad gangen, færdigt og testet,
før det næste røres.

**Torben:** flyt en linje op, hvis du vil have den frem i køen. Skriv nye ønsker
ind hvor som helst. Det, der står øverst, er det, der bliver lavet i nat.

Punkterne øverst er *målte* problemer — vi ved, de findes. Længere nede er de
mere "gå det efter i sømmene". Hvert punkt siger, hvilket af de ni punkter i
`redaktionens-oejne.md` det handler om.

---

## Kø

*Sorteret 26.07.2026 efter: (1) i stykker for læseren nu, (2) bryder
målestokken synligt, (3) gør siden mærkbart bedre, (4) undersøgelser.*

### 1 — I stykker for læseren lige nu

*Ingen kendte lige nu.*

### 2 — Bryder målestokken synligt

*Ingen kendte lige nu.*

### 3 — Gør siden mærkbart bedre

- [ ] **`articles.json` er ikke et arkiv, men det tror resten af koden.** Målt
      26.07 kl. 15: `main()` bygger listen forfra af det, feedene serverer *nu*,
      og bruger kun den gamle fil som cache pr. link. Derfor lever en artikel
      præcis så længe, kildens RSS-feed nævner den — **dage på et travlt feed**,
      ikke de 30 dage `MAX_DAGE_GAMMEL` lover. **35 af 109 artikelsider er ude
      af listen lige nu, den nyeste fra i går.** Konsekvensen er, at ingen
      forbedring af artikelskabelonen nogensinde rammer mere end den nyeste uge,
      og at hver ny nat skal skrive endnu et engangsscript. Nattens rettelser
      lukkede symptomerne (tomme sider bygges ikke, billeder slettes ikke under
      siderne), men ikke årsagen. Mindste rettelse: bevar artikler, der har en
      side, indtil de 30 dage faktisk er gået. **Venter på Torben:** forsiden
      ville vise mærkbart flere artikler, og de 35 genoplivede ville blive
      kandidater til omskrivning og billeder, altså koste penge. Byg ikke, før
      det er afklaret. *Punkt 4 og 10.*

- [ ] **Forsiden på en telefon.** Hierarkiet er bygget og testet på bred skærm.
      Hvordan holder hero + fire kort + kompakt liste på 390 px? *Punkt 4.*
      **Halvt undersøgt 26.07 kl. 15:45 — kan ikke lukkes herfra.** Der er ingen
      browser i sandkassen (hverken Chromium, Puppeteer eller Playwright), og
      jsdom beregner ikke layout, så det kan ikke *måles*, om noget flyder ud.
      Statisk gennemgang af kaskaden ved præcis 390 px (13 media queries, 345
      selektorer) udelukker det, der mekanisk skal sprænge: ingen faste bredder
      over 390 px, alle fem grids falder til én kolonne (største spor 340 px mod
      358 px indhold), læsevisningens to spalter slår om ved 820 px, `viewport`
      er rigtig, `min-width: 0` står 10 steder. De længste rigtige ord passer
      også — 31 tegn mod cirka 34 der er plads til. **Mangler: at nogen ser den
      på en telefon.** Bemærk til hovedkørslen: der står 0 `overflow-wrap` og 0
      `word-break` i hele stilarket, så margenen er tynd — og der ligger allerede
      et **35-tegns** ubrydeligt token i data (en rå YouTube-URL i det uoversatte
      `resume`-felt på "Ny gratis AI-videoredigering til din Mac"), som kun holdes
      væk fra skærmen af, at `resume_da` findes på netop den artikel.

- [ ] **Hvor hurtigt loader forsiden?** Mål størrelsen på `data/articles.json`
      og billederne. Er der noget, der er vokset sig for stort? *Punkt 4.*

- [ ] **Tilgængelighed.** Kan man bruge forsiden med tastatur alene? Er
      kontrasten god nok til svagtseende? (Alt-tekst er klaret 25.07.)
      *Punkt 9.*

- [ ] **`sitemap.xml` mangler tre sider.** Målt 26.07: 29 URL'er i sitemappet,
      32 HTML-filer i roden (404 fraregnet). De tre, der mangler, er
      `velkommen.html`, `tak.html` og `undervisning.html`. De to første er
      formentlig med vilje ude (kvitteringssider), men det står ingen steder —
      og `undervisning.html` skal ind, den dag den bliver linket. Filen er
      skrevet i hånden, så den falder bagud, hver gang der kommer en side til.
      *Punkt 4 og 10.*

- [ ] **Tjek at alle interne links virker.** Gennemgå alle HTML-sider for links
      til sider, der ikke findes. *Punkt 4.*

- [ ] **Tjek at PWA'en stadig virker.** Service worker, manifest, ikoner —
      efter alle dagens ændringer. *Punkt 4.*

- [ ] **Gennemgå crawlerens fejlbeskeder.** Er der steder, hvor noget fejler
      stille uden at sige hvorfor? Det var netop dét, der skjulte tre fejl.
      *Punkt 6.*

- [ ] **Ryd op i `_to_delete/`.** Mappen ligger stadig i repoet med gamle
      workflow-filer. Er der noget, der skal gemmes, før den ryger?

- [ ] **`data/img/` kan ikke længere rydde op efter sig.** Fra 26.07 sletter
      oprydningen aldrig et billede, en side på disken peger på — det var
      rettelsen, der fjernede 25 brudte billeder. Prisen er, at **62 af 69 filer
      nu er permanente**, og at mappen vokser med ~10 billeder à 88 kB på travle
      dage, altså 25–30 MB om måneden i git. Hæves `BILLED_STIL_VERSION`, låses
      hele det gamle sæt fast oveni. Intet er i stykker; spørgsmålet er, hvornår
      repoet bliver ubehageligt stort. Mindste rettelse er formentlig at flytte
      billeder for sider ældre end X måneder ud af git og lade siderne pege på
      `assets/og.png` — men det er Torbens valg, om det er værd at gøre endnu.
      *Punkt 4.*

- [ ] **En dubletside kan pege canonical mod en side, der aldrig bygges.**
      `_peg_dubletsider_mod_hovedhistorien` kaldes øverst i `lav_artikelsider`,
      altså **før** den nye `_har_noget_at_vise`-vagt, og den tjekker ikke, at
      vinderens side faktisk bliver skrevet. Før 26.07 var `rubrik` nok til at
      vinderen blev bygget; nu kan vagten blokere den, og så står dubletsiden
      med en canonical mod en 404 — samtidig med at den selv er ude af
      sitemappet. **Målt 26.07 kl. 15: 0 tilfælde**, så intet er i stykker nu.
      Mindste rettelse: samme vagt i vinder-tjekket. Fundet af den uafhængige
      gennemgang. *Punkt 4 og 10.*

### 4 — Undersøgelser: vi ved ikke, om der er et problem

- [ ] **Tjek dubletfangeren.** Find historier i arkivet, der reelt dækker samme
      begivenhed, men står som to. Er `saml_dublet_historier` for forsigtig?
      *Punkt 3.* — Bemærk: selve **valget** af hovedhistorie blev rettet
      26.07; det her handler om de grupper, den slet ikke finder.

- [ ] **Er dagens overblik virkelig dagens vigtigste fem?** Sammenlign
      `data/brief.json` med de højest prioriterede artikler samme døgn.
      *Punkt 6.*

- [ ] **Gennemgå kategoriseringen.** Ligger artiklerne i de rigtige kategorier,
      eller ender for meget i "Lanceringer"? *Punkt 6.*

- [ ] **Virker siden uden JavaScript?** Artikelsiderne gør. Forsiden gør ikke.
      Er det et problem for Google og for folk med langsomme forbindelser?
      *Punkt 9.*

- [ ] **AI-kørekortet, modul for modul.** Er sproget stadig til en nabo uden
      teknisk baggrund, eller har der sneget sig jargon ind? *Punkt 7.*

- [ ] **Erhvervsoverbygningens fire moduler.** Samme gennemgang. Rammer de folk,
      der møder AI på jobbet — uden at blive konsulentsprog? *Punkt 7.*

- [ ] **prompts.html og prompt-arkivet.** Er de 17 prompts stadig de bedste, vi
      kan lave? Er der gengangere mellem biblioteket og kartoteket? *Punkt 3.*

- [ ] **vaerktoejer.html.** Er de 13 værktøjer og noterne stadig rigtige? Priser
      og funktioner skifter hurtigt — flag det, der ser forældet ud, i loggen
      i stedet for at gætte. *Punkt 5.*

- [ ] **laer.html.** Er den stadig inspirerende, eller er den blevet en
      linksamling? *Punkt 7.*

- [ ] **faq.html.** Svarer den på det, en ny besøgende faktisk undrer sig over?
      *Punkt 7.*

- [ ] **En tilfældig artikelside.** Ser den professionel ud alene, uden forsiden
      omkring sig? Det er den, folk lander på fra Google. *Punkt 4.*

- [ ] **En tilfældig videoside.** Samme prøve. *Punkt 4.*

- [ ] **uge.html — ugens overblik.** Holder den stadig, eller er den blevet en
      opremsning? *Punkt 2.*

- [ ] **om.html.** Stemmer beskrivelsen med, hvad siden faktisk gør i dag?
      Kildelisten er ændret, og DeepSeek er på vej ind. *Punkt 5.*

- [ ] **Læs `data/opslag.json` igennem, når der er udkast i den.** Er tonen i
      de automatiske opslag noget, Torben ville skrive selv? *Punkt 5 og 8.*

---

## Klaret

- [x] **11 frosne artikelsider havde brudt billede igen.** *(26.07.2026, ekstra
      kørsel kl. 15:32)* Punktet ventede på Torbens push, og det kom kl. 15:30 —
      `_BILLED_I_HTML`, `_billedfil`, `_har_noget_at_vise` og `_side_har_indhold`
      ligger nu alle i `origin/main`, så mekanismen bag er lukket, og oprydningen
      kan ikke slette billederne igen. Tallet 11 holdt, men hver side havde **tre**
      døde referencer til den samme forsvundne fil, ikke én: `<img class="top">`,
      `og:image` (sort delevisning) og `"image"` i JSON-LD ("Image not found" i
      Search Console) — 33 i alt. Alle 11 viste sig at være **dubletsider**, hvis
      canonical peger på en hovedhistorie; det forklarer, hvorfor de er frosne.
      Rettet fire linjer pr. fil, 44 i alt, intet andet rørt. Efter: 0, 0, 0, og 0
      sider der lover en illustration uden at have en. Kontrolleret at
      håndrettelsen er tegn for tegn identisk med `_artikel_side_html()`s egen
      udskrift for en død billedsti, og at crawleren fejler pænt på fem slags
      vrøvl-input. 326 assertions på siderne, 18 på forsiden, alle grønne. Samme
      måling bekræftede, at **0 af 109 artikelsider** har canonical mod en 404 —
      køens latente punkt om dét er stadig på nul.

- [x] **25 artikelsider viste et brudt billede.** *(26.07.2026, ekstra kørsel
      kl. 14:37 — fund uden for køen)* Målt: 25 af de 87 sider med billede pegede
      på en fil, der ikke findes; dertil 25 døde `og:image` (ødelagt delevisning)
      og 17 døde billeder i structured data ("Image not found" i Search Console).
      Årsagen var to regler, der trak i hver sin retning: `lav_artikelsider`
      gemmer siderne for evigt, mens oprydningen i `lav_billeder` slettede alt,
      der ikke stod i den aktuelle liste — og artiklen forlader listen efter
      dage. Et tredje hul lå i cachen, der bar en `billede`-sti videre til en
      slettet fil, så **forsiden** viste det brudte billede for 2 levende
      artikler i stedet for den tegnede grafik. Rettet fire steder: oprydningen
      spørger nu siderne (nyt `_BILLED_I_HTML`), nyt `_billedfil()` slår filen op
      og udelader `<img>`, `og:image` og JSON-LD-billedet på én gang, `main()`
      rydder en død sti før `lav_billeder`, og de 25 sider er reparteret på
      disken. Efter: 0, 0 og 0. 117 jsdom-assertions på 20 sider, alle grønne.

- [x] **22 sider lovede en illustration, de ikke havde.** *(26.07.2026, ekstra
      kørsel kl. 14:37 — fund uden for køen)* Varedeklarationen nederst stod som
      fast tekst i skabelonen og sagde "AI-genereret illustration" også på sider
      helt uden billede. Punkt 5. Noten bygges nu af led, og de 22 sider er
      rettet på disken med samme ordlyd. Tørløb krævede præcis én ændret linje
      pr. fil. Efter: 0 lyver, 87 med billede siger det stadig.

- [x] **Artikelsider fryses, når de falder ud af 30-dages-vinduet.**
      *(26.07.2026, ekstra kørsel kl. 14:37)* Punktet var rigtigt i, at siderne
      fryser, men **forkert forklaret på tre måder**. (1) Fristen er dage, ikke
      30: `articles.json` bygges forfra af feedene hver kørsel, så 35 af 109
      sider er ude af listen nu, den nyeste fra i går. (2) Målingen kl. 11 talte
      kun levende sider; tælles alle 109, er der **16 tomme** på 465–574 tegn, og
      **12 af dem stod i sitemappet**, så Google blev inviteret til at sende
      læsere til en rubrik, én sætning og et link ud af huset. (3) De blev ikke
      tynde af at fryse — de blev **bygget** tynde, fordi en side skrives så snart
      `rubrik` findes, ét AI-kald før genfortællingen; 12 af de 15 er Hacker
      News-links til PDF'er, hvor der ikke var tekst at hente. Køens forslag
      kunne ikke bruges: `opgrader-gamle-artikelsider.py` skriver kun JSON-LD og
      alt-tekst, og på de 15 sider er der intet indhold at genskrive ud fra.
      Rettet med to gratis guards: `_har_noget_at_vise()` venter med at bygge,
      til der er noget at læse (placeret før `a["side"]` sættes, så forsiden ikke
      linker i blinde), og `_side_har_indhold()` holder tomme sider ude af
      sitemappet — 72 URL'er mod 85. 38 assertions. **Årsagen står urørt og er
      skrevet ind i køen som eget punkt.**

- [x] **Ingen af de statiske sider har en canonical.** *(26.07.2026, ekstra
      kørsel kl. 14)* Målt: 2 af 33 havde én. Sat på **28 sider** i crawlerens
      eget format, lige efter `<meta name="description">`. `index.html` peger på
      `https://ainyheder.com/` uden filnavn — samme form som sitemappets `<loc>`,
      så `/` og `/index.html` ikke længere kan indekseres som to sider. Undervejs
      viste målingen, at **`uge.html` ikke er en statisk fil**: crawleren
      genskriver den fra `_uge_side_html()`, så en rettelse i hånden var
      forsvundet ved næste kørsel. Linjen er lagt i skabelonen, og den genskabte
      fil er byte for byte identisk med den på disken. Alle 22 `write_text` i
      crawleren og hele `crawl.yml` gennemgået: `uge.html` er den eneste rod-HTML,
      der genereres. `404.html` fik med vilje ingen (fejlside), og `tak.html` +
      `velkommen.html` heller ikke (de har allerede `noindex`). Alle 29
      sitemap-URL'er har nu en side, der peger på præcis den adresse. 203
      assertions, alle grønne.

- [x] **12 rubrikker mangler stadig et navn.** *(26.07.2026, ekstra kørsel kl. 14)*
      Tallet holdt — 12 af 96, alle låst af `navngivet`, ingen uprøvede. Men de
      var ikke låst, fordi AI'en gav op: `navngiv_rubrikker` viste den kun den
      engelske titel, RSS-resuméet og vores egen navnløse rubrik — **aldrig**
      `sektioner` og `detaljer`, den danske genfortælling crawleren selv skriver
      ét kald tidligere. Navnene stod netop dér: **Microsoft** i én, **ChatGPT,
      Claude og Gemini** i en anden. Git-historikken beviser skaden: rubrikken
      *"…fremtidens computerkraft"* blev 25.07 omskrevet til *"…fremtidens
      **AI-kraft**"* og låst — modellen satte ordet "AI" ind, og den dengang
      utætte `_har_navn` godtog det som et navn. Rettet: nyt `_dansk_uddrag()`
      lægger genfortællingen i payloaden, navnebærende stumper først (en simpel
      klipning ved 700 tegn nåede aldrig frem, fordi sektionerne fylder 1.100);
      prompten siger nu, at "AI" ikke er et navn, og at et tomt svar er gyldigt;
      ét vrøvl-element taber ikke længere hele klumpen. `navngivet` nulstillet
      for **præcis de 3**, hvor uddraget nu leverer et sikkert navn — de øvrige
      9 har intet navn i noget materiale vi har, og fem af dem er `kun_aktuel`,
      hvor vi aldrig får mere. 58 assertions, alle grønne.

- [x] **Viser videosiderne faktisk tidsstempler?** *(målt 26.07 kl. 11)* Ja.
      17 af 40 videoer har hoejdepunkter, og praecis de 17 videosider viser dem
      - ingen falder for tidstjekket. De 23 uden har intet at vise, fordi
      YouTube ikke udleverede undertekster. Intet at rette.

- [x] **Læs 20 tilfældige rubrikker som en nabo uden teknisk baggrund.**
      *(26.07.2026, ekstra kørsel)* Læste alle 107. Jargon er **ikke**
      problemet — kun tre rubrikker kan en nabo ikke læse ("Runway lancerer ny
      smart **model-router**", "Østrigs militær vælger **open source**",
      "USA's hær opbruger alle sine **AI-tokens**"). Til gengæld stod der en
      **stavefejl** på forsiden: *"barrierer **spæner** ben for eksperter"* —
      det hedder "spænder ben". Modellen brugte ordet forkert 8 gange: 3 i
      `articles.json` og 5 på artikelsiden, heriblandt `<title>`, `og:title`
      og NewsArticle-schemaets `headline`, altså også dét Google viser.
      Rettet begge steder via `json.load`/`dump`, diff på præcis 3 + 5 linjer,
      JSON-LD stadig gyldig, forsiden grøn i jsdom. 9 af 107 rubrikker er over
      8 ord; "kunstig intelligens" står 0 steder. De tre uforståelige
      rubrikker kræver et AI-kald at omskrive.

- [x] **Læs 20 tilfældige "Hvad betyder det for dig" igennem.**
      *(26.07.2026, ekstra kørsel)* Læste alle 79 i stedet for 20. De fleste
      er fine: median 21 ord, nul over to sætninger, nul gengangere. Men **6
      taler OM "almindelige mennesker" i stedet for TIL læseren** — og de er
      en anden slags tekst: median 42 ord mod 20, alle 6 uden "du", 4 af 6
      over promptens grænse. Boksen hedder "Hvad betyder det for **dig**?", så
      de svarer på et andet spørgsmål end det, der står over dem. Årsagen var
      redaktør-agenten: dens regel 4 var selv formuleret i tredjeperson
      ("konkret **for almindelige danskere**"), så den godkendte netop den
      fejl, den skulle fange — og den håndhævede hverken de 35 ord eller
      "du"-tiltalen, skribentens prompt kræver. Rettet regel 4, tilføjet et
      deterministisk `_betydning_problemer()`, der fodrer den eksisterende
      omskrivningsvej (udløses på 10 %, ikke på de gode), plus et værn mod at
      omskrivningen gør det værre. `GENKOER_ALT=betydning` retter de 8
      eksisterende for 8 kald i stedet for 80. 45 assertions, alle grønne.

- [x] **32 af 110 artikler står uden billede.** *(26.07.2026, ekstra kørsel)*
      Målt mod crawlerens eget udvalg: 0 overlap — men den måling spørger
      crawleren, om den er enig med sig selv. Målt mod **forsiden** var
      svaret et andet: `_kort_artikler()` og `index.html` var uenige om, hvad
      et billedkort er, tre steder. (1) `kun_aktuel` blev udeladt, selvom
      arkivforbuddet gælder udgiverens *tekst* — to prio 7-historier stod som
      store kort med tomt billedfelt. (2) Forskning blev grupperet sammen med
      nyhederne, selvom forsiden har to faner, der ikke deler artikler, så en
      forskningsartikel brugte en plads, ingen ser på nyhedsfanen. (3)
      Forsidens `prioAf()` giver flerkilde-historier +1; crawleren gjorde ikke
      — alene dét flyttede 6 links. Standard var 2 af 9 pladser tom,
      Forskning 5 af 6; begge er nu 100 % dækket. Udvalget går 53 → 61, og 8
      billeder laves ved næste kørsel (~$0,27, loft 35). 25 Python-assertions
      og 9 jsdom-assertions, alle grønne. **Emnefiltrene er stadig ikke
      dækket** — det koster ~$1,46 at give alle artikler billede, og det er
      Torbens beslutning; se loggen.

- [x] **Overskrifter uden navn.** *(26.07.2026, ekstra kørsel)* Læste alle 102
      rubrikker. Svaret var ikke "er de ni rimelige?" men at **detektoren var i
      stykker**: `_har_navn` godtog **"AI"** som et navn, fordi et stort bogstav
      midt i en sætning tæller som navn — og "AI" står i næsten hver eneste
      rubrik på et AI-nyhedssite. Samme leak gav "Det" og "Nu" efter et kolon.
      Derfor mente crawleren, at kun **7 af 102** manglede navn, og 5 af de 7 var
      falske alarmer. Imens slap **"Gigantens milliard-regnskab…"** og
      **"…gigantisk AI-firma"** igennem — præcis det eksempel, målestokkens
      punkt 1 er skrevet imod. Rettet: "AI" tæller ikke, stort bogstav efter
      kolon tæller ikke, rolleord ("Gigant", "Kommune", "Forskere") tæller ikke,
      ejefald slår nu op i mærkelisten ("Blueskys", "Østrigs"). Tallet er gået
      fra 7 til **29 af 102**, og de 29 er læst igennem — de mangler alle et
      navn. 42 assertions, alle grønne.

- [x] **`koerekort-tjek.html` lover mere, end tjekket kan holde.**
      *(26.07.2026, ekstra kørsel)* Bevist først: jeg lavede et gyldigt
      bevis-nummer til "Aldrig Deltaget Hansen" med ti linjer kode og vores egen
      kildekode, og vores egen tjek-side svarede "✅ Beviset er ægte" —
      både på grundkort og erhverv. Så det var ikke kun én sætning, der var
      forkert; det var også den grønne overskrift, en arbejdsgiver ser.
      Rettet fem steder: overskriften er nu "Nummeret passer til navnet",
      manchetten og meta-beskrivelsen lover ikke længere "ægte udstedt", og
      varedeklarationen siger, hvad tjekket faktisk gør. Tilføjet én boks, der
      siger rent ud, at opskriften står i kildekoden, at én der kan læse kode
      kan lave et nummer til et hvilket som helst navn, og at det ville kræve
      server og login at forhindre — hvad kørekortet bevidst ikke har.
      Kodekommentaren i `koerekort.html` og `erhverv.html` rettet samme sted.
      14 assertions, alle grønne; tjekket godkender og afviser som før.

- [x] **Kørekortet kan ikke nulstilles, og det spærrer for hold.**
      *(26.07.2026, ekstra kørsel)* Bygget: et afsnit nederst på `koerekort.html`
      med to-trins bekræftelse, der siger præcis hvad der ryddes ("7 gennemførte
      moduler i grundforløbet, 4 moduler i erhvervsoverbygningen og 9 gemte svar
      fra øvelserne") og en kvittering med antal. Målingen ændrede rettelsen:
      **`aikort*` var ikke nok.** Erhvervsbeviset gemmer sin dato og sit nummer
      under `aike_udstedt` og `aike_bevisnr` — uden "ort" — så det mønster, der
      stod i køen, ville have efterladt to nøgler, og næste deltager ville arve
      forrige deltagers udstedelsesdato. Knappen spørger nu til begge præfikser.
      `laeste` (læste artikler på forsiden) og andet i browseren røres ikke.
      40 assertions i jsdom, alle grønne.

- [x] **Nat-loggen i panelet opdaterer sig ikke selv** *(klaret 2026-07-26 — natsessionen kalder nu `skriv_hjerne_status()` som sidste skridt; verificeret: loggen fylder 31.861 tegn i panelet)*

*(Natsessionen flytter afkrydsede punkter herned med dato.)*

- [x] **Virker det strammede Hacker News-feed?** *(26.07.2026)* Ja. Med
      point-grænsen hævet fra 50 til 150 ligger der **4 Hacker News-artikler**
      i arkivet, og alle fire er set **i dag**: om open-weight-modeller, om
      argumenterne mod open source-AI, om en ny videoeditor og om en F-16 fløjet
      af en robot. Feedet er ikke gået i nul, og de fire ligner præcis dét, den
      højere grænse skulle give — historier med reel vægt frem for støj.

- [x] **Nat-loggen blev vist som rå markdown i kontrolpanelet.**
      *(26.07.2026)* Panelet viste `**stjerner**`, `##` og backticks i en
      monospace-tekstboks. Den renderes nu som ét kort pr. nat med datoen skrevet
      ud, titlen i Fraunces og **Fandt / Gjorde / Testede / Til Torben** som
      mærkede felter; nattens regnskab får sit eget fremhævede kort. Rendereren
      er skrevet i hånden, fordi panelet åbnes fra `file://`. Grænsen for,
      hvor meget der indlejres, er hævet fra 4.000 til 30.000 tegn, og
      klipningen tager altid nattens regnskab med. Modalen bruger nu skærmen:
      `min(1560px, 96vw)`, to spalter over 1120 px og tre over 1900 px. Elleve
      injektionsforsøg afvist — heriblandt et `javascript:`-link, der slap
      igennem første udgave. **Det, filen bliver vist med, er løst; at den bliver
      opdateret, er det ikke** — se punktet i køen.

- [x] **ordbog.html — mangler der ord, folk møder i nyhederne i dag?**
      *(26.07.2026)* Gennemgået i fase 2. Ordbogen har 48 opslag. Jeg trak alle
      rubrikker, resuméer, sektioner, detaljer og betydninger ud af de 105
      artikler (133.200 tegn) og talte, hvor tit hvert af 48 tekniske udtryk
      optræder. **Ordbogen dækker praktisk talt alt, læseren møder** — agent,
      benchmark, token, model, GPU, API, open source, datacenter, chatbot,
      cloud, hallucination, kontekstvindue, RAG, prompt injection, vandmærke og
      resten står der alle. De eneste ord uden opslag er "chip" (3 gange, og
      det er almindeligt dansk), samt transformer, superintelligens, copilot og
      evaluering — én forekomst hver. **Fandt intet, der bryder målestokken.**

- [x] **35 af 96 artikler mangler det fulde brief.** *(26.07.2026)* Problemet
      findes ikke som beskrevet. Feltet `brief` udfyldes aldrig — prompten beder
      om `sektioner`, aldrig om `brief` — så tallet målte et dødt felt. Rigtige
      tal: **78 af 105 har fuld genfortælling**, 26 af de resterende 27 er
      `kun_aktuel` (arkivforbud, tilsigtet), og **1 er reelt uforklaret**
      (OpenAI Blog, 9. juli). Loftet er 250, ikke i nærheden. Rettede det ene
      sted, hvor det døde felt kunne mærkes: `_slaa_sammen`s første prioritet.
      De 16 tynde sider er heller ikke brief-relaterede — 15 af dem er frosne
      sider uden for 30-dages-vinduet.

- [x] **Sammenlagte historier efterlader en forældreløs artikelside.**
      *(26.07.2026)* Målt: 5 sider, ikke "næsten samme indhold" men 6–20 %
      lighed — problemet er tre sider, der konkurrerer om samme søgning. De
      peger nu canonical mod hovedhistorien og er ude af sitemappet (102 filer
      står stadig, intet slettet; sitemappet gik 102 → 97). Undervejs viste
      målingen en større fejl: `_slaa_sammen` tog den **første** udgave, ikke
      den med mest indhold, så OpenAIs egen pressemeddelelse på 1.417 tegn slog
      to Ars Technica-udgaver på 2.798 og 2.063. Rettet — men kun for
      fremtidige sammenlægninger.

- [x] **Der findes ingen side, der taler til undervisere.** *(26.07.2026)* Målt:
      ordene "underviser", "undervisning", "aftenskole" og "jobcenter" stod nul
      steder på nogen af de 30 HTML-sider. `undervisning.html` er skrevet og
      testet — men **ikke linket fra noget endnu**; hvor den skal stå er Torbens
      valg, og den skal i `sitemap.xml` samtidig. Undervejs viste målingen, at
      forløbet tager 95 minutter og ikke de 105–140, `koerekort.html` lovede
      (rettet), at fremdrift på delte computere er et reelt problem uden
      nulstil-knap, og at bevis-saltet står i klartekst i kildekoden.

- [x] **Dagens overblik skrives hver dag og bruges ét sted.** *(25.07.2026)*
      Undersøgt: Buttondowns gratis plan tillader udtrykkeligt én daglig mail, og
      planlagt afsendelse er også gratis. Infrastrukturen findes allerede.
      Undersøgelsen ligger i `_redaktion/undersoegelse-daglig-mail.md`. **Venter
      på en beslutning fra Torben:** abonnenterne har sagt ja til en ugentlig
      mail, og at lade dem vælge koster +$9/md. Byg ikke før det er afklaret.

- [x] **Kørekortet er gemt bag nyhederne.** *(25.07.2026)* Målt: 2 af 56 links på
      forsiden fører til lære-indhold, 0 direkte til kørekortet, og ordet
      "kørekort" står ikke ét sted. Det ene link er en pille sidst i
      filterrækken, der ligner et filter. Forslag ligger i
      `_redaktion/forslag-koerekort-indgang.html` — en fodlinje i Dagens
      overblik, til at se på og sige ja eller nej til. Forsiden er ikke rørt.

- [x] **Ingen ved, om Google har set de 83 artikelsider.** *(25.07.2026)*
      Sitemappene svarer korrekt live — 102 + 40 URL'er, alle sider 200, 404
      virker. Men Google har indekseret 0 artikelsider og 0 videosider; kun 7
      statiske sider er inde. Sitemappene er aldrig indsendt, og det kan kun
      Torben gøre — instruksen står i nat-loggen. Undervejs viste målingen, at
      alle 102 artikelsider manglede NewsArticle-schema (videosiderne havde det),
      at alle 129 billeder havde tom alt-tekst, og at en rubrik med `</script>`
      kunne ødelægge den strukturerede data. Alt tre rettet og testet.

---

## Ting kun Torben kan gøre

Disse venter på ham — natsessionen skal ikke forsøge dem:

- Læg `DEEPSEEK_API_KEY` i GitHub secrets, hvis DeepSeek skal overtage teksterne
- Send besked til community@version2.dk om brug af deres RSS-feed
- Opret Bluesky-konto og læg `BLUESKY_BRUGER` + `BLUESKY_KODE` ind
- Opret Facebook-side og LinkedIn-virksomhedsside, hvis de skal bruges
- Sæt `OPSLAG_LIVE = ja`, når tørkørslerne ser rigtige ud
- Sæt budgetalarm på Google Cloud
- Indsæt de 14 kursusmails i Buttondown
