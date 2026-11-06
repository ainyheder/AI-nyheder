# Workflowgennemgang · 6. november 2026

Gennemgået: kildehentning, modelvalg/reasoning, redaktøragent, artikel- og kildekontrol, genoptagelse, billeder, overblik, sociale udkast, nyhedsbrevets drift og de tre GitHub-workflows. Ændringerne i denne gennemgang er lokale og kræver commit/push, før GitHub bruger dem.

## Målt i produktion

[Crawl #796](https://github.com/ainyheder/AI-nyheder/actions/runs/42294330733) sluttede med success kl. 22.16 dansk tid. Hele jobbet tog 7m16s; crawleren tog 385,71 sekunder, dvs. 6,43 minutter. Tidligere afsluttet crawl havde taget 1.167,94 sekunder, dvs. 19,47 minutter. Det er forskellige arbejdsgrundlag, så forskellen er ikke en kontrolleret hastighedsmåling af disse nye ændringer.

| Trin i #796 | Sekunder |
|---|---:|
| Resuméer | 43,78 |
| Nyhedsvurdering | 61,15 |
| Redaktionsmøde | 44,63 |
| Artikler og kildekontrol | 60,84 |
| Udgavekontrol | 12,91 |
| Dubletter | 18,52 |
| Billedmotiver | 11,99 |
| Billeder | 87,26 |
| Ugens overblik | 31,00 |
| Dagens overblik | 7,42 |

GitHubs `_redaktion/hjerner.json` havde GPT-6.1 Terra med medium på alle 14 aktive teksttrin i panelet. Loggen havde ingen model-reservekald. Agenten gennemførte seks modelkald uden transportfejl, men den samlede kildekontrol afviste forsideplanen. Derfor blev regeludvalget brugt. Et grønt Actions-job er ikke en garanti for, at forsideagentens plan blev godkendt.

## Rettet lokalt

- Anthropic-listen placerer datoen uden for linket. Parseren binder nu dato og overskrift inden for samme eksplicitte nyhedsrække. Hentet HTML gav 24 daterede artikler efter rettelsen, mod nul før. Udaterede rækker og indhold i scripts accepteres ikke.
- Identiske sociale udkast genbruges ved uændret artikel, model, reasoning og instruks. Ændringer udløser et nyt kald. Gentagne tørkørsler giver ikke flere identiske kladder.
- Faktiske modeltransporter måles med model-ID, reasoning, fejl, tid og reservebrug. GitHub-resuméet viser tallene; rapporten gemmes som artifact i 14 dage, også ved fejl hvor Python nåede at skrive rapporten.
- Kommandocentralens statuspakke bevarer nu `openai_tilgaengelig`, så manglende OpenAI-adgang kan vises.
- Checkout, Python-opsætning, cache og artifacts er opdateret til verificerede officielle udgaver: checkout v7.0.1, setup-python v7.1.0, cache v6.1.0 og upload-artifact v7.0.2. Den aktuelle GitHub-runner opfylder Node 24-kravet. Eksisterende cache-nøgler bevares.
- Nyhedsbrevets to billedjobs bruger nu pip-cache med stien til den relevante requirements-fil.
- Cloudflare-billedfejl viser HTTP-status uden at logge token eller svarindhold.
- Paneltestens startkontrol accepterer cache-versioner i URL'en. En særskilt test dækker Terra/medium fra fællesvalg til gemt fil.

## Kontrolleret uden nye betalte kald

Alle 16 Python-testsuiter fra crawlerens workflow bestod. Billedtestene blev kørt med Pillow og Pooch tilgængelige, uden modeldownload. Alle 23 panelkontroller bestod. De tre YAML-filer og deres indlejrede Python blev syntakskontrolleret. De seneste ændringer i driftsmålingen blev desuden kontrolleret med 13 driftstests og 83 modelvalgskontroller. Ingen rigtige mails eller sociale opslag blev sendt af gennemgangen.

## Punkter, der stadig kræver driftsopfølgning

- xAI svarede HTTP 403 i #796. Det er en ekstern adgangsfejl; kilden bevares med synlig fejlstatus.
- OpenAI-bloggens RSS blev hentet, men mange artikelsider gav for lidt læsbar kildetekst. De forbliver kladder; korte RSS-uddrag ophøjes ikke til færdige artikler.
- Cloudflare leverede ét billede og derefter to HTTP-fejl. Den nuværende breaker stopper yderligere billedforsøg efter to fejl i træk. Fritlægningen af ét billede overskred 45 sekunder, så originalbilledet blev brugt. Den nye HTTP-kode i loggen skal vise, om de næste fejl er adgang, kvote eller noget andet.
- Først næste GitHub-kørsel efter push kan måle effekten af ændringerne i denne gennemgang. Modelforbrug måles som kald og tid, ikke som kroner eller en dokumenteret kvalitetsgevinst.
