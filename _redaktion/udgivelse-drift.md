# Færdige artikler og modellanceringer

Crawleren skriver og kildekontrollerer artikler før offentliggørelse. Et kort
RSS-resumé er kun en kandidat. Ufuldstændige tekster og afviste udkast gemmes i
`_redaktion/udgivelsesdata.json` under `kladder`, med en forklaring i `afventer`.
Køen læses ved næste kørsel. De aktive kilders aktuelle historier kan dermed
færdiggøres, også når kildens feed ruller videre. Der er fortsat et skrivebudget
pr. kørsel; køen betyder ikke, at alle historier færdiggøres på én gang.

En artikel kræver dansk overskrift og indledning, mindst to udfoldede afsnit
med i alt mindst 80 ord samt godkendt kildekontrol. Antallet er kun et gulv;
skriveren sigter efter 180–350 ord, når kilden kan bære det. Oplysninger må ikke
opfindes for at nå en længde. En tidligere `brief_instruks` bevarer beviset for
den gamle kildekontrol. En eksplicit afvisning eller en ufærdig tekst vinder
altid over denne ældre markering.

Den samme grænse gælder den offentlige JSON-fil, forsiden, RSS, den ugentlige
opsamling og permanente artikelsider. Filer i `_redaktion` er udeladt af Pages.
GitHub Actions gemmer køen sammen med nyhedsdata. Den skal ikke slettes ved en
oprydning: så mister næste kørsel både udkast og udgivelseshistorik.

AI'ens dublettjek kører efter artiklerne er skrevet. Det får artikeltekster og
relevante tidligere udgivelser fra de seneste 30 dage, ikke kun rubrikker.
Kendte ekstra omtaler huskes i udgivelseshistorikken i 90 dage. En senere omtale
af samme hændelse beholder hovedartiklens adresse og `historie_dato`.
`dato` er fortsat kildens egen udgivelsesdato. Nye selvstændige hændelser må
ikke samles, blot fordi de handler om det samme firma.

`modeller.html` bruger `data/modellanceringer.json`. Crawleren opdaterer
oversigten automatisk fra færdige artikler og 90 dages udgivelseshistorik.
Den viser modellanceringer kronologisk med links til artikelsiderne. En
kundecase eller ny app er ikke automatisk en ny model; AI-vurderingen afgør
indholdet, og kan korrigeres ved en senere vurdering.

Skrive- og kontrolprompts findes både som standarder i Python og som aktive
valg i `_redaktion/hjerner.json`, som kommandocentralen redigerer.

Lokale kontroller: `proeve-udgivelse.py`, `proeve-workflow.py`,
`proeve-redaktoer-agent.py`, `proeve-forside.js` og `proeve-modellanceringer.js`.
JavaScript-kontrollerne bruger jsdom. Ingen af disse prøver sender et brev
eller kalder en betalt model.
