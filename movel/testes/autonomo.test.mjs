// Aprender sozinha e avaliar o cérebro no celular: relógio, rede, conversa e sandbox falsos (nenhuma rede real).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { Agendador } from "../js/agendador.js";
import { MAX_POR_DIA, Autonomo, assuntoDe } from "../js/autonomo.js";
import { Avaliador, TAREFAS, arquivosDaTarefa, avaliar, codigoDe } from "../js/avaliar.js";
import { Memoria } from "../js/memoria.js";
import { Motor } from "../js/motor.js";
import { Saber } from "../js/saber.js";

const saber = new Saber(JSON.parse(readFileSync(new URL("../dados/saber.json", import.meta.url), "utf8")));
const resposta = (corpo, status = 200) => ({ ok: status < 400, status, json: async () => corpo });

function cenario({ pedidos = [], ligado = true } = {}) {
  const relogio = { agora: new Date("2026-10-19T10:00:00") };
  const memoria = new Memoria(undefined, () => relogio.agora);
  const urls = [];
  const buscar = async (url) => {
    urls.push(url);
    if (url.includes("list=search")) return resposta({ query: { search: [{ title: decodeURIComponent(/srsearch=([^&]+)/.exec(url)[1]), snippet: "trecho" }] } });
    return resposta({ extract: "Resumo do assunto.", content_urls: { desktop: { page: "https://pt.wikipedia.org/wiki/X" } } });
  };
  const autonomo = new Autonomo({ memoria, saber, buscar, relogio: () => relogio.agora });
  return { relogio, memoria, urls, autonomo, preparar: async () => {
    for (const p of pedidos) await memoria.diario(`Pedido: ${p}`);
    if (ligado) await autonomo.definirLigado(true);
  } };
}

test("assuntoDe: pega o assunto de perguntas e ignora o resto", () => {
  assert.equal(assuntoDe("O que é Computação Quântica?"), "computacao quantica");
  assert.equal(assuntoDe("explique o blockchain em python"), "blockchain");
  assert.equal(assuntoDe("que horas são"), null);
  assert.equal(assuntoDe("o que é isso"), null);
  assert.equal(assuntoDe("explique uma coisa muito longa com muitas palavras aqui"), null);
});

test("desligada por padrão: nada é estudado nem pesquisado", async () => {
  const c = cenario({ pedidos: ["o que é computacao quantica"], ligado: false });
  await c.preparar();
  assert.equal(await c.autonomo.ligado(), false);
  assert.equal(await c.autonomo.ciclo(), null);
  assert.equal(c.urls.length, 0);
});

test("estuda o assunto mais perguntado que a base não conhece e guarda a nota", async () => {
  const c = cenario({ pedidos: ["o que é computacao quantica", "explique fotossintese", "o que é computacao quantica?", "explique SOLID", "que horas são"] });
  await c.preparar();
  assert.deepEqual((await c.autonomo.candidatos()).map((x) => [x.assunto, x.mencoes]), [["computacao quantica", 2], ["fotossintese", 1]]);  // SOLID a base já conhece
  const feito = await c.autonomo.ciclo();
  assert.equal(feito.ok, true);
  assert.equal(feito.assunto, "computacao quantica");
  const nota = await c.memoria.ler("Aprendizado/computacao quantica");
  assert.match(nota.corpo, /Resumo do assunto[\s\S]*não verificado/);
  assert.match((await c.autonomo.relatorio()), /computacao quantica[\s\S]*Wikipédia/);
  assert.deepEqual((await c.autonomo.candidatos()).map((x) => x.assunto), ["fotossintese"]);  // não repete
});

test("no máximo 3 por dia; no dia seguinte volta a estudar", async () => {
  const c = cenario({ pedidos: ["o que é aaa1", "o que é bbb2", "o que é ccc3", "o que é ddd4"] });
  await c.preparar();
  for (let i = 0; i < MAX_POR_DIA; i++) assert.equal((await c.autonomo.ciclo()).ok, true);
  assert.equal(await c.autonomo.ciclo(), null);
  assert.equal(await c.autonomo.feitosHoje(), 3);
  c.relogio.agora = new Date("2026-10-20T10:00:00");
  assert.equal((await c.autonomo.ciclo()).assunto, "ddd4");
});

test("usa o Brave quando cadastrado e cai para a Wikipédia se ele falhar; erro de rede não derruba nem repete", async () => {
  const c = cenario({ pedidos: ["o que é computacao quantica"] });
  await c.preparar();
  const chamadas = [];
  c.autonomo.buscar = async (url, op) => { chamadas.push(url); if (url.includes("/brave/")) return resposta({ web: { results: [{ title: "K8s", url: "https://k8s.io", description: "Orquestrador" }] } }); throw new Error("sem rede"); };
  c.autonomo.brave = async () => ({ base: "https://proxy.exemplo", chave: "x" });
  const feito = await c.autonomo.ciclo();
  assert.equal(feito.origem, "Brave Search");
  assert.ok(chamadas[0].startsWith("https://proxy.exemplo/brave/"));

  const d = cenario({ pedidos: ["o que é computacao quantica"] });
  await d.preparar();
  d.autonomo.buscar = async () => { throw new Error("sem rede"); };
  const falha = await d.autonomo.ciclo();
  assert.equal(falha.ok, false);
  assert.equal(await d.memoria.ler("Aprendizado/computacao quantica"), null);
  assert.deepEqual(await d.autonomo.candidatos(), []);  // já tentado: não insiste todo dia
});

test("agendador: só dispara depois de 10 min parado e espaça as execuções", async () => {
  let agora = 0, execucoes = 0;
  const a = new Agendador({ tarefa: async () => { execucoes++; }, relogio: () => agora });
  agora = 9 * 60000; assert.equal(await a.passo(), false);
  agora = 10 * 60000; assert.equal(await a.passo(), true);
  agora = 15 * 60000; assert.equal(await a.passo(), false);  // precisa de outros 10 min parado
  agora = 18 * 60000; a.atividade();  // o usuário voltou
  agora = 27 * 60000; assert.equal(await a.passo(), false);
  agora = 28 * 60000; assert.equal(await a.passo(), true);
  assert.equal(execucoes, 2);
  let timer = null;
  const b = new Agendador({ tarefa: async () => {}, ligarTimer: (fn, ms) => (timer = { fn, ms }), pararTimer: () => (timer = "parado") });
  b.iniciar(); assert.equal(timer.ms, 60000);
  b.parar(); assert.equal(timer, "parado");
});

// ── avaliação ──────────────────────────────────────────────────────────────
const SOLUCOES = {
  ehPar: "function ehPar(n) { return n % 2 === 0; }",
  somaLista: "const somaLista = (xs) => xs.reduce((a, b) => a + b, 0);",
  maior: "function maior(xs) { return Math.max(...xs); }",
  palindromo: "function palindromo(s) { s = s.toLowerCase(); return s === [...s].reverse().join(''); }",
  fatorial: "function fatorial(n) { return n <= 1 ? 1 : n * fatorial(n - 1); }",
};
const funcaoDoPedido = (m) => /função (\w+)\(/.exec(m[0].content)[1];
// "sandbox" falso: avalia a solução com o assert/test de verdade do node, sem rede nem iframe.
const rodarFalso = async ({ arquivos }) => {
  const casos = [];
  const modulo = { exports: {} };
  new Function("module", arquivos["solucao.js"])(modulo);
  const requisicoes = { "node:test": (n, fn) => casos.push(fn), "node:assert": assert, "./solucao.js": modulo.exports };
  try { new Function("require", arquivos["solucao.test.js"])((n) => requisicoes[n]); for (const fn of casos) await fn(); return { ok: casos.length > 0 }; } catch (e) { return { ok: false }; }
};

test("codigoDe e arquivosDaTarefa: tira o bloco de código e exporta a função mesmo sem module.exports", () => {
  assert.equal(codigoDe("Aqui:\n```js\nconst a = 1;\n```\nfim"), "const a = 1;");
  assert.equal(codigoDe("const b = 2;"), "const b = 2;");
  const arq = arquivosDaTarefa("ehPar", SOLUCOES.ehPar, [[[4], true]]);
  assert.match(arq["solucao.js"], /module\.exports\.ehPar = ehPar/);
  assert.match(arq["solucao.test.js"], /ehPar\(\.\.\.\[4\]\), true/);
});

test("avaliar: acerta tudo com boas respostas e perde pontos com respostas erradas ou sandbox que falha", async () => {
  const boa = async (m) => "```js\n" + SOLUCOES[funcaoDoPedido(m)] + "\n```";
  const perfeita = await avaliar({ conversa: boa, rodar: rodarFalso });
  assert.deepEqual([perfeita.acertos, perfeita.total, perfeita.nota], [5, 5, 100]);

  const ruim = async (m) => (funcaoDoPedido(m) === "maior" ? "function maior(xs) { return xs[0]; }" : funcaoDoPedido(m) === "fatorial" ? "isto nem é código {" : SOLUCOES[funcaoDoPedido(m)]);
  const parcial = await avaliar({ conversa: ruim, rodar: rodarFalso });
  assert.deepEqual([parcial.acertos, parcial.nota], [3, 60]);
  assert.deepEqual(Object.entries(parcial.detalhes).filter(([, ok]) => !ok).map(([f]) => f), ["maior", "fatorial"]);

  const semConversa = await avaliar({ conversa: async () => { throw new Error("modelo caiu"); }, rodar: rodarFalso });
  assert.equal(semConversa.nota, 0);
  assert.equal(TAREFAS.length, 5);
});

test("avaliador: só roda com cérebro ligado, guarda nota com data, compara com a anterior e vence em 7 dias", async () => {
  const relogio = { agora: new Date("2026-10-19T10:00:00") };
  const memoria = new Memoria(undefined, () => relogio.agora);
  let ligado = false;
  const av = new Avaliador({ memoria, conversa: async (m) => SOLUCOES[funcaoDoPedido(m)], rodar: rodarFalso, disponivel: async () => ligado, rotulo: () => "Llama 1B", relogio: () => relogio.agora });
  assert.match(await av.executar(), /preciso de um cérebro ligado/);
  assert.equal((await av.historico()).length, 0);
  assert.equal(await av.vencida(), true);

  ligado = true;
  assert.match(await av.executar(), /nota 100\/100[\s\S]*Acertou tudo[\s\S]*primeira avaliação/);
  const [salva] = await av.historico();
  assert.deepEqual([salva.nota, salva.modelo, salva.quando], [100, "Llama 1B", relogio.agora.toISOString()]);
  assert.equal(await av.vencida(), false);
  assert.match(await av.resumo(), /nota 100\/100/);

  relogio.agora = new Date("2026-10-27T10:00:00");
  assert.equal(await av.vencida(), true);
  av.conversa = async () => "x ===";
  assert.match(await av.executar(), /nota 0\/100[\s\S]*anterior \(2026-10-19\) a nota foi 100/);
  assert.equal((await av.historico()).length, 2);
});

test("conversa: 'o que você aprendeu' e 'avaliar cérebro' / 'como está meu cérebro'", async () => {
  const c = cenario({ pedidos: ["o que é computacao quantica"] });
  await c.preparar();
  const motor = new Motor({ saber, memoria: c.memoria, buscar: async () => null, agora: () => c.relogio.agora });
  assert.equal(motor.classificar("o que você aprendeu?"), "aprendeu");
  assert.equal(motor.classificar("avaliar cérebro"), "avaliar_cerebro");
  assert.equal(motor.classificar("Como está meu cérebro?"), "avaliar_cerebro");
  assert.match(await motor.responder("avaliar cérebro"), /ainda não está carregada/);  // sem os objetos ligados, explica em vez de falhar
  assert.equal(motor.classificar("o que é computacao quantica"), "explicar");  // não rouba os pedidos de sempre

  motor.autonomo = c.autonomo;
  assert.match(await motor.responder("o que você aprendeu"), /Ainda não aprendi nada sozinha/);
  await c.autonomo.ciclo();
  assert.match(await motor.responder("o que você aprendeu"), /\*\*computacao quantica\*\*/);

  motor.avaliador = new Avaliador({ memoria: c.memoria, conversa: async (m) => SOLUCOES[funcaoDoPedido(m)], rodar: rodarFalso, disponivel: async () => false });
  assert.match(await motor.responder("como está meu cérebro"), /Ainda não avaliei/);
  assert.match(await motor.responder("avaliar cérebro"), /preciso de um cérebro ligado/);
});
