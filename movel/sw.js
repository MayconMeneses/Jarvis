"use strict";
// Guarda a casca do app e o conhecimento para abrir sem rede. Chamadas a outros sites (Wikipédia, modelos) nunca passam pelo cache daqui.
const CACHE = "jarvis-movel-1";
const CASCA = ["./", "index.html", "css/app.css", "dados/saber.json", "manifest.webmanifest", "icones/icone-180.png", "icones/icone-512.png",
  "js/main.js", "js/util.js", "js/memoria.js", "js/saber.js", "js/design.js", "js/gerar.js", "js/aprender.js", "js/motor.js", "js/contexto.js",
  "js/cerebro.js", "js/proativo.js", "js/md.js", "js/cripto.js", "js/chat.js", "js/painel-memoria.js", "js/painel-cerebro.js"];

self.addEventListener("install", (ev) => ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(CASCA)).then(() => self.skipWaiting())));
self.addEventListener("activate", (ev) => ev.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (ev) => {
  const url = new URL(ev.request.url);
  if (ev.request.method !== "GET" || url.origin !== self.location.origin) return;
  // Rede primeiro (sempre a versão nova quando há internet); sem rede, o que estiver guardado.
  ev.respondWith(fetch(ev.request).then((r) => { const copia = r.clone(); caches.open(CACHE).then((c) => c.put(ev.request, copia)); return r; })
    .catch(() => caches.match(ev.request)));
});
