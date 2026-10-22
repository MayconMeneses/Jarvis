// "Silêncio nunca": vocativo no fim da frase, saudações por horário, os 3 modos de "Como pensar", prazo das IAs, nada na nuvem no modo aprender
// e o fluxo do modo foco de ponta a ponta com reconhecimento FALSO. Prova a lógica no Node; NÃO prova o iPhone/Safari nem o microfone reais.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { EscutaContinua } from "../js/escuta.js";
import { criarEstadoFoco } from "../js/foco-estado.js";
import { ligarFocoVoz } from "../js/foco-voz.js";
import { criarCaminhos } from "../js/ia-caminhos.js";
import { limite } from "../js/limite.js";
import { ArmazemMemoria } from "../js/memoria.js";
import { Nuvem } from "../js/nuvem.js";
import { AVISO_NUVEM, DICA_SEM_CEREBRO, NOTA_APRENDER, Pensador, SEM_CHAVE_NUVEM } from "../js/pensar.js";
import { ehSaudacao, responderSaudacao } from "../js/saudacao.js";
import { extrairChamada, extrairComando } from "../js/voz-ativacao.js";
import { montar } from "./auxiliar-entendimento.mjs";

const dado = (nome) => JSON.parse(readFileSync(new URL(`./dados/${nome}`, import.meta.url), "utf8"));

test("vocativo no fim: casos compartilhados aceitos e menções rejeitadas", () => {
  const { aceitar, rejeitar } = dado("ativacao_vocativo.json");
  for (const [frase, comando] of aceitar) assert.equal(extrairChamada(frase), comando, frase);
  for (const frase of rejeitar) assert.equal(extrairChamada(frase), null, JSON.stringify(frase));
});

test("a regra antiga (nome no começo) continua igual", () => {
  for (const f of ["Jarvis, que horas são", "Hey Jarvis, tudo bem?", "Veja, Jarvis, que horas são."]) assert.equal(extrairChamada(f), extrairComando(f), f);
  assert.equal(extrairComando("oi, boa noite, Jarvis"), null);  // o extrairComando "puro" é o do Python; o vocativo é a extensão
});

test("saudações puras: casos compartilhados", () => {
  const { sim, nao } = dado("saudacoes.json");
  for (const f of sim) assert.ok(ehSaudacao(f), f);
  for (const f of nao) assert.ok(!ehSaudacao(f), JSON.stringify(f));
});

test("saudação responde com a hora certa, com e sem nome", () => {
  const em = (h) => new Date(2026, 9, 21, h, 0);
  assert.match(responderSaudacao("oi", em(9), "Maycon"), /^Bom dia, Maycon! .*Em que posso ajudar/);
  assert.match(responderSaudacao("oi, boa noite, Jarvis", em(15)), /^Boa tarde! /);
  assert.match(responderSaudacao("boa noite", em(21)), /^Boa noite! /);
  assert.match(responderSaudacao("oi tudo bem", em(21)), /Tudo bem por aqui/);
  assert.equal(responderSaudacao("oi, que horas são", em(9)), null);
});

test("o motor responde saudações (nunca 'não entendi'), com e sem entendimento", async () => {
  const { motor } = montar({ relogio: () => new Date(2026, 9, 21, 21, 0) });
  for (const f of ["oi, boa noite, Jarvis", "boa noite Jarvis", "oi", "olá", "bom dia", "e aí"]) assert.match(await motor.responder(f), /^Boa noite! /, f);
  assert.match(await motor.responder("que horas são"), /Agora são/);
  motor.entendimento = null;
  assert.match(await motor.responder("oi"), /^Boa noite! /);
});

// ── pensador ───────────────────────────────────────────────────────────────
function cenario({ aparelhoLigado = false, nuvemConfig = false, regras = {}, aparelho, nuvem, limiteMs = 40, meta = {} } = {}) {
  const dados = new Map(Object.entries(meta)), saida = { mostrados: [], erros: [], avisos: [], chamadas: [] };
  const memoria = { meta: async (k) => dados.get(k), definirMeta: async (k, v) => { dados.set(k, v); } };
  const cerebro = { ligado: () => cenario.ligado };
  cenario.ligado = aparelhoLigado;
  const nuv = { configurada: async () => nuvemConfig };
  const motor = { entendimento: { tomarWidget: () => null, registrarIA: async (t) => { saida.chamadas.push("registrarIA:" + t); } },
    responder: async (t) => (t in regras ? regras[t] : null), fallback: async (t) => `Não entendi “${t}”.` };
  const caminhos = {
    perguntarAparelho: async (t, ms) => { saida.chamadas.push("aparelho"); return limite(aparelho ? aparelho(t, ms) : "resposta do aparelho", ms); },
    perguntarNuvem: async (t, ms) => { saida.chamadas.push("nuvem"); return nuvem ? nuvem(t, ms) : "resposta da nuvem"; },
  };
  const p = new Pensador({ motor, cerebro, nuvem: nuv, memoria, caminhos, limiteMs, mostrar: (t, w, c = "jarvis") => saida.mostrados.push([c, t]), erro: (t) => saida.erros.push(t), avisar: (t) => saida.avisos.push(t) });
  return { p, saida, dados, cerebro, nuv };
}
const via = (s) => s.chamadas.filter((c) => c === "aparelho" || c === "nuvem");

test("regras respondem primeiro, sem gastar IA", async () => {
  const { p, saida } = cenario({ aparelhoLigado: true, nuvemConfig: true, regras: { "que horas são": "Agora são 10:00." } });
  assert.equal(await p.pensar("que horas são"), "Agora são 10:00.");
  assert.deepEqual(via(saida), []);
  assert.deepEqual(saida.mostrados, [["jarvis", "Agora são 10:00."]]);
});

test("automático: aparelho ligado responde; se falha ou demora, a nuvem assume", async () => {
  let c = cenario({ aparelhoLigado: true, nuvemConfig: true });
  assert.equal(await c.p.pensar("conte uma história"), "resposta do aparelho");
  assert.deepEqual(via(c.saida), ["aparelho"]);
  assert.equal(await c.p.status(), "cérebro: aparelho (automático)");

  c = cenario({ aparelhoLigado: true, nuvemConfig: true, aparelho: async () => { throw new Error("GPU perdida"); } });
  assert.equal(await c.p.pensar("x"), "resposta da nuvem");
  assert.deepEqual(via(c.saida), ["aparelho", "nuvem"]);
  assert.match(c.saida.mostrados[0][1], /cérebro do aparelho \(GPU perdida\)/);

  c = cenario({ aparelhoLigado: true, nuvemConfig: true, aparelho: () => new Promise(() => {}), limiteMs: 30 });  // lento demais: nunca responde
  assert.equal(await c.p.pensar("x"), "resposta da nuvem");
  assert.deepEqual(via(c.saida), ["aparelho", "nuvem"]);
});

test("automático: cérebro do aparelho desligado -> nuvem sozinha, com aviso UMA vez", async () => {
  const c = cenario({ aparelhoLigado: true, nuvemConfig: true });
  cenario.ligado = false;
  await c.p.cerebroMudou(false);  // o dono desligou o cérebro
  assert.deepEqual(c.saida.avisos, [AVISO_NUVEM]);
  assert.equal(await c.p.pensar("a"), "resposta da nuvem");
  assert.equal(await c.p.pensar("b"), "resposta da nuvem");
  assert.deepEqual(c.saida.avisos, [AVISO_NUVEM]);  // não repete
  assert.equal(await c.p.status(), "cérebro: nuvem (automático)");
  cenario.ligado = true; await c.p.cerebroMudou(true);  // ligou de novo: volta ao aparelho
  assert.equal(await c.p.pensar("c"), "resposta do aparelho");
});

test("automático sem aparelho e sem nuvem: só regras, com dica clara uma vez; nunca vazio", async () => {
  const c = cenario();
  const a = await c.p.pensar("conte uma história");
  assert.match(a, /^Não entendi/);
  assert.ok(a.includes(DICA_SEM_CEREBRO));
  const b = await c.p.pensar("outra");
  assert.ok(!b.includes(DICA_SEM_CEREBRO) && b.trim());
  assert.equal(await c.p.status(), "cérebro: regras (automático)");
});

test("todos os caminhos de IA falham: resposta de regras com o motivo, nunca silêncio", async () => {
  const c = cenario({ aparelhoLigado: true, nuvemConfig: true, aparelho: async () => { throw new Error("sem memória"); }, nuvem: async () => { throw new Error("HTTP 429"); } });
  const r = await c.p.pensar("x");
  assert.match(r, /A IA não respondeu agora/);
  assert.equal(c.saida.mostrados.filter(([k]) => k === "jarvis aviso").length, 2);
  assert.equal(c.saida.mostrados.at(-1)[1], r);
});

test("modo aprender: nunca chama a nuvem (nem o aparelho), registra e explica que está aprendendo", async () => {
  const c = cenario({ aparelhoLigado: true, nuvemConfig: true, meta: { cerebro_modo: "aprender" } });
  await c.p.iniciar();
  const r = await c.p.pensar("conte uma história");
  assert.deepEqual(via(c.saida), []);
  assert.ok(r.includes(NOTA_APRENDER));
  assert.equal(await c.p.status(), "cérebro: aprender (só aparelho)");
  assert.equal(c.dados.get("cerebro_modo"), "aprender");
});

test("modo só nuvem: ignora o aparelho; sem chave, erro claro em português", async () => {
  let c = cenario({ aparelhoLigado: true, nuvemConfig: true, meta: { cerebro_modo: "nuvem" } });
  await c.p.iniciar();
  assert.equal(await c.p.pensar("x"), "resposta da nuvem");
  assert.deepEqual(via(c.saida), ["nuvem"]);
  c = cenario({ aparelhoLigado: true, meta: { cerebro_modo: "nuvem" } });
  await c.p.iniciar();
  assert.equal(await c.p.pensar("x"), SEM_CHAVE_NUVEM);
  assert.deepEqual(c.saida.erros, [SEM_CHAVE_NUVEM]);
  assert.match(SEM_CHAVE_NUVEM, /Cérebro > Nuvem/);
});

test("modo inválido salvo volta ao automático; trocar de modo grava", async () => {
  const c = cenario({ meta: { cerebro_modo: "qualquer" } });
  await c.p.iniciar();
  assert.equal(c.p.modoAtual, "automatico");
  await c.p.definirModo("aprender");
  assert.equal(c.dados.get("cerebro_modo"), "aprender");
  await c.p.definirModo("invalido");
  assert.equal(c.p.modoAtual, "aprender");
});

test("pensar() nunca lança nem devolve vazio: erro inesperado e travamento total viram mensagem", async () => {
  let c = cenario();
  c.p.motor.responder = async () => { throw new Error("banco quebrou"); };
  let r = await c.p.pensar("x");
  assert.match(r, /Não consegui responder: banco quebrou/);
  assert.equal(c.saida.erros.length, 1);
  c = cenario({ limiteMs: 10 });
  c.p.motor.responder = () => new Promise(() => {});
  r = await c.p.pensar("x");
  assert.match(r, /demorei mais de/);
  assert.ok(r.trim());
});

test("duas falhas seguidas do aparelho: descansa e vai direto à nuvem (se houver)", async () => {
  let agora = 1000;
  const c = cenario({ aparelhoLigado: true, nuvemConfig: true, aparelho: async () => { throw new Error("x"); } });
  c.p.agora = () => agora;
  await c.p.pensar("a"); await c.p.pensar("b");
  c.saida.chamadas.length = 0;
  await c.p.pensar("c");
  assert.deepEqual(via(c.saida), ["nuvem"]);
  agora += 11 * 60 * 1000;
  await c.p.pensar("d");
  assert.equal(via(c.saida)[1], "aparelho");
});

test("caminho do aparelho real: IA que trava estoura o prazo, a bolha some e o estado destrava", async () => {
  const bolhas = [], estados = [];
  const bolha = { remove() { bolhas.push("removida"); } };
  const d = { motor: { consultarAntes: async () => "", entendimento: null }, saber: {}, memoria: {}, contexto: { sistema: async () => "sistema" }, nome: async () => "Maycon", cartoes: async () => {},
    conversa: { paraPrompt: () => [] }, cerebro: { modelo: "m", perguntar: () => new Promise(() => {}) }, agentes: { marcar() {} },
    adicionar: () => bolha, atualizar() {}, pensando: (sim) => estados.push(sim) };
  await assert.rejects(criarCaminhos(d).perguntarAparelho("oi", 20), /demorou mais de/);
  assert.deepEqual(bolhas, ["removida"]);
  assert.equal(estados.at(-1), false);
  d.cerebro.perguntar = async () => "   ";  // resposta vazia também é falha explícita
  await assert.rejects(criarCaminhos(d).perguntarAparelho("oi", 20), /resposta vazia/);
});

test("limite(): rejeita com a mensagem e solta o relógio", async () => {
  await assert.rejects(limite(new Promise(() => {}), 10, "demorou"), /demorou/);
  assert.equal(await limite(Promise.resolve(7), 1000), 7);
});

test("nuvem bloqueada (modo aprender): nada é enviado, nem pela Oficina/documentos", async () => {
  const enviados = [];
  const n = new Nuvem({ armazem: new ArmazemMemoria(), buscar: async (...a) => { enviados.push(a); throw new Error("não devia chamar"); } });
  await n.armazem.gravar?.("segredo:groq", { provedor: "groq", chave: "chave-ficticia", modelo: "m" }).catch(() => {});
  n.bloqueio = () => true;
  await assert.rejects(n.perguntar([{ role: "user", content: "segredo" }], () => {}), /modo aprender/);
  assert.equal(enviados.length, 0);
});

// ── modo foco de ponta a ponta, com reconhecimento falso ───────────────────
class Rec {
  static todas = [];
  constructor() { Rec.todas.push(this); }
  start() { this.onstart?.(); }
  abort() {}
  dizer(texto) { this.onresult?.({ resultIndex: 0, results: [Object.assign([{ transcript: texto }], { isFinal: true })] }); }
}

async function focoCompleto() {
  Rec.todas = [];
  const { motor } = montar({ relogio: () => new Date(2026, 9, 21, 21, 0) });
  const mostrados = [];
  const memoria = { meta: async () => undefined, definirMeta: async () => {} };
  const p = new Pensador({ motor, cerebro: { ligado: () => false }, nuvem: { configurada: async () => false }, memoria, caminhos: {}, mostrar: (t) => mostrados.push(t), erro: (t) => mostrados.push(t), avisar: () => {} });
  const escuta = new EscutaContinua({ Reconhecimento: Rec, esperar: () => 0, cancelar: () => {}, seguro: true });
  const comandos = [];
  escuta.configurar({ aoComando: async (c) => { comandos.push(c); await p.pensar(c); } });
  const foco = criarEstadoFoco();
  ligarFocoVoz({ foco, escuta });
  return { foco, escuta, comandos, mostrados, rec: () => Rec.todas.at(-1) };
}
const esperar = () => new Promise((r) => setTimeout(r, 5));

test("foco: tocar em Falar e dizer 'oi, boa noite, Jarvis' gera a saudação (antes ficava mudo)", async () => {
  const f = await focoCompleto();
  await f.foco.pressionarMicrofone();
  f.rec().dizer("oi, boa noite, Jarvis");
  await esperar();
  assert.deepEqual(f.comandos, ["oi, boa noite"]);
  assert.match(f.mostrados[0], /^Boa noite! /);
  f.escuta.parar();
});

test("foco: depois de tocar em Falar, a primeira frase vale mesmo sem o nome; a seguinte volta a exigir 'Jarvis'", async () => {
  const f = await focoCompleto();
  await f.foco.pressionarMicrofone();
  f.rec().dizer("oi");
  await esperar();
  f.rec().dizer("boa noite");  // sem o nome e fora da janela: ignorada (anti falso positivo)
  await esperar();
  f.rec().dizer("boa noite Jarvis");
  await esperar();
  assert.deepEqual(f.comandos, ["oi", "boa noite"]);
  assert.equal(f.mostrados.length, 2);
  f.escuta.parar();
});

test("foco: conversa ao fundo sem chamar a Jarvis não responde nada", async () => {
  const f = await focoCompleto();
  await f.foco.pressionarMicrofone();
  f.rec().dizer("oi");  // consome a janela do toque
  await esperar();
  for (const t of ["o Jarvis é legal", "falei com o Jarvis ontem", "boa noite pessoal"]) { f.rec().dizer(t); await esperar(); }
  assert.deepEqual(f.comandos, ["oi"]);
  f.escuta.parar();
});
