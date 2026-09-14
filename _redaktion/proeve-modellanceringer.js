/* Kør med jsdom tilgængelig. Kun lokale fixtures, ingen netværkskald. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');
const root = path.resolve(__dirname,'..');
const html = fs.readFileSync(path.join(root,'modeller.html'),'utf8');
const read = file => fs.readFileSync(path.join(root,'assets',file),'utf8');
const now = Date.parse('2026-09-14T12:00:00Z');
const item = (name,age) => ({rubrik:name,resume:'Det nye er forklaret på dansk.',emne:name,side:`artikel/${name}.html`,dato:new Date(now-age*86400000).toISOString()});
async function mount(fail=false) {
  const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
  const dom=new JSDOM(html,{url:'https://ainyheder.com/modeller.html',runScripts:'outside-only',virtualConsole:vc});
  const w=dom.window;w.Date.now=()=>now;
  w.fetch=async()=>({ok:!fail,json:async()=>({lanceringer:[item('Aeldre',40),item('Nova',2),item('Beta',10),item('Nova',2),{...item('Ugyldig',1),side:'javascript:alert(1)'}]})});
  w.eval(read('nyheder.js'));w.eval(read('modeller.js'));
  await new Promise(resolve=>setTimeout(resolve,10));
  return {dom,w,d:w.document,errors};
}
(async()=>{
  const {dom,w,d,errors}=await mount();
  const names=()=>[...d.querySelectorAll('.launch h2')].map(e=>e.textContent);
  assert.deepEqual(names(),['Nova','Beta']);
  d.querySelector('[data-days="7"]').click();assert.deepEqual(names(),['Nova']);
  d.querySelector('[data-days="90"]').click();assert.deepEqual(names(),['Nova','Beta','Aeldre']);
  const input=d.getElementById('modelSoeg');input.value='beta';input.dispatchEvent(new w.Event('input'));
  assert.deepEqual(names(),['Beta']);
  input.value='Ingen sådan model';input.dispatchEvent(new w.Event('input'));
  assert.match(d.querySelector('.models-empty').textContent,/Ingen lanceringer/);
  d.getElementById('menuKnap').click();assert.equal(d.getElementById('menuKnap').getAttribute('aria-expanded'),'true');
  d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape'}));assert.equal(d.getElementById('menuKnap').getAttribute('aria-expanded'),'false');
  assert.equal(errors.length,0);dom.window.close();
  const failed=await mount(true);assert(failed.d.getElementById('modelRetry'));assert.equal(failed.errors.length,0);failed.dom.window.close();
  console.log('OK: Modeloversigt — rækkefølge, perioder, søgning, dubletter, links, mobilmenu og netværksfejl.');
})().catch(error=>{console.error(error);process.exitCode=1;});
