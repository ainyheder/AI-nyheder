// Nyheder og JSON hentes fra nettet. Kun dokument-navigation får en fejlside;
// en fejlet JSON-, CSS- eller billedrequest må aldrig blive besvaret som HTML.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", event => {
  if (event.request.mode !== "navigate" || event.request.method !== "GET") return;
  event.respondWith(fetch(event.request).catch(() => new Response(
    '<!doctype html><html lang="da"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Siden kan ikke nås · AI-nyheder</title><body style="font:18px/1.7 system-ui,sans-serif;background:#0c0e12;color:#f2f3f5;max-width:36rem;margin:12vh auto;padding:24px"><h1>Siden kan ikke nås</h1><p>Vi kan ikke få forbindelse til AI-nyheder. Det betyder ikke nødvendigvis, at du er offline.</p><p>Det kan skyldes en midlertidig fejl, manglende internet eller et sikkerhedsfilter på dit netværk.</p><p>Hvis andre hjemmesider virker, kan netværkets IT-support undersøge adgangen til ainyheder.com og www.ainyheder.com.</p><a href="" style="color:#d5ff5f">Prøv igen →</a></body></html>',
    {status:503,headers:{"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store"}}
  )));
});
