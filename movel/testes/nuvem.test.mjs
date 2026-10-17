// Chaves de API no celular: testar antes de guardar, recuperar de modelo aposentado, tentar os provedores em ordem e nunca exportar a chave.
import assert from "node:assert/strict";
import test from "node:test";
import { Memoria } from "../js/memoria.js";
import { Nuvem, PROVEDORES } from "../js/nuvem.js";

const CHAVE = "AIzaSy-chave-de-teste-1234567890";
const resposta = (status, corpo) => ({ ok: status < 400, status, json: async () => corpo, text: async () => JSON.stringify(corpo), body: null });
const sse = (partes) => ({ ok: true, status: 200, body: { getReader() { const itens = [...partes.map((p) => `data: ${JSON.stringify({ choices: [{ delta: { content: p } }] })}\n\n`), "data: [DONE]\n\n"].map((t) => new TextEncoder().encode(t)); let i = 0; return { read: async () => (i < itens.length ? { done: false, value: itens[i++] } : { done: true }) }; } } });

function servidor(regra) {
  const chamadas = [];
  const buscar = async (url, opcoes = {}) => { chamadas.push({ url, corpo: opcoes.body ? JSON.parse(opcoes.body) : null, auth: opcoes.headers?.Authorization }); return regra(url, opcoes.body ? JSON.parse(opcoes.body) : null); };
  return { buscar, chamadas };
}

test("testa a chave antes de guardar e nunca a exporta na cópia de segurança", async () => {
  const memoria = new Memoria();
  const s = servidor(() => resposta(200, { choices: [{ message: { content: "ok" } }] }));
  const nuvem = new Nuvem({ armazem: memoria.armazem, buscar: s.buscar });
  assert.equal(await nuvem.salvar("gemini", CHAVE), PROVEDORES.gemini.modelo);
  assert.equal(s.chamadas[0].auth, `Bearer ${CHAVE}`);
  assert.deepEqual((await nuvem.salvas()).map((x) => x.id), ["gemini"]);
  await memoria.guardar("Teste/a", "nota", "nota");
  assert.ok(!(await memoria.exportar()).includes(CHAVE));  // a chave fica fora da cópia de segurança
  await nuvem.remover("gemini");
  assert.equal(await nuvem.configurada(), false);
});

test("chave recusada ou curta não é guardada", async () => {
  const memoria = new Memoria();
  const nuvem = new Nuvem({ armazem: memoria.armazem, buscar: servidor(() => resposta(401, { error: "invalid" })).buscar });
  await assert.rejects(() => nuvem.salvar("gemini", CHAVE), /chave recusada/);
  await assert.rejects(() => nuvem.salvar("gemini", "curta"), /muito curta/);
  await assert.rejects(() => nuvem.salvar("personalizado", CHAVE, { base: "http://inseguro/v1" }), /https/);
  assert.equal(await nuvem.configurada(), false);
});

test("modelo padrão aposentado: acha outro de conversa que a chave enxerga", async () => {
  const memoria = new Memoria();
  const s = servidor((url, corpo) => {
    if (url.endsWith("/models")) return resposta(200, { data: [{ id: "models/gemini-2.5-flash" }, { id: "models/gemini-3.8-flash" }, { id: "models/gemini-3.8-flash-lite" }, { id: "models/text-embedding-004" }] });
    return corpo.model === "gemini-3.8-flash" ? resposta(200, { choices: [{ message: { content: "ok" } }] }) : resposta(404, { error: "not found" });
  });
  const nuvem = new Nuvem({ armazem: memoria.armazem, buscar: s.buscar });
  assert.equal(await nuvem.salvar("gemini", CHAVE), "gemini-3.8-flash");
  assert.equal((await nuvem.salvas())[0].modelo, "gemini-3.8-flash");
});

test("a NVIDIA direto do navegador falha com uma explicação (o servidor dela não libera CORS)", async () => {
  const memoria = new Memoria();
  const nuvem = new Nuvem({ armazem: memoria.armazem, buscar: async () => { throw new TypeError("Failed to fetch"); } });
  await assert.rejects(() => nuvem.salvar("nvidia", CHAVE, { base: "https://integrate.api.nvidia.com/v1" }), /bloqueou.*proxy/);
  assert.ok(PROVEDORES.nvidia.exigeBase && PROVEDORES.nvidia.base === "");  // por padrão pede a URL do proxy, não a da NVIDIA
});

test("pergunta em fluxo, passa para o próximo provedor se um falhar e recupera de modelo aposentado depois de salvo", async () => {
  const memoria = new Memoria();
  const nuvem = new Nuvem({ armazem: memoria.armazem, buscar: servidor(() => resposta(200, { choices: [{ message: { content: "ok" } }] })).buscar });
  await nuvem.salvar("gemini", CHAVE);
  await nuvem.salvar("groq", "gsk_chave_de_teste_1234567890");
  const parciais = [];
  const s2 = servidor((url, corpo) => {
    if (url.includes("generativelanguage")) return resposta(429, { error: "quota" });
    return sse(["Olá", ", ", "mundo"]);
  });
  nuvem.buscar = s2.buscar;
  const r = await nuvem.perguntar([{ role: "user", content: "oi" }], (t) => parciais.push(t));
  assert.equal(r.texto, "Olá, mundo");
  assert.equal(r.provedor, "Groq");
  assert.deepEqual(parciais, ["Olá", "Olá, ", "Olá, mundo"]);
  assert.ok(s2.chamadas.every((c) => c.corpo === null || c.corpo.stream === true));
  // todos falham: o erro lista cada provedor
  nuvem.buscar = servidor(() => resposta(429, {})).buscar;
  await assert.rejects(() => nuvem.perguntar([{ role: "user", content: "x" }], () => {}), /gemini: limite de uso.*groq: limite de uso/);
  await assert.rejects(() => new Nuvem({ armazem: new Memoria().armazem }).perguntar([], () => {}), /nenhuma chave/);
});

test("proxy da NVIDIA: só aceita o app, só /v1 e repassa a chave sem guardar", async () => {
  const { default: worker } = await import("../proxy/nvidia-worker.js");
  let repassado;
  globalThis.fetch = async (url, init) => { repassado = { url, init }; return new Response('{"ok":true}', { status: 200, headers: { "Content-Type": "application/json" } }); };
  const origem = "https://mayconmeneses.github.io";
  const req = (metodo, caminho, cab = {}, corpo) => new Request("https://proxy.exemplo.workers.dev" + caminho, { method: metodo, headers: cab, body: corpo });
  assert.equal((await worker.fetch(req("OPTIONS", "/v1/chat/completions", { Origin: origem }))).status, 204);
  assert.equal((await worker.fetch(req("POST", "/v1/chat/completions", { Origin: "https://outro-site.com" }, "{}"))).status, 403);
  assert.equal((await worker.fetch(req("GET", "/admin", { Origin: origem }))).status, 404);
  const ok = await worker.fetch(req("POST", "/v1/chat/completions", { Origin: origem, Authorization: "Bearer nvapi-x", "Content-Type": "application/json" }, '{"a":1}'));
  assert.equal(ok.status, 200);
  assert.equal(ok.headers.get("Access-Control-Allow-Origin"), origem);
  assert.equal(repassado.url, "https://integrate.api.nvidia.com/v1/chat/completions");
  assert.equal(repassado.init.headers.authorization, "Bearer nvapi-x");
});

test("proxy: a rota do Brave repassa só o token de busca e tira o prefixo /brave", async () => {
  const { default: worker } = await import("../proxy/nvidia-worker.js");
  let repassado;
  globalThis.fetch = async (url, init) => { repassado = { url, init }; return new Response('{"web":{"results":[]}}', { status: 200 }); };
  const origem = "https://mayconmeneses.github.io";
  const r = await worker.fetch(new Request("https://proxy.exemplo.workers.dev/brave/res/v1/web/search?q=teste", { headers: { Origin: origem, "X-Subscription-Token": "tok-brave", Authorization: "Bearer nao-deve-passar" } }));
  assert.equal(r.status, 200);
  assert.equal(repassado.url, "https://api.search.brave.com/res/v1/web/search?q=teste");
  assert.equal(repassado.init.headers["x-subscription-token"], "tok-brave");
  assert.equal(repassado.init.headers.authorization, undefined);  // a chave de outro serviço nunca vai para o Brave
  assert.equal((await worker.fetch(new Request("https://p.workers.dev/brave/admin", { headers: { Origin: origem } }))).status, 404);
});

test("Brave Search: cadastrar testa a busca, vira a fonte de pesquisa e não conta como cérebro de conversa", async () => {
  const memoria = new Memoria();
  const s = servidor((url) => resposta(200, { web: { results: [
    { title: "Quasares", url: "https://exemplo.org/quasares", description: "Quasares são <strong>núcleos</strong> galácticos muito brilhantes." },
    { title: "Mais", url: "https://exemplo.org/mais", description: "Emitem jatos de energia." }] } }));
  const nuvem = new Nuvem({ armazem: memoria.armazem, buscar: s.buscar });
  assert.equal(await nuvem.salvar("brave", "BSA-chave-de-teste-1234567890", { base: "https://meu-proxy.workers.dev" }), "busca na web");
  assert.ok(s.chamadas[0].url.startsWith("https://meu-proxy.workers.dev/brave/res/v1/web/search"));
  assert.equal(await nuvem.configurada(), false);  // só busca: não responde conversa
  const { Motor } = await import("../js/motor.js");
  const { Saber } = await import("../js/saber.js");
  const m = new Motor({ saber: new Saber({}), memoria, buscar: s.buscar, brave: () => nuvem.brave() });
  const r = await m.responder("aprenda sobre quasares");
  assert.match(r, /Brave Search/);
  assert.match((await memoria.ler("Aprendizado/quasares")).corpo, /núcleos galácticos muito brilhantes[\s\S]*jatos de energia/);
  assert.match(await m.responder("pesquise sobre quasares"), /\(Brave Search\)/);
  assert.ok(!(await memoria.exportar()).includes("BSA-chave"));
});

test("Brave com chave recusada ou fora do ar: a pesquisa cai para a Wikipédia sem travar", async () => {
  const memoria = new Memoria();
  const chamadas = [];
  const buscar = async (url) => {
    chamadas.push(url);
    if (url.includes("/brave/")) return resposta(401, {});
    return url.includes("list=search") ? resposta(200, { query: { search: [{ title: "Quasar", snippet: "x" }] } }) : resposta(200, { extract: "Quasares são núcleos ativos.", content_urls: { desktop: { page: "https://pt.wikipedia.org/wiki/Quasar" } } });
  };
  const { Motor } = await import("../js/motor.js");
  const { Saber } = await import("../js/saber.js");
  const m = new Motor({ saber: new Saber({}), memoria, buscar, brave: async () => ({ chave: "k", base: "https://p.workers.dev" }) });
  assert.match(await m.responder("pesquise sobre quasares"), /\(Wikipédia\)/);
  assert.ok(chamadas[0].includes("/brave/") && chamadas.length > 1);
});
