// Nyheder og JSON hentes fra nettet. Kun dokument-navigation får offline-HTML;
// en fejlet JSON-, CSS- eller billedrequest må aldrig blive besvaret som HTML.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", event => {
  if (event.request.mode !== "navigate" || event.request.method !== "GET") return;
  event.respondWith(fetch(event.request).catch(() => new Response(
    '<!doctype html><html lang="da"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Du er offline · AI-nyheder</title><body style="font:18px/1.7 system-ui,sans-serif;color:#182131;max-width:36rem;margin:12vh auto;padding:24px"><h1>Du er offline</h1><p>AI-nyheder kræver internet. Tjek forbindelsen, og prøv igen.</p><a href="/" style="color:#254bdc">Prøv igen →</a></body></html>',
    {status:503,headers:{"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store"}}
  )));
});
