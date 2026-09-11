# Kildegennemgang · 11. september 2026

Retning: internationale AI-nyheder fortalt på dansk, med nye modeller som
førsteprioritet. Der gives ingen bonus for Danmark eller EU. Dansk adgang er
ikke en forudsætning for en relevant nyhed.

## Fund og ændringer

De otte hidtidige kilder var allerede internationale. Problemet var blandingen:
100 af de 226 artikler i den lokale udgave kom fra arXiv cs.AI. Det brede feed
leverede 245 forskningsartikler ved kontrollen, mens direkte kilder fra flere
modeludviklere manglede. Hacker News-søgningen gav også debat og genomtaler.
Begge strømme er derfor pauset, ikke slettet. Store forskningsresultater er
stadig relevante, når de dækkes af labs eller internationale medier.

Seks direkte eller specialiserede kilder er tilføjet. De eksisterende medier
bevares som modvægt til modeludviklernes egne udmeldinger. Kandidatlofterne
begrænser brede strømme; de er ikke en kvote eller garanti for en forsideplads.
Redaktøren skal fortsat frasortere reklame, små virksomhedsnyheder, snævre
papers og gentagelser af samme begivenhed.

## Aktive kilder

Alle nedenstående adresser er hentet over nettet og læst med den færdige
crawler den 11. september. 12 af 12 bestod. Antal gælder kandidater før
aldersgrænse, AI-vurdering og samling af historier.

| Kilde | Valg og rolle | Format | Loft | Læst ved kontrol |
|---|---|---|---:|---:|
| [Anthropic News](https://www.anthropic.com/news) | Ny: Claude-udgivelser og officielle forklaringer | Dateret HTML | 15 | 13 |
| [Mistral AI](https://mistral.ai/news/) | Ny: europæiske modeller, åbne udgivelser og produktnyheder | RSS | 15 | 15 |
| [Google Gemini](https://blog.google/products-and-platforms/products/gemini/) | Ny: Gemini-app, modeladgang og kreative modeller som supplement til DeepMind | RSS | 12 | 12 |
| [xAI News](https://x.ai/news) | Ny: Grok-modeller og officiel produktadgang | Dateret HTML | 15 | 15 |
| [Hugging Face](https://huggingface.co/blog) | Ny: åbne modeller, tekniske gennemgange og udgivelser fra flere lande | RSS | 12 | 12 |
| [Simon Willison AI](https://simonwillison.net/tags/ai/) | Ny: praktiske tests, modelgennemgange og begrænsninger | Atom, kun AI-tag | 10 | 10 |
| [TechCrunch AI](https://techcrunch.com/category/artificial-intelligence/) | Behold: hurtig international dækning; mindre indtag af finansiering og eventreklame | RSS | 10 | 10 |
| [The Verge AI](https://www.theverge.com/ai-artificial-intelligence) | Behold: produkter, anvendelse og konsekvenser | RSS | 10 | 10 |
| [Ars Technica AI](https://arstechnica.com/ai/) | Behold: teknisk og kritisk international dækning | RSS | 12 | 12 |
| [MIT Technology Review AI](https://www.technologyreview.com/topic/artificial-intelligence/) | Behold: større analyser; lavere indtag end modelkilderne | RSS | 6 | 6 |
| [OpenAI News](https://openai.com/news/) | Behold: direkte model- og produktudgivelser | RSS | 25 | 25 |
| [Google DeepMind](https://deepmind.google/blog/) | Behold: officielle modeller og større forskningsresultater | RSS | 15 | 15 |

De præcise crawl-adresser står i `feeds.json`. Mistrals feed bruger den
kontrollerede slutadresse `https://mistral.ai/news/rss`. Googles Gemini-feed
er det RSS-link, som deres egen Gemini-side henviser til. Simon Willisons
[egen feedvejledning](https://feeds.simonwillison.net/about/) beskriver feeds
for enkelte tags; den valgte adresse er kontrolleret som Atom.

## Begrænsninger og fravalg

- **arXiv cs.AI:** virker teknisk, men den brede forskningsstrøm passer dårligt
  som selvstændig daglig nyhedskilde til den ønskede forside. Pauset.
- **Hacker News: AI:** virker i kontrollen, men er en bred søgning i en
  aggregator. Direkte nyheder og praktiske modelgennemgange prioriteres. Pauset.
- **DeepSeek:** både den offentlige nyhedsside og API-dokumentationens
  indgang afbrød crawlerens forbindelse under kontrollen. Nyhedsteksten kunne
  læses i websøgningen, men en fungerende automatisk kilde blev ikke bekræftet.
  Derfor er ingen ustabil adresse aktiveret. DeepSeek dækkes fortsat via de
  øvrige internationale kilder. Det påvirker ikke sidens DeepSeek-modelvalg.
- **Qwen:** blogsiden svarede, men den hentede HTML gav hverken et brugbart
  feedlink eller læsbare daterede nyheder. Ingen direkte kilde er aktiveret.
  Hugging Face og de øvrige kilder supplerer dækningen af åbne modeller.

En officiel kilde dokumenterer, hvad leverandøren har udgivet eller annonceret.
Den beviser ikke automatisk leverandørens kvalitetsløfter. Agentens instruktion
kræver fortsat tilskrivning af påstande og kritiske, uafhængige gennemgange.
Kildelisten garanterer ikke, at alle verdens modellanceringer bliver fanget.

## Drift og kontrol

`nyhedskilder.py` læser overskrifter, egne links og udgivelsesdatoer fra
Anthropics og xAI's nyhedsoversigter. Dublerede kort samles, og den nyeste
udgivelse kommer først, før kildens loft anvendes. Dage uden klokkeslæt får
midnat UTC; artikler uden publiceringsdato bliver ikke gjort kunstigt aktuelle.
Ændret sideformat, tomme feeds og HTML på en RSS-adresse vises som kildefejl.

Gentag den ufarlige kildekontrol fra projektets rod:

```bash
python3 opsaetning/proev-kilder.py
```

Den henter kun aktive offentlige kilder, skriver resultatet i terminalen og
returnerer en fejlkode, hvis en kilde fejler. Ingen AI-kald, filændringer,
nyhedsbreve eller sociale opslag. De automatiske regressioner ligger i
`_redaktion/proeve-nyhedskilder.py` og kører før crawleren på GitHub.

Ændringerne tager effekt ved næste crawlerkørsel efter push. Den eksisterende
artikeludgave er ikke erstattet under kontrollen. Pausede kilders gamle
artikler genindlæses ikke i nyhedslisten ved næste crawl; arkivet bevares.
