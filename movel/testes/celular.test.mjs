// Robustez do app no iPhone: erros humanos, teclado virtual, retomada após o Safari matar o app, barra de abas e service worker offline.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";
import { erroHumano } from "../js/erros.js";
import { dividirAbas } from "../js/navegacao.js";
import { Retomada, ligarRetomada } from "../js/rascunho.js";
import { medirTeclado } from "../js/teclado.js";
import { precisaAvisar } from "../js/atualizacao.js";

test("erros viram frases claras, sem código técnico solto", () => {
  assert.match(erroHumano(new Error("not-allowed")), /microfone/);
  assert.match(erroHumano(Object.assign(new Error("x"), { name: "NotAllowedError" })), /microfone/);
  assert.match(erroHumano(Object.assign(new Error("full"), { name: "QuotaExceededError" })), /sem espaço/);
  assert.match(erroHumano(new TypeError("Load failed")), /internet/);
  assert.match(erroHumano(new Error("WebGPU não disponível")), /WebGPU/);
  assert.equal(erroHumano(undefined), "Algo deu errado.");
  assert.match(erroHumano(new Error("coisa estranha"), "Falhou."), /^Falhou\. \(coisa estranha\)$/);
  assert.ok(erroHumano(new Error("a".repeat(500))).length < 220);
});

test("teclado: só conta como aberto quando a área visível encolhe bastante", () => {
  assert.deepEqual(medirTeclado({ height: 926, offsetTop: 0 }, { innerHeight: 926 }), { altura: 926, topo: 0, aberto: false });
  assert.equal(medirTeclado({ height: 860, offsetTop: 0 }, { innerHeight: 926 }).aberto, false);  // só a barra do Safari
  const m = medirTeclado({ height: 520, offsetTop: 40 }, { innerHeight: 926 });
  assert.equal(m.aberto, true); assert.equal(m.altura, 520); assert.equal(m.topo, 40);
  assert.equal(medirTeclado(null, { innerHeight: 700 }).aberto, false);  // sem visualViewport
});

const armazemFalso = () => { const d = new Map(); return { getItem: (k) => d.get(k) ?? null, setItem: (k, v) => d.set(k, v), removeItem: (k) => d.delete(k) }; };

test("retomada: lembra aba e rascunho, limita tamanho e sobrevive a armazenamento quebrado", () => {
  const r = new Retomada(armazemFalso());
  assert.deepEqual(r.ler(), { aba: "", texto: "" });
  r.gravar({ aba: "oficina" }); r.gravar({ texto: "x".repeat(9000) });
  assert.equal(r.ler().aba, "oficina"); assert.equal(r.ler().texto.length, 4000);
  r.gravar({ aba: "", texto: "" });
  assert.deepEqual(r.ler(), { aba: "", texto: "" });
  const quebrado = new Retomada({ getItem() { throw new Error("bloqueado"); }, setItem() { throw new Error("cheio"); }, removeItem() { throw new Error("x"); } });
  assert.deepEqual(quebrado.ler(), { aba: "", texto: "" });
  assert.doesNotThrow(() => quebrado.gravar({ texto: "oi" }));
  assert.deepEqual(new Retomada({ getItem: () => "{lixo" }).ler(), { aba: "", texto: "" });
});

test("retomada: ao reabrir devolve o texto e a aba; enviar limpa o rascunho", () => {
  const r = new Retomada(armazemFalso());
  r.gravar({ aba: "memoria", texto: "meio escrito" });
  const ouvintes = {};
  const clicks = [];
  const campo = { value: "", form: { addEventListener: (e, f) => { ouvintes.submit = f; } }, addEventListener: (e, f) => { ouvintes.input = f; } };
  const botoes = ["conversa", "memoria"].map((aba) => ({ dataset: { aba }, click: () => clicks.push(aba), addEventListener() {} }));
  ligarRetomada({ campo, abas: botoes, retomada: r, doc: { addEventListener() {}, hidden: false } });
  assert.equal(campo.value, "meio escrito"); assert.deepEqual(clicks, ["memoria"]);
  campo.value = "novo"; ouvintes.input();
  assert.equal(r.ler().texto, "novo");
  ouvintes.submit();
  assert.equal(r.ler().texto, "");
});

test("abas: 6 abas viram 4 + Mais; até 5 cabem todas na barra", () => {
  const seis = ["conversa", "memoria", "cerebro", "oficina", "instagram", "agenda"];
  assert.deepEqual(dividirAbas(seis), { barra: seis.slice(0, 4), mais: ["instagram", "agenda"] });
  assert.deepEqual(dividirAbas(seis.slice(0, 5)), { barra: seis.slice(0, 5), mais: [] });
  assert.deepEqual(dividirAbas([]), { barra: [], mais: [] });
});

test("atualização: só avisa quando já havia versão controlando e ainda não avisou", () => {
  assert.equal(precisaAvisar(true, false), true);
  assert.equal(precisaAvisar(false, false), false);  // primeira instalação
  assert.equal(precisaAvisar(true, true), false);
});

// Carrega o sw.js de verdade num contexto falso, para testar a estratégia offline.
function carregarSw({ rede, guardado = new Map(), put = async () => {} }) {
  const ouvintes = {};
  const caches = {
    match: async (req) => guardado.get(typeof req === "string" ? req : req.url),
    open: async () => ({ put, addAll: async () => {} }), keys: async () => [], delete: async () => true,
  };
  const self = { addEventListener: (n, f) => { ouvintes[n] = f; }, location: { origin: "http://x" }, skipWaiting() {}, clients: { claim() {} } };
  const Resposta = { error: () => "ERRO-DE-REDE" };
  vm.runInNewContext(readFileSync(new URL("../sw.js", import.meta.url), "utf8"), { self, caches, fetch: rede, URL, Response: Resposta, Promise, setTimeout });
  return async (req) => { let r; ouvintes.fetch({ request: req, respondWith: (p) => { r = p; } }); return r; };
}
const pedido = (url, mode = "no-cors") => ({ url: "http://x/" + url, method: "GET", mode });

test("service worker: sem rede serve o guardado; sem guardado e navegando, serve a página inicial", async () => {
  const guardado = new Map([["http://x/js/main.js", "VELHO"], ["./", "CASCA"]]);
  const cair = async () => { throw new TypeError("offline"); };
  const sw = carregarSw({ rede: cair, guardado });
  assert.equal(await sw(pedido("js/main.js")), "VELHO");
  assert.equal(await sw(pedido("nada", "navigate")), "CASCA");
  assert.equal(await sw(pedido("nada")), "ERRO-DE-REDE");
});

test("service worker: com internet usa a versão nova e só guarda respostas boas do próprio site", async () => {
  const guardadas = [];
  const boa = { ok: true, status: 200, type: "basic", clone() { return "copia"; } };
  const ruim = { ok: false, status: 404, type: "basic", clone() { return "copia404"; } };
  const guardado = new Map([["http://x/a", "VELHO"]]);
  const sw1 = carregarSw({ rede: async () => boa, guardado, put: async (_r, c) => guardadas.push(c) });
  assert.equal(await sw1(pedido("a")), boa);
  const sw2 = carregarSw({ rede: async () => ruim, guardado, put: async (_r, c) => guardadas.push(c) });
  assert.equal(await sw2(pedido("a")), ruim);
  await new Promise((r) => setTimeout(r, 10));
  assert.deepEqual(guardadas, ["copia"]);  // o 404 não substituiu o arquivo bom
});

test("service worker: cache cheio não derruba a resposta e o cache tem nome novo", async () => {
  const boa = { ok: true, status: 200, type: "basic", clone: () => "c" };
  const sw = carregarSw({ rede: async () => boa, put: async () => { throw new Error("QuotaExceededError"); } });
  assert.equal(await sw(pedido("b")), boa);
  assert.match(readFileSync(new URL("../sw.js", import.meta.url), "utf8"), /jarvis-movel-15/);
});
