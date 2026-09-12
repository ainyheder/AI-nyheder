# Fremtiden, forklaret — redaktionel retning

Opdateret 12. september 2026 efter Torbens referencebrev fra Peter Diamandis.

## Læserløftet

Fyldige, letlæste breve, som følger Peter Diamandis’ nye skriverier, når de udkommer og hjælper læseren forstå idéerne, eksemplerne og deres mulige betydning. Internationalt udsyn, dansk sprog. Brevet skal give en selvstændig læseoplevelse med stof til eftertanke.

## Redaktørprompt — én kilde til instruktionen

Den komplette systemprompt ligger i [opsaetning/nyhedsbrev-prompt.md](../opsaetning/nyhedsbrev-prompt.md). Brug den sammen med hele originalbrevet og kontrollerede metadata som brugerinput. De tidligere instruktioner i dette dokument er erstattet af denne prompt.

Prompten kræver substans og trofasthed mod hovedidéen, et selvstændigt udvalg og en selvstændig fortælling, kreditering i introen og en intern redaktionsnote. Den afviser både tynde referater, uvedkommende kommentarer og afsnitsvis oversættelse med nye ord. Den giver ingen garanti mod plagiat eller ophavsretlige krav.

To adskilte spørgsmål skal vurderes: om læseren tydeligt kan se kilden, og om genbrugen af den oprindelige udformning kræver tilladelse. Kreditering løser ikke automatisk det sidste. Kulturministeriets vejledning behandler både citater og bearbejdelser: https://kum.dk/kulturomraader/vil-du-vide-mere-om-ophavsret/boeger-og-tekster

## Kontrol før en udgave er klar

- Gengiver brevet den rigtige hovedidé og forklarer det, der gjorde originalen interessant?
- Er tekstens vinkel, udvalg og sammenhæng selvstændige, eller følger den originalen afsnit for afsnit?
- Er særprægede vendinger, oversatte metaforer og lånte jeg-oplevelser undgået?
- Er krediteringen kun den linkede tekst “Peter Diamandis’ læserbrev” i introen, mens metadata gemmes internt og særlige fremtidsbud stadig kan henføres til deres ophav?
- Er supplerende fakta belagt, og er uafklarede forhold synlige i den interne redaktionsnote?
- Kan indholdet bære længden uden fyld eller tæt gengivelse?

## Mailfooter

Buttondowns automatiske footer er eneste sted med afmelding og abonnementsadministration. Brevets HTML må ikke tilføje et ekstra afmeldingslink. Den aktuelle usendte prøve 4 følger dette. Tidligere udsendte prøver er bevaret som historik.

## Udsendelse

Det selvstændige forløb i `nyhedsbrev.py` følger nye offentlige Metatrends-breve.
GitHub kontrollerer kilden én gang i døgnet; et godkendt brev overdrages
straks til Buttondown, uden at vente på en bestemt ugedag. GitHub og kildens
RSS-udgivelse kan give ventetid. Automatiseringen er aktiv efter push til main.

Det gamle fredagsbrev er frakoblet. Uge.html har stadig sit eget overblik og
sin egen instruks. Gamle originaler, herunder prøvebrevet fra 10. september,
genudsendes ikke. Kvalitetskontrol og varig historik beskytter mod dårlige og
dobbelte udsendelser. Se [driftsvejledningen](nyhedsbrev-drift.md).
