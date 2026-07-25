# Natsessionens arbejdsinstruks

Det her er den instruks, natsessionen arbejder efter kl. 23 og kl. 03.
Ret den frit — den læses forfra hver nat, så ændringer virker med det samme.

---

## Først: tjek at du er alene

Der kører to sessioner i døgnet, og de må aldrig arbejde samtidig i de samme filer.

1. Findes `_redaktion/.nat-koerer`, så læs tidsstemplet. Er det mindre end 3 timer
   gammelt, arbejder en anden session lige nu: **stop med det samme** og skriv én
   linje i `_redaktion/nat-log.md` om, at du sprang over. Er den ældre, er den
   efterladt af en afbrudt session — overskriv den og fortsæt.
2. Ellers: skriv nuværende tidspunkt (ISO 8601) i `_redaktion/.nat-koerer`.
3. **Slet altid `_redaktion/.nat-koerer`, før du slutter** — også hvis du stopper undervejs.

## Hvilken kørsel er du?

Der er to hver nat, og de har **forskellige opgaver**. Kig på klokken:

- **Er den mellem 22 og 01: du er FØRSTE kørsel.** Du laver kun fase 1 — arbejd
  køen. Du skal hverken evaluere eller omprioritere. Spring fase 2 og 3 over.
- **Er den mellem 02 og 05: du er SIDSTE kørsel.** Du laver fase 1, og derefter
  fase 2 og 3, som afslutter natten.
- **Er du i tvivl** (kørslen er forsinket, eller den første aldrig kørte): kig i
  `nat-log.md`. Findes der allerede et "Nattens regnskab" for i dag, er du
  første kørsel af den næste nat. Findes der ikke noget for i dag, og klokken er
  efter 01, så tag hele turen — fase 1, 2 og 3.

Grunden: evaluering og omprioritering skal ske ÉN gang pr. nat. Sker det to
gange, omgør den anden kørsel den førstes prioritering, og køen skifter
rækkefølge uden at nogen har lært noget nyt.

## Læs derefter, i denne rækkefølge

1. `_redaktion/redaktionens-oejne.md` — målestokken. Ni punkter, og et afsnit om
   hvad der IKKE er et problem. Den afgør alt.
2. `_redaktion/opgavekoe.md` — køen. Du arbejder oppefra og ned. Crawlerens
   natlige gennemgang skriver selv sine forslag ind nederst i køen under
   "Fra den natlige gennemgang" — så der er kun ÉN liste at forholde sig til.
3. `_redaktion/nat-log.md` — hvad tidligere nætter fandt og besluttede.
4. `_redaktion/kritik-seneste.md` — gennemgangens fulde tekst med tallene bag.
   Kun hvis du har brug for baggrunden; forslagene står allerede i køen.

**Tjek også, om der ligger uafhentet arbejde.** Kør `git status --short`. Er der
ændrede filer fra tidligere nætter, har Torben ikke pushet endnu. Skriv det
ØVERST i nat-loggen med det samme — han bygger videre på noget, verden ikke har
set, og de filer, crawleren selv skriver, vil begynde at give merge-konflikter.

---

## Fase 1 — Arbejd (hovedparten af natten)

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

**Stop i tide.** Er du sidste kørsel, så sørg for at have plads tilbage til fase
2 og 3. De er vigtigere end ét punkt mere.

### Til allersidst i fase 1: virker det hele stadig sammen?

Hvert punkt er testet for sig. Det siger intet om, hvad tre ændringer gør ved
hinanden. Har du rørt noget som helst i nat, så kør en samlet prøve, FØR du går
videre:

- `python3 -c "import ast;ast.parse(open('crawler.py',encoding='utf-8').read())"`
- Indlæs `crawler.py` som modul, og tjek at der ikke er dobbeltdefinerede
  konstanter på modulniveau. Præcis dén fejl gjorde, at hver eneste artikel-brief
  blev skrevet med den forkerte instruks i ugevis, uden at nogen opdagede det.
- Forsiden i jsdom mod de rigtige datafiler: ingen JS-fejl, kortene tegnes,
  dagens overblik vises, og et klik åbner en artikel.
- Er der rørt ved kontrolpanelet: samme prøve på `_redaktion/kontrolpanel.html`.

Fejler noget, så ret det, før du logger. En nat, der efterlader siden i stykker,
er værre end en nat uden arbejde — Torben pusher om morgenen uden at læse koden.
Skriv resultatet af den samlede prøve i loggen, også når alt er grønt.

## Fase 2 — Evaluér siden med friske øjne

**Kun sidste kørsel.** Er du første kørsel, springer du fase 2 og 3 over, skriver
loggen for det, du nåede, sletter låsefilen og stopper.

Tæl, hvor mange punkter der er klaret i nat i alt — også dem, første kørsel tog.
Kald tallet N.

Gå på jagt efter nye. Vælg et sted, der ikke har været gennemgået de seneste
nætter — en side, en del af crawleren, en måling. Se på det som en læser.

**Du må skrive op til N nye punkter i køen. Du SKAL ikke skrive N.**

Et punkt kommer kun i køen, hvis det kan svare på alle tre:

1. Hvad ser eller mister **en læser**? Konkret, med et eksempel fra siden.
2. Hvilket af de ni punkter i målestokken brydes?
3. Hvad er den mindste rettelse? Noget, der kan laves på én nat.

Fandt du ingen, skriver du nul og noterer: *"Gennemgik X — fandt intet, der
bryder målestokken."* Det er et fuldgyldigt resultat. Opfundet arbejde koster
Torben tid og gør siden dårligere.

Genåbn ikke noget fra "Klaret", medmindre du kan måle, at det er gået i stykker igen.

## Fase 3 — Prioritér hele køen til næste nat

Sortér **hele** køen om efter denne rækkefølge:

1. **Noget er i stykker for læseren lige nu** — tomme sider, døde links, forkerte tal.
2. **Noget bryder målestokken synligt** — jargon, gentagelser, uprofessionelt udseende.
3. **Noget gør siden mærkbart bedre** — nyt indhold, bedre struktur, hurtigere.
4. **Undersøgelser** — hvor vi ikke ved, om der er et problem.

Inden for samme trin: det, der rammer flest læsere, kommer først. Ved uafgjort:
det billigste at rette.

Bliver køen længere end 40 punkter, flyttes de svageste ned under `## Parkeret`.

Skriv til sidst, hvad der nu står øverst — og én sætning om hvorfor rækkefølgen
ændrede sig. Torben skal kunne være uenig.

---

## Loggen

Efter hvert færdigt punkt: flyt det i `opgavekoe.md` ned under "Klaret" med dato,
og skriv øverst i `nat-log.md`:

```
## <dato> · <opgavens navn>
**Fandt:** <hvad målingerne viste — også hvis problemet ikke var som beskrevet>
**Gjorde:** <hvad du ændrede, i hvilke filer>
**Testede:** <hvad du kørte, og hvad der kom ud>
**Til Torben:** <hvad han skal vide, beslutte eller gøre>
```

Afslut natten med:

```
### Nattens regnskab · <dato>
Klaret: <N> punkter. Nye i køen: <M> (<hvorfor færre end N, hvis M < N>).
Gennemgik: <hvad du så på i fase 2>
Øverst i køen nu: <punktet> — <én sætning om hvorfor>
```
