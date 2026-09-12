(function () {
  'use strict';
  const menu = document.getElementById('menuKnap');
  const nav = document.getElementById('navigation');
  menu.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {
      menu.setAttribute('aria-expanded', 'false');
      nav.classList.remove('is-open');
      menu.focus();
    }
  });
  const filters = document.querySelector('.tool-filters');
  const cards = [...document.querySelectorAll('.tool-card')];
  filters.hidden = false;
  filters.addEventListener('click', event => {
    const button = event.target.closest('button[data-filter]');
    if (!button) return;
    filters.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    const filter = button.dataset.filter;
    cards.forEach(card => { card.hidden = filter !== 'alle' && !card.dataset.tasks.split(' ').includes(filter); });
    const count = cards.filter(card => !card.hidden).length;
    document.getElementById('tool-count').textContent = `${count} ${count === 1 ? 'værktøj' : 'værktøjer'} · ${filter === 'alle' ? 'vores anbefalede rækkefølge' : 'oprindelig prioritet bevaret'}`;
  });
  function revealExample(id, focus) {
    const example = document.getElementById(id);
    if (!example || !example.classList.contains('tool-example')) return;
    const card = example.closest('.tool-card');
    if (card.hidden) filters.querySelector('[data-filter="alle"]').click();
    example.open = true;
    if (focus) example.querySelector('summary').focus();
  }
  window.addEventListener('hashchange', () => revealExample(location.hash.slice(1), false));
  revealExample(location.hash.slice(1), false);
})();
