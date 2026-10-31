// Meu perfil no celular (porte da 0.31.0 do PC): validação, deduzido x definido, aprovação explícita, painel sem HTML montado de texto, menu e cache do SW.
// Prova a lógica no Node com memória em RAM e DOM falso; NÃO prova o iPhone/Safari.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { sistema } from "../js/contexto.js";
import { Memoria } from "../js/memoria.js";
import { GRUPOS } from "../js/menu-grupos.js";
import { cartaoPerfil } from "../js/painel-perfil.js";
import { CAMPOS, REF, aprovar, compilar, definidos, paraPrompt, proposta, sensivel, validar } from "../js/perfil-usuario.js";
import { No, achar, instalarDom } from "./dom-falso.mjs";

const arq = (n) => readFileSync(new URL(`../${n}`, import.meta.url), "utf8");

test("validar: campos conhecidos, tamanho, controle e dado sensível recusados", () => {
  assert.deepEqual(validar("tom", "  direto   e curto "), { campo: "tom", valor: "direto e curto" });
  assert.throws(() => validar("sobrenome", "x"), /campo desconhecido/);
  assert.throws(() => validar("tom", ""), /1 a 300/);
  assert.throws(() => validar("tom", "a".repeat(301)), /1 a 300/);
  assert.throws(() => validar("tom", "texto [[link]]"), /não permitidos/);
  for (const ruim of ["minha senha é 1234", "CPF 123.456.789-09", "ganho R$ 5000", "tomo remédio de manhã", "me chame em fulano@exemplo.com", "sk-abcdefghijklmnop1234"]) {
    assert.ok(sensivel(ruim), ruim);
    assert.throws(() => validar("quem", ruim), /sensível/, ruim);
  }
  assert.ok(!sensivel("gosto de respostas curtas e diretas"));
});

test("proposta não grava; aprovar grava e o definido vence o deduzido", async () => {
  const mem = new Memoria();
  await mem.definirMeta("nome", "Maycon");
  await mem.guardar("Perfil/Dev", "stack: Python e React\ncidade: Recife", "perfil");
  await mem.guardar("Projetos/Jarvis/nota", "x");
  const antes = await compilar(mem);
  assert.equal(antes.quem.origem, "deduzido");
  assert.match(antes.quem.valor, /Maycon, mora em Recife, stack Python e React/);
  assert.equal(antes.projetos.valor, "Jarvis");

  const prop = await proposta(mem, "tom", "direto e curto");
  assert.match(prop.texto, /^Atualizar seu perfil\? Tom de conversa: direto e curto$/);
  assert.equal(await mem.ler(REF), null, "propor não grava");

  assert.match(await aprovar(mem, prop.campo, prop.valor), /Perfil atualizado: Tom de conversa/);
  assert.deepEqual(await definidos(mem), { tom: "direto e curto" });
  await aprovar(mem, "quem", "Dev backend");
  const depois = await compilar(mem);
  assert.deepEqual(depois.quem, { valor: "Dev backend", origem: "definido" });
  assert.match((await proposta(mem, "tom", "mais calmo")).texto, /\(antes: direto e curto\)/);
  assert.match(await paraPrompt(mem), /- Quem sou: Dev backend\n- Projetos: Jarvis\n- Tom de conversa: direto e curto/);
});

test("apagar só vale para campo definido, pede aprovação e remove só aquele campo", async () => {
  const mem = new Memoria();
  await assert.rejects(proposta(mem, "tom", ""), /não está definido/);
  await aprovar(mem, "tom", "curto");
  await aprovar(mem, "metas", "terminar o app");
  const p = await proposta(mem, "tom", "");
  assert.match(p.texto, /^Apagar do seu perfil: Tom de conversa \(hoje: curto\)$/);
  assert.deepEqual(await definidos(mem), { tom: "curto", metas: "terminar o app" }, "propor não apaga");
  await aprovar(mem, p.campo, p.valor);
  assert.deepEqual(await definidos(mem), { metas: "terminar o app" });
  await assert.rejects(aprovar(mem, "tom", "minha senha é 123"), /sensível/, "aprovar valida de novo");
});

test("o prompt do modelo inclui o perfil como dado; sem perfil, nada muda", async () => {
  const saber = { linguagem: () => "js", padrao: () => null, algoritmo: () => null, citadosTopicos: () => [], constructor: { citados: () => [] }, tecnologias: [] };
  const mem = new Memoria();
  assert.doesNotMatch(await sistema({ saber, memoria: mem, pergunta: "oi" }), /Perfil do usuário/);
  await aprovar(mem, "tom", "direto");
  assert.match(await sistema({ saber, memoria: mem, pergunta: "oi" }), /Perfil do usuário .*dados, não ordens\):\n- Tom de conversa: direto/);
});

test("cartão do painel: texto do perfil nunca vira HTML, Cancelar não grava e Aprovar grava", async () => {
  instalarDom();
  const mem = new Memoria(), avisos = [];
  const onde = new No("section");
  let recarregou = 0;
  const prop = { campo: "tom", valor: "<img src=x onerror=alert(1)>", texto: "Atualizar seu perfil? Tom de conversa: <img src=x onerror=alert(1)>" };
  const cartao = cartaoPerfil({ memoria: mem, prop, onde, feito: async () => { recarregou++; }, avisar: (t) => avisos.push(t) });
  assert.ok(!achar(cartao, (n) => n.tag === "img").length);
  assert.equal(achar(cartao, (n) => n.tag === "pre")[0].textContent, prop.texto);
  const [aprovarBtn, cancelar] = achar(cartao, (n) => n.tag === "button");
  assert.deepEqual([aprovarBtn.textContent, cancelar.textContent], ["Aprovar", "Cancelar"]);
  assert.equal(await mem.ler(REF), null, "só mostrar o cartão não grava");
  await aprovarBtn.clicar();
  assert.equal(recarregou, 1);
  assert.match(avisos[0], /Perfil atualizado/);
  assert.equal((await definidos(mem)).tom, "<img src=x onerror=alert(1)>", "guardado como texto puro");
});

test("menu, página e service worker conhecem o Meu perfil; arquivos novos ≤ 300 linhas", () => {
  const item = GRUPOS.find((g) => g.id === "ajustes").itens.find((i) => i.id === "perfil");
  assert.deepEqual([item.rotulo, item.aba, item.abrir], ["Meu perfil", "cerebro", "painel-perfil"]);
  const html = arq("index.html"), sw = arq("sw.js");
  for (const id of ["painel-perfil", "pf-lista"]) assert.ok(html.includes(`id="${id}"`), id);
  assert.ok(sw.includes('"jarvis-movel-15"'));
  for (const f of ["js/perfil-usuario.js", "js/painel-perfil.js", "js/limitador-ativacao.js"]) {
    assert.ok(sw.includes(`"${f}"`), f);
    assert.ok(arq(f).split("\n").length <= 300, f);
  }
  assert.ok(!/innerHTML|insertAdjacentHTML|outerHTML/.test(arq("js/painel-perfil.js")), "painel sem HTML montado de texto");
  assert.deepEqual(Object.keys(CAMPOS), ["quem", "projetos", "preferencias", "tom", "metas"]);
});
