// Testes do núcleo do app do celular (rodam com `node --test movel/testes`).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { avisos } from "../js/proativo.js";
import * as design from "../js/design.js";
import * as gerar from "../js/gerar.js";
import { Memoria } from "../js/memoria.js";
import { Motor } from "../js/motor.js";
import { Saber } from "../js/saber.js";
import * as contexto from "../js/contexto.js";
import { semanaIso } from "../js/util.js";

const dados = JSON.parse(readFileSync(new URL("../dados/saber.json", import.meta.url), "utf8"));
const saber = new Saber(dados);
const relogio = (iso) => () => new Date(iso);
const motor = (iso = "2026-10-19T10:30:00", buscar) => new Motor({ saber, memoria: new Memoria(undefined, relogio(iso)), buscar, agora: relogio(iso) });

test("memória guarda, busca sem acento, apaga e faz cópia de segurança", async () => {
  const m = new Memoria(undefined, relogio("2026-10-19T10:00:00Z"));
  await m.guardar("Lembranças/café", "Eu gosto de café sem açúcar", "lembranca");
  await m.guardar("Projetos/Loja", "Loja virtual em FastAPI", "projeto", "Loja");
  assert.equal((await m.buscar("cafe acucar"))[0].ref, "Lembranças/café");
  assert.equal((await m.buscar("loja"))[0].titulo, "Loja");
  assert.deepEqual(await m.buscar("xadrez"), []);
  await m.diario("abriu o app");
  assert.match((await m.ler("Diário/2026-10-19")).corpo, /abriu o app/);
  const copia = await m.exportar();
  const nova = new Memoria();
  assert.equal(await nova.importar(copia), 3);
  assert.equal((await nova.ler("Projetos/Loja")).corpo, "Loja virtual em FastAPI");
  await assert.rejects(() => nova.importar('{"formato":"outro"}'), /inválido/);
  await m.apagar("Projetos/Loja");
  assert.equal(await m.ler("Projetos/Loja"), null);
});

test("conhecimento curado vem inteiro do PC e é encontrado como lá", () => {
  assert.ok(saber.topicos.length >= 59 && saber.padroes.length >= 8 && saber.estruturas.length >= 9 && saber.algoritmos.length >= 15 && saber.tecnologias.length > 10);
  assert.equal(saber.topico("SOLID").id, "solid");
  assert.equal(saber.topico("recursão").id, "recursao");
  assert.equal(saber.padrao("quero desfazer e refazer").id, "command");
  assert.equal(saber.algoritmo("busca binária em java").id, "busca_binaria");
  assert.equal(saber.algoritmo("como implementar uma trie").id, "trie");
  assert.equal(saber.algoritmo("árvore binária de busca").id, "arvore_busca");
  assert.equal(saber.citadosTopicos("arquitetura hexagonal")[0].id, "arquitetura-hexagonal");
  assert.equal(saber.linguagem("quicksort em C#"), "csharp");
  assert.match(saber.explicar("SOLID"), /Como aplicar/);
  assert.match(saber.explicar("padrão Observer em javascript", "javascript"), /```javascript/);
  assert.equal(saber.explicar("receita de bolo"), null);
});

test("contraste, paleta e escala batem com os valores de referência do PC", () => {
  assert.ok(Math.abs(design.contraste("#000", "#fff") - 21) < 1e-9);
  assert.ok(Math.abs(design.contraste("#767676", "#ffffff") - 4.54) < 0.01);
  assert.ok(design.contraste("#777777", "#ffffff") < 4.5);
  assert.throws(() => design.paraRgb("azul"), /cor inválida/);
  assert.deepEqual(Object.keys(design.paleta("#3b82f6")), ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900"]);
  assert.ok(design.luminancia(design.paleta("#3b82f6")["50"]) > design.luminancia(design.paleta("#3b82f6")["900"]));
  assert.deepEqual(design.escalaTipografica()[2], ["base", 16]);
  assert.deepEqual(design.escalaEspacamento().slice(0, 3), [4, 8, 12]);
  const css = design.tokensCss("#3b82f6");
  assert.equal(css.split("{").length, css.split("}").length);
});

test("geradores produzem texto válido e recusam nomes perigosos", () => {
  assert.match(gerar.esquemaSql("clientes", { nome: "texto", idade: "inteiro" }), /CREATE TABLE clientes[\s\S]*idade INTEGER/);
  assert.throws(() => gerar.esquemaSql("1; DROP TABLE x"), /nome inválido/);
  assert.match(gerar.adr("Usar SQLite", "ctx", "dec", "", 3, new Date("2026-10-19T12:00:00")), /^# ADR 0003: Usar SQLite/);
  assert.match(gerar.workflowCi("js"), /setup-node/);
  assert.throws(() => gerar.workflowCi("cobol"), /sem modelo/);
  assert.match(gerar.dockerfile("node", 3000), /USER node[\s\S]*3000/);
  assert.match(gerar.openapi("Loja", ["clientes"]), /\/clientes\/\{id\}/);
});

test("o motor entende pedidos, guarda memória e agenda lembretes", async () => {
  const m = motor();
  const intencoes = { "que horas são?": "hora", "que dia é hoje": "data", "lembre que eu gosto de café": "lembrar", "me lembre de pagar a luz amanhã": "lembrete",
    "o que você sabe sobre mim": "memoria", "contraste #767676 sobre #ffffff": "ux", "crie uma tabela clientes com nome texto": "gerar",
    "compare React e Vue": "comparar", "mostre o padrão Observer em JavaScript": "padrao", "explique SOLID": "explicar", "aprenda sobre quasares": "aprender",
    "conte uma piada": null };
  for (const [texto, esperado] of Object.entries(intencoes)) assert.equal(m.classificar(texto), esperado, texto);
  assert.match(await m.responder("que horas são?"), /10:30/);
  assert.match(await m.responder("que dia é hoje"), /segunda-feira, 19 de outubro de 2026/);
  assert.match(await m.responder("lembre que eu gosto de café sem açúcar"), /Guardei/);
  assert.match(await m.responder("o que você sabe sobre café"), /café sem açúcar/);
  assert.match(await m.responder("me lembre de pagar a luz amanhã"), /20 de outubro/);
  assert.equal((await m.memoria.listar("Lembretes/")).length, 1);
  assert.match(await m.responder("apague a nota café"), /Apaguei/);
  assert.match(await m.responder("contraste #999 sobre #fff"), /FALHA/);
  assert.match(await m.responder("paleta a partir de #3b82f6"), /700/);
  assert.match(await m.responder("tokens css para #3b82f6"), /--cor-500/);
  assert.match(await m.responder("crie uma tabela clientes com nome texto, idade inteiro"), /CREATE TABLE clientes/);
  assert.match(await m.responder("compare monólito e microsserviços"), /×/);
  assert.match(await m.responder("como fazer fatorial em go"), /```go/);
  assert.match(await m.fallback("receita de bolo"), /modo independente/);
});

test("aprender guarda a nota da Wikipédia (simulada) e passa a consultá-la", async () => {
  const buscar = async (url) => ({
    ok: true,
    json: async () => (url.includes("list=search") ? { query: { search: [{ title: "Quasar", snippet: "objeto <b>muito</b> brilhante" }] } }
      : { extract: "Quasares são núcleos galácticos ativos.", content_urls: { desktop: { page: "https://pt.wikipedia.org/wiki/Quasar" } } }),
  });
  const m = motor("2026-10-19T10:30:00", buscar);
  const resposta = await m.responder("aprenda sobre quasares");
  assert.match(resposta, /não foi verificado/);
  assert.match((await m.memoria.ler("Aprendizado/quasares")).corpo, /não verificado/);
  assert.match(await m.responder("explique quasares"), /Do que aprendi na internet[\s\S]*núcleos galácticos/);
  const semRede = motor("2026-10-19T10:30:00", async () => { throw new Error("sem rede"); });
  assert.match(await semRede.responder("pesquise sobre quasares"), /sem internet/);
});

test("o prompt do modelo tem persona, conhecimento, memória e dados reais, dentro do limite", async () => {
  const memoria = new Memoria();
  await memoria.guardar("Lembranças/café", "gosto de café", "lembranca");
  const texto = await contexto.sistema({ saber, memoria, pergunta: "explique o padrão Observer e SOLID, quero café", nome: "Maycon", dados: "Agora são 10:30." });
  assert.match(texto, /Jarvis/); assert.match(texto, /Dados reais[\s\S]*10:30/); assert.match(texto, /Conhecimento confiável/); assert.match(texto, /café/);
  assert.ok(texto.length <= contexto.LIMITE_TOTAL + 1);
  const longo = Array.from({ length: 10 }, () => ({ role: "user", content: "x".repeat(5000) }));
  assert.equal(contexto.historico(longo).length, contexto.MAX_HISTORICO);
});

test("avisos ao abrir: bom dia, lembrete do dia, tópico do dia e treino, uma vez cada", async () => {
  const memoria = new Memoria();
  const agora = new Date("2026-10-19T10:00:00");  // segunda-feira
  await memoria.guardar("Lembretes/2026-10-19 pagar a luz", "Para: 2026-10-19\npagar a luz", "lembrete");
  const primeiro = await avisos({ memoria, saber, agora, nome: "Maycon" });
  assert.ok(primeiro.some((a) => a.startsWith("Bom dia, Maycon")) && primeiro.some((a) => a.includes("pagar a luz")));
  assert.ok(primeiro.some((a) => a.startsWith("💡")) && primeiro.some((a) => a.startsWith("📚")));
  assert.deepEqual(await avisos({ memoria, saber, agora, nome: "Maycon" }), []);
  assert.deepEqual(semanaIso(new Date("2026-10-19T10:00:00")), [2026, 43]);
});
