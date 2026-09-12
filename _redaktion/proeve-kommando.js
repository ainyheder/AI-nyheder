#!/usr/bin/env node
/* Regression checks for the local command center. No network, real writes,
 * crawler calls or credentials. Run with jsdom available in NODE_PATH. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM, VirtualConsole } = require("jsdom");

const ROOT = path.resolve(process.env.PROEVE_REPO || path.join(__dirname, ".."));
const CONFIG_PATHS = ["opsaetning/feeds.json", "_redaktion/hjerner.json", "opsaetning/redaktoer.md"];
const clone = value => JSON.parse(JSON.stringify(value));
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
let passed = 0, failed = 0;

function fixture() {
  return {
    version: 1, genereret: "2026-09-11T14:45:00Z",
    tilgaengelige: { feeds: true, hjerner: true, redaktoer: true, artikler: true,
      redaktoer_status: true, hjerner_status: true, kilder: true, laesertal: true },
    fejl: [],
    feeds_fil: { kommentar: "Keep this comment", future: { keep: true }, feeds: [
      { navn: "Example Lab", url: "https://example.org/feed.xml", kategori: "Labs", max: 12,
        note: "Keep this source note", future_field: { values: [3, 1] } },
      { navn: "Another Source", url: "https://news.example.com/atom", kategori: "Dybde", aktiv: false },
    ] },
    hjerner_fil: { kommentar: "Keep model notes", future: 42, hjerner: {
      motiv: { prompt: "Describe a concrete illustration.", custom: { preserve: true } },
    } },
    redaktoer_instruks: "# Redaktionens retning\n\nPrioritér internationale modellanceringer.\n",
    artikler: { opdateret: "2026-09-11T14:38:00Z", antal: 158, med_billede: 42,
      paa_dansk: 152, kategorier: { Lanceringer: 12 }, kilder: { "Example Lab": 2 },
      udvalgte: [{ rubrik: "A documented model release", titel: "Model release", link: "https://example.org/model",
        side: "artikel/test.html", kilde: "Example Lab", dato: "2026-09-11T12:00:00Z", billede: "" }], seneste: [] },
    redaktoer_status: { opdateret: "2026-09-11T14:38:00Z", status: "reserve", model: "deepseek-flash",
      forklaring: "Redaktionsmødet fejlede: ValueError", modelkald: 7, kildehentninger: 8,
      regelbaseret_udvalg: [], udgivet_udvalg: [], vaerktoejer: [], kildegrundlag: [] },
    hjerner_status: { opdateret: "2026-09-11T14:38:00Z", daglig_model: "deepseek-flash", udbyder: "deepseek",
      billedmodel: "gemini-3.1-flash-lite-image", gemini_tilgaengelig: true, deepseek_tilgaengelig: true,
      hjerner: {
        motiv: { beskrivelse: "Finder billedmotiver", model: "deepseek-flash", udbyder: "deepseek",
          egen_model: false, egen_prompt: true, standard_prompt: "Default art direction.", aktiv_prompt: "Describe a concrete illustration." },
        omskriv: { beskrivelse: "Skriver rubrik og resumé", model: "deepseek-flash", udbyder: "deepseek",
          egen_model: false, egen_prompt: false, standard_prompt: "Write Danish news.", aktiv_prompt: "Write Danish news." },
      } },
    kilder: { opdateret: "2026-09-11T14:38:00Z", artikler_i_alt: 158, kilder: [
      { navn: "Example Lab", status: "ok", hentet: 12, i_listen: 2, som_ekstra: 1, seneste: [] },
    ] },
    laesertal: { opdateret: "2026-09-11T14:44:00Z", maaling: "ok", dage: 30, serie_dage: 30,
      besoeg_i_alt: 26, sidevisninger_i_alt: 43, ai_chat_besoeg: 3,
      serie: [{ dato: "2026-09-11", besoeg: 3, visninger: 4 }], sider: [], artikler: [], henvisere: [], laeste_temaer: [] },
  };
}

function fakeDirectory(data = fixture()) {
  const content = {
    "opsaetning/feeds.json": JSON.stringify(data.feeds_fil, null, 2) + "\n",
    "_redaktion/hjerner.json": JSON.stringify(data.hjerner_fil, null, 2) + "\n",
    "opsaetning/redaktoer.md": data.redaktoer_instruks,
  };
  const reads = [], writes = [], requested = [];
  let failWrite = "";
  function error(name, message) { const e = new Error(message); e.name = name; return e; }
  function directory(prefix = "") {
    return { kind: "directory", name: prefix ? prefix.split("/").at(-1) : "AI NEWS",
      queryPermission: async () => "granted", requestPermission: async () => "granted",
      getDirectoryHandle: async (name, options) => {
        assert(!options?.create, "The command center must not create unexpected project folders");
        const full = prefix ? `${prefix}/${name}` : name;
        assert(["opsaetning", "_redaktion"].includes(full), `Unexpected directory: ${full}`);
        return directory(full);
      },
      getFileHandle: async (name, options) => {
        const full = prefix ? `${prefix}/${name}` : name;
        requested.push(full);
        assert(CONFIG_PATHS.includes(full), `Unexpected settings file: ${full}`);
        if (!(full in content)) throw error("NotFoundError", "File does not exist");
        return { kind: "file", name,
          getFile: async () => ({ name, text: async () => { reads.push(full); return content[full]; } }),
          createWritable: async () => {
            if (failWrite === full) throw error("NotAllowedError", "Simulated write denial");
            let pending;
            return { write: async value => { pending = value; }, close: async () => {
              content[full] = pending; writes.push({ path: full, text: pending });
            }, abort: async () => {} };
          },
        };
      },
    };
  }
  return { handle: directory(), content, reads, writes, requested, fail: name => { failWrite = name; } };
}

async function panel(data = fixture(), options = {}) {
  const failures = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => failures.push(e.message));
  const markup = fs.readFileSync(path.join(ROOT, "Indstillinger.html"), "utf8")
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "");
  const dom = new JSDOM(markup, { url: "file:///Users/example/AI%20NEWS/Indstillinger.html",
    runScripts: "outside-only", pretendToBeVisual: true, virtualConsole: vc });
  const w = dom.window;
  w.KOMMANDO_DATA = data;
  const storage = new Map(Object.entries(options.storage || {}));
  Object.defineProperty(w, "localStorage", { value: {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: key => storage.delete(key),
  } });
  w.matchMedia ||= () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  w.HTMLElement.prototype.scrollIntoView = function () {};
  if (w.HTMLDialogElement) {
    w.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
    w.HTMLDialogElement.prototype.close = function () { this.open = false; this.dispatchEvent(new w.Event("close")); };
  }
  w.eval(fs.readFileSync(path.join(ROOT, "assets/kommando.js"), "utf8"));
  await tick();
  assert(w.Kommando, "Command-center test API should be available");
  assert.deepEqual(failures, [], "No application errors on load");
  return { w, d: w.document, app: w.Kommando, failures, storage, close: () => dom.window.close() };
}

async function check(name, fn) {
  try { await fn(); passed++; console.log("OK " + name); }
  catch (error) { failed++; console.error("FAIL " + name + ": " + error.message); }
}

async function usingPanel(fn, data = fixture(), options = {}) {
  const p = await panel(data, options);
  try { await fn(p); assert.deepEqual(p.failures, [], "No browser errors after interaction"); }
  finally { p.close(); }
}

function setToggle(p, index, checked) {
  const input = p.d.querySelector(`[data-source-toggle="${index}"]`);
  assert(input, "Expected source toggle " + index);
  input.checked = checked;
  input.dispatchEvent(new p.w.Event("change", { bubbles: true }));
}

async function run() {
  await check("Every command-center view renders with actual data", () => usingPanel(p => {
    for (const view of ["overview", "editor", "sources", "models", "images", "readers", "operations"]) {
      p.app.navigate(view);
      assert.equal(p.app.state.view, view);
      assert(p.d.getElementById("view-content").textContent.trim().length > 80, view);
    }
    p.app.navigate("overview");
    assert.match(p.d.getElementById("view-content").textContent, /Reserve aktiv/);
    assert.match(p.d.getElementById("view-content").textContent, /ValueError/);
  }));

  await check("Missing data stays unknown and settings can still be connected", () => usingPanel(async p => {
    assert.match(p.d.getElementById("view-content").textContent, /Ikke målt|Ingen måling/);
    assert.equal(p.app.state.drafts.feeds, null);
    p.app.navigate("readers");
    assert.match(p.d.getElementById("view-content").textContent, /betyder ikke.*nul/);
    const dir = fakeDirectory();
    await p.app.connectDirectory(dir.handle);
    assert.equal(p.app.state.drafts.feeds.feeds.length, 2);
    assert.deepEqual([...new Set(dir.requested)].sort(), CONFIG_PATHS.slice().sort());
  }, {}));

  await check("Source names and story titles cannot inject HTML or script URLs", () => {
    const data = fixture();
    const malicious = '<img src=x onerror="window.RAMT=1"> " & <svg onload="window.RAMT=2">';
    data.feeds_fil.feeds[0].navn = malicious;
    data.artikler.udvalgte[0].rubrik = malicious;
    data.artikler.udvalgte[0].link = "javascript:window.RAMT=3";
    return usingPanel(p => {
      assert(!p.d.querySelector("#view-content [onerror],#view-content [onload]"));
      assert(!p.d.querySelector('#view-content a[href^="javascript:"]'));
      assert(p.d.getElementById("view-content").textContent.includes(malicious));
      p.app.navigate("sources");
      assert(p.d.getElementById("source-list").textContent.includes(malicious));
      assert(!p.d.querySelector("#source-list img,#source-list svg"));
      assert.equal(p.w.RAMT, undefined);
    }, data);
  });

  await check("Canonical comparison ignores object key order but keeps array order", () => usingPanel(p => {
    assert.equal(p.app.canonical({ b: [1, 2], a: { z: 1, x: 2 } }), p.app.canonical({ a: { x: 2, z: 1 }, b: [1, 2] }));
    assert.notEqual(p.app.canonical({ b: [1, 2] }), p.app.canonical({ b: [2, 1] }));
    assert.equal(p.app.canonical("line\r\nnext"), p.app.canonical("line\nnext"));
  }));

  await check("Malformed, wrong-schema and invalid execution settings are rejected", () => usingPanel(p => {
    const validate = p.app.validateConfig;
    for (const value of [{ hjerner: {} }, { feeds: [] }, { feeds: [null] },
      { feeds: [{ navn: "A", url: "javascript:alert(1)" }] },
      { feeds: [{ navn: "A", url: "https://example.org", max: 0 }] },
      { feeds: [{ navn: "A", url: "https://example.org", max: 1.5 }] },
      { feeds: [{ navn: "A", url: "https://example.org", format: "unknown" }] },
      { feeds: [{ navn: "A", url: "https://example.org", aktiv: "false" }] }]) {
      assert.throws(() => validate("feeds", value));
    }
    for (const value of [{ feeds: [] }, { hjerner: [] }, { hjerner: { motiv: { prompt: 5 } } }]) {
      assert.throws(() => validate("hjerner", value));
    }
    for (const value of [null, "", " ", "x".repeat(10001)]) assert.throws(() => validate("retning", value));
    assert.equal(validate("feeds", fixture().feeds_fil), true);
    assert.equal(validate("hjerner", fixture().hjerner_fil), true);
  }));

  await check("Source toggles preserve unknown fields and baseline until saved", () => usingPanel(async p => {
    const dir = fakeDirectory(); await p.app.connectDirectory(dir.handle); p.app.navigate("sources");
    const before = clone(p.app.state.baseline.feeds);
    setToggle(p, 1, true); setToggle(p, 0, false);
    assert.equal(p.app.state.drafts.feeds.feeds[0].aktiv, false);
    assert.deepEqual(clone(p.app.state.baseline.feeds), before);
    assert.deepEqual(clone(p.app.state.drafts.feeds.feeds[0].future_field), before.feeds[0].future_field);
    assert.equal(p.app.state.drafts.feeds.kommentar, before.kommentar);
    assert.equal(await p.app.saveChanges(), true);
    const written = JSON.parse(dir.content[CONFIG_PATHS[0]]);
    assert.equal(written.feeds[0].aktiv, false);
    assert.deepEqual(written.future, before.future);
    assert.deepEqual(written.feeds[0].future_field, before.feeds[0].future_field);
    assert.equal(written.feeds[0].note, before.feeds[0].note);
    assert.deepEqual(dir.writes.map(x => x.path), [CONFIG_PATHS[0]]);
  }));

  await check("Model edits and resets retain unrecognized step metadata", () => usingPanel(async p => {
    const dir = fakeDirectory(); await p.app.connectDirectory(dir.handle);
    p.app.setOverride("motiv", { model: "deepseek-flash", prompt: "New art direction" });
    assert.deepEqual(clone(p.app.state.drafts.hjerner.hjerner.motiv.custom), { preserve: true });
    await p.app.saveChanges();
    p.app.setOverride("motiv", {});
    assert.deepEqual(clone(p.app.state.drafts.hjerner.hjerner.motiv), { custom: { preserve: true } });
    await p.app.saveChanges();
    assert.equal(JSON.parse(dir.content[CONFIG_PATHS[1]]).future, 42);
  }));

  await check("Connecting a wrong folder is atomic and does not replace drafts", () => usingPanel(async p => {
    const before = clone(p.app.state.drafts), dir = fakeDirectory();
    dir.content[CONFIG_PATHS[1]] = JSON.stringify({ feeds: [] });
    await assert.rejects(() => p.app.connectDirectory(dir.handle), /hjerner/);
    assert.equal(p.app.state.directory, null);
    assert.deepEqual(clone(p.app.state.drafts), before);
    assert.equal(dir.writes.length, 0);
  }));

  await check("External config drift blocks all writes before the first file", () => usingPanel(async p => {
    const dir = fakeDirectory(); await p.app.connectDirectory(dir.handle);
    p.app.state.drafts.feeds.feeds[0].max = 8;
    p.app.state.drafts.retning += "\nMore original model tests.\n";
    dir.content[CONFIG_PATHS[2]] += "\nAn external edit.\n";
    await assert.rejects(() => p.app.saveChanges(), /ændret/);
    assert.equal(dir.writes.length, 0);
    assert.equal(p.app.state.drafts.feeds.feeds[0].max, 8);
    assert.equal(p.app.dirtyKeys().length, 2);
    assert.equal(p.app.state.busy, false);
  }));

  await check("Key reordering is not drift and a second save refreshes baseline", () => usingPanel(async p => {
    const dir = fakeDirectory(); await p.app.connectDirectory(dir.handle);
    const old = JSON.parse(dir.content[CONFIG_PATHS[0]]);
    dir.content[CONFIG_PATHS[0]] = JSON.stringify({ feeds: old.feeds, future: old.future, kommentar: old.kommentar });
    p.app.state.drafts.feeds.feeds[0].max = 9; await p.app.saveChanges();
    assert.equal(p.app.dirtyKeys().length, 0);
    p.app.state.drafts.feeds.feeds[0].max = 7; await p.app.saveChanges();
    assert.equal(JSON.parse(dir.content[CONFIG_PATHS[0]]).feeds[0].max, 7);
    assert.equal(p.app.state.baseline.feeds.feeds[0].max, 7);
    assert.equal(p.app.dirtyKeys().length, 0);
    assert.equal(dir.writes.length, 2);
    assert.match(p.d.getElementById("app-status").textContent, /Gemt i projektmappen/);
    assert.match(p.d.getElementById("app-status").textContent, /ikke udgivet/);
    assert.equal(await p.app.saveChanges(), false);
    assert.equal(dir.writes.length, 2);
  }));

  await check("Partial save failure retains unsaved drafts and retries only remaining files", () => usingPanel(async p => {
    const dir = fakeDirectory(); await p.app.connectDirectory(dir.handle);
    p.app.state.drafts.feeds.feeds[0].max = 8;
    p.app.setOverride("motiv", { prompt: "A precise and lively illustration." });
    p.app.state.drafts.retning += "\nPrefer hands-on testing.\n";
    dir.fail(CONFIG_PATHS[1]);
    await assert.rejects(() => p.app.saveChanges(), /write denial/);
    assert.deepEqual(dir.writes.map(x => x.path), [CONFIG_PATHS[0]]);
    assert.deepEqual([...p.app.dirtyKeys()], ["hjerner", "retning"]);
    assert.equal(p.app.state.baseline.feeds.feeds[0].max, 8);
    assert.equal(p.app.state.drafts.hjerner.hjerner.motiv.prompt, "A precise and lively illustration.");
    assert.match(p.app.state.drafts.retning, /hands-on testing/);
    assert.match(p.d.getElementById("app-status").textContent, /resterende.*kladde/);
    dir.fail(""); await p.app.saveChanges();
    assert.deepEqual(dir.writes.map(x => x.path), CONFIG_PATHS);
    assert.equal(p.app.dirtyKeys().length, 0);
  }));

  await check("Unreadable and wrong-file content at save time is never overwritten", () => usingPanel(async p => {
    const dir = fakeDirectory(); await p.app.connectDirectory(dir.handle);
    p.app.state.drafts.feeds.feeds[0].max = 8;
    for (const corrupt of ["{not JSON", JSON.stringify({ hjerner: {} })]) {
      dir.content[CONFIG_PATHS[0]] = corrupt;
      await assert.rejects(() => p.app.saveChanges());
      assert.equal(dir.writes.length, 0);
      assert.equal(p.app.state.drafts.feeds.feeds[0].max, 8);
    }
  }));

  await check("Stale recovered browser draft never replaces newer configuration", () => {
    const data = fixture(), baseline = { feeds: clone(data.feeds_fil), hjerner: clone(data.hjerner_fil), retning: data.redaktoer_instruks };
    const drafts = clone(baseline); drafts.feeds.feeds[0].max = 2;
    baseline.feeds.feeds[0].max = 99;
    const serialized = JSON.stringify({ version: 1, baseline, drafts });
    return usingPanel(p => {
      assert.equal(p.app.state.drafts.feeds.feeds[0].max, 12);
      assert.equal(p.app.dirtyKeys().length, 0);
      assert.match(p.d.getElementById("app-status").textContent, /ældre kladde/);
      assert.equal(p.storage.get("ai-kommandocentral-draft"), serialized);
    }, data, { storage: { "ai-kommandocentral-draft": serialized } });
  });

  await check("Reader table uses the actual snapshot's visninger field", () => {
    const data = fixture(); data.laesertal.sider = [{ sti: "/model.html", besoeg: 5, visninger: 17 }];
    return usingPanel(p => {
      p.app.navigate("readers");
      const values = [...p.d.querySelectorAll("tbody td")].map(td => td.textContent);
      assert.deepEqual(values, ["/model.html", "5", "17"]);
    }, data);
  });

  await check("Failed analytics measurement is not represented as zero visitors", () => {
    const data = fixture(); Object.assign(data.laesertal, { maaling: "fejl", besoeg_i_alt: 0, sidevisninger_i_alt: 0 });
    return usingPanel(p => {
      p.app.navigate("readers");
      assert.match(p.d.getElementById("view-content").textContent, /Ingen læsertal tilgængelige|Målingen.*fejl|betyder ikke.*nul/);
      assert.equal(p.d.querySelectorAll(".stat-value").length, 0);
    }, data);
  });

  await check("Exact model selection, manual catalog and special roles", () => usingPanel(p => {
    p.app.state.drafts.hjerner.hjerner.omskriv={model:"gemini-custom"};
    p.app.navigate("models");
    assert.match(p.d.querySelector('[data-edit-model="omskriv"]').textContent,/gemini-custom/);
    assert.ok(p.d.querySelector('[data-edit-model="forside_agent"]'));
    p.d.querySelector('[data-edit-model="omskriv"]').click();
    const select=p.d.getElementById('step-model');
    assert.equal(select.tagName,'SELECT');assert.equal(select.value,'gemini-custom');
    select.value='manual';select.dispatchEvent(new p.w.Event('change',{bubbles:true}));
    p.d.getElementById('manual-model').value='gemini-new-test';
    p.d.getElementById('model-form').dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));
    assert.equal(p.app.state.drafts.hjerner.hjerner.omskriv.model,'gemini-new-test');
    assert.ok(p.app.state.drafts.hjerner.modeller.includes('gemini-new-test'));
    p.d.querySelector('[data-edit-model="forside_agent"]').click();
    assert.ok([...p.d.getElementById('step-model').options].every(o=>!o.value.startsWith('gemini')));
  }));

  await check("Automatic catalogs need no browser keys or API requests", () => usingPanel(p => {
    p.app.navigate('models');
    assert.equal(p.d.querySelectorAll('[data-update-provider], #provider-key').length,0);
    assert.match(p.d.getElementById('view-content').textContent,/Automatisk opdatering hver dag/);
    p.app.state.snapshot.modelkatalog={udbydere:{Gemini:{modeller:Array.from({length:40},(_,i)=>'gemini-model-'+i),opdateret:'2026-09-12T00:00:00Z'}}};
    assert.equal(p.app.modelList('omskriv').filter(m=>m.startsWith('gemini-model-')).length,40);
  }));

  await check("All revised prompts render and image style edits preserve FLUX", async () => {
    const data=fixture();
    data.hjerner_fil=JSON.parse(fs.readFileSync(path.join(ROOT,'_redaktion/hjerner.json'),'utf8'));
    data.hjerner_fil.hjerner.billedgenerator={model:'@cf/black-forest-labs/flux-2-klein-4b',prompt:'Test image style'};
    data.hjerner_fil.hjerner.motiv ||= {prompt:'Test motif'};
    return usingPanel(p => {
      p.app.validateConfig('hjerner',p.app.state.drafts.hjerner);
      p.app.navigate('models');
      for(const [name,step] of Object.entries(data.hjerner_fil.hjerner).filter(([,s])=>s.prompt)) {
        p.d.querySelector(`[data-edit-model="${name}"]`).click();
        assert.equal(p.d.getElementById('step-prompt').value,step.prompt);
        p.d.getElementById('edit-dialog').close();
      }
      p.d.querySelector('[data-edit-model="billedgenerator"]').click();
      p.d.getElementById('step-prompt').value='Updated image style';
      p.d.getElementById('model-form').dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));
      assert.equal(p.app.state.drafts.hjerner.hjerner.billedgenerator.prompt,'Updated image style');
      assert.equal(p.app.state.drafts.hjerner.hjerner.billedgenerator.model,'@cf/black-forest-labs/flux-2-klein-4b');
      assert.equal(p.app.dirtyKeys().join(','),'hjerner');
      assert.equal(p.app.state.drafts.hjerner.hjerner.motiv.prompt,data.hjerner_fil.hjerner.motiv.prompt);
    },data);
  });

  console.log(`\nKOMMANDOCENTRAL: ${passed} passed · ${failed} failed`);
  process.exitCode = failed ? 1 : 0;
}

run().catch(error => { console.error(error.stack); process.exitCode = 1; });
