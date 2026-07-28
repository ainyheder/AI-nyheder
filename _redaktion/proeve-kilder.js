// Prøve: viser og redigerer kontrolpanelet kilderne rigtigt?
// Kører _redaktion/kontrolpanel.html i jsdom med de RIGTIGE datafiler.
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const REPO = process.env.PROEVE_REPO || path.join(__dirname, "repo");
let groen = 0, roed = 0;
function ok(navn, betingelse, ekstra = "") {
  if (betingelse) groen++;
  else { roed++; console.log("  ROED  " + navn + "  " + ekstra); }
}

// Byg kilder-data.js som crawleren ville have skrevet den.
const feedsFil = JSON.parse(fs.readFileSync(path.join(REPO, "opsaetning", "feeds.json"), "utf-8"));
const arts = JSON.parse(fs.readFileSync(path.join(REPO, "data", "articles.json"), "utf-8")).artikler;
const iListen = {}, somEkstra = {};
arts.forEach(a => {
  iListen[a.kilde] = (iListen[a.kilde] || 0) + 1;
  (a.andre || []).forEach(k => { if (k && k.kilde) somEkstra[k.kilde] = (somEkstra[k.kilde] || 0) + 1; });
});
// Filen er skrevet af crawlerens EGEN skriv_kilde_status mod de rigtige data.
// Bygger prøven sin egen udgave, prøver den kun panelet — ikke kæden.
const kilderJs = fs.readFileSync(path.join(REPO, "data", "kilder-data.js"), "utf-8");
const KILDER = (function () {
  const w = {}; new Function("window", kilderJs)(w); return w.KILDER_STATUS;
})();

const jsFejl = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => jsFejl.push(String((e && e.message) || e)));

let html = fs.readFileSync(path.join(REPO, "_redaktion", "kontrolpanel.html"), "utf-8");
// Datafilerne ligger i ../data og hentes af <script src>. jsdom henter dem ikke
// fra file://, så vi lægger dem ind som inline-scripts i stedet.
// `</script>` skal maskeres: hjerne-data.js indeholder hele arbejdsloggen, og
// dén nævner strengen. Uden det her lukker HTML-parseren script-blokken midt i
// data. I panelet selv er det ufarligt — dér hentes filen med <script src>.
const hjerne = fs.readFileSync(path.join(REPO, "data", "hjerne-data.js"), "utf-8")
  .split("</script>").join("<\\/script>");
html = html.replace('<script src="../data/hjerne-data.js" onerror="window.HJERNE_MANGLER=true"></script>',
  "<script>" + hjerne + "</script>");
html = html.replace('<script src="../data/kilder-data.js" onerror="window.KILDER_MANGLER=true"></script>',
  "<script>window.KILDER_STATUS_HER</script>");

function lavPanel(kilderTekst) {
  var h = html.replace("<script>window.KILDER_STATUS_HER</script>",
    "<script>" + kilderTekst.split("</script>").join("<\\/script>") + "</script>");
  var dm = new JSDOM(h, { url: "https://ainyheder.local/", runScripts: "dangerously",
    pretendToBeVisual: true, virtualConsole: vc });
  return dm.window;
}
const w = lavPanel(kilderJs), d = w.document;
// Panelets script kører i en lukket funktion, så prøven kan ikke kalde tegn().
// Ondsindet data prøves derfor i sit EGET panel, ikke ved at pille i det her.
const ondKilder = JSON.parse(JSON.stringify(KILDER));
ondKilder.kilder[0].navn = 'Wired "AI"';
ondKilder.kilder[0].seneste = [{ rubrik: "Test", foerst_set: "2026-07-28T00:00:00",
  link: 'https://x.dk/a" onmouseover="window.RAMT=1', side: "", hvor: "forside", under: "" }];
ondKilder.feeds_fil = JSON.parse(JSON.stringify(KILDER.feeds_fil));
ondKilder.feeds_fil.feeds[0].navn = 'Wired "AI"';
const w2 = lavPanel("window.KILDER_STATUS = " + JSON.stringify(ondKilder) + ";");

setTimeout(() => {
  ok("1 ingen JS-fejl i panelet", jsFejl.length === 0, jsFejl.slice(0, 2).join(" | "));

  const knap = [...d.querySelectorAll(".side-punkt")].find(b => /Kilder/.test(b.textContent));
  ok("2 Kilder står i menuen", !!knap, [...d.querySelectorAll(".side-punkt")].map(b => b.textContent.slice(0, 12)).join("|"));
  if (!knap) { console.log("GROENNE " + groen + " · ROEDE " + roed); process.exit(1); }
  knap.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));

  // ALT skal slås op på ny efter hver optegning: panelet erstatter rudens
// indhold, så en gemt reference peger på et element, der ikke længere sidder i
// dokumentet — og så bobler klikket aldrig op til den delegerede lytter.
const raekker = () => [...d.querySelectorAll("tr.kilde-r")];
// Slå op på selve navnefeltet, ikke på rækkens tekst: overlaps-linjen nævner
// ANDRE kilders navne, så en substreng-søgning finder den forkerte række.
// Slå op på selve navnefeltet, ikke på rækkens tekst: overlaps-linjen nævner
// ANDRE kilders navne, så en substreng-søgning i rækken finder den forkerte.
const raekke = (navn) => raekker().find(r => {
  const b = r.querySelector("[data-kilde-fold]");
  if (b) return b.dataset.kildeFold.indexOf(navn) === 0;
  const n = r.querySelector(".kilde-navn");
  return n && n.textContent.trim().indexOf(navn) === 0;
});
  ok("3 alle kilder vises", raekker().length === feedsFil.feeds.length, raekker().length + " af " + feedsFil.feeds.length);

  const tekst = d.getElementById("rude").textContent;
  feedsFil.feeds.forEach(f => ok("4 " + f.navn + " står i tabellen", tekst.includes(f.navn)));

  // Tallene skal være de rigtige, ikke bare til stede
  const vb = () => raekke("VentureBeat");
  ok("5 VentureBeat vises med 0 på forsiden", /\b0\b/.test(vb().querySelectorAll("td.tal")[1].textContent),
     vb().querySelectorAll("td.tal")[1].textContent);
  ok("6 og er mærket som en kilde, der intet gav", /gav intet/.test(vb().textContent), vb().textContent.slice(0, 80));
  const tc = () => raekke("TechCrunch");
  ok("7 TechCrunch viser sit rigtige tal (" + iListen["TechCrunch AI"] + ")",
     tc().querySelectorAll("td.tal")[1].textContent.trim() === String(iListen["TechCrunch AI"]),
     tc().querySelectorAll("td.tal")[1].textContent);

  console.log("== kolonnerne viser det, overskrifterne lover ==");
  // Uden de her kan man bytte to kolonner om, og alt er stadig grønt.
  const kolFejl = [];
  KILDER.kilder.forEach(k => {
    const r = raekke(k.navn);
    if (!r) return;
    const t = [...r.querySelectorAll("td.tal")].map(x => x.textContent.trim());
    if (t[0] !== String(k.hentet)) kolFejl.push(k.navn + " hentet:" + t[0] + "≠" + k.hentet);
    if (t[1] !== String(k.i_listen)) kolFejl.push(k.navn + " i_listen:" + t[1] + "≠" + k.i_listen);
    if (t[2] !== String(k.som_ekstra)) kolFejl.push(k.navn + " ekstra:" + t[2] + "≠" + k.som_ekstra);
  });
  ok("K1 alle tre talkolonner viser det rigtige felt", kolFejl.length === 0, kolFejl.slice(0, 3).join(" | "));
  const hd = [...d.querySelectorAll("table.kilder thead th")].map(x => x.textContent.trim());
  ok("K2 og overskrifterne står i den rækkefølge", hd[1] === "Hentet" && hd[2] === "På forsiden" && hd[3] === "Som ekstra", hd.join("|"));

  console.log("== fremmed tekst kan ikke bryde ud af en attribut ==");
  // Et link fra et RSS-feed med et anførselstegn må ikke kunne blive til kode,
  // og en kilde med " i navnet må ikke ødelægge fold-ud-knappen i tavshed.
  const d2 = w2.document;
  const k2 = [...d2.querySelectorAll(".side-punkt")].find(b => /Kilder/.test(b.textContent));
  k2.dispatchEvent(new w2.MouseEvent("click", { bubbles: true }));
  const r0 = [...d2.querySelectorAll("tr.kilde-r")].find(r => {
    const b = r.querySelector("[data-kilde-fold]");
    return b && b.dataset.kildeFold === 'Wired "AI"';
  });
  ok("X1 en kilde med anførselstegn i navnet vises stadig", !!r0,
     [...d2.querySelectorAll("[data-kilde-fold]")].map(b => b.dataset.kildeFold).join("|"));
  if (r0) {
    const fk = r0.querySelector("[data-kilde-fold]");
    ok("X2 attributten bærer hele navnet", fk.dataset.kildeFold === 'Wired "AI"', fk.dataset.kildeFold);
    ok("X3 knappen har ikke fået ekstra attributter",
       fk.attributes.length === 3, [...fk.attributes].map(x => x.name).join(","));
    fk.dispatchEvent(new w2.MouseEvent("click", { bubbles: true }));
    const rk = d2.querySelector(".kilde-fold-r");
    ok("X4 fold-ud virker for den", !!rk);
    const a0 = rk && rk.querySelector("a[href]");
    ok("X5 det onde link fik ingen ekstra attributter",
       a0 && a0.attributes.length === 3, a0 && [...a0.attributes].map(x => x.name).join(","));
    ok("X6 og ingen kode kørte", !w2.RAMT);
  }

  console.log("== loftet på datafilen ==");
  const egne = (k) => (k.seneste || []).filter(r => r.hvor !== "under").length;
  const flest = Math.max(...KILDER.kilder.map(egne));
  ok("L1 ingen kilde lægger mere end 12 egne rubrikker i filen", flest <= 12, flest);
  ok("L2 og mindst én rammer loftet, ellers prøver tallet intet",
     KILDER.kilder.some(k => egne(k) === 12),
     KILDER.kilder.map(egne).join(","));
  ok("L3 filen er under 100 kB", kilderJs.length < 100000, kilderJs.length);

  console.log("== fold ud: hvad kilden faktisk leverede ==");
  const v2 = () => raekke("Version2");
  ok("F1 hver kilde har en fold-ud-knap",
     raekker().every(r => r.querySelector("[data-kilde-fold]")),
     raekker().filter(r => !r.querySelector("[data-kilde-fold]")).length + " uden");
  ok("F2 listen er lukket til at begynde med", !d.querySelector(".kilde-fold-r"));
  ok("F3 Version2 er mærket med, at den overlapper Ingeniøren",
     /Skrev det samme som Ingeniøren/.test(v2().textContent), v2().textContent.slice(0, 120));
  v2().querySelector("[data-kilde-fold]").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  const fold = d.querySelector(".kilde-fold-r");
  ok("F4 et klik folder listen ud", !!fold);
  const linjer = fold ? fold.querySelectorAll(".ka") : [];
  ok("F5 der står artikler i den", linjer.length > 0, linjer.length);
  const kilde = KILDER.kilder.find(k => k.navn === "Version2");
  ok("F6 præcis de artikler, crawleren målte (" + kilde.seneste.length + ")",
     linjer.length === kilde.seneste.length, linjer.length);
  ok("F7 hver linje har en dato og en overskrift",
     [...linjer].every(l => l.querySelector(".ka-dato") && l.textContent.trim().length > 12));
  const dubletter = [...linjer].filter(l => l.classList.contains("ka-dublet"));
  ok("F8 dubletter er markeret", dubletter.length === kilde.seneste.filter(r => r.hvor === "under").length,
     dubletter.length + " mod " + kilde.seneste.filter(r => r.hvor === "under").length);
  ok("F9 og siger hvilken histories overskrift de lå under",
     dubletter.every(l => /lå under «.+»/.test(l.textContent)),
     dubletter[0] && dubletter[0].textContent);
  ok("F10 overskriften over listen tæller dubletterne",
     /lå under en anden kildes overskrift/.test(fold.textContent), fold.textContent.slice(0, 90));
  ok("F11 rubrikkerne er de rigtige",
     kilde.seneste.every(r => fold.textContent.includes(r.rubrik.slice(0, 25))),
     kilde.seneste[0] && kilde.seneste[0].rubrik);
  ok("F12 artiklerne kan åbnes", [...linjer].filter(l => l.querySelector("a[href]")).length > 0);
  v2().querySelector("[data-kilde-fold]").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  ok("F13 et klik mere folder den sammen igen", !d.querySelector(".kilde-fold-r"));
  // en kilde uden artikler må ikke give en tom kasse uden forklaring
  const tom = KILDER.kilder.find(k => !(k.seneste || []).length);
  if (tom) {
    const tr = raekke(tom.navn);
    raekke(tom.navn).querySelector("[data-kilde-fold]").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    ok("F14 en kilde uden artikler siger det med ord",
       /Ingen artikler fra/.test(d.querySelector(".kilde-fold-r").textContent));
    raekke(tom.navn).querySelector("[data-kilde-fold]").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  }

  console.log("== slå fra ==");
  const fra = vb().querySelector("[data-kilde-til]");
  fra.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  const vb2 = () => raekke("VentureBeat");
  ok("8 kilden er nu mærket slået fra", /slået fra/.test(vb2().textContent), vb2().textContent.slice(0, 60));
  ok("9 knappen tilbyder at slå den til igen", /Slå til/.test(vb2().textContent));

  console.log("== tilføj ==");
  d.getElementById("knNavn").value = "Wired AI";
  d.getElementById("knUrl").value = "https://www.wired.com/feed/tag/ai/latest/rss";
  d.getElementById("knKat").value = "Nyheder";
  d.getElementById("knTilfoej").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  let nu = raekker();
  ok("10 der er en kilde mere", nu.length === feedsFil.feeds.length + 1, nu.length);
  ok("11 den nye er mærket 'ikke hentet endnu'",
     /ikke hentet endnu/.test(raekke("Wired").textContent));

  console.log("== afvisning af vrøvl ==");
  function proev(navn, url) {
    d.getElementById("knNavn").value = navn; d.getElementById("knUrl").value = url;
    d.getElementById("knTilfoej").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    return d.getElementById("knKvit").textContent;
  }
  const antalFoer = d.querySelectorAll("tr.kilde-r").length;
  ok("12 tom adresse afvises", /udfyldes/.test(proev("Noget", "")));
  ok("13 adresse uden http afvises", /http/.test(proev("Noget", "www.dr.dk/feed")));
  ok("14 samme navn to gange afvises", /allerede en kilde/.test(proev("Wired AI", "https://x.dk/a")));
  ok("15 samme adresse to gange afvises", /adresse står allerede/.test(proev("Andet navn", "https://www.wired.com/feed/tag/ai/latest/rss")));
  ok("16 og ingen af dem kom med på listen",
     d.querySelectorAll("tr.kilde-r").length === antalFoer,
     d.querySelectorAll("tr.kilde-r").length);

  console.log("== slet kræver to tryk ==");
  nu = raekker();
  const wr = raekke("Wired");
  const sletKnap = wr.querySelector("[data-kilde-slet]");
  sletKnap.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  ok("17 første tryk sletter ikke",
     d.querySelectorAll("tr.kilde-r").length === nu.length, d.querySelectorAll("tr.kilde-r").length);
  ok("18 men spørger med navnet", /Slet Wired AI\?/.test(sletKnap.textContent), sletKnap.textContent);
  const forkl = d.getElementById("kSletForklar");
  ok("18b og forklarer hvad der sker", /aldrig igen/.test(forkl.textContent), forkl.textContent.slice(0, 90));
  ok("18c inklusive at det kræver et push", /pushet/.test(forkl.textContent));
  // en kilde MED artikler skal også få tallene med
  const v2r = raekke("Version2");
  const v2s = v2r.querySelector("[data-kilde-slet]");
  v2s.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  const f2 = d.getElementById("kSletForklar").textContent;
  const kv2 = KILDER.kilder.find(k => k.navn === "Version2");
  ok("18d og siger hvor mange artikler der forsvinder fra forsiden",
     f2.indexOf(String(kv2.i_listen)) > -1, f2.slice(0, 140));
  ok("18e og at kilden stadig linkes til som ekstra kilde",
     /ekstra kilde under/.test(f2), f2.slice(0, 160));
  ok("18f og at de permanente sider bliver liggende", /bliver liggende/.test(f2));
  sletKnap.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  ok("19 andet tryk sletter", d.querySelectorAll("tr.kilde-r").length === nu.length - 1,
     d.querySelectorAll("tr.kilde-r").length);

  console.log("== en tom liste må aldrig gemmes oven i den rigtige ==");
  // Uden vagten kan ét klik lægge en tom kildeliste oven i feeds.json, og så
  // holder siden op med at få nyheder, uden at noget siger fra.
  {
    const w3 = lavPanel("window.KILDER_STATUS = " +
      JSON.stringify(Object.assign({}, KILDER, { feeds_fil: { kommentar: "x", feeds: [] } })) + ";");
    const d3 = w3.document;
    [...d3.querySelectorAll(".side-punkt")].find(b => /Kilder/.test(b.textContent))
      .dispatchEvent(new w3.MouseEvent("click", { bubbles: true }));
    let skrevet = false;
    w3.URL.createObjectURL = () => { skrevet = true; return "blob:x"; };
    w3.showSaveFilePicker = undefined;
    const g3 = d3.getElementById("kGem");
    g3.removeAttribute("disabled");
    g3.dispatchEvent(new w3.MouseEvent("click", { bubbles: true }));
    ok("T1 der blev IKKE skrevet en tom fil", !skrevet);
    ok("T2 og panelet siger hvorfor",
       /tom/.test(d3.getElementById("kGemKvit").textContent),
       d3.getElementById("kGemKvit").textContent);
  }

  console.log("== gem-knappen er låst, når intet er rørt ==");
  {
    const w4 = lavPanel(kilderJs);
    const d4 = w4.document;
    [...d4.querySelectorAll(".side-punkt")].find(b => /Kilder/.test(b.textContent))
      .dispatchEvent(new w4.MouseEvent("click", { bubbles: true }));
    ok("T3 knappen er låst fra start", d4.getElementById("kGem").hasAttribute("disabled"));
    ok("T4 og panelet siger hvor gammelt øjebliksbilledet er",
       /som .*feeds\.json.* så ud/.test(d4.querySelector(".kilde-alder").textContent),
       (d4.querySelector(".kilde-alder") || {}).textContent);
    d4.querySelectorAll("[data-kilde-til]")[0]
      .dispatchEvent(new w4.MouseEvent("click", { bubbles: true }));
    ok("T5 og låses op, når noget er ændret",
       !d4.getElementById("kGem").hasAttribute("disabled"));
  }

  console.log("== det, der ville blive gemt ==");
  // Panelet gemmer feedsFil-arbejdskopien. Vi henter den via download-vejen.
  let gemt = null;
  w.URL.createObjectURL = (b) => { gemt = b; return "blob:x"; };
  w.showSaveFilePicker = undefined;
  d.getElementById("kGem").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  setTimeout(async () => {
    ok("20 der blev lavet en fil at gemme", !!gemt);
    const txt = gemt ? await gemt.text() : "";
    let obj = null; try { obj = JSON.parse(txt); } catch (e) {}
    ok("21 og den er gyldig JSON", !!obj, txt.slice(0, 60));
    if (obj) {
      ok("22 kommentaren fra den oprindelige fil er bevaret",
         obj.kommentar === feedsFil.kommentar, String(obj.kommentar).slice(0, 40));
      ok("23 alle kilder er der stadig", obj.feeds.length === feedsFil.feeds.length, obj.feeds.length);
      const v = obj.feeds.find(f => f.navn === "VentureBeat AI");
      ok("24 VentureBeat er markeret aktiv:false", v && v.aktiv === false, JSON.stringify(v));
      const tc2 = obj.feeds.find(f => f.navn === "TechCrunch AI");
      ok("25 en urørt kilde er byte for byte som før",
         JSON.stringify(tc2) === JSON.stringify(feedsFil.feeds.find(f => f.navn === "TechCrunch AI")),
         JSON.stringify(tc2));
      ok("26 den slettede er ikke med", !obj.feeds.some(f => f.navn === "Wired AI"));
    }
    console.log("");
    console.log("GROENNE " + groen + " · ROEDE " + roed);
    process.exit(roed ? 1 : 0);
  }, 60);
}, 2500);
