# Analyse · 2026-07-28 kl. 05:45 (hovedkørsel, chat med Torben)
**Læsere:** 261 besøg / 738 visninger på 7 dage (målt 22:47 UTC i går). Forsiden
246 besøg / 456 visninger. Udefra **uændret på tredje døgn**: 19 Facebook, 4
Google, 3 Buttondown — heller ikke efter at sitemappene blev indsendt 27.07. De
tre faste sider uden ét eneste besøg er stadig `prompt-arkiv.html`, `quiz.html`
og `vaerktoejer.html`. Fem artikelsider har 1–3 visninger, alle "herfra selv".
`laer.html` er den mest læste side efter forsiden med 88 visninger.
**Live:** ainyheder.com svarer 200 på 0,67 s. `articles.json` over nettet er
gyldig JSON med 145 artikler — **samme antal som disken**. Alle tre sitemaps og
`feed.xml` svarer 200. MEN: nettets fil er `opdateret` 2026-07-28T03:37, diskens
2026-07-27T22:45. **Den lokale mappe er bagud** — Actions har kørt og pushet.
Skrevet øverst i loggen.
**Målt:** 145 artikler, 8 vindere med `andre`, 10 slugte (mod 12/16 i går — flere
er rullet ud). 168 sider i `artikel/`, 41 i `video/`, 42 videoer i youtube.json.
85 artikler med billede, hvoraf **2 bærer et billede, der ikke er deres eget**.
**Set som læser:** forsiden tegner i jsdom uden en eneste JS-fejl; kort, dagens
overblik og læseren virker. Men **de 168 artikelsider har alle præcis fire
interne links** — to til forsiden, ét til `om.html`, ét til `laer.html`. Det er
de sider, Google netop er inviteret ind på.
**Sidste kørsels arbejde:** holder. Fortryd-mekanismen og `efterproev.py` er
begge committet af Torben, git status ren ved start.
**Efterprøvet:** «Kørekortet er gemt bag nyhederne» (25.07) — **holder**. 2 af 93
links på den tegnede forside fører til lære-indhold, begge til `laer.html`; 0 til
kørekortet; ordet "kørekort" står 0 steder. **Efterslæb: 27 modne punkter aldrig
efterprøvet** (grænsen er 10).
**Køen:** øverste punkts tal var døde, men fejlen var større end beskrevet og
vendt om: skaden ligger hos artikler UDEN `andre`, ikke med. To af de tre er de
vindere, hvis tabere blev frigivet i går, og git beviser lånet ned til
mikrosekundet. Punktet er klaret. Nyt punkt fra rækkevidderunden. Nummer ét er nu
"Tre faste sider fik nul besøg", som endelig har fået den måling, den bad om.
**Jeg gik i gang med:** frigivelsen, der kun rullede `andre` tilbage — det eneste
punkt i trin 1, og det eneste, der var i stykker for en læser lige nu.

---

# Analyse · 2026-07-27 kl. 20:20 (ekstra kørsel, chat-session med Torben)
**Læsere:** 257 besøg/727 visninger på 7 dage (målt 17:46 UTC). Forsiden 242
besøg/450 visninger. Udefra uændret: 19 Facebook, 4 Google, 3 Buttondown — de 17
nye besøg siden 13:47 er alle direkte. Fire artikelsider har nu 1–3 visninger
hver, men `sidehenvisere` siger "herfra selv" på dem alle: det er redaktionen,
der klikker. Faste sider uden besøg er faldet fra ni til tre.
**Live:** ainyheder.com svarer 200, articles.json over nettet er gyldig JSON og
har samme `opdateret` og samme antal som disken (138 = 138).
**Målt:** 138 artikler i articles.json, **12 vindere med `andre`, 16 slugte** —
mod 15 vindere og 46–47 slugte kl. 19:45. Faldet skyldes `_samme_sag`, den
deterministiske vagt køens øverste punkt beder om. **Den findes allerede** og
blev committet kl. 19:18 i `d95c041` (+230 linjer i `crawler.py`). Den commit
rørte ingen logfil, og intet logindlæg nævner den — arbejdet er lavet, men aldrig
skrevet ned, og punktet blev derfor aldrig lukket.
**Set som læser:** ikke gennemgået denne gang — tiden gik med at måle de 16
tilbageværende sammenlægninger.
**Sidste kørsels arbejde:** holder. Fravælg-knappen i kontrolpanelet (20:05) er
committet af Torben i `90b22bb`, git status ren.
**Køen:** øverste punkts tal er døde — "47 artikler er væk", "13 grupper",
"median 3,4 %" gælder ikke længere. Men punktet er ikke løst. Ny måling af de 16:
**ingen af de 16 tabere er i dagens liste**, og frigivelsen i trin 0 kræver, at
begge udgaver står i dagens liste med deres tekst. Frigivelsen kan altså i dag
fyre for præcis **0 af 16**. Elleve af de 16 har stadig en frossen side i
`artikel/`, hvor rubrik og resumé står i `og:title` og `og:description` — teksten
er der, den bliver bare aldrig læst. Holdt op mod vinderen med crawlerens egne
funktioner er **fire af de elleve** hverken samme sag efter `_samme_sag` eller
åbenlys dublet efter `_samme_historie`: «Er åben AI virkelig farligt?» under
«Nvidia og Mistral advarer…», «Eks-googlere bag AegisAI» under «Strømsvigt i
Washington…» (0 % fælles ord), «Claude taler nu ud…» under «Anthropic sender
billigere AI-model» og «Meta vælger dyster sang…» under «Biblioteker afholder
'Avoiding AI'-workshops» (0 % fælles ord).
**Jeg går i gang med:** at gøre en fejlsammenlægning mulig at fortryde —
`_slaa_sammen` gemmer taberens rubrik og resumé, og trin 0 må bruge den gemte
tekst eller den frosne side som bevis, når taberen ikke er i dagens feed.

---

# Analyse · 2026-07-27 kl. 19:45 (ekstra kørsel, chat-session med Torben)
**Læsere:** 240 besøg/690 visninger på 7 dage (målt 13:47). Forsiden 220 besøg;
udefra kun 19 Facebook, 4 Google, 3 Buttondown. Artikelsiderne optræder slet
ikke i sidelisten. Dagskurven falder: 70→60→30→10 besøg (24.–27.07).
**Live:** ainyheder.com svarer 200, articles.json gyldig og identisk med disken
(110 = 110). Alle tre sitemaps svarer 200.
**Målt:** 110 artikler i articles.json (15 vindere med `andre`, 46 slugte),
149 sider i artikel/, 41 i video/. 0 canonical-kæder. Sitemaps på disk:
30 + 91 + 41 URL'er.
**Set som læser:** ikke gennemgået denne gang — kørslen var kort og brugte
tiden på GSC (se nedenfor).
**Sidste kørsels arbejde:** holder. `_bryd_canonical_kaeder` = 0 kæder på disk,
git status ren (alt er hentet og pushet).
**Køen:** øverste punkts formodning er nu MÅLT i selve Search Console:
sitemap.xml VAR indsendt (22.07, Succes, 30 sider), men sitemap-artikler.xml og
sitemap-videoer.xml var ALDRIG indsendt — Google fik aldrig besked om de 132
artikel-/videosider. Begge er nu indsendt (se loggen). Punktet står stadig
øverst: effekten skal ses i læsertallene, og GSC's "Sider"-rapport skal tjekkes
om nogle dage.
**Jeg går i gang med:** stopper her — ekstra kørsel i chat med begrænset tid.
Næste punkt for næste kørsel: dubletfangeren (uændret næst-øverst).
