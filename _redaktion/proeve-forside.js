// DOM- og adfærdsprøve. Ingen browser eller netværksadgang kræves.
// JSdom findes via NODE_PATH (se README). Rigtige data, fejl og gamle links.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const {JSDOM,VirtualConsole}=require('jsdom');
const repo=path.resolve(__dirname,'..');
const api=require(path.join(repo,'assets/nyheder.js'));
const html=fs.readFileSync(path.join(repo,'index.html'),'utf8');
const script=fs.readFileSync(path.join(repo,'assets/nyheder.js'),'utf8');
const real=JSON.parse(fs.readFileSync(path.join(repo,'data/articles.json'),'utf8'));
const testNow=Date.parse(real.opdateret)+3600000;
let checks=0;
function ok(value,message){assert.ok(value,message);checks++;}
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function mount(data=real,{hash='',blockedStorage=false,fail=false,now=testNow}={}){
  const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
  const dom=new JSDOM(html,{url:'https://ainyheder.com/'+hash,runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});
  const w=dom.window;
  w.Date.now=()=>now;
  w.HTMLElement.prototype.scrollIntoView=function(){};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  w.HTMLDialogElement.prototype.close=function(){this.open=false;};
  w.fetch=async url=>({ok:!fail,status:fail?503:200,json:async()=>String(url).includes('youtube')?JSON.parse(fs.readFileSync(path.join(repo,'data/youtube.json'),'utf8')):JSON.parse(JSON.stringify(data))});
  Object.defineProperty(w.navigator,'clipboard',{value:{writeText:async()=>{}}});
  if(blockedStorage)Object.defineProperty(w,'localStorage',{get(){throw new Error('Storage blocked');}});
  else{w.localStorage.setItem('visninger',JSON.stringify(Object.fromEntries(real.artikler.map(a=>[a.link,20]))));w.localStorage.setItem('laeste','null');}
  w.eval(script);await pause(25);return {dom,w,errors,close:()=>dom.window.close()};
}
(async()=>{
  // Samme rækkefølge i Python og JS, for alle de rigtige artikler.
  const now='2026-09-05T16:00:00+00:00';
  const py=JSON.parse(execFileSync('python3',['-c',`import json,redaktion;from datetime import datetime;a=json.load(open('data/articles.json'))['artikler'];n=datetime.fromisoformat('${now}');print(json.dumps({'selected':[x['link'] for x in redaktion.udvaelg(a,nu=n)],'scores':[redaktion.score(x,n) for x in a]}))`],{cwd:repo,encoding:'utf8'}));
  assert.deepEqual(api.select(real.artikler,6,Date.parse(now)).map(a=>a.link),py.selected);checks++;
  assert.deepEqual(real.artikler.map(a=>api.score(a,Date.parse(now))),py.scores);checks++;
  for(const url of ['javascript:alert(1)','data:text/html,test','//evil.example','http://[',''])ok(api.safeUrl(url)==='','Usikkert link afvises: '+url);
  for(const url of ['../secrets','/other.html','data/img/../../secret','https://evil.example/x.jpg'])ok(api.safeUrl(url,true)==='','Ugyldig lokal sti afvises');
  ok(api.escapeHtml('<img onerror="x">').includes('&lt;'),'HTML escapes');
  const test=await mount();const {w}=test,d=w.document;
  ok(d.querySelectorAll('.lead-story').length===1,'Én hovedhistorie');
  ok(d.querySelectorAll('.feature-story').length===2,'To andre udvalgte historier');
  ok(d.querySelectorAll('.quick-item,.secondary-story').length===0,'De gentagne overblik er fjernet');
  function visibleHeadlines(doc){return [...doc.querySelectorAll('main h2 a[data-article],main h3 a[data-article]')].filter(a=>!a.closest('[hidden]')).map(a=>a.dataset.article);}
  const headlines=visibleHeadlines(d);
  ok(headlines.length===new Set(headlines).size,'Hver historie vises kun én gang på forsiden');
  ok(d.querySelectorAll('.news-row').length===12,'Første side er begrænset');
  ok(!test.errors.length,'Ingen scriptfejl: '+test.errors.join(', '));
  ok(w.localStorage.getItem('visninger')===null,'Gammel skjult rotation ryddes');
  ok(d.querySelectorAll('#videoer a').length===3,'Eksisterende videoer kan åbnes');
  ok([...d.querySelectorAll('a[data-article]')].every(a=>api.safeUrl(a.getAttribute('href'),true)||api.safeUrl(a.getAttribute('href'))),'Nyhedslinks virker uden klikhandler');
  d.getElementById('visFlere').click();ok(d.querySelectorAll('.news-row').length===24,'Vis flere');
  ok(visibleHeadlines(d).length===new Set(visibleHeadlines(d)).size,'Vis flere gentager heller ikke toppen');
  const searchButton=d.getElementById('soegeKnap'),searchPanel=d.getElementById('soegePanel');
  ok(searchPanel.hidden&&searchButton.getAttribute('aria-expanded')==='false','Søgning er foldet sammen fra start');
  ok(searchPanel.closest('.site-header')&&!d.querySelector('main .news-controls'),'Søgepanelet ligger i hovedbjælken og ikke mellem historierne');
  searchButton.click();
  ok(!searchPanel.hidden&&searchButton.getAttribute('aria-expanded')==='true'&&d.activeElement.id==='soeg','Søgeikonet åbner panelet med fokus i feltet');
  d.querySelector('[data-category="Forskning"]').click();
  ok(d.getElementById('udvalgte').hidden,'Filtre skjuler topfeltet');
  ok([...d.querySelectorAll('.news-row .category')].every(n=>n.textContent==='Forskning'),'Emnefilter');
  ok(d.activeElement.dataset.category==='Forskning','Tastaturfokus bevares ved emnevalg');
  d.getElementById('lukSoegning').click();
  ok(searchPanel.hidden&&d.activeElement===searchButton,'Luk søgning skjuler panelet og sender fokus tilbage');
  ok(searchButton.classList.contains('has-filters')&&d.getElementById('udvalgte').hidden,'Lukkede filtre bevares og markeres ved søgeikonet');
  searchButton.click();
  ok(d.querySelector('[data-category="Forskning"]').getAttribute('aria-pressed')==='true','Valgt emne bevares ved genåbning');
  d.getElementById('nulstil').click();
  ok(!d.getElementById('udvalgte').hidden,'Nulstilling viser topfeltet igen');
  ok(!searchButton.classList.contains('has-filters'),'Nulstilling fjerner markeringen af aktive filtre');
  const input=d.getElementById('soeg');input.value='gpt-6 astra';input.dispatchEvent(new w.Event('input'));await pause(150);
  ok(d.querySelectorAll('.news-row').length>0,'Søgning uden forskel på store/små bogstaver');
  input.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
  ok(searchPanel.hidden&&d.activeElement.id==='nyhederTitel','Enter lukker panelet og går til søgeresultaterne');
  searchButton.click();
  ok(input.value==='gpt-6 astra','Søgeord bevares efter genåbning');
  d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
  ok(searchPanel.hidden&&d.activeElement===searchButton,'Escape lukker søgepanelet og sender fokus tilbage');
  searchButton.click();
  input.value='xyz-findes-slet-ikke';input.dispatchEvent(new w.Event('input'));await pause(150);
  ok(d.querySelector('.empty-state h3').textContent==='Ingen historier matcher','Tomt søgeresultat');
  d.querySelector('[data-reset]').click();ok(d.querySelectorAll('.news-row').length===12,'Nulstilling');
  d.getElementById('sortering').value='nyeste';d.getElementById('sortering').dispatchEvent(new w.Event('change'));
  const latest=[...real.artikler].filter(a=>!api.promotional(a)).sort((a,b)=>api.timestamp(b)-api.timestamp(a))[0];
  ok(d.querySelector('.news-row h3 a').dataset.article===latest.link,'Nyeste er kildens udgivelsesdato');
  ok(d.getElementById('udvalgte').hidden,'Nyeste først har kun én samlet liste');
  d.getElementById('nulstil').click();
  searchButton.click();
  const first=d.querySelector('.lead-story h2 a');const target=first.dataset.article;first.click();
  ok(d.getElementById('laeser').open,'Artiklen åbnes');
  ok(d.getElementById('laeserTitel').textContent===real.artikler.find(a=>a.link===target).rubrik,'Rigtig artikel');
  ok(d.activeElement.id==='laeserTitel','Læserens fokus flyttes ind');
  ok(w.location.hash.startsWith('#a='),'Delelink og historik');
  ok(d.querySelector('.source-links a'),'Originalkilde er synlig');
  d.getElementById('delArtikel').click();await pause(5);ok(d.getElementById('delStatus').textContent==='Linket er kopieret','Kopiér artikel-link');
  d.getElementById('lukLaeser').click();await pause(40);
  ok(!d.getElementById('laeser').open&&!d.body.classList.contains('reader-open'),'Luk og browser-tilbage');
  ok(d.activeElement.dataset.article===target,'Fokus vender tilbage til historien');
  ok(JSON.parse(w.localStorage.getItem('laeste'))[target]>0,'Læst-markering gemmes');
  w.history.forward();await pause(40);ok(d.getElementById('laeser').open,'Browser-frem genåbner artiklen');
  d.getElementById('laeser').dispatchEvent(new w.Event('cancel',{cancelable:true}));await pause(40);ok(!d.getElementById('laeser').open,'Escape lukker');
  d.getElementById('menuKnap').click();ok(d.getElementById('menuKnap').getAttribute('aria-expanded')==='true','Mobilmenu åbnes');
  searchButton.click();ok(!searchPanel.hidden&&!d.getElementById('navigation').classList.contains('is-open'),'Søgning lukker mobilmenuen');
  d.getElementById('menuKnap').click();ok(searchPanel.hidden&&d.getElementById('navigation').classList.contains('is-open'),'Mobilmenuen lukker søgepanelet');
  d.getElementById('menuKnap').click();ok(d.getElementById('menuKnap').getAttribute('aria-expanded')==='false','Mobilmenu lukkes');
  ok(!test.errors.length,'Ingen fejl efter interaktioner');test.close();
  const launchArticle={...real.artikler[0],andre:[],titel:"OpenAI releases GPT-6 Astra",rubrik:"OpenAI lancerer GPT-6 Astra",resume_da:'En ny model.',link:"https://example.com/astra-launch",dato:new Date(testNow-48*3600000).toISOString(),kategori:"Lanceringer",redaktion:{version:2,nyhed:5,betydning:4,brugbarhed:1,dokumentation:2,dansk:0,type:"lancering",ai_relevant:true}};
  const financeArticle={...real.artikler[0],andre:[],titel:"Firma henter penge",rubrik:"Firma henter penge",link:"https://example.org/finance",dato:new Date(testNow-3600000).toISOString(),kategori:"Penge & marked",redaktion:{version:3,model_lancering:false,nyhed:4,betydning:4,brugbarhed:4,dokumentation:4,dansk:2,type:"forretning",ai_relevant:true}};
  for(const version of [2,3]){
    const international={...financeArticle,redaktion:{...financeArticle.redaktion,version,dansk:0}};
    const local={...international,redaktion:{...international.redaktion,dansk:5}};
    ok(api.score(international,testNow)===api.score(local,testNow),'Ingen geografisk bonus i version '+version);
  }
  // Et gyldigt, men forældet udvalg må ikke skjule Astra efter en dataopdatering.
  const modelTest=await mount({artikler:[financeArticle,launchArticle],opdateret:new Date().toISOString(),forside:{version:3,beregnet:new Date().toISOString(),udvalgte:[financeArticle.link],raekkefoelge:[financeArticle.link]}});
  const md=modelTest.w.document;
  ok(md.querySelector('.lead-story h2').textContent.includes('Astra'),'Astra med den gamle AI-vurdering er hovedhistorie');
  ok(!md.querySelector('.news-row'),'De to udvalgte gentages ikke i listen');
  ok(md.querySelector('.empty-state h3').textContent==='Du har set alle historierne','Kort udgave får en retvisende afslutning');
  ok(md.querySelector('.lead-story .category').textContent==='Ny AI-model','Modellancering fremhæves tydeligt');
  md.querySelector('[data-category="Modeller"]').click();
  ok(md.querySelectorAll('.news-row').length===1,'Modelfilter viser kun modellanceringer');
  ok(md.querySelector('.news-row h3').textContent.includes('Astra'),'Astra findes under modellanceringer');
  ok(!modelTest.errors.length,'Ny modelprioritet uden scriptfejl');modelTest.close();
  const editorTime=new Date(testNow).toISOString();
  const editorPlan={metode:'agent',agent_version:1,kontrolleret:true,beregnet:editorTime,data_opdateret:editorTime,
    udvalgte:[financeArticle.link],raekkefoelge:[financeArticle.link,launchArticle.link],samlede:{[financeArticle.link]:[]}};
  const editorial=await mount({artikler:[launchArticle,financeArticle],opdateret:editorTime,forside:editorPlan});
  ok(editorial.w.document.querySelector('.lead-story h2 a').dataset.article===financeArticle.link,'Godkendt redaktørvalg overtager pointlistens Astra-valg');
  ok(editorial.w.document.querySelector('.news-row h3 a').dataset.article===launchArticle.link,'Øvrige historier er fortsat synlige');
  editorial.w.document.querySelector('[data-category="Modeller"]').click();
  ok(editorial.w.document.querySelector('.news-row h3 a').dataset.article===launchArticle.link,'Model-filteret virker med et agentudvalg');editorial.close();
  for(const invalidPlan of [{...editorPlan,kontrolleret:false},{...editorPlan,data_opdateret:'andet'},
    {...editorPlan,beregnet:new Date(testNow-25*3600000).toISOString()},
    {...editorPlan,udvalgte:['https://unknown.example/story']},
    {...editorPlan,samlede:{[financeArticle.link]:[launchArticle.link]}}]){
    ok(api.editorEdition([launchArticle,financeArticle],invalidPlan,editorTime,testNow)===null,'Ugyldig, forældet eller blandet agentplan afvises');
  }
  const emptyEditorial=api.editorEdition([launchArticle,financeArticle],{...editorPlan,udvalgte:[],samlede:{},raekkefoelge:[launchArticle.link,financeArticle.link]},editorTime,testNow);
  ok(emptyEditorial.selected.length===0,'En godkendt stille dag tvinger ingen hovedhistorie ind');
  const duplicate={...launchArticle,link:'https://second.example/astra',titel:'En ny udgave til alle',rubrik:'En ny udgave til alle',andre:[{link:launchArticle.link,kilde:'Originalkilden'}]};
  const semanticDuplicate={...financeArticle,link:'https://second.example/music',titel:'En helt anden overskrift',rubrik:'En anden vinkel fra andet medie',andre:[]};
  const semanticPlan={...editorPlan,samlede:{[financeArticle.link]:[semanticDuplicate.link]}};
  const semantic=await mount({artikler:[launchArticle,financeArticle,semanticDuplicate],opdateret:editorTime,forside:semanticPlan});
  ok(visibleHeadlines(semantic.w.document).length===2,'Agentens dokumenterede sammenlægning fjerner en anden vinkling fra listen');
  semantic.w.document.querySelector('.lead-story h2 a').click();
  ok(semantic.w.document.querySelectorAll('.source-links a').length===2,'Agentens sammenlægning bevarer begge kilder');
  ok(!semantic.errors.length,'Agentudvalg uden scriptfejl');semantic.close();
  const sourced=await mount({artikler:[{...launchArticle,redaktoer_kilder:[{link:'https://deepseek.com/news/release',kilde:'Officiel meddelelse'}]}],opdateret:editorTime});
  sourced.w.document.querySelector('.lead-story h2 a').click();
  ok([...sourced.w.document.querySelectorAll('.source-links a')].some(a=>a.href==='https://deepseek.com/news/release'),'Agentens ekstra officielle kilde følger med ind i læseren');sourced.close();
  const grouped=await mount({artikler:[launchArticle,duplicate,financeArticle],opdateret:new Date(testNow).toISOString()});
  ok(visibleHeadlines(grouped.w.document).length===2,'To omtaler af samme historie får én plads');
  grouped.w.document.querySelector('.lead-story h2 a').click();
  ok(grouped.w.document.querySelectorAll('.source-links a').length===2,'Begge originalkilder bevares i den samlede historie');
  grouped.w.document.getElementById('lukLaeser').click();await pause(40);
  grouped.w.history.forward();await pause(40);
  ok(grouped.w.document.querySelectorAll('.source-links a').length===2,'Browser-frem bevarer de samlede kilder');
  grouped.w.document.getElementById('lukLaeser').click();await pause(40);
  grouped.w.document.getElementById('soeg').value='udgave til alle';grouped.w.document.getElementById('soeg').dispatchEvent(new grouped.w.Event('input'));await pause(150);
  ok(grouped.w.document.querySelector('.news-row h3 a').dataset.article===launchArticle.link,'Søgning finder også teksten fra en samlet omtale');
  grouped.close();
  const oldDuplicateLink=await mount({artikler:[launchArticle,duplicate]}, {hash:'#a='+encodeURIComponent(duplicate.link)});
  ok(oldDuplicateLink.w.document.getElementById('laeserTitel').textContent===duplicate.rubrik,'Gamle delelinks åbner stadig den oprindelige artikel');oldDuplicateLink.close();
  const single=await mount({artikler:[launchArticle]});
  ok(single.w.document.querySelector('.lead-grid.single-story'),'En enkelt historie får ingen tomme kort');
  single.w.document.querySelector('#soeg').value='astra';single.w.document.querySelector('#soeg').dispatchEvent(new single.w.Event('input'));await pause(150);
  ok(single.w.document.querySelector('.news-row h3 a').dataset.article===launchArticle.link,'Søgning finder også historien fra toppen');single.close();
  // Valgfri frisk datakopi uden at omskrive crawlerens genererede filer i Git.
  if(process.env.AI_NEWS_DATA){
    const live=JSON.parse(fs.readFileSync(process.env.AI_NEWS_DATA,'utf8'));
    const liveNow=Date.parse(live.opdateret)+3600000;
    const liveTest=await mount(live,{now:liveNow});
    ok(visibleHeadlines(liveTest.w.document).length===new Set(visibleHeadlines(liveTest.w.document)).size,'Aktuelle data har ingen gentagne pladser');
    const suno=api.uniqueStories(api.rank(live.artikler,liveNow)).filter(a=>/suno v6\b/i.test([a.rubrik,a.resume_da].join(' ')));
    ok(suno.length===1&&suno[0].andre.length>=1,'De faktiske Suno v6-omtaler er samlet med kilder');
    const pyLive=JSON.parse(execFileSync('python3',['-c',"import json,redaktion,sys;from datetime import datetime;d=json.load(open(sys.argv[1]));n=datetime.fromtimestamp(float(sys.argv[2])/1000).astimezone();print(json.dumps({'selected':[a['link'] for a in redaktion.udvaelg(d['artikler'],nu=n)],'groups':[a['link'] for a in redaktion.unikke_historier(redaktion.prioriter(d['artikler'],n))]}))",process.env.AI_NEWS_DATA,String(liveNow)],{cwd:repo,encoding:'utf8'}));
    assert.deepEqual(api.select(live.artikler,6,liveNow).map(a=>a.link),pyLive.selected);checks++;
    assert.deepEqual(api.uniqueStories(api.rank(live.artikler,liveNow)).map(a=>a.link),pyLive.groups);checks++;
    ok(!liveTest.errors.length,'Aktuelle data uden scriptfejl');liveTest.close();
  }
  const direct=await mount(real,{hash:'#a='+encodeURIComponent(real.artikler[0].link),blockedStorage:true});
  ok(direct.w.document.getElementById('laeser').open,'Gammelt direkte delelink og blokeret lagring');ok(!direct.errors.length,'Blokeret localStorage vælter ikke siden');direct.close();
  const gone=await mount(real,{hash:'#a='+encodeURIComponent('https://example.com/old-story')});
  ok(!gone.w.document.getElementById('dataBesked').hidden,'Gammel artikel giver en vedvarende forklaring');ok(gone.w.document.querySelector('#dataBesked a').href==='https://example.com/old-story','Gammelt link beholder originalkilden');gone.close();
  const broken=await mount(real,{hash:'#a='+encodeURIComponent('javascript:alert(1)')});ok(!broken.w.document.querySelector('#dataBesked a'),'Usikkert delt link bliver aldrig aktivt');broken.close();
  const fail=await mount(real,{fail:true});ok(fail.w.document.getElementById('proevIgen'),'Netværksfejl har prøv-igen-knap');ok(!fail.errors.length,'Netværksfejl håndteres');fail.close();
  const empty=await mount({artikler:[]});ok(empty.w.document.querySelector('.empty-state'),'Tomt feed håndteres');ok(!empty.errors.length,'Tomt feed uden fejl');empty.close();
  const stale=await mount({...real,opdateret:'2020-01-01T12:00:00Z',forside:null});ok(!stale.w.document.getElementById('dataBesked').hidden,'Gamle data kaldes ikke aktuelle');stale.close();
  const hostileArticle={...real.artikler[0],rubrik:'<img src=x onerror=alert(1)>',dato:new Date(testNow).toISOString(),billede:'javascript:alert(1)',sektioner:[{overskrift:'<script>x</script>',tekst:'<img onerror=x>'}],andre:[null],figurer:[null]};
  const hostile=await mount({artikler:[hostileArticle],opdateret:new Date().toISOString()});hostile.w.document.querySelector('a[data-article]').click();
  ok(!hostile.w.document.querySelector('#artikelIndhold img'),'Artikelfelter indsætter ikke HTML');ok(!hostile.errors.length,'Ufuldstændige felter håndteres');hostile.close();
  console.log(`OK: ${checks} kontroller. Rigtige data, sortering, filtre, læser, historik, lagring, fejl og sikre links.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
