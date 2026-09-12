/* Lokale forhåndsvisninger skal ikke ændre GitHubs genererede statusfil. */
(function () {
  function start() {
    const script = document.createElement('script');
    script.src = 'assets/kommando.js?v=10';
    document.head.appendChild(script);
  }
  if (location.protocol === 'file:' || ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)) {
    const cache = document.createElement('script');
    cache.src = 'data/kommando-lokal.js';
    cache.onload = start;
    cache.onerror = start; // En frisk klon fungerer også uden en lokal cache.
    document.head.appendChild(cache);
  } else start();
})();
