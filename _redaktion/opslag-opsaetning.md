# Automatiske opslag på sociale platforme

Crawleren kan vælge dagens bedste historie, lade AI'en skrive et opslag på dansk
og lægge det ud. Motoren er bygget og testet — den venter bare på adgang.

**Vigtigst af alt: der bliver ikke sendt noget, før du selv slår det til.**
Uden variablen `OPSLAG_LIVE` skriver crawleren kun udkastet i loggen og gemmer det
i `data/opslag.json`. Det er med vilje: et opslag kan ikke trækkes tilbage.

Læg aldrig nøgler eller tokens ind i chatten. De hører kun hjemme ét sted:
**repoet → Settings → Secrets and variables → Actions**.

---

## Sådan virker den

- Kører som en del af hvert crawl.
- Vælger den nyeste historie med prioritet 7 eller derover, som har en
  "Hvad betyder det for dig", og som ikke er delt før.
- Springer kilder over, der ikke må arkiveres (Version2, Ingeniøren).
- Skriver tre varianter: kort til Bluesky, hverdagsagtig til Facebook,
  saglig til LinkedIn.
- **Højst 2 opslag om dagen.** Fejler en platform, kører crawlet videre.

---

## 1. Bluesky — nemmest, ingen godkendelse

1. Opret kontoen på bsky.app (fx `ainyheder.bsky.social`).
2. Gå til **Settings → Privacy and security → App passwords → Add app password**.
   Kald den "ainyheder-crawler". Kopiér koden — den vises kun én gang.
3. Læg to secrets i GitHub:
   - `BLUESKY_BRUGER` = dit fulde handle, fx `ainyheder.bsky.social`
   - `BLUESKY_KODE` = app-adgangskoden (ikke din rigtige adgangskode)

Brug **altid** en app-adgangskode. Den kan tilbagekaldes uden at røre din konto.

---

## 2. Facebook-side — kræver en udvikler-app

1. Opret Facebook-siden for AI-nyheder, hvis den ikke findes.
2. Gå til developers.facebook.com → **My Apps → Create App** → typen "Business".
3. Tilføj produktet **Facebook Login** og tilladelsen `pages_manage_posts`
   samt `pages_read_engagement`.
4. I **Graph API Explorer**: vælg din app, vælg din side, og generér et
   side-token med de to tilladelser.
5. Byt det korte token til et **langtidsholdbart side-token** — ellers udløber
   det efter en time. Meta har en vejledning under "Long-Lived Tokens".
6. Find sidens ID nederst på siden under **Om**.
7. Læg i GitHub:
   - `FACEBOOK_SIDE_ID`
   - `FACEBOOK_TOKEN` (det langtidsholdbare)

Meta kræver app-gennemgang, før en app må slå op på vegne af andre. Så længe det
kun er din egen side, og du selv er administrator, kan du typisk køre i
udviklingstilstand. Regn med lidt bøvl her.

---

## 3. LinkedIn-virksomhedsside — kræver ansøgning

1. Opret virksomhedssiden.
2. developer.linkedin.com → **Create app**, knyt den til siden.
3. Ansøg om produktet **Community Management API** og tilladelsen
   `w_organization_social`. LinkedIn læser din begrundelse manuelt — beskriv
   ærligt, at det er et dansk nyhedssite, der deler sine egne artikler.
4. Når det er godkendt: generér et access token via OAuth.
5. Find organisations-ID'et i URL'en på din admin-side.
6. Læg i GitHub:
   - `LINKEDIN_ORG_ID`
   - `LINKEDIN_TOKEN`

**Husk:** LinkedIn-tokens udløber efter 60 dage. Sæt en påmindelse, eller vær
forberedt på, at opslagene stopper med en fejl i loggen.

---

## 4. Slå det live

Så længe du ikke gør det her, sker der ingenting udadtil.

1. Kør et crawl og læs loggen. Linjerne `📣 [TØRKØRSEL] ...` viser præcis,
   hvad der ville være blevet slået op.
2. Er du tilfreds med tonen: **Settings → Secrets and variables → Actions →
   Variables → New repository variable**
   - Navn: `OPSLAG_LIVE`
   - Værdi: `ja`
3. Vil du stoppe igen, sletter du variablen. Så er du tilbage i tørkørsel med
   det samme.

---

## Hvis noget går galt

Alt står i Actions-loggen under "Kør crawleren":

| Linje | Betyder |
|---|---|
| `📣 [TØRKØRSEL] Bluesky: ...` | Alt virker, men live er ikke slået til |
| `📣 Delt på Bluesky: ...` | Opslaget er ude |
| `📣 ⚠️ Facebook fejlede: ...` | Token udløbet eller tilladelse mangler |
| ingen 📣-linje overhovedet | Ingen historie var god nok i dag, eller loftet på 2 var nået |

Historier, der er delt, huskes i `data/opslag.json`, så de aldrig går ud to gange.
