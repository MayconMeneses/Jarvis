// Cérebro de IA do celular, com um WebLLM falso (o modelo de verdade só roda no aparelho).
import assert from "node:assert/strict";
import test from "node:test";
import { Cerebro, MODELOS, RECOMENDADO, URL_WEBLLM } from "../js/cerebro.js";

function falso(modelos = MODELOS.map((m) => m.id)) {
  const chamadas = { importou: 0, descarregou: 0 };
  const lib = {
    prebuiltAppConfig: { model_list: modelos.map((model_id) => ({ model_id })) },
    async CreateMLCEngine(id, opcoes) {
      opcoes.initProgressCallback({ text: "baixando", progress: 0.5 });
      opcoes.initProgressCallback({ text: "pronto", progress: 1 });
      return {
        async unload() { chamadas.descarregou++; },
        chat: { completions: { async create({ messages }) {
          return (async function* () { for (const t of ["Olá", ", ", "mundo"]) yield { choices: [{ delta: { content: t } }] }; chamadas.ultimo = messages; })();
        } } },
      };
    },
  };
  return { chamadas, importar: async (url) => { chamadas.importou++; chamadas.url = url; return lib; } };
}

test("sem WebGPU o cérebro explica o que falta e não carrega nada", async () => {
  const f = falso();
  const c = new Cerebro({ importar: f.importar, gpu: () => undefined });
  assert.equal(c.suportado(), false);
  await assert.rejects(() => c.carregar(RECOMENDADO), /WebGPU.*iOS 26/);
  assert.equal(f.chamadas.importou, 0);
});

test("liga o modelo com progresso, responde em fluxo e desliga", async () => {
  const f = falso();
  const c = new Cerebro({ importar: f.importar, gpu: () => ({}) });
  const etapas = [];
  await c.carregar(RECOMENDADO, (texto, p) => etapas.push([texto, p]));
  assert.equal(f.chamadas.url, URL_WEBLLM);
  assert.match(URL_WEBLLM, /web-llm@\d+\.\d+\.\d+\//);  // versão fixa, nunca "latest"
  assert.deepEqual(etapas.at(-1), ["pronto", 1]);
  assert.ok(c.ligado() && c.modelo === RECOMENDADO);
  const parciais = [];
  const texto = await c.perguntar([{ role: "user", content: "oi" }], (t) => parciais.push(t));
  assert.equal(texto, "Olá, mundo");
  assert.deepEqual(parciais, ["Olá", "Olá, ", "Olá, mundo"]);
  await c.descarregar();
  assert.ok(!c.ligado() && f.chamadas.descarregou === 1);
  await assert.rejects(() => c.perguntar([]), /não está ligado/);
});

test("só oferece modelos que a versão da biblioteca tem e recusa ids desconhecidos", async () => {
  const f = falso(["gemma3-1b-it-q4f16_1-MLC", "outro-modelo"]);
  const c = new Cerebro({ importar: f.importar, gpu: () => ({}) });
  assert.deepEqual((await c.modelosDisponiveis()).map((m) => m.id), ["gemma3-1b-it-q4f16_1-MLC"]);
  await assert.rejects(() => c.carregar("outro-modelo"), /desconhecido/);
});

test("a lista de modelos está do menor para o maior e o recomendado existe", () => {
  assert.ok(MODELOS.some((m) => m.id === RECOMENDADO));
  assert.deepEqual(MODELOS.map((m) => m.mb).slice(0, 2), [380, 950]);
});

test("conflito de janela do Gemma (erro real de um iPhone): tenta de novo com uma janela desligada", async () => {
  const tentativas = [];
  const lib = {
    prebuiltAppConfig: { model_list: [] },
    async CreateMLCEngine(id, config, ajuste) {
      tentativas.push(ajuste);
      if (!ajuste?.sliding_window_size) {
        throw new Error("Only one of context_window_size and sliding_window_size can be positive. Got: context_window_size: 4096, sliding_window_size: 512");
      }
      return { chat: { completions: { create: async () => [] } }, unload: async () => {} };
    },
  };
  const c = new Cerebro({ importar: async () => lib, gpu: () => ({}) });
  await c.carregar("gemma3-1b-it-q4f16_1-MLC");
  assert.deepEqual(tentativas, [undefined, { sliding_window_size: -1 }]);
  assert.ok(c.ligado());
});

test("se nenhuma combinação de janela funciona, explica e sugere outro modelo; outros erros não são mascarados", async () => {
  const sempreErro = { prebuiltAppConfig: { model_list: [] }, async CreateMLCEngine() { throw new Error("sliding_window_size conflito"); } };
  const c = new Cerebro({ importar: async () => sempreErro, gpu: () => ({}) });
  await assert.rejects(() => c.carregar("gemma3-1b-it-q4f16_1-MLC"), /escolha outro.*Llama 1B/);
  let chamadas = 0;
  const memoria = { prebuiltAppConfig: { model_list: [] }, async CreateMLCEngine() { chamadas++; throw new Error("out of memory"); } };
  const d = new Cerebro({ importar: async () => memoria, gpu: () => ({}) });
  await assert.rejects(() => d.carregar(RECOMENDADO), /out of memory/);
  assert.equal(chamadas, 1);  // erro de memória não repete as tentativas de janela
});

test("o modelo recomendado não é o que deu conflito", () => {
  assert.ok(!RECOMENDADO.startsWith("gemma"));
});

test("contexto estourado: tenta de novo só com o sistema e a última fala (a conversa não encerra)", async () => {
  const usos = [];
  const lib = { prebuiltAppConfig: { model_list: [] }, async CreateMLCEngine() {
    return { chat: { completions: { async create({ messages }) {
      usos.push(messages.length);
      if (messages.length > 2) throw new Error("ContextWindowSizeExceededError: Prompt tokens exceed context window size");
      return (async function* () { yield { choices: [{ delta: { content: "ok" } }] }; })();
    } } }, unload: async () => {} };
  } };
  const c = new Cerebro({ importar: async () => lib, gpu: () => ({}) });
  await c.carregar(RECOMENDADO);
  const historico = [{ role: "system", content: "s" }, { role: "user", content: "a" }, { role: "assistant", content: "b" }, { role: "user", content: "c" }];
  assert.equal(await c.perguntar(historico), "ok");
  assert.deepEqual(usos, [4, 2]);
});

test("GPU perdida (o iPhone tomou a memória): religa o modelo e responde", async () => {
  let motores = 0, falhou = false;
  const lib = { prebuiltAppConfig: { model_list: [] }, async CreateMLCEngine() {
    motores++;
    return { chat: { completions: { async create() {
      if (!falhou) { falhou = true; throw new Error("GPUDevice was lost"); }
      return (async function* () { yield { choices: [{ delta: { content: "voltei" } }] }; })();
    } } }, unload: async () => {} };
  } };
  const c = new Cerebro({ importar: async () => lib, gpu: () => ({}) });
  await c.carregar(RECOMENDADO);
  const avisos = [];
  assert.equal(await c.perguntar([{ role: "user", content: "oi" }], () => {}, (a) => avisos.push(a)), "voltei");
  assert.equal(motores, 2);
  assert.match(avisos[0], /religando/);
});

test("outros erros do modelo continuam aparecendo (não são engolidos)", async () => {
  const lib = { prebuiltAppConfig: { model_list: [] }, async CreateMLCEngine() {
    return { chat: { completions: { async create() { throw new Error("falha desconhecida"); } } }, unload: async () => {} };
  } };
  const c = new Cerebro({ importar: async () => lib, gpu: () => ({}) });
  await c.carregar(RECOMENDADO);
  await assert.rejects(() => c.perguntar([{ role: "system", content: "s" }, { role: "user", content: "a" }]), /falha desconhecida/);
});
