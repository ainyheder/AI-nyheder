# Nyhedsbrev — drift

Workflowet `.github/workflows/nyhedsbrev.yml` bliver aktivt efter push til main.
Det kontrollerer det offentlige https://metatrends.substack.com/feed én gang
dagligt kl. 18.13 UTC (20.13 dansk sommertid / 19.13 dansk vintertid).
Push udløser ikke ekstra kontroller; en manuel kørsel kan startes i Actions.
GitHub kan forsinke planlagte jobs, og et RSS-opslag kan komme efter
originalens mail. Vi har ikke adgang til Diamandis’ afsendelsessystem.

## Forløb

1. Læs hele `content:encoded` fra RSS. Brug ikke resumé som erstatning.
2. Spring originaler fra før `nye_fra` i `opsaetning/nyhedsbrev.json` over.
   Det eksisterende prøvebrev fra 10. september genudsendes derfor ikke.
3. Redaktøren skriver med `opsaetning/nyhedsbrev-prompt.md`.
4. En separat AI-kørsel læser original og udkast med
   `opsaetning/nyhedsbrev-kontrol-prompt.md`. Afviste breve får højst tre
   skriveforsøg fordelt på kørsler. Ufuldstændige kilder venter på fuld tekst.
5. Kun godkendt indhold oprettes som Buttondown-kladde og overdrages til
   udsendelse til de aktive abonnenter. Buttondown styrer tilmeldinger,
   afmeldinger og den faktiske levering.

Modellen er som standard `deepseek-flash`. Begge trin kan få egen model og
instruks i Indstillinger → Modeller & instrukser; valgene gemmes i
`_redaktion/hjerner.json`. Den eksisterende provider-reserve fra crawleren
bruges ved modelfejl, og fallback skrives i Actions-loggen. AI-kontrollen er
en redaktionel kontrol, ikke et bevis for fejlfrihed eller en juridisk godkendelse.

GitHub-secrets: `DEEPSEEK_API_KEY` (evt. `GEMINI_API_KEY` som reserve) og
`BUTTONDOWN_API_KEY`. Ingen nøgler skal i HTML eller git. Crawlerens workflow
har ikke længere Buttondown-nøglen og udsender ikke fredagsbrevet. Ugesiden
opdateres fortsat med de syv afsluttede dage.

## Historik og fejl

Workflowet vedligeholder `state.json` på den separate gren
`codex/nyhedsbrev-status`. Den deler ikke genererede filer med main og kører
derfor uden at blokere crawleren eller skabe de tidligere merge-konflikter.
Der gemmes kildemetadata, godkendt dansk udkast, kontrolresultat og Buttondown-id;
ingen abonnentliste, API-nøgler eller originalbrevets fulde tekst.
Hvis repoet er offentligt, er grenen også offentlig. Den er ikke en webside.

Hvert checkpoint pushes før et kald, som kan skabe eller sende en mail.
Oprettelse og udsendelse har hver en stabil `X-Idempotency-Key`. En tidsudløbet
eller afbrudt udsendelse gentages aldrig automatisk: næste kørsel spørger først
Buttondown om den kendte mail. Status `overdraget` betyder, at Buttondown har
overtaget mailen, ikke at alle modtagere har fået den. Levering ses i Buttondown.

- `baseline`: gammel original, sendes ikke.
- `venter`: mangler fuld kilde eller et godkendt udkast; `fejl` og `kontrol`
  forklarer eventuelle afvisninger. Efter tre forsøg kræves rettelse og manuel
  nulstilling af `forsog`, hvorefter en ny kørsel kan forsøge igen.
- `klar` / `kladde`: godkendt brev før afsendelse.
- `opretter`: et afbrudt POST kan have oprettet en kladde. Find den i Buttondown
  via titel/kildelink; læg dens `email_id` i posten og sæt `status` til `kladde`.
  Hvis ingen kladde blev oprettet, kan en verificeret manuel rettelse sætte `klar`.
- `sender` / `afventer`: undersøg den gemte `email_id` i Buttondown. Sæt ikke
  tilbage til `klar`. Hvis den er sendt eller står i kø, registrér `overdraget`.
  Kun hvis det er bekræftet, at intet er sendt eller i kø, kan den eksisterende
  kladde sættes til `kladde` for et nyt forsøg.
- `overdraget` / `sendt`: originalen bliver ikke behandlet igen, heller ikke hvis
  RSS-teksten ændres. Slet ikke historikken eller statusgrenen for at fejlrette.

En fejlet Actions-kørsel viser, at et brev er tilbageholdt. Tilpas GitHubs
Actions-notifikationer på din konto, hvis du vil have mail om driftsfejl.
Der udsendes aldrig et kort nødresumé i stedet for et afvist brev.

## Pause og kontrol

Deaktivér workflowet i GitHub Actions for at pause, eller sæt `aktiv: false`
i `opsaetning/nyhedsbrev.json` og push. Lad `nye_fra` blive stående; flytning
bagud kan gøre historiske originaler til kandidater ved en ny installation.

`python3 nyhedsbrev.py --check` læser kun RSS og viser aktuelle originaler.
Kontrollen virker også, når udsendelsen er pauset. Den kontrollerer, at seneste
original har tekst og forventet forfatter; ingen AI-kald eller mails startes.
I Actions → Run workflow vælges **Kontrollér KUN det levende feed** for samme
kontrol på GitHubs server. Den har forrang over Gmail-test, hvis begge vælges.
`python3 _redaktion/proeve-nyhedsbrev.py` tester forløbet med falske AI- og
mailtjenester. Ingen af kommandoerne sender mails eller bruger betalt AI.
Layoutet ligger i `opsaetning/nyhedsbrev-design.css` og `render()` i
`nyhedsbrev.py`. Buttondowns egen footer er eneste afmeldingsmulighed.

## Layoutkontrol 12. september 2026

Den aktuelle usendte prøve (v4) og generatoren bruger fuld tilgængelig bredde,
smalle sidemargener og ingen egen yderramme eller navne-/datolinje. Allerede
sendte prøver er historik og ændres ikke.

Buttondowns konto viser, at Custom CSS kræver Basic eller højere. CSS-regler,
der ændrer selve tjenestens mailskabelon, er derfor ikke bekræftet aktive på
kontoen. Buttondowns egen ramme kan stadig begrænse den leverede mails bredde.
Et forsøg med Classic-skabelonen blev ikke gemt: browserfanen blev lukket under
kontrollen. Ingen opgradering er købt. Deres logo nederst (Powered by Buttondown)
er tjenestens branding; fuld fjernelse kræver ifølge dokumentationen Professional.

Senere samme dag: Prøve 5 blev indsat og sendt via Buttondowns almindelige
HTML/Markdown-editor. Den faktiske mailforhåndsvisning viste yderramme 0px og
max-width none samt ét afmeldingslink. Det virker derfor i denne forhåndsvisning
uden ændring af kontoens betalte Custom CSS-indstilling. Den modtagne mail er
stadig den endelige kontrol i Outlook. Testen blev kun sendt til Torben, og
abonnentprofilen bekræftede Received. Se prøve 5's statusfil for mail-id.

## Ny visuel skabelon og faktisk status

Prøve 6 er modtaget i mail og gennemgået via Torbens PDF. Den viste den mørke
baggrund og én afmelding, men lange ens tekstblokke og Buttondowns eget logo.
Prøve 7 er en lokal layoutprøve med limefarvet titel, to talfelter, en fremhævet
pointe og en kort liste. Den er ikke sendt og har ikke fået separat AI-kontrol.

Den fælles renderer og begge prompts understøtter nu almindelige Markdown-
tabeller med to kolonner, korte lister og egne pointer markeret med `> `.
De visuelle felter skal erstatte tekst, ikke gentage den. Tal og forbehold skal
stå samlet. Ren brødtekst fra eksisterende udkast kan stadig vises. Dobbelt-
escaped linjeskift afvises før rendering, så hele brevet ikke bliver én overskrift.
Layoutet bruger HTML-tabeller og inline-stile; medieregler tilpasser små skærme.
Det er browserkontrolleret; den nye version skal også vurderes i modtagerens mail.

Fuld automatisk drift er endnu ikke bekræftet: RSS-kilden gav HTTP 403 fra GitHub.
Gmail-testen kunne køres med fuld kilde angivet manuelt. Både DeepSeek-skriver og
kontrollant kørte, men tredje prøve blev afvist og krævede Codex-rettelser før den
manuelle testafsendelse. Layoutændringen retter ikke RSS-adgangen eller beviser,
at næste automatisk skrevne brev bliver godkendt.

## Fritlagte illustrationer

`opsaetning/nyhedsbrev.json` har `billeder.aktiv` og `billeder.maks_pr_brev`
(0–2). Skriveren foreslår højst to motiver i `illustrationer`; kontrollanten
vurderer relevans og misvisende billedidéer sammen med teksten. Billederne
genereres først efter tekstens godkendelse. Kontrollanten ser motivplanen,
ikke de færdige billeder. Maskekontrollen er teknisk, ikke en semantisk kontrol.

Det nye trin `illustrerer` gemmes før billedarbejdet. Systemet bruger
Cloudflares `@cf/black-forest-labs/flux-2-klein-4b`, derefter eksisterende
`birefnet-general`. Den fælles motivstil ligger i
`opsaetning/nyhedsbrev-billedprompt.md`. Resultatet bliver en RGBA-PNG på højst
560×420 pixels. Originaler med baggrund bruges aldrig som fallback i mailen.
Fejlede illustrationer udelades; det godkendte brev kan stadig sendes.

Buttondowns dokumenterede `POST /v1/images` hoster PNG-filen, så mailen får
en offentlig HTTPS-adresse og ikke afhænger af en lokal fil eller en senere
publicering af hjemmesiden. API: https://docs.buttondown.com/api-images-create
Nyhedsbrevets workflow får nu de samme Cloudflare-secrets som crawleren samt
billedbiblioteket og modelcache. Det kræver ingen nye nøgler i HTML.

Før hvert billedkald gemmes et checkpoint. Klar-billeder genbruges; et afbrudt
eller fejlet motiv genereres ikke igen automatisk. Budgettet nulstilles ikke
ved ændringer i prompt eller stil. Et afbrudt upload kan efterlade en ubrugt
fil hos Buttondown, men udløser ikke automatisk et nyt billedkøb.

Prøve 8 demonstrerer to gennemsigtige billeder ved intro og planetafsnit.
De er genereret med Codex' image_gen-værktøj til lokal designkontrol, fordi
Cloudflare-nøglerne kun findes på GitHub. Originale prompts og billedfiler
ligger i `nyhedsbrev-proever/illustrationer/`. Prøven er ikke sendt.
Den nye FLUX → BiRefNet → Buttondown-kæde skal verificeres i en rigtig
GitHub-test efter push. RSS-problemet beskrevet ovenfor er ikke ændret.

## Feed-hentning: undersøgelse og ny transport

GitHub-kørsel 34690746848 den 12. september bekræftede endnu en HTTP 403 fra
den gamle urllib-hentning. Der blev ikke startet AI eller sendt en mail.
Det officielle feed kunne samtidig hentes lokalt: 20 breve, seneste fra
10. september med 1.790 ord. Årsagen til forskellen er endnu ikke fastslået.

`_redaktion/nyhedsbrev_feed.py` bruger nu curl, som forhandler HTTP/2 og
komprimering. Samme offentlige feed og tydelige AI-nyheder-identifikation
bevares. Op til to genforsøg gælder kun curls midlertidige fejl (fx timeout,
429 og 503), med tidsgrænse; 401/403 gentages ikke som en endeløs løkke.
En eventuel Cloudflare-browserkontrol angives i fejlen. HTML-fejlsider,
omdirigeringer og ufuldstændige downloads behandles aldrig som brevtekst.
Ingen login-cookie eller manuel kildetekst bruges.

Gmail-testen og den daglige udsendelse bruger den samme fetch_feed-funktion.
Det tidligere test_source_json-input er fjernet, så en grøn test ikke kan
skjule en defekt feed-hentning. `--check` viser HTTP-status, antal breve,
seneste titler/datoer og antal ord; originaltekster og cookies logges ikke.

Kørsel 34691400598 på GitHub bekræftede HTTP 403 med `cf-mitigated: challenge`
også med curl/HTTP2. Den direkte adgang er derfor fortsat blokeret fra runneren.

### Automatisk RSS-læser som reserve

Når den direkte transport afvises eller er midlertidigt utilgængelig, bruges
RSS2JSONs dokumenterede læse-API med præcis den samme Metatrends-feedadresse.
Det kræver ikke en API-nøgle. Standardresponsen indeholder de ti nyeste breve.
Den nye transport deler ikke credentials med tjenesten; kun den offentlige
feedadresse. RSS2JSON er en ekstra ekstern afhængighed, og deres cache kan
forsinke opdagelsen. Tjenesten har i den aktuelle respons cachetid på 30 min.;
det er ikke en garanti for deres interne opdateringsinterval.

Før integrationen blev alle ti brevtekster sammenlignet med RSS-originalen:
de var identiske. Forfattere, links og datoer matchede også. Én ældre titel
havde fået fjernet et afsluttende mellemrum; selve teksten var uændret.

`reader_items` afviser forkert feed, manglende `content`, ukendte kildelinks,
dubletter og ukendte datoformater. `description` bruges aldrig som erstatning.
Originalens URL og hash-id bevares, så skift mellem direkte RSS og læseren ikke
kan udløse en dobbelt udsendelse. Redaktøren og kontrollanten får fuld tekst;
de eksisterende krav til forfatter, længde og kvalitet gælder stadig.
Hvis begge læseveje fejler, stoppes udsendelsen tydeligt.

RSS-læseren er testet lokalt med det levende feed. **Den samlede reservevej
fra GitHub mangler stadig bekræftelse efter push.** Start en ny kørsel med kun
check_feed valgt. Loggen skal vise RSS-læser HTTP 200, verificeret Metatrends-
feed og fuld seneste original, før adgangen kaldes løst.

RSS-læserens API: https://rss2json.com/docs

Officiel RSS-adresse: https://support.substack.com/hc/en-us/articles/360038239391-Is-there-an-RSS-feed-for-my-publication
Curls genforsøg: https://curl.se/docs/manpage.html#--retry
