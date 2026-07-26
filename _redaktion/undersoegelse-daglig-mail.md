# Kan Dagens overblik sendes som daglig mail?

Undersøgelse fra natsessionen 25. juli 2026 til køpunktet *„Dagens overblik
skrives hver dag og bruges ét sted“*. Intet er ændret i koden — det her er
grundlaget for at beslutte.

**Kort svar:** Ja, teknisk. Buttondowns gratis plan tillader det udtrykkeligt,
og det meste af koden findes allerede. Men der er en spærre, som ikke er
teknisk, og som skal løses først: **de nuværende abonnenter har sagt ja til en
ugentlig mail, ikke en daglig.**

---

## 1. Hvad Buttondown tillader gratis

Hentet fra deres egne sider i nat:

| Spørgsmål | Svar | Kilde |
|---|---|---|
| Koster daglig afsendelse ekstra? | **Nej.** „All of these prices assume that you're sending at most one email a day to your entire subscriber base.“ Én daglig mail er præcis det, prisen forudsætter. | prisside, FAQ |
| Hvor mange abonnenter gratis? | **100.** Derefter stiger prisen med listens størrelse. | prisside |
| Kan afsendelse planlægges til et klokkeslæt? | **Ja, og det er gratis.** Dokumentationssiden om scheduling siger direkte „Available on the Free plan.“ | scheduling-doc |
| Pris pr. mail? | **Ingen** på nogen plan. | prisside |

Så den gratis plan er ikke problemet. Til gengæld koster de add-ons, man ville
få brug for, hvis man vil lade folk *vælge* mellem dagligt og ugentligt:
**tagging & segmentering +$9/md**, eller **flere nyhedsbreve +$29/md**.
Det er kernen i beslutningen længere nede.

## 2. Hvad der allerede virker

Overraskende meget. Der skal ikke bygges en integration — den er der.

- `_send_nyhedsbrev()` i `crawler.py` (linje 1612) sender allerede til
  `api.buttondown.com/v1/emails` med `status: "about_to_send"`.
- `BUTTONDOWN_API_KEY` ligger i GitHub Actions secrets og er allerede sat i
  `crawl.yml`. Ingen nye hemmeligheder skal oprettes.
- Tilmeldingsformularen står på forsiden, på `uge.html` og i crawlerens
  ugeskabelon, alle mod samme Buttondown-liste.
- `lav_dagens_brief()` (linje 2337) skriver `data/brief.json` én gang pr. dansk
  døgn og springer over, hvis dagens brief allerede findes. Der ligger altså
  hver dag fem færdige punkter med links.

Der mangler i praksis kun én funktion, der bygger fem punkter om til en mail —
og et svar på, hvornår den skal sendes.

## 3. Timingen er det egentlige tekniske problem

Det er her, en naiv løsning går galt.

Crawleren kører efter to cron-linjer: `37 4-21 * * *` og `37 0 * * *`. Den
sidste er 00:37 UTC — **02:37 dansk om sommeren, 01:37 om vinteren.** Og
`lav_dagens_brief` bruger dansk dato til at afgøre, om dagens brief er skrevet.

Konsekvensen: dagens brief bliver skrevet i kørslen **kl. 02:37 om natten**.
Sender man mailen i samme øjeblik, som briefet skrives, lander den hos
læserne midt om natten og ligger nederst i indbakken kl. 7.

Det løses ikke ved at flytte cron — briefet *skal* skrives tidligt, så forsiden
er klar om morgenen. Det løses med Buttondowns `scheduled`-status:

```python
{
  "subject": "…",
  "body": "…",
  "status": "scheduled",
  "publish_date": "2026-07-26T05:00:00Z",   # 07:00 dansk sommertid
}
```

Klokkeslættet skal regnes ud med `zoneinfo`, ikke hardkodes: 07:00 dansk er
05:00 UTC om sommeren og 06:00 UTC om vinteren. Hardkodes det, rykker mailen
sig en time to gange om året.

## 4. Dublet-faren

`lav_dagens_brief` returnerer tidligt, hvis `brief.json` allerede har dagens
dato — så mailen ville normalt kun blive sendt én gang. Men den sikkerhed
hviler på, at `brief.json` **bliver committet**. Fejler commit- eller
push-trinnet i workflow'et én gang, skriver næste kørsel briefet igen, og så
sendes mailen to gange samme dag. Crawleren kører 19 gange i døgnet, så der er
19 chancer for det.

Den rettelse er lille: skriv en markør ind i filen, når mailen er afsendt, og
tjek den før afsendelse.

```python
if data.get("mail_sendt"):
    return
# … send …
data["mail_sendt"] = True   # og skriv brief.json igen
```

Så er det idempotent uanset hvad der sker med git.

## 5. Spærren, der ikke er teknisk

Det her er den vigtigste del af undersøgelsen.

Tilmeldingsformularen siger **„Få ugens AI-overblik på mail — hver fredag,
gratis“**. Ugebrevets fodnote siger **„Du får denne mail, fordi du har tilmeldt
dig Ugens AI-overblik.“** Der står *uge* og *fredag* fire steder.

At begynde at sende dagligt til den liste er at levere syv gange mere, end
folk sagde ja til. Det bryder punkt 5 i målestokken — ærlighed frem for
markedsføring — og i praksis straffer det sig selv: uventet frekvens er den
hyppigste grund til afmeldinger og spam-markeringer, og spam-markeringer
rammer afsenderens omdømme, altså også ugebrevets leveringsevne.

Fire veje, med den ærlige pris på hver:

**A. Send dagligt til alle på den nuværende liste.**
Gratis og hurtigt. Men det er det, der bryder samtykket. Jeg vil fraråde det.

**B. Lad folk vælge — tags og segmentering.** +$9/md.
Formularen får to muligheder, dagligt eller ugentligt, og eksisterende
abonnenter bliver spurgt én gang. Det er den rigtige løsning, hvis begge skal
findes ved siden af hinanden. Bemærk, at punkt 9 i målestokken siger, at penge
skal bruges på indhold, ikke på maskineri — $9/md er ikke meget, men det er
maskineri.

**C. To selvstændige nyhedsbreve.** +$29/md. Renere adskillelse, men samme
indvending og tre gange prisen. Svært at forsvare.

**D. Skift listen til dagligt, ærligt og med et valg.** Gratis.
Ret formularteksten, send én mail til de nuværende abonnenter om, at
overblikket bliver dagligt fra en bestemt dato, med et tydeligt „bliv på
ugentligt“ eller „meld fra“. Nogle falder fra. De, der bliver, har sagt ja til
det, de får.

Der er også en femte overvejelse, som taler for at vente: **er der nok
abonnenter til, at det betyder noget?** Jeg kan ikke se abonnenttallet — det
kræver API-nøglen, og den rører jeg ikke. Er tallet under ca. 20, er en daglig
mail formentlig ikke det, der flytter mest; så er punktet om Search Console
og punktet om undervisere større. Er det over 50, er en daglig vane
klart værd at bygge.

## 6. Hvis det skal bygges: hvad det kræver

Under en nats arbejde, når beslutningen i afsnit 5 er truffet:

1. En funktion `_send_dagens_mail(data)` ved siden af `_send_nyhedsbrev` — samme
   mønster, samme fejlhåndtering (fejl må aldrig vælte crawlet).
2. Emnelinje med **indhold**, ikke dato. „Dagens AI-overblik“ bliver ignoreret
   efter tre dage; det første punkts navn og tal bliver åbnet. Punkt 1 i
   målestokken gælder også i indbakken.
3. Body i Markdown fra `brief.json`s fem punkter, hvert med link til artiklen —
   Buttondown detekterer Markdown automatisk. **Pas på:** API'et afviser med
   `body_contains_frontmatter`, hvis body'en starter med en linje med `---`.
   Ugebrevet har `---` midt i teksten, hvilket er i orden, men en ny skabelon
   må ikke begynde med det.
4. `status: "scheduled"` med `publish_date` beregnet til 07:00 dansk via
   `zoneinfo`.
5. Markøren `mail_sendt` i `brief.json` (afsnit 4).
6. Tilmeldingsteksten rettet på forsiden, `uge.html` og i crawlerens skabelon,
   så den passer til det, der faktisk sendes.
7. Prøvekørsel uden afsendelse først: byg body'en og skriv den til en fil, så
   den kan læses igennem, før nogen mail forlader huset.

## 7. Min anbefaling

Byg det, men ikke først. Rækkefølgen bør være:

1. **Afklar samtykket** (afsnit 5) — det er en beslutning, ikke kode, og den
   kan træffes på fem minutter.
2. **Se abonnenttallet.** Er det tocifret og lavt, så lad punktet ligge og tag
   Search Console-punktet og undervisersiden først. En daglig mail til femten
   mennesker flytter mindre end at blive fundet i Google.
3. Byg det derefter — det er en overkommelig nats arbejde, og infrastrukturen
   er der allerede.

Sagt med målestokkens ord: en daglig vane slår en ugentlig påmindelse, og det
er rigtigt. Men en daglig mail, ingen har bedt om, slår ingenting.

---

**Kilder:** Buttondowns prisside og FAQ, `docs.buttondown.com` om scheduling og
om oprettelse af mails via API. Alt læst 25.07.2026.
