// Samlet prøve på forsiden: jsdom + de RIGTIGE datafiler.
// Kører uden net: fetch læses fra disk.
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const REPO = path.join(__dirname, "..");
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

setTimeout(() => {
  const d = w.document;
  ok("1 ingen JS-fejl", jsFejl.length === 0, jsFejl.slice(0, 3).join(" | "));

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
    aabnet = !!dlg && (dlg.getAttribute("aria-hidden") !== "true");
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

  console.log("");
  console.log("GROENNE " + groen + " · ROEDE " + roed);
  fejl.forEach(f => console.log("  - " + f));
  process.exit(0);
}, 3000);
