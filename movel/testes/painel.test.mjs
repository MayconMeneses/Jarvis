// Temas (contraste AA), efeitos unificados com o orbe, uso de IA (contadores, custo, orçamento, importação segura) e painel de Agentes.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { AGENTES, Agentes, DIA, MINUTO, decidir, haQuanto } from "../js/agentes.js";
import { Agendador } from "../js/agendador.js";
import { Cerebro } from "../js/cerebro.js";
import { contraste } from "../js/design.js";
import { Memoria } from "../js/memoria.js";
import { Motor } from "../js/motor.js";
import { Nuvem } from "../js/nuvem.js";
import { TEMAS, aplicarEfeitos, aplicarTema, guardarTema, lerTema, temaValido } from "../js/temas.js";
import { Uso, custoDe, estimarTokens } from "../js/uso.js";
import { barras } from "../js/uso-grafico.js";

const css = readFileSync(new URL("../css/tema.css", import.meta.url), "utf8");
const base = readFileSync(new URL("../css/app.css", import.meta.url), "utf8");
const pegar = (texto) => Object.fromEntries([...texto.matchAll(/--([a-z-]+):\s*(#[0-9a-f]{6})/g)].map((m) => [m[1], m[2]]));
function variaveis(id) {
  const padrao = pegar(base), raiz = pegar(css.match(/:root \{([^}]*)\}/)[1]);
  if (id === "hud") return { ...padrao, ...raiz };
  return { ...padrao, ...raiz, ...pegar(css.match(new RegExp(`html\\[data-tema="${id}"\\] \\{([^}]*)\\}`))[1]) };
}

test("todos os temas têm bloco no CSS e passam no contraste AA (texto 4,5:1); alto contraste chega a 7:1", () => {
  assert.deepEqual(TEMAS.map((t) => t.id), ["hud", "ambar", "esmeralda", "contraste"]);
  for (const { id } of TEMAS) {
    const v = variaveis(id);
    for (const fundo of [v.fundo, v.painel, v.sel, v.codigo]) {
      for (const texto of [v.texto, v.suave, v.ciano]) assert.ok(contraste(texto, fundo) >= 4.5, `${id}: ${texto} sobre ${fundo} = ${contraste(texto, fundo).toFixed(2)}`);
    }
    for (const cor of [v.erro, v.ok, v.laranja]) assert.ok(contraste(cor, v.painel) >= 4.5, `${id}: ${cor} sobre o painel`);
  }
  const hc = variaveis("contraste");
  assert.ok(contraste(hc.texto, hc.fundo) >= 7 && contraste(hc.linha, hc.fundo) >= 3 && contraste(hc["sel-borda"], hc.fundo) >= 3);
});

test("tema vai no html, volta ao padrão se inválido e é guardado em meta (falha de armazenamento tolerada)", async () => {
  const atributos = {}, barra = { setAttribute: (k, v) => { atributos.barra = v; } };
  const doc = { documentElement: { setAttribute: (k, v) => { atributos[k] = v; } }, querySelector: () => barra };
  assert.equal(aplicarTema("ambar", doc), "ambar");
  assert.equal(atributos["data-tema"], "ambar");
  assert.equal(aplicarTema("<img>", doc), "hud");
  aplicarEfeitos("suave", doc);
  assert.equal(atributos["data-efeitos"], "suave");
  const memoria = new Memoria();
  await guardarTema(memoria, "esmeralda");
  assert.equal(await lerTema(memoria), "esmeralda");
  assert.equal(temaValido("x"), "hud");
  const quebrada = { meta: async () => { throw new Error("bloqueado"); }, definirMeta: async () => { throw new Error("bloqueado"); } };
  assert.equal(await lerTema(quebrada), "hud");
  await guardarTema(quebrada, "ambar");
});

test("o CSS corta animações com reduzir movimento, esconde a aurora fora do modo completo e sempre mostra o foco", () => {
  assert.match(css, /prefers-reduced-motion: reduce[\s\S]*#aurora \{ display: none !important/);
  assert.match(css, /html\[data-efeitos="completo"\] #aurora \{ display: block/);
  assert.match(css, /:focus-visible \{ outline: 2px/);
  assert.match(css, /html\[data-oculto\] #aurora \{ animation-play-state: paused/);
});

const DIA_FIXO = () => new Date("2026-10-20T12:00:00");

test("uso: conta chamadas e tokens por fonte, estima quando falta usage e calcula custo, economizado e orçamento", async () => {
  const uso = new Uso(new Memoria(), DIA_FIXO);
  await uso.registrar("gemini", { entrada: 1000000, saida: 100000 });
  await uso.registrar("gemini", { textoEntrada: "x".repeat(400), textoSaida: "y".repeat(80) });
  await uso.registrar("brave");
  await uso.registrar("aparelho", { entrada: 2000000, saida: 1000000 });
  await uso.registrar("../hack");  // id inválido é ignorado
  assert.equal(estimarTokens("x".repeat(400)), 100);
  const r = await uso.resumo();
  const g = r.fontes.find((f) => f.id === "gemini"), b = r.fontes.find((f) => f.id === "brave"), a = r.fontes.find((f) => f.id === "aparelho");
  assert.equal(r.fontes.length, 3);
  assert.deepEqual([g.c, g.e, g.s, g.x], [2, 1000100, 100020, 1]);
  assert.equal(b.c, 1); assert.equal(b.e, 0); assert.ok(Math.abs(b.custo - 0.005) < 1e-9);
  assert.equal(a.custo, 0);
  assert.ok(r.economizado > 0.89 && r.economizado < 0.91);  // 2M x 0,15 + 1M x 0,60 = 0,90
  assert.ok(Math.abs(custoDe({ c: 0, e: 1e6, s: 1e6 }, { e: 1, s: 2, c: 0 }) - 3) < 1e-9);
  assert.equal(r.pct, null);
  await uso.definirConfig({ orcamento: 1, alerta: 50 });
  const r2 = await uso.resumo();
  assert.ok(r2.pct > 50 && r2.alerta);
  assert.match(await uso.relatorio(), /Gasto estimado/);
  assert.equal((await uso.serieDiaria(3)).length, 3);
});

test("uso: exportar não leva chave nenhuma e importar descarta lixo e ids malucos", async () => {
  const memoria = new Memoria();
  await memoria.armazem.gravar("segredo:gemini", { provedor: "gemini", chave: "AIzaSy-segredo-123456" });
  const uso = new Uso(memoria, DIA_FIXO);
  await uso.registrar("gemini", { entrada: 5, saida: 6 });
  const json = await uso.exportar();
  assert.ok(!json.includes("AIzaSy") && !json.includes("segredo") && !/chave/i.test(json));
  const outra = new Uso(new Memoria(), DIA_FIXO);
  assert.equal(await outra.importar(json), 1);
  assert.equal((await outra.resumo()).fontes[0].e, 5);
  const sujo = JSON.stringify({ formato: "jarvis-uso-1", config: { orcamento: -5, alerta: "x", precos: { "<b>": { e: 1 }, gemini: { e: "9", s: -1 } } }, meses: { "2026-09": { "2026-09-01": { "<script>": { c: 1 }, groq: { c: 3, e: "abc", s: -2 } } }, lixo: {} } });
  await outra.importar(sujo);
  const cfg = await outra.config();
  assert.equal(cfg.orcamento, 0); assert.ok(!("<b>" in cfg.precos)); assert.deepEqual(cfg.precos.gemini, { e: 9, s: 0, c: 0 });
  assert.deepEqual((await outra.mes(new Date("2026-09-15T12:00:00")))["2026-09-01"], { groq: { c: 3, e: 0, s: 0, x: 0 } });
  await assert.rejects(outra.importar('{"formato":"outro"}'));
});

test("nuvem e cérebro do aparelho registram uso; a pergunta quanto gastei é reconhecida", async () => {
  const chamadas = [];
  const resposta = { ok: true, status: 200, body: null, json: async () => ({ choices: [{ message: { content: "oi" } }], usage: { prompt_tokens: 11, completion_tokens: 3 } }), text: async () => "" };
  const memoria = new Memoria();
  await memoria.armazem.gravar("segredo:gemini", { provedor: "gemini", chave: "AIzaSy-chave-de-teste-1234567890", base: "https://x.test/v1", modelo: "m" });
  const nuvem = new Nuvem({ armazem: memoria.armazem, buscar: async () => resposta, aoUsar: (f, d) => chamadas.push([f, d]) });
  await nuvem.perguntar([{ role: "user", content: "oi" }]);
  assert.equal(chamadas[0][0], "gemini"); assert.equal(chamadas[0][1].entrada, 11); assert.equal(chamadas[0][1].saida, 3);
  const cerebro = new Cerebro({ aoUsar: (f, d) => chamadas.push([f, d]), gpu: () => true });
  cerebro.engine = { chat: { completions: { create: async () => (async function* () { yield { choices: [{ delta: { content: "ola" } }] }; })() } } };
  await cerebro.perguntar([{ role: "user", content: "abcd" }]);
  assert.equal(chamadas[1][0], "aparelho"); assert.equal(chamadas[1][1].textoSaida, "ola");
  const motor = new Motor({ saber: { topicos: [], tecnologias: [], tipos: [], habilidades: [] }, memoria, buscar: async () => null });
  for (const frase of ["quanto gastei", "uso de IA", "quanto gastei com ia este mês"]) assert.equal(motor.classificar(frase), "uso_ia", frase);
});

test("gráfico: barras proporcionais ao custo, dia zerado sem barra", () => {
  const b = barras([{ dia: "a", custo: 0 }, { dia: "b", custo: 1 }, { dia: "c", custo: 0.5 }], 300, 140);
  assert.equal(b[0].h, 0); assert.ok(b[1].h > b[2].h && b[1].y < b[2].y); assert.ok(b.every((x) => x.x >= 0 && x.x + x.w <= 300));
});

test("agentes: estados ok/atrasado/erro/ocioso/desligado e app estava fechado como estado próprio", () => {
  const agora = 10 * DIA, sessao = agora - 5 * MINUTO;
  const c = (extra) => decidir({ agora, ultimo: agora - MINUTO, estado: "ok", cadenciaMs: MINUTO, ligado: true, inicioSessao: sessao, ...extra });
  assert.equal(c({}), "ok");
  assert.equal(c({ ligado: false }), "desligado");
  assert.equal(c({ ultimo: null }), "ocioso");
  assert.equal(c({ estado: "ocioso" }), "ocioso");
  assert.equal(c({ estado: "erro" }), "erro");
  assert.equal(c({ ultimo: agora - 2.5 * MINUTO }), "ok");        // fronteira exata ainda é ok
  assert.equal(c({ ultimo: agora - 2.5 * MINUTO - 1 }), "atrasado");
  assert.equal(c({ ultimo: sessao - 1 }), "fechado");             // batimento de antes de abrir o app: não é vermelho
  assert.equal(c({ ultimo: agora + MINUTO }), "ok");              // relógio recuado
  assert.equal(decidir({ agora, ultimo: sessao - DIA, cadenciaMs: 7 * DIA, inicioSessao: sessao }), "ok");  // semanal não vira fechado
  assert.equal(haQuanto(3 * MINUTO), "há 3 min");
});

test("agentes: batimentos gravados em meta e lidos por processo", async () => {
  let t = Date.parse("2026-10-20T10:00:00Z");
  const memoria = new Memoria();
  await memoria.definirMeta("agente:aprender:ultimo", "2026-10-19T10:00:00.000Z");  // de uma sessão anterior
  const ag = new Agentes(memoria, () => t);
  await ag.marcar("proativo");
  t += 30 * 1000;
  const lista = await ag.todos({ ligados: { aprender: true, cerebro: false }, ultimos: { avaliacao: null } });
  const por = Object.fromEntries(lista.map((a) => [a.id, a.situacao]));
  assert.deepEqual(Object.keys(por), AGENTES.map((a) => a.id));
  assert.equal(por.proativo, "ok"); assert.equal(por.aprender, "fechado"); assert.equal(por.cerebro, "desligado"); assert.equal(por.oficina, "ocioso");
  await ag.marcar("cerebro", "erro");
  assert.equal((await ag.todos({})).find((a) => a.id === "cerebro").situacao, "erro");
  await new Agentes({ definirMeta: async () => { throw new Error("x"); } }).marcar("oficina");
});

test("agendador bate o ponto: ocioso enquanto você usa, ok ao rodar, erro se a tarefa falhar", async () => {
  let agora = 0, falhar = false;
  const batidas = [];
  const ag = new Agendador({ tarefa: async () => { if (falhar) throw new Error("x"); }, relogio: () => agora, aoBater: (e) => batidas.push(e) });
  await ag.passo(); agora = 11 * MINUTO; await ag.passo(); falhar = true; agora = 23 * MINUTO; await ag.passo();
  assert.deepEqual(batidas, ["ocioso", "ok", "erro"]);
});
