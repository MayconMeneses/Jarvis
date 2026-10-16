"use strict";
// Guarda só a casca do app (tela, estilo, script e ícones) para abrir rápido. As chamadas /api/ nunca passam pelo cache.
const CACHE = "jarvis-casca-1";
const CASCA = ["/", "/app.css", "/app.js", "/manifest.webmanifest", "/icone-180.png", "/icone-512.png"];

self.addEventListener("install", (ev) => ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(CASCA)).then(() => self.skipWaiting())));
self.addEventListener("activate", (ev) => ev.waitUntil(
  caches.keys().then((chaves) => Promise.all(chaves.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (ev) => {
  const url = new URL(ev.request.url);
  if (ev.request.method !== "GET" || url.pathname.startsWith("/api/")) return;
  ev.respondWith(fetch(ev.request).catch(() => caches.match(ev.request)));
});
