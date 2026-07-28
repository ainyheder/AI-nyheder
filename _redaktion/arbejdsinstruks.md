# Arbejdssessionens instruks

Det her er den instruks, arbejdssessionen følger — uanset hvornår på døgnet den
kører. Ret den frit; den læses forfra hver gang, så ændringer virker med det samme.

---

## Allerførst: sidder nogen og arbejder lige nu?

Du deler mappe med redaktionen. Redigerer I den samme fil samtidig, vinder den, der
skriver sidst — der er ingen fletning, og den anden mister sit arbejde uden at
opdage det. Derfor: kig efter, om nogen har rørt projektet for nylig.

Stå i repoets rod, når du kører den her — den bruger relative stier.

```
find . -newermt '-30 minutes' \( -name '*.py' -o -name '*.html' -o -name '*.md' \
  -o -name '*.json' -o -name '*.yml' \) -not -path './data/*' -not -path './.git/*' \
  -not -path './artikel/*' -not -path './video/*' -not -path './_to_delete/*' \
  -not -name 'arbejdslog.md' -not -name 'opgavekoe.md' -not -name 'analyse-seneste.md' \
  -not -name 'oensker.md'
```

`data/`, `artikel/` og `video/` er undtaget, fordi crawleren selv skriver dem
nitten gange i døgnet. `arbejdslog.md`, `opgavekoe.md`, `analyse-seneste.md` og `oensker.md` er
undtaget, fordi **du selv** skriver i dem — uden den undtagelse ser enhver kørsel,
der starter mindre end en halv time efter den forrige, sit eget arbejde og
konkluderer, at et menneske er i gang. Ingen af dem siger noget om, hvorvidt
nogen sidder ved tastaturet.

`redaktionens-oejne.md` og `retning.md` er **med** i tjekket med vilje: dem
redigerer kun redaktionen. `kontrolpanel.html` er også med — rører du selv den,
så regn med, at næste kørsel stopper, og skriv det i loggen.

**Kommer der filer ud af den kommando, arbejder et menneske sandsynligvis lige nu.**
Så stopper du: skriv én linje i `arbejdslog.md` om, at du sprang over, hvilke filer
der var rørt, og hvornår — og slut. Prøv ikke at arbejde udenom. Den næste
kørsel samler op, og køen løber ingen steder.

Kører du, fordi nogen lige har trykket **Kør nu**, vil de ændringer ofte
udløse den her. Er de eneste rørte filer dem, opgaven i køen handler om, må du
gerne fortsætte — men skriv i loggen, at du gjorde det, og hvorfor.

## Dernæst: er en anden session i gang?

Der kan køre flere sessioner i døgnet, og de må aldrig arbejde samtidig i de samme filer.

1. Findes `_redaktion/.koerer`, så læs tidsstemplet. Er det mindre end 3 timer
   gammelt, arbejder en anden session lige nu: **stop med det samme** og skriv én
   linje i `_redaktion/arbejdslog.md` om, at du sprang over. **Rør ikke låsefilen
   — den er ikke din.** Er den ældre, er den efterladt af en afbrudt session:
   overskriv den og fortsæt.
2. Ellers: skriv nuværende tidspunkt (ISO 8601) i `_redaktion/.koerer`.
3. **Slet `_redaktion/.koerer`, før du slutter — men kun hvis den er din**, altså
   hvis du selv skrev den, uanset om det var som ny lås eller som overtagelse af
   en efterladt. Også hvis du stopper undervejs. Sletter du en
   fremmed lås, går den næste kørsel lige ind oven i den, der arbejder.

## Hvilken slags kørsel er du?

Du kan blive startet af en tidsplan eller af, at nogen trykker **Kør nu**.
**Kig ikke på klokken — kig på, hvad der allerede er sket.** Så virker det samme
regelsæt, uanset hvornår på døgnet du kører.

Åbn `arbejdslog.md` og søg efter en overskrift, der indeholder **`regnskab · <dagens dato i ÅÅÅÅ-MM-DD>`**. Match på ordet *regnskab* og datoen, ikke på hele
overskriften: de ældre poster hedder `### Nattens regnskab · …`, de nye
`### Sessionens regnskab · …`, og en session, der kun leder efter den ene, finder
aldrig noget og udnævner sig selv til hovedkørsel hver eneste gang.

- **Findes der INTET regnskab for i dag:** du er dagens hovedkørsel. Du tager
  hele turen — fase 0, 1, 2 og 3 — og skriver regnskabet til sidst.
- **Findes der ALLEREDE et regnskab for i dag:** du er en ekstra kørsel. Du laver
  **fase 0 og fase 1**: analysér, arbejd køen, og skriv en log-post pr. færdigt punkt. Rør ikke
  prioriteringen, og skriv ikke et regnskab til. Tilføj i stedet én linje under
  dagens regnskab: `**Ekstra kørsel <klokkeslæt>:** klarede <N> punkter mere.`

Grunden: evaluering og omprioritering skal ske ÉN gang i døgnet. Sker det oftere,
omgør hver kørsel den forriges rækkefølge, og køen skifter udseende, uden at
nogen har lært noget nyt. At arbejde køen kan derimod ske så mange gange, det skal
være.

## Læs derefter, i denne rækkefølge

1. `_redaktion/redaktionens-oejne.md` — målestokken. Ti punkter, og et afsnit om
   hvad der IKKE er et problem. Den afgør alt andet.
1b. `_redaktion/retning.md` — hvor siden skal hen. **Den stod ikke på den her
   liste før 28.07, og det betød, at ingen kørsel nogensinde åbnede den.** Filen
   beskriver, hvad der er værd at bruge tid på — og den regner selv med en
   søndagsregel, loopet aldrig har haft. Læs den som en kilde til arbejde, ikke
   som baggrund: står der noget, siden burde kunne, hører det i `## Nyt`.
2. `_redaktion/oensker.md` — **redaktionens egne ønsker. De kommer altid først.**
   Her står i almindeligt dansk, hvad der ønskes. Hvert ønske oversætter du til
   et rigtigt køpunkt og flytter ned under "Behandlet" med en note om, hvor det
   endte. Er et ønske mærket `#haster`, ryger det øverst i køen før alt andet —
   også før noget, du selv har målt som værre.
   Er et ønske en dårlig idé, så lav det ikke: skriv i loggen hvorfor, læg det i
   `## Fravalgt`, og lad ønsket blive stående, så der kan svares igen.
   Du **læser** den her og **oversætter** den i fase 0, punkt 5 — når du har dine
egne tal og kan se, hvad ønsket vejer op imod.
3. `_redaktion/opgavekoe.md` — syv lister, som ikke må blandes sammen:
   `## Kø` er **målte** problemer og det eneste, der prioriteres.
   `## Nyt` er ting, siden **bør kunne** og ikke kan — mangler, ikke fejl.
   Den har sine egne regler; de står i filen. Der kræves intet rammer-tal,
   men der kræves et svar på, hvad det mindste er, der kan bygges og ses virke.
   `## Mistanker` er set, men ikke målt — måles først, laves derefter.
   `## Fast gennemgang` er den rotation, du tager af, når køen er tom.
   `## Venter på redaktionen` rører du ikke; der er stillet et spørgsmål,
   og du skal ikke gætte svaret.
   `## Fravalgt` er sagt nej til — læs den, før du skriver nye punkter.
   `## Klaret` er historik. Genåbn ikke noget derfra uden en måling.
   Nederst står `## Ting kun et menneske kan gøre` — konti, nøgler, mails.
   Den er redaktionens huskeliste; du hverken sorterer eller udfører den, men
   opdager du, at noget på den er gjort, må du gerne krydse det af.
4. `_redaktion/arbejdslog.md` — hvad tidligere kørsler fandt og besluttede.
5. `_redaktion/analyse-seneste.md` — din egen analyse fra sidst. Findes den ikke,
   er det ikke en fejl; så er du den første, der skriver den.

Crawleren laver **ingen** gennemgang længere. Den måler kun rå tal
(`data/laesertal.json` fra Cloudflare). Vurderingen er din alene.

**Du må hverken committe eller pushe.** Redaktionen gør begge dele selv i GitHub
Desktop, og det er med vilje: intet går live, uden at et menneske har set det.
Du efterlader altså dit arbejde ucommittet, og det er det rigtige.

**Tjek til gengæld, om der ligger uafhentet arbejde.** Kør
`git --no-optional-locks status --short`. Er der ændrede filer fra tidligere
kørsler, er de ikke hentet endnu. Skriv det ØVERST i arbejdsloggen med det samme
— der bygges videre på noget, verden ikke har set, og de filer, crawleren selv
skriver, vil begynde at give merge-konflikter.

`--no-optional-locks` er ikke pynt. Et almindeligt `git status` skriver
`.git/index.lock`, og efterlades den, kan redaktionen ikke committe i GitHub
Desktop — *"Unable to create index.lock"*. Det har generet fire gange, og en
tidligere kørsel valgte derfor at droppe tjekket helt. Det er den forkerte
løsning: flaget fjerner grunden i stedet for tjekket. Ligger der alligevel en
`.git/index.lock`, og er den over fem minutter gammel, må du slette den — det er
en efterladt låsefil, ikke data.

---

## Fase 0 — Din egen analyse, FØR du rører noget

**Gør det her hver gang, også som ekstra kørsel.** Køen er et forslag fra i går.
Siden har ændret sig siden — crawleren har kørt, artikler er kommet til og faldet
ud, og forrige session har ændret kode. At gå direkte i gang med øverste punkt er
at arbejde efter et kort, ingen har tjekket.

Sæt cirka en tiendedel af din tid af til det her. Ikke mere.

**Kører du kort efter en anden session, så lav kun forskellen.** Åbn
`analyse-seneste.md`. Er den øverste analyse under tre timer gammel, er dens tal
om **disken** stadig gyldige, og så springer du punkt 2 over og måler kun det,
der kan have flyttet sig: hvad crawleren har lavet i mellemtiden, og hvad forrige
session rørte. Skriv det som `**Siden <klokkeslæt>:** <hvad der har ændret sig>`.

**Punkt 1 og 3 skal du altid igennem, også på den korte tur.** Live-tjekket er
hele grunden til, at nogen opdager en død side — det er to opslag og tager under
et minut.

**1. Tjek FØRST, at siden overhovedet svarer.** Hent **`https://ainyheder.com/`
over nettet**, før du rører noget andet. Repoet er ikke siden: der ligger et push
og en GitHub Action imellem, og siden har været nede i timevis uden at nogen
opdagede det, fordi en flettekonflikt kom med i `data/articles.json`. Tjek som
minimum, at forsiden svarer, at `data/articles.json` på nettet er gyldig JSON, og
at antallet af artikler ligner det, du tæller på disken i punkt 2. Er der
forskel, er dét dagens første opgave — alt andet er ligegyldigt, mens siden er i
stykker.

Kig samtidig i `data/laesertal.json` og skriv **én linje** i analysen: besøg,
hvorfra, og hvad der blev åbnet. **Ikke mere end én linje, og brug ikke tid på
at lede efter mønstre i tallene.** Siden er under opbygning, og trafikken er
redaktionen selv. Tallene er baggrund, ikke et fund — se reglen øverst i
`## Fravalgt` i opgavekøen, før du skriver et punkt, der hviler på dem.

Det stod anderledes før 28.07: læsertallene var punkt 1 og blev kaldt "den eneste
måling, der siger noget om, hvorvidt arbejdet rammer nogen". Det holder ikke, når
der ikke er noget publikum endnu. Målingen kan ikke skelne mellem *en side, ingen
gider* og *en side på et website, ingen kender* — og hver kørsel brugte tid på at
læse det samme tal og drage den samme konklusion.

**2. Mål tilstanden selv.** Skriv et lille engangsscript og kør det. Tæl i
`data/articles.json`, `data/youtube.json`, `artikel/`, `video/` og filerne i
roden. Ikke ét fast sæt tal — se på dét, der er relevant lige nu, og på dét, du
ændrede sidste gang. Tallene i køen er fra i går; dine er fra nu.

**3. Se på siden som en læser — og tjek at det, du ser, er det, verden ser.**
Hent forsiden og en tilfældig artikelside ind fra **disken** og læs dem. Tal
fortæller, om noget mangler — ikke om det er godt. Hold det op mod de ti punkter
i målestokken.

Sammenlign med det, du hentede over nettet i punkt 1. Ser forsiden på disken
anderledes ud end den, verden får, er dét dagens første opgave.

**4. Tjek sidste kørsels arbejde.** Læs den øverste post i `arbejdslog.md` og
verificér, at rettelsen holder. Vi har set flere gange, at en rettelse løste
symptomet og efterlod årsagen — eller flyttede fejlen et andet sted hen.

**4b. Efterprøv ét ældre punkt.** Sidste kørsels arbejde er stadig varmt —
det er de gamle rettelser, ingen kigger på igen. Kør:

```
python3 _redaktion/efterproev.py
```

Den vælger selv ét punkt fra `## Klaret` i køen: det ældste, der er mindst to
døgn gammelt og ikke er i karens efter en tidligere efterprøvning. Vælger den
intet, siger den det, og så springer du punktet over. Du vælger ikke selv — så
kan du ikke komme til at vælge det, der er nemmest at give ret.

Så gør du dette, og kun dette:

**a. Find punktets hovedpåstand og citér den ordret.** Det er den påstand,
titlen handler om — ikke det tal, der er nemmest at måle igen. Står der flere
tal, er hovedpåstanden den, der ville gøre punktet forkert, hvis den var
usand. Skriv den ordret i mærket, i anførselstegn. Kan du ikke citere den, har
du ikke fundet den.

**b. Mål den samme påstand igen i dag.** Ikke læse koden og skønne — måle.

**c. Skriv ét af disse tre udfald** som en linje for sig til sidst i punktet.
De udelukker hinanden. Vælg det, der passer på **hovedpåstanden** — ikke det,
der passer på den del, du tilfældigvis kunne måle:

- `**Efterprøvet DD.MM.ÅÅÅÅ: holder.** <tallet, du målte i dag>`
- `**Efterprøvet DD.MM.ÅÅÅÅ: gik i stykker igen.** <hvad du målte, og hvad der
  er anderledes>`
- `**Efterprøvet DD.MM.ÅÅÅÅ: kan ikke måles herfra.** <hvorfor>`

**Kan hovedpåstanden ikke måles, er svaret det tredje — også selvom alt det
andet i punktet holdt.** Skriv gerne bagefter, hvad der så kunne måles, men
etiketten skal passe på det, punktet lovede. Ellers er efterprøvningen
markedsføring, og så bryder den punkt 5 i målestokken.

Gik det i stykker, skriver du punktet ind i `## Kø` igen med dagens måling som
grundlag — ikke den gamle tekst. En rettelse, der ikke holdt, er et nyt problem,
ikke en gentagelse af det gamle.

**Tidsloftet er 15 minutter.** Kan påstanden ikke måles på et kvarter — fordi
den kræver tal fra Google, fra en læser eller fra noget, kun Torben kan se — så
skriv det tredje udfald og gå videre. Et ærligt "ved det ikke" er bedre end en
efterprøvning, der bare gentager, hvad der stod i forvejen.

**Et mærke er ikke en fritagelse på livstid.** Punktet er kandidat igen efter
karensen: 21 døgn for "holder", 7 for de to andre. Et punkt, der ikke kunne
måles i dag, skal prøves igen — ellers ville den billigste udvej også være den
endelige.

**Råber scriptet op om efterslæb**, så skriv tallet i loggen. Det betyder, at
klarede punkter hober sig op hurtigere, end én efterprøvning pr. kørsel kan
indhente — det kan du ikke rette i dag, men det skal stå et sted, hvor det kan
ses vokse.

Rører du selv `efterproev.py`, så kør `python3 _redaktion/efterproev-proeve.py`
bagefter. Den prøver valget, karensen, datoerne og de skæve køer mod opdigtede
data — 45 prøver, og den rigtige kø bliver ikke rørt.

Hvorfor det her overhovedet står her: loggen og køen har hele tiden kunnet
fortælle, hvad der blev *gjort*. Det her er det eneste sted, systemet får at
vide, om det havde **ret**.

**5. Afgør, hvad køen skal.** Nu — og først nu — holder du `oensker.md` og køen
op mod dine egne tal. **Ønskelisten vejer tungere end dine egne fund**;
de ser noget, ingen måling fanger. Derefter:

- Er øverste punkts påstand stadig sand? Er den ikke, så luk punktet med din
  måling som dokumentation, eller skriv den om, så den passer.
- Fandt du noget, der er værre end øverste punkt? Så skriv det ind og tag det.
- Fandt du intet nyt, og passer køen? Så tag øverste punkt. Det er et fint svar.

**6. Skriv analysen ned** øverst i `_redaktion/analyse-seneste.md`. Behold de to
forrige nedenunder og slet resten — så kan næste session se, hvad der har
flyttet sig, i stedet for kun hvor tingene står. Kort; det er et arbejdspapir,
ikke en rapport:

```
# Analyse · <dato og klokkeslæt>
**Live:** <svarer ainyheder.com det samme som repoet?>
**Læsere:** <én linje: besøg, hvorfra. Ikke en analyse — se punkt 1>
**Målt:** <de tal, du faktisk kiggede på>
**Set som læser:** <hvad du lagde mærke til på forsiden og artikelsiden>
**Sidste kørsels arbejde:** <holder det, eller er der noget efterladt?>
**Køen:** <hvad du ændrede i den, og hvorfor>
**Jeg går i gang med:** <punktet> — <én sætning om hvorfor netop det>
```

## Fase 1 — Arbejd (hovedparten af tiden)

**Tag ét punkt ad gangen — men bliv ved.** Et punkt kan tage tyve minutter eller
flere timer. Når ét er færdigt, testet og logget, tager du det næste.

**Den hårde regel: aldrig to opgaver i luften på én gang.** Punkt to røres først,
når punkt et er færdigt. Fem halvfærdige ting, der hver især ser ud til at virke,
er værre end ingenting.

**Én undtagelse — samme årsag, samme måling.** Graver du i et punkt og finder
noget mere, der har **samme rod**, ligger i **filer du allerede har målt**, og kan
dækkes af **den prøve, du alligevel skal køre** — så retter du det nu og skriver
det ind under samme log-post. Fandt du 11 sider med et brudt billede, og der er 25,
retter du alle 25.

Det er ikke en åbning for at samle op undervejs. Er der bare én af de tre ting,
der ikke passer — anden rod, andre filer, egen prøve — så skriver du fundet i køen
med din måling og lader det ligge. Reglen findes, fordi målingen er det dyre.
Har du først betalt for at forstå et hjørne af koden, er det spild at lade et
andet punkt betale for det igen i morgen. Loggen viser seks gange, hvor et fund
ved siden af opgaven var mere værd end selve opgaven.

**Er noget i stykker for læseren lige nu, må du tage det først** — også selvom det
ikke står øverst. Kravet er, at du kan **måle** det, og at det hører til trin 1 i
prioriteringen nedenfor. Skriv i loggen, at du sprang køen over, og hvad målingen
viste. En kø fra i går må ikke holde en tom forside i live til i morgen.

**Mål, før du bygger.** Antag aldrig at problembeskrivelsen er rigtig. Tæl i
`data/articles.json`, læs koden, kør funktionen. Tre alvorlige fejl blev fundet
præcis sådan: en `AttributeError` der tømte alle briefs, 83 artikelsider der blev
bygget og smidt væk hver kørsel, og 18 videoer der var låst fast for evigt. Ingen
af dem stod i nogen fejlrapport. Viser målingen, at problemet ikke findes, så
skriv dét — det er også et resultat, og punktet er klaret.

**Test alt, du rører.** Python: `ast.parse` plus kør funktionen med `kald_ai`
erstattet af en falsk funktion — test et gyldigt svar, et svar pakket i et array,
og noget vrøvl. Frontend: jsdom + node med `fetch` mod de rigtige datafiler,
`timeout 30 node` og `process.exit(0)`. Test både at det virker, og at det fejler pænt.

**Og prøv så prøven. Slet din egen rettelse på skift og se, at den går rød.**
Tag hver enkelt ting, du har ændret — hver ny linje, hver vagt, hvert felt du
lagde i en hvidliste — fjern den eller vend den om i en KOPI af filen, kør
prøven, og skriv ned, hvor mange påstande der blev røde. Bliver ingen røde,
prøver din prøve ikke den ting. Så er den ikke en prøve, den er en dekoration.

Det er ikke en teoretisk risiko. 28.07 stod prøven på **59 grønne, 0 røde** — og
man kunne slette selve rettelsen, tømme cache-hvidlisten eller vende en vagt om,
uden at én eneste påstand rørte sig. **Fire huller**, alle i en prøve, jeg selv
mente var grundig. Efter mutationsprøven: 15 ændringer prøvet på skift, hver
eneste fanget af netop de rigtige påstande.

Skriv resultatet i loggen som et tal: *"15 mutationer, alle fanget."* Er der
mutationer, du bevidst ikke dækker, så skriv hvilke og hvorfor.

Kør også prøven mod `git show HEAD:<fil>` — den skal være **rød før og grøn
efter**. En prøve, der er grøn mod den gamle kode, prøver ikke rettelsen.

**Rør ikke andet end nødvendigt.** Ingen omskrivning af ting, der virker.

**Kan et punkt ikke lade sig gøre** — manglende adgang, forkert antagelse — så
skriv hvorfor, flyt det ned med en note, og tag det næste. Gå ikke i stå.

**Er `## Kø` tom, er du ikke færdig.** Så tager du enten en `## Mistanker` og
måler den efter, eller den ældste i `## Fast gennemgang` — det er de spørgsmål
uden ende, hver med en dato for, hvornår de sidst blev set på. Har de samme
dato, eller står der "aldrig" ud for flere, tager du den øverste. Sæt en time af,
ikke mere, og skriv dagens dato på bagefter, uanset om du fandt noget.

En tom kø er et godt tegn, ikke en fejl — find ikke på arbejde for at fylde den.

**Men en tom `## Nyt` er IKKE et godt tegn.** Skrevet ind 28.07, fordi
redaktionen sagde det rent ud: loopet bidrog ikke nok, det kørte i ring om det,
der allerede fandtes. Årsagen var strukturel — `## Kø` er defineret som *målte
problemer*, og fase 2 leder efter fejl, så der var ingen lovlig plads til
sætningen *"siden bør kunne X"*. En fejlfindingsmaskine finder fejl, også når
det, der mangler, ikke er en fejl.

**To krav, der gælder fra nu:**

- **Efter hver hovedkørsel skal der stå mindst ét punkt i `## Nyt`.** Findes der
  intet, har ingen spurgt, hvad siden mangler — så gør det, før du logger.
- **Der skal bygges mindst én ny ting om ugen.** Kig i loggen: er der gået syv
  døgn, uden at noget nyt er kommet til, går det forud for køens øverste punkt,
  medmindre noget er i stykker for læseren lige nu.

**Spørg først, hvis** det koster penge, sender noget ud til nogen, opretter en
side, der skal linkes fra forsiden, eller ændrer et dataformat. Alt andet bygger
du og viser bagefter. Reglen er ikke en opfordring til at bygge stort: den
mindste ting, der kan ses virke, slår stadig planen om det store.

**Log efter hvert punkt, ikke til sidst.**

**Stop i tide.** Er du dagens hovedkørsel, så hold plads tilbage til fase 2 og 3.
De er vigtigere end ét punkt mere.

### Til allersidst i fase 1: virker det hele stadig sammen?

Hvert punkt er testet for sig. Det siger intet om, hvad tre ændringer gør ved
hinanden. Har du rørt noget som helst, så kør en samlet prøve, FØR du går
videre:

- `python3 -c "import ast;ast.parse(open('crawler.py',encoding='utf-8').read())"`
- Find dobbeltdefinerede konstanter på modulniveau med `ast` — **ikke** ved at
  importere modulet, for et import beholder kun den sidste værdi, og så er
  dubletten netop usynlig:
  `python3 -c "import ast,collections;n=[t.id for x in ast.parse(open('crawler.py',encoding='utf-8').read()).body if isinstance(x,ast.Assign) for t in x.targets if isinstance(t,ast.Name) and t.id.isupper()];print([k for k,v in collections.Counter(n).items() if v>1] or 'ingen')"` Præcis dén fejl gjorde, at hver eneste artikel-brief
  blev skrevet med den forkerte instruks i ugevis, uden at nogen opdagede det.
- Forsiden i jsdom mod de rigtige datafiler: ingen JS-fejl, kortene tegnes,
  dagens overblik vises, og et klik åbner en artikel. **jsdom ligger ikke i
  repoet** — installér det i din arbejdsmappe med `npm install jsdom` først, og
  installér det uden for repoet, så `node_modules` ikke havner i git.
- Er der rørt ved kontrolpanelet: samme prøve på `_redaktion/kontrolpanel.html`.

Fejler noget, så ret det, før du logger. En session, der efterlader siden i stykker, er værre end en session uden
arbejde: redaktionen pusher uden at læse koden igennem.
Skriv resultatet af den samlede prøve i loggen, også når alt er grønt.

### Og lad en anden læse det

**Har du rørt kode overhovedet, skal en uafhængig gennemgang læse dit arbejde,
før du logger.** Én fil er nok. Én linje er nok. Ikke en ekstra runde af dig selv
— en, der ikke har set, hvad du tænkte undervejs, og som får ændringerne og
målestokken og intet andet.

Det her er ikke en formalitet, og grænsen stod før ved "mere end én fil". Den
blev flyttet 28.07 af en grund: den dags ændring lå i **én fil**, den var testet
med 59 grønne påstande, og efter den gamle regel behøvede den slet ingen
gennemgang. Gennemgangen fandt **19 ting fordelt på tre runder** — heriblandt at
selve rettelsen kunne slettes, uden at én eneste påstand blev rød. Tidligere er
den brugt to gange frivilligt og fandt **fem ting hver gang**: første gang fem
fejl i koden, anden gang fem fejl i selve loggen, altså i beskrivelsen af
arbejde, der ellers var korrekt. Ingen anden enkeltting i loopet har den
træfsikkerhed, og antallet af filer siger intet om, hvor galt det står til.

**Bliv ved, indtil en runde ikke finder noget.** De tre runder 28.07 fandt 7, 6
og 6 ting. Var jeg stoppet efter den første — som var den, reglen lagde op til —
var elleve fejl gået med i køleskabet, heriblandt to, der ville have revet
vinderens egen alt-tekst af og gemt et lånt tidsstempel som en permanent
sandhed.

Giv den ændringerne (`git diff`), `redaktionens-oejne.md`, og ét spørgsmål:
*hvad er der galt med det her, som den, der skrev det, ikke kan se?* Ret det,
den finder, før du logger, og skriv i log-posten hvad den fandt — også hvis det
var ingenting.

## Fase 2 — Evaluér siden med friske øjne

**Kun dagens hovedkørsel** — den, der ikke fandt et regnskab for i dag. Er du en
ekstra kørsel, springer du fase 2 og 3 over (men ALDRIG fase 0), skriver loggen
for det, du nåede, sletter din låsefil og stopper.

Tæl, hvor mange punkter der er klaret i dag i alt — dine egne og dem, tidligere
kørsler tog. Kald tallet **L** (for loft).

**Du må skrive op til L nye punkter — og altid mindst ét, hvis du fandt noget.**
Loftet findes for at holde køen kortere end arbejdslysten, ikke for at forbyde
dig at skrive ned, at noget er i stykker: er L nul, og fandt du en tom side,
skriver du den alligevel. Fandt du intet, skriver du nul, og det kræver ingen
forklaring.

### Hvad du leder efter — det skifter hver gang

Kig i `arbejdslog.md`, hvad forrige regnskab skrev under `Gennemgik:`. Der er
tre slags, og de går på skift: **kvalitet → rækkevidde → udvikling → kvalitet**.
Skriv selv, hvilken slags du kørte, så den næste kan se det.

**Kvalitetsrunde.** Vælg et sted, der ikke har været gennemgået de seneste
kørsler — en side, en del af crawleren, en måling. Se på det som en læser, og
hold det op mod målestokkens ni første punkter.

**Rækkevidderunde.** Ét spørgsmål: **hvorfor når det her ikke nogen?** Punkt 10
i målestokken, og det eneste punkt der ikke kan besvares ved at læse kode. Start
i `data/laesertal.json` og se på, hvad tallene faktisk siger — hvor kommer
besøgene fra, hvilke sider bliver aldrig åbnet, hvad blev delt og af hvem.
Målt 27.07 som udgangspunkt: **4 besøg fra Google på en uge, 19 fra Facebook,
og 141 artikelsider med 2 sidevisninger tilsammen.**

Regler for runden: forslag må gerne være ting, siden ikke har i dag, men de skal
bygge på noget, der allerede findes, og de må **aldrig** kræve betaling, login
eller persondata. Foreslå ikke noget, der kun kan udføres af et menneske, uden at
skrive det under `## Venter på redaktionen` — sessionen kan ikke oprette konti
eller sende mails.

**Udviklingsrunde.** Ét spørgsmål: **hvad skal siden kunne, som den ikke kan
i dag?** Læs `retning.md` og de sider, der findes, og spørg hvad en læser ikke
kan gøre her. Fundene går i `## Nyt`, ikke i `## Kø` — de er mangler, ikke fejl,
og de skal ikke have et rammer-tal. Det er den eneste af de tre runder, der kan
gøre siden større; de to andre kan kun gøre den bedre.

Alle tre slags runder afleverer efter reglerne nedenfor — kvalitet og rækkevidde
i `## Kø` eller `## Mistanker`, udvikling i `## Nyt`.

### Hvor et fund skal hen — og hvorfor det er to steder

Halvdelen af alle punkter, der er blevet lavet, viste sig at være beskrevet
forkert. Det står sort på hvidt i loggen: 14 ud af 28 poster begynder med, at
målingen sagde noget andet end køen. *"Fristen er dage og ikke 30." "De 15 sider
blev bygget tynde, ikke frosset tynde." "Det foreslåede script kan ikke skrive
tekst."* Hver af dem kostede en session tid på at rette et kort, ingen havde
tjekket — og prioriteringen i fase 3 var lavet oven på den forkerte beskrivelse.

Årsagen er ikke sjusk. Det er, at fase 2 skriver punkter ud fra at *kigge*, og at
punktet så bliver læst som noget, nogen har *målt*. De to ting skal skilles ad:

**Har du et tal, går fundet i `## Kø`.** Punktet skal indeholde:

1. **Symptomet:** hvad ser eller mister en læser? Konkret, med et eksempel.
2. **Målingen der beviser det:** tallet, datoen, og kommandoen eller filen, der
   gav tallet. `Målt 27.07: 39 af 112 sider …`
3. **Rammer-tallet.** Slå den berørte side op i `data/laesertal.json` og skriv
   sidevisningerne de sidste syv dage: `Rammer: 88 visninger/7 dage (laer.html)`.
   Er problemet i crawleren og ikke på en enkelt side, så skriv tallet for **den
   side, læseren mærker det på** — dubletfangeren rammer forsiden, altså
   `Rammer: 440 visninger/7 dage (forsiden)`. Der skal stå et tal; "hele siden"
   er ikke et tal.
4. **Hvilket punkt i målestokken** der brydes.

Et lavt tal er ikke i sig selv en grund til at lade noget ligge. En nybygget side
har nul, fordi den er ny; en artikelside kan have nul, *fordi* den er i stykker.
**Er tallet nul, skal punktet forklare vejen derfra til en læser** — hvem skulle
finde siden, og hvordan? Kan du ikke svare, hører punktet til i trin 3, uanset
hvor galt det ser ud i koden.

**Skriv ikke, hvad rettelsen er.** Du har ikke målt nok til at vide det, og et
forkert forslag er værre end ingen: den næste session bruger tid på at afvise det.
Har du en formodning, så skriv den som netop dét — *"formentlig i
`saml_dublet_historier`"* — på en linje for sig.

**Har du ikke et tal, går fundet i `## Mistanker`.** En mistanke er en helt
ordentlig ting at aflevere: *"Forsiden føles lang på en telefon — ikke målt."*
Den bliver ikke prioriteret og bliver ikke lavet, før nogen har målt den. Det er
hele pointen. En mistanke, der får lov at ligge i køen som et punkt, bliver til
et arbejdskort, ingen har dækning for.

Fandt du ingen af delene, skriver du nul: *"Gennemgik X — fandt intet, der
bryder målestokken."* Det er et fuldgyldigt resultat. Opfundet arbejde koster
redaktionen tid og gør siden dårligere.

Genåbn ikke noget fra "Klaret", medmindre du kan måle, at det er gået i stykker igen.

### Skriv ned, hvad I sagde nej til

**Læs `## Fravalgt` i `opgavekoe.md`, før du skriver nye punkter.** Står
dit fund der allerede, skriver du det ikke ind igen — medmindre du kan måle, at
grundlaget har ændret sig, og så skriver du dét som en del af punktet.

Og omvendt: forkaster du selv en idé — din egen, en mistanke eller noget fra
`## Kø`, der viste sig ikke at holde — så flyt den til `## Fravalgt` med **datoen
og hvorfor**. Loggen fortæller i dag kun, hvad der blev lavet. En idé, ingen
skrev ned som afvist, kommer igen om en måned og koster den samme udredning
forfra.

## Fase 3 — Prioritér køen til næste kørsel

Sortér `## Kø` om efter denne rækkefølge. **Kun `## Kø`** — `## Mistanker`,
`## Fast gennemgang`, `## Venter på redaktionen` og `## Fravalgt` sorteres ikke.
De er ikke arbejde endnu.

1. **Noget er i stykker for læseren lige nu** — tomme sider, døde links, forkerte
   tal, eller **ingen vej ind til siden overhovedet**. Det sidste hører med her:
   en læser, der søger og ikke finder os, oplever nøjagtig det samme som en
   læser, der finder en tom side.
2. **Noget bryder målestokken synligt** — jargon, gentagelser, uprofessionelt udseende.
3. **Noget gør siden mærkbart bedre** — nyt indhold, bedre struktur, hurtigere.

**Inden for samme trin sorteres efter rammer-tallet, ikke efter fornemmelse.**
88 visninger slår 2. Har et punkt intet rammer-tal, så slå det op nu — det tager
et minut, og uden det er rækkefølgen et gæt. Ved uafgjort: det billigste at rette.

**Rør ikke et punkt, redaktionen selv har flyttet.** Står der `#fastholdt` i
punktet, bliver det, hvor det er. Panelets pile skriver mærket på, når nogen
flytter en linje, og uden den regel ville din sortering slette et menneskes
beslutning uden at nogen opdagede det.

**Tag stilling til aldrende punkter.** Er et punkt over en uge gammelt og aldrig
blevet målt siden, så mål det om eller flyt det til `## Mistanker`. Tal fra i
sidste uge er ikke tal.

Bliver `## Kø` længere end 25 punkter, flyttes de svageste ned under
`## Fravalgt` med `fravalgt <dato>: for svagt til at fylde i køen` og deres
måling i behold. **Ikke til `## Mistanker`** — den liste betyder "ikke målt", og
næste session ville måle punktet efter og hente det op igen i en ring.

Skriv til sidst, hvad der nu står øverst — og én sætning om hvorfor rækkefølgen
ændrede sig. Redaktionen skal kunne være uenig.

---

## Loggen

Efter hvert færdigt punkt: flyt det i `opgavekoe.md` ned under "Klaret" med dato,
og skriv øverst i `arbejdslog.md`:

```
## <dato> · <opgavens navn>
**Fandt:** <hvad målingerne viste — også hvis problemet ikke var som beskrevet>
**Gjorde:** <hvad du ændrede, i hvilke filer>
**Testede:** <hvad du kørte, og hvad der kom ud>
**Til redaktionen:** <hvad han skal vide, beslutte eller gøre>
```

**Opdatér kontrolpanelet, før du slutter.** Panelet læser et øjebliksbillede i
`data/hjerne-data.js`, ikke filerne direkte — så uden det her viser det din log
og din kø, som de så ud sidst, nogen huskede at genskabe dem. Kør:

```
python3 -c "import importlib.util,os;os.chdir('.');\
s=importlib.util.spec_from_file_location('c','crawler.py');\
m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.skriv_hjerne_status()"
```

Den kræver ingen API-nøgle og rører kun de to panelfiler.

Afslut med:

```
### Sessionens regnskab · <ÅÅÅÅ-MM-DD>
Klaret: <N> punkter. Nye i køen: <M>.
Gennemgik: <kvalitet|rækkevidde> — <hvad du så på i fase 2>
Læsere i dag: <besøg, og hvorfra de kom>
Øverst i køen nu: <punktet> — <rammer-tal> — <én sætning om hvorfor>
```

`Gennemgik:` skal begynde med **kvalitet**, **rækkevidde** eller **udvikling**.
Det er sådan, den næste kørsel ved, hvilken slags runde den selv skal tage.
Rækkefølgen er kvalitet → rækkevidde → udvikling → kvalitet.
