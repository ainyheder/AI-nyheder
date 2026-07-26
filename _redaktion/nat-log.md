# Nat-log

Nyeste øverst. Skrevet af natsessionen efter hvert færdigt punkt.

---

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
