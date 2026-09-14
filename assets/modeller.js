(function () {
  'use strict';
  const {escapeHtml: esc, safeUrl} = window.AINews;
  const list = document.getElementById('modelListe');
  const status = document.getElementById('modelStatus');
  const search = document.getElementById('modelSoeg');
  const periods = [...document.querySelectorAll('[data-days]')];
  let launches = [], days = 30;
  const date = new Intl.DateTimeFormat('da-DK', {day:'numeric', month:'short', year:'numeric', timeZone:'Europe/Copenhagen'});
  const normalize = s => String(s || '').toLocaleLowerCase('da-DK').normalize('NFKC');
  function render() {
    const q = normalize(search.value).trim(), now = Date.now();
    const items = launches.filter(a => now - Date.parse(a.dato) <= days * 86400000
      && normalize([a.rubrik, a.resume, a.emne].join(' ')).includes(q));
    status.textContent = `${items.length} ${items.length === 1 ? 'lancering' : 'lanceringer'} · nyeste først`;
    list.innerHTML = items.map((a, i) => {
      const picture = safeUrl(a.billede, true);
      return `<li class="launch${i === 0 ? ' launch-latest' : ''}"><div class="launch-date"><time datetime="${esc(a.dato)}">${esc(date.format(Date.parse(a.dato)))}</time>${i === 0 && !q ? '<span>Seneste</span>' : ''}</div><article><h2><a href="${esc(safeUrl(a.side, true))}">${esc(a.rubrik)}</a></h2><div class="launch-excerpt">${picture ? `<img src="${esc(picture)}" alt="" loading="lazy" decoding="async" width="132" height="110">` : ''}<p>${esc(a.resume)}</p></div></article></li>`;
    }).join('');
    if (!items.length) list.innerHTML = '<li class="models-empty">Ingen lanceringer matcher. Prøv en længere periode eller en anden søgning.</li>';
  }
  periods.forEach(button => button.addEventListener('click', () => {
    days = Number(button.dataset.days);
    periods.forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    render();
  }));
  search.addEventListener('input', render);
  const menu = document.getElementById('menuKnap'), nav = document.getElementById('navigation');
  menu.addEventListener('click', () => {
    const expanded = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(expanded));
    nav.classList.toggle('is-open', expanded);
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {
      menu.click(); menu.focus();
    }
  });
  async function load() {
    try {
      const response = await fetch('data/modellanceringer.json', {cache:'no-cache'});
      if (!response.ok) throw new Error('Oversigten kunne ikke hentes');
      const data = await response.json();
      if (!Array.isArray(data.lanceringer)) throw new Error('Ugyldig oversigt');
      const seen = new Set();
      launches = data.lanceringer.filter(a => {
        if (!a || typeof a.rubrik !== 'string' || !a.rubrik.trim() || !safeUrl(a.side, true) || !a.side.startsWith('artikel/') || !Number.isFinite(Date.parse(a.dato)) || Date.parse(a.dato) > Date.now() || seen.has(a.side)) return false;
        seen.add(a.side); return true;
      }).sort((a,b) => Date.parse(b.dato) - Date.parse(a.dato));
      render();
    } catch {
      status.textContent = 'Modeloversigten kunne ikke hentes.';
      list.innerHTML = '<li class="models-empty"><p>Prøv igen om lidt.</p><button id="modelRetry">Hent oversigten igen</button></li>';
      document.getElementById('modelRetry').addEventListener('click', load);
    } finally { list.setAttribute('aria-busy', 'false'); }
  }
  load();
})();
