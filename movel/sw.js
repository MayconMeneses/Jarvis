"use strict";
// Guarda a casca do app e o conhecimento para abrir sem rede. Chamadas a outros sites (Wikipédia, modelos) nunca passam pelo cache daqui.
const CACHE = "jarvis-movel-10";
const CASCA = ["./", "index.html", "css/app.css", "css/tema.css", "css/mobile.css", "dados/saber.json", "dados/modelos.json", "manifest.webmanifest", "icones/icone-180.png", "icones/icone-512.png",
  "js/main.js", "js/temas.js", "js/painel-aparencia.js", "js/uso.js", "js/uso-grafico.js", "js/painel-uso.js", "js/motor-uso.js", "js/agentes.js", "js/painel-agentes.js", "js/util.js", "js/memoria.js", "js/saber.js", "js/design.js", "js/gerar.js", "js/aprender.js", "js/motor.js", "js/contexto.js",
  "js/cerebro.js", "js/leque.js", "js/zip.js", "js/oficina-espaco.js", "js/nuvem.js", "js/painel-nuvem.js", "js/habilidades.js", "js/revisao.js", "js/stack.js", "js/info.js", "js/motor-extra.js", "js/proativo.js", "js/md.js", "js/conversa.js", "js/cripto.js", "js/chat.js", "js/painel-memoria.js", "js/painel-cerebro.js",
  "js/sandbox.js", "js/sandbox-codigo.js", "js/modelos.js", "js/criar-ia.js", "js/painel-oficina.js", "js/painel-oficina-ia.js", "js/autonomo.js", "js/agendador.js", "js/avaliar.js", "js/motor-autonomo.js", "js/painel-autonomo.js",
  "js/orbe.js", "js/orbe-desenho.js", "js/orbe-voz.js", "js/orbe-ui.js", "js/memoria-viva.js", "js/instagram.js", "js/instagram-base.js", "js/instagram-temas.js", "js/instagram-metricas.js", "js/instagram-importar.js", "js/instagram-entrevista.js", "js/instagram-relatorio.js", "js/instagram-motor.js", "js/painel-instagram.js", "js/cartao-memoria.js", "js/areas.js", "js/grafo-desenho.js", "js/painel-grafo.js",
  "js/erros.js", "js/teclado.js", "js/rascunho.js", "js/navegacao.js", "js/atualizacao.js",
  "js/pc-pareado.js", "js/motor-pc.js", "js/painel-pc.js",
  "sandbox/js.html", "sandbox/py.html", "sandbox/host.js"];

self.addEventListener("install", (ev) => ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(CASCA)).then(() => self.skipWaiting())));
self.addEventListener("activate", (ev) => ev.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
const ESPERA_REDE_MS = 3500;  // rede lenta ou "meio caída": depois disso, usa o que está guardado

// Rede primeiro (versão nova sempre que há internet). Se a rede demora ou cai, serve o guardado. Só guarda resposta boa e do próprio site
// (um 404, uma resposta parcial ou um erro nunca substituem o que funciona), e cache cheio não derruba a resposta.
async function responder(req) {
  const guardado = await caches.match(req, { ignoreSearch: req.mode === "navigate" });
  const rede = fetch(req).then((r) => {
    if (r.ok && r.type === "basic" && r.status === 200) { const copia = r.clone(); caches.open(CACHE).then((c) => c.put(req, copia)).catch(() => {}); }
    return r;
  });
  if (!guardado) return rede.catch(async () => (req.mode === "navigate" && (await caches.match("./"))) || Response.error());
  const espera = new Promise((ok) => setTimeout(() => ok(guardado), ESPERA_REDE_MS));
  rede.catch(() => {});  // se perdeu a corrida e falhou depois, ninguém reclama
  return Promise.race([rede, espera]).catch(() => guardado);
}
self.addEventListener("fetch", (ev) => {
  const url = new URL(ev.request.url);
  if (ev.request.method !== "GET" || url.origin !== self.location.origin) return;
  ev.respondWith(responder(ev.request));
});
