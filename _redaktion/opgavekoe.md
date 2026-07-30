# Opgavekø

Sessionen arbejder oppefra og ned. Ét punkt ad gangen, færdigt og testet,
før det næste røres.

**Redaktionen:** flyt en linje op i panelet, hvis du vil have den frem. Så
sætter panelet mærket `#fastholdt` på, og sessionens omsortering lader punktet
stå — ellers ville din beslutning blive sorteret væk ved næste kørsel. Skriv nye
ønsker i `oensker.md`. Det, der står øverst, er det, der bliver lavet først.

Filen har syv lister, og de skal ikke blandes sammen:

| Liste | Hvad det er | Bliver det lavet? |
|---|---|---|
| `## Kø` | Målte problemer. Hvert punkt har et tal og en dato. | Ja, oppefra og ned |
| `## Nyt` | Ting siden BØR kunne, men ikke kan. Ikke fejl. | Ja — mindst én om ugen |

- **Vurdér humor-motiverne efter en uge (fra 30.07).** Torben har fået et
  udkast til en ny motiv-instruks med "glimtet i øjet": højst én lun detalje
  pr. scene, aldrig ved svindel/ofre/fyringer/misbrug, tvivl falder til alvor.
  Når den har kørt ~en uge: tag de første ti billeder lavet med den nye
  instruks, hold dem op mod ti fra før (side om side, som FLUX-prøven), og
  tjek tre ting: (1) er der PRÆCIS én lun detalje, ikke to; (2) er alvorlige
  historier friholdt — gennemgå alle motiver for perioden, ikke kun de ti;
  (3) er glimtet til at FÅ ØJE PÅ, eller forsvandt det i renderingen. Beslut
  derefter med Torben: behold, justér eller rul tilbage ("Tilbage til
  standard" i panelet). Instruksen ligger kun i hjerner.json — ingen kode er
  ændret.

- **`hjerner.json` mangler drift-værn ved Gem.** Er filen ændret siden panelet
  hentede sine tal (anden maskine, håndretning), skriver et gem ændringen ud af
  verden uden et ord. Et værn blev bygget og trukket tilbage 29.07: det afviste
  panelets eget andet gem (grundlaget blev ikke genopfrisket) og låste ved en
  afsluttende linjeskift i en prompt. Rettes det: genopfrisk grundlaget efter
  hver skrivning, og sammenlign uafhængigt af nøglerækkefølge. Rammer: kun
  redaktionen (2 personer), men tabet er tavst. Målt: hullet er reelt,
  fejlscenariet kræver to redigeringssteder.
| `## Mistanker` | Noget nogen har set, men ikke målt | Først når det er målt |
| `## Fast gennemgang` | Spørgsmål uden ende, på skift | Når der er plads |
| `## Venter på redaktionen` | Målt, men kræver en beslutning | Når du har svaret |
| `## Fravalgt` | Idéer der er sagt nej til, med begrundelse | Nej — og læses før nye skrives |
| `## Klaret` | Historik | Nej — genåbnes kun med en måling |

Hvert punkt siger, hvilket af de ti punkter i `redaktionens-oejne.md` det handler
om — og **hvem det rammer**, målt i sidevisninger de sidste syv dage. Uden det tal
er "det, der rammer flest læsere, kommer først" et gæt, og gættet har været
forkert: en hel uges arbejde gik på sider med to visninger tilsammen.

**Et punkt i køen skal kunne blive færdigt.** Det skal være noget, én session kan
gøre og teste, så feltet kan hakkes af og punktet forsvinder herfra. Et *mål* er
ikke et punkt: "ingen kan finde siden" kan aldrig blive færdigt, så det stod
øverst i dagevis og spærrede for alt under sig, mens hver kørsel bare skrev endnu
en måling på det. Mål hører hjemme i `redaktionens-oejne.md` — de ti punkter dér
er dét, køen bedømmes op imod. Kan et fund ikke skrives som "gør X, og mål Y
bagefter", er det enten en mistanke eller et mål, og så skal det ikke i køen.

**Dét, hele køen måles op imod — og som ikke selv er en opgave:** siden skal nå
nogen. Målt 28.07 kl. 05:45, syv dage: **261 besøg / 738 visninger**, hvoraf
**235 er direkte** — altså redaktionen selv, bogmærker og appen. Udefra kom
**19 besøg fra Facebook, 4 fra Google og 3 fra Buttondown**. De tre tal har
ikke rørt sig i to døgn, heller ikke efter at sitemappene blev indsendt 27.07.
Fem artikelsider har 1–3 visninger hver, men `sidehenvisere` siger "herfra selv"
på dem alle. Ethvert punkt i køen forbedrer altså noget, som **26 mennesker
udefra** ser om ugen. Det tal er baggrunden for rækkefølgen — det er ikke noget,
der kan klares. *Se `redaktionens-oejne.md`, punkt 10.*

**Og det er ikke en fejl.** Siden er under opbygning, og trafikken er de to, der
bygger den. Et lavt besøgstal er derfor baggrund, ikke et fund — se reglen
øverst i `## Fravalgt`, før du skriver et punkt, der hviler på et tal fra
`data/laesertal.json`.

---

## Kø

*Sorteret efter: (1) i stykker for læseren nu, (2) bryder målestokken synligt,
(3) gør siden mærkbart bedre. Kun målte problemer står her — resten ligger under
`## Mistanker` og `## Fast gennemgang` længere nede.*

### 1 — I stykker for læseren lige nu

*Ingen kendte lige nu.*

### 2 — Bryder målestokken synligt

*Ingen kendte lige nu.*

### 3 — Gør siden mærkbart bedre

- [ ] **Tjek at PWA'en stadig virker.** Service worker, manifest, ikoner —
      efter alle de seneste dages ændringer.
      **Rammer: 456 visninger/7 dage (forsiden)** — en stor del af den direkte
      trafik kommer sandsynligvis fra appen, så et brud ville ramme netop dem.
      *Punkt 4.*

- [ ] **`MAX_DAGE_GAMMEL` lover 30 dage og holder dage.** Redaktionen sagde ja
      28.07: artikler, der har en side, skal bevares i 30 døgn.
      **Målt 26.07 kl. 15 og bekræftet 28.07:** `main()` bygger listen forfra af
      det, feedene serverer *nu*, og bruger kun den gamle fil som cache pr. link.
      En artikel lever derfor præcis så længe, kildens RSS nævner den — **dage på
      et travlt feed**, ikke de 30 døgn, konstanten lover. I dag ligger der
      **168 sider i `artikel/` mod 145 i listen**.
      **Hvad en læser mister:** forsiden viser færre artikler, end den skulle, og
      enhver forbedring af artikelskabelonen rammer aldrig mere end den nyeste
      uge.
      **Mindste rettelse:** bevar artikler, der har en side på disken, indtil de
      30 dage faktisk er gået.
      **Mål før du bygger — to ting, redaktionen har accepteret prisen for, men
      som skal kendes:** (1) vægten. Forsiden henter hele `articles.json` i én
      blok, og den koster **781 bytes pr. artikel på tråden** (målt 26.07). De
      sidste to hele døgn tog 24 og 19 nye ind, så et rigtigt arkiv bliver
      **~570-600 artikler = 435-460 kB, cirka 7× mere end i dag**, hentet før der
      står noget på skærmen. Forsiden svarer i dag efter 173 ms og er færdig
      efter 634 ms; mål det igen bagefter og skriv tallet i loggen. (2) prisen.
      Tjek FØR du bygger, om de genoplivede artikler udløser nye AI-kald eller
      nye billeder — de har rubrik og resumé i cachen, men `lav_billeder` har sit
      eget udvalg. Koster det penge, så stop og spørg.
      **Rammer: 456 visninger/7 dage (forsiden).**
      *Punkt 4 og 6.*

- [ ] **39 dubletsider modsiger sig selv over for Google.** Målt 27.07:
      `_peg_dubletsider_mod_hovedhistorien` retter kun `<link rel="canonical">`.
      **Alle 39** har stadig et `og:url` og et JSON-LD-`url`/`@id`, der peger på
      dem selv — så siden siger på én gang "den rigtige udgave er derovre" og
      "jeg er den rigtige". Google bruger begge signaler, og modstrid er en
      kendt grund til, at en canonical bliver ignoreret; sker det, konkurrerer
      vores egne sider om samme søgning. **Intet er i stykker for et menneske**,
      og sådan har det været hele tiden — men det er billigt at rette samme sted,
      hvor canonical skrives, og det gælder hele arkivet. Mindste rettelse: sæt
      `og:url` og JSON-LD-`mainEntityOfPage` til samme adresse som canonical.
      **Rammer: 2 visninger/7 dage (artikelsiderne tilsammen).**
      *Punkt 5 og 10.*

- [ ] **En dubletside kan pege canonical mod en side, der aldrig bygges.**
      `_peg_dubletsider_mod_hovedhistorien` kaldes **før** `_har_noget_at_vise`-
      vagten og tjekker ikke, at vinderens side faktisk bliver skrevet.
      **Målt igen 27.07: 0 tilfælde** — og `_bryd_canonical_kaeder` nægter nu at
      pege på en side, der ikke findes, så hullet er delvist lukket. Tilbage står
      selve pegningen. Mindste rettelse: samme vagt i vinder-tjekket.
      **Rammer: 0 målte tilfælde og 2 visninger/7 dage på artikelsiderne.**
      *Punkt 4 og 10.*

- [ ] **Gennemgå crawlerens fejlbeskeder.** Er der steder, hvor noget fejler
      stille uden at sige hvorfor? Det var netop dét, der skjulte tre fejl —
      og 27.07 en fjerde: **8 canonical-kæder stod i et døgn**, uden at nogen
      kørsel sagde et ord, selvom `lav_artikelsider` skriver et tal ud hver gang.
      **Rammer: intet direkte — det er en måling, ikke en side.** Kan derfor
      aldrig stå højere end trin 3.
      *Punkt 6.*

- [ ] **Ryd op i `_to_delete/`.** Mappen ligger stadig i repoet med gamle
      workflow-filer. Er der noget, der skal gemmes, før den ryger?
      **Rammer: ingen læsere** — det er husholdning, ikke en fejl. Står i trin 3,
      fordi det er billigt, ikke fordi det haster. *Punkt 4.*

---

## Nyt

Ting, siden **bør kunne**, men ikke kan i dag. Ikke fejl — mangler.

Den her liste findes, fordi loopet indtil 28.07 ikke havde noget sted at skrive
dem. `## Kø` er defineret som *målte problemer*, og fase 2 leder efter fejl, så
sætningen *"siden bør kunne X"* kunne bogstaveligt talt ikke skrives ned nogen
steder. Resultatet var en maskine, der kunne gøre siden fejlfri og aldrig større.

**Reglerne her er andre end i `## Kø`:**

- Et punkt skal sige, **hvad en læser får**, som han ikke får i dag. Ikke hvad
  der er teknisk pænt.
- Der kræves **ikke** et rammer-tal. Det, der ikke findes, har ingen
  sidevisninger, og kravet ville gøre listen tom for altid.
- Der kræves til gengæld et svar på: **hvad er det mindste, der kan bygges og
  ses virke?** Kan du ikke svare, er det et ønske og hører hjemme i `oensker.md`.
- **Spørg først, hvis** det koster penge, sender noget ud, opretter en side, der
  skal linkes fra forsiden, eller ændrer et dataformat. Ellers byg det.
- **Mindst ét punkt skal stå her efter hver hovedkørsel**, og **mindst én ny ting
  skal bygges om ugen**. Er listen tom, er det ikke et godt tegn her — det
  betyder, at ingen har spurgt, hvad siden mangler.

- [ ] **En slettet kilde bliver ved med at blive linket til fra forsiden.**
      Målt 28.07: `andre`-posterne bæres videre i cachen pr. link, helt
      uafhængigt af hvilke feeds der hentes — `omskriv_nye` genskaber feltet fra
      `cache`. Lige nu står **Ingeniøren som ekstra kilde 3 gange, Version2 2,
      TechCrunch 3**. Sletter man en kilde, viser forsiden altså stadig
      "+1 kilder" med et klikbart link til den, indtil selve vinder-artiklen
      ruller ud af listen — dage.
      **Hvad læseren får:** at "fjern kilde" betyder fjern, også for de links,
      der allerede står. Panelet siger i dag ærligt, at det ikke sker; det er
      bedre end at lyve, men det er ikke det, knappen hedder.
      **Mindste ting, der kan bygges og ses virke:** når et link ikke længere
      hører til nogen kilde i `feeds.json`, fjernes det fra `andre` ved næste
      kørsel. Ingen ny datastruktur.
      *Punkt 4.*

- [ ] **En slettet kildes artikelsider bliver i sitemappet for altid.** Målt
      28.07 på de 178 sider i `artikel/`, talt på det udgående kildelink:
      TechCrunch 38, OpenAI 26, arXiv 25, Ars Technica 25, MIT Tech Review 15,
      The Verge 14, DeepMind 8. **Version2 og Ingeniøren har 0** — de er
      `kun_aktuel`, så der bygges aldrig en permanent side for dem.
      Sletter man fx Ars Technica, bliver de 25 sider liggende, står stadig
      blandt sitemappets 138 URL'er, og Google bliver ved med at blive inviteret
      ind på dem.
      **Det er ikke sikkert, det er forkert** — siderne er skrevet, de virker,
      og at slette dem ville give 404 på noget, Google allerede har indekseret.
      Spørgsmålet er, om en kilde, vi har sagt fra til, stadig skal have 25
      sider stående. **Det er en redaktionel beslutning, ikke en fejl.**
      **Mindste ting, der kan bygges:** tag siderne ud af sitemappet, men lad
      filerne ligge — så holder invitationen op, uden at noget går i stykker.
      *Punkt 4 og 10.*

- [ ] **`undervisning.html` findes, men ingen kan komme derhen.** Målt 28.07:
      siden er bygget og testet 26.07 og står i `sitemap.xml`, men **0 af de 33
      rodsider linker til den**. `laer.html` linker til 11 af 13 lære-sider —
      den her er den ene af de to, der mangler. Den er altså synlig for Google
      og usynlig for et menneske.
      **Mindste ting, der kan bygges og ses virke:** et link fra `laer.html`
      (88 visninger/7 dage) og en linje nederst på `koerekort.html` og
      `erhverv.html` — *"Vil du bruge det her på et hold?"* Ren HTML, ingen
      data, ingen penge.
      **Hvad læseren får:** en underviser, der er nået til slutningen af
      kørekortet, får at vide, at han må bruge det på sit hold. Det er vej 3 i
      `retning.md`, og den er den eneste af de tre, siden har et forspring på.
      **Redaktionen har sagt ja 28.07** til `laer.html`, `koerekort.html` og
      `erhverv.html`. **Forsiden er et nej** — den er nyheder, og det gælder også
      her. Spørg ikke om den igen.
      *Punkt 7.*

- [ ] **En læser kan ikke finde en artikel igen.** Målt 28.07: der ligger **168
      sider i `artikel/`**, men forsiden viser kun de **145**, der står i
      `data/articles.json` — og den liste bygges forfra af feedene hver kørsel,
      så en artikel forsvinder fra forsiden efter dage. Der er ingen søgning på
      tværs af arkivet, intet index over alle artikler, og ingen vej til de
      sider, der er rullet ud. Læste man noget her i sidste uge, kan man ikke
      finde det igen uden at gemme linket.
      **Mindste ting, der kan bygges og ses virke:** en side, der lister alle
      sider i `artikel/` med rubrik og dato, bygget af crawleren som
      `sitemap-artikler.xml` allerede bliver det. Ingen ny datastruktur, ingen
      AI-kald, ingen penge.
      **Hvad læseren får:** en vej tilbage til noget, han har læst — og Google
      får en side, der linker til alle 168 i stedet for 0.
      *Punkt 6 og 7.*

---

## Mistanker

Ting nogen har lagt mærke til, men ingen har målt. **De bliver ikke prioriteret
og bliver ikke lavet, før nogen har målt dem.** Det er meningen: halvdelen af de
punkter, der er blevet lavet, viste sig at være beskrevet forkert, fordi et fund
uden tal blev skrevet ind som en opgave. En mistanke er en fin ting at aflevere —
den skal bare stå her og ikke i køen.

Måler en session en mistanke efter, flytter den enten op i `## Kø` med sit tal
eller ud herfra med en note om, at der ikke var noget.

- **13 artikelsider er faldet ud af sitemappet, men ligger der stadig og siger,
  de er originalen.** Målt 27.07 kl. 21:05 af den første efterprøvning: der er
  161 sider i `artikel/`, 135 af dem peger på sig selv med canonical, men kun
  122 står i `sitemap-artikler.xml`. De 13, der mangler, er alle fra 26.07 —
  de er ikke i `data/articles.json` længere, og de er ikke `andre` under en
  anden artikel. De er bare rullet ud af feed-vinduet, mens siden blev
  liggende. Eksempler: «Oracle fyrer 21.000 ansatte efter AI-satsning»,
  «Googles nye ATLAS viser, hvordan vi bruger AI», «OpenAI udlover dusør for
  biologi-fejl». Det ser ud til at ske hver dag: en side er i sitemappet ét
  døgn og derefter aldrig igen. Rammer punkt 10 — men **hvor meget det koster,
  er ikke målt**: `data/laesertal.json` har `artikler: []`, altså nul målte
  visninger på artikelsider overhovedet, og om Google beholder en side, den
  har set én gang, ved vi ikke. Skal måles i Search Console, før det bliver
  til en opgave.

- **To sammenlægninger ser forkerte ud, men er ikke frigivet.** Noteret 27.07:
  «Er åben AI virkelig farligt?» ligger under «Nvidia og Mistral advarer mod at
  forbyde kinesisk AI», og «Claude taler nu ud med tre stærke hjerner» ligger
  under «Anthropic sender billigere AI-model på gaden». Læst med øjnene er det
  to forskellige historier. Maskinen frigiver dem ikke, fordi de deler
  henholdsvis 28 % af ordene og navnet "anthropic" med deres vinder — og en
  frigivelse af en artikel, der ikke længere er i feedet, kan ikke fortrydes.
  **Ikke målt:** hvor mange af den slags par der findes over tid, og om et
  strengere ord-krav (fx 25 % i stedet for 15 %) ville ramme dem uden at splitte
  ægte dubletter. Kun to eksempler er ikke et tal.

---

## Fast gennemgang

Spørgsmål uden ende. De bliver aldrig klaret — de forfalder bare igen, og derfor
hører de ikke til i en kø. Har sessionen plads, eller er køen tom, tages **den,
der har ventet længst**. Én time, ikke mere. Findes der et målt problem, skrives
det i køen; ellers noteres bare, at den holder. Sæt dagens dato på uanset hvad.

- **Hvad har Google faktisk indekseret?** Sitemappene blev indsendt 27.07;
  Search Consoles Sider-rapport er dét, der viser, om de 132 artikel- og
  videosider kommer med — og `data/laesertal.json` viser, om det giver besøg.
  Kræver browseradgang, så det kan kun gøres i en chat-kørsel. *Punkt 10.*
  *Sidst set: 27.07.2026 — indsendt, endnu ikke indekseret.*

- **Gennemgå kategoriseringen.** Ligger artiklerne i de rigtige kategorier,
  eller ender for meget i "Lanceringer"? *Punkt 6.*
  *Sidst set: aldrig.*

- **Virker siden uden JavaScript?** Artikelsiderne gør. Forsiden gør ikke.
  Er det et problem for Google og for folk med langsomme forbindelser?
  *Punkt 9.*
  *Sidst set: aldrig.*

- **AI-kørekortet, modul for modul.** Er sproget stadig til en nabo uden
  teknisk baggrund, eller har der sneget sig jargon ind? *Punkt 7.*
  *Sidst set: aldrig.*

- **Erhvervsoverbygningens fire moduler.** Samme gennemgang. Rammer de folk,
  der møder AI på jobbet — uden at blive konsulentsprog? *Punkt 7.*
  *Sidst set: aldrig.*

- **prompts.html og prompt-arkivet.** Er de 17 prompts stadig de bedste, vi
  kan lave? Er der gengangere mellem biblioteket og kartoteket? *Punkt 3.*
  *Sidst set: aldrig.*

- **vaerktoejer.html.** Er de 13 værktøjer og noterne stadig rigtige? Priser
  og funktioner skifter hurtigt — flag det, der ser forældet ud, i loggen
  i stedet for at gætte. *Punkt 5.*
  *Sidst set: aldrig.*

- **laer.html.** Er den stadig inspirerende, eller er den blevet en
  linksamling? *Punkt 7.*
  *Sidst set: aldrig.*

- **faq.html.** Svarer den på det, en ny besøgende faktisk undrer sig over?
  *Punkt 7.*
  *Sidst set: aldrig.*

- **En tilfældig artikelside.** Ser den professionel ud alene, uden forsiden
  omkring sig? Det er den, folk lander på fra Google. *Punkt 4.*
  *Sidst set: aldrig.*

- **En tilfældig videoside.** Samme prøve. *Punkt 4.*
  *Sidst set: aldrig.*

- **uge.html — ugens overblik.** Holder den stadig, eller er den blevet en
  opremsning? *Punkt 2.*
  *Sidst set: aldrig.*

- **om.html.** Stemmer beskrivelsen med, hvad siden faktisk gør i dag?
  Kildelisten er ændret, og DeepSeek er på vej ind. *Punkt 5.*
  *Sidst set: aldrig.*

- **Læs `data/opslag.json` igennem, når der er udkast i den.** Er tonen i
  de automatiske opslag noget, redaktionen ville skrive selv? *Punkt 5 og 8.*
  *Sidst set: aldrig.*

---

## Venter på redaktionen

Målt og forstået, men må ikke bygges, før nogen har taget stilling. De sorteres
ikke med i køen, og sessionen skal ikke gætte svaret.

- **Hvor skal læserne komme fra?**
  *Målt 27.07, syv dage: 19 besøg fra Facebook, 4 fra Google, 3 fra Buttondown —
  resten er direkte. Sitemappene er nu indsendt, og det kan hjælpe hos Google,
  men kun hos Google. Opslagsmaskinen er bygget og kører tørt (`OPSLAG_LIVE`
  står på nej), og der findes hverken en Facebook-side, en LinkedIn-side eller
  en Bluesky-konto. Sessionen må ikke oprette konti eller sende noget ud på
  nogen platform. Uden en beslutning her kan intet punkt i køen flytte tallet —
  se `## Ting kun et menneske kan gøre` nederst.*

- **Er det tid at flytte gamle billeder ud af git?**
  *Spørgsmålet: mappen vokser nu med 25–30 MB om måneden og kan ikke rydde op
  længere. Skal sider ældre end X måneder pege på `assets/og.png` i stedet — og
  hvad er X? Eller er repoets størrelse ikke et problem endnu?*

  `data/img/` kan ikke længere rydde op efter sig. Fra 26.07 sletter
  oprydningen aldrig et billede, en side på disken peger på — det var
  rettelsen, der fjernede 25 brudte billeder. Prisen er, at **62 af 69 filer
  nu er permanente**, og at mappen vokser med ~10 billeder à 88 kB på travle
  dage, altså 25–30 MB om måneden i git. Hæves `BILLED_STIL_VERSION`, låses
  hele det gamle sæt fast oveni. Intet er i stykker; spørgsmålet er, hvornår
  repoet bliver ubehageligt stort. Mindste rettelse er formentlig at flytte
  billeder for sider ældre end X måneder ud af git og lade siderne pege på
  `assets/og.png` — men det er redaktionens valg, om det er værd at gøre endnu.
  *Punkt 4.*

---

## Fravalgt

Idéer, der er sagt nej til, og hvorfor. **Læs listen, før du skriver nye punkter.**
Står dit fund her, skal det ikke i køen igen — medmindre du kan måle, at
grundlaget har ændret sig, og så skal målingen med.

Loggen fortæller kun, hvad der blev lavet. Uden den her liste kommer den samme
afviste idé igen om en måned og koster den samme udredning forfra.

- **"De 168 artikelsider har ingen vej til lære-indholdet"** — fravalgt
  28.07.2026, af mig selv, samme dag jeg skrev det, og af samme grund som
  punktet nedenfor. Overskriften modsagde punktets egen måling: der stod sort på
  hvidt, at hver artikelside linker til `/laer.html` — og `laer.html` linker til
  11 af de 13 lære-sider. Vejen findes. Den går bare gennem ét link, og det er
  ikke det samme som ingen vej.

  **To falske fund på én formiddag, begge skrevet af mig, begge slået ihjel af
  min egen måling en time senere.** Fælles årsag: fase 2 leder efter fejl, og
  når man leder efter fejl, kan man altid finde en formulering, der lyder som
  en. Begge punkter talte noget nemt (links på én sidetype) og konkluderede om
  noget andet (om læseren kan komme frem). Prøven, der ville have fanget dem
  begge, er at spørge: *kan en læser faktisk ikke gøre det her?* — og så prøve
  det, i stedet for at tælle.

- **"Forsiden linker kun til én af syv lære-sider"** — fravalgt 28.07.2026, af
  mig selv, samme dag jeg skrev det. Punktet talte døre på forsiden og
  konkluderede, at lære-indholdet var utilgængeligt. Målingen en time senere
  siger noget andet: **`laer.html` linker til 11 af de 13 lære-sider** —
  kørekortet, erhverv, prompts, prompt-arkivet, ordbogen, quizzen,
  værktøjslisten, alle tre guider og FAQ'en. Forsiden linker til `laer.html`,
  og `laer.html` linker til resten. Strukturen er altså ikke i stykker; den er
  et nav med én indgang.

  Tallene bekræfter det: `laer.html` 88 visninger/7 dage, `koerekort.html` 26,
  `prompts.html` 14, `faq.html` 9. Folk kommer igennem. Og de tre sider med nul
  besøg — prompt-arkivet, quizzen og værktøjslisten — **er linket fra
  `laer.html`**, så manglende links kan ikke være forklaringen på deres nul.
  Det er stadig bare, at der ikke er nogen endnu.

  Lærestykket er ubehageligt og hører til her: jeg målte det, der var nemt at
  tælle (links på én side), og skrev en konklusion om noget andet
  (tilgængelighed på tværs af siden). Redaktionen sagde desuden samme dag, at
  forsiden skal være nyheder. De to eneste sider, `laer.html` IKKE linker til,
  er `undervisning.html` og `koerekort-tjek.html` — den første har sit eget
  punkt, den anden nås fra selve kørekortet, hvor den hører hjemme.

- **"Send Dagens overblik som daglig mail"** — fravalgt 28.07.2026 af
  redaktionen. Undersøgelsen fra 25.07 (`undersoegelse-daglig-mail.md`) holder
  teknisk: Buttondowns gratis plan tillader udtrykkeligt én daglig mail, og
  maskineriet findes. Men **abonnenterne har sagt ja til én mail om ugen**, og
  at begynde at sende dagligt er en anden aftale end den, de indgik. At lade dem
  vælge selv koster $9/md, og det er ikke pengene værd nu. Genåbnes kun, hvis
  abonnenterne bliver spurgt.

- **"Kørekort-indgang på forsiden"** — fravalgt 28.07.2026 af redaktionen.
  Forslaget fra 25.07 ligger stadig i `_redaktion/forslag-koerekort-indgang.html`
  og bliver ikke bygget: **forsiden er nyheder.** Vejen til kørekortet går
  gennem `laer.html`, og de 26 visninger på syv dage viser, at den vej virker.
  Sessionen skal ikke foreslå det igen — heller ikke i en anden indpakning.

- **"Få eller nul besøg er i sig selv et problem"** — fravalgt 28.07.2026 af
  redaktionen, og det er en regel, ikke en enkelt afvisning.

  Siden er under opbygning, og den trafik, der er, er de to, der bygger den. Et
  besøgstal på nul måler derfor ikke, om en side er god, eller om den kan
  findes. Det måler, at siden endnu ikke har et publikum — og dét kan ingen
  session lave om på. Et punkt, der bygger på tallet, kan aldrig hakkes af, så
  det bliver stående og fylder, mens det siger det samme hver dag.

  **Regel herfra: ingen session må skrive et punkt i `## Kø`, hvis dets eneste
  begrundelse er få eller nul besøg eller visninger.** Det gælder alle sider —
  faste sider, artikelsider og videosider. Tallene skal stadig måles, stadig
  stå som `Rammer:` og stadig bruges til at sortere rækkefølgen af det, der ER
  målt i stykker. De kan bare ikke selv gøre noget til et fund.

  Et fund, der handler om en side med lav trafik, skal altså kunne stå på egne
  ben uden tallet: *"forsiden linker ikke til den"* holder, *"ingen har besøgt
  den"* gør ikke. Reglen falder bort, når siden har rigtige læsere udefra, og
  det er redaktionens afgørelse, hvornår det er.

- **"Tre faste sider fik nul besøg på syv dage"** — fravalgt 28.07.2026 efter
  reglen ovenfor. `prompt-arkiv.html`, `quiz.html` og `vaerktoejer.html` stod på
  nul besøg og nul visninger både 27. og 28.07, og det er stadig sandt. Det er
  bare ikke et fund. Den halvdel af punktet, der kan måles uafhængigt af
  trafik — at forsiden ikke linker til dem — står nu som eget punkt i `## Kø`
  under overskriften *"Forsiden linker kun til én af syv lære-sider"*.

---

## Klaret

- [x] **Kontrolpanelet kan nu vise og redigere nyhedskilderne.** *(28.07.2026,
      chat — bedt om af redaktionen direkte)* Ny sektion "Kilder" i panelet, og
      `data/kilder.json` + `kilder-data.js` skrevet af crawleren ved hver
      kørsel — også på Actions, fordi crawleren er eneste skribent dér og der
      derfor ikke er en flettekonflikt at frygte.

      **Viser:** pr. kilde hvad feedet gav (`hentet`), hvad der endte på
      forsiden (`i_listen`) og hvor tit kilden står som ekstra kilde under en
      anden histories overskrift (`som_ekstra`). De tre tal er ikke ens, og det
      står i manchetten hvorfor. **Målt ved bygningen: VentureBeat AI havde 0 og
      0** — hentet 19 gange i døgnet uden at give noget.

      **Fold ud pr. kilde** viser dens seneste artikler, med de dubletter, der
      lå under en anden kildes overskrift, tydeligt markeret og med navnet på
      den historie, de lå under. Dertil en linje pr. kilde om, hvem den skriver
      det samme som. **Målt: Version2 og Ingeniøren overlapper 4 gange**,
      TechCrunch og MIT Tech Review 2. Det er dét, der skal kunne afgøre, om en
      kilde kan undværes.

      **Redigering:** slå til/fra (nyt felt `aktiv` i `feeds.json`; kun præcis
      `false` slukker, så en halvskrevet værdi ikke kan slukke for nyhederne),
      slet med to tryk, og tilføj med navn/adresse/kategori/loft. Gemmes tilbage
      i `opsaetning/feeds.json` med samme fil-vælger, køen bruger. Panelet kan
      ikke selv prøve en ny adresse — browseren blokerer det fra `file://` — så
      crawleren melder tilbage, og en ny kilde står som "ikke hentet endnu",
      indtil den har kørt.

      **Prøver:** `_redaktion/proeve-kilder.py` **40 grønne / 0 røde** og
      `_redaktion/proeve-kilder.js` (jsdom mod det rigtige panel) **66 / 0**.
      **17 mutationer**, alle fanget.

      **Den uafhængige gennemgang fandt fem ting, og den første var alvorlig:**
      panelets `esc()` escaper ikke anførselstegn — den blev skrevet til tekst
      mellem tags — og jeg brugte den i to attributter. Et link fra et fremmed
      RSS-feed med et `"` kunne køre kode i panelet, og en kilde ved navn
      `Wired "AI"` ødelagde fold-ud-knappen uden en eneste fejlbesked. Ny
      `escA()` til attributter. Dertil: fold-ud-loftet skar præcis de dubletter
      væk, listen findes for (de har ofte intet `foerst_set`, så de sorterede
      sidst — Ars Technica stod med "som ekstra 1" og nul at folde ud);
      panelet kunne skrive et forældet øjebliksbillede tilbage og rulle en
      tidligere ændring tilbage i tavshed (nu står der, hvor gammelt det er, og
      knappen er låst, indtil noget er rørt); `som_ekstra` talte en kilde under
      sig selv med; og to mutationer overlevede prøven. Alt rettet.
      *Punkt 4 og 6.*


- [x] **Frigivelsen ruller kun `andre` tilbage — vinderen beholder taberens
      tidspunkt og billede.** *(28.07.2026, hovedkørsel kl. 05:45-07:1x — chat
      med Torben)* Rettet i `crawler.py` alene, +226 linjer / −5.

      **Målingen vendte punktet om.** Køen talte artikler **med** `andre`; men en
      frigivet vinder har jo ikke længere `andre`, så skaden ligger i den anden
      gruppe. Målt 28.07: **3 af 137 artikler uden `andre`** har `foerst_set`
      mere end en time før deres `dato` — og **2 af de 3 er præcis de to
      vindere, hvis tabere blev frigivet 27.07**. «Strømsvigt i Washington»
      (udkom 25.07 kl. 13:05) og «Biblioteker afholder 'Avoiding AI'-workshops»
      (udkom 25.07 kl. 16:00) lå begge på forsiden under **23. juli**.

      **Beviset står i git, ikke i et skøn:** «Strømsvigt» havde selv
      `foerst_set` 2026-07-25T16:26:44 (commit `05ce75b`) og bar
      2026-07-23T20:37:15.313153 — **præcis** `foerst_set` på «Eks-googlere bag
      AegisAI» (commit `c137a3d`), den kilde, den var sammenlagt med.

      **To fejl mere med samme rod, rettet i samme omgang:** et medlem, vagten
      lige havde **afvist**, kunne aflevere både tid og billede til
      hovedhistorien (koden brugte `medlemmer`, ikke de beholdte), og billedarven
      blev aldrig registreret, så en frigivelse hverken kunne give billedet
      tilbage eller lade være.

      **Gjort:** `_saet_foerst_set()` gemmer `eget_foerst_set` ved artiklens
      fødsel — det eneste sted, tiden med sikkerhed er dens egen.
      `_rul_arven_tilbage()` giver tid og billede tilbage ved en frigivelse, men
      kun hvis værdien stadig ER den lånte. `laant_billede = {fra, billede,
      motiv}` husker både hvem og hvad. `_gulv_paa_laante_tider()` retter de to
      gamle, som ingen frigivelse kan hjælpe, med en grænse på **24 timer**, der
      er målt over **163 udgaver af `articles.json`**: kun fire artikler uden
      `andre` har nogensinde haft `foerst_set` før `dato` — 5,54 t og 0,55 t
      (lovlige) mod 40,5 t og 47,0 t (fejlene).

      **Prøven:** `_redaktion/proeve-arv.py`, **65 grønne, 0 røde** — kørt mod
      `HEAD` også: 29 grønne, 36 røde før. **15 mutationer** kørt, hver eneste
      fanges. Mod de rigtige data ændrer hele rettelsen **præcis to felter**.
      Den uafhængige gennemgang læste arbejdet **tre gange og fandt 19 ting**,
      heriblandt fire mutationer, der overlevede prøven. Alt rettet på ét nær,
      som er bevidst fravalgt: at lade gulvet skrive `eget_foerst_set` ville
      registrere en udledt værdi som artiklens egen og bryde punkt 5.
      *Punkt 4, 5 og 6.*

- [x] **Loopet efterprøver aldrig sit eget arbejde — 36 klarede punkter, 0
      efterprøvninger.** *(27.07.2026, ekstra kørsel kl. 21:00-21:15 — chat med
      Torben)* Bedt om af Torben direkte.

      **Fundet:** loggen og køen kan fortælle, hvad der blev *gjort*. Intet sted
      står der, om det var *rigtigt*. Fase 0 tjekkede kun sidste kørsels arbejde,
      som stadig er varmt — de gamle rettelser så ingen på igen.

      **Gjort:** nyt punkt 4b i fase 0. `_redaktion/efterproev.py` vælger
      deterministisk ét modent punkt fra `## Klaret`; sessionen citerer punktets
      hovedpåstand ordret, måler den igen og skriver ét af tre udfald ind:
      *holder* / *gik i stykker igen* / *kan ikke måles herfra*. Karens 21 døgn
      for det første, 7 for de to andre — et mærke er ikke en fritagelse på
      livstid.

      **Resultat:** 36 punkter i `## Klaret`, hvoraf 2 var modne (mindst 2 døgn
      gamle). Den første efterprøvning kørte og fandt 13 artikelsider, der er
      faldet ud af `sitemap-artikler.xml` — se `## Mistanker`.

      **Prøven:** `_redaktion/efterproev-proeve.py`, 45 prøver, 0 røde. Den fandt
      selv en fejl, der ville have gjort hvert mærke evigt. Den uafhængige
      gennemgang fandt syv ting, herunder at det første mærke var selvros —
      rettet.

      **Målingen modsagde planen:** jeg havde lovet "et punkt fra for en uge
      siden". 0 af 36 punkter var en uge gamle. Grænsen blev to døgn.

- [x] **En fejlsammenlægning kan ikke fortrydes — 16 artikler var låst under en
      historie, de ikke handler om.** *(27.07.2026, ekstra kørsel kl. 20:20-20:45
      — chat med Torben)* Målt på `data/articles.json` (138 artikler) med
      crawlerens egne funktioner.

      **Fundet:** den deterministiske vagt, punktet oprindeligt bad om, var
      allerede committet kl. 19:18 i `d95c041` uden at nogen logfil blev rørt.
      Den virker — slugte artikler faldt fra 47 til 16, vindere med `andre` fra
      15 til 12. Tilbage stod fortrydelsen: trin 0 krævede, at **begge** udgaver
      stod i dagens liste, men `articles.json` bygges forfra af feedsene hver
      kørsel, mens `andre` arves videre (linje 1645). **0 af de 16 tabere var i
      dagens liste**, så frigivelsen kunne fyre for ingen af dem, og
      `_slaa_sammen` gemte kun `{kilde, link}` — taberens tekst var kastet væk.

      **Gjort:** `_slaa_sammen` gemmer nu taberens rubrik og resumé (klippet ved
      400 tegn), og `_taberens_udgave` kan hente teksten fra den frosne side i
      `artikel/`, når taberen er væk fra feedet. Er taberen ude af feedet, kan en
      forkert frigivelse ikke rettes af en ny sammenlægning senere i samme
      kørsel, så beviset er strengere: `_deler_intet` kræver, at **begge** ben i
      `_samme_sag` falder — hverken fælles ord over 15 % eller ét fælles navn.
      `_giv_frigivne_deres_canonical_tilbage` retter bagefter siden på disken, så
      den frigivne artikel kommer tilbage i sitemappet.

      **Resultat, målt:** **2 af de 16** slippes løs i dag — «Eks-googlere bag
      AegisAI skaffer millioner» (lå under «Strømsvigt i Washington») og «Meta
      vælger dyster sang til glad AI-reklame» (lå under «Biblioteker afholder
      'Avoiding AI'-workshops»), begge med 0 % fælles ord og intet fælles navn.
      Punktet pegede oprindeligt på fire par; de to sidste bliver liggende, og
      det er med vilje: «Er åben AI virkelig farligt?» deler 28 % af sine ord med
      sin vinder, og «Claude taler nu ud med tre stærke hjerner» deler navnet
      "anthropic". En frigivelse, der ikke kan fortrydes, skal ikke bygge på så
      tyndt et grundlag. De to står nu under `## Mistanker`.

      **Prøven:** `/tmp/frigiv-proeve.py`, 30 grønne, 0 røde — kørt mod de
      rigtige datafiler, men mod en **kopi** af artikelsiderne, så arkivet ikke
      røres. En uafhængig gennemlæsning fandt fire ting undervejs; tre er rettet
      (den strenge regel, ét-forsøgs-risikoen i diskrettelsen, og at trin 0 nu
      rører disken og skal tåle en ulæselig fil), og den fjerde står nu som
      punkt 1 i køen. *Punkt 1, 4, 6 og 10.*

- [x] **To af tre sitemaps var aldrig indsendt i Search Console.**
      *(27.07.2026, ekstra kørsel kl. 19:45 — chat med browseradgang)* Det stod
      i køen som en formodning, ingen kunne måle. Målt direkte i Search Console:
      `sitemap.xml` var indsendt 22.07 (Succes, 30 sider), men
      **`sitemap-artikler.xml` (91 sider) og `sitemap-videoer.xml` (41 sider)
      var aldrig indsendt** — Google havde aldrig fået at vide, at de 132
      artikel- og videosider fandtes. Begge er nu indsendt: artikler gik straks
      til **Succes / 91 sider**, videoer står på "Kunne ikke hentes", som er den
      kendte ventestatus lige efter indsendelse (XML'en er verificeret gyldig,
      41 `<loc>`, HTTP 200). Om det flytter læsertallet, kan først måles om
      nogle dage — dét spørgsmål står nu i `## Fast gennemgang`. *Punkt 10.*

- [x] **Indsend sitemappene i Google Search Console.** *(27.07.2026, ekstra
      kørsel i chat)* Chat-sessionen har adgang til redaktionens browser og
      målte i stedet for at gætte: sitemap.xml var indsendt 22.07, men
      sitemap-artikler.xml (91 sider) og sitemap-videoer.xml (41 sider) var
      aldrig indsendt. Begge indsendt; artikler gik straks til Succes/91.
      Effekten måles i GSC's Sider-rapport og laesertal.json. *Punkt 10.*

- [x] **Er dagens overblik virkelig dagens vigtigste fem?** *(målt 27.07.2026 i
      fase 2)* **Ja — intet at rette.** `lav_dagens_brief` tilbyder AI'en de 12
      højest prioriterede artikler set inden for 26 timer. Af dagens 5 punkter er
      **4 blandt de 5 højest prioriterede**, alle 5 kommer fra kandidatlisten
      (ingen opfundne), og prioriteterne falder pænt 8-7-6-5-5. Den ene afvigelse
      er et bevidst valg: AI'en tog "Regeringen tester AI til at afgøre din
      behandling" (prio 5) frem for "Sådan puster Kina-panik AI-debatten op"
      (prio 6) — en historie, der rammer læserens eget liv, frem for en
      debat-analyse. Det er redaktionelt rigtigt. *Punkt 6.*

- [x] **Tjek dubletfangeren.** *(27.07.2026)* Undersøgelsen spurgte, om
      `saml_dublet_historier` var for **forsigtig**. Målingen viste det modsatte,
      og svaret står nu som et målt punkt øverst i køen i stedet: 47 artikler er
      slået sammen, median ordoverlap 3,4 %. Undersøgelsen er dermed lukket.

- [x] **7 levende artikler var usynlige for Google og viste gamle rubrikker.**
      *(27.07.2026 — fund uden for køen)* **8 af 112 artikelsider stod i en
      canonical-kæde** (A → B → C), fordi `_peg_dubletsider_mod_hovedhistorien`
      peger en tabers side mod vinderen og aldrig ser på den igen — og vinderen
      blev selv slået sammen bagefter. **7 af de 8 var levende, selvstændige
      artikler**, som forsiden viser og deleknapperne deler, men hvis side
      fortalte Google, at den rigtige udgave var en urelateret historie ("Ny
      gratis AI-videoredigering til din Mac" → "AI Kill Switch Act"). Fordi
      `_dubletsider_paa_disk` læser netop den canonical, stod **0 af de 7 i
      sitemappet**. Nyt `_bryd_canonical_kaeder()` rører kun kædehoveder — en
      almindelig dublet står urørt, også når vinderen mangler i dagens liste.
      Efter: **0 kæder, sitemappet 53 → 60**. Da de 7 holdt op med at være
      dubletter, blev de bygget forfra og fik deres **navne** tilbage:
      "Politikere kræver nødstop" → "Ted Lieu og Nathaniel Moran vil have
      nødstop på AI". 135 påstande grønne i en prøve, der bygger sine egne
      kæder, plus 21 på de reparerede sider. *Punkt 1, 5 og 10.*

- [x] **Nyhedsbrevet, feedet og ugesiden linkede med `#a=` i stedet for den
      permanente side.** *(27.07.2026)* Rettet ét sted: nyt `_dele_link()` i
      `crawler.py`, brugt af `lav_rss`, `_uge_side_html`, `_send_nyhedsbrev` —
      og af opslagene, som var et fjerde sted, køen ikke nævnte. Køens forslag
      om at skrive `side` med i `uge.json` viste sig **unødvendigt**: slugget er
      en ren md5 af linket, så vi kan slå siden op på disken og rammer dermed
      også historier, der for længst er ude af `articles.json` — netop dem,
      `#a=` ikke kan finde. Ingen dataformat-ændring. **Målt efter: feed.xml
      20 af 40 permanente**, og de 20 andre er alle `kun_aktuel`, hvor
      udgiveren forbyder et arkiv — de *skal* have `#a=`. **Ugens otte
      kandidater lige nu: 8 af 8 permanente**, så næste fredags nyhedsbrev
      bliver 5 af 5. 86 påstande grønne; prøven kørt mod `HEAD` også: 25 røde
      før, 0 efter. *Punkt 6 og 10.*

- [x] **Et delt link til en historie, der er faldet af forsiden, gjorde
      ingenting.** *(27.07.2026)* Routeren slog `#a=<kildens URL>` op i
      `articles.json` og havde intet `else`. Fandt den ikke historien, skete der
      **ingenting** — ingen fejl, ingen besked, bare forsiden. Målt 27.07: **5 af
      5 links på `uge.html` var døde** på præcis den måde, og samme form bruges i
      `feed.xml` (40 links), i det ugentlige nyhedsbrev og i hvert link, en læser
      har delt. Rettet ét sted i `index.html`: nyt `aabnDeltLink()` slår nu også
      op i `andre`, så en historie, der er slået sammen under en anden kilde,
      stadig åbner (**47 sådanne links findes lige nu**), og ellers vises en
      besked, der siger hvad der skete og linker videre til kilden. Kun
      `http(s)` bliver klikbart, og hash'et fjernes bagefter. **39 påstande
      grønne — og prøven kørt mod `2a2cfe3` også: 13 røde før, 0 efter.**
      Samlet prøve på forsiden: 12 grønne. *Punkt 4, 6 og 10.*

- [x] **Tjek at alle interne links virker.** *(målt 26.07 kl. 23:40, lukket
      27.07)* **2.861 interne referencer på 185 sider peger alle på en fil, der
      findes** — 33 rodsider, 111 artikelsider, 41 videosider, 3.583 referencer i
      alt. Sitemaps (30 + 53 + 41 URL'er), `manifest.json`, `llms.txt`, `sw.js`
      og `feed.xml`: nul døde. De 15 "døde links" i første måling var parserens
      egne — den læste JavaScript-skabeloner (`${esc(a.link)}`) som adresser — og
      `#udgiver` / `#hjemmeside` er JSON-LD-id'er, ikke links. **Det eneste
      virkelige hul var `uge.html`s fem `#a=`-links**, og det har sit eget punkt
      ovenfor, som er klaret. *Punkt 4.*

- [x] **`sitemap.xml` manglede én side, ikke tre.** *(26.07.2026, ekstra kørsel
      kl. 17:05)* Målt: 33 HTML-filer, 29 URL'er, fire filer udenfor — og **tre
      af de fire er rigtige at holde ude**: `404.html` er en fejlside, og
      `tak.html` + `velkommen.html` har begge `noindex`, så en invitation til dem
      ville modsige sig selv. Det var bare aldrig skrevet ned, og dét var køens
      egentlige klage. **Kun `undervisning.html` var en reel mangel** — 6.232 tegn
      synlig tekst, egen canonical, ingen `noindex`, og **intet på sitet linker
      til den** (søgt i alle 33 filer), så Google kunne slet ikke nå den. Punkt
      10. Lagt ind (29 → 30 URL'er) og begrundelsen for de tre andre skrevet ind i
      filen. Dertil: `sitemap.xml` er den **eneste** af de tre sitemaps, der er
      håndskrevet, så nyt `tjek_statisk_sitemap()` i `crawler.py` siger nu til i
      Actions-loggen, hvis listen falder bagud — glemt side, `noindex` sluppet
      ind, eller URL uden fil. Skriver intet, retter intet, kan ikke vælte et
      crawl. **12 påstande, alle grønne** — testet at den *fanger* fejl, ikke kun
      at den er tilfreds, plus vrøvl-input. **Venter på en beslutning:** siden er nu
      synlig for Google, men **intet linker til den for en læser** — hvor den skal
      stå er hans valg.

- [x] **Tilgængelighed: tastatur og kontrast.** *(26.07.2026, ekstra kørsel kl.
      17:05)* **Tastaturets grundlag var i orden — men læseren var i stykker.**
      Alle interaktive elementer er ægte `<button>`/`<a>` (nul `onclick` på en
      `div`), og fokusringen er intakt: kun **ét** `outline:none` i filen, på
      søgefeltet, som har sin egen `:focus`-erstatning. **Rør ikke ved det.**
      Tre ting holdt ikke: (1) **24 tabtryk** fra sidens start til første rubrik
      og intet spring-over-link; (2) **læseren efterlod fokus bag sit eget
      overlay** — `aabnLaeser` kaldte aldrig `.focus()`, så vejen til Luk var
      **40 tabtryk, 39 gennem usynlige elementer**, mens `aria-modal="true"`
      lovede, at de 72 elementer udenfor ikke fandtes; (3) **3 af 97
      tekststilarter** under WCAG AA. Rettet i `index.html` alene (95 linjer ind,
      5 ud): spring-over-link, `<main>` som fokusmål, dialogen fik `tabindex`,
      navn og en Tab-fælde, fokus flyttes til rullebeholderen ved åbning og gives
      tilbage til kortet ved luk, og to farver mørknet (`--yt-roed` 4,38 →
      **4,63**; `.laest-maerke` 3,41 → **4,95**). **64 påstande, alle grønne** —
      den samlede prøve kørt mod `git show HEAD` også: 18/21 før, 21/21 efter.
      **To målefejl hos mig selv blev smidt undervejs:** en kontrast på 1,17:1 var
      min parsers manglende `color(srgb …)`, og påstanden om at artiklen ikke kan
      rulles med tastatur **kunne ikke bevises** — værktøjet kan ikke sende
      tastetryk til siden. **Venter på en beslutning:** tryk PageDown i en åben artikel
      én gang og bekræft, at den ruller. Se loggen.

- [x] **Hvor hurtigt loader forsiden?** *(26.07.2026, ekstra kørsel kl. 16:45)*
      **Intet er vokset sig for stort.** Målt på den levende side med cachen
      forbigået: GitHub serverer gzip, så første besøg henter **ca. 225 kB på
      tråden** — `index.html` 29 kB (102 på disken), `articles.json` 62 kB (206 på
      disken), `youtube.json` 17 kB, `brief.json` 1 kB, `skrifter.css` 2 kB og 113
      kB skrifter. Svar efter **173 ms**, DOM klar efter **408 ms**, færdig efter
      **634 ms**. To ting er sat rigtigt op og må ikke "rettes": `unicode-range` i
      `skrifter.css` gør, at browseren kun henter **2 af 4** skriftfiler — ikke ét
      tegn i `index.html` eller i seks tekstfelter på alle 81 artikler falder i
      latin-ext, så de 144 kB hentes aldrig — og billederne er `loading="lazy"`,
      så første indlæsning henter **1** billede, ikke 34. Ingenting ændret. **Men
      målingen gav et tal, arkiv-spørgsmålet under `## Venter på redaktionen` manglede:** 781 bytes pr.
      artikel på tråden, og de sidste to hele døgn tog 24 og 19 nye ind, så et
      rigtigt 30-dages-arkiv bliver ~570–600 artikler = **435–460 kB, cirka 7×
      mere end i dag**, hentet i én blok før der står noget på skærmen. Se loggen.

- [x] **Forsiden på en telefon.** *(26.07.2026, ekstra kørsel kl. 16:28)* **Den
      holder — ingen kode ændret.** Forrige kørsel skrev, at det ikke kunne måles,
      fordi der ikke er nogen browser i sandkassen. Det er stadig sandt, men den
      forkerte kasse: Chrome kører på Torbens maskine. Forsiden i en **390 px
      iframe** mod live-siden giver en ægte telefon-viewport, fordi media queries i
      en iframe reagerer på iframens egen bredde. Målt på hele siden (9.274 px):
      **0** elementer bredere end skærmen, **0** der stikker ud, **0 px** vandret
      rul, **0** tekster der flyder ud af deres egen kasse. Hit-test af topbjælken i
      skridt af 5 px: hvert tryk rammer det, det ser ud som. Begge bekymringer i det
      gamle punkt faldt: det 35-tegns token er ude af data (**81 af 81** artikler
      har `resume_da`, så `resume`-tilbagefaldet fyrer ingen steder), og en
      stress-prøve med tokens på 26–138 tegn i seks tekstfelter gav **0 px**
      udflydning overalt undtagen `.mikro-meta` — og de felter kan højst rumme 11
      tegn, fra lukkede lister. Ingen CSS lagt ind: målestokken siger, at teknisk
      gæld en læser ikke kan mærke, ikke er et problem. 11 påstande på forsiden i
      jsdom, alle grønne. **Til hovedkørslen: metoden kan genbruges** — flere punkter
      i køen er lukket med "kan ikke måles herfra", og det gælder ikke længere.

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

      **Efterprøvet 28.07.2026: holder.** Hovedpåstanden er «2 af 56 links på
      forsiden fører til lære-indhold, 0 direkte til kørekortet, og ordet
      "kørekort" står ikke ét sted». Målt igen i jsdom mod den rigtige
      `index.html` og de rigtige datafiler: den tegnede forside har i dag **93
      links, 16 interne**, og **2 af dem fører til lære-indhold — begge til
      `laer.html`**. 0 til `koerekort.html`, 0 til `prompts.html`, 0 til
      `ordbog.html`, 0 til `prompt-arkiv.html`, 0 til `quiz.html`, 0 til
      `vaerktoejer.html`. Ordet "kørekort" står **0 gange** i den tegnede tekst.
      Nævneren er vokset fra 56 til 93, fordi siden er blevet større; tælleren
      er den samme. Bemærk dog: kørekortet får trods alt **26 visninger/7 dage**
      — vejen går gennem `laer.html`, som har 88.

- [x] **Ingen ved, om Google har set de 83 artikelsider.** *(25.07.2026)*
      Sitemappene svarer korrekt live — 102 + 40 URL'er, alle sider 200, 404
      virker. Men Google har indekseret 0 artikelsider og 0 videosider; kun 7
      statiske sider er inde. Sitemappene er aldrig indsendt, og det kan kun
      Torben gøre — instruksen står i nat-loggen. Undervejs viste målingen, at
      alle 102 artikelsider manglede NewsArticle-schema (videosiderne havde det),
      at alle 129 billeder havde tom alt-tekst, og at en rubrik med `</script>`
      kunne ødelægge den strukturerede data. Alt tre rettet og testet.

      **Efterprøvet 27.07.2026: kan ikke måles herfra.** Punktets egen påstand
      er «Google har indekseret 0 artikelsider og 0 videosider». Det tal står
      kun i Search Console, og sessionen kan ikke se det — så udfaldet er ikke
      "holder", uanset hvor meget andet der kunne måles. Torben indsendte
      sitemappene 27.07; om Google har set dem, ved vi tidligst om nogle dage.
      Det, der KUNNE måles i dag, holdt: 161 artikelsider på disken, 0 uden
      NewsArticle-schema (var 102 af 102 uden), 81 billeder, 0 med tom
      alt-tekst, og vagten mod `</script>` står stadig i crawler.py — også på
      de 59 sider, der er bygget siden.
      **Men målingen fandt noget nyt:** 13 af de 135 kanoniske artikelsider er
      ikke længere i `sitemap-artikler.xml`. Se `## Mistanker`.

---

## Ting kun et menneske kan gøre

Disse venter på ham — sessionen skal ikke forsøge dem:

- Læg `DEEPSEEK_API_KEY` i GitHub secrets, hvis DeepSeek skal overtage teksterne
- Send besked til community@version2.dk om brug af deres RSS-feed
- Opret Bluesky-konto og læg `BLUESKY_BRUGER` + `BLUESKY_KODE` ind
- Opret Facebook-side og LinkedIn-virksomhedsside, hvis de skal bruges
- Sæt `OPSLAG_LIVE = ja`, når tørkørslerne ser rigtige ud
- Sæt budgetalarm på Google Cloud
- Indsæt de 14 kursusmails i Buttondown
