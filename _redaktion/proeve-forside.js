// Samlet prøve på forsiden: jsdom + de RIGTIGE datafiler.
// Kører uden net: fetch læses fra disk.
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const REPO = process.env.PROEVE_REPO
  || (fs.existsSync(path.join(__dirname, "repo", "crawler.py"))
      ? path.join(__dirname, "repo")
      : path.join(__dirname, ".."));
let groen = 0, roed = 0;
const fejl = [];
function ok(navn, betingelse, ekstra = "") {
  if (betingelse) { groen++; }
  else { roed++; fejl.push(navn + " " + ekstra); console.log("  ROED  " + navn + " " + ekstra); }
}

const jsFejl = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => jsFejl.push(String(e && e.message || e)));
vc.on("error", (...a) => jsFejl.push("console.error: " + a.join(" ")));

const html = fs.readFileSync(path.join(REPO, "index.html"), "utf-8");
function monterFetch(w) {
  w.fetch = (u) => {
  const rel = String(u).replace(/^https?:\/\/[^/]+\//, "").split("?")[0];
  const p = path.join(REPO, rel);
  if (!fs.existsSync(p)) {
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.reject(new Error("404")), text: () => Promise.resolve("") });
  }
    const txt = fs.readFileSync(p, "utf-8");
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(txt)), text: () => Promise.resolve(txt) });
  };
  w.matchMedia = w.matchMedia || (q => ({ matches: false, media: q, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }));
  if (!w.navigator.serviceWorker) Object.defineProperty(w.navigator, "serviceWorker", { value: { register: () => Promise.resolve() }, configurable: true });
}

const dom = new JSDOM(html, {
  url: "https://ainyheder.com/",
  runScripts: "dangerously",
  pretendToBeVisual: true,
  virtualConsole: vc,
  beforeParse: monterFetch,
});
const w = dom.window;

// Andet vindue med en GAMMEL læsers gemte valg — podes FØR scriptet kører.
// Aflæses i samme callback som resten, når begge har haft 3 sekunder.
const domGammelVane = new JSDOM(html, {
  url: "https://ainyheder.com/", runScripts: "dangerously",
  pretendToBeVisual: true, virtualConsole: vc,
  beforeParse: (w2) => {
    monterFetch(w2);
    try {
      w2.localStorage.setItem("visning", "kompakt");
      w2.localStorage.setItem("sortering", "vigtigst");
    } catch (e) {}
  },
});

// == Hero vælger på prio — prøvet med PODEDE data, begge grene ==
const nu = Date.now();
const lavFixture = (arts) => new JSDOM(html, {
    url: "https://ainyheder.com/", runScripts: "dangerously",
    pretendToBeVisual: true, virtualConsole: vc,
    beforeParse: (w3) => {
      monterFetch(w3);
    const rigtig = w3.fetch;
      w3.fetch = (u) => String(u).includes("articles.json")
        ? Promise.resolve({ ok: true, status: 200,
            json: () => Promise.resolve({ artikler: arts }),
            text: () => Promise.resolve(JSON.stringify({ artikler: arts })) })
        : rigtig(u);
    },
  });
const art = (rubrik, prio, timerSiden) => ({
    titel: rubrik, rubrik, resume: "r", resume_da: "Resumé.", prio,
    kategori: "Lanceringer", kilde: "Test", link: "https://t.dk/" + rubrik,
    foerst_set: new Date(nu - timerSiden * 3600e3).toISOString(),
    dato: new Date(nu - timerSiden * 3600e3).toISOString(),
  });
// VIGTIGT om prio-valget i fixturene: breaking-bjælken støvsuger alt med
// prio ≥ 8 inden for 48 timer (og prio 7, når der er færre end 4
// kandidater) og ROTERER mellem dem hen over døgnet. Lå "den store" på
// prio 9, var det bjælken - ikke heroen - der fik den, og hvilken artikel
// bjælken tager, afhænger af klokkeslættet. Derfor: den store er prio 6
// (under alle bjælkens grænser), notitsen prio 3, og fylden prio 4. Så er
// bjælken tom, og påstandene prøver DET, de siger, de prøver: heroen.
// Gren 1: friske findes — nyeste er prio 3, en ældre (men frisk) er prio 6
const fxFrisk = lavFixture([art("Nyeste notits", 3, 1), art("Dagens store", 6, 8),
                              art("Fyld A", 4, 12), art("Fyld B", 4, 14), art("Fyld C", 4, 16)]);
// Gren 2: INGEN friske — nyeste er prio 2, den største er prio 6 og tre dage gammel
const fxGammel = lavFixture([art("Gammel notits", 2, 30), art("Ugens store", 6, 72),
                               art("Fyld D", 4, 80), art("Fyld E", 4, 90), art("Fyld F", 4, 100)]);

setTimeout(() => {
  const d = w.document;
  ok("1 ingen JS-fejl", jsFejl.length === 0, jsFejl.slice(0, 3).join(" | "));

  console.log("== forsiden efter 31.07: én visning, nyeste først, kølig palette ==");
  // Knapperne er FJERNET - står de der igen, er beslutningen rullet tilbage
  // ved et uheld. Og tegn() må ikke røre dem: en tidligere udgave kaldte
  // getElementById("sortSkift").style på et element, der ikke findes - null-
  // fejlen væltede HELE tegningen, og forsiden viste "Kunne ikke hente".
  ok("N1 ingen sorterings-knapper i topbaren", !d.getElementById("sortSkift"));
  ok("N2 ingen visnings-knapper i topbaren", !d.getElementById("visningSkift"));
  ok("N3 forsiden står i nyeste-tilstand: 'Seneste historier' som sektionstitel",
     /Seneste historier/.test(d.body.textContent));
  ok("N4 og IKKE i dag-grupperet vigtigst-tilstand",
     !/I går|I dag/.test([...d.querySelectorAll(".sektion-titel")].map(x => x.textContent).join("|")));
  const rod = w.getComputedStyle(d.documentElement).getPropertyValue("--bg").trim();
  ok("N5 baggrunden er den kølige tone, ikke avispapir",
     rod === "#f6f7f9", rod);
  ok("N6 theme-color følger med",
     (d.querySelector('meta[name=theme-color]') || {}).content === "#f6f7f9");
  // En gammel gemt indstilling må ikke give én læser en anden forside.
  // Prøves i sit EGET vindue med localStorage podet FØR scriptet kører -
  // ellers prøver påstanden ingenting, for et frisk vindue har ingen gemt værdi.
  const d2 = domGammelVane.window.document;
  ok("N7 en gammel gemt 'kompakt'-indstilling ignoreres",
     !d2.querySelector(".kat-kolonner"), "kompakt-visningen blev tegnet");
  ok("N7b og gemt 'vigtigst' giver stadig nyeste-forsiden",
     /Seneste historier/.test(d2.body.textContent));
  // Stjernen skal stadig sidde på de vigtige artikler
  const stjerner = d.querySelectorAll(".vigtig-chip, .mikro-stjerne");
  ok("N8 vigtigst-stjernen findes stadig på artiklerne", stjerner.length > 0,
     "ingen ★ på forsiden - er prio-chippen røget med i faldet?");
  // Klikker en læser fra forsiden ind på en artikel, må farveuniverset ikke
  // skifte. Crawleren bærer sin egen kopi af paletten i tre skabeloner - de
  // SKAL følge forsidens. Før 31.07 var alle fire varme; nu skal alle være kølige.
  const kravlerKilde = fs.readFileSync(path.join(REPO, "crawler.py"), "utf-8");
  ok("N10 artikelsidernes palette følger forsidens",
     (kravlerKilde.match(/--bg:#f6f7f9/g) || []).length >= 3
     && !/f4f2ec|e2ddd2|6d675d/.test(kravlerKilde),
     "crawler.py har stadig den varme palette et sted");
  ok("N9 heroen har en rubrik", (() => {
       const heroT = (d.querySelector(".hero h1, .hero h2") || {}).textContent || "";
       return heroT.trim().length > 0;
     })(), "ingen hero-rubrik");
  const kort = d.querySelectorAll(".kort, .mikro-kort, article");
  ok("2 kort tegnes", kort.length > 5, "antal=" + kort.length);

  const tekst = d.body.textContent || "";
  ok("3 dagens overblik vises", /overblik|Dagens historie|Største historie/i.test(tekst));

  const hero = d.querySelector(".kicker");
  ok("4 hero har en etiket", !!hero && hero.textContent.trim().length > 3, hero && hero.textContent.slice(0, 40));

  // Klik på et kort skal åbne læseren
  const klikbar = d.querySelector("[onclick], .kort, .mikro-kort");
  let aabnet = false;
  if (klikbar) {
    klikbar.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    const dlg = d.querySelector('[role="dialog"], .laeser, #laeser');
    // Klassen "aaben" er det, der faktisk viser læseren. aria-hidden sættes
    // aldrig, så det gamle tjek kunne ikke fejle - en mutation, der fjernede
    // classList.add("aaben"), gik igennem med alt grønt.
    aabnet = !!dlg && dlg.classList.contains("aaben");
  }
  ok("5 et klik åbner en artikel", aabnet, "dialog=" + !!d.querySelector('[role="dialog"], .laeser, #laeser'));

  ok("6 spring-over-link findes", !!d.querySelector('a[href="#hovedindhold"]'));
  ok("7 canonical peger på forsiden",
     (d.querySelector('link[rel="canonical"]') || {}).href === "https://ainyheder.com/",
     (d.querySelector('link[rel="canonical"]') || {}).href);

  // Måling: hvilken dag bliver de to frigivne artikler grupperet under?
  const arts = JSON.parse(fs.readFileSync(path.join(REPO, "data", "articles.json"), "utf-8")).artikler;
  const maal = arts.filter(a => /Strømsvigt i Washington|Avoiding AI/.test(a.rubrik || ""));
  maal.forEach(a => {
    console.log("     MÅLT  «" + (a.rubrik || "").slice(0, 46) + "» udkom " +
      String(a.dato).slice(0, 10) + ", grupperes under " + String(a.foerst_set).slice(0, 10));
  });
  // Påstanden er vendt om 28.07: efter rettelsen SKAL de ligge på deres egen
  // udgivelsesdag. Prøven dokumenterer nu virkningen i stedet for fejlen.
  ok("8 de to tidligere frigivne ligger nu på deres egen udgivelsesdag",
     maal.every(a => String(a.foerst_set).slice(0, 10) === String(a.dato).slice(0, 10)),
     "fundet=" + maal.length);
  // Parse datoerne — strengsammenligning duer ikke, når nogle datoer har
  // +02:00 og andre +00:00, og længderne er forskellige.
  const alle = arts.filter(a => a.foerst_set && a.dato);
  const foran = alle.filter(a => new Date(a.foerst_set).getTime() < new Date(a.dato).getTime());
  console.log("     MÅLT  " + foran.length + " af " + alle.length + " artikler er set før deres egen udgivelse");

  const heroFrisk = (fxFrisk.window.document.querySelector(".hero h1, .hero h2") || {}).textContent || "";
  ok("N11 blandt friske vinder den vigtigste, ikke den nyeste",
     /Dagens store/.test(heroFrisk), heroFrisk.slice(0, 50));
  const heroGammel = (fxGammel.window.document.querySelector(".hero h1, .hero h2") || {}).textContent || "";
  ok("N12 uden friske vinder stadig den vigtigste — ikke sidste indløb",
     /Ugens store/.test(heroGammel), heroGammel.slice(0, 50));

  console.log("");
  console.log("GROENNE " + groen + " · ROEDE " + roed);
  fejl.forEach(f => console.log("  - " + f));
  process.exit(roed ? 1 : 0);
}, 3000);
