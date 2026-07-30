// Prøve: viser kontrolpanelet de rigtige modeller — og siger det, når et valg
// ikke bliver brugt? Kører _redaktion/kontrolpanel.html i jsdom.
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

// Virker både fra `_redaktion/` i repoet og fra en arbejdsmappe med repoet i en
// undermappe. PROEVE_REPO slår begge, så prøven kan køres mod fx en kopi af HEAD.
const REPO = process.env.PROEVE_REPO
  || (fs.existsSync(path.join(__dirname, "repo", "crawler.py"))
      ? path.join(__dirname, "repo")
      : path.join(__dirname, ".."));
let groen = 0, roed = 0;
function ok(navn, betingelse, ekstra = "") {
  if (betingelse) groen++;
  else { roed++; console.log("  ROED  " + navn + "  " + ekstra); }
}

const jsFejl = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => jsFejl.push(String((e && e.message) || e)));

let skabelon = fs.readFileSync(path.join(REPO, "_redaktion", "kontrolpanel.html"), "utf-8");
const hjerneFil = fs.readFileSync(path.join(REPO, "data", "hjerne-data.js"), "utf-8");
const GRUND = (function () { const w = {}; new Function("window", hjerneFil)(w); return w.HJERNE_STATUS; })();
const kilderJs = fs.readFileSync(path.join(REPO, "data", "kilder-data.js"), "utf-8");

skabelon = skabelon.replace('<script src="../data/kilder-data.js" onerror="window.KILDER_MANGLER=true"></script>',
  "<script>" + kilderJs.split("</script>").join("<\\/script>") + "</script>");

// `</script>` skal maskeres: hjerne-data.js indeholder hele arbejdsloggen, og
// dén nævner strengen. Uden det lukker HTML-parseren script-blokken midt i data.
function lavPanel(status) {
  const js = "window.HJERNE_STATUS = " + JSON.stringify(status) + ";";
  const h = skabelon.replace('<script src="../data/hjerne-data.js" onerror="window.HJERNE_MANGLER=true"></script>',
    "<script>" + js.split("</script>").join("<\\/script>") + "</script>");
  const dm = new JSDOM(h, { url: "https://ainyheder.local/", runScripts: "dangerously",
    pretendToBeVisual: true, virtualConsole: vc });
  return dm.window;
}

// Sådan ser produktionen ud: DeepSeek skriver, Google tegner billederne.
function status(aendring) {
  const s = JSON.parse(JSON.stringify(GRUND));
  s.udbyder = "deepseek";
  s.daglig_model = "deepseek-v4-flash";
  s.gemini_tilgaengelig = true;
  s.deepseek_tilgaengelig = true;
  Object.keys(s.hjerner).forEach(n => {
    s.hjerner[n].model = "deepseek-v4-flash";
    s.hjerner[n].udbyder = "deepseek";
    s.hjerner[n].egen_model = false;
  });
  return Object.assign(s, aendring || {});
}

function aabnHjerne(w, navn) {
  const d = w.document;
  const menu = [...d.querySelectorAll(".side-punkt")].find(b => /Crawleren/.test(b.textContent));
  if (menu) menu.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  // Hele kortet ER knappen, og den bærer trinnets navn i data-n. Vi ledte før
  // efter overskriftens tekst, men har trinnet en egen model, hænger der et
  // ÆNDRET-mærke i samme element — så var teksten ikke længere kun navnet.
  const knap = d.querySelector('[data-n="' + navn + '"]');
  if (knap) knap.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  return d.getElementById("mModel");
}

setTimeout(() => {
  const w = lavPanel(status()), d = w.document;
  ok("1 ingen JS-fejl i panelet", jsFejl.length === 0, jsFejl.slice(0, 2).join(" | "));

  const vaelger = aabnHjerne(w, "omskriv");
  ok("2 model-vælgeren kan åbnes", !!vaelger,
     "fandt ikke #mModel — resten af prøven kan ikke køre");
  if (!vaelger) { console.log("GROENNE " + groen + " · ROEDE " + roed); process.exit(1); }

  const vaerdier = [...vaelger.options].map(o => o.value);
  const tekster = [...vaelger.options].map(o => o.textContent);

  console.log("== A. listen indeholder det rigtige ==");
  ok("A1 deepseek-v4-flash kan vælges", vaerdier.includes("deepseek-v4-flash"), vaerdier.join("|"));
  ok("A2 deepseek-v4-pro kan vælges", vaerdier.includes("deepseek-v4-pro"), vaerdier.join("|"));
  // De to udgåede. Står de i listen, inviterer panelet til at vælge dem.
  ok("A3 gemini-3.5-flash er væk", !vaerdier.includes("gemini-3.5-flash"), vaerdier.join("|"));
  ok("A4 gemini-3.1-flash-lite er væk", !vaerdier.includes("gemini-3.1-flash-lite"), vaerdier.join("|"));
  ok("A5 gemini-3.6-flash er stadig med", vaerdier.includes("gemini-3.6-flash"), vaerdier.join("|"));
  ok("A6 gemini-3.5-flash-lite er stadig med", vaerdier.includes("gemini-3.5-flash-lite"), vaerdier.join("|"));
  ok("A7 den daglige model står øverst med tom værdi", vaerdier[0] === "", vaerdier[0]);
  ok("A8 og den nævner den model, der faktisk kører",
     /deepseek-v4-flash/.test(tekster[0]), tekster[0]);
  ok("A9 hver linje har en etiket", tekster.every(t => t.trim().length > 3), tekster.join("|"));

  console.log("== B. noten siger, hvad valget betyder ==");
  const note = d.getElementById("mModelNote");
  ok("B0 noten findes", !!note);
  if (note) {
    ok("B1 uden valg peger den på den daglige model",
       /deepseek-v4-flash/.test(note.textContent), note.textContent);
    vaelger.value = "gemini-3.6-flash";
    vaelger.dispatchEvent(new w.Event("change", { bubbles: true }));
    ok("B2 et Gemini-valg siger, at trinnet flytter til Google",
       /Google/.test(note.textContent) && /flytter/.test(note.textContent), note.textContent);
    vaelger.value = "deepseek-v4-pro";
    vaelger.dispatchEvent(new w.Event("change", { bubbles: true }));
    ok("B3 et DeepSeek-valg siger, at det er samme udbyder",
       /[Ss]amme udbyder/.test(note.textContent), note.textContent);
  }

  console.log("== C. manglende nøgle bliver sagt højt ==");
  const wU = lavPanel(status({ deepseek_tilgaengelig: false, gemini_tilgaengelig: true }));
  const advU = wU.document.getElementById("advarsel");
  ok("C1 advarslen vises, når DeepSeek-nøglen mangler", advU && !advU.hidden, advU && advU.hidden);
  ok("C2 og den nævner DeepSeek — ikke kun Google",
     advU && /DeepSeek-nøgle/.test(advU.textContent), advU && advU.textContent.slice(0, 90));
  const vU = aabnHjerne(wU, "omskriv");
  if (vU) {
    vU.value = "deepseek-v4-pro";
    vU.dispatchEvent(new wU.Event("change", { bubbles: true }));
    const nU = wU.document.getElementById("mModelNote");
    ok("C3 og noten siger, at valget bliver sprunget over",
       nU && /sprunget over/.test(nU.textContent), nU && nU.textContent);
  } else { ok("C3 og noten siger, at valget bliver sprunget over", false, "kunne ikke åbne"); }

  const wG = lavPanel(status({ gemini_tilgaengelig: false }));
  const advG = wG.document.getElementById("advarsel");
  ok("C4 samme for en manglende Google-nøgle",
     advG && !advG.hidden && /Google-nøgle/.test(advG.textContent),
     advG && advG.textContent.slice(0, 90));

  const wB = lavPanel(status());
  const advB = wB.document.getElementById("advarsel");
  ok("C5 er begge nøgler sat, står der ingen advarsel",
     advB && advB.hidden, advB && advB.textContent.slice(0, 60));

  // En gammel datafil har ikke feltet. Så VED vi ikke, om nøglen mangler, og
  // en advarsel i blinde ville sende folk ud at lede efter et problem, der
  // måske ikke findes.
  const gammel = status();
  delete gammel.deepseek_tilgaengelig;
  const wA = lavPanel(gammel);
  const advA = wA.document.getElementById("advarsel");
  ok("C6 en gammel datafil uden feltet advarer ikke i blinde",
     advA && advA.hidden, advA && advA.textContent.slice(0, 90));

  console.log("== D. et gemt, udgået modelnavn må ikke forsvinde ==");
  const udgaaet = status();
  udgaaet.hjerner.omskriv.model = "gemini-3.5-flash";
  udgaaet.hjerner.omskriv.egen_model = true;
  udgaaet.hjerner.omskriv.udbyder = "gemini";
  const wD = lavPanel(udgaaet);
  const vD = aabnHjerne(wD, "omskriv");
  ok("D0 vælgeren kan åbnes", !!vD);
  if (vD) {
    const vv = [...vD.options].map(o => o.value);
    ok("D1 det gemte navn er med som mulighed", vv.includes("gemini-3.5-flash"), vv.join("|"));
    ok("D2 og det er DET, der står valgt — ikke den daglige model",
       vD.value === "gemini-3.5-flash", vD.value);
    const linje = [...vD.options].find(o => o.value === "gemini-3.5-flash");
    ok("D3 og linjen siger, at den er udgået",
       linje && /udgået/.test(linje.textContent), linje && linje.textContent);
  }

  console.log("== E. anførselstegn i et modelnavn bliver ikke kode ==");
  const ondt = status();
  ondt.hjerner.omskriv.model = 'x" onmouseover="window.RAMT=1';
  ondt.hjerner.omskriv.egen_model = true;
  const wE = lavPanel(ondt);
  const vE = aabnHjerne(wE, "omskriv");
  ok("E1 vælgeren kan stadig åbnes", !!vE);
  ok("E2 ingen levende attribut sneg sig ind", !wE.RAMT, wE.RAMT);
  if (vE) {
    const vv = [...vE.options].map(o => o.value);
    ok("E3 navnet står som ren tekst i værdien",
       vv.includes('x" onmouseover="window.RAMT=1'), vv.join("|"));
  }

  console.log("== F. gem-vejen: valget skal ende i hjerner.json ==");
  // Uden dette afsnit kunne man slette `if (mo) e.model = mo;` og se 28 grønne,
  // mens et tryk på Gem skrev {"hjerner":{}} — altså slettede redaktionens valg.
  function gem(w2, trin, vaerdi) {
    const d2 = w2.document;
    const v = aabnHjerne(w2, trin);
    if (!v) return null;
    v.value = vaerdi;
    v.dispatchEvent(new w2.Event("change", { bubbles: true }));
    d2.getElementById("mGem").dispatchEvent(new w2.MouseEvent("click", { bubbles: true }));
    // Panelets json() ligger i en lukket funktion. Teksten hentes derfor fra
    // knappen "Kopiér JSON", som skriver den samme streng til udklipsholderen.
    let fanget = null;
    Object.defineProperty(w2.navigator, "clipboard", {
      configurable: true, value: { writeText: function (t) { fanget = t; return Promise.resolve(); } }
    });
    const kopi = [...d2.querySelectorAll("button")].find(b => /Kopiér JSON/.test(b.textContent));
    if (kopi) kopi.dispatchEvent(new w2.MouseEvent("click", { bubbles: true }));
    return fanget;
  }
  const wF = lavPanel(status());
  const tekst = gem(wF, "omskriv", "deepseek-v4-pro");
  ok("F0 JSON-teksten kunne hentes", !!tekst, String(tekst).slice(0, 60));
  if (tekst) {
    let fil = null;
    try { fil = JSON.parse(tekst); } catch (e) { /* fanges af F1 */ }
    ok("F1 teksten er gyldig JSON", !!fil, String(tekst).slice(0, 80));
    const h = fil && fil.hjerner || {};
    ok("F2 trinnet står i filen", !!h.omskriv, JSON.stringify(h).slice(0, 90));
    ok("F3 med præcis det modelnavn, der blev valgt",
       h.omskriv && h.omskriv.model === "deepseek-v4-pro",
       h.omskriv && h.omskriv.model);
    ok("F4 og crawleren ville læse det uden ændring — ingen store bogstaver, " +
       "ingen understreger", h.omskriv && h.omskriv.model === h.omskriv.model.trim() &&
       /^deepseek-v4-pro$/.test(h.omskriv.model || ""), h.omskriv && h.omskriv.model);
    ok("F5 de øvrige 13 trin står ikke i filen, når de ikke er ændret",
       Object.keys(h).length === 1, Object.keys(h).join("|"));
  }
  // Et udgået navn skal kunne GEMMES uændret, hvis redaktionen lader det stå —
  // ellers ville selve det at åbne vinduet ændre valget.
  const udgaaet2 = status();
  udgaaet2.hjerner.omskriv.model = "gemini-3.5-flash";
  udgaaet2.hjerner.omskriv.egen_model = true;
  const wF2 = lavPanel(udgaaet2);
  const t2 = gem(wF2, "omskriv", "gemini-3.5-flash");
  let h2 = null;
  try { h2 = JSON.parse(t2).hjerner; } catch (e) { /* fanges nedenfor */ }
  ok("F6 et udgået navn bliver gemt uændret, ikke slettet",
     h2 && h2.omskriv && h2.omskriv.model === "gemini-3.5-flash",
     h2 && JSON.stringify(h2.omskriv || {}).slice(0, 70));

  console.log("== F2. instruksen og nulstillingen skal også nå filen ==");
  // Prompten er det STØRSTE stykke redaktionelt indhold på samme gem-knap.
  // Uden disse påstande kunne man slette `if (pr.trim() …) e.prompt = pr;` og
  // se alt grønt, mens en omskrevet instruks forsvandt i tavshed.
  function gemMed(w2, trin, vaerdi, prompt) {
    const d2 = w2.document;
    const v = aabnHjerne(w2, trin);
    if (!v) return null;
    if (vaerdi !== null) { v.value = vaerdi; v.dispatchEvent(new w2.Event("change", { bubbles: true })); }
    if (prompt !== undefined) d2.getElementById("mPrompt").value = prompt;
    d2.getElementById("mGem").dispatchEvent(new w2.MouseEvent("click", { bubbles: true }));
    let fanget = null;
    Object.defineProperty(w2.navigator, "clipboard", {
      configurable: true, value: { writeText: function (t) { fanget = t; return Promise.resolve(); } }
    });
    const kopi = [...d2.querySelectorAll("button")].find(b => /Kopiér JSON/.test(b.textContent));
    if (kopi) kopi.dispatchEvent(new w2.MouseEvent("click", { bubbles: true }));
    try { return JSON.parse(fanget).hjerner; } catch (e) { return null; }
  }
  const wP = lavPanel(status());
  const hP = gemMed(wP, "kategori", "", "Min egen instruks til kategori-trinnet.");
  ok("F2a en ny instruks ender i filen",
     hP && hP.kategori && hP.kategori.prompt === "Min egen instruks til kategori-trinnet.",
     hP && JSON.stringify(hP).slice(0, 110));
  ok("F2b og trinnet får ikke en model, det ikke har valgt",
     hP && hP.kategori && !("model" in hP.kategori), hP && JSON.stringify(hP.kategori || {}));

  // Nulstilling: står trinnet på "Brug den daglige model" uden egen instruks,
  // skal overstyringen VÆK fra filen — ellers kan man ikke fortryde.
  const nulstil = status();
  nulstil.hjerner.omskriv.model = "deepseek-v4-pro";
  nulstil.hjerner.omskriv.egen_model = true;
  const wN = lavPanel(nulstil);
  const hN = gemMed(wN, "omskriv", "");
  ok("F2c vælger man den daglige model igen, forsvinder overstyringen",
     hN && !hN.omskriv, hN && JSON.stringify(hN).slice(0, 110));

  // Vinduet skal også lukke, og kortet skal vise det nye. Ellers kan man ikke
  // se, at klikket gjorde noget, og trykker igen.
  const wL = lavPanel(status());
  const vL = aabnHjerne(wL, "omskriv");
  if (vL) {
    vL.value = "deepseek-v4-pro";
    vL.dispatchEvent(new wL.Event("change", { bubbles: true }));
    wL.document.getElementById("mGem").dispatchEvent(new wL.MouseEvent("click", { bubbles: true }));
  }
  // `luk()` fjerner klassen "aaben" fra baggrunden; den tømmer ikke modalen,
  // så #mModel bliver liggende i DOM'en. Det er klassen, der afgør, om vinduet
  // er synligt.
  const bagL = [...wL.document.querySelectorAll("*")].find(e => e.classList.contains("aaben"));
  ok("F2d vinduet lukker efter Gem", !bagL, bagL && bagL.className);
  const kort = wL.document.querySelector('[data-n="omskriv"]');
  ok("F2e og kortet viser den nye model",
     kort && /deepseek-v4-pro/.test(kort.textContent), kort && kort.textContent.slice(0, 90));
  ok("F2f og er mærket som ændret",
     kort && /ÆNDRET/.test(kort.textContent), kort && kort.textContent.slice(0, 90));

  console.log("== G. mellemrum omkring et gemt navn må ikke slette valget ==");
  const med_mellemrum = status();
  med_mellemrum.hjerner.omskriv.model = "  deepseek-v4-pro  ";
  med_mellemrum.hjerner.omskriv.egen_model = true;
  const wMel = lavPanel(med_mellemrum);
  const vG = aabnHjerne(wMel, "omskriv");
  ok("G1 rullelisten står på modellen, ikke på den daglige",
     vG && vG.value === "deepseek-v4-pro", vG && JSON.stringify(vG.value));

  console.log("== H. uden nøgle til den daglige model lyver noten ikke ==");
  // Her er den selvmodsigelse, der stod før: "der er ingen Google-nøgle, så
  // trinnet kører på gemini-3.5-flash-lite" — som selv er en Google-model.
  const ingen = status({ udbyder: "ingen", gemini_tilgaengelig: false,
                         deepseek_tilgaengelig: false,
                         daglig_model: "gemini-3.5-flash-lite" });
  const wH = lavPanel(ingen);
  const vH = aabnHjerne(wH, "omskriv");
  const nH = wH.document.getElementById("mModelNote");
  ok("H0 vælgeren kan åbnes", !!vH && !!nH);
  if (vH && nH) {
    ok("H1 uden valg står der, at trinnet bliver sprunget over",
       /sprunget over/.test(nH.textContent) && !/kører på gemini/.test(nH.textContent),
       nH.textContent);
    vH.value = "gemini-3.6-flash";
    vH.dispatchEvent(new wH.Event("change", { bubbles: true }));
    ok("H2 og et valg lover ikke, at en Google-model overtager",
       !/kører på gemini-3\.5-flash-lite/.test(nH.textContent), nH.textContent);
    ok("H3 den siger i stedet, at der ikke er nogen model tilbage",
       /ingen model tilbage|sprunget over/.test(nH.textContent), nH.textContent);
  }
  const advH = wH.document.getElementById("advarsel");
  ok("H4 advarslen lover heller ikke en daglig model, der ikke findes",
     advH && !/videre på den daglige model, gemini/.test(advH.textContent),
     advH && advH.textContent.slice(0, 140));

  // Den datafil, der ligger i repoet lige nu: udbyder "ingen", ingen
  // Google-nøgle, og feltet for DeepSeek mangler helt. `udbyder: "ingen"`
  // skriver crawleren kun, når HVERKEN nøgle er sat — så panelet må ikke
  // samtidig påstå, at et DeepSeek-valg kommer til at køre.
  const tom = status({ udbyder: "ingen", gemini_tilgaengelig: false,
                       daglig_model: "gemini-3.5-flash-lite" });
  delete tom.deepseek_tilgaengelig;
  const wT = lavPanel(tom);
  const vT = aabnHjerne(wT, "omskriv");
  const nT = wT.document.getElementById("mModelNote");
  ok("H5 vælgeren kan åbnes", !!vT && !!nT);
  if (vT && nT) {
    vT.value = "deepseek-v4-pro";
    vT.dispatchEvent(new wT.Event("change", { bubbles: true }));
    ok("H6 uden nogen nøgler lover panelet ikke, at et DeepSeek-valg kører",
       !/Dette trin kører på DeepSeek/.test(nT.textContent), nT.textContent);
    ok("H7 den siger i stedet, at valget bliver sprunget over",
       /sprunget over/.test(nT.textContent), nT.textContent);
  }

  console.log("== I. et låst dokument kan ikke gemmes — heller ikke ad bagvejene ==");
  // Ønske- og kø-kortene har deres EGNE redigeringsvinduer med egne gem-knapper,
  // som returnerer før den generelle grens lås. Uden dette afsnit kunne man
  // fjerne låsen fra de to grene og se alt grønt — mens en fremført, forældet
  // udgave af opgavekøen kunne gemmes oven i den rigtige fil.
  function aabnDokKort(w2, noegle) {
    const d2 = w2.document;
    const menu = [...d2.querySelectorAll(".side-punkt")].find(b => /Arbejdsloopet/.test(b.textContent));
    if (menu) menu.dispatchEvent(new w2.MouseEvent("click", { bubbles: true }));
    const kort = d2.querySelector('[data-dok="' + noegle + '"]');
    if (kort) kort.dispatchEvent(new w2.MouseEvent("click", { bubbles: true }));
    return d2;
  }
  const laast = status();
  (laast.arbejdsloop || []).forEach(x => {
    if (x.noegle === "opgavekoe" || x.noegle === "oensker") {
      x.kan_rettes = false;
      x.beskrivelse = (x.beskrivelse || "") + " KAN IKKE RETTES NU: filen kunne ikke læses.";
    }
  });
  const wI = lavPanel(laast);
  for (const noegle of ["opgavekoe", "oensker"]) {
    const dI = aabnDokKort(wI, noegle);
    const knapper = [...dI.querySelectorAll("#modal button, .modal button")]
      .concat([...dI.querySelectorAll("button")].filter(b => /Gem (opgavekoe|oensker)\.md/.test(b.textContent)));
    ok("I-" + noegle + " ingen gem-knap i det låste vindue",
       !knapper.some(b => /^Gem /.test(b.textContent.trim())),
       knapper.map(b => b.textContent.trim()).filter(t => /^Gem/.test(t)).join("|"));
    const felter = [...dI.querySelectorAll("textarea")].filter(t => t.closest && !t.hidden);
    ok("I-" + noegle + " teksten kan læses, men ikke redigeres",
       felter.length === 0 || felter.every(t => t.readOnly || t.disabled),
       felter.map(t => t.readOnly).join("|"));
    ok("I-" + noegle + " og der står hvorfor",
       /KAN IKKE RETTES NU/.test(dI.body.textContent), "forklaringen mangler");
    const lukI = dI.getElementById("mLuk");
    if (lukI) lukI.dispatchEvent(new wI.MouseEvent("click", { bubbles: true }));
  }
  // Og de ULÅSTE udgaver skal stadig kunne redigeres — låsen må ikke smitte.
  const wJ = lavPanel(status());
  const dJ = aabnDokKort(wJ, "oensker");
  ok("I-kontrol et ulåst dokument har stadig sit redigeringsvindue",
     [...dJ.querySelectorAll("button")].some(b => /Gem oensker\.md|Tilføj/.test(b.textContent)),
     [...dJ.querySelectorAll("button")].map(b => b.textContent.trim()).slice(0, 8).join("|"));

  console.log();
  console.log("GROENNE " + groen + " · ROEDE " + roed);
  process.exit(roed ? 1 : 0);
}, 250);
