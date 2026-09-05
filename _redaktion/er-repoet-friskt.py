#!/usr/bin/env python3
"""Svarer på ét spørgsmål, før en session rører noget: er mappen den samme
kode, som verden kører?

Baggrunden står i arbejdsloggen 14.08.2026. Den lokale mappe var **86 commits
bagud**, sidste commit fra 31.07, og ingen kørsel havde opdaget det i fjorten
døgn. Fase 0 tjekkede kun den ene retning — `git status` fanger *uafhentet*
arbejde, altså det, sessionen selv har lavet og ingen har committet. Den kan per
definition ikke se *uhentet* arbejde: 86 commits, der ligger på GitHub og aldrig
er trukket ned. Arbejdstræet er spejlblankt i begge tilfælde.

Prisen for at overse det er ikke teoretisk. En session, der retter `crawler.py`
på en fjorten dage gammel udgave, afleverer en flettekonflikt i netop den fil,
redaktionen skal committe i hånden — og den nemmeste vej ud af den konflikt i
GitHub Desktop er at vælge "min version", hvilket ruller to ugers arbejde
tilbage uden at nogen opdager det.

**Den regel, der betyder noget, er ikke hvor mange commits.** Crawleren pusher
flere gange i døgnet, så mappen er næsten altid et par commits bagud på
`data/`, `artikel/` og `video/` — og det er ufarligt, fordi ingen session
redigerer dem i hånden. Farligt er det først, når **kode** er bagud: crawleren,
rodsiderne, kontrolpanelet, kildelisten.

**Tvivl er ikke det samme som grønt lys.** Kan en delmåling ikke laves — fetch
fejler, `git diff` fejler — så svarer scriptet 2 og ikke 0. Den regel er skrevet
ind efter en gennemgang 14.08, der viste, at den første udgave sagde "arbejd
løs" i præcis de situationer, hvor den ikke vidste noget: uden netværk faldt den
tilbage på en cachet ref, og en gammel cache siger naturligvis "0 bagud".

Udgange:
  0 = arbejd løs (evt. med en advarsel, der skal i loggen)
  1 = STOP, mappen er bagud på kode
  2 = kan ikke afgøres — skriv det i loggen, og lad kode være

Kør: python3 _redaktion/er-repoet-friskt.py
     python3 _redaktion/er-repoet-friskt.py --kun-cache   (spring fetch over)

Scriptet skriver ikke i arbejdstræet og bruger `--no-optional-locks` overalt, så
det aldrig efterlader den `.git/index.lock`, der har spærret GitHub Desktop før.
Det henter til gengæld fra den remote, målestokken ligger på, og `git fetch`
skriver i `.git` (refs, packs, FETCH_HEAD) — ikke i dine filer, men det er ikke
ingenting. `--kun-cache` lader det være.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Scriptet ligger i `_redaktion/`, så repoets rod er mappen over. Alle
# git-kald forankres her med `-C`, i stedet for at arve den mappe, processen
# tilfældigvis blev startet i.
#
# Uden forankringen svarer scriptet på et helt andet spørgsmål, end det tror.
# Står cwd i en anden klon — og repoets egen `.gitignore` nævner `AI-nyheder/`,
# "en klon af præcis dette repo" — svarer det "✅ Arbejd løs" om den klon,
# mens mappen, sessionen faktisk redigerer, er fjorten døgn bagud. Startes det
# med absolut sti fra en agents arbejdsmappe, svarer det "ikke et git-repo" →
# 2 hver eneste nat, og ingen kan se forskel på det og et rigtigt problem.
REPO_ROD = Path(__file__).resolve().parent.parent

# Mapper, crawleren selv skriver ved hver kørsel. At være bagud på dem betyder
# kun, at Actions har kørt siden sidst — ikke at nogen kan komme til at redigere
# en forældet udgave, for ingen session redigerer dem i hånden. Skråstregen er
# ikke pynt: uden den ville `assets.py` i roden tælle med.
#
# `assets/` stod her i den første udgave og er taget ud igen. Den er ikke
# crawlerens: `git log origin/main -- assets/` giver 9 commits, alle fra
# mennesker (Torben 5, ntorsleff 4), og `crawler.py` skriver ingen steder i
# mappen — den nævner kun `/assets/…` som `src` i genereret HTML. Logo,
# favicons og `assets/fonts/skrifter.css` er redaktionens egne filer, og en
# forældet udgave af dem skal kunne udløse et stop.
CRAWLER_MAPPER = ("data/", "artikel/", "video/")

# Crawlerens output i roden, som ingen redigerer i hånden, fordi de bliver
# skrevet forfra ved hver kørsel. Skabelonen for `uge.html` ligger i
# `_uge_side_html()` i crawler.py (`UGE_HTML.write_text`, to steder) — retter
# man selve filen, er ændringen væk ved næste kørsel.
#
# Uden `uge.html` her rammer et repo, der er halvandet døgn bagud på ren
# crawler-output, et hårdt STOP med teksten "1 af de bagudliggende filer er
# KODE: uge.html" og hele flettekonflikt-advarslen — hvor der ikke er nogen
# konflikt. En vagt, der råber ulven kommer hver anden dag, bliver ikke adlydt.
#
# Ærligt om tallene, så den næste kan være uenig: `uge.html` har 10
# bot-commits, men også 7 fra mennesker (Torben 5, ntorsleff 2). Den består
# altså ikke falsifikationsprøven nedenfor rent. Afvejningen er, at filen
# skrives forfra af `_uge_side_html()` ved hver ugekørsel, så en håndrettelse
# i selve filen alligevel forsvinder — rettelsen hører hjemme i crawler.py.
# Alle syv menneske-commits rørte da også kode samtidig, så de ville være
# blevet fanget alligevel.
CRAWLER_ROD = ("uge.html",)

# Både præfiks OG .xml kræves, og kun i roden — ellers fanger reglen
# `opsaetning/feeds.json`, som er kildelisten, redaktionen selv retter i
# hånden, og som derfor SKAL kunne udløse et stop.
#
# Bindestregen i `sitemap-` er ikke en tastefejl. `sitemap-artikler.xml` (138
# bot-commits) og `sitemap-videoer.xml` (44) skrives af crawleren, men
# **`sitemap.xml` gør ikke**: den har 0 bot-commits og 9 fra mennesker, den
# skriver selv i sin egen kommentar at den "vedligeholdes i hånden", og
# `tjek_statisk_sitemap()` i crawler.py er netop bygget til at få en session
# til at rette den i hånden. Uden bindestregen ville en forældet udgave af en
# håndholdt fil blive kaldt crawlerens og aldrig udløse et stop.
CRAWLER_ROD_XML = ("sitemap-", "feed")

# Sådan efterprøves de tre lister, når nogen er i tvivl. Spørgsmålet er ikke,
# hvem der har committet filen, men **om crawleren skriver den**:
#
#   grep -n 'write_text\|open(' crawler.py | grep '<filnavn>'
#
# Brug IKKE `git log --format='%an'` alene. Redaktionen committer maskinens
# arbejde i hånden i GitHub Desktop, så `%an` fortæller, hvem der trykkede på
# knappen — ikke hvem der skrev filen. Målt på origin har `data/` 272
# bot-commits og 93 fra mennesker, og `data/hjerner-status.json` har 49 fra
# mennesker, selvom `skriv_hjerne_status()` i crawler.py skriver den hver
# kørsel. Fulgt efter bogstavet ville navnetællingen stryge hele `data/` fra
# listen. Den er et fint supplement, når man er i tvivl — men det er
# `crawler.py`, der afgør sagen.

# Selv når kun crawlerens egne filer er bagud, holder tallene op med at være
# tal: `data/laesertal.json` og `data/articles.json` beskriver så ikke længere
# den side, en måling i fase 0 tror, den måler.
#
# Tallet er målt, ikke gættet. Cron'en kører 19 gange i døgnet, men crawleren
# committer kun, når der er noget nyt — de faktiske commits på origin/main over
# fjorten døgn var 7, 7, 10, 3, 5, 4, 2, 8, 10, 9, 6, 6, 6, 6, altså omkring
# seks i døgnet. 12 er derfor cirka to døgn. Den første udgave satte 40 ud fra
# de 19 kørsler og var dermed tre gange for løs.
MAX_COMMITS_BAGUD = 12


def er_crawlerfil(sti: str) -> bool:
    """Sand, hvis filen skrives af crawleren og ikke af et menneske."""
    if any(sti.startswith(m) for m in CRAWLER_MAPPER):
        return True
    if "/" in sti:                       # rod-reglerne gælder kun roden
        return False
    if sti in CRAWLER_ROD:
        return True
    if sti.endswith(".xml"):
        return any(sti.startswith(p) for p in CRAWLER_ROD_XML)
    return False


def koer(args: list[str], timeout: int = 30,
         rod: Path | str | None = None) -> tuple[int, str, str]:
    """Kør en git-kommando. Returnerer (exitkode, stdout, stderr).

    Vælter aldrig. De to strømme holdes adskilt, fordi to kaldere parser
    resultatet som DATA — fillisten og status. Limes de sammen, kan en
    `warning: could not open directory …` på stderr blive talt som en fil:
    et opdigtet filnavn i STOP-beskeden, eller en ekstra "ændret fil", der
    ikke findes.

    `-C` forankrer kaldet i repoets rod i stedet for processens cwd.
    `core.quotepath=false` er der, fordi git ellers skriver et filnavn med æøå
    som `"artikel/bl\\303\\245b\\303\\246r.html"` — med anførselstegn foran, så
    `startswith("artikel/")` fejler og filen fejlagtigt tælles som kode. Der er
    ingen sådanne filnavne i repoet i dag; flaget koster ingenting og fjerner
    fælden, før nogen falder i den.

    `--no-optional-locks` er heller ikke pynt: uden det efterlader git en
    `.git/index.lock`, og så kan redaktionen ikke committe i GitHub Desktop.
    Det har generet fire gange.
    """
    forankring = ["-C", str(rod)] if rod else []
    try:
        p = subprocess.run(
            ["git", "--no-optional-locks", *forankring,
             "-c", "core.quotepath=false", *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, (p.stdout or ""), (p.stderr or "")
    except Exception as f:
        # Timeout er den mest realistiske netværksfejl af alle: en `fetch`, der
        # HÆNGER — DNS-blackhole, lukket havn, VPN — i stedet for at fejle
        # hurtigt. Returnerede den her 0, ville en hængende hentning blive
        # aflæst som en vellykket, og scriptet ville sige "arbejd løs". 127 er
        # ikke pynt; det er den samme fail-closed-regel som alle andre steder.
        return 127, "", f"{type(f).__name__}: {f}"


def find_maalestok(rod: Path | str | None = None) -> str | None:
    """Hvad skal vi sammenligne med? Branchens egen upstream, hvis den har en.

    Hårdkodet `origin/main` ville give permanent falsk STOP for enhver, der
    arbejder på en anden gren — alt på main ville se ud som uhentet kode.
    """
    kode, ud, _ = koer(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        rod=rod)
    if kode == 0 and ud.strip():
        return ud.strip()
    for kandidat in ("origin/main", "origin/master"):
        if koer(["rev-parse", "--verify", "--quiet", kandidat], rod=rod)[0] == 0:
            return kandidat
    return None


def hent_tilstand(kun_cache: bool = False,
                  rod: Path | str | None = None) -> dict:
    """Saml de rå tal. Ingen vurdering her — den ligger i doem().

    `rod` er repoet, der måles. Er den None, bruges processens cwd — det er
    kun til prøven; `main()` sender altid REPO_ROD.
    """
    t: dict = {"fejl": None, "hentede": False, "sprang_hentning": kun_cache,
               "bagud": 0, "foran": 0, "urene": 0,
               "kodefiler": [], "crawlerfiler": 0, "maalestok": None,
               "rod": str(rod) if rod else None}

    if koer(["rev-parse", "--git-dir"], rod=rod)[0] != 0:
        t["fejl"] = "ikke et git-repo"
        return t

    t["maalestok"] = find_maalestok(rod)
    if not t["maalestok"]:
        t["fejl"] = "fandt ingen upstream at sammenligne med"
        return t
    m = t["maalestok"]

    if not kun_cache:
        # Hent fra DEN remote, målestokken ligger på — ikke fra `origin` per
        # automatik. Ligger branchens upstream på en anden remote, ville et
        # hårdkodet `fetch origin` lykkes, sætte hentede=True og efterlade den
        # ref, vi faktisk måler mod, urørt. Så svarer scriptet "Mappen er den
        # samme kode, som verden kører" om en måling, det ikke har lavet — den
        # mest selvsikre besked, det har, om det, det ved mindst om.
        remote = m.split("/")[0] if "/" in m else "origin"
        # Fetch rører ikke arbejdstræet. Fejler den — ingen netværk, lukket
        # havn — arbejder vi videre på den cachede ref, men doem() nægter så at
        # sige god for et repo, der ser rent ud. Et gammelt facit ligner et
        # rent repo på en prik.
        t["hentede"] = koer(["fetch", remote, "--quiet"],
                            timeout=180, rod=rod)[0] == 0

    kode, ud, _ = koer(["rev-list", "--left-right", "--count", f"HEAD...{m}"],
                       rod=rod)
    if kode != 0:
        t["fejl"] = f"kunne ikke tælle commits mod {m}"
        return t
    try:
        foran, bagud = ud.split()[:2]
        t["foran"], t["bagud"] = int(foran), int(bagud)
    except ValueError:            # for få felter ELLER ikke-tal — begge er ValueError
        t["fejl"] = f"kunne ikke læse commit-tallene: {ud.strip()[:80]}"
        return t

    # TRE prikker. To ville sammenligne træerne direkte og dermed også vise de
    # ændringer, der ligger i vores EGNE ucommittede-men-upushede commits — så
    # et repo, der er 1 foran og 0 bagud, ville få "STOP, crawler.py er bagud",
    # og rådet "træk ned" kunne ikke fjerne det. Tre prikker måler fra
    # merge-base og viser kun det, den anden side har, som vi ikke har.
    # Kun stdout parses som filnavne. Ville stderr limes med, kunne en
    # `warning: could not open directory …` blive talt som en KODE-fil og
    # udløse et STOP med et opdigtet filnavn.
    kode, ud, _ = koer(["diff", "--name-only", f"HEAD...{m}"], rod=rod)
    if kode != 0:
        t["fejl"] = f"kunne ikke se, hvilke filer der er bagud ({m})"
        return t
    for sti in (l.strip() for l in ud.splitlines() if l.strip()):
        if er_crawlerfil(sti):
            t["crawlerfiler"] += 1
        else:
            t["kodefiler"].append(sti)

    # `-uall` folder nye mapper ud til enkeltfiler. Uden det svarer git med
    # `?? _redaktion/` i stedet for `?? _redaktion/.koerer`, når mappen er ny —
    # og så rammer undtagelsen nedenfor forbi, og sessionens egen låsefil bliver
    # talt som uafhentet arbejde. Prøven fangede det i et nybygget testrepo.
    kode, ud, _ = koer(["status", "--short", "-uall"], rod=rod)
    if kode != 0:
        t["fejl"] = "kunne ikke læse git status"
        return t
    # Sessionens egen låsefil er ikke uafhentet arbejde. Sammenlign på stien og
    # ikke som understreng i hele linjen: ellers ville en fil, der tilfældigvis
    # hedder noget med `.koerer`, forsvinde lydløst ud af tællingen.
    t["urene"] = len([l for l in ud.splitlines()
                      if l.strip()
                      and l[3:].strip().strip('"') != "_redaktion/.koerer"])
    return t


def _uafhentet(t: dict) -> list[str]:
    """Linjerne om vores eget arbejde, der ikke er hentet af redaktionen."""
    if not (t["foran"] or t["urene"]):
        return []
    dele = []
    if t["foran"]:
        dele.append(f"{t['foran']} commits foran")
    if t["urene"]:
        dele.append(f"{t['urene']} ændrede filer")
    return [f"⚠️  Uafhentet arbejde: {' og '.join(dele)}.",
            "   Skriv det ØVERST i arbejdsloggen — det er ikke hentet endnu."]


def doem(t: dict, maks_bagud: int = MAX_COMMITS_BAGUD) -> tuple[int, list[str]]:
    """Den rene vurdering: tilstand ind, (exitkode, linjer) ud.

    Holdt fri for git med vilje, så prøven kan prøve hver enkelt regel mod
    opdigtede tal.
    """
    l: list[str] = []

    if t["fejl"]:
        return 2, [f"❓ Kan ikke afgøre, om mappen er frisk: {t['fejl']}.",
                   "   Skriv det i loggen, og lad kode være. Tvivl er ikke",
                   "   grønt lys — det var netop den fejl, der lod mappen",
                   "   drive fjorten døgn fra virkeligheden i august 2026."]

    if not t["hentede"]:
        # De to grunde skal ikke hedde det samme. "Kunne ikke" er en fejl, der
        # skal undersøges; "sprang over" er noget, kalderen selv bad om.
        # Remoten skal nævnes ved navn: står upstream på `andet`, hjælper det
        # ingen at læse, at "origin" fejlede.
        remote = (t.get("maalestok") or "origin/?").split("/")[0]
        if t.get("sprang_hentning"):
            l.append("⚠️  Sprang hentningen over (--kun-cache) — tallene er fra")
        else:
            l.append(f"⚠️  Kunne ikke hente fra {remote} — tallene er fra")
        l.append("   den cachede ref og er derfor et MINIMUM. Der kan være flere.")

    kodefiler = t["kodefiler"]
    if kodefiler:
        # Står der kodefiler, er STOP rigtigt, også uden en frisk hentning:
        # tallet kan kun blive værre, aldrig bedre.
        vis = ", ".join(kodefiler[:6]) + (" …" if len(kodefiler) > 6 else "")
        return 1, l + [
            f"🛑 STOP. Mappen er {t['bagud']} commits bagud i forhold til "
            f"{t['maalestok'] or 'upstream'}, og {len(kodefiler)} af de "
            f"bagudliggende filer er KODE:",
            f"   {vis}",
            "",
            "   Retter du noget i dag, afleverer du en flettekonflikt i filer,",
            "   redaktionen skal committe i hånden — og den nemmeste vej ud af",
            "   den konflikt ruller det uhentede arbejde tilbage.",
            "",
            "   Redaktionen skal trække ned i GitHub Desktop først.",
            "   Skriv én linje i arbejdsloggen om, at du sprang over, slet din",
            "   låsefil `_redaktion/.koerer`, og slut.",
        ] + _uafhentet(t)         # den værste kombination skal nævne begge dele

    # Grænsen gælder UANSET om hentningen lykkedes. Samme argument som ovenfor:
    # tallet kan kun blive større af en frisk hentning, aldrig mindre. Lå den
    # her efter cache-porten, ville et netværksudfald have gjort 14.08 til et
    # roligt "2 — lad kode være", og sessionen ville have målt løs på et
    # fjorten dage gammelt `data/`. Det er præcis den ene ting, grænsen
    # findes for at forbyde.
    if t["bagud"] > maks_bagud:
        return 1, l + [
            f"🛑 STOP. Mappen er {t['bagud']} commits bagud (grænsen er "
            f"{maks_bagud}). Kun crawlerens egne filer er bagud, så der er",
            "   ingen kodekonflikt — men `data/` er så gammel, at enhver måling",
            "   i fase 0 ville beskrive en side, der ikke findes længere.",
            "   Redaktionen skal trække ned i GitHub Desktop først.",
            "   Skriv én linje i arbejdsloggen, slet din låsefil, og slut.",
        ] + _uafhentet(t)

    # Modsigelsen SKAL prøves før cache-porten. Lå den bagefter, ville et repo
    # uden frisk hentning få teksten "alle i crawlerens egne filer (0 stk.)" —
    # en påstand om en måling, der ikke findes, og præcis den slags sætning
    # scriptet ellers forbyder. Dommen er 2 i begge tilfælde; det er
    # begrundelsen, der skal kunne holde.
    if t["bagud"] and not t["crawlerfiler"] and not t["kodefiler"]:
        # To målinger, der modsiger hinanden: der er commits bagud, men ingen
        # filer bagud. Det sker lovligt ved et merge-commit, hvis indhold vi
        # allerede har — men "ingen filer målt" må ikke oversættes til "kun
        # crawlerens filer". Samme regel som alle andre steder: en måling, der
        # ikke hænger sammen, er tvivl og ikke grønt lys.
        return 2, l + [
            f"❓ {t['bagud']} commits bagud, men fillisten er tom. De to tal",
            "   modsiger hinanden — typisk et merge-commit, hvis indhold vi",
            "   allerede har, men det kan ikke afgøres herfra.",
            "   Skriv det i loggen, og lad kode være.",
        ] + _uafhentet(t)

    if not t["hentede"]:
        # Intet at se på en cachet ref betyder ikke, at der intet er. Præcis
        # sådan så repoet ud i fjorten døgn. Men beskeden skal passe på det,
        # der faktisk står.
        if t["bagud"]:
            return 2, l + [
                f"❓ Cachen viser {t['bagud']} commits bagud, alle i crawlerens",
                f"   egne filer ({t['crawlerfiler']} stk.) — men uden en frisk",
                "   hentning kan det være flere, og kode kan være iblandt.",
                "   Skriv det i loggen, og lad kode være.",
            ] + _uafhentet(t)
        return 2, l + [
            "❓ Uden en frisk hentning kan 'ingenting bagud' ikke skelnes fra",
            "   'cachen er gammel'. Skriv det i loggen, og lad kode være.",
        ] + _uafhentet(t)

    if t["bagud"]:
        l.append(f"⚠️  {t['bagud']} commits bagud, men kun i crawlerens egne "
                 f"filer ({t['crawlerfiler']} stk.).")
        l.append("   Ufarligt at arbejde — men skriv tallet i loggen, og husk at")
        l.append("   dine tal fra `data/` er så gamle som den sidste hentning.")

    l += _uafhentet(t)

    if not l:
        l.append("✅ Mappen er den samme kode, som verden kører. Arbejd løs.")
    return 0, l


KENDTE_FLAG = {"--kun-cache"}


def main(argv: list[str] | None = None) -> int:
    """Hele kontrakten med arbejdsinstruksen ligger i returværdien her.

    `argv` kan gives med, så prøven kan kalde main() uden at rode med sys.argv.
    """
    argv = list(sys.argv[1:] if argv is None else argv)

    # Et ukendt flag må ikke accepteres tavst. `--cache-only` eller en tastefejl
    # i `--kun-cache` ville ellers udløse en fuld hentning — altså netop den
    # skrivning i `.git`, kalderen bad om at undgå — og se ud, som om alt gik
    # efter planen.
    ukendte = [a for a in argv if a not in KENDTE_FLAG]
    if ukendte:
        print(f"❓ Kender ikke flaget {' '.join(ukendte)}. "
              f"Kendte flag: {', '.join(sorted(KENDTE_FLAG))}.")
        return 2

    # REPO_ROD, ikke cwd. Se kommentaren ved konstanten.
    t = hent_tilstand(kun_cache="--kun-cache" in argv, rod=REPO_ROD)
    kode, linjer = doem(t)
    print("\n".join(linjer))
    return kode


if __name__ == "__main__":
    raise SystemExit(main())
