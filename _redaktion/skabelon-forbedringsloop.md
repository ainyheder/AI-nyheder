# Skabelon: kontrolpanel og forbedringsloop til et nyt projekt

Det her er ikke dokumentation for ainyheder.com. Det er **en prompt, du kan
kopiere** ind i en Claude Code-session i et *andet* projekt, så den bygger det
samme maskineri der — tilpasset dét projekt.

## Sådan bruger du den

1. Åbn en session i det nye projekts mappe (rodmappen, ikke en undermappe).
2. Kopiér alt mellem de to streger nedenfor og send det som din første besked.
3. Svar på spørgsmålene. Det tager 15-20 minutter, og det er dér, kvaliteten
   afgøres — resten kan maskinen selv.

Et par ting, det er værd at vide, før du går i gang:

- **Svar konkret på "hvem er det til".** Skriver du "alle", får du en målestok,
  der ikke kan afgøre noget, og så finder loopet kun stavefejl.
- **Spørgsmålet om, hvad der IKKE er et problem, er det vigtigste.** Uden det
  finder en agent uendeligt meget "teknisk gæld", ingen bruger nogensinde mærker.
- **Har projektet ingen målinger, så sig det.** Prompten sætter så det letteste
  op i stedet for at lade som om.

---

Jeg vil have det samme maskineri, som kører på et andet projekt af mig: et
kontrolpanel, jeg kan åbne lokalt, og et loop, hvor en agent med jævne mellemrum
gennemgår projektet og foreslår, hvad der skal forbedres. Du skal bygge det her,
tilpasset dette projekt.

## Hvad maskineriet består af

Fem dele. De hænger sammen, og ingen af dem virker alene.

1. **En målestok** — ét dokument, der beskriver hvad "godt" betyder *for netop
   dette projekt*, skrevet ud fra mine faktiske beslutninger, ikke ud fra
   generelle råd. Den indeholder også et afsnit om, hvad der udtrykkeligt
   **ikke** tæller som et problem. Målestokken afgør alt andet.
2. **Én kø** — én prioriteret liste over hvad der skal laves. Både jeg og
   maskinen skriver i den samme liste. Aldrig to lister.
3. **En log** — et regnskab pr. færdigt punkt: hvad blev målt, hvad blev
   ændret, hvad blev testet, hvad skal jeg vide.
4. **En arbejdsinstruks** — reglerne agenten arbejder efter, når den kører.
5. **Et kontrolpanel** — én lokal HTML-side, der viser tilstanden og lader mig
   redigere målestokken, køen og instruksen uden at åbne en editor.

Oveni de fem: **en måling**, der forbinder loopet med virkeligheden, så
forslagene handler om, hvad brugerne faktisk gør — ikke om hvad der ser pænt ud.

## Trin 1 — Undersøg selv, før du spørger mig

Spørg mig ikke om noget, du kan finde ud af ved at kigge. Læs projektet igennem
først og find selv ud af:

- Hvad er det for et projekt, hvilket sprog og hvilke rammeværk?
- Hvordan bygges, køres og udrulles det? Findes der CI (`.github/workflows/`,
  `.gitlab-ci.yml`, andet)?
- Findes der allerede målinger — analytics-scripts i HTML, en fejllog,
  Sentry, App Store Connect, en database med brug?
- Findes der allerede noget, der ligner en kø eller en køreplan (TODO-filer,
  issues, et projektboard)?
- Er der en README eller CLAUDE.md, der siger noget om, hvem projektet er til?
- Hvad ville en agent kunne ændre uden at ødelægge noget, og hvad er skrøbeligt?

Skriv derefter kort til mig, hvad du fandt — og stil så kun de spørgsmål,
du stadig mangler svar på.

## Trin 2 — Spørg mig om det her

Grupperne betyder noget. Spring ikke en gruppe over, fordi den er svær.

**A. Målestokken — hvad "godt" betyder her**

1. Hvem er det til? Beskriv ikke en målgruppe, men **én konkret person**. Hvad
   kan de, hvad gider de ikke, og hvad er de kommet efter? Formulér til sidst
   en enkelt prøve, som ethvert forslag kan holdes op imod — noget i retning af
   *"ville hun forstå det her og gide gå videre?"*
2. Nævn 5-10 beslutninger, du har truffet i projektet, som du ville **forsvare**,
   hvis nogen foreslog det modsatte. Det er dem, der bliver til punkterne i
   målestokken. Generelle råd om god kode eller godt design skal ikke med — kun
   det, der er sandt for netop dette projekt.
3. Hvad har nogen (eller en AI) foreslået, som du bevidst har sagt **nej** til?
   Hvad bliver du træt af at få stillet forslag om? Det bliver til afsnittet om,
   hvad der ikke tæller som et problem — og det er dét afsnit, der afgør, om
   loopet bliver brugbart eller bare støjende.
4. Hvornår går det **godt**? Giv mig et tal, ikke en følelse. Og: kan et
   projekt være fejlfrit og alligevel mislykket her? Hvis ja, skal det være et
   selvstændigt punkt i målestokken, der trækker mod de andre.

**B. Virkeligheden — hvad vi kan måle**

5. Hvilke tal findes allerede? Besøg, brugere, fejl, nedbrud, anmeldelser,
   supportsager, frafald, salg — hvad som helst, der siger noget om, hvad folk
   *gør*, ikke hvad vi tror.
6. Findes der ingen: hvad ville være det letteste at få op at køre? Hvem kan
   oprette nøglen — kan jeg selv, eller skal andre involveres?
7. Hvilket tal ville, hvis du kendte det i morgen, **ændre hvad du arbejder på**?
   Det er dét, målingen skal hente først.

**C. Maskineriet — hvor loopet kører**

8. Hvor skal agenten køre: på min maskine, i CI, eller begge dele? Hvor ofte?
9. Må agenten committe og pushe selv, eller skal jeg godkende? Hvem trykker på
   knappen i dag?
10. Arbejder jeg selv i mappen, mens loopet kan finde på at køre? (Hvis ja, skal
    der bygges en lås og et tjek for, om jeg er i gang — ellers taber en af os
    sit arbejde uden at opdage det.)
11. Hvor skal køen bo: en fil i repoet, GitHub-issues, eller noget tredje?
12. Koster noget af det her penge pr. kørsel (API-kald, byggetid)? Hvad er loftet?

**D. Grænser**

13. Hvad må agenten ændre uden at spørge? Hvad skal den **aldrig** røre?
14. Hvad går der galt, hvis noget fejler ubemærket? Hvor skal den hellere stoppe
    og sige til end at gætte?

## Trin 3 — Byg det

Når jeg har svaret, bygger du de fem dele. Følg de her regler — de er lært den
hårde vej på det andet projekt, og de skal ikke genopfindes.

**Om målestokken**

- Skriv den ud fra mine svar på spørgsmål 2, i mine ord, ikke i generelle vendinger.
- Hvert punkt skal kunne afgøre en uenighed. Kan et punkt ikke bruges til at
  sige nej til noget, er det ikke et punkt.
- Tag afsnittet om, hvad der ikke er et problem, med — ordret fra mine svar.
- Skriv øverst, at hvis jeg retter i filen, ændrer det hvad maskinen leder efter.
  Det er meningen.

**Om køen og forslagene**

- Én liste. Maskinens forslag skrives ind i den samme kø som mine egne, ikke i
  en separat rapport, jeg skal huske at læse.
- Et forslag kommer kun i køen, hvis det kan svare på alle tre: (1) hvad ser
  eller mister **en bruger**, konkret og med et eksempel; (2) hvilket punkt i
  målestokken brydes; (3) hvad er den **mindste** rettelse, der kan laves i én
  omgang. Kan det ikke kobles til målestokken, er det ikke vigtigt.
- Prioriteringen er fast, i denne rækkefølge: (1) i stykker for brugeren lige
  nu, (2) bryder målestokken synligt, (3) gør det mærkbart bedre, (4)
  undersøgelser, hvor vi ikke ved, om der er et problem. Inden for samme trin:
  det, der rammer flest, først; ved uafgjort det billigste at rette.
- **Loft på nye forslag:** agenten må skrive op til lige så mange nye punkter,
  som den har klaret — men den *skal* ikke skrive nogen. "Gennemgik X, fandt
  intet, der bryder målestokken" er et fuldgyldigt resultat. Opfundet arbejde
  er dyrere end ingenting.
- Evaluering og omprioritering sker **én gang pr. periode**. At arbejde køen må
  ske så tit, det skal være. Ellers omgør hver kørsel den forriges rækkefølge,
  uden at nogen har lært noget nyt.

**Om arbejdsinstruksen**

- **Mål, før du bygger.** Antag aldrig at problembeskrivelsen er rigtig — tæl
  det, læs koden, kør funktionen. Viser målingen, at problemet ikke findes, er
  dét også et resultat.
- **Ét punkt ad gangen, færdigt og testet, før det næste røres.** Fem halvfærdige
  ting, der hver især ser ud til at virke, er værre end ingenting.
- **Test både at det virker, og at det fejler pænt.** Og kør til sidst en samlet
  prøve: hvert punkt er testet for sig, hvilket intet siger om, hvad tre
  ændringer gør ved hinanden.
- **Log efter hvert punkt, ikke til sidst.** Formatet: *Fandt / Gjorde /
  Testede / Til mig*.
- **Rør ikke andet end nødvendigt.** Ingen omskrivning af ting, der virker.
- Kan et punkt ikke lade sig gøre, så skriv hvorfor, flyt det ned, og tag det
  næste. Gå ikke i stå.
- Kan flere kørsler overlappe: lav en låsefil med tidsstempel, tjek om jeg selv
  har rørt filer for nylig, og slet altid låsen igen — også ved afbrydelse.

**Om målingen**

- Den skal **fejle stille**. Mangler nøglen, springes trinnet over, og loopet
  kører videre uden. Målinger er en gave, ikke en forudsætning.
- Gem tallene i en fil i repoet, så de kan versioneres og ses over tid.
- Før tallene ind i agentens gennemgang som et afsnit, den skal vægte **højest**
  — og sæt dem op, så det, der *ikke* bliver brugt, er lige så synligt som det,
  der bliver. Fraværet er som regel det interessante.
- Bed mig aldrig om at sende dig en API-nøgle. Skriv i stedet en opskrift på,
  hvordan jeg selv laver den med færrest mulige rettigheder, og hvor den skal
  lægges.

**Om kontrolpanelet**

- Én selvstændig HTML-fil, ingen byggetrin, ingen eksterne biblioteker.
- **Den må ikke være offentligt tilgængelig.** Læg den et sted, udrulningen ikke
  publicerer, og verificér bagefter med et rigtigt kald, at den giver 404. Gæt
  ikke — tjek.
- Den skal kunne åbnes direkte fra `file://`. Det betyder: læs data fra en
  `.js`-fil, der sætter en variabel på `window` (ikke `fetch` mod JSON, som
  browseren blokerer lokalt), og brug **relative** stier til alt — også til
  skrifttyper og deres `url()` inde i CSS-filen.
- Panelet skal vise tilstanden og lade mig redigere målestokken, køen og
  instruksen. Kan projektet vælge model eller instruks pr. AI-trin, skal det
  også kunne styres her.
- Mangler data, skal panelet **selv sige hvad der mangler, og hvad jeg skal
  gøre** — ikke stå tomt.
- Vis det, jeg skal handle på, mindst lige så tydeligt som det, der går godt.

## Trin 4 — Verificér, og vis mig det

Byg ikke bare og sig, det er færdigt.

- Kør loopet igennem én gang for øjnene af mig, eller vis en prøvekørsel med
  realistiske data.
- Vis kontrolpanelet i **begge** tilstande: med data og uden.
- Verificér, at panelet ikke er offentligt tilgængeligt.
- Sig eksplicit, hvad der endnu ikke virker, og hvad jeg selv skal gøre — især
  hvis der er en nøgle, kun jeg kan oprette.

Og sig til, hvis noget af det, jeg har svaret, ikke hænger sammen. En målestok,
der ikke kan afgøre noget, er værre end ingen målestok.
