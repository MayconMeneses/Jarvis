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
