Aktuel indstilling fra 14. september 2026: Alle tekstopgaver bruger `deepseek-flash` med `reasoning_effort: high`. Historiske kørsler nedenfor kan omtale max.

# Nyhedsbrev — drift

## Aktuel teststatus — tokenloft, 14. september 2026

Den seneste Gmail-prøve bestod fritlægningskontrollen og gemte BiRefNet-cachen.
Feedet blev hentet via RSS2JSON. Skriveren brugte derefter alle 32.768 tokens
på tænkning uden synligt svar i tre forsøg, selv med Flash/high.

Nyhedsbrevets skriver og kvalitetskontrol har nu begge et loft på **100.000
tokens pr. kald**, inklusive tænkning. Det gælder både Gmail-test og daglig
drift. DeepSeek Flash/high og forsøgsgrænsen på tre redaktionsrunder er bevaret.
En ny GitHub-test efter push skal stadig bekræfte et færdigt brev og afsendelse.

## Tidligere fejl — fritlægning, 14. september 2026

[Kørsel 34815469159](https://github.com/ainyheder/AI-nyheder/actions/runs/34815469159)
stoppede før AI og mail: BiRefNet-trinnet sluttede efter 61 sekunder med
`model / ProcesAfbrudt / returkode 1`. Loggen skelnede ikke mellem download
og ONNX-indlæsning, så den præcise procesfejl er ikke fastslået.

Nyhedsbrevets cache blev kun gemt ved succes for hele jobbet. Der fandtes
ingen newsletter-cache, selv om crawlerens samme model allerede lå i cache.
Begge newsletter-jobs genbruger nu også crawlerens cache og gemmer modellen
lige efter en bestået fritlægningsprøve, før betalte AI-kald og mail.

Modelhentningen kontrollerer checksum, reparerer defekte modeldownloads og
har højst to genforsøg. Kontrollen har 600 sekunder til en eventuel kold
download på cirka 973 MB; de efterfølgende billeder beholder 180-sekundersloftet.
Loggen skelner mellem `modelkontrol`, `modeldownload` og `modelindlaesning`.
Trin, fejltype og eventuel HTTP-status gemmes separat fra bibliotekernes
progress-output. Installerede biblioteksversioner vises også, uden API-nøgler
eller udbydernes request-data.

166 lokale kontroller bestod: 16 for fritlægning/cache/fejl, 14 for feed,
42 for nyhedsbrev, 11 for Gmail og 83 for modelvalg. Modelcachetestene bruger
små testfiler og simulerede netværksfejl; de er ikke en fuld BiRefNet-kørsel.

En ny Gmail-test på GitHub skal stadig bekræfte hele forløbet efter push.
Start **Run workflow** med Gmail-test valgt; brug ikke **Re-run jobs**,
da testscriptet kræver en ny kørsel for at undgå dobbelt afsendelse.

## Tidligere modtaget prøve — prøve 12

[Kørsel 34737586357](https://github.com/ainyheder/AI-nyheder/actions/runs/34737586357)
på `d5d90db` hentede “What's Your Moonshot?” fra 12. september via RSS2JSON.
Skriver og kontrol brugte begge `deepseek-flash` med max reasoning. Skriveren
afleverede første udkast med 31.286 outputtokens; kontrollen godkendte det med
51.021. Begge FLUX-illustrationer blev genereret, fritlagt med BiRefNet og
uploadet til Buttondown.

Testen til `soemandtorben@gmail.com` blev accepteret 13. september kl. 06.29
dansk tid: Buttondowns API-historik viser HTTP 200 på
`/v1/emails/em_2rxq0jae2w9kc9rjrx9tatnb54/send-draft`
(request `api_req_41fyaptc6w9pva8y4w3xxmnqha`). Emne:
“AI forstærker alt, du peger den mod – også støj”. Torben har bekræftet
modtagelsen og delt en PDF af brevet. Ingen abonnentudsendelse blev startet af
denne prøve.

GitHub-kørslen står fejlet, fordi klienten forsøgte at læse den tomme
HTTP 200-kvittering som JSON efter afsendelsen. Klienten håndterer nu tomme
200/204-svar specifikt fra test-endpointet. Andre svar kræver stadig JSON;
HTTP-fejl accepteres eller genprøves ikke. 37 nyhedsbrevstests og 11 Gmail-tests
bestod lokalt efter rettelsen. Prøve 12 må ikke genudsendes for at gøre den grøn.

Den menneskelige efterkontrol finder stadig indholdsfejl trods AI-godkendelsen:
introen gør oplæsning af Altmans ord til hans deltagelse i podcasten; brevet
bruger meget plads på arrangementsprogram, navne og billetter; afslutningen
placerer virksomhedernes levedygtighed efter arrangementet uden kildebelæg.
Sproget har også engelske rester og gentagne henvisninger til “originalen”.
Dette er en teknisk gennemført prøve, ikke dokumentation for færdig
redaktionel kvalitet. Det allerede afsendte prøvebrev er bevaret uændret.

## Rettelser efter den modtagne prøve — 14. september 2026

Den delte PDF viste lange tekstflader og to billedfelter uden indlæste billeder.
Ved efterfølgende kontrol af samme mail i Outlook blev både telefonen og
filmklapperen vist. Det bekræfter, at billederne kan indlæses i den modtagne
mail; den præcise årsag til de manglende billeder i PDF'en er ikke fastslået.
Ingen indstillinger for automatisk billedhentning eller sikkerhed er ændret.
Torbens vurdering er, at selve motiverne er for generiske.

Skrive- og kontrolprompten kræver nu en forståelig fortælling med konkrete
eksempler, korte afsnit og indbydende overskrifter. Nødvendige fagord forklares;
gentagne henvisninger til originalen, salgsprogram og navnelister skal ikke
fylde brevet. Lokale forbehold og præcist ophav bevares ved usikre påstande.
Lange afsnit og teksttunge tabeller afvises også af formatkontrollen, så et
AI-godkendt brev stadig skal have en brugbar læserytme.

Skabelonen viser normal brødtekstvægt, afsnitsfelter, korte fremhævninger og
større fritlagte illustrationer i overskrifternes egne celler. Billeder presser
dermed ikke brødteksten ind i en smal spalte. Ved logoet står en automatisk
beregnet læsetid: cirka 200 synlige ord pr. minut, rundet op. Linkadresser tæller
ikke med. Visningen er kontrolleret ved 320, 390 og 960 pixels uden vandret
overløb; den faktiske næste mail skal stadig kontrolleres i mailprogrammet.

Der planlægges normalt tre billeder fordelt over intro, midte og sidste del,
og både billedbudget og rendering understøtter tre. Billedprompten sigter nu
mod kompakte tredimensionelle scener med en tydelig forbindelse til historien,
dybde, bred silhuet og farvekontrast. En løs telefon eller filmklapper opfylder
ikke længere motivinstruksen alene. FLUX 2 Klein og BiRefNet er bevaret.
Kontrollanten vurderer fortsat kun motivplanen, ikke de genererede billeder.

42 nyhedsbrevstests og 11 Gmail-tests består lokalt, inklusive at tre billeder
genereres én gang og alle tre kommer med i HTML'en. Testene bruger falske
AI- og mailtjenester; de dokumenterer ikke den næste AI-teksts billedkvalitet.

`nyhedsbrev-proever/design-2026-09-13.html` er en manuelt redigeret, usendt
designprøve med to genbrugte billeder fra prøve 12. Den viser tekstretningen,
læsetiden og layoutet; den er ikke output fra de nye prompts. En ny manuel
Gmail-test skal efter push hente det levende feed, skrive med Flash/high,
generere nye motiver og sende kun til Torbens Gmail.

## Tidligere test — prøve 10

[Kørsel 34704214872](https://github.com/ainyheder/AI-nyheder/actions/runs/34704214872)
på `7f17aa9` bestod de tekniske tests og den rigtige BiRefNet-prøve på GitHub.
RSS2JSON leverede hele brevet “AI Is About to Break Settled Science” fra
10. september. Skriveren brugte 20.618 outputtokens, heraf 17.058 til tænkning,
og afleverede et JSON-udkast. Kontrollen brugte alle 32.768 på tænkning og
stoppede med `finish_reason=length` og nul synlige tegn. Det var en teknisk
fejl, ikke en redaktionel afvisning. Forsøget blev annulleret under den
unødvendige genskrivning. Ingen illustrationer eller testmail blev sendt.

Kontrollens loft er nu 65.536; Flash og max reasoning er bevaret. Et teknisk
kontrolsvigt genprøver samme validerede udkast. En rigtig afvisning sender
fortsat teksten og kritikken til skriveren. Højst tre redaktionsrunder i alt,
og udkast, næste trin og forbrugt forsøgsbudget gemmes før det lange kontrolkald.
37 nyhedsbrevstests, 8 Gmail-tests og 83 modelvalgskontroller bestod lokalt.
Prøve 12 ovenfor har siden afprøvet det større budget, billeder og testafsendelse.

Feedets aktualitet har en begrænsning: Det direkte feed viste allerede
“What’s Your Moonshot?” fra 12. september kl. 15.01 UTC, mens RSS2JSON stadig
viste brevet fra den 10. Direkte RSS blev afvist med 403 på GitHub. Reservens
forsinkelse er observeret; dens opdateringsinterval er ikke bekræftet. En
vellykket hentning beviser derfor ikke, at allerførste nye brev er tilgængeligt.

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
   redaktionsrunder i samme kørsel med tidligere udkast og konkret kritik.
   Ved et manglende eller ødelagt kontrolsvar genprøves kun kontrollen af
   det gemte, formatvaliderede udkast. En indholdsmæssig afvisning giver
   skriveren teksten og kritikken tilbage. Teksten gemmes før kontrolkaldet.
   Forsøgstælleren gemmes løbende og nulstilles ikke ved genoptagelse.
   Ufuldstændige kilder venter på fuld tekst.
5. Kun godkendt indhold oprettes som Buttondown-kladde og overdrages til
   udsendelse til de aktive abonnenter. Buttondown styrer tilmeldinger,
   afmeldinger og den faktiske levering.

Modellen er som standard `deepseek-flash`. Begge trin kan få egen model og
instruks i Indstillinger → Modeller & instrukser; valgene gemmes i
`_redaktion/hjerner.json`. Fejl i nyhedsbrevets DeepSeek-kald stopper det
pågældende trin uden et skjult ekstra kald til en anden model. AI-kontrollen er
en redaktionel kontrol, ikke et bevis for fejlfrihed eller en juridisk godkendelse.

GitHub-secrets: `DEEPSEEK_API_KEY` (evt. `GEMINI_API_KEY` ved et aktivt modelvalg) og
`BUTTONDOWN_API_KEY`. Ingen nøgler skal i HTML eller git. Crawlerens workflow
har ikke længere Buttondown-nøglen og udsender ikke fredagsbrevet. Ugesiden
opdateres fortsat med de syv afsluttede dage.

## Historik og fejl

Workflowet vedligeholder `state.json` på den separate gren
`codex/nyhedsbrev-status`. Den deler ikke genererede filer med main og kører
derfor uden at blokere crawleren eller skabe de tidligere merge-konflikter.
Der gemmes kildemetadata, seneste afviste eller godkendte danske udkast,
kontrolresultat og Buttondown-id;
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
(0–3, normalt 3). Skriveren foreslår højst tre motiver i `illustrationer`; kontrollanten
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

**Reservevejen er bekræftet fra GitHub den 12. september 2026.** Kørsel
[34692494507](https://github.com/ainyheder/AI-nyheder/actions/runs/34692494507)
på commit `bc3a416` bestod. Loggen viste direkte RSS HTTP 403 med
Cloudflare-browserkontrol, derefter RSS2JSON HTTP 200 og ti Metatrends-breve.
Seneste original var “AI Is About to Break Settled Science”, dateret
10. september kl. 16.54.27 UTC, med 1.790 ord og korrekt forfatter.

Dette bekræfter den automatiske kildehentning. Ingen manuel tekst blev
indsat. Både Gmail-test og abonnentudsendelse var sprunget over; der blev
ikke sendt mail eller kaldt AI. Den samlede tekst-, billed- og mailkæde
skal stadig kontrolleres i en ny Gmail-test. Den daglige plan bruger
samme fetch_feed-funktion og den allerede publicerede rettelse.

## Samlet Gmail-test efter feedrettelsen

Kørsel [34693272666](https://github.com/ainyheder/AI-nyheder/actions/runs/34693272666)
på commit `2e7256b` hentede den 10. september-original automatisk via RSS-læseren.
Begge AI-trin kørte med `deepseek-flash`, men alle tre udkast blev afvist.
Ingen billeder blev genereret, og ingen Buttondown-kladde eller mail blev oprettet.

De tre gemte udkast og kontroller viste både reelle tekstproblemer og forkert
kontrolkritik. Udkastene gentog deres konklusioner og ændrede blandt andet
Rubin-observatoriets hyppighed fra hver få nætter til hver nat. Kontrollanten
påstod også fejlagtigt, at udkastene fulgte originalens eksempelrækkefølge,
og efterlyste dansk aktualitet, som materialet ikke indeholdt.

Skriveprompten er nu forkortet og kræver en konkret disposition før teksten,
forskelligt stof i afsnittene og præcise tal, tidsrum og hyppigheder.
Kontrolprompten kræver belæg for hver væsentlig kritik, adskiller fakta fra
stil og efterprøver påstande om kildens struktur. Den accepterer tydeligt
markerede, forestillede emneillustrationer uden at kalde dem videnskabelige fund.
Godkendelseskravene og grænsen på tre forsøg er bevaret.

Gmail-test og daglig drift bruger nu samme `editorial_attempt()` til skrivning,
formatkontrol og separat AI-kontrol. Formatfejl skjuler ikke indholdskritikken.
Daglig drift gemmer det afviste udkast og retter i samme kørsel; tidligere ventede
den til næste dag og gav kun fejlteksten til skriveren. Afbrudte forsøg tæller
fortsat med i budgettet, og udsendelsens checkpoints er uændrede.

De nye prompts skal efter push afprøves i en ny Gmail-test. Lokale tests med
falske AI-svar kontrollerer rettelsesforløb og udsendelsesgrænser, ikke kvaliteten
af næste rigtige brev. FLUX → BiRefNet → Buttondown er stadig ikke bekræftet.

### Gmail-prøve 8 og de næste rettelser

[Kørsel 34695026486](https://github.com/ainyheder/AI-nyheder/actions/runs/34695026486)
på `8c554ea` hentede igen originalen automatisk. AI-kontrollen godkendte tredje
udkast. En efterfølgende gennemlæsning fandt dog fortsat gentagelser og flere
passager tæt på originalens formuleringer. Godkendelsen beviser altså ikke,
at tekstkvaliteten er tilstrækkelig.

Torben ønsker fortsat Flash og har valgt maksimal tænkning. Nyhedsbrevets
DeepSeek-kald får `thinking: enabled`, `reasoning_effort: max` med samme
valgte model. Niveauet står i `opsaetning/nyhedsbrev.json` og logges for begge
roller. Loftet er 32.768 outputtokens til skriveren og 65.536 til kontrollen,
inklusive tænkning. Tænkning afregnes som output; rå reasoning_content gemmes
eller vises ikke. Alle crawlerens DeepSeek-kald bruger nu også max (se nedenfor).
AI-kaldene tillader op til 600 sekunders netværksventetid; workflowet har
75 minutter til højst tre skrive-/kontrolrunder plus billeder og udsendelse.
Dokumentation: https://api-docs.deepseek.com/guides/thinking_mode/

Prøve 8 oprettede Buttondown-kladde `em_5p5vbxhqxa8d6sm2e0h23h2zsd`, men
stoppede før send-draft. Der er ikke sendt en testmail. Buttondowns viste
HTML var indholdsmæssigt identisk med den indsendte: forskellen var automatisk
indsat tbody, normaliserede mellemrum i CSS og afkodede tegnkoder. Den nye
sammenligning læser HTML-tags, attributter og tekst frem for at sammenligne
rå bytes. Den tillader disse serialiseringsforskelle og editorens dokumenterede
markør, men stopper fortsat ved ændret emne, status, tekst, links, billeder
eller stil. Ved afvigelse gemmer Gmail-testen nu også kladden i artefaktet.
Formatmarkør: https://docs.buttondown.com/api-emails-create

Prøvens ene illustration blev udeladt efter CalledProcessError i fritlægningen.
Den gamle kode kasserede stdout/stderr, så den præcise årsag er ukendt.
FLUX-kaldet nåede at returnere et billede; BiRefNet og billedhosting er ikke
bekræftet fra den kørsel. Fritlægningens proces rapporterer nu trin, returkode
og fejltype uden rå udbydersvar. Gmail-testen prøver desuden hele BiRefNet-
konverteringen på en teknisk prøvefigur før betalte AI- og billedkald.
Denne kontrol er bestået lokalt med den samme rembg-version, men skal stadig
bestå på GitHub. Den tekniske figur indsættes aldrig i nyhedsbrevet.

### Gmail-prøve 9: max reasoning og API-svar

[Kørsel 34698190313](https://github.com/ainyheder/AI-nyheder/actions/runs/34698190313)
på `dfcc308` tog 13m 14s i testjobbet. De tekniske tests og den fulde
BiRefNet-prøve bestod, og seneste original blev hentet fra det levende feed.
Begge redaktionelle roller blev kaldt med `deepseek-flash` og `max`.

Forsøg 1 og 2 havde kun JSON-læsefejl. Loggen viste desuden et IncompleteRead
og et ekstra, automatisk kald til den daglige model. Forsøg 3 gav et udkast,
men kontrollens svar kunne ikke parses. Udkastet placerede et allerede
markeret fremtidsbud i feltet uafklaret. Det havde også gentaget historisk
stof og en tabel uden Markdown-separator. Det blev ikke godkendt, og der
blev hverken købt illustrationer, oprettet Buttondown-kladde eller sendt mail.

API-svarenes slutårsag og tokenforbrug blev ikke gemt i denne kørsel.
Derfor ved vi ikke, om JSON-fejlene skyldtes tomt indhold, tokenloft eller
andet. De beviser hverken god eller dårlig kvalitet af max reasoning.

Næste rettelse aktiverer DeepSeeks dokumenterede JSON-format for de
redaktionelle reasoning-kald. Den kræver normal afslutning, ikke-tomt indhold
og et JSON-objekt; selv gyldig JSON afvises ved finish_reason=length.
Kun slutårsag og numerisk token-/tegnstatistik logges, aldrig intern tænkning
eller rå udbyderfejl. Transportfejl udløser ikke længere en skjult ekstra
generation via daglig-model-fallback. De højst tre synlige forsøg gælder
fortsat. Loggen vises løbende med PYTHONUNBUFFERED.

Skriveprompten præciserer forskellen på markerede fremtidsbud og uløste
kildeproblemer samt kræver Markdown-tabellers separatorrække. Valideringen
af uafklaret og den separate kvalitetskontrol er uændret. Flash beholder max
og tokenloftet 32.768; ingen ny budgetforøgelse på baggrund af en ukendt fejl.

Lokalt bestod 32 nyhedsbrevstests, 6 Gmail-tests, 79 modelvalgskontroller samt
actionlint. Ny live-test kræver push af rettelserne. Testresultatet fra
GitHub er fortsat afvist; ingen prøve 9 er sendt til Gmail.

RSS-læserens API: https://rss2json.com/docs

Officiel RSS-adresse: https://support.substack.com/hc/en-us/articles/360038239391-Is-there-an-RSS-feed-for-my-publication
Curls genforsøg: https://curl.se/docs/manpage.html#--retry


### Fælles high reasoning og en aktuel forside

Alle tre DeepSeek-transportveje bruger `_redaktion/ai_indstillinger.py`:
`thinking: enabled`, `reasoning_effort: high`, mindst 32.768 tokens til
samlet tænkning/svar og 600 sekunders timeout. Det gælder også batchvurdering,
omskrivning, billedmotiver, ugens overblik og agentens research/slutkontrol.
Alle transportveje følger den fælles high-politik, også ved et gammelt max-argument.
Arrays og almindelig tekst er stadig tilladt i opgaver, som kræver dem.
Kun nyhedsbrevets eksplicitte objektkontrakt tvinger JSON-objekter.
Tool-samtalen viderefører reasoning_content til næste værktøjsrunde i
hukommelsen, som API'et kræver; feltet skrives aldrig i log eller historik.

Agentversion 2 forkaster tidligere planer med den gamle sortering. Op til
3 kildekontrollerede hovedhistorier vælges blandt de seneste 48 timer.
Resten vises nyeste først, også når en godkendt plan genbruges og nye artikler
kommer til. Anbefalinger bliver kontrolleret selv uden hovedhistorier og
kan ikke fastholde gamle artikler foran nye. Ved AI-fejl prioriterer reserven
også de seneste 48 timer; kun helt stille perioder bruger ældre hovedhistorier.

Crawlerens planlagte job kan nu bruge op til 120 minutter (manuelt 180).
Timerytmen er bevaret, men kørsler overlapper ikke. Max kan øge både
svartid og tokenforbrug; faktisk køretid og redaktionel kvalitet skal vurderes
på den første GitHub-kørsel efter push. Lokale kontrakttests bruger simulerede
API-svar og dokumenterer ikke modellens faktiske kvalitet.

### Billedmotiver og genkendelige selskaber

Artikelrollen `motiv` læser nu rubrik, resumé og den færdige artikeltekst
(op til 8.000 tegn). Den vælger scenens handling og den centrale aktør.
OpenAI, Anthropic/Claude, Google/Gemini, DeepSeek og Meta har beskrevne
kendetegn; en tilfældig omtale af et andet selskab skal ikke give et ekstra logo.
Motivet skal forklare nyheden samtidig med, at mærket identificerer aktøren.
De aktive artikelprompts ligger fortsat i `_redaktion/hjerner.json` og kan
redigeres i kommandocentralen. De indbyggede standarder i `crawler.py` er
opdateret tilsvarende. Nyhedsbrevets skrive-, kontrol- og billedprompts i
`opsaetning/` følger samme princip.

Begge billedforløb sender motivet før stilreglerne, i tråd med
[FLUX' anbefaling om at placere motiv og handling først](https://docs.bfl.ai/guides/prompting_guide_flux2).
Gemini beskrives med den firspidsede form og Googles fire farver efter
[Googles opdatering af G-ikonet og Gemini-mærket](https://blog.google/company-news/inside-google/company-announcements/gradient-g-logo-design/).

Artikelmotiver returneres med `nr`, så ændret svarrækkefølge ikke bytter dem
mellem artikler. Tvetydige numre bruges ikke. Et motiv uden et gemt billede
opdateres, når skriveinstruksen eller artikelteksten ændres. Eksisterende
billeder genbruges fortsat, og billedbudgetterne er bevaret. FLUX og BiRefNet
har samme opgaver som før; de lokale prøver køber eller sender intet.
Form og motivrelevans i de faktiske billeder skal vurderes ved næste
generering. Prompts alene garanterer ikke en pixelpræcis gengivelse af et logo.
