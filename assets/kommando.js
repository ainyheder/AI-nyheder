/* Kommandocentral: rigtige indstillinger, kildebaseret status og lokale filgem. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const copy = value => value == null ? value : JSON.parse(JSON.stringify(value));
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const plain = v => !!v && typeof v === 'object' && !Array.isArray(v);
  const canonical = v => typeof v === 'string' ? v.replace(/\r\n/g, '\n') : JSON.stringify(sortKeys(v));
  function sortKeys(v) { return Array.isArray(v) ? v.map(sortKeys) : plain(v) ? Object.fromEntries(Object.keys(v).sort().map(k => [k, sortKeys(v[k])])) : v; }
  const hostname = value => { try { return new URL(value).hostname; } catch (_) { return 'Ugyldig adresse'; } };
  const safeUrl = value => { try { const u = new URL(value); return ['https:', 'http:'].includes(u.protocol) ? u.href : ''; } catch (_) { return ''; } };
  const PATHS = {feeds:'opsaetning/feeds.json', hjerner:'_redaktion/hjerner.json', retning:'opsaetning/redaktoer.md'};
  const NAMES = {feeds:'Nyhedskilder', hjerner:'Modeller og instruktioner', retning:'Redaktionens retning'};
  const STEP_NAMES = {forside_agent:'Vælg forsiden · redaktøragent',billedgenerator:'Generér illustrationer',omskriv:'Rubrik og resumé',kategori:'Vurder nyhedsværdi',dublet:'Saml dubletter',brief:'Skriv hele artiklen',redaktoer:'Kontrollér artiklen',stram:'Stram teksten op',navngiv:'Forbedr gamle rubrikker',motiv:'Beskriv billedmotivet',kartotek:'Skriv dagens læserprompt',quiz:'Lav quizzen',dagens_overblik:'Dagens overblik',ugens_overblik:'Ugens overblik',youtube:'Bearbejd videoer',opslag:'Skriv sociale opslag'};
  const VIEWS = {
    overview:['Overblik','REDAKTIONEN','Det vigtigste fra din seneste udgave.','grid'],
    editor:['AI-redaktør','DEN REDAKTIONELLE LINJE','Bestem, hvad der er værd at fortælle — og hvorfor.','spark'],
    sources:['Nyhedskilder','INPUT TIL REDAKTIONEN','Vælg, hvor historierne kommer fra.','signal'],
    models:['Modeller & instrukser','DIT AI-HOLD','Giv hvert arbejdstrin den rette opgave.','cpu'],
    images:['Billeder & stil','DEN VISUELLE RETNING','Giv historierne et fælles visuelt udtryk.','image'],
    readers:['Læserne','HVAD BLIVER LÆST?','Se, hvad læserne faktisk finder frem til.','chart'],
    operations:['Drift & arbejdsrum','FRA KLADDE TIL UDGIVELSE','Status, opdateringer og det videre arbejde.','layers']
  };
  const ICONS = {grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',spark:'m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z',signal:'M4 20h2M4 12a8 8 0 0 1 8 8M4 4a16 16 0 0 1 16 16',cpu:'M7 7h10v10H7zM9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4',image:'M3 4h18v16H3zM3 16l6-6 5 5 3-3 4 4M16 8h.01',chart:'M4 19V5M4 19h17M8 15l4-6 4 3 5-7',layers:'m12 3 10 5-10 5L2 8Zm-10 9 10 5 10-5M2 16l10 5 10-5'};
  const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="${ICONS[name] || ICONS.grid}"/></svg>`;
  const fmt = value => typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('da-DK').format(value) : '—';
  const when = value => { const date = new Date(value); return value && Number.isFinite(+date) ? date.toLocaleString('da-DK',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : 'Ingen måling'; };
  const lokal = window.KOMMANDO_LOKAL;
  const lokalAdgang = location.protocol === 'file:' || ['localhost','127.0.0.1','[::1]'].includes(location.hostname);
  const snapshot = lokalAdgang && lokal?.data && lokal.grundlag === (window.KOMMANDO_DATA?.genereret ?? null)
    ? lokal.data : window.KOMMANDO_DATA || {};
  const initial = {feeds: snapshot.tilgaengelige?.feeds ? copy(snapshot.feeds_fil) : null, hjerner:snapshot.tilgaengelige?.hjerner ? copy(snapshot.hjerner_fil) : null, retning:snapshot.tilgaengelige?.redaktoer ? snapshot.redaktoer_instruks : null};
  const state = {snapshot, baseline:copy(initial), drafts:copy(initial), directory:null, view:'overview', query:'', sourceFilter:'all', busy:false, localSaved:false};
  const dirtyKeys = () => Object.keys(PATHS).filter(key => canonical(state.drafts[key]) !== canonical(state.baseline[key]));
  const activeFeeds = () => (state.drafts.feeds?.feeds || []).filter(f => f.aktiv !== false);
  const editorStatus = () => state.snapshot.redaktoer_status || {};
  const brainStatus = () => state.snapshot.hjerner_status || {};
  const sourceStatus = () => state.snapshot.kilder?.kilder || [];
  const articleStatus = () => state.snapshot.artikler || {};
  const badge = (label, type='neutral') => `<span class="badge badge-${type}">${esc(label)}</span>`;
  function notify(message, type='info') { const el=$('app-status'); el.hidden=false; el.className='status-banner '+type; el.textContent=message; }
  function validateConfig(key, value) {
    if(key==='retning') { if(typeof value!=='string' || !value.trim() || value.length>10000) throw new Error('Redaktionens retning skal indeholde 1–10.000 tegn.'); return true; }
    if(!plain(value)) throw new Error('Filen har ikke det forventede indhold: '+PATHS[key]);
    if(key==='feeds') {
      if(!Array.isArray(value.feeds) || !value.feeds.length) throw new Error('Kildelisten må ikke være tom.');
      const names=new Set();
      for(const f of value.feeds) {
        if(!plain(f) || typeof f.navn!=='string' || !f.navn.trim() || typeof f.url!=='string' || !safeUrl(f.url)) throw new Error('Hver kilde skal have et navn og en gyldig http- eller https-adresse.');
        if(names.has(f.navn.trim().toLowerCase())) throw new Error('To kilder må ikke have samme navn.');
        names.add(f.navn.trim().toLowerCase());
        if(f.max!==undefined && (!Number.isInteger(f.max) || f.max<1)) throw new Error('Antal artikler pr. kilde skal være et positivt heltal.');
        if(f.format!==undefined && !['feed','nyhedsoversigt'].includes(f.format)) throw new Error('Ukendt kildeformat: '+f.format);
        if(f.aktiv!==undefined && typeof f.aktiv!=='boolean') throw new Error('Kildens aktiv-felt skal være sandt eller falsk.');
      }
      if(!value.feeds.some(f=>f.aktiv!==false)) throw new Error('Behold mindst én aktiv kilde. Hele automatiseringen kan pauses i GitHub Actions.');
    } else if(key==='hjerner') {
      if(value.modeller!==undefined&&(!Array.isArray(value.modeller)||value.modeller.some(m=>typeof m!=='string'||!(allowedModel('omskriv',m)||allowedModel('billedgenerator',m))))) throw new Error('Ugyldig modelliste.');
      if(value.modelkatalog!==undefined&&(!plain(value.modelkatalog)||Object.entries(value.modelkatalog).some(([n,p])=>!['DeepSeek','Gemini'].includes(n)||!plain(p)||!Array.isArray(p.modeller)||p.modeller.some(m=>typeof m!=='string'||!(allowedModel('omskriv',m)||allowedModel('billedgenerator',m)))))) throw new Error('Ugyldigt API-modelkatalog.');
      if(!plain(value.hjerner)) throw new Error('Dette er ikke en hjerner.json-fil.');
      for(const [name, step] of Object.entries(value.hjerner)) {
        if(['__proto__','constructor','prototype'].includes(name) || !plain(step)) throw new Error('Ugyldigt arbejdstrin.');
        if(step.model!==undefined && typeof step.model!=='string' || step.prompt!==undefined && typeof step.prompt!=='string') throw new Error('Model og instruktion skal være tekst.');
      }
    } else throw new Error('Ukendt indstillingsfil.');
    return true;
  }
  function rememberDraft() {
    try {
      if(dirtyKeys().length) localStorage.setItem('ai-kommandocentral-draft', JSON.stringify({version:1,baseline:state.baseline,drafts:state.drafts}));
      else localStorage.removeItem('ai-kommandocentral-draft');
    } catch (_) { /* Privat tilstand må ikke forhindre redigering og gem. */ }
  }
  function changed() { state.localSaved=false; rememberDraft(); renderDock(); }
  function renderDock() {
    const keys=dirtyKeys(); $('save-dock').hidden=!keys.length;
    $('save-count').textContent=`${keys.length} ${keys.length===1?'fil':'filer'} med ændringer`;
    $('save-detail').textContent=keys.map(k=>NAMES[k]).join(' · ');
    $('save-button').disabled=state.busy;
    $('save-button').textContent=state.busy?'Gemmer …':'Gem i projektmappen';
  }
  function renderNav() {
    $('command-nav').innerHTML=Object.entries(VIEWS).map(([id,v])=>`<button class="nav-item${state.view===id?' is-active':''}" data-view="${id}"${state.view===id?' aria-current="page"':''}><span class="nav-icon">${icon(v[3])}</span>${v[0]}${id==='sources'?`<span class="nav-count">${activeFeeds().length || '—'}</span>`:''}</button>`).join('');
    $('connection-state').textContent=state.directory?'Projektmappe tilsluttet':'Lokalt arbejdsrum';
    $('connection-state').classList.toggle('connected',!!state.directory);
    $('connection-help').textContent=state.directory?`Du arbejder i ${state.directory.name || 'projektmappen'}. Gem lokalt, og push med GitHub Desktop.`:'Tilslut projektmappen for at læse og gemme dine indstillinger direkte.';
  }
  const stat = (label, value, note, name='grid') => `<article class="stat-card"><div class="stat-label">${esc(label)}<span class="stat-icon">${icon(name)}</span></div><strong class="stat-value${/[a-zæøå]/i.test(String(value))?' is-text':''}">${esc(value)}</strong><span class="stat-note">${esc(note)}</span></article>`;
  const panelHead = (title, sub='', action='') => `<div class="panel-head"><div><h2>${esc(title)}</h2>${sub?`<p>${esc(sub)}</p>`:''}</div>${action}</div>`;
  function editorLabel() { const s=editorStatus().status; return s==='godkendt'?'AI-redaktør':s==='reserve'?'Reserve aktiv':s==='genbrugt'?'Tidligere udvalg':s?String(s):'Ikke målt'; }
  function statusRows() {
    const ed=editorStatus(), hs=brainStatus(), errors=sourceStatus().filter(k=>k.status==='fejl');
    const entries=[['AI-redaktør',editorLabel(),ed.status==='godkendt'?'ok':'warn'],['Nyhedskilder',sourceStatus().length?(errors.length?errors.length+' med fejl':'Seneste hentning gennemført'):'Ingen måling',sourceStatus().length&&!errors.length?'ok':'warn'],['Tekstmodel',hs.udbyder==='ingen'?'Ingen tekstnøgle målt':modelLabel(hs.daglig_model)||'Ikke målt',hs.udbyder&&hs.udbyder!=='ingen'?'ok':'warn'],['Billedgenerator',hs.billedmodel&&hs.billedmodel!=='ingen'?hs.billedmodel:'Ingen aktiv model målt',hs.billedmodel&&hs.billedmodel!=='ingen'?'ok':'warn']];
    return entries.map(([name,label,type])=>`<div class="status-row"><span class="dot dot-${type}" aria-hidden="true"></span><div><strong>${esc(name)}</strong><small>${esc(label)}</small></div></div>`).join('');
  }
  function stories(items) {
    if(!items?.length) return '<div class="empty-state">Den seneste udgave har endnu ikke noget udvalg at vise.</div>';
    return items.slice(0,3).map((a,i)=>`<article class="story-preview"><span class="story-number">0${i+1}</span><div class="story-info"><span class="story-category">${esc(a.kategori||'AI-nyhed')}</span><h3>${safeUrl(a.link)?`<a href="${esc(safeUrl(a.link))}" target="_blank" rel="noopener">${esc(a.rubrik||a.titel)} <span aria-hidden="true">↗</span></a>`:esc(a.rubrik||a.titel)}</h3><div class="story-meta">${esc(a.kilde||'Kilde ukendt')} · ${esc(when(a.dato))}</div></div></article>`).join('');
  }
  function overview() {
    const a=articleStatus(), ed=editorStatus(), errors=sourceStatus().filter(k=>k.status==='fejl');
    return `<div class="stat-grid">${stat('Historier i udgaven',fmt(a.antal),'Senest udgivne artikeldata','layers')}${stat('Aktive kilder',state.drafts.feeds?fmt(activeFeeds().length):'—',`${state.drafts.feeds?.feeds?.length || 0} kilder i opsætningen`,'signal')}${stat('Forsidens udvalg',editorLabel(),ed.status==='reserve'?'Redaktørens reserve har taget over':'Status fra seneste redaktionsmøde','spark')}${stat('Med illustration',fmt(a.med_billede),'Billeder gemt sammen med artiklerne','image')}</div>
    <div class="dashboard-grid"><section class="panel">${panelHead('På forsiden lige nu','Senest udgivne udvalg',badge('UDGIVET','green'))}<div class="panel-body">${stories(a.udvalgte)}</div></section>
    <section class="panel">${panelHead('Maskinrummet','Målt '+when(a.opdateret),`<button class="btn btn-quiet" data-view="operations">Se drift ↗</button>`)}<div class="panel-body">${statusRows()}${ed.status==='reserve'?`<div class="notice notice-warn"><strong>Redaktøren skal have opmærksomhed</strong><p>${esc(ed.forklaring||'Den almindelige prioritering bruges i denne udgave.')}</p><button class="btn btn-quiet" data-view="editor">Se redaktionsmødet →</button></div>`:''}${errors.length?`<div class="notice notice-warn">${esc(errors.map(k=>k.navn).join(', '))} havde fejl ved seneste hentning.</div>`:''}</div></section></div>
    <section class="panel quick-panel">${panelHead('Tag styringen','De vigtigste greb er ét klik væk.')}<div class="quick-grid"><button class="quick-action" data-view="editor">${icon('spark')}<span><strong>Sæt retningen</strong><small>Fortæl redaktøren, hvad du vil læse.</small></span><b>↗</b></button><button class="quick-action" data-view="sources">${icon('signal')}<span><strong>Skær støjen fra</strong><small>Justér kilder og antal kandidater.</small></span><b>↗</b></button><button class="quick-action" data-view="images">${icon('image')}<span><strong>Giv billederne karakter</strong><small>Redigér instruktionen til motiverne.</small></span><b>↗</b></button></div></section>
    <div class="workflow-strip"><span>DIN ARBEJDSGANG</span><b>Vælg retning</b><i>→</i><b>Gem lokalt</b><i>→</i><b>Push i GitHub</b><i>→</i><b>Næste udgave</b></div>`;
  }
  function editor() {
    const e=editorStatus(), calls=e.vaerktoejer||[];
    return `<div class="settings-grid"><section class="panel">${panelHead('Din redaktionelle linje','Det er denne tekst, forside-redaktøren arbejder efter.',badge('KAN REDIGERES','green'))}<div class="panel-body"><div class="field"><label for="editor-direction">Hvad skal redaktøren prioritere?</label><textarea class="prompt-editor" id="editor-direction" data-field="direction" rows="20" maxlength="10000"${state.drafts.retning===null?' disabled':''}>${esc(state.drafts.retning||'')}</textarea><small class="help"><span id="direction-count">${(state.drafts.retning||'').length}</span> / 10.000 tegn · Gemmes i opsaetning/redaktoer.md</small></div><div class="notice">Vær konkret om nyheder, du vil se mere og mindre af. Agenten vurderer stadig kilderne og samler omtaler af samme begivenhed.</div></div></section>
    <div><section class="panel">${panelHead('Seneste redaktionsmøde',when(e.opdateret),badge(editorLabel(),e.status==='godkendt'?'green':'amber'))}<div class="panel-body"><p>${esc(e.forklaring||'Der er ikke noget redaktionsmøde i de tilgængelige data.')}</p><div class="split-summary"><div><strong>${fmt(e.modelkald)}</strong><span>modelkald</span></div><div><strong>${fmt(e.kildehentninger)}</strong><span>kilder læst</span></div></div><div class="status-row"><span class="stat-icon">${icon('cpu')}</span><div><strong>Redaktørens model</strong><small>${esc(modelLabel(e.model||brainStatus().daglig_model)||'Ikke målt')}</small></div></div><small class="help">Du kan ændre agentens præcise model under Modeller & instrukser → Vælg forsiden.</small></div></section>
    <section class="panel">${panelHead('Fra mødet',calls.length?'De seneste værktøjskald':'Ingen værktøjskald registreret')}<div class="panel-body">${calls.slice(-5).map(c=>`<div class="activity-row"><span class="dot ${c.fejl?'dot-warn':'dot-ok'}"></span><div><strong>${esc(c.vaerktoej==='laes_kilde'?'Læs kilde':c.vaerktoej==='find_kilder'?'Find kilder':c.vaerktoej)}</strong><p>${esc(c.fejl||'Gennemført')}</p></div></div>`).join('')}</div></section></div></div>`;
  }
  function sources() {
    return `<div class="source-toolbar"><label class="search-input"><span class="sr-only">Find en kilde</span><input type="search" id="source-search" placeholder="Find en kilde …" value="${esc(state.query)}"></label><div class="segmented" aria-label="Vis kilder">${[['all','Alle'],['active','Aktive'],['paused','Pausede']].map(([v,t])=>`<button data-source-filter="${v}" class="${state.sourceFilter===v?'is-active':''}" aria-pressed="${state.sourceFilter===v}">${t}</button>`).join('')}</div><button class="btn btn-primary" data-action="add-source"${!state.drafts.feeds?' disabled':''}>+ Tilføj kilde</button></div><div class="notice">Kilderne leverer kandidater. AI-redaktøren vælger historierne på tværs. Pauser du en kilde, stopper nye hentninger efter næste push.</div><div id="source-list" class="source-list">${sourceRows()}</div>`;
  }
  function sourceRows() {
    const feeds=state.drafts.feeds?.feeds;
    if(!feeds) return '<div class="empty-state">Tilslut projektmappen for at læse dine kilder.</div>';
    const filtered=feeds.map((f,i)=>({f,i})).filter(({f})=>(state.sourceFilter==='all'||(state.sourceFilter==='active')===(f.aktiv!==false))&&(f.navn+' '+f.url).toLowerCase().includes(state.query.toLowerCase()));
    if(!filtered.length) return '<div class="empty-state">Ingen kilder matcher. Prøv en anden søgning.</div>';
    return filtered.map(({f,i})=>{ const s=sourceStatus().find(s=>s.navn===f.navn), paused=f.aktiv===false; return `<article class="source-card${paused?' is-paused':''}"><span class="source-logo" aria-hidden="true">${esc(f.navn.split(/\s+/).map(w=>w[0]).slice(0,2).join(''))}</span><div class="source-info"><h3>${esc(f.navn)} ${badge(paused?'Pauset':s?.status==='fejl'?'Hentning fejlede':'Aktiv',paused?'neutral':s?.status==='fejl'?'amber':'green')}</h3><p>${esc(hostname(f.url))} <span>· ${f.format==='nyhedsoversigt'?'Nyhedsoversigt':'RSS / Atom'} · Op til ${esc(f.max||25)} kandidater</span></p>${s?.status==='fejl'?`<small class="source-error">${esc(s.fejl||'Ukendt kildefejl')}</small>`:`<small>${s?`${fmt(s.hentet)} hentet · ${fmt(s.i_listen)} i udgaven ved seneste måling`:'Ingen måling for denne kilde endnu'}</small>`}</div><div class="source-controls"><label class="toggle-row"><span class="sr-only">Aktivér ${esc(f.navn)}</span><input type="checkbox" data-source-toggle="${i}" role="switch"${paused?'':' checked'}><span class="toggle-track" aria-hidden="true"></span></label><button class="btn btn-secondary" data-edit-source="${i}">Redigér</button></div></article>`; }).join('');
  }
  // Versionsnavn fra projektets konfiguration (10.09.2026).
  // API-aliaset beholdes synligt og sendes uændret til udbyderen.
  const FLUX_MODEL='@cf/black-forest-labs/flux-2-klein-4b';
  const MODEL_NAMES = {[FLUX_MODEL]:'FLUX.2 Klein 4B','deepseek-flash':'DeepSeek V4.1 Flash'};
  const modelLabel = id => MODEL_NAMES[id] ? MODEL_NAMES[id]+' · '+id : id;
  function modelDefault(name) {
    const h=brainStatus();
    return name==='forside_agent' ? (h.forside_standard||'deepseek-flash') : name==='billedgenerator' ? (h.billed_standard||'gemini-3.1-flash-lite-image') : h.daglig_model||'';
  }
  function reportedModel(name) {
    return name==='forside_agent'?editorStatus().model:name==='billedgenerator'?brainStatus().billedmodel:brainStatus().hjerner?.[name]?.model;
  }
  function allowedModel(name,m) {
    if(m===FLUX_MODEL) return name==='billedgenerator';
    return /^(deepseek|gemini)[a-z0-9._-]*$/i.test(m) && (name!=='forside_agent'||m.startsWith('deepseek')) && (name!=='billedgenerator'||m.startsWith('gemini')&&m.includes('image'));
  }
  function providerCatalog(name) {
    const local=state.drafts.hjerner?.modelkatalog?.[name],remote=state.snapshot.modelkatalog?.udbydere?.[name];
    return local&&(!remote||!(Date.parse(remote.opdateret)>Date.parse(local.opdateret)))?local:remote||{};
  }
  function modelList(name) {
    return [...new Set([FLUX_MODEL,...(state.drafts.hjerner?.modeller||[]),...['DeepSeek','Gemini'].flatMap(n=>providerCatalog(n).modeller||[]),...Object.values(state.drafts.hjerner?.hjerner||{}).map(s=>s.model),...Object.keys(STEP_NAMES).flatMap(n=>[modelDefault(n),reportedModel(n)])])].filter(m=>typeof m==='string'&&allowedModel(name,m)).sort();
  }
  function models() {
    const h=brainStatus();
    return `<section class="panel"><div class="panel-body"><div class="inline-actions"><span class="badge badge-green">Automatisk opdatering hver dag</span><button class="btn btn-secondary" data-action="model-list">Administrér modelliste</button><a class="btn btn-secondary" href="https://github.com/ainyheder/AI-nyheder/actions/workflows/modeller.yml" target="_blank" rel="noopener">Se automatisk opdatering ↗</a></div><p>GitHub henter hver dag modellisterne fra DeepSeek og Gemini med de eksisterende hemmelige nøgler. Hent projektets ændringer med Pull i GitHub Desktop og genindlæs centralen. Nye modeller bliver valgbare; dine modelvalg ændres ikke automatisk.</p><small class="help">${['DeepSeek','Gemini'].map(n=>{const p=providerCatalog(n);return esc(n)+': '+(p.modeller?.length||0)+' modeller · '+esc(p.status||'Ikke hentet')+' · '+esc(when(p.opdateret));}).join(' · ')||'Modellisterne er endnu ikke hentet fra udbyderne.'}</small></div></section><div class="notice">“Valgt til næste kørsel” er din indstilling. “Senest rapporteret” er crawlerens status, ikke en garanti for, at alle kald lykkedes. Ved API-fejl kan crawleren bruge sin reserve.</div><div class="model-grid">${Object.entries(STEP_NAMES).map(([n,title])=>{const own=state.drafts.hjerner?.hjerner?.[n],s=h.hjerner?.[n]||{},m=own?.model||modelDefault(n);return `<button class="model-card" data-edit-model="${n}"${!state.drafts.hjerner?' disabled':''}><div class="model-card-top">${badge(m===FLUX_MODEL?'Cloudflare':m.startsWith('deepseek')?'DeepSeek':'Gemini', 'green')}${badge(own?.model?'Eget valg':'Standard')}</div><h2>${title}</h2><p>${esc(s.beskrivelse||(n==='forside_agent'?'Vælger og prioriterer historier på tværs af kilder.':'Tegner billeder ud fra motivbeskrivelsen.'))}</p><small>Valgt til næste kørsel</small><div class="model-card-foot"><div>${MODEL_NAMES[m]?`<strong>${esc(MODEL_NAMES[m])}</strong><br>`:''}<code>${esc(m||'Standard ikke rapporteret')}</code></div><span>Skift ↗</span></div><small>Senest rapporteret: ${esc(modelLabel(reportedModel(n))||'Ikke målt')}</small>${(m.startsWith('deepseek')&&h.deepseek_tilgaengelig===false||m.startsWith('gemini')&&h.gemini_tilgaengelig===false)?'<p class="source-error">API-nøgle manglede ved seneste måling.</p>':''}</button>`;}).join('')}</div>`;
  }
  function images() {
    const h=brainStatus(),a=articleStatus(),p=state.drafts.hjerner?.hjerner?.motiv?.prompt || h.hjerner?.motiv?.standard_prompt || '';
    const count=typeof a.med_billede==='number'&&a.antal?Math.round(a.med_billede/a.antal*100):0;
    return `<div class="settings-grid"><section class="panel">${panelHead('Billeder med en tydelig idé','Instruktionen bruges, når AI beskriver motivet til en artikel.')}<div class="panel-body"><div class="field"><label for="image-direction">Din instruktion til billedmotiver</label><textarea id="image-direction" data-field="image-prompt" class="prompt-editor" rows="20"${!state.drafts.hjerner?' disabled':''}>${esc(p)}</textarea><small class="help">Motivbeskrivelsen styrer, hvad der tegnes. Den vælger ikke billedgeneratoren.</small></div><button class="btn btn-secondary" data-action="reset-image">Brug standardinstruktionen</button></div></section>
    <div><section class="panel image-status">${panelHead('Den visuelle dækning','Eksisterende illustrationer i den seneste udgave')}<div class="panel-body"><div class="split-summary"><div><strong>${fmt(a.med_billede)}</strong><span>med billede</span></div><div><strong>${fmt(a.antal)}</strong><span>historier i alt</span></div></div><div class="meter-track" role="meter" aria-label="Andel historier med billede" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${count}"><span class="meter-fill" style="width:${count}%"></span></div><div class="status-row"><span class="stat-icon">${icon('image')}</span><div><strong>Generator ved seneste kørsel</strong><small>${esc(h.billedmodel||'Ikke målt')}</small></div></div><p class="help">Nye illustrationer fritlægges med BiRefNet General og gemmes som gennemsigtig WebP. Hvis behandlingen fejler eller masken afvises, bruges originalen. Eksisterende billeder genbruges.</p></div></section><section class="panel">${panelHead('FLUX.2 Klein 4B','Cloudflare Workers AI')}<div class="panel-body"><p>FLUX.2 Klein 4B er tilsluttet i crawleren. Kræver Cloudflare-token med Workers AI-adgang. Derefter fjerner BiRefNet General (birefnet-general) baggrunden på GitHubs server. Dette trin kræver ingen API-nøgle.</p><button class="btn btn-secondary" data-edit-model="billedgenerator">Redigér billedmodellens stil</button></div></section></div></div>`;
  }
  function readers() {
    const l=state.snapshot.laesertal||{},available=state.snapshot.tilgaengelige?.laesertal && l.maaling==='ok' && typeof l.besoeg_i_alt==='number';
    if(!available) return `<section class="panel"><div class="empty-state">${icon('chart')}<h2>Ingen læsertal tilgængelige</h2><p>Der er ikke en brugbar måling i det seneste datasæt. Det betyder ikke, at siden har nul besøgende.</p><a class="btn btn-secondary" href="_redaktion/kontrolpanel.html" target="_blank" rel="noopener">Åbn avanceret læseranalyse ↗</a></div></section>`;
    const pages=l.sider||[];
    return `<div class="stat-grid">${stat('Besøg',fmt(l.besoeg_i_alt),`Måleperiode: ${l.dage||7} dage`,'chart')}${stat('Sidevisninger',fmt(l.sidevisninger_i_alt),'I samme måleperiode','layers')}${stat('Fra AI-tjenester',fmt(l.ai_chat_besoeg),'Registrerede henvisninger fra AI-chat','spark')}</div><section class="panel">${panelHead('Læsernes mest besøgte sider','Målt '+when(l.opdateret),'<a class="btn btn-quiet" href="_redaktion/kontrolpanel.html" target="_blank" rel="noopener">Fuld læseranalyse ↗</a>')}<div class="table-wrap"><table><thead><tr><th>Side</th><th>Besøg</th><th>Sidevisninger</th></tr></thead><tbody>${pages.slice(0,10).map(p=>`<tr><td>${esc(p.rubrik||p.titel||p.sti||p.side||p.path||'Ukendt side')}</td><td>${fmt(p.besoeg??p.visits)}</td><td>${fmt(p.visninger??p.sidevisninger??p.pageviews)}</td></tr>`).join('')}</tbody></table></div></section>`;
  }
  function operations() {
    const e=editorStatus(),errors=sourceStatus().filter(k=>k.status==='fejl');
    return `<div class="settings-grid"><section class="panel">${panelHead('Sådan bliver dine ændringer udgivet','Tre trin fra beslutning til ny udgave.')}<div class="panel-body"><div class="activity-row"><span class="story-number">01</span><div><strong>Gem i projektmappen</strong><p>Tilslut AI NEWS med knappen til venstre. Gem ændringerne direkte i de eksisterende indstillingsfiler.</p></div></div><div class="activity-row"><span class="story-number">02</span><div><strong>Push med GitHub Desktop</strong><p>Gennemse ændringerne, lav et commit og push. Centralen hverken committer eller sender noget automatisk.</p></div></div><div class="activity-row"><span class="story-number">03</span><div><strong>Følg opdateringen</strong><p>Push starter den eksisterende crawler. Den kan også startes manuelt i GitHub Actions.</p><a class="btn btn-primary" href="https://github.com/ainyheder/AI-nyheder/actions/workflows/crawl.yml" target="_blank" rel="noopener">Åbn GitHub Actions ↗</a></div></div></div></section><section class="panel">${panelHead('Seneste drift','Dette er et øjebliksbillede, ikke en liveforbindelse.')}<div class="panel-body">${statusRows()}<div class="notice ${e.status==='reserve'||errors.length?'notice-warn':''}">${esc(e.forklaring||'Der er ingen yderligere status fra redaktionsmødet.')}</div><p class="help">Automatisk kørsel hver time hele døgnet, 37 minutter over timen, samt ved push. Den aktuelle kørsel og log findes i GitHub.</p></div></section></div><section class="panel">${panelHead('Det videre arbejde','Dine eksisterende redaktionsværktøjer er bevaret.')}<div class="quick-grid"><a class="quick-action" href="_redaktion/kontrolpanel.html" target="_blank" rel="noopener">${icon('layers')}<span><strong>Opgaver, ønsker & historik</strong><small>Åbn de avancerede redaktionsværktøjer.</small></span><b>↗</b></a><a class="quick-action" href="https://github.com/ainyheder/AI-nyheder/issues" target="_blank" rel="noopener">${icon('signal')}<span><strong>Forslag fra gennemgangen</strong><small>Se projektets issues på GitHub.</small></span><b>↗</b></a></div></section>`;
  }
  const renderers={overview,editor,sources,models,images,readers,operations};
  function render() {
    const v=VIEWS[state.view];renderNav();$('page-eyebrow').textContent=v[1];$('page-heading').textContent=v[0];$('page-description').textContent=v[2];
    $('snapshot-label').textContent='Sidste udgave · '+when(articleStatus().opdateret);
    $('view-content').innerHTML=renderers[state.view](); renderDock();
  }
  function navigate(view) {
    if(!VIEWS[view]) return;state.view=view;render();document.body.classList.remove('nav-open');$('mobile-nav').setAttribute('aria-expanded','false');
    try {history.replaceState(null,'','#'+view);} catch (_) {}
    $('view-content').focus({preventScroll:true});
  }
  async function getFile(directory, path) {
    const parts=path.split('/');let dir=directory;
    for(const part of parts.slice(0,-1)) dir=await dir.getDirectoryHandle(part);
    return dir.getFileHandle(parts.at(-1));
  }
  async function readConfig(directory,key) {
    const handle=await getFile(directory,PATHS[key]);const raw=await (await handle.getFile()).text();
    let value;
    try {value=key==='retning'?raw:JSON.parse(raw);} catch (_) {throw new Error('Filen kan ikke læses som JSON: '+PATHS[key]);}
    validateConfig(key,value);return {handle,value};
  }
  async function connectDirectory(directory) {
    // Læs alle filer før tilstanden ændres, så en forkert mappe ikke giver et halvt grundlag.
    const loaded={};for(const key of Object.keys(PATHS)) loaded[key]=(await readConfig(directory,key)).value;
    for(const key of dirtyKeys()) if(canonical(loaded[key])!==canonical(state.baseline[key])) throw new Error('Projektfilen er ændret siden din kladde: '+PATHS[key]+'. Hent kladden som fil, før du genindlæser.');
    const changedKeys=new Set(dirtyKeys());
    for(const key of Object.keys(PATHS)) {state.baseline[key]=copy(loaded[key]);if(!changedKeys.has(key)) state.drafts[key]=copy(loaded[key]);}
    state.directory=directory;rememberDraft();render();notify('Projektmappen er tilsluttet. Indstillingerne er læst direkte fra filerne.','success');return true;
  }
  async function connect() {
    if(!window.showDirectoryPicker) {notify('Direkte filgem kræver Chrome eller Edge. Åbn Indstillinger.html dér, eller brug “Hent ændrede filer” og læg filerne i de viste mapper.');return false;}
    const dir=await window.showDirectoryPicker({mode:'readwrite',id:'ai-news-project'});return connectDirectory(dir);
  }
  async function saveChanges() {
    if(state.busy) return false;
    const keys=dirtyKeys();if(!keys.length) return false;
    if(!state.directory) {await connect();if(!state.directory) return false;}
    state.busy=true;renderDock();const saved=[];
    try {
      // Tjek alle berørte filer før første skrivning. JSON-nøglernes rækkefølge er uden betydning.
      const files={};for(const key of keys) {validateConfig(key,state.drafts[key]);files[key]=await readConfig(state.directory,key);if(canonical(files[key].value)!==canonical(state.baseline[key])) throw new Error('En anden proces har ændret '+PATHS[key]+'. Intet er overskrevet. Din kladde er bevaret.');}
      for(const key of keys) {
        // Fang også en ændring, som skete efter forberedelsen af de øvrige filer.
        const latest=await readConfig(state.directory,key);if(canonical(latest.value)!==canonical(state.baseline[key])) throw new Error('Filen blev ændret under gem: '+PATHS[key]);
        const value=copy(state.drafts[key]);validateConfig(key,value);const text=key==='retning'?value:JSON.stringify(value,null,2)+'\n';
        const stream=await latest.handle.createWritable();
        try {await stream.write(text);await stream.close();} catch(error) {try {await stream.abort();} catch(_) {} throw error;}
        const written=await readConfig(state.directory,key);if(canonical(written.value)!==canonical(value)) throw new Error('Gemningen kunne ikke bekræftes for '+PATHS[key]);
        state.baseline[key]=copy(value);saved.push(key);rememberDraft();
      }
      state.localSaved=true;notify('Gemt i projektmappen. Næste trin: commit og push i GitHub Desktop. Siden er ikke udgivet endnu.','success');return true;
    } catch(error) {
      notify((saved.length?NAMES[saved[0]]+' er gemt. De resterende ændringer er bevaret som kladde. ':'')+(error.message||'Kunne ikke gemme filerne.'),'error');throw error;
    } finally {state.busy=false;renderDock();}
  }
  function download(key) {
    validateConfig(key,state.drafts[key]);const text=key==='retning'?state.drafts[key]:JSON.stringify(state.drafts[key],null,2)+'\n';
    const href=URL.createObjectURL(new Blob([text],{type:key==='retning'?'text/markdown;charset=utf-8':'application/json'}));const a=document.createElement('a');a.href=href;a.download=PATHS[key].split('/').at(-1);document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),1000);
    notify('Filen er hentet. Læg den i '+PATHS[key]+'. Den er ikke gemt i projektet eller udgivet.');
  }
  function openDialog(title,body) {
    $('dialog-content').innerHTML=`<div class="panel-head"><h2 id="dialog-title">${esc(title)}</h2><button class="btn btn-quiet" data-action="close-dialog" aria-label="Luk dialog">✕</button></div><div class="panel-body">${body}</div>`;
    $('edit-dialog').showModal();
  }
  function editSource(index) {
    const f=index===null?{navn:'',url:'',kategori:'Labs',max:12}:state.drafts.feeds.feeds[index];
    openDialog(index===null?'Tilføj nyhedskilde':f.navn,`<form id="source-form" data-index="${index===null?'new':index}"><div class="settings-grid"><div class="field"><label for="source-name">Kildens navn</label><input id="source-name" name="navn" value="${esc(f.navn)}" required></div><div class="field"><label for="source-max">Kandidater pr. kørsel</label><input id="source-max" type="number" name="max" min="1" value="${esc(f.max||25)}" required></div><div class="field field-wide"><label for="source-url">Feed eller nyhedsoversigt</label><input id="source-url" name="url" type="url" value="${esc(f.url)}" placeholder="https://…" required></div><div class="field"><label for="source-format">Format</label><select id="source-format" name="format"><option value="feed"${f.format!=='nyhedsoversigt'?' selected':''}>RSS / Atom</option><option value="nyhedsoversigt"${f.format==='nyhedsoversigt'?' selected':''}>Dateret nyhedsoversigt</option></select></div><div class="field"><label for="source-category">Reservekategori</label><input id="source-category" name="kategori" value="${esc(f.kategori||'Nyheder')}"></div><div class="field field-wide"><label class="checkbox-label"><input type="checkbox" name="kun_aktuel"${f.kun_aktuel?' checked':''}> Kun aktuelle overskrifter — ingen arkivering eller genfortælling</label></div></div><p class="help">Nyhedsoversigter er understøttet for Anthropic og xAI. En ny adresse kræver en kontrol af, at crawleren kan læse den.</p><p class="form-error" id="source-error" role="alert"></p><div class="inline-actions"><button class="btn btn-primary" type="submit">Brug ændringer</button><button class="btn btn-secondary" type="button" data-action="close-dialog">Annullér</button></div></form>`);
  }
  function editModel(name) {
    if(!STEP_NAMES[name]||!state.drafts.hjerner) return;
    const h=name==='billedgenerator'?{standard_prompt:brainStatus().billed_standard_prompt||''}:brainStatus().hjerner?.[name]||{},own=state.drafts.hjerner.hjerner[name]||{},special=name==='forside_agent';
    openDialog(STEP_NAMES[name],`<form id="model-form" data-step="${name}"><div class="field"><label for="step-model">Vælg præcis model</label><select id="step-model" name="model"><option value="">Standard · ${esc(modelLabel(modelDefault(name)))}</option>${modelList(name).map(m=>`<option value="${esc(m)}"${own.model===m?' selected':''}>${esc(modelLabel(m))}</option>`).join('')}<option value="manual">Skriv et nyt model-ID …</option></select></div><div class="field" id="manual-model-field" hidden><label for="manual-model">Nyt model-ID fra udbyderen</label><input id="manual-model" name="manualModel" placeholder="Præcist API-navn"></div><p class="help">${name==='forside_agent'?'Forsideagenten bruger DeepSeek med værktøjskald.':name==='billedgenerator'?'Vælg FLUX.2 Klein 4B via Cloudflare eller en Gemini-billedmodel.':'DeepSeek og Gemini er understøttet.'} Listen er ikke en garanti for adgang eller kvote på din konto.</p>${special?'':`<div class="field"><label for="step-prompt">${name==='billedgenerator'?'Visuel stil til billedgeneratoren':'Instruktion'}</label><textarea id="step-prompt" name="prompt" rows="16">${esc(own.prompt||h.standard_prompt||'')}</textarea></div>`}<p class="form-error" id="model-error" role="alert"></p><div class="inline-actions"><button class="btn btn-primary" type="submit">Brug ændringer</button><button class="btn btn-secondary" type="button" data-reset-model="${name}">Gendan indbygget standard</button></div></form>`);
  }
  function setOverride(name,fields) {
    const all=state.drafts.hjerner.hjerner,old=copy(all[name]||{});
    for(const key of ['model','prompt']) if(fields[key]?.trim()) old[key]=fields[key].trim();else delete old[key];
    if(Object.keys(old).length) all[name]=old;else delete all[name];changed();
  }
  document.addEventListener('click',async event=>{
    const view=event.target.closest('[data-view]');if(view) {navigate(view.dataset.view);return;}
    const filter=event.target.closest('[data-source-filter]');if(filter) {state.sourceFilter=filter.dataset.sourceFilter;render();return;}
    const source=event.target.closest('[data-edit-source]');if(source) {editSource(Number(source.dataset.editSource));return;}
    const model=event.target.closest('[data-edit-model]');if(model) {editModel(model.dataset.editModel);return;}
    const reset=event.target.closest('[data-reset-model]');if(reset) {setOverride(reset.dataset.resetModel,{});$('edit-dialog').close();render();return;}
    const target=event.target.closest('[data-action]');if(!target)return;
    try {
      switch(target.dataset.action) {
        case 'model-list': if(!state.drafts.hjerner) break;openDialog('Din modelliste', `<form id="catalog-form"><p>Tilføj præcise API-navne, ét pr. linje. Manuelle modeller er ikke adgangskontrolleret. Udbydernes modeller og eksisterende valg bliver fortsat vist.</p><div class="field"><label for="catalog-models">Manuelt tilføjede modeller</label><textarea id="catalog-models" rows="12">${esc((state.drafts.hjerner.modeller||[]).join('\n'))}</textarea></div><p id="catalog-error" class="form-error" role="alert"></p><button class="btn btn-primary">Brug modellisten</button></form>`);break;
        case 'connect': await connect();break;
        case 'save': await saveChanges();break;
        case 'close-dialog': $('edit-dialog').close();break;
        case 'close-nav': document.body.classList.remove('nav-open');$('mobile-nav').setAttribute('aria-expanded','false');break;
        case 'add-source': editSource(null);break;
        case 'reset-image': {const own=state.drafts.hjerner?.hjerner.motiv;if(own) {delete own.prompt;if(!Object.keys(own).length)delete state.drafts.hjerner.hjerner.motiv;}changed();render();break;}
        case 'discard': if(window.confirm('Fortryd de ændringer, som endnu ikke er gemt i projektmappen?')) {state.drafts=copy(state.baseline);changed();render();notify('De ugemte ændringer er fortrudt.');}break;
        case 'export': openDialog('Hent dine ændringer',`<p>Hent hver fil, og læg den på den viste placering i projektmappen. Derefter kan du committe og pushe.</p>${dirtyKeys().map(key=>`<div class="status-row"><code>${PATHS[key]}</code><button class="btn btn-secondary" data-download="${key}">Hent fil ↓</button></div>`).join('')}`);break;
        case 'refresh': if(dirtyKeys().length) {notify('Gem eller hent din kladde først. En genindlæsning erstatter grundlaget for indstillingerne.');break;}location.reload();break;
      }
    } catch(error) {if(error.name!=='AbortError')notify(error.message||'Handlingen kunne ikke gennemføres.','error');}
  });
  document.addEventListener('click',event=>{const button=event.target.closest('[data-download]');if(button)try {download(button.dataset.download);}catch(error){notify(error.message,'error');}});
  document.addEventListener('input',event=>{
    if(event.target.id==='source-search') {state.query=event.target.value;$('source-list').innerHTML=sourceRows();}
    if(event.target.dataset.field==='direction') {state.drafts.retning=event.target.value;$('direction-count').textContent=event.target.value.length;changed();}
    if(event.target.dataset.field==='image-prompt'&&state.drafts.hjerner) {const existing=state.drafts.hjerner.hjerner.motiv||{};setOverride('motiv',{model:existing.model,prompt:event.target.value===brainStatus().hjerner?.motiv?.standard_prompt?'':event.target.value});}
  });
  document.addEventListener('change',event=>{
    if(event.target.id==='step-model') $('manual-model-field').hidden=event.target.value!=='manual';
    const index=event.target.dataset.sourceToggle;if(index!==undefined) {state.drafts.feeds.feeds[Number(index)].aktiv=event.target.checked;changed();renderNav();$('source-list').innerHTML=sourceRows();}
  });
  document.addEventListener('submit',async event=>{
    if(event.target.id==='source-form') {
      event.preventDefault();const f=event.target,elements=f.elements,index=f.dataset.index,candidate=copy(state.drafts.feeds);
      const row=index==='new'?{}:candidate.feeds[Number(index)];Object.assign(row,{navn:elements.navn.value.trim(),url:elements.url.value.trim(),max:Number(elements.max.value),format:elements.format.value,kategori:elements.kategori.value.trim(),kun_aktuel:elements.kun_aktuel.checked});
      if(index==='new')candidate.feeds.push(row);
      try {validateConfig('feeds',candidate);state.drafts.feeds=candidate;changed();$('edit-dialog').close();render();}catch(error){$('source-error').textContent=error.message;}
    }
    if(event.target.id==='catalog-form') {
      event.preventDefault();const models=[...new Set($('catalog-models').value.split(/\s+/).filter(Boolean))];
      if(models.some(m=>!allowedModel('omskriv',m))) {$('catalog-error').textContent='Brug præcise DeepSeek- eller Gemini-modelnavne.';return;}
      state.drafts.hjerner.modeller=models;changed();$('edit-dialog').close();render();
    }
    if(event.target.id==='model-form') {
      event.preventDefault();const f=event.target,name=f.dataset.step,model=(f.elements.model.value==='manual'?f.elements.manualModel.value:f.elements.model.value).trim(),prompt=f.elements.prompt?.value||'';
      const original=state.drafts.hjerner.hjerner[name]?.model;
      if(model&&model!==original&&!allowedModel(name,model)) {$('model-error').textContent='Vælg en understøttet model til dette trin, som din API-konto har adgang til.';return;}
      if(f.elements.model.value==='manual'&&!model) {$('model-error').textContent='Skriv et model-ID.';return;}
      if(model) state.drafts.hjerner.modeller=[...new Set([...(state.drafts.hjerner.modeller||[]),model])];
      setOverride(name,{model,prompt:prompt===brainStatus().hjerner?.[name]?.standard_prompt?'':prompt});$('edit-dialog').close();render();
    }
  });
  $('mobile-nav').addEventListener('click',()=>{const open=document.body.classList.toggle('nav-open');$('mobile-nav').setAttribute('aria-expanded',String(open));});
  document.addEventListener('keydown',e=>{if(e.key==='Escape') {document.body.classList.remove('nav-open');$('mobile-nav').setAttribute('aria-expanded','false');}});
  window.addEventListener('beforeunload',event=>{if(dirtyKeys().length){event.preventDefault();event.returnValue='';}});
  try {
    const stored=JSON.parse(localStorage.getItem('ai-kommandocentral-draft')||'null');
    if(stored?.version===1 && plain(stored.drafts)) {
      if(canonical(stored.baseline)===canonical(state.baseline)) {
        for(const key of Object.keys(PATHS)) if(stored.drafts[key]!==null)validateConfig(key,stored.drafts[key]);
        state.drafts=stored.drafts;notify('Din tidligere kladde er gendannet. Den er endnu ikke gemt i projektmappen.');
      } else notify('Der findes en ældre kladde fra et andet grundlag. De aktuelle indstillinger vises; den ældre kladde er bevaret i browseren.');
    }
  }catch(_){ /* En ødelagt lokal kladde må ikke forhindre adgang til projektet. */ }
  const hash=location.hash.slice(1);if(VIEWS[hash])state.view=hash;
  render();
  if(!snapshot.version)notify('Statusfilen kunne ikke læses. Tilslut projektmappen for at redigere indstillinger, eller hent projektets seneste opdatering.','error');
  window.Kommando={canonical,validateConfig,state,render,navigate,connectDirectory,saveChanges,dirtyKeys,setOverride,modelList};
})();
