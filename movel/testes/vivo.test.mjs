// Memória viva: parser estrito de [[SAVE:...]], nada é gravado sozinho, cartão com Guardar/Descartar, diferença e origem.
import assert from "node:assert/strict";
import test from "node:test";
import { mostrarCartao } from "../js/cartao-memoria.js";
import { sistema, LIMITE_TOTAL } from "../js/contexto.js";
import { Memoria } from "../js/memoria.js";
import { AREAS_VIVAS, diferenca, extrair, guardarAprovada, semProposta } from "../js/memoria-viva.js";

test("extrai a proposta e remove a linha do texto", () => {
  const r = extrair("Anotado!\n[[SAVE:metas|Correr 5 km|Quero correr 5 km até dezembro]]");
  assert.equal(r.texto, "Anotado!");
  assert.deepEqual(r.propostas, [{ area: "metas", titulo: "Correr 5 km", texto: "Quero correr 5 km até dezembro" }]);
});

test("parser estrito: área fora da lista, título com / ou .., tamanhos e formato quebrado viram nada (mas somem do texto)", () => {
  for (const ruim of [
    "[[SAVE:hacker|x|y]]", "[[SAVE:METAS|x|y]]", "[[SAVE:metas|a/b|texto]]", "[[SAVE:metas|a\\b|texto]]", "[[SAVE:metas|..|texto]]",
    "[[SAVE:metas|a..b|texto]]", `[[SAVE:metas|${"t".repeat(61)}|texto]]`, `[[SAVE:metas|titulo|${"x".repeat(501)}]]`, "[[SAVE:metas||texto]]", "[[SAVE:metas|titulo|]]",
    "[[SAVE:metas|titulo|texto com [[ dentro]]",
  ]) {
    const r = extrair("Resposta. " + ruim);
    assert.deepEqual(r.propostas, [], ruim);
    assert.ok(!r.texto.includes("SAVE"), ruim);
  }
  assert.deepEqual(Object.keys(AREAS_VIVAS), ["metas", "trabalho", "projetos", "financas", "aprendizado", "saude", "relacoes", "meta"]);
});

test("no máximo 2 propostas por resposta; streaming esconde o pedaço que ainda está chegando", () => {
  const m = "[[SAVE:meta|a|1]] [[SAVE:meta|b|2]] [[SAVE:meta|c|3]]";
  assert.equal(extrair(m).propostas.length, 2);
  assert.equal(semProposta("Olá mundo\n[[SAVE:metas|Tít"), "Olá mundo");
  assert.equal(semProposta("Olá [[SAVE:metas|a|b]] fim"), "Olá  fim");
});

test("nada é gravado sozinho; só guardarAprovada grava, em <Área>/<título>, com a origem marcada", async () => {
  const mem = new Memoria();
  const { propostas } = extrair("ok [[SAVE:saude|Dormir cedo|Dormir às 22h]]");
  assert.deepEqual(await mem.listar(), []);
  const ref = await guardarAprovada(mem, propostas[0], false);
  assert.equal(ref, "Saúde/Dormir cedo");
  const nota = await mem.ler(ref);
  assert.ok(nota.corpo.startsWith("Dormir às 22h"));
  assert.match(nota.corpo, /Origem: sugerida pela Jarvis .* a partir da conversa; aprovada por você/);
  assert.equal(nota.tipo, "viva");
  const web = await guardarAprovada(mem, { area: "financas", titulo: "Preço", texto: "BTC alto" }, true);
  assert.match((await mem.ler(web)).corpo, /site, notícia ou pesquisa \(não verificados\)/);
});

test("diferença só aparece quando existe nota com o mesmo título e o texto mudou", async () => {
  const mem = new Memoria();
  const p = { area: "metas", titulo: "Meta", texto: "novo" };
  assert.equal(diferenca(null, p), null);
  await guardarAprovada(mem, { ...p, texto: "antigo" }, false);
  assert.deepEqual(diferenca(await mem.ler("Metas/Meta"), p), { antes: "antigo", depois: "novo" });
  assert.equal(diferenca(await mem.ler("Metas/Meta"), { ...p, texto: "antigo" }), null);
});

// DOM mínimo para testar o cartão (só o que ele usa).
function domFalso() {
  const no = (tag) => ({
    tag, filhos: [], texto: "", ouvintes: {}, atributos: {}, disabled: false,
    set textContent(v) { this.texto = v; this.filhos = []; }, get textContent() { return this.texto + this.filhos.map((f) => f.textContent).join(""); },
    append(...c) { this.filhos.push(...c); }, appendChild(c) { this.filhos.push(c); }, replaceChildren(...c) { this.filhos = c; this.texto = ""; },
    setAttribute(k, v) { this.atributos[k] = v; }, addEventListener(n, f) { this.ouvintes[n] = f; }, clique() { return this.ouvintes.click(); },
  });
  globalThis.document = { createElement: no };
  return no("div");
}
const acha = (n, rotulo) => (n.tag === "button" && n.textContent === rotulo ? n : n.filhos.map((f) => acha(f, rotulo)).find(Boolean));

test("cartão: mostra diff e aviso de origem; Descartar não grava; Guardar grava; texto malicioso vira só texto", async () => {
  const mem = new Memoria(), onde = domFalso();
  await guardarAprovada(mem, { area: "projetos", titulo: "App", texto: "versão 1" }, false);
  const proposta = { area: "projetos", titulo: "App", texto: "versão 2 <img src=x onerror=alert(1)>" };
  const c1 = await mostrarCartao({ proposta, memoria: mem, dadosExternos: true, onde });
  const texto = c1.textContent;
  assert.match(texto, /Guardar esta lembrança\?/);
  assert.match(texto, /Antes:\nversão 1/);
  assert.match(texto, /Depois:\nversão 2 <img/);
  assert.match(texto, /dados de site, notícia ou pesquisa/);
  await acha(c1, "Descartar").clique();
  assert.equal((await mem.ler("Projetos/App")).corpo.split("\n")[0], "versão 1");
  const c2 = await mostrarCartao({ proposta, memoria: mem, dadosExternos: false, onde });
  await acha(c2, "Guardar").clique();
  assert.match((await mem.ler("Projetos/App")).corpo, /^versão 2 <img/);
  assert.match(c2.textContent, /Guardado em "Projetos\/App"/);
});

test("o prompt do sistema ensina o [[SAVE]] e continua dentro do limite", async () => {
  const saber = { linguagem: () => null, padrao: () => null, algoritmo: () => null, citadosTopicos: () => [], constructor: { citados: () => [] }, tecnologias: [] };
  const s = await sistema({ saber, memoria: new Memoria(), pergunta: "oi", dados: "x".repeat(900) });
  assert.match(s, /\[\[SAVE:area\|titulo curto\|texto/);
  assert.ok(s.length <= LIMITE_TOTAL, `${s.length}`);
});
