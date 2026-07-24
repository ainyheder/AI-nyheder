// Minimal service worker: gør sitet installerbart og viser en venlig
// offline-besked. Nyhederne kræver net - vi cacher kun det nødvendige.
const CACHE = "ainyheder-v1";
self.addEventListener("install", e => { self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(clients.claim()); });
self.addEventListener("fetch", e => {
  e.respondWith(
    fetch(e.request).catch(() =>
      new Response(
        "<meta charset='utf-8'><body style='font-family:sans-serif;background:#f4f2ec;color:#191714;display:grid;place-items:center;height:100vh;margin:0'><div style='text-align:center'><h2>Du er offline 📡</h2><p>AI-nyheder kræver internet - prøv igen om lidt.</p></div></body>",
        { headers: { "Content-Type": "text/html; charset=utf-8" } }
      )
    )
  );
});
