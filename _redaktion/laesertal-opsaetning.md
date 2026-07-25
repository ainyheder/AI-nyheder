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

Tallene lander i `data/laesertal.json`, som du selv kan åbne.

---

## Hvad det ændrer

Den natlige gennemgang får nu et afsnit, den skal vægte **højest**: hvilke
sider bliver læst, hvilke får nul besøg, og hvor folk kommer fra.

Det flytter samtalen fra *"AI-kørekortet har syv moduler"* til *"AI-kørekortet
havde tre besøgende i sidste uge"* — og det er dét andet spørgsmål, der afgør,
hvad der er værd at arbejde på.

Forvent at de første gennemgange bliver ubehagelige at læse. Det er meningen.
