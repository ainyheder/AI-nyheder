// Prøve: siger kortet nyhedens alder først — og først derefter, hvornår vi fandt den?
// Kører index.html i jsdom mod de rigtige datafiler og kalder tidsTekst() direkte.
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
  if (betingelse) groen++;
  else { roed++; fejl.push(navn); console.log("  ROED  " + navn + "  " + ekstra); }
}

const vc = new VirtualConsole();
function monter(w) {
  w.fetch = (u) => {
    const rel = String(u).replace(/^https?:\/\/[^/]+\//, "").split("?")[0];
    const p = path.join(REPO, rel);
    if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404, json: () => Promise.reject(new Error("404")), text: () => Promise.resolve("") });
    const t = fs.readFileSync(p, "utf-8");
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(t)), text: () => Promise.resolve(t) });
  };
  w.matchMedia = w.matchMedia || (q => ({ matches: false, media: q, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }));
  if (!w.navigator.serviceWorker) Object.defineProperty(w.navigator, "serviceWorker", { value: { register: () => Promise.resolve() }, configurable: true });
}
const dom = new JSDOM(fs.readFileSync(path.join(REPO, "index.html"), "utf-8"),
  { url: "https://ainyheder.com/", runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc, beforeParse: monter });
const w = dom.window;

setTimeout(() => {
  const T = w.tidsTekst;
  if (typeof T !== "function") { console.log("  ROED  tidsTekst findes ikke i window"); console.log("GROENNE 0 · ROEDE 1"); process.exit(1); }
  const t = (timer) => new Date(Date.now() - timer * 3600 * 1000).toISOString();

  console.log("== A. udgivelsen står først ==");
  let s = T({ dato: t(24 * 6), foerst_set: t(21) });          // udgivet 6 dage, fundet 21 t
  ok("A1 nyhedens egen alder står først", /^for 6 dage siden/.test(s), s);
  ok("A2 fundet-tidspunktet står bagefter", / · fundet for 21 timer siden$/.test(s), s);
  ok("A3 ordet 'udgivet' bruges ikke længere som halehæng", !/udgivet/.test(s), s);

  console.log("== B. er der ikke noget at forklare, siges der ikke noget ==");
  s = T({ dato: t(20), foerst_set: t(19) });                   // 1 times forskel
  ok("B1 ingen hale ved lille forskel", !/fundet/.test(s), s);
  ok("B2 og teksten er nyhedens alder", /^for 20 timer siden$/.test(s), s);
  s = T({ dato: t(50), foerst_set: t(20) });                   // 30 timer — under grænsen
  ok("B3 30 timers forskel er stadig under grænsen", !/fundet/.test(s), s);
  s = T({ dato: t(60), foerst_set: t(20) });                   // 40 timer — over
  ok("B4 40 timers forskel udløser halen", /fundet/.test(s), s);

  console.log("== C. huller i data vælter ingenting ==");
  ok("C1 helt uden tider", T({}) === "", JSON.stringify(T({})));
  ok("C2 kun foerst_set", T({ foerst_set: t(5) }) === "for 5 timer siden", T({ foerst_set: t(5) }));
  ok("C3 kun dato", T({ dato: t(5) }) === "for 5 timer siden", T({ dato: t(5) }));
  ok("C4 vrøvl i dato", typeof T({ dato: "ikke en dato", foerst_set: t(5) }) === "string");
  ok("C5 fundet FØR udgivelsen giver ingen hale",
     !/fundet/.test(T({ dato: t(2), foerst_set: t(40) })), T({ dato: t(2), foerst_set: t(40) }));

  console.log("== D. på de rigtige data ==");
  const arts = JSON.parse(fs.readFileSync(path.join(REPO, "data", "articles.json"), "utf-8")).artikler;
  const medHale = arts.filter(a => /fundet/.test(T(a)));
  const tomme = arts.filter(a => T(a) === "");
  console.log("     kort med 'fundet'-hale: " + medHale.length + " af " + arts.length + " · kort uden tid: " + tomme.length);
  ok("D1 ingen kort står helt uden tid", tomme.length === 0, tomme.length);
  ok("D2 halen bruges, men ikke på alt", medHale.length > 0 && medHale.length < arts.length, medHale.length);
  const modstrid = arts.filter(a => {
    const s2 = T(a);
    const m = s2.match(/^for (\d+) dage siden · fundet for (\d+) (time|timer|dag|dage) siden$/);
    return m && Number(m[1]) < 2;         // "for 1 dag siden · fundet for 6 dage siden"
  });
  ok("D3 ingen kort siger, at nyheden er nyere end vores fund", modstrid.length === 0, modstrid.length);
  console.log("     eksempel: " + T(medHale[0] || arts[0]));

  console.log("");
  console.log("GROENNE " + groen + " · ROEDE " + roed);
  process.exit(roed ? 1 : 0);
}, 3000);
