/* AI-nyheder: almindelig HTML, små datafiler og ingen byggetrin.
   Redaktionens rækkefølge kommer fra crawleren. Reserven herunder holder
   gamle data læsbare og er dækket af de samme fixtures som Python. */
(function (root) {
  "use strict";
  const WEIGHTS = {nyhed:6, betydning:5, brugbarhed:5, dokumentation:4, dansk:0};
  const VERSION = 3;
  const MODEL_BONUS = 36;
  const HOUR = 3600000;
  const number = x => typeof x === "number" && Number.isFinite(x);
  function assessment(a) {
    const v = a.redaktion;
    return v && [2, VERSION].includes(v.version) && Object.keys(WEIGHTS).every(k => Number.isInteger(v[k]) && v[k] >= 0 && v[k] <= 5) ? v : null;
  }
  function timestamp(a) {
    for (const value of [a.dato, a.eget_foerst_set, a.foerst_set]) {
      if (!value) continue;
      if(typeof value!=="string" || !/^\d{4}-\d{2}-\d{2}(?:T|$)/.test(value))continue;
      const iso=value.includes("T")&&!/(Z|[+-]\d{2}:?\d{2})$/i.test(value)?value+"Z":value;
      const n = Date.parse(iso);
      if (Number.isFinite(n)) return n;
    }
    return null;
  }
  function promotional(a) {
    const v = assessment(a);
    return !!(v && (v.type === "reklame" || v.ai_relevant === false)) || /\b(last chance|last call|early.bird|promo code|side.events|ticket sale|save \$\d+|sidste frist for sideevents)\b/i.test((a.titel || "") + " " + (a.rubrik || ""));
  }
  function modelLaunch(a) {
    const v = assessment(a);
    if (promotional(a) || (v && (v.type !== "lancering" || v.dokumentation <= 1))) return false;
    const headline = ((a.titel || "") + " " + (a.rubrik || "")).toLowerCase();
    if (/\b(plugin|windows|nas|smart.home|case study|kundecase|nedbrud|downtime)\b|\bchatgpt\s+(?:for|til)\b/.test(headline)) return false;
    if (v && v.version === VERSION && typeof v.model_lancering === "boolean") return v.model_lancering;
    const text = headline + " " + (a.resume_da || a.resume || "").toLowerCase();
    if (/\b(rumou?rs?|rygte\w*|might|may launch|could launch|expected to|reportedly|planlægger|overvejer|forventes|ifølge rygter)\b/.test(headline)) return false;
    const action = /\b(introduc\w*|releas\w*|launch\w*|unveil\w*|announc\w*|lancer\w*|udgiv\w*|udsend\w*|præsenter\w*|tilgængelig)\b/.test(headline);
    const model = /\b(models?|modeller|sprogmodel\w*|language model\w*|gpt[- ]?\d|(?:claude|gemini|llama|qwen|deepseek|grok|mistral|phi)[- ](?:\d|opus|sonnet|haiku))/.test(text);
    return action && model;
  }
  function baseScore(a) {
    if (promotional(a)) return 0;
    const v = assessment(a);
    if (v) {
      let n = Object.entries(WEIGHTS).reduce((sum,[k,w]) => sum + v[k]*w, 0);
      if (v.dokumentation <= 1) n = Math.min(n,35);
      if (v.type === "rygte") n = Math.min(n,38);
      return n;
    }
    const p = a.prio == null ? NaN : Number(a.prio);
    return Number.isFinite(p) ? Math.max(1,Math.min(10,p))*8 : 40;
  }
  function score(a, now = Date.now()) {
    const date = timestamp(a);
    if (date === null) return Math.round(baseScore(a)*0.45*100)/100;
    const hours = (now-date)/HOUR;
    if (hours < -2) return 0;
    let freshness = 0.65 + 0.35 * (2 ** (-Math.max(0,hours)/48));
    const launch = modelLaunch(a), threshold = 72;
    if (hours > threshold) freshness *= 2 ** (-(hours-threshold)/96);
    const bonus = launch && hours <= 168 && baseScore(a) >= 32 ? MODEL_BONUS * 2 ** (-Math.max(0,hours-48)/48) : 0;
    return Math.round((baseScore(a)+bonus)*freshness*100)/100;
  }
  function source(a) { try { return new URL(a.link).hostname.replace(/^www\./,""); } catch { return a.kilde || ""; } }
  function topic(a) {
    const v = assessment(a);
    if (v && v.emne) return v.emne;
    const m = (a.titel || "").match(/\b(openai|chatgpt|anthropic|claude|google|gemini|nvidia|microsoft|apple|meta|xai)\b/i);
    const k = m ? m[1].toLowerCase() : "";
    return ({chatgpt:"openai",claude:"anthropic",gemini:"google"})[k] || k;
  }
  function rank(articles, now = Date.now()) {
    return [...articles].sort((a,b) => score(b,now)-score(a,now) || (timestamp(b)||0)-(timestamp(a)||0) || String(a.link).localeCompare(String(b.link)));
  }
  function storyKeys(a) {
    const keys = new Set();
    for (const item of [a,...(Array.isArray(a.andre)?a.andre:[])]) {
      if (!item || !safeUrl(item.link)) continue;
      const u = new URL(item.link);
      const params = [...u.searchParams].filter(([k])=>!k.toLowerCase().startsWith('utm_')&&!['fbclid','gclid','mc_cid','mc_eid'].includes(k.toLowerCase())).sort(([a,b],[c,d])=>a<c?-1:a>c?1:b<d?-1:b>d?1:0);
      keys.add('url:'+u.host.replace(/^www\./,'')+(u.pathname.replace(/\/+$/,'')||'/')+'?'+new URLSearchParams(params));
    }
    for (const text of [a.titel,a.rubrik]) {
      if (typeof text !== 'string') continue;
      const words = text.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').match(/[a-z0-9æø]+/g)||[];
      if (words.length>=4) keys.add('titel:'+words.join(' '));
    }
    const text=[a.titel,a.rubrik,a.resume_da].filter(Boolean).join(' ').toLowerCase().replace(/[‐‑–—]/g,'-');
    if(modelLaunch(a)&&!/\b(vs|versus|preview|beta|api|financ\w*|finans\w*|enterprise|eu|europe|europa|kina|china|benchmark\w*|sammenlign\w*)\b/.test(text)){
      const pattern=/\b(?!(?:model|models|modellen|modeller|version|versionen|release|udgave)\b)(?:[a-z][a-z0-9-]{2,} v\d+(?:\.\d+)*|(?:gpt|gemini|claude|llama|qwen|deepseek|grok|mistral|phi|sora|veo|suno)[- ](?:opus[- ]|sonnet[- ]|haiku[- ])?\d+(?:\.\d+)*)(?:[- ](?:flash|pro|mini|nano|lite|ultra|opus|sonnet|haiku|astra|thinking|instruct|cyber|codex|transcribe|vision|audio|realtime|omni|\d+b))*\b/gi;
      const models=new Set();let unknownVariant=false;
      for(const field of [a.titel,a.rubrik,a.resume_da]){
        const original=String(field||'').replace(/[‐‑–—]/g,'-').replace(/\b(gpt|gemini|claude|llama|qwen|deepseek|grok|mistral|phi|sora|veo|suno)\s+(?:(?:har|has|just|netop)\s+)?(?:lancerer|lanceret|udgiver|udgivet|frigiver|frigivet|releases?|released|launch(?:es|ed)?|introduces?|introduced)\s+(?:(?:sin|deres|its|the|a|new|ny|nye|nyeste)\s+)*(?=v?\d)/gi,'$1 ');
        for(const m of original.matchAll(pattern)){
          if(/^[a-z0-9-]*model(?:s|len|ler|serien|serier|series)?$/.test(m[0].toLowerCase().split(' ')[0]))continue;
          if(/^[- ]+[A-ZÆØÅ][a-zA-ZæøåÆØÅ-]+/.test(original.slice(m.index+m[0].length)))unknownVariant=true;
          models.add(m[0].toLowerCase().replace(/[- ]+/g,'-'));
        }
      }
      if(models.size===1&&!unknownVariant)keys.add('model:'+models.values().next().value);
    }
    return keys;
  }
  function uniqueStories(articles) {
    const groups=[];
    for (const a of articles) {
      const keys=storyKeys(a), matches=groups.filter(g=>{
        const shared=[...keys].filter(k=>g.keys.has(k));
        return shared.some(k=>!k.startsWith('model:'))||(shared.length&&timestamp(a)!==null&&g.items.some(b=>timestamp(b)!==null&&Math.abs(timestamp(a)-timestamp(b))<=168*HOUR));
      });
      if (!matches.length) {groups.push({items:[a],keys});continue;}
      const group=matches[0];group.items.push(a);keys.forEach(k=>group.keys.add(k));
      for (const other of matches.slice(1)) {group.items.push(...other.items);other.keys.forEach(k=>group.keys.add(k));groups.splice(groups.indexOf(other),1);}
    }
    return groups.map(g=>{
      const a=g.items[0];if(g.items.length===1)return a;
      const links=new Map();
      for(const item of g.items)for(const s of [item,...(Array.isArray(item.andre)?item.andre:[])])if(s&&safeUrl(s.link)&&s.link!==a.link&&!links.has(s.link))links.set(s.link,{link:s.link,kilde:s.kilde||''});
      return {...a,andre:[...links.values()]};
    });
  }
  function select(articles, count = 6, now = Date.now()) {
    const pool = uniqueStories(rank(articles,now)).filter(a => {
      const d = timestamp(a), v = assessment(a);
      return a.rubrik && !promotional(a) && baseScore(a)>=32 && d !== null && (now-d)/HOUR>=-2 && (now-d)/HOUR<=168 && !(v && (v.dokumentation<=1 || v.type === "rygte"));
    });
    const chosen = [], sources = new Map(), categories = new Map(), topics = new Map(), links = new Set();
    const countOf = (m,k) => m.get(k)||0;
    const add = (m,k) => m.set(k,countOf(m,k)+1);
    while (pool.length && chosen.length<count) {
      const weight = a => score(a,now)-countOf(sources,source(a))*12-countOf(categories,a.kategori)*(modelLaunch(a)?2:7)-(topic(a)?countOf(topics,topic(a))*14:0);
      let best=0;
      for(let i=1;i<pool.length;i++) if(weight(pool[i])>weight(pool[best])) best=i;
      const [a]=pool.splice(best,1);
      if(links.has(a.link)) continue;
      links.add(a.link);chosen.push(a);add(sources,source(a));add(categories,a.kategori);add(topics,topic(a));
    }
    return chosen;
  }
  function editorEdition(all, f, updated, now=Date.now()) {
    // Kun en kontrolleret plan fra PRÆCIS denne datafil må overtage pointlisten.
    if(!f||f.metode!=='agent'||f.agent_version!==1||f.kontrolleret!==true||f.data_opdateret!==updated)return null;
    const time=Date.parse(f.beregnet),age=now-time;
    if(!Number.isFinite(time)||age < -300000||age>24*HOUR)return null;
    const known=new Map(all.map(a=>[a.link,a])),chosen=f.udvalgte,order=f.raekkefoelge,groups=f.samlede;
    if(!Array.isArray(chosen)||chosen.length>3||new Set(chosen).size!==chosen.length)return null;
    if(chosen.some(k=>{const a=known.get(k);if(!a)return true;const d=timestamp(a),v=assessment(a);return !a.rubrik||promotional(a)||d===null||now-d < -2*HOUR||now-d>168*HOUR||(v&&(v.dokumentation<=1||v.type==='rygte'));}))return null;
    if(!Array.isArray(order)||new Set(order).size!==order.length||order.some(k=>!known.has(k))||chosen.some((k,i)=>order[i]!==k))return null;
    if(!groups||Array.isArray(groups)||typeof groups!=='object'||Object.keys(groups).some(k=>!chosen.includes(k)))return null;
    const excluded=new Set();
    for(const values of Object.values(groups)){
      if(!Array.isArray(values)||values.length>4)return null;
      for(const k of values){if(!known.has(k)||chosen.includes(k)||order.includes(k)||excluded.has(k))return null;excluded.add(k);}
    }
    const merged=new Map(known);
    for(const k of chosen){
      const a=known.get(k),others=(groups[k]||[]).map(x=>known.get(x));
      merged.set(k,{...a,andre:[...(Array.isArray(a.andre)?a.andre:[]),...others.flatMap(b=>[{link:b.link,kilde:b.kilde},...(Array.isArray(b.andre)?b.andre:[])])]});
    }
    const sequence=[...order,...rank(all,now).map(a=>a.link).filter(k=>!order.includes(k)&&!excluded.has(k))];
    const list=uniqueStories(sequence.map(k=>merged.get(k)).filter(a=>!promotional(a)));
    // Automatiske dubletregler må ikke erstatte chefens valgte repræsentant.
    const selected=chosen.map(k=>list.find(a=>a.link===k));
    if(selected.some(a=>!a))return null;
    return {articles:list,selected};
  }
  function safeUrl(value, local = false) {
    if (typeof value !== "string" || !value.trim()) return "";
    if (local) return /^(?:\/?(?:artikel|video)\/[a-zA-Z0-9_-]+\.html|\/?data\/img\/[a-zA-Z0-9_.-]+)$/.test(value) ? value : "";
    try { const url = new URL(value); return /^(https?:)$/.test(url.protocol) ? url.href : ""; } catch { return ""; }
  }
  function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g,x=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[x]); }
  function bold(value) { return escapeHtml(value).replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>"); }
  const api={modelLaunch,assessment,timestamp,promotional,baseScore,score,rank,select,storyKeys,uniqueStories,editorEdition,safeUrl,escapeHtml};
  if(typeof module!=="undefined" && module.exports) module.exports=api;
  root.AINews=api;
  if(typeof document==="undefined") return;

  const $=id=>document.getElementById(id);
  const categoryNames={"Alle":"Alle emner","Modeller":"Modellanceringer","Lanceringer":"Produkter","Hverdags-AI":"I hverdagen","Samfund & etik":"Samfund","Penge & marked":"Forretning","Politik & jura":"Politik","Forskning":"Forskning"};
  let articles=[], catalog=[], selected=[], category="Alle", query="", order="anbefalet", visible=12;
  let lastFocus=null, readerArticle=null, ownHistory=false, toastTimer, searchTimer;
  let read={};
  try { const stored=JSON.parse(localStorage.getItem("laeste")||"{}"); if(stored && !Array.isArray(stored) && typeof stored==="object") read=stored; } catch {}
  try { ["visninger","baandVist","visning","sortering"].forEach(k=>localStorage.removeItem(k)); } catch {}
  const formatDate=(date,options)=>new Intl.DateTimeFormat("da-DK",{timeZone:"Europe/Copenhagen",...options}).format(date);
  function dateText(a) {
    const ts=timestamp(a); if(ts===null) return "Dato ukendt";
    const hours=(Date.now()-ts)/HOUR;
    if(hours < -2) return formatDate(ts,{day:"numeric",month:"short",year:"numeric"});
    if(hours<1) return "Under en time siden";
    if(hours<24) return `${Math.floor(hours)} timer siden`;
    return formatDate(ts,{day:"numeric",month:"short",...(new Date(ts).getFullYear()!==new Date().getFullYear()?{year:"numeric"}:{})});
  }
  function readingTime(a) {
    const text=[a.resume_da||a.resume||"",a.brief||"",...(a.sektioner||[]).map(s=>s.tekst||""),...(a.detaljer||[])].join(" ");
    return `${Math.max(1,Math.ceil(text.split(/\s+/).length/210))} min. læsning`;
  }
  function title(a) { return a.rubrik||a.titel||"AI-nyhed"; }
  function summary(a) { return a.resume_da||a.resume||""; }
  function articleUrl(a) { return (!a.kun_aktuel && safeUrl(a.side,true)) || safeUrl(a.link) || "#nyhedsliste"; }
  function linkAttrs(a) { return `href="${escapeHtml(articleUrl(a))}" data-article="${escapeHtml(a.link)}"`; }
  function sources(a) {
    const items=[{link:a.link,kilde:a.kilde},...(Array.isArray(a.andre)?a.andre:[]),...(Array.isArray(a.redaktoer_kilder)?a.redaktoer_kilder:[])];
    return items.filter((s,i)=>s&&safeUrl(s.link)&&items.findIndex(x=>x&&x.link===s.link)===i);
  }
  function meta(a) {
    const count=new Set(sources(a).map(source)).size;
    return `<div class="story-meta"><span>${escapeHtml(a.kilde||"Originalkilde")}</span><span>${escapeHtml(dateText(a))}</span><span>${readingTime(a)}</span>${count>1?`<span>${count} kilder</span>`:""}${read[a.link]?'<span class="read-label">Læst</span>':""}${!a.rubrik?'<span>På engelsk</span>':""}</div>`;
  }
  function cardTopline(a, featured=false) {
    const ts=timestamp(a),label=featured&&modelLaunch(a)?"Ny AI-model":a.kategori||"AI-nyt";
    const date=ts===null?`<span class="story-date">${escapeHtml(dateText(a))}</span>`:`<time class="story-date" datetime="${new Date(ts).toISOString()}">${escapeHtml(dateText(a))}</time>`;
    return `<div class="story-topline"><span class="category">${escapeHtml(label)}</span>${date}</div>`;
  }
  function image(a,cls,lazy=true) {
    const src=safeUrl(a.billede,true);
    const alt=cls==="story-thumbnail"?"AI-genereret illustration":a.billedmotiv||"AI-genereret illustration";
    return src?`<img class="${cls}" src="${escapeHtml(src)}" alt="${escapeHtml(alt)}" ${lazy?'loading="lazy"':'fetchpriority="high"'} decoding="async">`:"";
  }
  function renderFeatured() {
    const box=$("udvalgte");box.setAttribute("aria-busy","false");
    if(!selected.length) { box.innerHTML="";return; }
    const [lead,...rest]=selected;
    box.innerHTML=`<div class="lead-grid${rest.length?'':' single-story'}"><article class="lead-story">${cardTopline(lead,true)}<h2><a class="story-link" ${linkAttrs(lead)}>${escapeHtml(title(lead))}</a></h2><div class="story-excerpt">${image(lead,"story-thumbnail",false)}<p class="lead-summary">${escapeHtml(summary(lead))}</p></div></article>${rest.length?`<div class="feature-stack">${rest.map(a=>`<article class="feature-story">${cardTopline(a,true)}<h3><a class="story-link" ${linkAttrs(a)}>${escapeHtml(title(a))}</a></h3><div class="story-excerpt">${image(a,"story-thumbnail")}<p>${escapeHtml(summary(a))}</p></div></article>`).join("")}</div>`:""}</div>`;
  }
  function renderCategories() {
    $("kategorier").innerHTML=Object.entries(categoryNames).map(([key,label])=>`<button type="button" data-category="${escapeHtml(key)}" aria-pressed="${key===category}">${label}</button>`).join("");
  }
  function normalize(value) { return String(value||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("da"); }
  function browsingAll(){return category!=="Alle"||query.trim()!==""||order!=="anbefalet";}
  function filtered() {
    const words=normalize(query).trim().split(/\s+/).filter(Boolean);
    let list=articles.filter(a=>!promotional(a) && (category==="Alle" || (category==="Modeller" ? modelLaunch(a) : a.kategori===category)));
    // Topfelt og liste har hver deres historier. Søgning og filtre dækker hele
    // arkivet; her skjules topfeltet i stedet for at skjule søgeresultater.
    if(!browsingAll()){const featured=new Set(selected.map(a=>a.link));list=list.filter(a=>!featured.has(a.link));}
    if(words.length) list=list.filter(a=>{
      const versions=[a,...sources(a).map(s=>catalog.find(item=>item.link===s.link)).filter(Boolean)];
      const text=normalize(versions.flatMap(item=>[title(item),summary(item),item.kilde,item.kategori,item.betydning,...(item.sektioner||[]).map(s=>s.tekst)]).join(" "));
      return words.every(w=>text.includes(w));
    });
    if(order==="nyeste") list=[...list].sort((a,b)=>(timestamp(b)||0)-(timestamp(a)||0));
    return list;
  }
  function renderList() {
    const list=filtered();$("nyhedsliste").setAttribute("aria-busy","false");
    const browsing=browsingAll();$("udvalgte").hidden=browsing||!selected.length;
    $("nyhederTitel").textContent=query.trim()?"Søgeresultater":(category!=="Alle"?categoryNames[category]:"Nyheder");
    $("nyhedsoverskrift").classList.toggle("sr-only",!browsing);
    $("antalNyheder").textContent=`${list.length} ${list.length===1?"historie":"historier"}`;
    $("filterBeskrivelse").textContent=query.trim()?`Søger efter “${query.trim()}”`:(order==="nyeste"?"Sorteret efter kildens udgivelsesdato":"Nye modeller og væsentlige nyheder først");
    $("nulstil").hidden=!browsing;
    $("soegeKnap").classList.toggle("has-filters",browsing);
    $("soegeKnap").setAttribute("aria-label",browsing?"Søg og filtrér nyheder — filtre er aktive":"Søg og filtrér nyheder");
    $("nyhedsliste").innerHTML=list.length?list.slice(0,visible).map(a=>`<article class="news-row"><div class="news-row-content">${cardTopline(a)}<h3><a class="story-link" ${linkAttrs(a)}>${escapeHtml(title(a))}</a></h3><div class="story-excerpt">${image(a,"story-thumbnail")}<p>${escapeHtml(summary(a))}</p></div></div></article>`).join(""):`<div class="empty-state"><h3>${browsing?"Ingen historier matcher":"Du har set alle historierne"}</h3><p>${browsing?"Prøv et andet søgeord, eller vælg alle emner.":"Der er ikke flere historier i denne udgave."}</p>${browsing?'<button data-reset>Vis alle nyheder</button>':""}</div>`;
    $("visFlere").hidden=list.length<=visible;
    $("visFlere").innerHTML=`Vis flere nyheder <span class="section-note">${Math.min(visible,list.length)} af ${list.length}</span><span aria-hidden="true">↓</span>`;
  }
  function resetFilters(){category="Alle";query="";order="anbefalet";visible=12;$("soeg").value="";$("sortering").value=order;renderCategories();renderList();}
  function setSearchOpen(open,returnFocus=false){
    $("soegePanel").hidden=!open;
    $("soegeKnap").setAttribute("aria-expanded",String(open));
    if(open){
      $("menuKnap").setAttribute("aria-expanded","false");
      $("navigation").classList.remove("is-open");
      $("soeg").focus({preventScroll:true});
    }else if(returnFocus)$("soegeKnap").focus({preventScroll:true});
  }
  function markRead(a) {
    read[a.link]=Date.now();
    Object.keys(read).sort((a,b)=>read[b]-read[a]).slice(800).forEach(k=>delete read[k]);
    try{localStorage.setItem("laeste",JSON.stringify(read));}catch{}
  }
  function showToast(message) {
    $("besked").textContent=message;$("besked").hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$("besked").hidden=true;},3500);
  }
  function openArticle(a,fromHistory=false,trigger=null) {
    if(a.kun_aktuel){location.assign(safeUrl(a.link));return;}
    if(!$("laeser").showModal){location.assign(articleUrl(a));return;}
    if(!$("laeser").open) lastFocus=trigger||document.activeElement;
    readerArticle=a;markRead(a);
    const sections=Array.isArray(a.sektioner)?a.sektioner:[];
    const body=sections.length?sections.map(s=>`<section><h2>${escapeHtml(s.overskrift||"")}</h2>${String(s.tekst||"").split(/\n\n+/).map(p=>`<p>${bold(p)}</p>`).join("")}</section>`).join(""):(a.brief?String(a.brief).split(/\n\n+/).map(p=>`<p>${bold(p)}</p>`).join(""):'<p>Vi har foreløbig kun et kort resumé. Læs mere hos originalkilden nedenfor.</p>');
    const local=safeUrl(a.side,true),sourceItems=sources(a),v=assessment(a);
    $("artikelIndhold").innerHTML=`<div class="category">${escapeHtml(a.kategori||"AI-nyt")}</div><h1 id="laeserTitel" tabindex="-1">${escapeHtml(title(a))}</h1>${meta(a)}<p class="reader-deck">${escapeHtml(summary(a))}</p><div class="reader-actions">${local?`<a class="permalink" href="${escapeHtml(local)}">Åbn artikelsiden ↗</a>`:""}<button class="share-button" id="delArtikel">Kopiér link ↗</button><span id="delStatus" role="status" class="reader-note"></span></div>${a.billede?`<figure class="reader-figure">${image(a,"reader-image")}<figcaption>AI-genereret illustration</figcaption></figure>`:""}<div class="reader-body">${a.betydning?`<aside class="reader-callout"><h2>Hvad betyder det for dig?</h2><p>${bold(a.betydning)}</p></aside>`:""}${body}${(a.figurer||[]).filter(f=>safeUrl(f.url)).map(f=>`<figure class="reader-figure"><img src="${escapeHtml(safeUrl(f.url))}" alt="${escapeHtml(f.tekst||"")}" loading="lazy"><figcaption>${escapeHtml(f.tekst||"")} · ${escapeHtml(f.kilde||a.kilde||"")}</figcaption></figure>`).join("")}${a.detaljer?.length?`<details class="reader-callout"><summary>Flere detaljer</summary><ul>${a.detaljer.map(d=>`<li>${bold(d)}</li>`).join("")}</ul></details>`:""}${v?.forbehold?`<aside class="reader-callout"><h2>Det ved vi endnu ikke</h2><p>${escapeHtml(v.forbehold)}</p></aside>`:""}</div><section class="reader-source"><h2 class="category">Læs originalkilderne</h2><div class="source-links">${sourceItems.map(s=>`<a href="${escapeHtml(safeUrl(s.link))}" target="_blank" rel="noopener noreferrer">${escapeHtml(s.kilde||source(s))} ↗</a>`).join("")}</div><p class="reader-note">Bearbejdet af AI med udgangspunkt i de viste kilder. Flere omtaler er ikke nødvendigvis uafhængige bekræftelser.</p></section>`;
    if(!fromHistory){history.pushState({aiArticle:a.link},"",`#a=${encodeURIComponent(a.link)}`);ownHistory=true;}
    document.title=`${title(a)} · AI-nyheder`;
    document.body.classList.add("reader-open");
    if(!$("laeser").open)$("laeser").showModal();
    $("laeser").scrollTop=0;$("laeserTitel").focus({preventScroll:true});
    $("delArtikel").addEventListener("click",async()=>{
      const url=local?new URL(local,location.href).href:`${location.origin}${location.pathname}#a=${encodeURIComponent(a.link)}`;
      try{await navigator.clipboard.writeText(url);$("delStatus").textContent="Linket er kopieret";}catch{$("delStatus").textContent=url;}
    });
  }
  function hideArticle(){const focusLink=lastFocus?.dataset?.article;if($("laeser").open)$("laeser").close();document.body.classList.remove("reader-open");readerArticle=null;document.title="AI-nyheder · Det vigtigste i AI, forklaret på dansk";renderFeatured();renderList();if(lastFocus?.isConnected)lastFocus.focus({preventScroll:true});else if(focusLink){const link=[...document.querySelectorAll("h2 a[data-article],h3 a[data-article]")].find(a=>a.dataset.article===focusLink);link?.focus({preventScroll:true});}}
  function closeArticle(){if(ownHistory){ownHistory=false;history.back();}else{history.replaceState(null,"",location.pathname+location.search);hideArticle();}}
  function resolveHash(){
    const match=location.hash.match(/^#a=(.*)$/);if(!match){if(readerArticle)hideArticle();return;}
    let value;try{value=decodeURIComponent(match[1]);}catch{showToast("Artikellinket kunne ikke læses.");return;}
    const a=articles.find(a=>a.link===value)||catalog.find(a=>a.link===value)||articles.find(a=>sources(a).some(s=>s.link===value));
    if(a){ownHistory=history.state?.aiArticle===a.link;openArticle(a,true);return;}
    // Ældre delte links kan pege på en permanent side, der er røget ud af feedet.
    if(safeUrl(value,true)){location.assign(value);return;}
    if(safeUrl(value)){
      const candidate=new URL(value);
      if(candidate.origin===location.origin && safeUrl(candidate.pathname,true)){location.assign(candidate.pathname);return;}
    }
    const sourceLink=safeUrl(value);
    $("dataBesked").innerHTML='Historien er ikke længere i nyhedsoverblikket.'+(sourceLink?` Du kan stadig <a href="${escapeHtml(sourceLink)}" target="_blank" rel="noopener noreferrer">læse originalkilden ↗</a>.`:"");
    $("dataBesked").hidden=false;
    history.replaceState(null,"",location.pathname+location.search);
  }
  async function getJSON(url){const r=await fetch(url,{cache:"no-cache"});if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();}
  async function load(){
    try{
      const data=await getJSON("data/articles.json");if(!Array.isArray(data.artikler))throw new Error("Ugyldigt nyhedsformat");
      const unique=new Map();
      data.artikler.filter(a=>a&&typeof a==="object"&&safeUrl(a.link)).forEach(a=>{
        a={...a,sektioner:Array.isArray(a.sektioner)?a.sektioner.filter(s=>s&&typeof s==="object"):[],detaljer:Array.isArray(a.detaljer)?a.detaljer:[],figurer:Array.isArray(a.figurer)?a.figurer.filter(f=>f&&typeof f==="object"):[]};
        if(a.kategori==="Benchmarks")a.kategori="Lanceringer";
        unique.set(a.link,a);
      });
      const all=[...unique.values()];
      // Følg den kontrollerede redaktionsplan; ved fejl beregnes reserven
      // på alle aktuelle artikler, så gamle metadata ikke skjuler nye modeller.
      catalog=all;
      const edition=editorEdition(all,data.forside,data.opdateret);
      articles=edition?edition.articles:uniqueStories(rank(all));
      selected=edition?edition.selected:select(articles,3);
      const updated=Date.parse(data.opdateret);
      if(Number.isFinite(updated)){
        $("opdateret").textContent=`Opdateret ${formatDate(updated,{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}`;
        if(Date.now()-updated>36*HOUR){$("dataBesked").textContent="Nyhederne er ikke opdateret for nylig. Du læser den senest tilgængelige udgave; udgivelsesdatoen står ved hver historie.";$("dataBesked").hidden=false;}
      }else $("opdateret").textContent="Seneste tilgængelige udgave";
      if(!all.length){$("dataBesked").textContent="Der er ingen nyheder i den seneste udgave. Prøv igen lidt senere.";$("dataBesked").hidden=false;}
      renderCategories();renderFeatured();renderList();resolveHash();
    }catch{
      $("udvalgte").innerHTML="";$("udvalgte").setAttribute("aria-busy","false");$("nyhedsliste").setAttribute("aria-busy","false");$("opdateret").textContent="Nyhederne kunne ikke hentes";
      $("nyhedsliste").innerHTML='<div class="empty-state"><h3>Vi kunne ikke hente nyhederne</h3><p>Tjek forbindelsen, og prøv igen om lidt.</p><button id="proevIgen">Prøv igen</button></div>';
      $("proevIgen").addEventListener("click",load);
    }
  }
  $("datoIdag").textContent=formatDate(new Date(),{weekday:"long",day:"numeric",month:"long",year:"numeric"});
  $("menuKnap").addEventListener("click",()=>{const open=$("menuKnap").getAttribute("aria-expanded")!=="true";if(open)setSearchOpen(false);$("menuKnap").setAttribute("aria-expanded",String(open));$("navigation").classList.toggle("is-open",open);});
  $("soegeKnap").addEventListener("click",()=>setSearchOpen($("soegePanel").hidden));
  $("lukSoegning").addEventListener("click",()=>setSearchOpen(false,true));
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&!$("soegePanel").hidden&&!$("laeser").open){event.preventDefault();setSearchOpen(false,true);}
  });
  $("kategorier").addEventListener("click",event=>{const button=event.target.closest("[data-category]");if(!button)return;category=button.dataset.category;visible=12;renderCategories();renderList();$("kategorier").querySelector(`[data-category="${category}"]`)?.focus({preventScroll:true});});
  $("sortering").addEventListener("change",event=>{order=event.target.value;visible=12;renderList();});
  $("soeg").addEventListener("input",event=>{query=event.target.value;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{visible=12;renderList();},120);});
  $("soeg").addEventListener("keydown",event=>{
    if(event.key!=="Enter"||event.isComposing)return;
    event.preventDefault();clearTimeout(searchTimer);visible=12;renderList();setSearchOpen(false);
    $("nyhederTitel").focus();
  });
  $("nulstil").addEventListener("click",resetFilters);
  $("visFlere").addEventListener("click",()=>{const previous=visible;visible+=12;renderList();const first=$("nyhedsliste").querySelectorAll(".news-row h3 a")[previous];first?.focus({preventScroll:true});});
  document.addEventListener("click",event=>{
    const reset=event.target.closest("[data-reset]");if(reset){resetFilters();return;}
    const link=event.target.closest("a[data-article]");if(!link||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
    const a=articles.find(a=>a.link===link.dataset.article);if(!a||a.kun_aktuel)return;
    event.preventDefault();openArticle(a,false,link);
  });
  document.addEventListener("error",event=>{if(event.target instanceof HTMLImageElement){const figure=event.target.closest("figure");if(figure)figure.remove();else event.target.remove();}},true);
  $("lukLaeser").addEventListener("click",closeArticle);
  $("laeser").addEventListener("cancel",event=>{event.preventDefault();closeArticle();});
  $("laeser").addEventListener("click",event=>{if(event.target===$("laeser")){const rect=$("laeser").getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)closeArticle();}});
  window.addEventListener("popstate",resolveHash);
  window.addEventListener("hashchange",resolveHash);
  if("serviceWorker" in navigator)navigator.serviceWorker.register("sw.js").catch(()=>{});
  load();
})(typeof globalThis!=="undefined"?globalThis:this);
