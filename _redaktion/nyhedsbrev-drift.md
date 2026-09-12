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
