# Arbejdssessionens instruks

Det her er den instruks, arbejdssessionen følger — uanset hvornår på døgnet den
kører. Ret den frit; den læses forfra hver gang, så ændringer virker med det samme.

---

## Allerførst: sidder nogen og arbejder lige nu?

Du deler mappe med redaktionen. Redigerer I den samme fil samtidig, vinder den, der
skriver sidst — der er ingen fletning, og den anden mister sit arbejde uden at
opdage det. Derfor: kig efter, om nogen har rørt projektet for nylig.

```
find . -newermt '-30 minutes' \( -name '*.py' -o -name '*.html' -o -name '*.md' \
  -o -name '*.json' -o -name '*.yml' \) -not -path './data/*' -not -path './.git/*' \
  -not -path './artikel/*' -not -path './video/*' -not -path './_to_delete/*'
```

`data/`, `artikel/` og `video/` er undtaget, fordi crawleren selv skriver dem
nitten gange i døgnet — de siger intet om, hvorvidt et menneske er i gang.

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
   linje i `_redaktion/arbejdslog.md` om, at du sprang over. Er den ældre, er den
   efterladt af en afbrudt session — overskriv den og fortsæt.
2. Ellers: skriv nuværende tidspunkt (ISO 8601) i `_redaktion/.koerer`.
3. **Slet altid `_redaktion/.koerer`, før du slutter** — også hvis du stopper undervejs.

## Hvilken slags kørsel er du?

Du kan blive startet af en tidsplan eller af, at nogen trykker **Kør nu**.
**Kig ikke på klokken — kig på, hvad der allerede er sket.** Så virker det samme
regelsæt, uanset hvornår på døgnet du kører.

Åbn `arbejdslog.md` og se efter en overskrift `### Sessionens regnskab · <dagens dato>`.

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

**Bliver du startet manuelt, er redaktionen sandsynligvis til stede.** Det ændrer ikke,
hvad du laver — men skriv loggen, som om den bliver læst om fem minutter, ikke i
morgen.

## Læs derefter, i denne rækkefølge

1. `_redaktion/oensker.md` — **Redaktionens egne ønsker. De kommer altid først.**
   Her står i almindeligt dansk, hvad der ønskes. Hvert ønske skal du
   oversætte til et rigtigt køpunkt (hvad ser en læser, hvilket punkt i
   målestokken, mindste rettelse) og flytte ned under "Behandlet" med en note om,
   hvor det endte. Står der **HASTER** foran, ryger det øverst i køen, før alt
   andet — også før noget, du selv har målt som værre.
   Er et ønske en dårlig idé, så lav det ikke: skriv i loggen hvorfor, og lad
   ønsket blive stående, så der kan svares igen.
2. `_redaktion/redaktionens-oejne.md` — målestokken. Ti punkter, og et afsnit om
   hvad der IKKE er et problem. Den afgør alt andet.
3. `_redaktion/opgavekoe.md` — køen.
4. `_redaktion/arbejdslog.md` — hvad tidligere kørsler fandt og besluttede.
5. `_redaktion/analyse-seneste.md` — din egen analyse fra sidst, hvis den findes.

Crawleren laver **ingen** gennemgang længere. Den måler kun rå tal
(`data/laesertal.json` fra Cloudflare). Vurderingen er din alene.

**Tjek også, om der ligger uafhentet arbejde.** Kør `git status --short`. Er der
ændrede filer fra tidligere nætter, er der ikke pushet endnu. Skriv det
ØVERST i arbejdsloggen med det samme — der bygges videre på noget, verden ikke har
set, og de filer, crawleren selv skriver, vil begynde at give merge-konflikter.

---

## Fase 0 — Din egen analyse, FØR du rører noget

**Gør det her hver gang, også som ekstra kørsel.** Køen er et forslag fra i går.
Siden har ændret sig siden — crawleren har kørt, artikler er kommet til og faldet
ud, og forrige session har ændret kode. At gå direkte i gang med øverste punkt er
at arbejde efter et kort, ingen har tjekket.

Sæt cirka en tiendedel af din tid af til det her. Ikke mere.

**1. Mål tilstanden selv.** Skriv et lille engangsscript og kør det. Tæl i
`data/articles.json`, `data/youtube.json`, `artikel/`, `video/`, `data/laesertal.json`
og filerne i roden. Ikke ét fast sæt tal — se på dét, der er relevant i aften,
og på dét, du ændrede sidste gang. Tallene i køen er fra i går; dine er fra nu.

**2. Se på siden som en læser.** Hent forsiden og en tilfældig artikelside ind, og
læs dem. Tal fortæller, om noget mangler — ikke om det er godt. Hold det op mod
de ti punkter i målestokken.

**3. Tjek dit eget arbejde fra sidst.** Læs den øverste post i `arbejdslog.md` og
verificér, at rettelsen holder. Vi har set flere gange, at en rettelse løste
symptomet og efterlod årsagen — eller flyttede fejlen et andet sted hen.

**4. Afgør, hvad køen skal.** Nu — og først nu — læser du `oensker.md` og køen
med dine egne tal i hånden. **Ønskelisten vejer tungere end dine egne fund**;
de ser noget, ingen måling fanger. Derefter:

- Er øverste punkts påstand stadig sand? Er den ikke, så luk punktet med din
  måling som dokumentation, eller skriv den om, så den passer.
- Fandt du noget, der er værre end øverste punkt? Så skriv det ind og tag det.
- Fandt du intet nyt, og passer køen? Så tag øverste punkt. Det er et fint svar.

**5. Skriv analysen ned** i `_redaktion/analyse-seneste.md` (overskriv den
forrige). Kort — det er et arbejdspapir, ikke en rapport:

```
# Analyse · <dato og klokkeslæt>
**Målt:** <de tal, du faktisk kiggede på>
**Set som læser:** <hvad du lagde mærke til på forsiden og artikelsiden>
**Sidste nats arbejde:** <holder det, eller er der noget efterladt?>
**Køen:** <hvad du ændrede i den, og hvorfor>
**Jeg går i gang med:** <punktet> — <én sætning om hvorfor netop det>
```

Er det søndag, stiller du desuden ét ekstra spørgsmål: **hvad ville få flere
danskere til at bruge siden?** Læs punkt 10 i målestokken. En fejlfri side, ingen
læser, opfylder ikke sit formål. Forslag herfra må gerne være ting, siden ikke
har i dag — men de skal bygge på noget, der allerede findes, og aldrig kræve
betaling, login eller persondata. Skriv dem i køen.

## Fase 1 — Arbejd (hovedparten af tiden)

**Tag ét punkt ad gangen — men bliv ved.** Et punkt kan tage tyve minutter eller
flere timer. Når ét er færdigt, testet og logget, tager du det næste.

**Den hårde regel: aldrig to opgaver i luften på én gang.** Punkt to røres først,
når punkt et er færdigt. Fem halvfærdige ting, der hver især ser ud til at virke,
er værre end ingenting.

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

**Rør ikke andet end nødvendigt.** Ingen omskrivning af ting, der virker.

**Kan et punkt ikke lade sig gøre** — manglende adgang, forkert antagelse — så
skriv hvorfor, flyt det ned med en note, og tag det næste. Gå ikke i stå.

**Log efter hvert punkt, ikke til sidst.**

**Stop i tide.** Er du dagens hovedkørsel, så sørg for at have plads tilbage til fase
2 og 3. De er vigtigere end ét punkt mere.

### Til allersidst i fase 1: virker det hele stadig sammen?

Hvert punkt er testet for sig. Det siger intet om, hvad tre ændringer gør ved
hinanden. Har du rørt noget som helst, så kør en samlet prøve, FØR du går
videre:

- `python3 -c "import ast;ast.parse(open('crawler.py',encoding='utf-8').read())"`
- Indlæs `crawler.py` som modul, og tjek at der ikke er dobbeltdefinerede
  konstanter på modulniveau. Præcis dén fejl gjorde, at hver eneste artikel-brief
  blev skrevet med den forkerte instruks i ugevis, uden at nogen opdagede det.
- Forsiden i jsdom mod de rigtige datafiler: ingen JS-fejl, kortene tegnes,
  dagens overblik vises, og et klik åbner en artikel.
- Er der rørt ved kontrolpanelet: samme prøve på `_redaktion/kontrolpanel.html`.

Fejler noget, så ret det, før du logger. En session, der efterlader siden i
stykker, er værre end en session uden arbejde — der pushes uden at koden bliver læst igennem.
Skriv resultatet af den samlede prøve i loggen, også når alt er grønt.

## Fase 2 — Evaluér siden med friske øjne

**Kun sidste kørsel.** Er du første kørsel, springer du fase 2 og 3 over (men ALDRIG fase 0), skriver
loggen for det, du nåede, sletter låsefilen og stopper.

Tæl, hvor mange punkter der er klaret i dag i alt — også dem, tidligere kørsler tog.
Kald tallet N.

Gå på jagt efter nye. Vælg et sted, der ikke har været gennemgået de seneste
kørsler — en side, en del af crawleren, en måling. Se på det som en læser.

**Du må skrive op til N nye punkter i køen. Du SKAL ikke skrive N.**

Et punkt kommer kun i køen, hvis det kan svare på alle tre:

1. Hvad ser eller mister **en læser**? Konkret, med et eksempel fra siden.
2. Hvilket af de ni punkter i målestokken brydes?
3. Hvad er den mindste rettelse? Noget, der kan laves på én nat.

Fandt du ingen, skriver du nul og noterer: *"Gennemgik X — fandt intet, der
bryder målestokken."* Det er et fuldgyldigt resultat. Opfundet arbejde koster
redaktionen tid og gør siden dårligere.

Genåbn ikke noget fra "Klaret", medmindre du kan måle, at det er gået i stykker igen.

## Fase 3 — Prioritér hele køen til næste kørsel

Sortér **hele** køen om efter denne rækkefølge:

1. **Noget er i stykker for læseren lige nu** — tomme sider, døde links, forkerte tal.
2. **Noget bryder målestokken synligt** — jargon, gentagelser, uprofessionelt udseende.
3. **Noget gør siden mærkbart bedre** — nyt indhold, bedre struktur, hurtigere.
4. **Undersøgelser** — hvor vi ikke ved, om der er et problem.

Inden for samme trin: det, der rammer flest læsere, kommer først. Ved uafgjort:
det billigste at rette.

Bliver køen længere end 40 punkter, flyttes de svageste ned under `## Parkeret`.

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
### Sessionens regnskab · <dato>
Klaret: <N> punkter. Nye i køen: <M> (<hvorfor færre end N, hvis M < N>).
Gennemgik: <hvad du så på i fase 2>
Øverst i køen nu: <punktet> — <én sætning om hvorfor>
```
