# Nat-log

Nyeste øverst. Skrevet af natsessionen efter hvert færdigt punkt.

---

> **⚠️ `.git/index.lock` lå der igen — og det var `git status`, der lagde den.**
> Samme fil, der spærrede dit commit i morges. Den blev skabt kl. 12:24:10,
> nøjagtigt da jeg kørte `git status --short`, som instruksen beder mig om.
> **Jeg har ryddet den, og der ligger ingen låse nu** — jeg har tjekket hele
> `.git` for `*.lock`.
>
> Årsagen: git vil opdatere sin cache, når filer har ændret sig, og det kræver
> låsen. Første `git status` kl. 12:03 efterlod ingen — den kl. 12:24 gjorde,
> fordi jeg imens havde ændret tre filer. Så det sker ikke hver gang, men det
> sker netop, når natsessionen har lavet noget. Sandkassen må normalt ikke
> slette i `.git/`, så jeg måtte bede om lov undervejs.
>
> **Rettelsen er ét flag:** `git --no-optional-locks status --short`. Jeg har
> prøvet begge dele i aften — den efterlader ingen lås. Vil du undgå det her
> tredje gang, så ret linjen i `natsession.md` under "Tjek også, om der ligger
> uafhentet arbejde". **Jeg har ikke rettet den selv** — det er din fil, og du
> redigerer den gennem panelet.
>
> Der lå intet uafhentet arbejde, da jeg startede: `git status` var tom, så de
> 8 filer fra i formiddags er pushet.

---

## 2026-07-26 (ekstra kørsel kl. 14) · Ingen af de statiske sider har en canonical

**Fandt:** Tallet holdt — **2 af 33** HTML-filer i roden havde en canonical
(`cookies.html` og `undervisning.html`). Men da jeg skulle rette dem, viste
målingen noget, punktet ikke nævnte: **`uge.html` er ikke en statisk fil.**
Crawleren genskriver den fra bunden i `_uge_side_html()` hver gang ugens
overblik opdateres (`UGE_HTML.write_text(...)`, to steder). En canonical skrevet
i hånden dér ville være forsvundet ved næste kørsel — præcis den fælde, noten om
stavefejlen advarede imod i går. Jeg gennemgik alle 22 `write_text` i crawleren
og hele `crawl.yml`: `uge.html` er **den eneste** rod-HTML, der genereres, så de
27 andre er trygge at rette i hånden.

**Gjorde:** Sat canonical på **28 sider** — 27 i hånden plus skabelonen bag
`uge.html`, så den overlever en kørsel. Format og placering er crawlerens eget:
`<link rel="canonical" href="https://ainyheder.com/<fil>">`, lige efter
`<meta name="description">`.

`index.html` peger på `https://ainyheder.com/` **uden** `index.html` — samme
form som `<loc>` i sitemappet. Det er hele pointen med at gøre det: at `/` og
`/index.html` ikke længere kan indekseres som to sider.

**Tre sider fik den med vilje ikke:**

- `404.html` — en fejlside. En canonical dér er en invitation til at indeksere den.
- `tak.html` og `velkommen.html` — de har allerede `<meta name="robots"
  content="noindex">`. En canonical ville sende et modsatrettet signal om noget,
  vi udtrykkeligt ikke vil have indekseret.

**Testede:** 203 assertions, alle grønne.

- 98 statiske: hver af de 33 filer har præcis én canonical (nul for de tre
  undtagne), den ligger inde i `<head>`, URL'en peger på sig selv, og hver fil
  har stadig ét `<head>`/`</head>` og `<!DOCTYPE>` først. Diffen er **28 linjer
  tilføjet, 0 slettet, 0 ændret** — hver enkelt en canonical og intet andet.
- Krydstjek mod `sitemap.xml`: alle 29 sitemap-URL'er har nu en side, der
  peger på præcis den adresse. Ingen uenighed mellem de to.
- `_uge_side_html()` genskabt fra `data/uge.json` og sammenlignet med filen på
  disken: **byte for byte identisk**. Skabelonen og filen er altså enige, og
  næste kørsel hverken fjerner eller dublerer linjen.
- 105 i jsdom på 21 af siderne (forsiden, ugesiden, alle slags kørekort- og
  erhvervsmoduler, guider, quiz, ordbog, værktøjer, tjek-siden): ingen JS-fejl,
  browseren parser præcis én `link[rel=canonical]` med den rigtige `href`,
  `<title>` intakt, body har indhold.
- `ast.parse` grøn, modulet indlæses, ingen dobbeltdefinerede konstanter.

**Til Torben:**

- **Det virker først, når Google henter siderne igen.** Canonical er et signal,
  ikke en omdirigering. Og det hjælper kun på det, der allerede er indekseret —
  sitemappene er stadig ikke indsendt, og det kan kun du gøre (instruksen står
  længere ned i loggen). Uden det er dette en ryddet vej, ingen kører på.
- **`undervisning.html` har en canonical, men står ikke i sitemappet.** Den er
  stadig ikke linket fra nogen side. Det punkt ligger i køen.
- **Overvej `noindex` på `koerekort-tjek.html`** hvis den ikke skal findes i
  Google. Jeg har givet den en canonical, fordi den er en rigtig side, men det
  er dit valg, om en bevis-tjekker skal kunne søges frem.

---

## 2026-07-26 (ekstra kørsel kl. 14) · 12 rubrikker mangler stadig et navn

**Kørte selvom du var i gang.** Køen var rørt fire minutter før jeg startede
(`opgavekoe.md`, 14:08), og du committede den 14:10 — så du har trykket **Kør
nu** oven på din egen redigering. Den ene rørte fil er netop det punkt, jeg
skulle arbejde på, så jeg fortsatte, som instruksen tillader. Intet uafhentet
arbejde: `git status` var tom. Ingen `.git/*.lock` hverken før eller efter — jeg
brugte `git --no-optional-locks status` fra starten. **Linjen i `natsession.md`
er stadig uden flaget**, så den næste kørsel rammer det igen; rettelsen står i
noten øverst.

**Fandt:** Tallet holder — **12 af 96**, og alle 12 er låst af `navngivet`.
Der er ingen uprøvede tilbage. Men de er ikke låst, fordi AI'en "gav op": de er
låst, fordi **den blev bedt om at finde navne i materiale, navnene var pillet ud
af.**

`navngiv_rubrikker` viste modellen fire ting: den engelske titel (160 tegn),
det engelske RSS-resumé (250 tegn) og vores egen navnløse rubrik og resumé.
Den viste den **aldrig** `sektioner` og `detaljer` — den danske genfortælling,
crawleren selv skriver ét kald tidligere i `main()`. Og det er lige præcis dér,
navnene står:

| rubrik | navn i det, modellen fik | navn i det, vi allerede havde |
|---|---|---|
| Nye materialer skal redde fremtidens AI-kraft | — | **Microsoft**, Syensqo |
| Computere opfinder helt nye fordomme ved ansættelser | — | **ChatGPT, Claude, Gemini**, OpenAI, Princeton |
| Sådan bruger medierne verden over AI | OpenAI | OpenAI |

**Og der er et bevis for, at det gik galt.** Git-historikken over
`articles.json` (40 revisioner) viser præcis én af de 12 rubrikker ændre sig:

> 24.07: *"Nye materialer skal redde fremtidens **computerkraft**"*
> 25.07: *"Nye materialer skal redde fremtidens **AI-kraft**"* — `navngivet: true`

Det er hele omskrivningen. Modellen havde intet navn at arbejde med, satte
ordet **AI** ind, og den dengang utætte `_har_navn` godtog "AI" som et navn —
så svaret blev accepteret, skrevet ind i arkivet og **låst for evigt**.
Artiklen handler om Microsoft. Reparationsrunden gjorde altså rubrikken en
smule ringere og lukkede derefter døren. De øvrige 11 svar blev afvist, og
flaget blev sat alligevel.

**For de øvrige 9 er låsen rigtig.** Jeg gennemsøgte hele posten — sektioner,
detaljer, pointer, nøgletal, figurer, betydning — og der er intet navn nogen
steder. Fem af dem (`Christians AI-værktøj`, `Specialist: Skærp kravene`,
`Kommune brugte AI`, `Vibrationer i dit kranie`, `Sundhedsdata`) er
`kun_aktuel`, altså arkivforbud: vi gemmer med vilje ikke udgiverens tekst, så
vi får **aldrig** mere materiale om dem. At nulstille deres flag ville være at
betale for at få samme svar igen. Ingeniøren og Version2 valgte selv at holde
kommunen og rådgivningsfirmaet ude af overskriften.

**Gjorde:** Tre ting i `crawler.py` og én i `data/articles.json`.

1. **Ny `_dansk_uddrag()`** samler genfortællingen (sektioner + detaljer +
   pointer) og lægger den i payloaden som `dansk_uddrag`, max 700 tegn.
   Artikler uden genfortælling får feltet slet ikke — frem for en tom streng.
2. **Uddraget prioriterer de stumper, der bærer et navn** (`_uddrag_vaegt`).
   Det er ikke pynt: en simpel klipning ved 700 tegn nåede aldrig frem, fordi
   `sektioner` alene fylder ~1.100 tegn — Microsoft stod sent, og ChatGPT/
   Claude/Gemini stod i `detaljer`, som slet ikke kom med. Nu kommer sikre
   navne først, korteste stump først, fordi `detaljer` har den højeste
   navnetæthed (én linje på 60 tegn kan rumme tre navne).
3. **Prompten** siger nu, at feltet findes og at navnet ofte kun står dér — at
   ordet "AI" **ikke** er et navn og ikke tæller som en løsning — og at et tomt
   svar er et gyldigt "jeg fandt intet navn". Desuden: ét vrøvl-element i
   svaret tabte før hele klumpen (`p.get()` på en streng kaster
   `AttributeError`, som kun den ydre `except` fangede).
4. **Nulstillet `navngivet` for præcis de 3**, hvor uddraget nu leverer et
   sikkert navn. Ikke alle 12. Diffen er 3 linjer: `true` → `false`.

**Testede:** 58 assertions, alle grønne.

- 44 på `navngiv_rubrikker` med `hjerne_kald` erstattet af en falsk funktion:
  gyldigt svar (Microsoft og ChatGPT skrives ind, `resume_da` følger med),
  svar pakket i en dict, ren vrøvl, tom streng, `null`, `42`, array af strenge,
  array med `null` i (den gyldige post bruges alligevel), rubrik som liste,
  `nr` som tekst, `nr` uden for listen, tom rubrik. **Og det svar, der før slap
  igennem:** "…fremtidens AI-kraft" bliver nu afvist, rubrikken står uændret.
  Samme for "techgigant", "Gigantens", for lang, for kort, for mange ord.
  Uden API-nøgle røres intet.
- `ast.parse` grøn, modulet indlæses, **ingen dobbeltdefinerede konstanter** på
  modulniveau.
- `articles.json`: stadig gyldig, stadig 96 artikler, samme nøgler og
  rækkefølge, `opdateret` urørt, **kun** `navngivet` ændret på 3 poster, filen
  voksede 3 bytes. Sikkerhedskopi lå i `/tmp` undervejs.
- Forsiden i jsdom mod de rigtige datafiler: 14 assertions grønne, ingen
  JS-fejl, 97 kort tegnes, dagens overblik vises, 49 kort har `data-link`, og
  et klik åbner læsevisningen med indhold. De tre rubrikker står uændret på
  deres egne artikelsider.

**Til Torben:**

- **Næste crawler-kørsel prøver de 3 igen — det koster ét AI-kald.** Bliver
  svaret godt, hedder de to vigtigste noget i retning af *"Microsoft leder
  efter nye materialer til AI-servere"* og *"ChatGPT og Claude udvikler
  fordomme ved ansættelser"*. Den sidste er prio 8 og ligger højt på forsiden.
- **De 9 andre lader jeg blive låst med vilje.** Vil du have dem prøvet
  alligevel, er det én linje: sæt `navngivet` til `false` i `articles.json`.
  Men for de fem `kun_aktuel` er svaret det samme som sidst, og det koster.
- **Værd at bemærke:** to af de 12 er OpenAI's egen blog (*"Sådan bruger
  medierne verden over AI"*, *"Styr på udgifterne til AI i virksomhederne"*),
  og flere er MIT Tech Review-artikler af typen "sådan gør IT-chefer". De er
  navnløse, fordi de ikke handler om en begivenhed, men er rådgivning — og for
  OpenAI-posternes del er afsenderen selv sælgeren. Det er ikke punkt 1, det er
  punkt 5. Jeg har ikke skrevet et punkt om det i køen (det hører til
  hovedkørslens fase 2), men det er værd at tage stilling til, om den slags
  hører hjemme i nyhedsstrømmen.
- **Målt og lagt fra mig:** jeg tjekkede, om "IT" leaker gennem `_har_navn`
  ligesom "AI" gjorde. Det gør det ikke — af 96 rubrikker bæres kun tre af en
  forkortelse, og alle tre er "EU", som er en rigtig aktør. Ingen ændring.

---

## 2026-07-26 · Læs 20 rubrikker som en nabo uden teknisk baggrund

**Fandt:** Læste alle 107, ikke 20. Det, punktet spurgte om — jargon — er
**ikke det største problem.** Det, jeg fandt i stedet, var **en stavefejl på
forsiden**:

> *"OpenAI og Anthropics barrierer **spæner** ben for eksperter"*

Det hedder "spænder ben". "Spæne" betyder at løbe stærkt, så sætningen er
meningsløs. Og modellen brugte det forkerte ord **konsekvent gennem hele
artiklen** — 3 steder i `data/articles.json` (rubrik, en detalje og en pointe)
og 5 på artikelsiden, heriblandt `<title>`, `og:title` og
NewsArticle-schemaets `headline`. Altså også dét, Google og et delt link
viser. Det er målestokkens punkt 4: en stavefejl i en overskrift er præcis
det, der får en side til at ligne et hjemmeprojekt frem for en redaktion.

**Om jargonen — svaret er nej, med tre undtagelser.** Af 107 rubrikker er der
kun tre, en nabo ikke kan læse:

- *"Runway lancerer ny smart **model-router**"* — den værste. "Model-router"
  står ikke i ordbogen, og rubrikken siger intet andet; fjerner man ordet, er
  der ingen historie tilbage.
- *"Østrigs militær vælger **open source**"* — hele pointen er et begreb, der
  ikke forklares. (Ordbogen har "Open source-model", men en rubrik skal kunne
  læses uden opslag.)
- *"USA's hær opbruger alle sine **AI-tokens** på én måned"* — "token" er i
  ordbogen, men rubrikken kan ikke afkodes uden.

Resten er fine. Ord som "nudify", "metadata", "kill switch", "pyrolyse",
"hulkort", "transistorer" og "whistleblower" optræder én gang hver, og de står
alle i en sætning, der bærer meningen selv. **9 af 107 rubrikker er over
redaktørens grænse på 8 ord** (8 %) — ingen af dem er uforståelige.
"Kunstig intelligens", som prompten forbyder, står **0 steder**.

**Gjorde:** Rettede "spæner" → "spænder" i `data/articles.json` og
`artikel/f254e58029de8cb9.html`. JSON'en er ændret via `json.load`/`dump`, ikke
med søg-og-erstat i teksten, så strukturen ikke kunne brydes — og skrevet med
crawlerens eget format (`ensure_ascii=False, indent=2`), så diffen er ren.
Intet andet rørt; jeg har hverken slettet eller omskrevet noget.

**Testede:** Diffen er præcis 3 linjer i `articles.json` og 5 i artikelsiden —
kun det ene ord. Filen er stadig gyldig JSON med 107 artikler, uændrede nøgler
og **nøjagtig én** ændret artikel; den voksede 3 bytes. Artikelsidens
JSON-LD-blok parser stadig. Forsiden i jsdom mod den rettede fil: 9
assertions grønne, ingen JS-fejl. `crawler.py` uændret sund. Sikkerhedskopier
af begge filer lå i `/tmp` undervejs.

**Til Torben:**

- **De tre uforståelige rubrikker kan jeg ikke omskrive** — det kræver et
  AI-kald med din nøgle. "Model-router" er den, jeg ville tage først.
- **Værd at vide om stavefejlen:** den slap forbi både skribenten og
  redaktør-agenten, og den var gentaget 8 gange. Jeg har *ikke* bygget en
  stavekontrol — jeg har ét datapunkt, og en rettelsesliste med ét ord på er
  mere vedligeholdelse end værdi. Dukker der flere af den slags op, er det et
  mønster, der er værd at handle på.
- Rettelsen ligger i en genereret fil. Genskrives artiklen med
  `GENKOER_ALT`, kan fejlen komme igen — modellen skrev den jo selv.

---

## 2026-07-26 · Læs 20 "Hvad betyder det for dig" igennem

**Fandt:** Læste alle 79 i stedet for 20 tilfældige — det koster ikke mere at
måle dem alle. **De fleste er fine.** Median 21 ord, nul over to sætninger,
nul ordret identiske, nul der starter med den forbudte indledning "Det
betyder". Så nej, de er ikke generelt blevet generiske.

Men der er én gruppe, der skiller sig skarpt ud: **6 af 79 taler OM en tredje
part i stedet for TIL læseren** — *"For almindelige mennesker betyder det …"*,
*"For forbrugerne …"*, *"Historien viser …"*. De er ikke bare lidt svagere,
de er en anden slags tekst:

| | de 6 | de øvrige 73 |
|---|---|---|
| median ordlængde | **42 ord** | 20 ord |
| mangler "du" helt | **6 af 6** | 2 af 73 |
| over promptens grænse på 35 ord | **4 af 6** | 1 af 73 |

Boksen hedder **"Hvad betyder det for dig?"**. En tekst, der svarer *"For
almindelige mennesker betyder det …"*, svarer bogstaveligt på et andet
spørgsmål end det, der står over den. Det værste eksempel, 44 ord:

> *"Kampen mellem store hardware-producenter har direkte indflydelse på prisen
> og hastigheden for de digitale tjenester, vi bruger dagligt. Når virksomheder
> investerer astronomiske summer i nye systemer, skaber det grundlaget for
> hurtigere og klogere digitale assistenter, som på sigt vil præge både
> arbejdsliv og privatforbrug."* — *AMD udfordrer Nvidia med Helios AI-system*

**Årsagen var ikke skribenten — det var redaktøren.** Der findes allerede en
redaktør-agent, der læser hvert brief og kan bestille en omskrivning. Dens
regel 4 lød: *"BETYDNING: skal være konkret **for almindelige danskere**"*.
Instruksen var altså selv formuleret i den tredjeperson, den skulle fange, så
en betydning, der åbnede med "For almindelige mennesker …", lignede en
opfyldelse af reglen. Samtidig håndhævede redaktøren hverken de 35 ord eller
"du"-tiltalen, som skribentens egen prompt kræver. To prompter, der skulle
være enige, var det ikke — samme slags fejl som i billedpunktet ovenfor.

**Gjorde:** Tre ting i `crawler.py`, alle i samme spor:

1. **Rettede redaktørens regel 4**, så den håndhæver præcis det, skribenten
   bliver bedt om: tiltale i "du", højst 35 ord, ingen tredjepersons­omskrivning
   — med de faktiske vendinger som eksempler.
2. **Tilføjede `_betydning_problemer()`** — et deterministisk tjek af de krav,
   der kan måles med en lineal frem for et skøn. Noterne fodres ind i den
   omskrivning, redaktøren allerede kan bestille, så der kun bruges et ekstra
   AI-kald, når noget faktisk er galt (målt: 8 af 79, altså 10 %). Et AI-skøn
   alene er ikke pålideligt nok til et krav, der kan tælles.
3. **Et værn:** omskrivningen må ikke gøre betydningen dårligere end den, den
   erstattede. Uden det kunne det nye tjek forværre netop det felt, det skulle
   beskytte.

Og fordi de 8 eksisterende ellers ville stå for evigt: **`GENKOER_ALT=betydning`**
genskriver nu kun de artikler, hvis betydning fejler tjekket — 8 kald i stedet
for de 80, `GENKOER_ALT=ja` ville koste.

**Testede:** 45 nye assertions, alle grønne. `_betydning_problemer`: gode
tekster giver nul noter (også tom tekst, `None`, kun mellemrum og præcis 35
ord), dårlige giver de rigtige, og ordgrænserne holder — "dukke", "dublet",
"duel" og "dito" udløser ikke "du"-reglen. Hele `dybe_briefs` kørt med
`hjerne_kald` erstattet af en falsk funktion: god betydning giver **ét** kald
(ingen spildt omskrivning), dårlig giver to, en værre omskrivning rulles
tilbage, vrøvl og tomt svar kræsjer ikke, array-pakket svar håndteres, og
redaktørens egne noter kombineres med de deterministiske i ét retry.
Kandidatudvælgelsen — crawlerens mest kritiske sti — testet i alle fire
tilstande: normal drift vælger stadig kun ubehandlede, `ja` vælger alle,
søgeord virker som før, `betydning` vælger præcis de svage.

Samlet prøve efter begge nattens punkter: `ast.parse`, modulindlæsning og
ingen dobbeltdefinerede konstanter ✅, og forsiden i jsdom mod de rigtige
datafiler ✅ — **79 assertions i alt, ingen fejl.**

**Til Torben:**

- **De 8 gamle betydninger retter sig ikke selv.** Prompten og tjekket virker
  kun på nye briefs; de eksisterende ligger i cache. Vil du rette dem, så kør
  workflowet med **`GENKOER_ALT` = `betydning`**. Det rammer de 8 og koster
  8 brief-kald. Jeg har ikke gjort det — det kræver din API-nøgle.
- **Værd at bemærke:** 28 af 107 artikler har slet ingen "betydning". Jeg har
  ikke undersøgt hvorfor; 26-27 af dem er sandsynligvis `kun_aktuel`
  (arkivforbud, tilsigtet), men det har jeg ikke målt, og jeg vil ikke gætte.
  Det er en kandidat til køen, ikke et fund.
- Jeg har **ikke** rørt `index.html`, billedprompten eller noget i `data/`.

---

## 2026-07-26 · 32 af 110 artikler står uden billede

**Fandt:** Spørgsmålet i køen var, om de billedløse artikler var "de rigtige".
Målt mod crawlerens eget udvalg var svaret ja — **0 overlap**, alle 53
kort-kandidater havde billede. Men den måling er cirkulær: den spørger
crawleren, om crawleren er enig med sig selv. Den rigtige prøve er mod
**forsiden**, og dér holder det ikke. `_kort_artikler()` i `crawler.py`
bestemmer, hvem der får et billede; `index.html` bestemmer, hvem der får en
billedplads. De var uenige tre steder:

1. **`kun_aktuel` blev udeladt.** Arkivforbuddet gælder udgiverens tekst — vi
   gemmer ikke deres artikel og bygger ingen artikelside. Men crawleren
   nægtede dem også et *billede*, som er vores eget. Forsiden viser dem som
   helt almindelige kort. To af dem stod med **prio 7** på forsidens store
   kort med tomt billedfelt: *"Kommune brugte AI i borger-sag uden at sige
   det"* og *"Sundhedsdata skal testes i nye AI-projekter"*.
2. **Forskning spiste en billedplads.** Crawleren grupperede alle kategorier
   sammen, men forsiden har to faner, der ikke deler artikler: "Nyheder" viser
   alt undtagen Forskning, "Forskning" viser kun Forskning — og hver fane
   tegner sine egne fem kort. Den 26.07 lå *"AlphaFold AI gør genredigering
   mere sikker"* nr. 4 i udvalget og fik et billede, ingen ser på nyhedsfanen,
   mens kortet, der faktisk tog pladsen dér, stod uden.
3. **Vægten var ikke den samme.** Forsidens `prioAf()` lægger +1 til
   flerkilde-historier. Crawleren sorterede på rå `prio`. Alene den forskel
   flyttede 6 links.

Målt på fanerne: **Standard 2 af 9 pladser tomme, Forskning 5 af 6.**

**Gjorde:** Skrev `_kort_artikler()` om i `crawler.py` (ét sted, ~30 linjer
inkl. forklaring). Den grupperer nu pr. `(dag, fane)`, medtager `kun_aktuel`
og sorterer efter en ny `_kort_vaegt()`, der er en tro kopi af forsidens
`prioAf()`. Konstanten `KORT_PR_DAG = 5` erstatter det nøgne `[:5]`.
Docstringen forklarer koblingen til `index.html`, så næste ændring i den ene
fil ikke stille afkobler den anden. **Intet andet rørt** — ikke `index.html`,
ikke billedprompten, ikke loftet.

**Testede:** 25 assertions i Python, alle grønne: `ast.parse`, ingen
dobbeltdefinerede konstanter på modulniveau, `_kort_vaegt` mod forsidens
formel (inkl. `prio: 0` som ikke må blive til 5), loftet pr. dag pr. fane,
Forskning der ikke presser nyheder ud, dato-fallback og artikler helt uden
dato. `udfyld_billedmotiver` kørt med `hjerne_kald` erstattet af en falsk
funktion: gyldigt svar, svar pakket i et ekstra array, rent vrøvl, tomt svar
og forkert svarlængde — alle fem fejler pænt uden at kræsje, og de fire
ugyldige sætter intet motiv. Samlet prøve i jsdom mod de rigtige datafiler: 9
assertions grønne, ingen JS-fejl, hero + 8 kort + 39 mikrokort tegnes, alle
kortbilleder har alt-tekst, et klik åbner læsevisningen med indhold.

DOM-prøven bekræftede målingen uafhængigt af min simulering: **9
billedpladser, 7 med `<img>`, 2 med genereret SVG** — og de to var præcis de
to `kun_aktuel`-artikler med prio 7. Efter rettelsen dækker udvalget **9/9 og
6/6** pladser. Udvalget går fra 53 til 61 artikler; **8 billeder skal laves
ved næste kørsel, ca. $0,27 engangs**, godt under loftet på 35 pr. kørsel.
Billederne findes først, når crawleren har kørt med en `GEMINI_API_KEY` — jeg
kan hverken generere dem eller bruge din nøgle.

**Til Torben:**

- **Emnefiltrene er ikke dækket, og det er en beslutning om penge, ikke om
  kode.** Klikker en læser ét emne fra, tegner forsiden fire store kort inden
  for dét emne — og de er sjældent dem, der fik billede. Målt nu: *Samfund &
  etik* 3 af 9 pladser dækket, *Lanceringer* 1 af 5, *Politik & jura* 4 af 9,
  *Hverdags-AI* 2 af 7, *Penge & marked* 2 af 5. Det kan kun lukkes helt ved at
  give **alle** artikler et billede: 43 mangler i dag, **ca. $1,46 engangs** og
  derefter prisen for hver ny artikel. Jeg har ikke gjort det — det er dine
  penge. Værd at vide: kommentaren ved `BILLED_ANTAL = 250` i `crawler.py`
  siger allerede *"ALLE artikler får AI-billede"*, så koden og hensigten har
  været ude af trit et stykke tid. Jeg lægger det ikke i køen selv; jeg er en
  ekstra kørsel og må ikke røre prioriteringen. **Hovedkørslen i aften bør tage
  det op i fase 2.**
- **Lille robusthedsting, ikke rettet:** svarer motiv-AI'en med et ekstra lag
  array (`[[{...}]]`), fanger `udfyld_billedmotiver` det som `AttributeError`
  og springer batchen over. Det fejler pænt — billedet får bare
  reserve-motivet fra rubrik + resumé — så jeg lod det ligge frem for at rode i
  en funktion, punktet ikke handlede om.
- **Dine 8 filer fra i formiddags er væk fra `git status`** — de er altså
  committet og pushet. Godt; crawlerens egne skrivninger giver ikke længere
  merge-konflikter oven på dem.

---

> **Ekstra kørsel 26.07, formiddag — kort version.** Tre punkter klaret:
> nulstil-knap på kørekortet, bevis-tjekket der lovede for meget, og
> overskrifter uden navn. Alle tre viste sig at være **anderledes end køen
> beskrev dem**, og i alle tre tilfælde fandt målingen det, ikke beskrivelsen.
> Ét fund uden for køen, som jeg mener er dagens største: **ingen side på
> ainyheder.com linker til de 103 artikelsider.** Se nedenfor.
>
> **8 ændrede filer at pushe:** `crawler.py`, `koerekort.html`,
> `koerekort-tjek.html`, `erhverv.html`, `data/hjerne-data.js`,
> `data/hjerner-status.json`, `nat-log.md`, `opgavekoe.md`. Intet i `artikel/`,
> `video/` eller `.github/`, intet slettet. Jeg har tjekket, at der ikke ligger
> en `.git/index.lock` — der lå faktisk en, som mit eget git-kald efterlod, og
> den er fjernet. Det var præcis den, der spærrede for dit commit i morges.
>
> **Du redigerede `natsession.md` kl. 10:01, mens jeg arbejdede.** Jeg læste
> instruksen kl. 09:37, så jeg har arbejdet efter den gamle udgave og har
> **ikke** fulgt din nye førsteregel om at tjekke, om du sidder ved maskinen —
> den fandtes ikke, da jeg startede. Din ændring står urørt; jeg har hverken
> overskrevet eller flettet den. Vi har ikke været i de samme filer: du var i
> `natsession.md`, jeg i `crawler.py`, de tre kørekortsider, køen og loggen.
> Fra næste kørsel gælder din nye regel. Havde den været der i morges, ville
> `find . -newermt '-30 minutes'` have fundet dine egne 09:29-ændringer og
> stoppet kørslen — værd at vide, hvis du trykker **Kør nu** lige efter at have
> rettet noget i panelet.

---

## 2026-07-26 (ekstra kørsel, formiddag) · FUND: ingen linker til vores 103 artikelsider

**Dette er ikke en opgave fra køen.** Det faldt ud af den samlede prøve, hvor jeg
skulle tjekke, at "et klik åbner en artikel". Det gør det — bare ikke vores egen.

**Målt:**

```
artikelsider på disken:                     103
sider i roden, der linker IND i artikel/:     0
artikelsider, der linker TILBAGE til forsiden: 103 af 103
artikelsider, der linker til hinanden:          0
URL'er i sitemap-artikler.xml:                 94   (9 sider mangler)
```

Forsidens kort har `href` og `data-link` sat til **kildens** adresse
(`version2.dk/artikel/…`, `techcrunch.com/…`), og selve artiklen åbnes som en
overlay på forsiden med `#a=<kildens url>`. Det er et fint design for læseren —
men det betyder, at de 103 sider i `artikel/` er **forældreløse**: der findes
ingen vej ind i dem fra nogen side på ainyheder.com. Kun ud af dem.

Det forklarer noget, der allerede står i loggen fra 25.07: *"Google har
indekseret 0 artikelsider."* Uden ét eneste indgående link har Google ingen
grund til at kravle dem og ingen signaler at rangere dem på. Sitemappet var den
eneste vej — og det er, som du ved, aldrig indsendt. Alt arbejdet fra de sidste
to nætter — JSON-LD på 142 sider, alt-tekst på 129 billeder, canonicals,
NewsArticle-schema — ligger på sider, ingen kan nå.

*Punkt 10 i målestokken: "Er der et sted, hvor godt arbejde ligger skjult, hvor
Google ikke kan se os … er dét et problem på lige fod med en fejl i koden. Ofte
et større."*

**Jeg har ikke rørt det, og jeg har ikke lagt det i køen.** Jeg er en ekstra
kørsel; instruksen siger, at omprioritering sker én gang i døgnet, og det er
nattens hovedkørsel, der skal placere det. Men det er efter min måling det
største enkeltfund i dag, større end de tre punkter jeg har lavet, og det bør
formentlig ind som nummer ét under trin 3 — over canonical-punktet, som handler
om de samme sider.

Bemærk også de 9 sider, der ligger på disken men ikke i sitemappet. 5 af dem er
dubletterne, der bevidst blev taget ud i nat. De sidste 4 har jeg ikke
undersøgt.

---

## 2026-07-26 (ekstra kørsel, formiddag) · "AI" talte som et navn

**Fandt:** Køen spurgte, om de ni flagede rubrikker var rimelige. Jeg læste alle
102 i stedet, og spørgsmålet viste sig at være det forkerte. **Selve detektoren
var i stykker.**

`_har_navn()` har fire regler. Den sidste siger: et stort bogstav midt i en
dansk sætning er et navn. På et AI-nyhedssite betyder det, at **"AI" tæller som
et navn** — og "AI" står i næsten hver eneste rubrik. Reglen lige ovenfor
udelukker udtrykkeligt "ai" (`ren != "ai"`), så hensigten var klar nok; den
næste linje åbnede hullet igen. Samme leak gjorde "Det" og "Nu" til navne, når
de stod efter et kolon: *"Bilfabrik afviser robotstrejke: **Det** handler om løn"*.

Resultatet var en måling, der pegede næsten stik modsat virkeligheden:

| | før | efter |
|---|---|---|
| rubrikker crawleren mente manglede navn | 7 af 102 | 29 af 102 |
| af dem, der var falske alarmer | 5 af 7 | 0 |

Og imens de fem falske alarmer optog pladsen, sejlede disse to forbi:

- *"**Gigantens** milliard-regnskab viser historisk minus pga. AI"*
- *"Kæmpe milliardforlig mellem forfattere og **gigantisk AI-firma**"*

Det er ordret det eksempel, punkt 1 i målestokken er skrevet imod: *"Oracle
fyrer 21.000", aldrig "Kæmpe gigant fyrer 21.000".* Reparationsrunden har kørt
i ugevis og har aldrig set dem.

Et sidste fund i samme funktion: prompten `SYSTEM_NAVNGIV` bad AI'en om at
skrive *"Kinesisk techgigant ..."*, når den ikke kan finde et navn — men
"techgigant" står på listen over vage vendinger og ville altid blive afvist.
Prompten foreslog altså et svar, som koden var sikker på at kassere, og brændte
artiklens ene forsøg af.

**Gjorde:** `crawler.py`, alt sammen omkring `_har_navn`:

- "AI" (og "AI-model", "AI-firma", "AI-laboratorium") tæller ikke længere som
  navn — hverken som forkortelse eller som stort bogstav i sætningen.
- Et stort bogstav lige efter kolon, semikolon eller tankestreg tæller ikke.
  Det er grammatik, ikke et navn.
- Ny liste `_GENERISKE_AKTOERER`: rolleord som "Gigant", "Kommune", "Forskere",
  "Stjerner", "Bilfabrik", "Politiker" tæller aldrig som navn, uanset placering.
- `"giganten"` og `"gigantens"` er føjet til de vage vendinger. **Ikke**
  "gigantisk" alene — det er som regel bare et tillægsord om noget andet
  ("OpenAI bygger gigantisk infrastruktur i Georgia"), og at forbyde det gav en
  falsk alarm med det samme. Kun de faste vendinger ("gigantisk AI-firma").
- Ejefald slår nu op i mærkelisten, så *"**Blueskys** AI-assistent"* og
  *"**Østrigs** militær"* genkendes. Mærkelisten har fået lande og de danske
  institutioner, der går igen i feedene (Skat, Ingeniøren, Version2, PFA).
- Prompten beder nu om det mest konkrete, der faktisk står i materialet, og
  siger direkte, at omskrivninger bliver afvist.

**Testede:** 42 assertions — 18 rubrikker der skal fanges, 24 der ikke må
fanges. Alle grønne. To falske alarmer dukkede op undervejs og blev rettet
(`Blueskys` på ejefald, `OpenAI bygger gigantisk infrastruktur` på tillægsordet).
Dertil den samlede prøve: `ast.parse` OK, ingen dobbeltdefinerede konstanter på
modulniveau, `crawler.py` indlæses som modul, `navngiv_rubrikker` uden API-nøgle
ændrer ingenting, og forsiden + kontrolpanelet + de tre rørte sider kører i
jsdom mod de rigtige datafiler uden JS-fejl.

**Til Torben:** To ting.

1. **Næste kørsel vil sende ~29 rubrikker til AI'en** i stedet for ingen. Det er
   en engangsudgift — den tager 25 ad gangen, og hver artikel prøves kun én
   gang — men den kommer på regningen i morgen. Vil du hellere have den delt
   over flere dage, kan `portion=25` sættes ned.
2. Jeg har **ikke** rettet de 29 rubrikker i hånden. Crawleren gør det selv, og
   jeg ville ikke have to hænder i de samme felter.

---

## 2026-07-26 (ekstra kørsel, formiddag) · Bevis-tjekket lovede for meget

**Fandt:** Køen bad om at bytte én sætning ud. Jeg valgte at efterprøve påstanden
først, og det var godt, for problemet var større end sætningen.

Jeg skrev de ti linjer kode, en udenforstående ville skrive — SHA-256 over
`navn|dato|salt`, med begge salte hentet fra vores egen kildekode — og lavede et
bevis-nummer til **"Aldrig Deltaget Hansen"**, som aldrig har åbnet et modul:

```
Grundkort: AIK-20260715-9ZB6MK
Erhverv:   AIKE-20260715-FU4LZ5
```

Begge to fik vores egen tjek-side til at svare **"✅ Beviset er ægte —
udstedt af ainyheder.com til Aldrig Deltaget Hansen, 15. juli 2026"**. Det er
den skærm, en arbejdsgiver kigger på. Så det var ikke kun sætningen nede i
brødteksten, der var forkert — det var også den grønne overskrift, og
manchetten, og meta-beskrivelsen, og første linje i varedeklarationen. Fem
steder sagde det samme, som ikke passer.

Til gengæld virker afvisningen præcis, som den skal: gæt, forkert navn, forkert
format og fremtidige datoer bliver alle afvist. Tjekket er ikke værdiløst — det
er bare noget andet, end vi skrev.

**Gjorde:** `koerekort-tjek.html`. Overskriften ved et gyldigt svar er nu
**"✅ Nummeret passer til navnet"** i stedet for "Beviset er ægte", og linjen
under siger, at nummeret er dét, kørekortet udsteder til navnet — ikke at
personen har bestået noget. Manchet og meta-beskrivelse siger "passer til navnet
og datoen". Varedeklarationen begynder nu med, hvad tjekket siger, ikke med
"bekræfter bevisets ægthed".

Og så tilføjede jeg en boks, der siger det lige ud: beregningen sker i browseren,
opskriften står derfor i sidens kildekode, én der kan læse kode kan lave et
gyldigt nummer til et hvilket som helst navn, og at forhindre det ville kræve en
server og et login — som kørekortet bevidst ikke har. Det er punkt 5 og punkt 9
i samme afsnit: vi vælger gratis og uden login, og så må vi sige, hvad det
koster. Kodekommentaren, som påstanden oprindelig stammer fra, er rettet samme
sted i `koerekort.html` og `erhverv.html`.

**Testede:** 14 assertions. Seks på at hver enkelt overdrivelse er væk, tre på at
forbeholdet står der, én på at rådet om at bede kandidaten vise sine færdigheder
kun står ét sted (jeg kom til at skrive det to gange og fjernede den ene —
punkt 3), og fire på at selve tjekket stadig godkender ægte numre og afviser
gæt, forkert navn, forkert format og fremtidige datoer. Alle grønne. Ingen
JS-fejl. Ingen dark mode på sitet, så de to hardkodede farver i den nye boks
(`#a8853c`, `#faf6ec`) er de samme, filen bruger i forvejen.

**Til Torben:** Der står nu sort på hvidt på tjek-siden, at beviset kan omgås af
én der kan læse kode. Det er ærligt, og det er den rigtige beslutning efter
målestokken — men det er også første gang, siden siger noget negativt om sit
eget produkt, og du kan have en anden mening om, hvor højt det skal stå. Boksen
er let at flytte eller tone ned. Det, jeg **ikke** vil anbefale, er at gå tilbage
til "Beviset er ægte": den sætning er målt forkert nu.

Vil du have et bevis, der faktisk ikke kan omgås, kræver det en server, der
udsteder og slår op. Det er et større stykke arbejde og bryder med "gratis og
uden login" — jeg har ikke lagt det i køen, fordi det er dit valg, ikke et fund.

---

## 2026-07-26 (ekstra kørsel, formiddag) · Nulstil-knap på kørekortet

**Fandt:** Rettelsen, som stod i køen, var forkert — og ville have set ud til at
virke. Køen sagde: "ryd `aikort*`-nøglerne". Jeg talte nøglerne igennem alle 31
HTML-sider først, og der er **elleve** i spil, ikke ni: `aikort`,
`aikort_praktik`, `aikort_praktik_tekst_1`–`_7`, `aikort_udstedt`,
`aikort_bevisnr`, `aikort_e`, `aikort_e_praktik`, `aikort_e_praktik_tekst_1`–`_4`
— **og `aike_udstedt` og `aike_bevisnr`**. De to sidste er
erhvervsbevisets dato og nummer, og de hedder `aike_`, ikke `aikort_`. Et mønster
på `aikort*` rammer dem ikke. Konsekvensen ville have været den værste slags: en
nulstil-knap, der ser ud til at rydde alt, men lader deltager nummer to hente et
erhvervsbevis med **forrige deltagers udstedelsesdato** på. Jeg fandt det kun,
fordi jeg listede nøglerne i stedet for at stole på beskrivelsen.

Desuden: `laeste` (læste artikler, forsiden og cookiesiden) ligger i samme
localStorage og må **ikke** ryddes med. Den er ikke kørekortfremdrift.

**Gjorde:** `koerekort.html` — nyt afsnit "Deler du computeren med andre?" nederst,
lige over kolofonen, plus ~70 linjer JS i det eksisterende IIFE og en håndfuld
CSS-regler. Knappen er ikke en `confirm()`-dialog, men to trin i selve siden:
første klik viser, hvad der står gemt, i klar tekst — *"Dette fjerner 7
gennemførte moduler i grundforløbet, 4 moduler i erhvervsoverbygningen og 9
gemte svar fra øvelserne. Er du sikker?"* — med **Ja, ryd det hele** og
**Fortryd** ved siden af. Efter rydningen tegnes modullisten, fremdriftsbjælken
og bevisboksen om med det samme, så siden viser det, der nu faktisk står gemt,
og kvitteringen tæller sletningerne. Der ryddes på **begge** præfikser,
`aikort` og `aike_`, og på intet andet. Tilføjede også én linje i den
eksisterende indlæsningsløkke, der gemmer modulernes oprindelige status-tekst
("Start her" / "Åbn modul"), så nulstillingen kan sætte dem tilbage præcist.

Teksten siger rent ud, at fremdriften kun ligger i browseren, at vi ikke har den,
at det ikke kan fortrydes, og at et bevis, der allerede er hentet, ikke bliver
ugyldigt af det.

**Testede:** 40 assertions i jsdom mod den rigtige fil, alle grønne — fuldt
gennemført forløb, tom browser, rester uden gennemførte moduler, ødelagt JSON i
localStorage, og localStorage helt spærret (privat browsing). Kontrolleret
specifikt at `aike_udstedt` og `aike_bevisnr` forsvinder, at `laeste` og
`cookie_valg` overlever, at **Fortryd** ikke sletter noget, og at der står
præcis to fremmede nøgler tilbage bagefter. Testen ligger ikke i repoet.

Undervejs fangede testen syv "fejl", der viste sig at være min egen: jeg havde
sat `navigator.serviceWorker = undefined`, hvilket gør `"serviceWorker" in
navigator` sand og `.register` udefineret — en tilstand ingen rigtig browser
har. Rettet i testen, ikke i siden.

**Til Torben:** Knappen sidder kun på `koerekort.html`, ikke på `erhverv.html`.
Den rydder begge forløb, så den dækker, men en der står på erhvervssiden skal
klikke sig tilbage for at finde den. Jeg lod være med at tilføje en linje der
også — det er én sætning, hvis du vil have den. Og: den her knap var
forudsætningen for hold-brug, som `undervisning.html` lægger op til. Siden er
stadig ikke linket fra noget.

> **Efterspil om morgenen (26.07, ca. 08:30).** Tre ting dukkede op, da Torben
> skulle hente nattens arbejde, og de er værd at kende, fordi de kommer igen:
>
> 1. **En efterladt `.git/index.lock`** spærrede for hans commit. Tom fil, fra
>    23:20, altså efterladt af en afbrudt git-kommando i første kørsel. Fjernet.
> 2. **103 merge-konflikter.** Crawleren havde kørt seks gange på GitHub imens og
>    lagt **selvhostede fonte** ind, mens nattens commit lagde **JSON-LD og
>    alt-tekst** ind — begge steder i `<head>`. Kun én linje var reelt i konflikt
>    i `crawler.py`; resten af nattens arbejde beholdt git selv. Løst ved at
>    beholde begge, og for de 102 artikelsider ved at tage crawlerens nyere
>    indhold og køre `opgrader-gamle-artikelsider.py`, som lagde JSON-LD og
>    alt-tekst tilbage. Resultat: 142 af 142 sider har nu begge dele.
>    **Læren: jo længere nattens arbejde ligger upushet, jo større bliver
>    konflikten.** Crawleren rører de samme filer nitten gange i døgnet.
> 3. **Kontrolpanelet sagde "Nat-loggen · FINDES IKKE ENDNU"** om en fil, der
>    havde ligget der i ni timer. Panelet læser et øjebliksbillede i
>    `data/hjerne-data.js`, og den fil skrives kun ved en **lokal** crawler-kørsel
>    — statusfilen var fra 22:28, loggen fra 23:20. Kørt `skriv_hjerne_status()`
>    manuelt. Lagt i køen som et selvstændigt punkt, for det rammer præcis dét,
>    panelet er til: at læse regnskabet om morgenen.
> 4. **Loggen blev vist som rå markdown** i en monospace-tekstboks — med
>    `**stjerner**`, `##` og backticks. Panelet renderer den nu som ét kort pr.
>    nat, med datoen som etiket, titlen i Fraunces, og **Fandt / Gjorde /
>    Testede / Til Torben** som mærkede felter. Nattens regnskab får sit eget
>    fremhævede kort. Rendereren er skrevet i hånden (~70 linjer), fordi panelet
>    åbnes fra `file://`, hvor et bibliotek ikke kan hentes. Grænsen for, hvor
>    meget af loggen der indlejres, er hævet fra 4.000 til 30.000 tegn, og
>    klipningen tager **altid** nattens regnskab med, uanset hvor langt nede det
>    ligger — den første udgave klippede lige før det.
> 5. **Modalen udnyttede ikke skærmen.** Den var låst til 820 px, så en 30.000
>    tegns log blev til meget scroll. Læsevisningen og opgavekøen åbner nu i
>    `min(1560px, 96vw)` og 94 vh. Loggens kort sættes i **to spalter** over
>    1120 px og tre over 1900 px, med `break-inside: avoid`, så et kort aldrig
>    deles. Køen bliver bred, men **ikke** spaltet: dér er rækkefølgen selve
>    indholdet, og to spalter ville gøre "flyt op" umulig at følge. De
>    redigerbare dokumenter beholder de 820 px — en formular bliver ikke bedre
>    af at være bred.
>
> **Uafhentet arbejde ved start af sidste kørsel (03:00):** 110 ændrede filer,
> intet committet. Jeg tjekkede, om noget stammer fra tidligere nætter — det gør
> det ikke. HEAD er `0b54df2` fra kl. 22:55, og alle ændringer har tidsstempel
> mellem 23:20 og 23:55, altså første kørsel i nat. **Ingen ophobning fra
> tidligere nætter, men bunken vokser i nat.** Se regnskabet nederst for den
> fulde liste over, hvad der skal pushes.

## 2026-07-26 · Uafhængig gennemgang af sidste kørsels arbejde

Jeg satte, som natten før, en separat gennemgang til at angribe mit eget arbejde
med besked om at finde fejl frem for at bekræfte. **Den fandt én alvorlig fejl,
mine egne tests ikke fangede — og den ophævede hele nattens rettelse.** Fem
mindre ting oveni. Alle seks er rettet.

**Fejl 1 — min dublet-rettelse ville slå sig selv ihjel ved næste feed-hikke.**

Jeg udledte "hvilke sider er dubletter" af **dagens artikelliste**. Men canonical
på disken er permanent, og artikellisten er ikke. Gennemgangen målte det på vores
egen historik: den slog `data/articles.json` op i fjorten tidligere commits og
fandt, at OpenAI/Hugging Face-historien **manglede i 6 af de 14 kørsler** —
`crawl_feed` returnerer en tom liste ved timeout, og så er artiklen bare væk den
kørsel.

Konsekvensen beviste den i en sandkasse med kopier af `artikel/`:

```
1) begge i feedet:          canonical -> HOVED   | i sitemap: nej
2) kun hovedhistorien:      canonical -> HOVED   | i sitemap: nej
3) hovedhistorien væk:      canonical -> SIG SELV| i sitemap: JA
4) hovedhistorien tilbage:  canonical -> HOVED   | i sitemap: nej
```

I trin 3 er dubletten ikke længere kendt som dublet, så hovedløkken i
`lav_artikelsider` skriver dens side om med en canonical til sig selv og lægger
den tilbage i sitemappet. Næste kørsel vender det tilbage igen. Resultatet ville
være, at sitemappet og fem canonicals svingede frem og tilbage flere gange i
døgnet — og at fem filer blev omskrevet i hver eneste commit. Fjernede man alle
fjorten ejere fra listen, kom **alle fem** dubletsider tilbage i sitemappet.

Med andre ord: den sætning, jeg skrev tidligere i nat — "sitemappet gik fra 102
til 97" — ville ikke have holdt en dag.

Rettet ved at spørge **disken** i stedet for artikellisten. Ny funktion
`_dubletsider_paa_disk()` læser hver af de 102 siders egen canonical og regner
en side for dublet, hvis dens canonical peger et andet sted hen end på den selv.
Hovedløkken springer nu de sider over. Disken er permanent hukommelse;
artikellisten er et øjebliksbillede af, hvad elleve feeds tilfældigvis svarede.

**Fejl 2 — `sektioner` var en hård port, ikke en vægt.** Jeg skrev
`[m for m in frie if m.get("sektioner")]`, og en liste med tolv **tomme**
sektioner er sand. Gennemgangen viste, at en udgave med tolv tomme sektioner
(vægt 396) derfor slog en udgave med 800 tegn rigtig tekst — den anden kom aldrig
i puljen, så vægtene blev aldrig sammenlignet. Stik imod funktionens eget formål.
Ikke udløst i dagens data (tyndeste reelle sektionsfelt er 500 tegn), men latent.
Porten spørger nu til, om der faktisk står tekst i mindst én sektion.

**Fejl 3 — canonical-kæder var mulige.** Peger B på A, og A senere på C, står B
tilbage og peger på en side, der selv er ude af sitemappet. Google følger normalt
ikke kæder. 0 kæder i dagens data, men nåbart, fordi `_slaa_sammen` kører to
gange pr. kørsel og primæren kan skifte mellem passene. Samme rod som fejl 1, og
løst af samme rettelse.

**Fejl 4 — jeg gentog den overdrivelse, jeg selv havde kritiseret.** Tidligere i
nat skrev jeg, at `koerekort-tjek.html` lover for meget med "et opdigtet nummer
vil ikke stemme", og lagde en rettelse i køen. Og så skrev jeg på
`undervisning.html`: *"Tjekket bekræfter, at nummeret er ægte udstedt til dét
navn på dén dato."* Samme påstand — og oven i købet inde i boksen med overskriften
"Ærligt om, hvad beviset ikke er". Rettet til, at tjekket bekræfter, at nummeret
**passer til navnet og datoen**, at det ikke kan gættes, men at det er regnet ud
i browseren og derfor ikke sikret mod nogen, der bevidst vil omgå det.

**Fejl 5 — en regnefejl i min egen undervisningsmodel.** Jeg skrev "to lektioner
à 45 minutter: modul 1–4 den ene gang, 5–7 den anden" og kaldte det den tætteste
pasform. Modul 1–4 er 50 minutter, ikke 45. Delingen sprænger den første lektion.
Rettet til 1–3 (40 min) og 4–7 (55 min), med den forkastede deling nævnt, så
ingen selv kommer til at regne den ud igen.

**Fejl 6 — en side uden canonical-tag kunne blive forældreløs.** Jeg markerede
en side som dublet, *før* jeg vidste, om erstatningen lykkedes. Uden et
canonical-tag ville siden hverken få en canonical eller stå i sitemappet. 0 af
102 sider mangler tagget i dag. Løst af omlægningen: disk-scanningen kan kun
markere en side, der faktisk har en canonical, der peger væk.

**Gennemgangen fandt også ting, den frikendte**, og de er værd at notere, fordi
jeg havde været i tvivl om flere af dem: lambdaen i `re.subn` gør regex-metategn
i erstatningen inerte (afprøvet med `\1`, `\g<0>`, `$&` og backslashes);
`_indholdsvaegt` kaster ikke på dict, set, bool, bytes, selvrefererende lister
eller 400 niveauers indlejring; `max()` kan ikke ramme en tom pulje, fordi begge
kaldsteder garanterer mindst to medlemmer; `kun_aktuel`-reglen er uændret; alle
tal på undervisningssiden passer med modulsidernes egne (7 moduler, 95 minutter,
erhverv 4 × 20); "10-15 minutter" er rigtigt for alle syv moduler; og
`.gitignore` skjuler intet, projektet bruger.

**Testede efter rettelserne:** Gennemgangens eget flip-flop-scenarie kørt mod den
nye kode på kopier — fuldt feed, tre hovedhistorier fjernet, feed tilbage: **5
dubletter og 97 URL'er i alle tre trin**, ingen side sneg sig tilbage i
sitemappet, ingen selv-canonical blev genskrevet. Tre kørsler i træk ændrer 0
filer, og filantallet står på 102. Tolv tomme sektioner taber nu til 800 tegn
tekst, og reelle sektioner slår stadig et langt resumé. Ti felttyper i
`sektioner`, selvreference i `andre` og `andre` uden link: ingen fejl.

Derefter hele den samlede prøve igen: syntaks OK, ingen dobbeltdefinerede navne
blandt 189 moduldefinitioner, import OK, 105 artikler + 40 videoer + ugesiden
gennem skabelonerne, forsiden grøn i jsdom (43 kort, 56 links med href, 12
billeder alle med alt-tekst, ingen JS-fejl), alle 142 artikel- og videosider med
gyldig JSON-LD, og `undervisning.html` grøn med 6.063 tegn og ingen døde links.
**Alt grønt.**

---

## 2026-07-26 · 35 af 96 artikler mangler det fulde brief

**Fandt:** Ingen af de tre mistanker i punktet holdt — hverken loftet,
`hent_artikeltekst` eller redaktør-agenten. **Problemet, som det er beskrevet,
findes ikke.** Til gengæld findes der en fejl bagved, som fik tallet til at se
alarmerende ud.

*Feltet `brief` udfyldes aldrig.* Tæller man det, mangler ikke 35 af 96 — der
mangler **105 af 105**. Grunden er, at `SYSTEM_BRIEF_ARTIKEL` beder modellen om
`rubrik`, `resume`, `sektioner`, `noegletal`, `detaljer`, `betydning` og
`pointer`. Den beder aldrig om et felt, der hedder `brief`. Så
`a["brief"] = str(r.get("brief", "")).strip()` i `_anvend_brief` sætter en tom
streng, hver eneste gang. Feltet er en rest fra en tidligere udgave af prompten.

*Det rigtige felt er `sektioner`, og så ser det helt anderledes ud:*

- **78 af 105 artikler har fuld genfortælling.**
- 27 har ikke. Af dem er **26 `kun_aktuel`** — Version2 og Ingeniøren, hvis
  udgivere ikke tillader arkivering. De får med vilje ingen genfortælling, og
  det er 100 % konsistent: 0 af 26 har sektioner. Det er design, ikke fejl.
- **Præcis 1 artikel er reelt uforklaret:** OpenAI Blog, "OpenAI udlover dusør
  for biologi-fejl", set 9. juli, prio 5. Den har rubrik, resumé og billede, men
  ingen sektioner. 1 ud af 105.

*Og loftet er ikke i nærheden:* `DYBDE_ANTAL = 250` og
`MAX_OMSKRIV_PR_KOERSEL = 200`, mod 105 artikler i arkivet.

*Så tog jeg de 16 tynde artikelsider, som første kørsel gættede var de samme
artikler. Det er de ikke.* Jeg målte hver af de 102 sider:

- **15 af de 16 er faldet ud af 30-dages-vinduet.** De er frosne sider fra en
  ældre skabelon, 375–462 tegn hver, og crawleren kan ikke røre dem, fordi
  artiklerne ikke længere står i `articles.json`.
- Den 16. er den ene uforklarede OpenAI-artikel ovenfor, 359 tegn.
- **`kun_aktuel`-artikler får slet ingen side** — 0 af 26 ligger på disk, fordi
  `lav_artikelsider` springer dem over. De kan altså ikke være årsag til tynde
  sider.

De to ting hænger altså ikke sammen, som vi troede. Tynde sider er ikke et
brief-problem, det er **det frosne arkiv**. Tre af de 16 er i øvrigt de
dubletsider, jeg tog tidligere i nat, så de er allerede ude af sitemappet.

**Gjorde:** Én rettelse — den eneste, en læser kan mærke.

Det døde `brief`-felt stod som **første prioritet i `_slaa_sammen`**:
`[m for m in frie if m.get("brief")]`. Den liste er altid tom, så trin 1 kunne
aldrig ramme, og prioriteringen "brief > rubrik > resten" var i praksis kun ét
trin. Rettet til `sektioner`, som er det felt, der faktisk betyder "fuld
genfortælling". Nu vinder en udgave med gennemskrevne afsnit over en, der kun
har en rubrik — hvilket var meningen hele vejen.

Jeg har **ikke** ryddet feltet ud af de øvrige syv steder, det står, og jeg har
**heller ikke** skrevet det som et punkt i køen. Det var fristende — feltet
kostede os en nat, hvor køen målte noget forkert. Men prøven for at komme i køen
er "hvad ser eller mister en læser", og svaret er: ingenting. Målestokken siger
udtrykkeligt, at teknisk gæld, der ikke kan mærkes af en læser, ikke er et
problem. Så det står her i loggen i stedet, hvor du kan finde det, hvis du en dag
rører ved `_anvend_brief`.

**Testede:** `ast.parse` og import: OK. Otte scenarier mod `_slaa_sammen`: en
udgave med sektioner slår nu en med 5.000 tegns resumé men ingen sektioner; den
fyldigste blandt flere med sektioner vinder; den virkelige OpenAI-sag med
rigtige feltstørrelser giver Ars Technica (vægt 1.962 mod 794);
`kun_aktuel`-reglen holder stadig; et `brief`-felt på 9.000 tegn påvirker nu
ingenting; otte forkerte typer i `sektioner` (`None`, `0`, `""`, `[]`, streng,
tal, dict, liste med `None`) kaster ingen fejl; 105 rigtige artikler gennem
`saml_dublet_historier` uden fejl; og 100 kørsler med uafgjort vægt giver samme
vinder. **Alt grønt.**

**Til Torben:** Punktet kan streges, men tre ting er værd at tage med.

1. **Køen målte på et felt, der ikke findes.** Det er værd at huske næste gang et
   tal ser galt ud: tallet "35 af 96" var hverken rigtigt eller forkert, det målte
   bare noget andet, end det troede. Det rigtige tal er 78 af 105 med fuld
   genfortælling, og 26 af de resterende 27 er tilsigtede.
2. **Version2 og Ingeniøren leverer 26 artikler, som aldrig bliver til rigtigt
   indhold.** De har rubrik og resumé på forsiden, men ingen side og ingen
   genfortælling. Det er det rigtige valg juridisk — men det er en fjerdedel af
   arkivet, der ikke arbejder for os i Google. Det er også dét, mailen til
   Teknologiens Mediehus handler om, og den ligger stadig usendt på din liste.
3. **Det frosne arkiv er det egentlige problem bag "thin content".** 15 sider kan
   ikke rettes af crawleren, fordi artiklerne er ude af vinduet. Første kørsel
   pegede på det samme i nat. Jeg har lagt det i køen som et selvstændigt punkt,
   nu hvor det er målt: det er ikke en teoretisk risiko, det er 15 sider i dag,
   og tallet vokser hver måned.

---

## 2026-07-26 · Sammenlagte historier efterlader en forældreløs artikelside

**Fandt:** Punktet var rigtigt i sin diagnose og forkert i sin begrundelse — og
under målingen dukkede en større fejl op, som ikke stod i det.

*Antallet: 5 sider.* 14 artikler har sammenlagte kilder, 20 kilder i alt. Af dem
har 5 efterladt en side på disk. Alle 5 lå i sitemappet, og alle 5 havde en
canonical, der pegede på dem selv.

*Men det er ikke "næsten samme indhold".* Jeg sammenlignede teksterne:
ligheden er **6–20 %**, og rubrikkerne er forskellige. Siderne er frosne på det
tidspunkt, de var selvstændige, så de er skrevet ud fra hver deres kilde. Google
ville næppe kalde det dobbelt indhold. Problemet er et andet og mere præcist:
**tre sider om samme begivenhed konkurrerer om den samme søgning**, og uden et
canonical-signal vælger Google selv hvilken — ofte ikke den, vi linker til.

*Og så det, der ikke stod i punktet: hovedhistorien var valgt forkert.* To af de
fem spøgelsessider er **fyldigere end den historie, de blev slået sammen med**:

| | side på disk | |
|---|---|---|
| Ars Technica (spøgelse) | **2.798 tegn** | konkrete detaljer: smuthullet i softwarepakke-cachen, hvordan agenten fik adgang |
| Ars Technica (spøgelse) | **2.063 tegn** | reinforcement learning, forskernes advarsler |
| OpenAI Blog (hovedhistorie) | **1.417 tegn** | "hændelsen giver vigtige indsigter", "de fleste detaljer er endnu ikke..." |

Alle tre handler om det samme — OpenAIs AI-agent brød ud af sit testmiljø og
angreb Hugging Faces servere. Grupperingen var altså rigtig. Men vinderen blev
**virksomhedens egen pressemeddelelse**, og den er diplomatisk dér, hvor de to
uafhængige udgaver er konkrete. Læseren, der klikker fra forsiden, får den
tommeste af de tre.

Årsagen står i `_slaa_sammen`. Kommentaren over funktionen lover "Behold den med
mest indhold: brief > dansk rubrik > nyeste" — men koden gjorde:

```python
primaer = next((m for m in frie if m.get("brief")), None) \
       or next((m for m in frie if m.get("rubrik")), None) or frie[0]
```

`next()` tager **den første**, ikke den bedste. Indholdsmængden blev aldrig målt.
Alle fire udgaver havde en rubrik, ingen havde et brief, og så afgjorde
rækkefølgen i listen det. OpenAI Blog stod først.

**Gjorde:** To ting i `crawler.py`.

- **Ny `_indholdsvaegt()`, og `_slaa_sammen` vælger nu `max()` i stedet for
  `next()`.** Rangordenen brief > rubrik > resten er bevaret — det er kun inden
  for hvert trin, at den bedste nu vinder over den første. Vægten er summen af
  tegn i `brief`, `resume_da`, `betydning`, `sektioner`, `detaljer`, `pointer`,
  `noegletal` og `figurer`. På den virkelige sag: OpenAI Blog 112, Ars Technica
  477.
- **Ny `_peg_dubletsider_mod_hovedhistorien()`**, kaldt fra `lav_artikelsider`.
  Den retter canonical i de tabende udgavers sider, så de peger på
  hovedhistorien, og holder dem ude af `sitemap-artikler.xml` — et sitemap bør
  kun indeholde canonical-URL'er. **Siderne slettes ikke.** Nogen kan have linket
  til dem, og en 404 er værre end en dublet; de står som før, men fortæller nu
  Google, hvor den rigtige udgave er.

  Køpunktet foreslog i stedet, at hovedhistorien kunne "arve den ældste URL". Det
  fravalgte jeg: slug'en er en md5 af kildelinket, så at flytte den ville ændre
  adressen på en side, der allerede er udgivet, og bryde ethvert eksisterende
  link. Canonical opnår det samme over for Google uden at flytte noget.

Kørt på de rigtige filer: 5 sider rettet, sitemappet gik fra 102 til **97 URL'er**,
og der ligger stadig 102 filer i `artikel/`.

**Testede:** `ast.parse` og import som modul: OK. `_slaa_sammen` mod ti
tilfælde med `kald_ai` urørt (funktionen kalder ingen model): den virkelige
OpenAI-sag vælger nu Ars Technica; brief slår stadig en fem gange længere tekst
uden brief; en `kun_aktuel`-kilde med 9.000 tegn taber stadig til en fri kilde
med 10; når alle har arkivforbud vælges den bedste af dem; ni varianter af tomme
og forkerte felttyper (`None`, tal, dict, liste, tom streng) kaster ingen fejl;
`foerst_set` arves stadig som det tidligste og billedet arves stadig; og 100
kørsler med uafgjort vægt giver samme vinder hver gang. Hele
`saml_dublet_historier` kørt mod de rigtige 105 artikler: 105 ud, ingen fejl.

`_peg_dubletsider_mod_hovedhistorien` kørt på **kopier i `/tmp` først**: alle 5
canonicals peger rigtigt, hver side har præcis én canonical, alle har stadig
`<h1>` og `</html>`, kørt to gange i træk ændrer 0 filer, og filantallet er
uændret 102. Derefter kørt på de rigtige filer og verificeret: sitemappet er
gyldig XML, ingen af de 5 står i det længere, alle 5 sider er intakte.

**Til Torben:**

**Rettelsen virker kun fremad.** De tre historier, der allerede er slået forkert
sammen, bliver ikke lavet om. Grunden er, at `saml_dublet_historier` starter med
at smide alt væk, der én gang er registreret som `andre` — de to Ars
Technica-udgaver findes ikke længere i `articles.json`, kun som frosne HTML-sider.
Deres brief og sektioner er væk som data, så jeg kan ikke bytte om på dem uden at
finde på indhold. Det ville bryde punkt 5.

Konsekvensen er værd at kende: for OpenAI-historien peger canonical nu **fra de
to fyldige sider mod den tynde**. Det er stadig bedre end tre sider, der slås om
samme søgning — men det er ikke godt. Den rigtige løsning er ikke
canonical-akrobatik, det er at hovedhistorien får et ordentligt brief. Den
artikel har `brief: False`, og det er præcis næste punkt i køen. De to hænger
sammen.

---

## 2026-07-26 · Der findes ingen side, der taler til undervisere

**Fandt:** Punktet var rigtigt, og bogstaveligt. Ordene *underviser*, *undervisning*,
*aftenskole* og *jobcenter* står **nul steder** på nogen af sidens 30 HTML-sider.
Der er ikke en svag indgang, sådan som kørekortet havde — der er ingen.

Men da jeg målte, hvad en sådan side ærligt kunne love, fandt jeg tre ting, der
betyder mere for en underviser end selve siden:

*1. Forløbet tager 95 minutter, ikke 105–140.* Modulsiderne siger hver især,
hvor lang tid de tager: 10, 15, 15, 10, 15, 15, 15 minutter. Summen er **95
minutter**. Men `koerekort.html` skrev "Hvert modul tager 15-20 minutter" — et
interval, som **ingen** af de syv moduler ligger i. Det er ikke en detalje for en
underviser: 95 minutter er to lektioner à 45, mens 140 minutter ikke passer ind i
nogen normal undervisningsblok. Tallet afgør, om forløbet overhovedet kan bruges.
Forslaget fra første kørsel i nat gentog "15–20 minutter hvert", fordi det er dét,
kørekortsiden siger — fejlen var begyndt at forplante sig.

*2. Fremdriften følger browseren, ikke personen — og der er ingen nulstil-knap.*
Alt gemmes i `localStorage` (`aikort`, `aikort_praktik`, `aikort_e` m.fl.). Jeg
søgte efter en måde at rydde det på og fandt ingen. For en privat læser er det
ligegyldigt. For et jobcenter eller et bibliotek med delte maskiner er det
afgørende: **deltager nummer to ved samme computer ser modulerne som allerede
gennemført**, og næste hold arver forrige holds afkrydsninger. Det er den slags,
der får en institution til at opgive efter første forsøg — og det står ikke
nogen steder.

*3. Beviset kan ikke bære den vægt, `retning.md` lægger på det.* Dokumentet siger,
at en underviser kan bruge beviserne "til at dokumentere, at holdet har været
igennem noget". Det kan de ikke helt. Bevis-nummeret er
`SHA-256(navn|dato|salt)`, og **saltet står i klartekst i sidens kildekode**
(`ainyheder-koerekort-v1`, og `ainyheder-koerekort-e-v1` til erhvervsbeviset).
Enhver, der kan åbne "vis kilde", kan lave et gyldigt nummer til et hvilket som
helst navn. Det er en uundgåelig følge af, at alt kører i browseren uden server —
altså prisen for punkt 9 — men `koerekort-tjek.html` skriver "et opdigtet nummer
vil ikke stemme", og det er en anelse for stærkt. Resten af den sides
varedeklaration er til gengæld god og ærlig.

**Gjorde:** To ting.

- **Ny side: `undervisning.html`** (i roden, 780 px kolonne, samme CSS-grundlag
  som `om.html`). Den er skrevet til den, der skal *bruge* forløbet på andre —
  ikke til en deltager. Indhold: de syv moduler med deres rigtige tider og summen
  95 minutter; tre konkrete undervisningsmodeller (to lektioner à 45, en formiddag
  på tre timer, et modul om ugen i syv uger); hvad der kræves rent praktisk; hvad
  beviset er; erhvervsoverbygningen; og et svar på "må vi bruge det, som vi vil".
  Den slutter med en kontaktopfordring til `kontakt@ainyheder.com`.

  De tre fund ovenfor står **på siden**, ikke skjult: et afsnit om at beviset ikke
  er en anerkendt uddannelse og ikke dokumenterer hvem der sad ved tastaturet, og
  et om at delte computere deler fremdrift. Jeg har skrevet dem som forbehold, en
  professionel ville skrive dem — de gør siden mere troværdig, ikke mindre, og en
  underviser, der opdager dem selv bagefter, holder op med at bruge siden.

  Jeg har også skrevet den største praktiske forhindring frem i lyset: **hver
  deltager skal have en gratis konto hos ChatGPT, Gemini eller Claude**, fordi
  modul 2 og frem beder dem gøre noget i en rigtig chatbot. For et hold på tyve er
  det tyve kontooprettelser med e-mail eller telefonnummer. Det er værd at vide,
  før man planlægger dagen, ikke midt i den.

- **Rettet ét tal i `koerekort.html`:** "Hvert modul tager 15-20 minutter" →
  "10-15 minutter". Det er ikke pynt. Uden rettelsen ville den nye side sige 95
  minutter, og siden ved siden af ville sige 105–140 — en underviser, der klikkede
  videre, ville se to forskellige svar på det spørgsmål, der afgør hans planlægning.

**Testede:** `undervisning.html` i jsdom: h1 og main og footer på plads, canonical
og description sat, 5.881 tegn tekst (langt over de 900, Google regner for tyndt
indhold), 9 links hvoraf 7 interne — **alle peger på filer, der findes**, og alle
har både href og tekst. Ankeret `#krav` findes. Ingen billeder uden alt-tekst
(der er ingen billeder). Alle syv modultitler står på siden, summen 10+15+15+10+
15+15+15 er efterregnet til 95, og nøgletallene AIK-formatet og "pensum version 1"
er der. Ingen JS-fejl. **Alt grønt.**

**Til Torben — siden er færdig, men den er ikke linket nogen steder.**

Det var med vilje: hvor den skal stå, er dit valg, ikke mit. Åbn den og se på den
først. Vil du have den, skal der gøres **to ting, og de hører sammen**:

1. **Link til den.** Mit forslag er en linje i footeren på `koerekort.html` og
   `erhverv.html` — "Underviser du? Sådan bruger du kørekortet på et hold" — plus
   et kort på `laer.html`. Ikke forsiden: en underviser kommer ikke ind via
   nyhederne, han kommer via kørekortet eller via en søgning.
2. **Læg den i `sitemap.xml`.** Gør det samtidig med at du linker den. En side i
   sitemappet, som intet linker til, ser for Google ud som en forældreløs side, og
   det er værre end ikke at have den med.

Tre ting, jeg **ikke** har rettet, fordi de er selvstændige beslutninger:

- **Der mangler en nulstil-knap på kørekortet.** Det er den mindste rettelse, der
  ville gøre forløbet brugbart på delte computere: én knap, der rydder
  `aikort*`-nøglerne, med en "er du sikker". Jeg har lagt det i køen.
- **`koerekort-tjek.html` lover en anelse for meget** med "et opdigtet nummer vil
  ikke stemme". Den ærlige formulering er, at nummeret ikke kan *gættes*. Også i
  køen.
- **`retning.md` bygger på, at beviserne kan dokumentere gennemførelse over for en
  institution.** Efter målingen ovenfor holder det ikke helt. Vej nr. 3 i
  dokumentet er stadig den rigtige — men argumentet er "her er et færdigt gratis
  forløb på dansk, I ikke selv skal skrive", ikke "her er et bevis, I kan stole
  på". Det er en rettelse i et dokument, du selv har skrevet, så jeg har ladet den
  være.

---

### Nattens regnskab · 2026-07-26

**Ekstra kørsel 09:37–11:0x:** klarede 3 punkter mere — nulstil-knappen på
kørekortet, overdrivelsen på bevis-tjekket, og overskrifter uden navn. Køen er
ikke omprioriteret (det hører til hovedkørslen). Ét fund uden for køen:
**ingen side linker til vores 103 artikelsider** — se øverst i loggen.

**Ekstra kørsel 12:03–12:40:** klarede **3 punkter** mere — de manglende
billeder, "Hvad betyder det for dig" og rubrikkerne læst som en nabo. Køen er
ikke omprioriteret; det hører til hovedkørslen. Alle tre var **anderledes end
køen beskrev dem**, og i alle tre tilfælde var årsagen den samme slags fejl:
**to steder i systemet, der skulle være enige, var det ikke** — crawlerens
billedudvalg mod forsidens, og skribentens prompt mod redaktørens. 79
assertions, alle grønne. To ting uden for køen: **`.git/index.lock` lå der
igen** (ryddet — se nedenfor), og der stod **en stavefejl i en rubrik på
forsiden**.

**Ekstra kørsel 14:13–15:0x:** klarede **2 punkter** mere — de 12 navnløse
rubrikker og canonical på de statiske sider. Køen er ikke omprioriteret; det
hører til hovedkørslen. Begge punkter var **rigtigt målt, men forkert
forklaret**: rubrikkerne var ikke låst, fordi AI'en gav op, men fordi den aldrig
fik crawlerens egen genfortælling at se — og canonical-punktet regnede
`uge.html` for en statisk fil, som crawleren i virkeligheden genskriver. 261
assertions, alle grønne. Jeg kørte oven på din egen redigering af køen kl. 14:08,
fordi den ene rørte fil var netop det punkt, jeg skulle arbejde på.

Klaret: **7 punkter** — 3 af første kørsel, 4 af sidste. Nye i køen: **4**.

Færre end de 7, jeg måtte skrive, og det er med vilje. Tre kandidater faldt for
prøven i målestokken: det døde `brief`-felt (en læser ser ingenting — teknisk
gæld tæller ikke), en fjerde tynd artikelside (samme sag som det frosne arkiv,
allerede skrevet), og en oprydning i `_anvend_brief`s `if True:` (kosmetik).
Køen har 33 åbne punkter, altså under de 40, hvor noget skal parkeres.

**De fire punkter i nat (sidste kørsel):**

1. **Undervisersiden.** Ordene "underviser" og "undervisning" stod nul steder på
   30 sider. `undervisning.html` er skrevet og testet — ikke linket endnu.
2. **Forældreløse artikelsider.** 5 sider, ikke "næsten samme indhold" men
   6–20 % lighed. De peger nu canonical mod hovedhistorien og er ude af
   sitemappet. Undervejs: `_slaa_sammen` valgte den *første* udgave, ikke den
   bedste — OpenAIs pressemeddelelse slog to fyldigere Ars Technica-udgaver.
   Den uafhængige gennemgang fandt bagefter, at min første udgave af rettelsen
   ville svinge frem og tilbage ved feed-timeouts; den læser nu disken i stedet
   for dagens artikelliste.
3. **De 35 manglende briefs.** Problemet findes ikke. Feltet `brief` udfyldes
   aldrig, så tallet målte et dødt felt. Rigtige tal: 78 af 105 har fuld
   genfortælling, 26 af resten er tilsigtede, 1 er uforklaret.
4. **Ordbogen** (fase 2). 48 opslag målt mod 133.200 tegn artikeltekst. Fandt
   intet, der bryder målestokken.

**Gennemgik i fase 2:** `ordbog.html`, som ikke har været set på. Og hele
sidesamlingen i den samlede prøve — det var dér, canonical-fundet dukkede op.

**Og som natten før satte jeg en uafhængig gennemgang på mit eget arbejde.** Det
var igen godt givet ud: den fandt, at min dublet-rettelse ville have ophævet sig
selv, første gang et feed fik timeout — hvilket den beviste sker i 6 af 14
kørsler. Plus fem mindre ting, heriblandt at jeg havde gentaget præcis den
overdrivelse om bevis-tjekket, som jeg selv havde kritiseret og lagt i køen tre
timer forinden. Alt seks er rettet og testet. Se afsnittet øverst.

**Øverst i køen nu:** **"Kørekortet kan ikke nulstilles, og det spærrer for
hold"** — fordi den er den eneste af nattens fund, der både bryder målestokken
synligt og står direkte i vejen for vej 3 i `retning.md`, samme dag som
undervisersiden blev skrevet.

Rækkefølgen ændrede sig mere end sædvanligt, fordi køen nu er sorteret efter de
fire trin i instruksen i stedet for efter emne. **Trin 1 — "i stykker for
læseren lige nu" — er tomt.** Det er et rigtigt resultat, ikke et hul: alt, der
var målt i stykker, er klaret. Du er velkommen til at være uenig i, at
nulstil-knappen slår de fire manglende navne i overskrifter; jeg vægtede den
højere, fordi den blokerer 200 læsere ad gangen frem for at genere fire.

**Det, jeg helst vil have dig til at se på:** ingen af de 31 statiske sider har
en canonical. Alle 142 artikel- og videosider har. Det er nummer ét under trin 3
og koster én linje pr. side — men det er også dét, der afgør, om arbejdet i
Search Console betaler sig, når du får sitemappene indsendt.

**Om det uafhentede arbejde:** 113 ændrede filer, HEAD står stadig på `0b54df2`.
Intet committet, intet pushet. Fordelingen: 102 sider i `artikel/` (5 af dem med
ny canonical i nat, resten fra første kørsel), plus `crawler.py`, `index.html`,
`koerekort.html`, `sitemap-artikler.xml`, `.gitignore`, `undervisning.html`,
`_redaktion/opgavekoe.md`, denne log, `forslag-koerekort-indgang.html`,
`undersoegelse-daglig-mail.md` og `opsaetning/opgrader-gamle-artikelsider.py`.
`data/`, `video/` og `.github/workflows/` er urørt.

**En efterladt git-lås spærrede for dit commit.** Da du prøvede at committe de
113 filer i GitHub Desktop, kom "A lock file already exists in the repository".
Det var `.git/index.lock` — tom, 0 bytes, med tidsstempel **25. juli kl. 23:20**,
altså efterladt af første kørsel, hvor en git-kommando er blevet afbrudt midt i.
Den har ikke noget med natsessionens egen `_redaktion/.nat-koerer` at gøre. Jeg
har fjernet den, og git svarer normalt igen.

*Til næste natsession:* rydder du ikke op efter dine git-kald, spærrer du for
Torbens commit om morgenen — og fejlbeskeden peger ikke på os. Tjek
`.git/index.lock` som en del af afslutningen, sammen med låsefilen. Er den tom
og der ikke kører en git-proces, kan den fjernes med `rm -f .git/index.lock`.

**En fejl, jeg selv lavede og rettede:** jeg kørte `npm install jsdom` i
projektmappen for at kunne teste, og lagde dermed 26 MB og 1.807 filer i
`node_modules/` midt i repoet. De er ryddet væk igen, og der er ikke noget for
dig at gøre. Jeg har desuden lagt `node_modules/`, `package.json` og
`package-lock.json` i `.gitignore` sammen med natsessionens låsefil, så det ikke
kan ske ved et uheld næste gang — testværktøjet hører ikke til siden og skal
aldrig pushes.

**Den samlede prøve efter alle ændringer:** `crawler.py` og engangsscriptet
parser; ingen dobbeltdefinerede navne blandt 188 moduldefinitioner; crawleren
importeres uden fejl; alle 105 artikler, 40 videoer og ugesiden gennem
skabelonerne uden en eneste fejl; forsiden i jsdom mod de rigtige datafiler
tegner 43 kort, 56 links med href, 12 billeder alle med alt-tekst, ingen
JS-fejl; alle 142 artikel- og videosider har gyldig JSON-LD med `@type`, h1,
canonical og alt-tekst, og intet JSON-LD er lækket ud i den synlige tekst;
`undervisning.html` er grøn. **Alt grønt.**

Én ting så rød ud og var det ikke: forsidens "Dagens overblik" er tomt i
jsdom-prøven. Det er ikke noget, jeg har brækket — `brief.json` er dateret
25. juli, og forsiden skjuler med vilje overblikket, når det ikke er fra i dag
(`if (d.dato !== dagNoegle(new Date())) return;`). Næste crawler-kørsel skriver
et nyt. Det er i øvrigt præcis det forbehold, første kørsel skrev om
kørekort-forslaget: lægger du indgangen ind i Dagens overblik, forsvinder den
sammen med overblikket, hvis en kørsel fejler.

---

## 2026-07-25 · Uafhængig gennemgang af nattens eget arbejde

Jeg satte en separat gennemgang til at angribe det, jeg selv havde lavet, med
besked om at finde fejl frem for at bekræfte. Det var godt givet ud: **den fandt
to reelle fejl, mine egne tests ikke fangede.** Begge er rettet.

**Fejl 1 — jeg havde åbnet et XSS-hul på forsiden.** Forsidens `esc()` bygger på
`textContent → innerHTML`, som escaper `&`, `<` og `>` — men **ikke
anførselstegn**. Det var uskadeligt, så længe `esc()` kun blev brugt til tekst.
Men mine to nye alt-tekster satte værdien ind i en *attribut*
(`alt="${esc(...)}"`), og der bryder et `"` ud af attributten. Gennemgangen
beviste det ved at lægge
`Skilt med teksten "STRØMSVIGT" x" onload="…"` ind i `billedmotiv` og indlæse
forsiden: `onload` blev sat som en rigtig DOM-attribut på `<img>`. I en browser
ville den kode køre, når billedet var hentet — fuld JS-eksekvering på
ainyheder.com.

Og det er ikke teoretisk: **7 af 79 billedmotiver indeholder allerede
anførselstegn** (`'STRØMSVIGT'`, `'Godkendt'`, `'100M'`), fordi modellen får
besked på at beskrive tekst på skilte. **11 af 40 YouTube-titler har også
anførselstegn.** Om modellen vælger `'` eller `"` næste gang er tilfældigt.

Rettet med én linje i `esc()`: `.replaceAll('"', "&quot;")`. Hullet i `esc()` var
der før i nat — det ramte allerede `data-link` og `title` — men det var mine
ændringer, der førte de to felter med flest anførselstegn ind i attributter, så
det var den rigtige anledning til at lukke det for alle 36 kaldesteder.

**Fejl 2 — min egen `_jsonld()`-escaping var ufuldstændig.** Jeg lukkede
`</script>`, men HTML-parseren har en anden vej ind: tegnfølgen `<!--<script`
indeholder ikke `</`, så min `.replace("</", "<\\/")` rørte den ikke. Den sætter
parseren i en tilstand, hvor det følgende `</script>` **ikke** afslutter blokken
— og så bliver resten af dokumentet slugt som scriptindhold. Gennemgangen målte
resultatet: siden blev **helt blank**, ingen `<h1>`, ingen `<main>`, ingen
`<footer>`. De to dele kan endda ligge i hvert sit felt (`<!--` i rubrikken,
`<script` i resuméet), så ingen enkelt streng ser mistænkelig ud.

Det er ikke XSS — indhold i `application/ld+json` kører ikke — men det er en
ét-tegns-nedlukning af en artikelside. Én uheldig feed-titel, fx en artikel *om*
HTML-injektion, og Google ser en tom side.

Rettet ved at escape `<`, `>` og `&` som JSON-unicode (`<`) i stedet.
Gyldig JSON, læses ens af alle parsere, og ingen af de farlige tegnfølger kan
opstå i det, browseren ser. Samme rettelse i engangsscriptet.

**Fire mindre ting, også rettet:**

- `dateModified` var sat til `foerst_set`, altså hvornår crawleren *først* så
  artiklen. Det rykker sig aldrig, når siden faktisk ændres, så feltet var i
  bedste fald meningsløst. Fjernet helt — det er valgfrit hos Google, og et
  ærligt `dateModified = nu` ville få hver kørsel til at genskrive alle sider.
- Engangsscriptet hardkodede `+02:00`. Alle nuværende sider er fra juli, hvor det
  er rigtigt, men scriptet er gemt til genbrug, og i november er offset `+01:00`.
  Udleder nu offset af datoen med `zoneinfo`.
- Scriptet udfyldte **alle** tomme `alt=""`. Det er konceptuelt forkert: et
  dekorativt billede *skal* have tomt alt efter WCAG. Begrænset til
  `<img class="top">`, altså artikelbilledet.
- `_uge_side_html` læste `h.get("billedmotiv")`, men `uge.json` gemmer aldrig det
  felt — død kode, der foregav en kilde, der ikke findes. Fjernet.

Gennemgangen fandt også en fejl, jeg havde indført i min egen rettelse: jeg
brugte `re.subn` med en erstatnings*streng*, hvor en rubrik med `\` eller `\g`
ville blive læst som en regex-backreference. Erstatter nu med en funktion.

**Testede efter rettelserne:** Gennemgangens egne angreb kørt mod `crawler.py`:
seks varianter af `<!--<script`, `</script>` og payload delt over to felter — alle
seks giver nu gyldig JSON-LD og en intakt side med h1, main og footer.
XSS-nyttelasten lagt i både `billedmotiv` og en YouTube-titel og forsiden
indlæst: **0 `on*`-attributter injiceret**, `window.__XSS` usat, kortbillederne
har præcis `src,alt,loading,style`, og alt-teksten er stadig korrekt *med*
anførselstegnene i. Derefter hele den samlede prøve igen: syntaks, ingen
dobbeltdefinitioner, 105 artikler og 40 videoer gennem skabelonerne uden fejl,
forsiden grøn mod de rigtige datafiler, alle 102 artikelsider og 40 videosider
valide, forslagssiden grøn, kontrolpanelet urørt og intakt. **Alt grønt.**

**Til Torben — to ting jeg *ikke* har rettet, med vilje:**

1. **10 artikelsider har `image` i deres JSON-LD, der peger på en billedfil, der
   ikke findes længere.** Crawleren rydder billeder op efter 30 dage, men lader
   siderne stå. Problemet er præeksisterende — `og:image` på præcis de samme 10
   sider pegede allerede på den samme manglende fil — men structured data er en
   mere synlig kanal, så det kan dukke op som "Image not found" i Search Console.
   Jeg har lukket det for fremtiden (scriptet dropper nu `image`, hvis filen ikke
   findes), men ikke gået tilbage og rettet de 10, fordi den rigtige løsning er
   at beslutte, om billeder skal bevares lige så længe som siderne. Det er et
   selvstændigt punkt, og jeg må ikke tilføje køpunkter som første kørsel.
2. **Ingen af crawlerens nye JSON-LD-linjer er kørt i produktion endnu.** Alle
   102 sider på disk er skrevet af engangsscriptet, ikke af crawleren. Det er
   som forventet — crawleren kører først næste gang workflow'et går — men det
   betyder, at ændringerne i videosiderne og ugesiden endnu ikke er set på disk.
   De er testet mod rigtige data, men bemærk det, når du pusher: den første
   kørsel derefter vil genskrive de 79 artikelsider, der stadig er i
   `articles.json`, med crawlerens egen version. Det er meningen.

---

## 2026-07-25 · Dagens overblik som daglig mail

**Fandt:** Ja, det kan gøres gratis — men den svære del er ikke teknisk.
Undersøgelsen ligger i `_redaktion/undersoegelse-daglig-mail.md`. Det korte:

*Buttondown tillader det udtrykkeligt.* Deres FAQ siger, at priserne "assume
that you're sending at most one email a day to your entire subscriber base" —
altså er én daglig mail præcis, hvad den gratis plan er beregnet til. Gratis op
til 100 abonnenter, ingen pris pr. mail. Og planlagt afsendelse på et bestemt
klokkeslæt er også gratis; deres dokumentation siger direkte "Available on the
Free plan".

*Der skal næsten intet bygges.* `_send_nyhedsbrev()` sender allerede til
Buttondowns API, `BUTTONDOWN_API_KEY` ligger i secrets og er sat i workflowet,
tilmeldingsformularen står tre steder, og `lav_dagens_brief()` skriver fem
færdige punkter med links hver dag. Der mangler en funktion, der laver fem
punkter om til en mail — og et svar på hvornår.

*Timingen er det egentlige tekniske problem.* Crawlerens natlige cron er 00:37
UTC, altså 02:37 dansk om sommeren og 01:37 om vinteren, og det er dén kørsel,
der skriver dagens brief. Sender man i samme øjeblik, lander mailen midt om
natten. Det løses ikke ved at flytte cron — briefet skal skrives tidligt, så
forsiden er klar om morgenen — men med `status: "scheduled"` og en
`publish_date`. Klokkeslættet skal regnes ud med `zoneinfo`: 07:00 dansk er
05:00Z om sommeren og 06:00Z om vinteren. Hardkodes det, rykker mailen sig en
time to gange om året.

*Og der er en dubletfare.* `lav_dagens_brief` springer over, hvis briefet
allerede har dagens dato — men det hviler på, at `brief.json` bliver committet.
Fejler commit eller push én gang, skriver næste kørsel briefet igen og sender
mailen igen. Crawleren kører 19 gange i døgnet, så der er 19 chancer for det.
En markør `mail_sendt` i filen gør det idempotent.

**Gjorde:** Ikke ændret noget i koden — punktet bad om en undersøgelse, og der
er en beslutning at træffe først. Skrev undersøgelsen med de fire mulige veje og
den ærlige pris på hver.

**Testede:** Regnede cron-tiderne efter med `zoneinfo` for både sommer- og
vintertid, talte kørslerne (19 i døgnet), verificerede linjenumre og funktioner
i `crawler.py`, og bekræftede at ugebrevets body ikke starter med `---` — det
ville API'et afvise med `body_contains_frontmatter`. Alle tal i undersøgelsen er
målt, ikke husket.

**Til Torben:** Der er en spærre, du skal tage stilling til, før noget bygges.
**Formularen siger "Få ugens AI-overblik på mail — hver fredag"**, og mailens
fodnote siger "Du får denne mail, fordi du har tilmeldt dig Ugens AI-overblik".
Der står *uge* eller *fredag* fire steder. At begynde at sende dagligt til den
liste er syv gange mere, end folk sagde ja til — det bryder punkt 5, og uventet
frekvens er den hyppigste grund til spam-markeringer, som også vil ramme
ugebrevets leveringsevne.

Vil du lade folk *vælge* mellem dagligt og ugentligt, koster det tagging og
segmentering hos Buttondown, **+$9/md**. To selvstændige nyhedsbreve koster
**+$29/md**. Gratis er kun to veje: sende dagligt til alle uden at spørge (det
vil jeg fraråde), eller ærligt lægge listen om til dagligt med en varsling og et
tydeligt valg om at blive på ugentligt eller melde fra.

Min anbefaling er at afklare samtykket først — det er fem minutters beslutning,
ikke kode — og derefter **se abonnenttallet**, som jeg ikke kan se uden
API-nøglen. Er det tocifret og lavt, flytter en daglig mail mindre end at blive
fundet i Google, og så bør Search Console-punktet og undervisersiden komme
først. En daglig vane slår en ugentlig påmindelse, men en daglig mail, ingen har
bedt om, slår ingenting.

---

## 2026-07-25 · Kørekortet er gemt bag nyhederne

**Fandt:** Værre end punktet antyder — kørekortet er ikke gemt bag nyhederne, det
er slet ikke nævnt. Jeg indlæste forsiden med dens egne data og talte, hvad en
førstegangsbesøgende kan klikke på:

- **2 af 56 links** peger på noget, man kan lære af. De 54 andre er nyheder,
  filtre og kilder.
- **0 links** peger direkte på kørekortet. Heller ikke på ordbogen, prompts,
  guiderne, quizzen eller erhvervsdelen — alle syv lære-sider er usynlige fra
  forsiden.
- Det ene lære-link er pillen "🎓 Lær AI", og den ligger **sidst** i topbarens
  filterrække: efter kategorifiltrene, emnemenuen, Forskning, YouTube og Ugens
  overblik. Den bruger samme `.pill`-klasse som nyhedsfiltrene, så den *ser ud
  som et filter* — ikke som en vej videre. På en telefon er den scrollet ud til
  højre.
- Det andet ligger i footeren.
- Begge fører til `laer.html`, en mellemside. Kørekortet er altså **to klik
  væk**, og ordet "kørekort" står **ikke ét sted** på forsiden.

Til gengæld er indholdet bag døren i orden: `laer.html` har en skarp overskrift,
en tre-vejs-indgang (helt ny / vil kunne det / skal bruge det på jobbet) og ni
værktøjskort. Problemet er ikke, hvad der ligger bag døren. Det er, at forsiden
ikke fortæller, at døren findes.

**Gjorde:** Ikke ændret noget på forsiden — punktet bad om et forslag, og
forsidens vigtigste plads er dit valg, ikke mit. I stedet ligger der nu et
forslag, du kan **se** i stedet for at læse:
`_redaktion/forslag-koerekort-indgang.html`. Åbn den i en browser.

Forslaget er **en fodlinje i bunden af Dagens overblik**: en tynd skillelinje,
teksten "Vil du kunne det selv? AI-kørekortet — syv moduler, 15 minutter ad
gangen, gratis" og en knap, der siger "Start modul 1 →" og går direkte til
`koerekort.html`, altså uden om mellemsiden.

Begrundelsen for netop det sted: dagens overblik er det første, en besøgende ser,
og det eneste sted på forsiden, hvor redaktionen taler direkte til læseren. Når
man netop har læst fem punkter om, hvad der sker i AI, er det dér spørgsmålet
"burde jeg egentlig forstå det her bedre?" opstår. Og det er ikke et banner: det
ligger inde i et kort, der allerede findes, med samme greb som "Hvad betyder det
for dig" på artikelsiderne.

Løftet er efterprøvet mod `koerekort.html`, så vi ikke lover for meget: syv
moduler, 15–20 minutter hvert, gratis, uden login. Det står der.

Siden viser forsiden før og med forslaget i sidens egne farver og fonte, den
færdige CSS, de to steder i `index.html` der skal røres — og tre andre
placeringer jeg forkastede, med grunden til hver. Hvis du er uenig, kan du se
præcis hvad du er uenig i.

**Testede:** Forslagssiden i jsdom: begge visninger tegnes, fodlinjen har tekst
og knap, linket peger rigtigt (`../koerekort.html` fra `_redaktion/`, verificeret
at filen findes), alle links har href, ingen JS-fejl, CSS'en er med i filen. Alt
grønt. Forsiden er ikke rørt, så der er intet at regressionsteste på den.

**Til Torben:** Der er ét forbehold, du skal kende, før du siger ja. Dagens
overblik skjuler sig selv, hvis `brief.json` ikke er fra i dag
(`if (d.dato !== dagNoegle(…)) return;`). Fejler crawleren en morgen, forsvinder
indgangen sammen med overblikket. Jeg mener, placeringen er værd at betale det
for — men vil du have indgangen stående uanset hvad, hører den i stedet lige
under `#dagensBrief` som sit eget element. Det står også i forslaget.

Uafhængigt af hvad du vælger: pillen "🎓 Lær AI" bør flyttes frem foran
kategorifiltrene eller ud af filterrækken. Så længe den ligger sidst blandt
filtre, læses den som et filter. Det er en lille ting, og den kan laves uanset
om fodlinjen kommer ind.

---

## 2026-07-25 · Ingen ved, om Google har set de 83 artikelsider

**Fandt:** Tre ting, og den vigtigste stod ikke i opgavebeskrivelsen.

*1. Selve leveringen er i orden.* Begge sitemaps svarer 200 live med gyldig XML —
`sitemap-artikler.xml` med 102 URL'er, `sitemap-videoer.xml` med 40. Hver URL
svarer til en fil, der findes; ingen dubletter, ingen forældreløse. Jeg hentede
alle 142 sider live: alle 200. `robots.txt` henviser til alle tre sitemaps, og
en URL, der ikke findes, giver korrekt 404. Der er intet i stykker her.

*2. Men Google har ikke indekseret én eneste af dem.* `site:ainyheder.com` giver
7 sider: forsiden, faq, om, erhverv-2, erhverv-3, koerekort-6, koerekort-tjek.
`site:ainyheder.com/artikel` giver Googles besked "matchede ikke nogen
dokumenter". Altså: 0 af 102 artikelsider og 0 af 40 videosider er indekseret.
Sitemappene er ikke problemet — de er formentlig aldrig blevet indsendt.

*3. Og da jeg målte hvorfor, viste det sig at artikelsiderne manglede
struktureret data.* Alle 40 videosider havde `VideoObject`-schema. Alle 102
artikelsider havde ingenting. Uden det kan Google ikke se, hvad der er en
nyhedsartikel, hvornår den udkom, eller hvilket billede der hører til — og
NewsArticle-schema er forudsætningen for at komme i Google Nyheder og Top
Stories. Koden til at gøre det rigtigt lå der allerede; den var bare kun brugt
til videoerne.

Samtidig: **alle 129 billeder på siden havde `alt=""`** — tom alt-tekst. Både på
artikelsiderne, på forsidens kort og på videokortene. For en skærmlæser findes
billedet ikke, og Google Billeder kan ikke se, hvad det viser. På videosiderne
var det værre: der er billedet det eneste indhold i et link, så linket havde
slet ingen tekst at læse højt.

Der lå en færdig løsning ubrugt i dataene: feltet `billedmotiv`, som findes på
alle 74 artikler med billede, er art director-beskrivelsen af præcis den scene,
billedet viser. Den er skrevet, gemt — og blev aldrig brugt til noget.

**Gjorde:**

- `crawler.py` · `_artikel_side_html`: tilføjet `NewsArticle`-JSON-LD med
  headline, description, billede, `datePublished`/`dateModified`,
  `articleSection`, `inLanguage: da-DK`, `isAccessibleForFree` og publisher
  "AI-nyheder" som organisation (ingen personnavne — punkt 8). `isBasedOn`
  peger på originalkilden, så det står i dataene, at vi genfortæller.
- `crawler.py` · alt-tekst fra `billedmotiv` med rubrikken som reserve — på
  artikelsiden, på ugesidens kort og på videosidens miniature.
- `crawler.py` · ny hjælpefunktion `_jsonld()`. **Den lukkede et reelt hul:** en
  rubrik med `</script>` i sig ville lukke JSON-LD-blokken for tidligt, så
  resten af den havnede som synlig tekst på siden og den strukturerede data gik
  tabt. Rubrikker kommer fra fremmede feeds. Videosiderne havde samme svaghed
  og har haft den hele tiden — nu bruger begge skabeloner den samme sikre vej.
- `crawler.py` · `_artikel_side_html` kastede `AttributeError`, hvis både
  `rubrik` og `titel` manglede. Nu falder den blødt tilbage til tom streng.
- `index.html` · samme alt-tekst-rettelse i forsidens `visuel()` og i
  YouTube-kortene, som bygges af sidens egen JavaScript.
- **Nyt:** `opsaetning/opgrader-gamle-artikelsider.py`. Crawleren genskriver kun
  sider for artikler, der stadig ligger i `articles.json` — og den beholder kun
  30 dage. 23 af de 102 sider var altså faldet ud af vinduet og ville aldrig få
  den nye skabelon. Scriptet bygger JSON-LD ud fra de oplysninger, siden selv
  bærer (og:title, description, og:image, canonical, kickeren, kildelinket) og
  udfylder tomme alt-tekster med rubrikken. Kørt: alle 102 sider opgraderet.

**Testede:**

- `ast.parse` på både `crawler.py` og det nye script: OK.
- `crawler.py` importeret som modul, ingen dobbeltdefinerede modulnavne.
- `_artikel_side_html` med `kald_ai` erstattet af en falsk funktion, mod seks
  tilfælde: rigtig artikel med billede, artikel uden billede, alle felter tomme,
  tal som `billedmotiv`, liste som `billedmotiv` med `None` i rubrik og titel,
  og HTML-injektion (`</script><b>` og `<script>alert(1)</script>` i rubrik og
  motiv). De første kørsler fandt tre fejl — TypeError på ikke-strenge,
  AttributeError på `None`, og den ødelagte JSON-LD-blok. Alle rettet, alle seks
  tilfælde består nu, og escapingen holder: `<h1>` og `alt` er HTML-escapet, og
  der er kun ét `</script>` på siden, JSON-LD'ens eget.
- Alle 105 artikler og alle 40 videoer gennem skabelonerne: 0 fejl. Ugesiden: OK.
- Forsiden i jsdom med `fetch` mod de rigtige datafiler (stubben sat i
  `beforeParse`, ellers kører sidens scripts først): 60 kort tegnes, dagens
  overblik vises, 41.852 tegn indhold, 56 links med href, klik på et
  artikellink kaster ingen fejl, 12 af 12 billeder har alt-tekst, ingen JS-fejl.
- Opgraderingsscriptet kørt på kopier i `/tmp` først, valideret med jsdom, og
  kørt en anden gang for at bekræfte, at det er idempotent: "0 opgraderet, 102
  var i orden".
- Til sidst alle 142 sider på disk gennem jsdom: 102 artikelsider og 40
  videosider har præcis én JSON-LD-blok, gyldig JSON, `@type` korrekt, h1 og
  canonical på plads, ingen billeder uden alt-tekst, intet JSON-LD lækket ud i
  den synlige tekst.
- **Samlet prøve efter alle ændringer: alt grønt.**

**Til Torben:**

*Det vigtigste i nat er noget, kun du kan gøre.* Koden er klar, men siden bliver
ikke fundet, fordi sitemappene aldrig er indsendt. Fire skridt i Google Search
Console, og det tager ti minutter:

1. **Bekræft ejerskabet af ainyheder.com**, hvis det ikke er gjort. Vælg
   "Domæne" og læg den TXT-post ind hos din DNS-udbyder — så dækker den også
   `www` og fremtidige undersider. (Alternativt "URL-præfiks" med en HTML-fil i
   roden, hvis DNS er besværligt.)
2. **Indsend alle tre sitemaps** under Sitemaps: `sitemap.xml`,
   `sitemap-artikler.xml`, `sitemap-videoer.xml`. Det er dét skridt, der mangler.
   `robots.txt` henviser til dem, men Google finder dem hurtigere, når de er
   indsendt.
3. **Bed om indeksering af forsiden** via URL-inspektion → "Anmod om
   indeksering". Gør det for én artikelside også, som stikprøve. Der er en
   kvote på ca. 10 om dagen, så gå ikke i gang med alle 102 — sitemappet
   klarer resten.
4. **Kig igen efter en uge** under Sider. Nu ved vi, hvad tallet skal
   sammenlignes med: 7 indekserede sider i dag, 149 mulige (102 artikler + 40
   videoer + 7 der er inde). Står artiklerne stadig som "Fundet – ikke
   indekseret" om to uger, er det et signal om, at Google vurderer indholdet
   som for tyndt, og så er det en anden opgave.

To ting, du selv skal beslutte:

- **16 artikelsider har under 900 tegn tekst.** Google kalder den slags "thin
  content", og de er de første, der bliver sprunget over. De 16 er formentlig
  dem, der mangler det fulde brief — det står som et selvstændigt punkt i køen
  ("35 af 96 artikler mangler det fulde brief"), og de to hænger sammen.
  Det bekræfter, at det punkt er vigtigere end det ser ud.
- **21 af 40 videosider har også under 900 tegn.** Samme problem, samme risiko.

En strukturel ting, jeg vil have dig til at kende: **artikelsider fryses, når de
falder ud af 30-dages-vinduet.** Det er derfor, jeg måtte skrive et engangsscript
i nat. Om et år vil langt de fleste artikelsider stå på en gammel skabelon, og
enhver forbedring vil kun ramme den nyeste måned. Scriptet kan køres igen, men
den rigtige løsning er, at crawleren selv kan genskrive en side ud fra sidens
eget indhold. Jeg skriver det ikke som et køpunkt nu — første kørsel må ikke
ændre køen — men sidste kørsel i nat bør vurdere det.

Endelig: der var **intet uafhentet arbejde** ved starten, `git status` var rent.
Nu er der 106 ændrede filer — 102 artikelsider, `crawler.py`, `index.html` og
det nye script. Jeg har hverken committet eller pushet.

Én ting, jeg lod stå med vilje: omslagsbilledet på `uge.html` har fortsat
`alt=""`. Det ligger som ren dekoration bag overskriften, og der er tom alt-tekst
det rigtige valg efter WCAG — en skærmlæser skal springe det over, ikke læse det
op.

---

### Nattens regnskab · 2026-07-25 (første kørsel)

Klaret: **3 punkter.** Nye i køen: 0 — første kørsel laver kun fase 1 og ændrer
ikke køen. Fase 2 og 3 er sidste kørsels opgave.

Gennemgik: ingen fase 2. Men jeg satte en uafhængig gennemgang på mit eget
arbejde, og den fandt to reelle fejl, som er rettet — se afsnittet øverst.

De tre punkter:

1. **Sitemaps og indeksering.** Leveringen er i orden, men Google har indekseret
   0 af 142 artikel- og videosider. Rettede undervejs manglende NewsArticle-schema
   på alle 102 artikelsider, tom alt-tekst på alle 129 billeder, og en sårbarhed,
   hvor en rubrik kunne ødelægge den strukturerede data.
2. **Kørekortet er gemt bag nyhederne.** Målt: 2 af 56 links fører til
   lære-indhold, 0 direkte til kørekortet. Forslag ligger til beslutning i
   `_redaktion/forslag-koerekort-indgang.html`.
3. **Dagens overblik som daglig mail.** Kan gøres gratis, og koden findes næsten.
   Men abonnenterne har sagt ja til en ugentlig mail — det skal afklares først.
   `_redaktion/undersoegelse-daglig-mail.md`.

Øverst i køen nu: **"Der findes ingen side, der taler til undervisere"** — de tre
punkter over den er klaret. Rækkefølgen er ikke ændret af mig; den flyttede sig af
sig selv, fordi de tre øverste røg af.

Det vigtigste, der venter på dig: **indsend de tre sitemaps i Google Search
Console.** Alt SEO-arbejdet i nat er spildt, indtil det er gjort. Instruksen står
i punkt 1 ovenfor.

**109 filer er ændret, og jeg har hverken committet eller pushet.** Der var intet
uafhentet arbejde, da jeg startede — `git status` var rent, og HEAD står stadig på
`0b54df2`, som den gjorde kl. 23.

Fordelingen, så du ved, hvad du pusher: 102 sider i `artikel/`, plus `crawler.py`,
`index.html`, `_redaktion/opgavekoe.md`, denne log,
`_redaktion/forslag-koerekort-indgang.html`,
`_redaktion/undersoegelse-daglig-mail.md` og
`opsaetning/opgrader-gamle-artikelsider.py`.

`data/`, `video/` og `.github/workflows/` er urørt.
