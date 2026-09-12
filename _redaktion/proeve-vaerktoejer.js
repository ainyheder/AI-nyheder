// NODE_PATH=/tmp/ai-news-checks/node_modules node _redaktion/proeve-vaerktoejer.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'vaerktoejer.html'), 'utf8');
const dom = new JSDOM(html, {url:'https://ainyheder.com/vaerktoejer.html',runScripts:'outside-only'});
const w = dom.window, d = w.document;
const visible = () => [...d.querySelectorAll('.tool-card:not([hidden])')].map(x => x.id);
assert.equal(visible().length, 5, 'Alle anbefalinger findes uden JavaScript');
assert.equal(d.querySelector('h2').textContent,'ChatGPT + Codex');
assert.equal(d.querySelectorAll('details .example-task').length,5,'Alle valg har en konkret opgave');
assert.equal(d.querySelectorAll('.tool-source').length,5,'Alle valg har en kilde');
const mainNav = [...d.querySelectorAll('#navigation a')].map(x=>x.getAttribute('href'));
assert.deepEqual(mainNav,['./','uge.html','vaerktoejer.html','https://artificialanalysis.ai/','om.html']);
w.eval(fs.readFileSync(path.join(root,'assets/vaerktoejer.js'),'utf8'));
assert.equal(d.querySelector('.tool-filters').hidden,false);
for(const [filter,ids] of Object.entries({byg:['chatgpt','claude'],design:['canva'],dokumenter:['chatgpt','claude','notebook'],research:['chatgpt','notebook','perplexity'],hverdag:['chatgpt','claude','perplexity']})) {
 const b=d.querySelector(`[data-filter="${filter}"]`);b.click();
 assert.deepEqual(visible(),ids,`Filter: ${filter}`);
 assert.equal(b.getAttribute('aria-pressed'),'true');
 assert.equal(d.querySelectorAll('[data-filter][aria-pressed="true"]').length,1);
 assert.equal(d.querySelector('#tool-count').textContent.startsWith(`${ids.length} `),true);
}
d.querySelector('[data-filter="design"]').click();
assert.match(d.querySelector('#tool-count').textContent,/^1 værktøj ·/);
w.location.hash='#chatgpt-example';w.dispatchEvent(new w.HashChangeEvent('hashchange'));
assert.equal(visible().length,5,'Direkte eksempellink åbner også et skjult kort');
assert.equal(d.querySelector('#chatgpt-example').open,true);
const menu=d.querySelector('#menuKnap');menu.click();
assert.equal(menu.getAttribute('aria-expanded'),'true');
d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape'}));
assert.equal(menu.getAttribute('aria-expanded'),'false');
assert.equal(d.activeElement,menu);
for(const file of ['youtube.html','laer.html','prompts.html','koerekort.html','erhverv.html']) {
 const retired=fs.readFileSync(path.join(root,file),'utf8');
 assert.match(retired,/noindex/);assert.match(retired,/url=vaerktoejer.html/);
}
dom.window.close();console.log('OK: Værktøjsguide, opgavefiltre, eksempler, menu, læsbarhed uden JS og gamle indgange.');
