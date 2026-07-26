# Læsertal ind i loopet

Den natlige gennemgang kan nu se, hvad folk faktisk læser — ikke bare om siden
er pæn. Den henter tallene fra Cloudflare Web Analytics, som allerede kører på
hver eneste side.

Det kræver **ét** secret i GitHub: et API-token. Uden det springes trinnet
stille over, og gennemgangen kører videre som før.

**Læg aldrig tokenet i chatten.** Det hører hjemme ét sted: repoet →
Settings → Secrets and variables → Actions.

---

## Lav et token med mindst mulige rettigheder

Giv aldrig en crawler mere adgang, end den skal bruge. Den her skal kun kunne
*læse* statistik — ikke røre din side, dit DNS eller din mail.

1. dash.cloudflare.com → klik på profilikonet øverst til højre → **Profile**.
2. Vælg **API Tokens** → **Create Token**.
3. Vælg **Create Custom Token** (ikke en færdig skabelon).
4. Navn: `ainyheder-laesertal`
5. Permissions — tilføj præcis én linje:
   - **Account** · **Account Analytics** · **Read**
6. Account Resources: **Include** → din konto.
7. Client IP Address Filtering: lad stå tomt.
8. TTL: lad stå, eller sæt en udløbsdato hvis du vil tvinges til at forny den.
9. **Continue to summary** → **Create Token**.
10. Kopiér tokenet. **Det vises kun én gang.**

Læg det i GitHub som secret'en `CLOUDFLARE_API_TOKEN`. Det er alt.

### Har du flere Cloudflare-konti?

Så — og kun så — skal crawleren vide, hvilken den skal læse fra. Find
**Account ID** på dash.cloudflare.com under din side i højre side, og læg det
i som secret'en `CLOUDFLARE_ACCOUNT_ID`. Har du kun én konto, springer du det
her helt over: crawleren bruger bare den konto, tokenet giver adgang til.

---

## Fælden: site-tag er ikke beacon-tokenet

De to ligner hinanden — begge er 32 tegn hex — men de er **forskellige felter
med forskellig værdi**, og de kan ikke bruges i stedet for hinanden.

| Hvad | Hvor det står | Bruges til |
|---|---|---|
| **Beacon-token** | `data-cf-beacon` i hver HTML-side | At *sende* målinger til Cloudflare |
| **Site-tag** | Adressen i Cloudflare, `?siteTag~in=…` | At *hente* dem igen via API'et |

Crawleren skal bruge **site-tag'et**, og det står i `CF_SITE_TAG` i `crawler.py`.
Find det ved at åbne Web Analytics for sitet og kigge i browserens adresselinje:

```
dash.cloudflare.com/<konto>/web-analytics/overview?siteTag~in=DET_HER&…
```

Bytter man dem om, sker der noget værre end en fejl: alt ser ud til at virke.
Godkendelsen går igennem, kontoen findes, filen bliver skrevet — der står bare
nul besøg overalt, som om ingen havde været på siden. Det kostede en eftermiddag
første gang.

## Tjek at det virker

Ved næste crawl står der i Actions-loggen:

```
📈 Læsertal: 534 besøg på 23 sider de seneste 7 dage
```

Står der i stedet en advarsel, fortæller den hvad der er galt:

| Linje | Betyder |
|---|---|
| ingen 📈-linje | Et af de to secrets mangler eller er stavet forkert |
| `Cloudflare svarede med fejl: Authentication error` | Tokenet er forkert eller mangler Account Analytics · Read |
| `Cloudflare gav ingen data - er konto-id'et rigtigt?` | `CLOUDFLARE_ACCOUNT_ID` passer ikke |

Tallene lander i `data/laesertal.json`, som du selv kan åbne — og i
`data/laesertal-data.js`, som er nøjagtig det samme, bare pakket ind i en
JavaScript-variabel, så kontrolpanelet kan læse dem fra `file://`.

---

## Hvor du selv ser tallene

Åbn `_redaktion/kontrolpanel.html`. Så snart der er tal, åbner panelet på en ny
rude, **Læserne**, øverst i sidebjælken. Er der ingen tal endnu, står panelet
hvor det plejer, og ruden fortæller selv, hvad der mangler.

Ruden viser fire ting:

| Afsnit | Hvad det svarer på |
|---|---|
| Tre tal øverst | Besøg, sidevisninger og hvor mange der kom fra en AI-chat |
| Mest læste sider | De 12 mest besøgte, med bjælker i forhold til hinanden |
| Faste sider uden ét eneste besøg | Dét, der som regel er værd at handle på |
| Hvor de kommer fra + Fundet i AI-chats | Henviserne, og AI-chatterne trukket ud for sig |

## Bliver vi fundet i AI-chats?

Kom nogen ind via ChatGPT, Perplexity, Claude, Gemini, Copilot, Grok, DeepSeek,
Le Chat, You.com, Poe eller Phind, bliver det talt for sig. To adresser for
samme tjeneste (`chatgpt.com` og `chat.openai.com`) lægges sammen til ét tal.

To ting, det **ikke** er:

- **Søgemaskiner tælles ikke med.** Google, Bing og DuckDuckGo står i
  "Hvor de kommer fra", ikke under AI-chats — også når de viser et AI-svar.
- **Det er ikke det samme som at blive citeret.** Her tælles kun dem, der rent
  faktisk *klikkede*. Bliver siden citeret uden link, ser vi det ikke. Og
  AI-robotternes egen hentning af siderne tælles heller ikke: Cloudflare
  sorterer bots fra, før tallene når hertil.

Nul er derfor et helt normalt sted at starte.

---

## Hvad det ændrer

Den natlige gennemgang får nu et afsnit, den skal vægte **højest**: hvilke
sider bliver læst, hvilke får nul besøg, hvor folk kommer fra — og om nogen
overhovedet finder frem gennem en AI-chat.

Det flytter samtalen fra *"AI-kørekortet har syv moduler"* til *"AI-kørekortet
havde tre besøgende i sidste uge"* — og det er dét andet spørgsmål, der afgør,
hvad der er værd at arbejde på.

Forvent at de første gennemgange bliver ubehagelige at læse. Det er meningen.
