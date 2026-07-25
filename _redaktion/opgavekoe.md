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

### Rækkevidde — punkt 10

*Baggrunden står i `retning.md`. De her punkter handler ikke om, at noget er i
stykker, men om at godt arbejde ligger skjult.*

- [ ] **Ingen ved, om Google har set de 83 artikelsider.** De blev synlige for
      første gang i aften; indtil da blev de bygget og smidt væk ved hver kørsel.
      Tjek om `sitemap-artikler.xml` og `sitemap-videoer.xml` svarer korrekt live,
      og om artikelsiderne kan hentes. Skriv i loggen, hvad Torben skal gøre i
      Google Search Console — det kan kun han.
      *Punkt 10. Uden det er hele SEO-arbejdet spildt.*

- [ ] **Kørekortet er gemt bag nyhederne.** Nyheder kan alle levere; et gratis
      dansk AI-kørekort med et bevis, der kan efterprøves, kan ingen andre. En
      førstegangsbesøgende skal kunne se inden for tre sekunder, at man kan
      *lære* noget her. Foreslå én konkret indgang på forsiden — ikke et banner.
      *Punkt 10 og 7.*

- [ ] **Dagens overblik skrives hver dag og bruges ét sted.** Fem færdige punkter
      ligger i `data/brief.json` hver morgen og står kun på forsiden. Nyhedsbrevet
      udkommer kun fredag. Undersøg, hvad der skal til for at sende det som en
      daglig mail — og om Buttondowns gratis plan kan.
      *Punkt 10. En daglig vane slår en ugentlig påmindelse.*

- [ ] **Der findes ingen side, der taler til undervisere.** Et jobcenter, en
      aftenskole eller en fagforening, der tager kørekortet i brug, er 200
      læsere ad gangen — og de kommer igen hvert hold. Skriv et udkast til en
      side: hvad forløbet er, hvor lang tid det tager, og hvad beviset kan bruges
      til. Torben tager selv kontakten.
      *Punkt 10. Det tætteste siden kommer på et forspring.*

### Kendte fejl — målt, ikke gættet

- [ ] **Sammenlagte historier efterlader en forældreløs artikelside.** Når to
      medier dækker samme nyhed, bliver den ene hovedhistorie og får sin egen
      permanente side — men den andens side står stadig i `artikel/` og i
      sitemappet med næsten samme indhold. Mål hvor mange sider det drejer sig
      om, og find ud af, om hovedhistorien i stedet kan arve den ældste URL.
      *Punkt 4 og 10 — Google kan se det som dobbelt indhold.*

- [ ] **35 af 96 artikler mangler det fulde brief.** Mål årsagen først: rammer
      vi et loft pr. kørsel, fejler `hent_artikeltekst` på bestemte kilder, eller
      afviser redaktør-agenten dem? Ret så dét, der viser sig at være årsagen.
      *Punkt 4 — en læser der klikker, møder en pladsholder.*

- [ ] **Viser videosiderne faktisk tidsstempler?** De 18 låste videoer har nu
      dansk resumé. Får højdepunkterne plads på deres statiske sider, eller
      falder de stadig for tidstjekket i `_yt_anvend`? *Punkt 7.*

- [ ] **20 af 96 artikler står uden billede.** Er det de rigtige 20 (dem der kun
      vises som tekstlinjer), eller mangler nogle af dagens topkort deres
      illustration? *Punkt 4.*

- [ ] **4 overskrifter mangler stadig navn.** Er de opgivet af reparationsrunden
      (flaget `navngivet`), og er det rimeligt i netop de fire tilfælde?
      *Punkt 1.*

- [ ] **Virker det strammede Hacker News-feed?** Point-grænsen er hævet fra 50
      til 150. Kom der stadig artikler igennem i de seneste kørsler, eller er
      feedet gået i nul? *Punkt 6.*

### Kvalitet i teksterne

- [ ] **Læs 20 tilfældige "Hvad betyder det for dig" igennem.** Rammer de én
      konkret konsekvens for læseren, eller er de blevet generiske? Skriv de
      dårligste eksempler i loggen. *Punkt 2.*

- [ ] **Læs 20 tilfældige rubrikker som en nabo uden teknisk baggrund.** Er der
      ord, der kræver forklaring? *Punkt 1 og prøven i målestokken.*

- [ ] **Tjek dubletfangeren.** Find historier i arkivet, der reelt dækker samme
      begivenhed, men står som to. Er `saml_dublet_historier` for forsigtig?
      *Punkt 3.*

- [ ] **Er dagens overblik virkelig dagens vigtigste fem?** Sammenlign
      `data/brief.json` med de højest prioriterede artikler samme døgn.
      *Punkt 6.*

- [ ] **Gennemgå kategoriseringen.** Ligger artiklerne i de rigtige kategorier,
      eller ender for meget i "Lanceringer"? *Punkt 6.*

### Sider gennemgået med redaktionens øjne

- [ ] **Forsiden på en telefon.** Hierarkiet er bygget og testet på bred skærm.
      Hvordan holder hero + fire kort + kompakt liste på 390 px? *Punkt 4.*

- [ ] **AI-kørekortet, modul for modul.** Er sproget stadig til en nabo uden
      teknisk baggrund, eller har der sneget sig jargon ind? *Punkt 7.*

- [ ] **Erhvervsoverbygningens fire moduler.** Samme gennemgang. Rammer de folk,
      der møder AI på jobbet — uden at blive konsulentsprog? *Punkt 7.*

- [ ] **prompts.html og prompt-arkivet.** Er de 17 prompts stadig de bedste, vi
      kan lave? Er der gengangere mellem biblioteket og kartoteket? *Punkt 3.*

- [ ] **ordbog.html.** Mangler der ord, folk møder i nyhederne i dag? Er
      forklaringerne stadig i øjenhøjde? *Punkt 7.*

- [ ] **laer.html.** Er den stadig inspirerende, eller er den blevet en
      linksamling? *Punkt 7.*

- [ ] **faq.html.** Svarer den på det, en ny besøgende faktisk undrer sig over?
      *Punkt 7.*

- [ ] **vaerktoejer.html.** Er de 13 værktøjer og noterne stadig rigtige? Priser
      og funktioner skifter hurtigt — flag det, der ser forældet ud, i loggen
      i stedet for at gætte. *Punkt 5.*

- [ ] **En tilfældig artikelside.** Ser den professionel ud alene, uden forsiden
      omkring sig? Det er den, folk lander på fra Google. *Punkt 4.*

- [ ] **En tilfældig videoside.** Samme prøve. *Punkt 4.*

- [ ] **uge.html — ugens overblik.** Holder den stadig, eller er den blevet en
      opremsning? *Punkt 2.*

- [ ] **om.html.** Stemmer beskrivelsen med, hvad siden faktisk gør i dag?
      Kildelisten er ændret, og DeepSeek er på vej ind. *Punkt 5.*

### Det tekniske, en læser kan mærke

- [ ] **Hvor hurtigt loader forsiden?** Mål størrelsen på `data/articles.json`
      og billederne. Er der noget, der er vokset sig for stort? *Punkt 4.*

- [ ] **Virker siden uden JavaScript?** Artikelsiderne gør. Forsiden gør ikke.
      Er det et problem for Google og for folk med langsomme forbindelser?
      *Punkt 9.*

- [ ] **Tilgængelighed.** Kan man bruge forsiden med tastatur alene? Har
      billederne alt-tekst? Er kontrasten god nok til svagtseende? *Punkt 9.*

- [ ] **Tjek at alle interne links virker.** Gennemgå alle HTML-sider for links
      til sider, der ikke findes. *Punkt 4.*

- [ ] **Er `sitemap.xml` opdateret?** Den er skrevet i hånden og nævner ikke
      alle sider. Sammenlign med de faktiske filer. *Punkt 4.*

- [ ] **Tjek at PWA'en stadig virker.** Service worker, manifest, ikoner —
      efter alle dagens ændringer. *Punkt 4.*

- [ ] **Læs `data/opslag.json` igennem, når der er udkast i den.** Er tonen i
      de automatiske opslag noget, Torben ville skrive selv? *Punkt 5 og 8.*

- [ ] **Gennemgå crawlerens fejlbeskeder.** Er der steder, hvor noget fejler
      stille uden at sige hvorfor? Det var netop dét, der skjulte tre fejl.
      *Punkt 6.*

- [ ] **Ryd op i `_to_delete/`.** Mappen ligger stadig i repoet med gamle
      workflow-filer. Er der noget, der skal gemmes, før den ryger?

---

## Klaret

*(Natsessionen flytter afkrydsede punkter herned med dato.)*

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
