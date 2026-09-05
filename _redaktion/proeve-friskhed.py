#!/usr/bin/env python3
"""Prøver `er-repoet-friskt.py`.

To slags påstande, og skellet er med vilje:

* **Den rene halvdel** prøver `doem()` mod opdigtede tal. Ingen git.
* **Den beskidte halvdel** bygger rigtige, små git-repoer i `/tmp` med en lokal
  bare-remote — ingen netværk — og kører `hent_tilstand()` mod dem.

Den anden halvdel findes, fordi en gennemgang 14.08.2026 kørte 30 mutationer
mod den første udgave: alle 19 i `doem()` blev fanget, og **alle 10 i
`hent_tilstand()` slap igennem**. Man kunne få scriptet til aldrig at
klassificere nogen fil som kode, bytte om på "foran" og "bagud" eller koble
hentningen helt fra, og prøven blev grøn. Den halvdel, der afgør, om noget
overhovedet opdages, var uprøvet.

Prøven bygger og skriver kun i `/tmp`. I det repo, den startes fra, læser den —
og lægger en `__pycache__` ved siden af sig selv, som `.gitignore` allerede
dækker.

Kør: python3 _redaktion/proeve-friskhed.py
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sti = Path(__file__).with_name("er-repoet-friskt.py")
spec = importlib.util.spec_from_file_location("friskhed", sti)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

fejl: list[str] = []
antal = 0


def paastand(navn: str, sand: bool) -> None:
    global antal
    antal += 1
    if not sand:
        fejl.append(navn)


def tilstand(**kw) -> dict:
    """Et rent repo, som kaldet kan skubbe til felt for felt."""
    t = {"fejl": None, "hentede": True, "sprang_hentning": False,
         "bagud": 0, "foran": 0, "urene": 0, "kodefiler": [],
         "crawlerfiler": 0, "maalestok": "origin/main"}
    t.update(kw)
    return t


def tekst(t: dict) -> str:
    return "\n".join(m.doem(t)[1])


def kode(t: dict) -> int:
    return m.doem(t)[0]


# ==========================================================================
# DEL 1 — er_crawlerfil: hvad er crawlerens, og hvad er et menneskes
# ==========================================================================

for f in ("data/articles.json", "data/img/a.png", "artikel/abc.html",
          "video/x.html",
          "sitemap-artikler.xml", "sitemap-videoer.xml",
          "feed.xml", "feed-uge.xml",
          "uge.html"):
    paastand(f"{f} er crawlerens", m.er_crawlerfil(f))

# `sitemap.xml` UDEN bindestreg er håndholdt: 0 bot-commits mod 9 fra
# mennesker, filen siger det selv i sin egen kommentar, og
# `tjek_statisk_sitemap()` i crawler.py findes netop for at få en session til
# at rette den i hånden. Derfor `sitemap-` og ikke `sitemap` på listen.
paastand("sitemap.xml er IKKE crawlerens (vedligeholdes i hånden)",
         not m.er_crawlerfil("sitemap.xml"))

# Rod-XML-reglen har to krav, og begge skal prøves for sig.
paastand("robots.xml i roden er IKKE crawlerens (forkert præfiks)",
         not m.er_crawlerfil("robots.xml"))
paastand("noget.xml i roden er IKKE crawlerens (forkert præfiks)",
         not m.er_crawlerfil("noget.xml"))
paastand("feed-noter.txt er IKKE crawlerens (ikke .xml)",
         not m.er_crawlerfil("feed-noter.txt"))
paastand("sitemap-plan.md er IKKE crawlerens (ikke .xml)",
         not m.er_crawlerfil("sitemap-plan.md"))
paastand("feed.xml.gammel er IKKE crawlerens (endelsen skal være .xml)",
         not m.er_crawlerfil("feed.xml.gammel"))

for f in ("crawler.py", "index.html", "laer.html",
          "_redaktion/kontrolpanel.html", "_redaktion/arbejdsinstruks.md",
          ".github/workflows/crawl.yml"):
    paastand(f"{f} er IKKE crawlerens", not m.er_crawlerfil(f))

# `assets/` stod på crawlerlisten i den første udgave. Målt på origin er alle
# 9 commits i mappen fra mennesker (Torben 5, ntorsleff 4), og crawler.py
# skriver ingen steder i den — logo, favicons og fonts/skrifter.css er
# redaktionens egne filer. En forældet udgave af dem skal kunne stoppe.
for f in ("assets/ai-logo.png", "assets/Logo.png", "assets/og.png",
          "assets/fonts/skrifter.css"):
    paastand(f"{f} er IKKE crawlerens (redaktionens egen mappe)",
             not m.er_crawlerfil(f))

# `uge.html` skrives derimod af crawleren (UGE_HTML.write_text, to steder i
# crawler.py), 6 gange i de sidste 400 commits. Uden den på listen rammer et
# repo, der er halvandet døgn bagud på ren crawler-output, et falsk STOP.
paastand("uge.html i en undermappe er IKKE crawlerens",
         not m.er_crawlerfil("_gammelt/uge.html"))
paastand("uge.json i roden er IKKE crawlerens (kun det præcise filnavn)",
         not m.er_crawlerfil("uge.json"))
# `CRAWLER_ROD` sammenlignes med `==`, ikke `startswith`. Ellers ville enhver
# fil, der begynder med et af navnene, smutte med — og det er præcis den løse
# matchning, der gjorde `opsaetning/feeds.json` til crawlerens i første udgave.
paastand("uge.html.bak er IKKE crawlerens",
         not m.er_crawlerfil("uge.html.bak"))
paastand("uge.html-gammel er IKKE crawlerens",
         not m.er_crawlerfil("uge.html-gammel"))

# Gennemgangen 14.08 fandt en ægte kollision: den første udgave matchede
# præfikset "feed" mod filnavnet hvor som helst i træet, så `opsaetning/
# feeds.json` — kildelisten, redaktionen selv retter i hånden — blev talt som
# crawlerens og kunne derfor aldrig udløse et stop.
paastand("opsaetning/feeds.json er IKKE crawlerens",
         not m.er_crawlerfil("opsaetning/feeds.json"))
paastand("feedback.html er IKKE crawlerens",
         not m.er_crawlerfil("feedback.html"))
paastand("_redaktion/feed-regler.md er IKKE crawlerens",
         not m.er_crawlerfil("_redaktion/feed-regler.md"))
paastand("_redaktion/sitemap-tjek.py er IKKE crawlerens",
         not m.er_crawlerfil("_redaktion/sitemap-tjek.py"))
# Skråstregen er ikke pynt — og den skal prøves på HVER mappe på listen,
# ikke kun på én. Uden `videoguide.html` og `artikelliste.html` kunne
# skråstregen fjernes fra netop de to uden en rød påstand.
paastand("dataark.html er IKKE crawlerens", not m.er_crawlerfil("dataark.html"))
paastand("assets.py er IKKE crawlerens", not m.er_crawlerfil("assets.py"))
paastand("videoguide.html er IKKE crawlerens",
         not m.er_crawlerfil("videoguide.html"))
paastand("artikelliste.html er IKKE crawlerens",
         not m.er_crawlerfil("artikelliste.html"))
paastand("min-data/x.py er IKKE crawlerens", not m.er_crawlerfil("min-data/x.py"))
# Rod-reglen kræver BÅDE præfiks, .xml OG at filen ligger i roden.
paastand("feed.html i roden er IKKE crawlerens", not m.er_crawlerfil("feed.html"))
paastand("sitemap-noter.md er IKKE crawlerens",
         not m.er_crawlerfil("sitemap-noter.md"))
paastand("opsaetning/feeds.xml er IKKE crawlerens",
         not m.er_crawlerfil("opsaetning/feeds.xml"))
paastand("_redaktion/sitemap-tjek.xml er IKKE crawlerens",
         not m.er_crawlerfil("_redaktion/sitemap-tjek.xml"))
# Kravet `"/" not in sti` gør reelt kun en forskel for stier, der SELV
# begynder med "feed" eller "sitemap". Uden de to her kunne man slette det,
# uden at prøven sagde et ord.
paastand("feed-arkiv/gammel.xml er IKKE crawlerens",
         not m.er_crawlerfil("feed-arkiv/gammel.xml"))
paastand("sitemap-noter/udkast.xml er IKKE crawlerens",
         not m.er_crawlerfil("sitemap-noter/udkast.xml"))

# ==========================================================================
# DEL 2 — doem(): den rene vurdering
# ==========================================================================

# --- rent repo -------------------------------------------------------------
t = tilstand()
paastand("rent repo giver 0", kode(t) == 0)
paastand("rent repo siger arbejd løs", "Arbejd løs" in tekst(t))
paastand("rent repo advarer ikke", "⚠️" not in tekst(t))
paastand("rent repo stopper ikke", "🛑" not in tekst(t))

# --- kode bagud er den vigtigste regel: den SKAL stoppe --------------------
t = tilstand(bagud=86, kodefiler=["crawler.py", "index.html"], crawlerfiler=778)
paastand("kode bagud giver 1", kode(t) == 1)
paastand("kode bagud siger STOP", "🛑 STOP" in tekst(t))
paastand("kode bagud nævner antal commits", "86" in tekst(t))
paastand("kode bagud nævner filerne", "crawler.py" in tekst(t))
paastand("kode bagud nævner flettekonflikt", "flettekonflikt" in tekst(t))
paastand("kode bagud beder om GitHub Desktop", "GitHub Desktop" in tekst(t))
paastand("kode bagud beder om at slette låsefilen", ".koerer" in tekst(t))
paastand("kode bagud nævner målestokken", "origin/main" in tekst(t))

# Én enkelt kodefil er nok. Grænsen må ikke være "mange filer".
paastand("én kodefil bagud stopper også",
         kode(tilstand(bagud=1, kodefiler=["crawler.py"])) == 1)
paastand("2 commits + kodefil stopper",
         kode(tilstand(bagud=2, kodefiler=["laer.html"], crawlerfiler=0)) == 1)

# Kodefiler uden commit-tal: gennemgangen fandt, at `if kodefiler and bagud`
# ville se rigtigt ud og lukke hullet i punkt 2 op igen.
paastand("kodefiler stopper også når bagud=0",
         kode(tilstand(bagud=0, kodefiler=["crawler.py"])) == 1)

# Lang filliste skal forkortes, ikke fylde skærmen.
t = tilstand(bagud=9, kodefiler=[f"fil{i}.html" for i in range(20)])
paastand("lang filliste forkortes med …", "…" in tekst(t))
paastand("lang filliste tæller alle 20", "20 af de" in tekst(t))

# Den værste kombination — kode bagud OG eget uafhentet arbejde — skal nævne
# begge dele. Den tidlige return fortiede den ene halvdel.
t = tilstand(bagud=5, kodefiler=["crawler.py"], foran=2, urene=3)
paastand("kode bagud + uafhentet nævner STOP", "🛑 STOP" in tekst(t))
paastand("kode bagud + uafhentet nævner uafhentet",
         "Uafhentet arbejde" in tekst(t))
paastand("kode bagud + uafhentet nævner begge tal",
         "2 commits foran" in tekst(t) and "3 ændrede filer" in tekst(t))

# --- kun crawlerfiler bagud: advar, men lad arbejde ------------------------
t = tilstand(bagud=5, crawlerfiler=40)
paastand("få crawlercommits giver 0", kode(t) == 0)
paastand("få crawlercommits advarer", "⚠️" in tekst(t))
paastand("få crawlercommits nævner tallet", "5 commits bagud" in tekst(t))
paastand("få crawlercommits stopper ikke", "🛑" not in tekst(t))

# --- for mange crawlercommits: data er ikke tal længere --------------------
t = tilstand(bagud=13, crawlerfiler=300)
paastand("13 commits over grænsen stopper", kode(t) == 1)
paastand("13 commits nævner grænsen", "12" in tekst(t))
paastand("13 commits siger ingen kodekonflikt", "kodekonflikt" in tekst(t))
paastand("12 commits er præcis på grænsen og går an",
         kode(tilstand(bagud=12, crawlerfiler=300)) == 0)
paastand("maks_bagud kan sættes ned",
         m.doem(tilstand(bagud=11, crawlerfiler=9), maks_bagud=10)[0] == 1)
paastand("maks_bagud kan sættes op",
         m.doem(tilstand(bagud=100, crawlerfiler=9), maks_bagud=200)[0] == 0)
paastand("over grænsen nævner også uafhentet arbejde",
         "Uafhentet" in tekst(tilstand(bagud=99, crawlerfiler=99, foran=1)))

# --- uafhentet arbejde: den retning fase 0 allerede kendte ----------------
t = tilstand(foran=3)
paastand("commits foran giver 0", kode(t) == 0)
paastand("commits foran advarer", "Uafhentet arbejde" in tekst(t))
paastand("commits foran skal øverst i loggen", "ØVERST" in tekst(t))
paastand("commits foran stopper IKKE", "🛑" not in tekst(t))

t = tilstand(urene=7)
paastand("ændrede filer advarer", "Uafhentet arbejde" in tekst(t))
paastand("ændrede filer nævner tallet", "7 ændrede filer" in tekst(t))

paastand("bagud og urent nævnes begge",
         "6 commits bagud" in tekst(tilstand(bagud=6, crawlerfiler=6, urene=2))
         and "Uafhentet" in tekst(tilstand(bagud=6, crawlerfiler=6, urene=2)))

# --- kunne ikke hente: tvivl er ikke grønt lys ----------------------------
# Den her regel er hele grunden til, at gennemgangen 14.08 blev kørt igen.
# Første udgave svarede 0 = "arbejd løs", når fetch fejlede — og en gammel
# cachet ref siger naturligvis "0 bagud". Præcis 14.08-situationen.
t = tilstand(hentede=False)
paastand("uden fetch advares der", "MINIMUM" in tekst(t))
paastand("uden fetch og intet bagud giver 2, ikke 0", kode(t) == 2)
paastand("uden fetch siger IKKE arbejd løs", "Arbejd løs" not in tekst(t))
paastand("uden fetch forklarer hvorfor tvivlen tæller",
         "cachen er gammel" in tekst(t))
paastand("mislykket fetch hedder 'Kunne ikke'", "Kunne ikke hente" in tekst(t))
paastand("mislykket fetch hedder ikke 'sprang over'",
         "Sprang hentningen over" not in tekst(t))
paastand("uden fetch nævner stadig uafhentet arbejde",
         "Uafhentet" in tekst(tilstand(hentede=False, foran=2)))

# Den kombination, hele scriptet findes for: hentningen fejlede, OG cachen
# viser allerede commits bagud. Uden de her påstande kunne porten snævres til
# `if not hentede and not bagud`, og et repo med en mislykket fetch og fem
# commits bagud ville få "Ufarligt at arbejde" — 14.08-fejlen genindført.
t = tilstand(hentede=False, bagud=5, crawlerfiler=40)
paastand("uden fetch + commits bagud giver 2, ikke 0", kode(t) == 2)
paastand("uden fetch + commits bagud siger ikke 'Ufarligt'",
         "Ufarligt" not in tekst(t))
paastand("uden fetch + commits bagud siger ikke arbejd løs",
         "Arbejd løs" not in tekst(t))
paastand("uden fetch + commits bagud nævner det rigtige tal",
         "5 commits bagud" in tekst(t))
paastand("uden fetch + commits bagud indrømmer at der kan være flere",
         "kan det være flere" in tekst(t))

# Over grænsen skal svaret være 1 — også når hentningen fejlede. Samme
# argument som ved kodefiler: tallet kan kun blive større af en frisk
# hentning, aldrig mindre. Lå grænsen efter cache-porten, ville et
# netværksudfald have gjort 14.08 til et roligt "2 — lad kode være", og
# sessionen ville have målt løs på et fjorten dage gammelt `data/`. Det er
# den ene ting, grænsen findes for at forbyde.
t = tilstand(hentede=False, bagud=200, crawlerfiler=900)
paastand("uden fetch + langt over grænsen giver 1, ikke 2", kode(t) == 1)
paastand("uden fetch + langt over grænsen siger STOP", "🛑 STOP" in tekst(t))
paastand("uden fetch + langt over grænsen nævner tallet",
         "200 commits bagud" in tekst(t))
paastand("uden fetch + langt over grænsen spørger ikke om der er noget",
         "ingenting bagud" not in tekst(t))
paastand("uden fetch + langt over grænsen nævner grænsen", "12" in tekst(t))
paastand("uden fetch + langt over grænsen beholder MINIMUM-forbeholdet",
         "MINIMUM" in tekst(t))
paastand("uden fetch + langt over grænsen beder om at slette låsefilen",
         "låsefil" in tekst(t))
paastand("over grænsen MED fetch siger også STOP og slet låsefil",
         "🛑 STOP" in tekst(tilstand(bagud=200, crawlerfiler=900))
         and "låsefil" in tekst(tilstand(bagud=200, crawlerfiler=900)))
paastand("over grænsen nævner uafhentet arbejde",
         "Uafhentet" in tekst(tilstand(hentede=False, bagud=200,
                                       crawlerfiler=900, foran=1)))

# --- commits bagud, men tom filliste: to målinger der modsiger hinanden ---
# `kodefiler == []` må ikke oversættes til "kun crawlerens filer", når der
# heller ikke blev målt nogen crawlerfiler. Så er der ikke målt noget.
t = tilstand(bagud=3, kodefiler=[], crawlerfiler=0)
paastand("bagud + tom filliste giver 2, ikke 0", kode(t) == 2)
paastand("bagud + tom filliste siger ikke 'kun i crawlerens egne filer'",
         "kun i crawlerens egne filer" not in tekst(t))
paastand("bagud + tom filliste siger ikke 'Ufarligt'", "Ufarligt" not in tekst(t))
paastand("bagud + tom filliste siger at tallene modsiger hinanden",
         "modsiger hinanden" in tekst(t))
paastand("bagud + tom filliste påstår ikke '(0 stk.)'",
         "(0 stk.)" not in tekst(t))
# ... men er der målt crawlerfiler, er det den normale, ufarlige hverdag.
paastand("bagud + målte crawlerfiler giver 0",
         kode(tilstand(bagud=3, crawlerfiler=9)) == 0)

# Remoten skal nævnes ved navn — ikke altid "origin".
paastand("mislykket hentning nævner den rigtige remote",
         "Kunne ikke hente fra andet" in
         tekst(tilstand(hentede=False, maalestok="andet/main")))
paastand("mislykket hentning siger origin, når det ER origin",
         "Kunne ikke hente fra origin" in tekst(tilstand(hentede=False)))

# --kun-cache er ikke en fejl, og må ikke skrives som en.
t = tilstand(hentede=False, sprang_hentning=True)
paastand("--kun-cache siger sprang over", "Sprang hentningen over" in tekst(t))
paastand("--kun-cache siger IKKE 'kunne ikke'",
         "Kunne ikke hente" not in tekst(t))
paastand("--kun-cache advarer stadig om MINIMUM", "MINIMUM" in tekst(t))
paastand("--kun-cache giver også 2 på et tilsyneladende rent repo",
         kode(t) == 2)

# Men ser vi kodefiler bagud selv på en gammel cache, er STOP rigtigt:
# tallet kan kun blive værre.
t = tilstand(hentede=False, bagud=86, kodefiler=["crawler.py"])
paastand("uden fetch stopper kode bagud stadig (1, ikke 2)", kode(t) == 1)
# ... og med et commit-tal UNDER grænsen, så påstanden ikke bare er
# grænse-reglen forklædt. `bagud=86` er over 12 og giver 1 helt uden
# kodefiler — så den ovenstående påstand alene ville lade kodefil-porten
# blive `if kodefiler and t["hentede"]` uden en rød.
t = tilstand(hentede=False, bagud=3, kodefiler=["crawler.py"])
paastand("uden fetch + få commits: kodefiler stopper stadig", kode(t) == 1)
paastand("uden fetch + få commits: siger STOP", "🛑 STOP" in tekst(t))
paastand("uden fetch + få commits: nævner flettekonflikt",
         "flettekonflikt" in tekst(t))
paastand("uden fetch + kodefiler uden commits talt: stopper også",
         kode(tilstand(hentede=False, bagud=0, kodefiler=["crawler.py"])) == 1)

# Modsigelsen skal opdages FØR cache-porten — ellers påstår teksten
# "alle i crawlerens egne filer (0 stk.)" om en måling, der ikke findes.
t = tilstand(hentede=False, bagud=3, crawlerfiler=0, kodefiler=[])
paastand("uden fetch + tom filliste giver 2", kode(t) == 2)
paastand("uden fetch + tom filliste påstår ikke '(0 stk.)'",
         "(0 stk.)" not in tekst(t))
paastand("uden fetch + tom filliste siger ikke 'kun i crawlerens'",
         "alle i crawlerens" not in tekst(t))
paastand("uden fetch + tom filliste siger at tallene modsiger hinanden",
         "modsiger hinanden" in tekst(t))
_t = tekst(tilstand(hentede=False, bagud=86, kodefiler=["crawler.py"]))
paastand("uden fetch står forbeholdet før STOP",
         "MINIMUM" in _t and "🛑" in _t and _t.index("MINIMUM") < _t.index("🛑"))

# --- fejl: hverken god eller dårlig, men ikke tavs ------------------------
t = tilstand(fejl="kender ikke origin/main")
paastand("fejl giver 2", kode(t) == 2)
paastand("fejl gentager grunden", "origin/main" in tekst(t))
paastand("fejl siger ikke arbejd løs", "Arbejd løs" not in tekst(t))
paastand("fejl vinder over alt andet",
         kode(tilstand(fejl="x", bagud=99, kodefiler=["crawler.py"])) == 2)

# ==========================================================================
# DEL 3 — hent_tilstand() mod rigtige git-repoer i /tmp
# ==========================================================================

ARB = Path(tempfile.mkdtemp(prefix="friskhed-proeve-"))


# Testrepoerne skal ikke kunne vælte af, hvad der tilfældigvis står i
# brugerens globale gitconfig. `commit.gpgsign = true` er udbredt, og uden den
# her isolering døde prøven i afsnit A med en nøgen CalledProcessError, som
# ligner en fejl i det script, der prøves. Det ville koste nogen en time.
GIT_MILJOE = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "proeve", "GIT_AUTHOR_EMAIL": "p@p",
    "GIT_COMMITTER_NAME": "proeve", "GIT_COMMITTER_EMAIL": "p@p",
}


def sh(*args: str, cwd: Path) -> None:
    # stderr fanges og kommer med ud i undtagelsen — en tavs exit 128 siger
    # ikke, hvad der gik galt.
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       env=GIT_MILJOE)
    if p.returncode != 0:
        raise RuntimeError(
            f"git fejlede i prøvens opsætning: {' '.join(args)}\n"
            f"  i {cwd}\n  {(p.stderr or p.stdout).strip()[:400]}")


def byg(navn: str) -> tuple[Path, Path]:
    """En bar 'origin' med ét commit, og en klon af den. Ingen netværk."""
    bar = ARB / f"{navn}.git"
    arbejde = ARB / navn
    sh("git", "init", "--bare", "-b", "main", str(bar), cwd=ARB)
    sh("git", "clone", str(bar), str(arbejde), cwd=ARB)
    for n, v in (("user.email", "p@p"), ("user.name", "proeve")):
        sh("git", "config", n, v, cwd=arbejde)
    (arbejde / "crawler.py").write_text("# start\n")
    (arbejde / "data").mkdir()
    (arbejde / "data" / "articles.json").write_text("{}\n")
    sh("git", "add", "-A", cwd=arbejde)
    sh("git", "commit", "-m", "start", cwd=arbejde)
    sh("git", "push", "-u", "origin", "main", cwd=arbejde)
    return bar, arbejde


def commit_paa_origin(bar: Path, navn: str, filer: dict[str, str]) -> None:
    """Læg et commit på 'origin' uden om arbejdsmappen — som Actions gør."""
    spejl = ARB / f"_spejl-{navn}"
    shutil.rmtree(spejl, ignore_errors=True)
    sh("git", "clone", str(bar), str(spejl), cwd=ARB)
    for n, v in (("user.email", "p@p"), ("user.name", "proeve")):
        sh("git", "config", n, v, cwd=spejl)
    for rel, indhold in filer.items():
        f = spejl / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(indhold)
    sh("git", "add", "-A", cwd=spejl)
    sh("git", "commit", "-m", "fra actions", cwd=spejl)
    sh("git", "push", "origin", "main", cwd=spejl)


def i(mappe: Path, **kw) -> dict:
    """Kør hent_tilstand i en bestemt mappe."""
    hjem = Path.cwd()
    gammelt = {n: os.environ.get(n) for n in GIT_MILJOE}
    try:
        os.chdir(mappe)
        os.environ.update(GIT_MILJOE)
        return m.hent_tilstand(**kw)
    finally:
        os.chdir(hjem)
        for n, v in gammelt.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v


def som_proces(mappe: Path, *flag: str, fra: Path | None = None) -> tuple[int, str]:
    """Kør scriptet som en rigtig proces mod `mappe` og aflæs udgangskoden.

    Instruksen bygger på præcis den kode. Uden det her kunne `main()` slutte
    med `return 0` i stedet for `return kode`, og alle påstande ville stadig
    være grønne — mens scriptet svarede "arbejd løs" på 87 commits bagud.

    Scriptet forankrer sig i sin EGEN mappe (`REPO_ROD = __file__/../..`), så
    en kopi lægges ind i testrepoets `_redaktion/`. Det er ikke en omvej — det
    er selve pointen: `cwd` må ikke kunne afgøre, hvilket repo der måles.
    `fra` er den mappe, processen startes i, og skal være uden betydning.
    """
    maal = mappe / "_redaktion" / sti.name
    maal.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(sti, maal)
    p = subprocess.run([sys.executable, str(maal), *flag],
                       cwd=(fra or mappe), capture_output=True, text=True,
                       env=GIT_MILJOE)
    return p.returncode, p.stdout + p.stderr


try:
    # --- A. lokal = remote ------------------------------------------------
    bar, rep = byg("rent")
    rep_rent = rep
    t = i(rep)
    paastand("[repo] rent: ingen fejl", t["fejl"] is None)
    paastand("[repo] rent: hentede", t["hentede"] is True)
    paastand("[repo] rent: 0 bagud, 0 foran",
             t["bagud"] == 0 and t["foran"] == 0)
    paastand("[repo] rent: ingen kodefiler", t["kodefiler"] == [])
    paastand("[repo] rent: dømmes 0", m.doem(t)[0] == 0)
    paastand("[repo] rent: fandt en målestok", bool(t["maalestok"]))

    # --- B. kun crawlerens filer bagud ------------------------------------
    bar, rep = byg("data-bagud")
    commit_paa_origin(bar, "data-bagud", {"data/articles.json": '{"n":1}\n'})
    t = i(rep)
    paastand("[repo] data bagud: 1 bagud", t["bagud"] == 1)
    paastand("[repo] data bagud: 0 kodefiler", t["kodefiler"] == [])
    paastand("[repo] data bagud: 1 crawlerfil", t["crawlerfiler"] == 1)
    paastand("[repo] data bagud: dømmes 0", m.doem(t)[0] == 0)
    # "1 commit bagud" er den tilstand, scriptet oftest møder — ca. 6 gange i
    # døgnet. Uden en påstand på selve teksten kunne advarslen blive
    # `if t["bagud"] > 1`, og den hyppigste tilstand ville få et tavst
    # "✅ Mappen er den samme kode, som verden kører".
    linjer = "\n".join(m.doem(t)[1])
    paastand("[repo] data bagud: advarer i teksten", "⚠️" in linjer)
    paastand("[repo] data bagud: nævner tallet", "1 commits bagud" in linjer)
    paastand("[repo] data bagud: nævner antal crawlerfiler", "(1 stk.)" in linjer)
    paastand("[repo] data bagud: siger IKKE at alt er som verden kører",
             "samme kode, som verden kører" not in linjer)

    # Og med FLERE crawlerfiler, så tallet i "(N stk.)" ikke bare kan være et
    # hårdkodet 1-tal. Afsnit C2 har flere filer, men rammer STOP-grenen —
    # den her advarsels-gren har sit eget tal.
    commit_paa_origin(bar, "data-bagud", {
        "data/uge.json": "{}\n", "artikel/en.html": "<p>1\n",
        "video/to.html": "<p>2\n", "feed.xml": "<rss/>\n",
        "sitemap-artikler.xml": "<urlset/>\n",
    })
    t = i(rep)
    paastand("[repo] flere crawlerfiler: stadig 0 kodefiler", t["kodefiler"] == [])
    paastand("[repo] flere crawlerfiler: 6 talt", t["crawlerfiler"] == 6)
    linjer = "\n".join(m.doem(t)[1])
    paastand("[repo] flere crawlerfiler: tallet i teksten er 6",
             "(6 stk.)" in linjer)
    paastand("[repo] flere crawlerfiler: 2 commits bagud",
             "2 commits bagud" in linjer)
    paastand("[repo] flere crawlerfiler: dømmes stadig 0", m.doem(t)[0] == 0)

    # --- C. kode bagud ----------------------------------------------------
    bar, rep = byg("kode-bagud")
    commit_paa_origin(bar, "kode-bagud",
                      {"crawler.py": "# nyt\n", "data/articles.json": '{"n":2}\n'})
    t = i(rep)
    paastand("[repo] kode bagud: 1 bagud", t["bagud"] == 1)
    paastand("[repo] kode bagud: crawler.py er kode",
             t["kodefiler"] == ["crawler.py"])
    paastand("[repo] kode bagud: data tælles for sig", t["crawlerfiler"] == 1)
    paastand("[repo] kode bagud: dømmes 1", m.doem(t)[0] == 1)

    # Og som proces, for det er udgangskoden, instruksen handler om.
    rc, ud = som_proces(rep)
    paastand("[proces] kode bagud giver exit 1", rc == 1)
    paastand("[proces] kode bagud skriver STOP", "🛑 STOP" in ud)
    paastand("[proces] rent repo giver exit 0", som_proces(rep_rent)[0] == 0)
    paastand("[proces] rent repo skriver noget", som_proces(rep_rent)[1].strip() != "")
    rc, ud = som_proces(rep, "--vrøvl")
    paastand("[proces] ukendt flag giver exit 2", rc == 2)
    paastand("[proces] ukendt flag nævner flaget", "--vrøvl" in ud)
    paastand("[proces] ukendt flag henter ikke", "STOP" not in ud)
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()) as tavs:
        _kode = m.main(["--kun-cache", "--også-vrøvl"])
    paastand("[main] ukendt flag vinder over kendt flag", _kode == 2)
    paastand("[main] ukendt flag nævnes i beskeden",
             "--også-vrøvl" in tavs.getvalue())

    # --- C2. FLERE filer ad gangen: tallene i beskeden skal passe ---------
    # Uden det her overlever `crawlerfiler = 1` og "gem kun den første
    # kodefil": alle testrepoer havde præcis én fil af hver slags, så en
    # optælling, der altid svarer 1, ville se rigtig ud.
    bar, rep = byg("flere")
    commit_paa_origin(bar, "flere", {
        "crawler.py": "# a\n", "index.html": "<p>b\n", "laer.html": "<p>c\n",
        "om.html": "<p>d\n", "faq.html": "<p>e\n", "quiz.html": "<p>f\n",
        "ordbog.html": "<p>g\n",
        "data/articles.json": '{"n":3}\n', "data/uge.json": "{}\n",
        "artikel/en.html": "<p>1\n", "video/to.html": "<p>2\n",
    })
    t = i(rep)
    paastand("[repo] flere: 7 kodefiler talt", len(t["kodefiler"]) == 7)
    paastand("[repo] flere: 4 crawlerfiler talt", t["crawlerfiler"] == 4)
    linjer = "\n".join(m.doem(t)[1])
    paastand("[repo] flere: beskeden siger 7", "7 af de" in linjer)
    paastand("[repo] flere: beskeden forkorter listen", "…" in linjer)
    paastand("[repo] flere: crawlerfiler er ikke med i kodelisten",
             "articles.json" not in linjer and "artikel/" not in linjer)
    # Forkortelsen skal vise seks navne, ikke ét. Uden den her kunne
    # `kodefiler[:6]` blive `[:1]`, og beskeden ville stadig have både tallet
    # og prikkerne — men kun fortælle om én af de syv filer.
    paastand("[repo] flere: beskeden nævner seks filnavne",
             sum(1 for n in t["kodefiler"] if n in linjer) == 6)

    # --- D. FORAN, ikke bagud ---------------------------------------------
    # Gennemgangen 14.08: en to-punkts-diff gav her "STOP, crawler.py er bagud"
    # på et repo, der var 1 FORAN — og rådet "træk ned" kunne ikke fjerne det,
    # for commit'et manglede på origin. En dødlås, der spærrede alle sessioner.
    bar, rep = byg("foran")
    (rep / "crawler.py").write_text("# min egen rettelse\n")
    sh("git", "add", "-A", cwd=rep)
    sh("git", "commit", "-m", "min rettelse", cwd=rep)
    t = i(rep)
    paastand("[repo] foran: 1 foran, 0 bagud",
             t["foran"] == 1 and t["bagud"] == 0)
    paastand("[repo] foran: INGEN kodefiler bagud", t["kodefiler"] == [])
    paastand("[repo] foran: dømmes 0, ikke 1", m.doem(t)[0] == 0)
    paastand("[repo] foran: siger uafhentet arbejde",
             "Uafhentet" in "\n".join(m.doem(t)[1]))
    paastand("[repo] foran: siger IKKE træk ned",
             "GitHub Desktop" not in "\n".join(m.doem(t)[1]))

    # --- E. foran OG bagud på kode ----------------------------------------
    commit_paa_origin(bar, "foran", {"index.html": "<p>nyt\n"})
    t = i(rep)
    paastand("[repo] foran+bagud: 1 foran og 1 bagud",
             t["foran"] == 1 and t["bagud"] == 1)
    paastand("[repo] foran+bagud: kun deres fil er bagud",
             t["kodefiler"] == ["index.html"])
    linjer = "\n".join(m.doem(t)[1])
    paastand("[repo] foran+bagud: dømmes 1", m.doem(t)[0] == 1)
    paastand("[repo] foran+bagud: nævner begge retninger",
             "index.html" in linjer and "Uafhentet" in linjer)

    # --- F. ucommitterede ændringer, og .koerer skal ikke tælle -----------
    bar, rep = byg("urent")
    (rep / "crawler.py").write_text("# rodet til\n")
    (rep / "_redaktion").mkdir()
    (rep / "_redaktion" / ".koerer").write_text("2026-08-14T03:22:21+02:00\n")
    t = i(rep)
    paastand("[repo] urent: 1 uren fil", t["urene"] == 1)
    paastand("[repo] urent: .koerer tæller ikke med", t["urene"] == 1)
    paastand("[repo] urent: advarer om uafhentet",
             "Uafhentet" in "\n".join(m.doem(t)[1]))

    # --- G. mange crawlercommits ------------------------------------------
    bar, rep = byg("mange")
    for n in range(14):
        commit_paa_origin(bar, "mange", {"data/articles.json": '{"n":%d}\n' % n})
    t = i(rep)
    paastand("[repo] mange: 14 bagud", t["bagud"] == 14)
    paastand("[repo] mange: stadig 0 kodefiler", t["kodefiler"] == [])
    paastand("[repo] mange: dømmes 1 (over grænsen på 12)", m.doem(t)[0] == 1)

    # --- H. --kun-cache henter ikke ---------------------------------------
    bar, rep = byg("cache")
    commit_paa_origin(bar, "cache", {"crawler.py": "# nyt\n"})
    t = i(rep, kun_cache=True)
    paastand("[repo] kun-cache: sprang_hentning er sat",
             t["sprang_hentning"] is True)
    paastand("[repo] kun-cache: hentede er falsk", t["hentede"] is False)
    paastand("[repo] kun-cache: ser ikke det uhentede commit", t["bagud"] == 0)
    paastand("[repo] kun-cache: dømmes 2, ikke 0", m.doem(t)[0] == 2)
    # ... og med hentning ser den det.
    t = i(rep)
    paastand("[repo] med hentning ses commit'et", t["bagud"] == 1)
    paastand("[repo] med hentning dømmes 1", m.doem(t)[0] == 1)

    # --- I. ingen upstream -------------------------------------------------
    tom = ARB / "uden-remote"
    tom.mkdir()
    sh("git", "init", "-b", "main", ".", cwd=tom)
    for n, v in (("user.email", "p@p"), ("user.name", "proeve")):
        sh("git", "config", n, v, cwd=tom)
    (tom / "a.txt").write_text("a\n")
    sh("git", "add", "-A", cwd=tom)
    sh("git", "commit", "-m", "en", cwd=tom)
    t = i(tom)
    paastand("[repo] uden upstream: sætter fejl", t["fejl"] is not None)
    paastand("[repo] uden upstream: dømmes 2", m.doem(t)[0] == 2)
    # Fejlteksten skal sige, hvad der faktisk manglede. Falder scriptet tilbage
    # på et hårdkodet origin/main, bliver udfaldet det samme (2), men beskeden
    # bliver "kunne ikke tælle commits" — og så leder nogen efter en tællefejl
    # i stedet for en manglende upstream. Punkt 5 i målestokken.
    # Den rigtige påstand er, at målestokken IKKE blev fundet. At lede efter
    # ordet "upstream" i fejlteksten passerer også, når scriptet falder tilbage
    # på et hårdkodet origin/main — fordi git's egen fejl tilfældigvis
    # indeholder ordet.
    paastand("[repo] uden upstream: fandt ingen målestok",
             t["maalestok"] is None)
    paastand("[repo] uden upstream: fejlteksten nævner upstream",
             "upstream" in (t["fejl"] or ""))

    # --- I2. fallbacken til origin/main, når branchen ingen upstream har ---
    # Den gren bruges ved detached HEAD (under en rebase) og på grene, ingen
    # har sat op. Uden det her kunne hele løkken slettes, uden at prøven
    # sagde et ord — alle andre testrepoer har en upstream.
    bar, rep = byg("uden-upstream")
    sh("git", "branch", "--unset-upstream", "main", cwd=rep)
    t = i(rep)
    paastand("[repo] uden branch-upstream: falder tilbage på origin/main",
             t["maalestok"] == "origin/main")
    paastand("[repo] uden branch-upstream: ingen fejl", t["fejl"] is None)
    paastand("[repo] uden branch-upstream: dømmes 0", m.doem(t)[0] == 0)
    commit_paa_origin(bar, "uden-upstream", {"crawler.py": "# nyt\n"})
    t = i(rep)
    paastand("[repo] uden branch-upstream: ser stadig kode bagud",
             t["kodefiler"] == ["crawler.py"])

    # Fallbacken skal også være forankret. Målt fra `tom`, som er et git-repo
    # HELT uden remote: glemmer `find_maalestok` sit `rod=` i fallback-kaldet,
    # leder den efter origin/main i `tom`, finder ingen og svarer 2 — mens det
    # repo, der faktisk skulle måles, har en udmærket origin/main.
    hjem = Path.cwd()
    try:
        os.chdir(tom)
        t_fjern = m.hent_tilstand(kun_cache=True, rod=rep)
    finally:
        os.chdir(hjem)
    paastand("[forankring] fallback bruger rod og ikke cwd",
             t_fjern["maalestok"] == "origin/main")
    paastand("[forankring] fallback fra fremmed cwd giver ingen fejl",
             t_fjern["fejl"] is None)

    # --- J. slet ikke et git-repo -----------------------------------------
    ikke = ARB / "ikke-git"
    ikke.mkdir()
    t = i(ikke)
    paastand("[repo] ikke git: sætter fejl", t["fejl"] == "ikke et git-repo")
    paastand("[repo] ikke git: dømmes 2", m.doem(t)[0] == 2)

    # --- K. fetch FEJLER: den vigtigste fail-open-vej ---------------------
    # Punkt 1 i gennemgangen 14.08. Kan vi ikke nå origin, ser et forældet repo
    # ud som et rent repo, og første udgave svarede "arbejd løs". Her rives
    # remoten væk, efter klonen er lavet.
    bar, rep = byg("doed-remote")
    commit_paa_origin(bar, "doed-remote", {"crawler.py": "# nyt\n"})
    shutil.rmtree(bar)                     # origin kan ikke nås længere
    # Den lokale `origin/main`-ref bliver stående og peger på start-commit'et,
    # så målestokken FINDES — den er bare gammel. Det er hele pointen: sådan så
    # repoet ud i fjorten døgn. Ref'en må ikke slettes her; gør man det, fejler
    # `find_maalestok()`, hent_tilstand returnerer på fejl-grenen, og
    # påstanden om `hentede` beviser ingenting.
    t = i(rep)
    paastand("[repo] død remote: ingen fejl — målestokken findes",
             t["fejl"] is None)
    paastand("[repo] død remote: hentede er falsk", t["hentede"] is False)
    paastand("[repo] død remote: den gamle cache ser rent ud", t["bagud"] == 0)
    paastand("[repo] død remote: dømmes 2, ikke 0", m.doem(t)[0] == 2)
    paastand("[repo] død remote: siger ikke arbejd løs",
             "Arbejd løs" not in "\n".join(m.doem(t)[1]))
    paastand("[repo] død remote: kalder det en mislykket hentning",
             "Kunne ikke hente" in "\n".join(m.doem(t)[1]))

    # ... og --kun-cache må ikke bare give samme svar ved et tilfælde: den skal
    # kunne ses på beskeden, at hentningen blev sprunget over med vilje.
    rc, ud = som_proces(rep, "--kun-cache")
    paastand("[proces] --kun-cache springer hentningen over",
             "Sprang hentningen over" in ud)
    paastand("[proces] --kun-cache kalder det ikke en fejl",
             "Kunne ikke hente" not in ud)
    paastand("[proces] --kun-cache giver også 2 her", rc == 2)
    rc, ud = som_proces(rep)
    paastand("[proces] uden flag forsøges hentningen",
             "Kunne ikke hente" in ud)

    # --- L. en delmåling fejler: skal give 2, ikke stiltiende 0 -----------
    # Punkt 4 i gennemgangen: fejlede `git diff` eller `git status` blev
    # ignoreret, og scriptet svarede "Ufarligt at arbejde (0 stk.)" om et repo,
    # hvor crawler.py var 90 commits bagud. Det kan kun prøves ved at få netop
    # ét kald til at fejle, så her byttes `koer` ud et øjeblik.
    bar, rep = byg("delfejl")
    commit_paa_origin(bar, "delfejl", {"data/articles.json": '{"n":9}\n'})
    ægte = m.koer
    for spærret, navn in (("diff", "git diff"), ("status", "git status")):
        def falsk(args, timeout=30, rod=None, _s=spærret):
            if args and args[0] == _s:
                return 128, "", "fatal: opdigtet fejl"
            return ægte(args, timeout, rod)
        m.koer = falsk
        try:
            t = i(rep)
        finally:
            m.koer = ægte
        paastand(f"[repo] {navn} fejler: sætter fejl", t["fejl"] is not None)
        paastand(f"[repo] {navn} fejler: dømmes 2", m.doem(t)[0] == 2)
        paastand(f"[repo] {navn} fejler: siger ikke 'Ufarligt at arbejde'",
                 "Ufarligt" not in "\n".join(m.doem(t)[1]))

    # `rev-list` har sin egen fejlvej og sin egen ValueError-vagt. Begge kunne
    # fjernes uden en rød påstand, fordi afsnittet ovenfor kun spærrer `diff`
    # og `status`.
    def rev_fejler(args, timeout=30, rod=None):
        if args and args[0] == "rev-list":
            return 128, "", "fatal: opdigtet"
        return ægte(args, timeout, rod)

    def rev_vrøvler(args, timeout=30, rod=None):
        if args and args[0] == "rev-list":
            return 0, "ikke-tal-her\n", ""
        return ægte(args, timeout, rod)

    def rev_tavs(args, timeout=30, rod=None):
        # Exit 0 og TOM stdout. Klares i dag af udpakningen, men en
        # "hjælpsom" rettelse som `(ud.split() + ["0","0"])[:2]` ville gøre
        # scriptet fail-open: bagud=0 → "✅ Arbejd løs".
        if args and args[0] == "rev-list":
            return 0, "", ""
        return ægte(args, timeout, rod)

    for falsk_rev, navn in ((rev_fejler, "rev-list fejler"),
                            (rev_vrøvler, "rev-list svarer vrøvl"),
                            (rev_tavs, "rev-list svarer tomt")):
        m.koer = falsk_rev
        try:
            t = i(rep)
        finally:
            m.koer = ægte
        paastand(f"[repo] {navn}: sætter fejl", t["fejl"] is not None)
        paastand(f"[repo] {navn}: dømmes 2", m.doem(t)[0] == 2)
        paastand(f"[repo] {navn}: siger ikke arbejd løs",
                 "Arbejd løs" not in "\n".join(m.doem(t)[1]))

    # stderr må ikke limes på stdout og parses som filnavne. En git-advarsel
    # ville ellers blive talt som en KODE-fil — et opdigtet filnavn i
    # STOP-beskeden — eller som en ekstra ændret fil, der ikke findes.
    def med_stoej(args, timeout=30, rod=None):
        kode_, ud_, fejl_ = ægte(args, timeout, rod)
        if args and args[0] in ("diff", "status"):
            return kode_, ud_, "warning: could not open directory 'x/'\n"
        return kode_, ud_, fejl_

    m.koer = med_stoej
    try:
        t = i(rep)
    finally:
        m.koer = ægte
    paastand("[repo] stderr-støj tælles ikke som en kodefil",
             t["kodefiler"] == [])
    paastand("[repo] stderr-støj tælles ikke som en crawlerfil",
             t["crawlerfiler"] == 1)
    paastand("[repo] stderr-støj tælles ikke som en ændret fil",
             t["urene"] == 0)

    # --- M. koer() skal altid sende de to flag, der beskytter redaktionen --
    # `--no-optional-locks` er ikke pynt: uden det efterlader git en
    # `.git/index.lock`, og så kan redaktionen ikke committe i GitHub Desktop.
    # Det har generet fire gange. Udfaldet af scriptet ændrer sig ikke, hvis
    # flaget fjernes — kun bivirkningen — så det skal prøves direkte.
    set_args: list[list[str]] = []
    ægte_run = subprocess.run

    def opsnap(args, **kw):
        set_args.append(list(args))
        return ægte_run(args, **kw)

    subprocess.run = opsnap
    try:
        m.koer(["rev-parse", "--git-dir"])
    finally:
        subprocess.run = ægte_run
    # `all()` over en tom liste er sand. Uden den her længde-påstand kunne
    # koer() skifte til subprocess.Popen og droppe begge flag, mens alle tre
    # påstande nedenfor blev grønne — og vagten mod `.git/index.lock`, der har
    # generet redaktionen fire gange, ville være væk uden en lyd.
    paastand("koer kaldte overhovedet subprocess.run", len(set_args) == 1)

    # koer() skal aflevere de to strømme HVER FOR SIG. Limes de sammen, kan en
    # `warning:`-linje fra git blive parset som et filnavn og udløse et STOP om
    # en fil, der ikke findes. Det skal prøves på koer selv — en monkeypatch af
    # koer ville netop erstatte den kode, der er tale om.
    class FalsktSvar:
        returncode, stdout, stderr = 0, "linje-a\n", "advarsel-b\n"

    subprocess.run = lambda *a, **k: FalsktSvar()
    try:
        k_, ud_, fejl_ = m.koer(["status"])
    finally:
        subprocess.run = ægte_run
    paastand("koer holder stdout ren", ud_ == "linje-a\n")
    paastand("koer holder stderr for sig", fejl_ == "advarsel-b\n")
    paastand("koer limer ikke stderr på stdout", "advarsel-b" not in ud_)
    paastand("koer sender --no-optional-locks",
             all("--no-optional-locks" in a for a in set_args))
    paastand("koer slår quotepath fra",
             all("core.quotepath=false" in a for a in set_args))
    paastand("koer kalder git", all(a[0] == "git" for a in set_args))

    # --- M2. en hængende git-kommando må ikke ligne en vellykket ----------
    # Timeout er den mest realistiske netværksfejl: en fetch, der hænger i
    # stedet for at fejle hurtigt. Rammer den `except`-grenen i koer() og den
    # returnerer 0, bliver `hentede` True, og scriptet siger "arbejd løs".
    # Ingen anden påstand rammer den gren — den blev målt til nul ramninger.
    def haenger(args, **kw):
        raise subprocess.TimeoutExpired(args, 1)

    subprocess.run = haenger
    try:
        rc_t, _o_t, ud_t = m.koer(["fetch", "origin"])
    finally:
        subprocess.run = ægte_run
    paastand("koer: timeout giver ikke 0", rc_t != 0)
    paastand("koer: timeout siger hvad der skete", "Timeout" in ud_t)

    # Og hele vejen igennem: en hængende fetch skal give 2, ikke 0.
    bar, rep = byg("haenger")
    commit_paa_origin(bar, "haenger", {"data/articles.json": '{"n":1}\n'})
    ægte_koer = m.koer

    def fetch_haenger(args, timeout=30, rod=None):
        if args and args[0] == "fetch":
            return 127, "", "TimeoutExpired: opdigtet"
        return ægte_koer(args, timeout, rod)

    m.koer = fetch_haenger
    try:
        t = i(rep)
    finally:
        m.koer = ægte_koer
    paastand("[repo] hængende fetch: hentede er falsk", t["hentede"] is False)
    paastand("[repo] hængende fetch: dømmes 2, ikke 0", m.doem(t)[0] == 2)
    paastand("[repo] hængende fetch: siger ikke arbejd løs",
             "Arbejd løs" not in "\n".join(m.doem(t)[1]))

    # --- N1. forankring: cwd må ikke afgøre, hvilket repo der måles -------
    # Gennemgangen 14.08 (fjerde runde) fandt, at scriptet målte det repo,
    # processen tilfældigvis stod i. Tre måder det gik galt på, alle prøvet
    # her: et fremmed repo ved siden af, en undermappe, og en mappe der slet
    # ikke er git. Prøvens egen `i()` og `som_proces()` satte altid cwd til
    # repoets rod, så den kunne per konstruktion ikke se fejlen.
    bar, rep = byg("forankret")
    commit_paa_origin(bar, "forankret", {"crawler.py": "# uhentet\n"})

    # a) startet fra et HELT ANDET repo, der selv er rent. Det står på en
    #    ANDEN gren med vilje: er det formmæssigt identisk med målerepoet
    #    (gren `main`, upstream `origin/main`), kan `rod=` fjernes fra
    #    `find_maalestok` uden en rød påstand — begge repoer ville svare det
    #    samme på "hvad er min upstream?".
    _, fremmed = byg("fremmed-og-rent")
    sh("git", "checkout", "-q", "-b", "sidegren", cwd=fremmed)
    sh("git", "push", "-q", "-u", "origin", "sidegren", cwd=fremmed)
    rc, ud = som_proces(rep, fra=fremmed)
    paastand("[forankring] fremmed cwd: måler stadig sit eget repo", rc == 1)
    paastand("[forankring] fremmed cwd: ser crawler.py bagud",
             "crawler.py" in ud)
    paastand("[forankring] fremmed cwd: siger ikke arbejd løs",
             "Arbejd løs" not in ud)

    # b) startet fra en UNDERMAPPE i samme repo. `git status` bruger
    #    cwd-relative stier som standard, så uden forankring holder
    #    `.koerer`-undtagelsen op med at virke, og `diff.relative` ville
    #    begrænse fillisten til undermappen.
    #    Målt direkte på hent_tilstand og ikke som proces: `som_proces` lægger
    #    selv en kopi af scriptet i `_redaktion/`, og den kopi ER en ægte
    #    utracket fil, som med rette tælles med i `urene`. Derfor også et
    #    frisk repo her, så tællingen ikke måler prøvens eget affald.
    bar_u, rep_u = byg("forankret-under")
    commit_paa_origin(bar_u, "forankret-under", {"crawler.py": "# uhentet\n"})
    (rep_u / "_redaktion").mkdir(exist_ok=True)
    (rep_u / "_redaktion" / ".koerer").write_text("2026-08-14T03:22:21+02:00\n")
    hjem = Path.cwd()
    try:
        os.chdir(rep_u / "_redaktion")
        # Rigtig hentning her: med --kun-cache ville den lokale origin/main-ref
        # aldrig blive opdateret, og så var der ikke noget bagud at se.
        t_under = m.hent_tilstand(rod=rep_u)
        t_uforankret = m.hent_tilstand()                 # arver cwd
    finally:
        os.chdir(hjem)
    paastand("[forankring] undermappe: ser stadig crawler.py bagud",
             t_under["kodefiler"] == ["crawler.py"])
    paastand("[forankring] undermappe: låsefilen tælles stadig fra",
             t_under["urene"] == 0)
    paastand("[forankring] undermappe: ingen fejl", t_under["fejl"] is None)
    # Uden forankring ser den samme måling låsefilen som `.koerer` uden mappe,
    # og undtagelsen — der sammenligner med den fulde sti — rammer forbi.
    # Det er selve skaden, `rod=` findes for at forhindre.
    paastand("[forankring] uden rod= rammer låsefil-undtagelsen forbi",
             t_uforankret["urene"] == 1)

    # c) startet fra en mappe, der slet ikke er et git-repo
    ikke_git = ARB / "slet-ikke-git"
    ikke_git.mkdir(exist_ok=True)
    rc, ud = som_proces(rep, fra=ikke_git)
    paastand("[forankring] cwd uden git: siger ikke 'ikke et git-repo'",
             "ikke et git-repo" not in ud)
    paastand("[forankring] cwd uden git: måler stadig rigtigt", rc == 1)

    # Og forankringen skal kunne slås fra i biblioteksbrug, ellers kan prøven
    # ikke måle andre repoer end sit eget.
    paastand("[forankring] hent_tilstand(rod=…) måler den angivne mappe",
             m.hent_tilstand(kun_cache=True, rod=rep)["maalestok"] is not None)
    # Beregnet ud fra scriptets egen placering, ikke ud fra et mappenavn:
    # prøven kører også mod kopier i /tmp, hvor mappen ikke hedder
    # `_redaktion`, og en navnepåstand ville derfor ikke prøve noget.
    paastand("[forankring] REPO_ROD er to niveauer op fra scriptfilen",
             m.REPO_ROD == sti.resolve().parent.parent)
    paastand("[forankring] REPO_ROD er ikke scriptets egen mappe",
             m.REPO_ROD != sti.resolve().parent)

    # --- N2. upstream på en ANDEN remote end origin -----------------------
    # Scriptet hentede før hårdkodet fra `origin`, men målte mod branchens
    # upstream. Ligger de to forskellige steder, lykkes hentningen, `hentede`
    # bliver True, og den ref, der faktisk måles mod, opdateres aldrig — så
    # svarer scriptet "Mappen er den samme kode, som verden kører" om en
    # måling, det ikke har lavet.
    bar, rep = byg("to-remotes")
    anden = ARB / "anden.git"
    sh("git", "clone", "--bare", str(bar), str(anden), cwd=ARB)
    sh("git", "remote", "add", "andet", str(anden), cwd=rep)
    sh("git", "fetch", "andet", "--quiet", cwd=rep)
    sh("git", "branch", "--set-upstream-to=andet/main", "main", cwd=rep)
    # Læg et uhentet kodecommit på DEN anden remote, ikke på origin.
    spejl = ARB / "_spejl-andet"
    sh("git", "clone", str(anden), str(spejl), cwd=ARB)
    (spejl / "crawler.py").write_text("# kun paa den anden remote\n")
    sh("git", "add", "-A", cwd=spejl)
    sh("git", "commit", "-m", "andet", cwd=spejl)
    sh("git", "push", "origin", "main", cwd=spejl)
    t = i(rep)
    paastand("[repo] anden remote: måler mod andet/main",
             t["maalestok"] == "andet/main")
    paastand("[repo] anden remote: hentningen ramte den rigtige remote",
             t["hentede"] is True and t["bagud"] == 1)
    paastand("[repo] anden remote: ser crawler.py bagud",
             t["kodefiler"] == ["crawler.py"])
    paastand("[repo] anden remote: dømmes 1, ikke 0", m.doem(t)[0] == 1)
    paastand("[repo] anden remote: siger ikke 'Arbejd løs'",
             "Arbejd løs" not in "\n".join(m.doem(t)[1]))

    # --- N. anden branch må ikke give falsk STOP --------------------------
    bar, rep = byg("gren")
    sh("git", "checkout", "-b", "forsoeg", cwd=rep)
    (rep / "crawler.py").write_text("# forsoeg\n")
    sh("git", "add", "-A", cwd=rep)
    sh("git", "commit", "-m", "forsoeg", cwd=rep)
    sh("git", "push", "-u", "origin", "forsoeg", cwd=rep)
    t = i(rep)
    paastand("[repo] anden branch: ingen fejl", t["fejl"] is None)
    paastand("[repo] anden branch: måler mod sin egen upstream",
             "forsoeg" in (t["maalestok"] or ""))
    paastand("[repo] anden branch: intet falsk STOP", m.doem(t)[0] == 0)

finally:
    shutil.rmtree(ARB, ignore_errors=True)

print(f"{antal - len(fejl)} grønne, {len(fejl)} røde af {antal} påstande")
for f in fejl:
    print(f"  ✗ {f}")
sys.exit(1 if fejl else 0)
