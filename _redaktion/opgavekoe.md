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

*Ingen kendte. Alt, der var målt i stykker, er klaret. Står der intet her
næste nat heller, er det et godt tegn — ikke et tomt afsnit, der skal fyldes.*

### 2 — Bryder målestokken synligt

- [ ] **Kørekortet kan ikke nulstilles, og det spærrer for hold.** Al fremdrift
      ligger i `localStorage` (`aikort`, `aikort_praktik`, `aikort_e` m.fl.), og
      der findes **ingen** måde at rydde den på — jeg søgte efter en. På en delt
      computer på et bibliotek eller et jobcenter ser deltager nummer to
      modulerne som allerede gennemført, og næste hold arver forrige holds
      afkrydsninger. Mindste rettelse: én knap nederst på `koerekort.html`, der
      rydder `aikort*`-nøglerne efter en bekræftelse. *Punkt 7 — og det er den
      konkrete forhindring for vej 3 i `retning.md`.*

- [ ] **`koerekort-tjek.html` lover mere, end tjekket kan holde.** Siden skriver
      "et opdigtet nummer vil ikke stemme". Men bevis-nummeret er
      `SHA-256(navn|dato|salt)`, og **begge salte står i klartekst i
      kildekoden** (`ainyheder-koerekort-v1` og `ainyheder-koerekort-e-v1`).
      Enhver, der åbner "vis kilde", kan lave et gyldigt nummer til et hvilket
      som helst navn. Det kan ikke laves om uden en server — men sætningen kan.
      Mindste rettelse: skriv "nummeret kan ikke gættes" i stedet for "kan ikke
      opdigtes". Resten af varedeklarationen på siden er god. *Punkt 5.*

- [ ] **4 overskrifter mangler stadig navn.** Er de opgivet af reparationsrunden
      (flaget `navngivet`), og er det rimeligt i netop de fire tilfælde?
      *Punkt 1 — den vigtigste regel i målestokken.*

- [ ] **20 af 96 artikler står uden billede.** Er det de rigtige 20 (dem der kun
      vises som tekstlinjer), eller mangler nogle af dagens topkort deres
      illustration? *Punkt 4.*

- [ ] **Læs 20 tilfældige "Hvad betyder det for dig" igennem.** Rammer de én
      konkret konsekvens for læseren, eller er de blevet generiske? Skriv de
      dårligste eksempler i loggen. *Punkt 2.*

- [ ] **Læs 20 tilfældige rubrikker som en nabo uden teknisk baggrund.** Er der
      ord, der kræver forklaring? *Punkt 1 og prøven i målestokken.*

### 3 — Gør siden mærkbart bedre

- [ ] **Ingen af de 31 statiske sider har en canonical.** Alle 102 artikelsider
      og alle 40 videosider har én — crawleren sætter den, fordi den er
      nødvendig. Men forsiden, `koerekort.html`, alle syv kørekortmoduler, alle
      fire erhvervsmoduler, `laer.html`, `ordbog.html`, `faq.html` og resten har
      ingen. Målt: 1 af 32 sider i roden har canonical, og det er
      `undervisning.html`, som blev skrevet i nat. Det er præcis de sider,
      Google *har* indekseret. Uden canonical kan samme side indekseres under
      flere adresser (med og uden `www`, med `?utm_source=…` fra et delt link),
      og signalerne splittes mellem dem. Mindste rettelse: én linje pr. side.
      *Punkt 10 — en åbenlys vej til flere læsere, der står ubrugt hen.*

- [ ] **Artikelsider fryses, når de falder ud af 30-dages-vinduet.** Målt i nat:
      **15 af de 16 sider under 900 tegn** er sider, crawleren ikke længere kan
      røre, fordi artiklen er ude af `articles.json`. De står på en ældre
      skabelon med 375–462 tegn hver. Tallet vokser hver måned, og enhver
      fremtidig forbedring vil kun ramme den nyeste måned. Første kørsel måtte
      skrive et engangsscript af samme grund. Mindste rettelse: crawleren kan
      genskrive en side ud fra sidens eget indhold, sådan som
      `opsaetning/opgrader-gamle-artikelsider.py` allerede gør — den skal bare
      kaldes fast i stedet for i hånden. *Punkt 4 og 10.*

- [ ] **Forsiden på en telefon.** Hierarkiet er bygget og testet på bred skærm.
      Hvordan holder hero + fire kort + kompakt liste på 390 px? *Punkt 4.*

- [ ] **Hvor hurtigt loader forsiden?** Mål størrelsen på `data/articles.json`
      og billederne. Er der noget, der er vokset sig for stort? *Punkt 4.*

- [ ] **Tilgængelighed.** Kan man bruge forsiden med tastatur alene? Er
      kontrasten god nok til svagtseende? (Alt-tekst er klaret 25.07.)
      *Punkt 9.*

- [ ] **Er `sitemap.xml` opdateret?** Den er skrevet i hånden og nævner ikke
      alle sider — bl.a. hverken `velkommen.html`, `tak.html` eller den nye
      `undervisning.html`. Sammenlign med de faktiske filer. *Punkt 4.*

- [ ] **Tjek at alle interne links virker.** Gennemgå alle HTML-sider for links
      til sider, der ikke findes. *Punkt 4.*

- [ ] **Tjek at PWA'en stadig virker.** Service worker, manifest, ikoner —
      efter alle dagens ændringer. *Punkt 4.*

- [ ] **Gennemgå crawlerens fejlbeskeder.** Er der steder, hvor noget fejler
      stille uden at sige hvorfor? Det var netop dét, der skjulte tre fejl.
      *Punkt 6.*

- [ ] **Ryd op i `_to_delete/`.** Mappen ligger stadig i repoet med gamle
      workflow-filer. Er der noget, der skal gemmes, før den ryger?

### 4 — Undersøgelser: vi ved ikke, om der er et problem

- [ ] **Virker det strammede Hacker News-feed?** Point-grænsen er hævet fra 50
      til 150. Kom der stadig artikler igennem i de seneste kørsler, eller er
      feedet gået i nul? *Punkt 6.*

- [ ] **Viser videosiderne faktisk tidsstempler?** De 18 låste videoer har nu
      dansk resumé. Får højdepunkterne plads på deres statiske sider, eller
      falder de stadig for tidstjekket i `_yt_anvend`? *Punkt 7.*

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

*(Natsessionen flytter afkrydsede punkter herned med dato.)*

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
