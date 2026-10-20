// Criar com IA: o mesmo fluxo do PC (planejar, escrever um por vez, conferir, testar no sandbox, reparar), com uma conversa falsa.
import assert from "node:assert/strict";
import test from "node:test";
import { conferir, criar, extrairCodigo, interpretarPlano, leiame, sintaxeJs } from "../js/criar-ia.js";

const cerca = (t, l = "js") => "```" + l + "\n" + t + "\n```";

test("extrairCodigo pega o primeiro bloco ou tira cercas soltas", () => {
  assert.equal(extrairCodigo("Aqui:\n" + cerca("let a = 1;") + "\nFim"), "let a = 1;");
  assert.equal(extrairCodigo("```py\nx = 1\n```"), "x = 1");
  assert.equal(extrairCodigo("\n\nsó texto\n"), "só texto");
});

test("interpretarPlano aceita listas, ignora README, caminhos ruins e repetidos, e respeita o limite", () => {
  const texto = ["Plano:", "1. `calc.js`: soma e subtração", "- calc.test.js - testes da calc", "* README.md: docs", "/etc/passwd.txt: ruim", "../x.js: ruim",
    "calc.js: de novo", "run.exe: não permitido", "tosco sem formato", "> util/ajuda.py — ajuda"].join("\n");
  assert.deepEqual(interpretarPlano(texto), [["calc.js", "soma e subtração"], ["calc.test.js", "testes da calc"], ["util/ajuda.py", "ajuda"]]);
  assert.equal(interpretarPlano(Array.from({ length: 12 }, (_, i) => `a${i}.js: x`).join("\n")).length, 8);
});

test("conferir: vazio, JSON, sintaxe JS (sem executar) e Python só com verificador", async () => {
  assert.equal(await conferir("a.js", "  "), "o arquivo ficou vazio");
  assert.match(await conferir("a.json", "{x"), /JSON inválido/);
  assert.equal(await conferir("a.json", '{"x":1}'), null);
  assert.match(await conferir("a.js", "function ("), /sintaxe JavaScript/);
  assert.match(sintaxeJs("import x from 'y';"), /require\/module\.exports/);
  globalThis.__executou = false;
  assert.equal(sintaxeJs("globalThis.__executou = true;"), null);
  assert.equal(globalThis.__executou, false);  // só compilou, não rodou
  assert.equal(await conferir("a.py", "def ("), null);  // sem Pyodide, pula
  assert.equal(await conferir("a.py", "def (", { conferirPython: async () => "erro na linha 1" }), "erro na linha 1");
});

// Conversa falsa: responde conforme o que o prompt pede.
function modelo({ calcRuim = false } = {}) {
  const chamadas = [];
  let calcs = 0;
  const conversa = async (m) => {
    const ultimo = m.at(-1).content;
    chamadas.push(ultimo);
    if (ultimo.includes("Liste os arquivos")) return "calc.js: funções de soma\ncalc.test.js: testes da soma";
    if (ultimo.includes("Escreva o arquivo calc.test.js")) return cerca("const test = require('node:test');\nconst a = require('node:assert');\nconst { soma } = require('./calc');\ntest('soma', () => a.equal(soma(2, 3), 5));");
    if (ultimo.includes("Escreva o arquivo calc.js") || ultimo.includes("problema")) return cerca(++calcs === 1 && calcRuim ? "function soma(a, b { return a + b }" : "exports.soma = (a, b) => a - b;");
    if (ultimo.includes("Corrija o arquivo calc.js")) return cerca("exports.soma = (a, b) => a + b;");
    if (ultimo.includes("Corrija o arquivo calc.test.js")) return cerca("const t = 1;");
    throw new Error("pedido inesperado: " + ultimo.slice(0, 80));
  };
  return { conversa, chamadas };
}

test("criar: planeja, escreve, reenvia o erro de sintaxe, roda os testes e repara o código", async () => {
  const { conversa, chamadas } = modelo({ calcRuim: true });
  const estados = [];
  const rodadas = [];
  const rodar = async (linguagem, arquivos) => {
    rodadas.push(linguagem);
    const ok = arquivos["calc.js"].includes("a + b");
    return { ok, estourou: false, saida: ok ? "1 passaram, 0 falharam" : "✖ soma — esperava 5, veio -1\n0 passaram, 1 falharam" };
  };
  const r = await criar("Calc", "uma calculadora", conversa, { sistema: "SIS", status: (t) => estados.push(t), rodar });
  assert.deepEqual(Object.keys(r.arquivos).sort(), ["README.md", "calc.js", "calc.test.js"]);
  assert.equal(r.arquivos["calc.js"], "exports.soma = (a, b) => a + b;");
  assert.deepEqual(rodadas, ["javascript", "javascript"]);  // falhou, reparou, passou
  assert.deepEqual([r.avisos, r.testes, r.linguagem, r.principal], [[], "", "javascript", "calc.js"]);
  assert.ok(chamadas.some((c) => c.includes("erro de sintaxe JavaScript")));  // o erro voltou ao modelo
  assert.match(r.arquivos["README.md"], /^# Calc\n\numa calculadora/);
  assert.ok(estados[0].startsWith("Planejando") && estados.some((e) => e.includes("pedindo uma correção")));
});

test("criar: se os testes continuam falhando depois de 2 rodadas, vira aviso (nada some)", async () => {
  const { conversa } = modelo();
  const r = await criar("Calc", "calc", conversa, { rodar: async () => ({ ok: false, estourou: false, saida: "0 passaram, 1 falharam" }) });
  assert.match(r.avisos.at(-1), /testes gerados ainda falham/);
  assert.ok(r.arquivos["calc.js"]);
});

test("criar: sem plano utilizável, erra com mensagem clara; sem sandbox, não testa", async () => {
  await assert.rejects(criar("X", "y", async () => "não sei"), /não conseguiu planejar/);
  const { conversa } = modelo();
  const r = await criar("Calc", "calc", conversa);
  assert.equal(r.testes, "");
});

test("leiame lista os arquivos", () => assert.match(leiame("N", "D", [["a.js", "faz a"]]), /- `a\.js`: faz a/));
