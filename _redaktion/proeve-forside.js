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
let checks=0;
function ok(value,message){assert.ok(value,message);checks++;}
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function mount(data=real,{hash='',blockedStorage=false,fail=false}={}){
  const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
  const dom=new JSDOM(html,{url:'https://ainyheder.com/'+hash,runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});
  const w=dom.window;
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
  ok(d.querySelectorAll('.quick-item').length===4,'Kort overblik');
  ok(d.querySelectorAll('.news-row').length===12,'Første side er begrænset');
  ok(!test.errors.length,'Ingen scriptfejl: '+test.errors.join(', '));
  ok(w.localStorage.getItem('visninger')===null,'Gammel skjult rotation ryddes');
  ok(d.querySelectorAll('#videoer a').length===3,'Eksisterende videoer kan åbnes');
  ok([...d.querySelectorAll('a[data-article]')].every(a=>api.safeUrl(a.getAttribute('href'),true)||api.safeUrl(a.getAttribute('href'))),'Nyhedslinks virker uden klikhandler');
  d.getElementById('visFlere').click();ok(d.querySelectorAll('.news-row').length===24,'Vis flere');
  d.querySelector('[data-category="Forskning"]').click();
  ok([...d.querySelectorAll('.news-row .category')].every(n=>n.textContent==='Forskning'),'Emnefilter');
  ok(d.activeElement.dataset.category==='Forskning','Tastaturfokus bevares ved emnevalg');
  d.getElementById('nulstil').click();
  const input=d.getElementById('soeg');input.value='gpt-6 astra';input.dispatchEvent(new w.Event('input'));await pause(150);
  ok(d.querySelectorAll('.news-row').length>0,'Søgning uden forskel på store/små bogstaver');
  input.value='xyz-findes-slet-ikke';input.dispatchEvent(new w.Event('input'));await pause(150);
  ok(d.querySelector('.empty-state h3').textContent==='Ingen historier matcher','Tomt søgeresultat');
  d.querySelector('[data-reset]').click();ok(d.querySelectorAll('.news-row').length===12,'Nulstilling');
  d.getElementById('sortering').value='nyeste';d.getElementById('sortering').dispatchEvent(new w.Event('change'));
  const latest=[...real.artikler].filter(a=>!api.promotional(a)).sort((a,b)=>api.timestamp(b)-api.timestamp(a))[0];
  ok(d.querySelector('.news-row h3 a').dataset.article===latest.link,'Nyeste er kildens udgivelsesdato');
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
  d.getElementById('menuKnap').click();ok(d.getElementById('menuKnap').getAttribute('aria-expanded')==='false','Mobilmenu lukkes');
  ok(!test.errors.length,'Ingen fejl efter interaktioner');test.close();
  const direct=await mount(real,{hash:'#a='+encodeURIComponent(real.artikler[0].link),blockedStorage:true});
  ok(direct.w.document.getElementById('laeser').open,'Gammelt direkte delelink og blokeret lagring');ok(!direct.errors.length,'Blokeret localStorage vælter ikke siden');direct.close();
  const gone=await mount(real,{hash:'#a='+encodeURIComponent('https://example.com/old-story')});
  ok(!gone.w.document.getElementById('dataBesked').hidden,'Gammel artikel giver en vedvarende forklaring');ok(gone.w.document.querySelector('#dataBesked a').href==='https://example.com/old-story','Gammelt link beholder originalkilden');gone.close();
  const broken=await mount(real,{hash:'#a='+encodeURIComponent('javascript:alert(1)')});ok(!broken.w.document.querySelector('#dataBesked a'),'Usikkert delt link bliver aldrig aktivt');broken.close();
  const fail=await mount(real,{fail:true});ok(fail.w.document.getElementById('proevIgen'),'Netværksfejl har prøv-igen-knap');ok(!fail.errors.length,'Netværksfejl håndteres');fail.close();
  const empty=await mount({artikler:[]});ok(empty.w.document.querySelector('.empty-state'),'Tomt feed håndteres');ok(!empty.errors.length,'Tomt feed uden fejl');empty.close();
  const stale=await mount({...real,opdateret:'2020-01-01T12:00:00Z',forside:null});ok(!stale.w.document.getElementById('dataBesked').hidden,'Gamle data kaldes ikke aktuelle');stale.close();
  const hostileArticle={...real.artikler[0],rubrik:'<img src=x onerror=alert(1)>',dato:new Date().toISOString(),billede:'javascript:alert(1)',sektioner:[{overskrift:'<script>x</script>',tekst:'<img onerror=x>'}],andre:[null],figurer:[null]};
  const hostile=await mount({artikler:[hostileArticle],opdateret:new Date().toISOString()});hostile.w.document.querySelector('a[data-article]').click();
  ok(!hostile.w.document.querySelector('#artikelIndhold img'),'Artikelfelter indsætter ikke HTML');ok(!hostile.errors.length,'Ufuldstændige felter håndteres');hostile.close();
  console.log(`OK: ${checks} kontroller. Rigtige data, sortering, filtre, læser, historik, lagring, fejl og sikre links.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
