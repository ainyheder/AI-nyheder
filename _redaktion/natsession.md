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

## Læs derefter, i denne rækkefølge

1. `_redaktion/redaktionens-oejne.md` — målestokken. Ni punkter, og et afsnit om
   hvad der IKKE er et problem. Den afgør alt.
2. `_redaktion/opgavekoe.md` — køen. Du arbejder oppefra og ned.
3. `_redaktion/kritik-seneste.md` — crawlerens egen gennemgang, hvis den findes.
4. `_redaktion/nat-log.md` — hvad tidligere nætter fandt og besluttede.

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

**Stop i tide.** Sørg for at have plads tilbage til fase 2 og 3. De er vigtigere
end ét punkt mere.

## Fase 2 — Evaluér siden med friske øjne

Tæl, hvor mange punkter du klarede. Kald tallet N.

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
