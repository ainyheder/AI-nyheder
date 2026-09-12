(function(){
  'use strict';
  const menu=document.getElementById('menuKnap'),nav=document.getElementById('navigation');
  menu.addEventListener('click',()=>{
    const open=menu.getAttribute('aria-expanded')!=='true';
    menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('is-open',open);
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&menu.getAttribute('aria-expanded')==='true'){
      menu.setAttribute('aria-expanded','false');nav.classList.remove('is-open');menu.focus();
    }
  });
})();
