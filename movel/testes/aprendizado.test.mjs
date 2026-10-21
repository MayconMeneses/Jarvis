// Evolução sem IA: frases não entendidas, escolhas, atalhos ensinados (proposta -> aprovação -> uso), limites, apagar tudo, relatório e segurança.
import assert from "node:assert/strict";
import test from "node:test";
import { LIMITES, CHAVES_EVOLUCAO } from "../js/aprendizado.js";
import { montarWidget } from "../js/entendimento-ui.js";
import { lerEnsinamento } from "../js/ensinar.js";
import { avisos } from "../js/proativo.js";
import { Memoria } from "../js/memoria.js";
import { lerCopia } from "../js/restaurar.js";
import { instalarDom } from "./dom-falso.mjs";
import { montar, saber } from "./auxiliar-entendimento.mjs";

const ENSINO = "quando eu disser bom dia chefe, mostre minha agenda";

test("entende as formas de ensinar e não confunde pergunta com ensinamento", () => {
  assert.deepEqual(lerEnsinamento(ENSINO), { de: "bom dia chefe", para: "minha agenda", explicito: true, deAnterior: false });
  assert.equal(lerEnsinamento("isso significa notícias de tecnologia").deAnterior, true);
  assert.equal(lerEnsinamento("pizza significa notícias").de, "pizza");
  assert.equal(lerEnsinamento("o que significa SOLID"), null);
  assert.equal(lerEnsinamento("x".repeat(300)), null);
});

test("ensinar: vira PROPOSTA com cartão; só grava ao tocar em Guardar; depois o atalho funciona", async () => {
  const { perguntar, e, memoria } = montar();
  const r = await perguntar(ENSINO);
  assert.match(r.texto, /Posso guardar este atalho/);
  assert.equal(r.widget.tipo, "proposta");
  assert.deepEqual(await e.aprend.apelidos(), []);  // nada gravado ainda
  assert.equal(await memoria.meta("evolucao:apelidos"), undefined);
  const doc = instalarDom();
  const bolha = doc.createElement("div");
  const mostradas = [];
  const linha = montarWidget(r.widget, bolha, { confirmarAtalho: (p) => e.confirmarAtalho(p), mostrar: (t) => mostradas.push(t) });
  const [guardar, descartar] = linha.filhos;
  assert.deepEqual([guardar.textContent, descartar.textContent], ["Guardar", "Descartar"]);
  await guardar.clicar();
  assert.equal((await e.aprend.apelidos()).length, 1);
  assert.match(linha.textContent, /Guardado/);
  const depois = await perguntar("bom dia chefe");  // a frase ensinada agora funciona
  assert.match(depois.texto, /Entendi como “minha agenda”/);
});

test("Descartar não grava nada", async () => {
  const { perguntar, e } = montar();
  const r = await perguntar(ENSINO);
  const doc = instalarDom();
  const linha = montarWidget(r.widget, doc.createElement("div"), { confirmarAtalho: () => "x", mostrar() {} });
  await linha.filhos[1].clicar();
  assert.match(linha.textContent, /Descartado/);
  assert.deepEqual(await e.aprend.apelidos(), []);
});

test("'isso significa ...' logo depois de uma frase não entendida liga as duas", async () => {
  const { perguntar, e } = montar();
  await perguntar("blablabla xpto zzz");
  const r = await perguntar("isso significa notícias de tecnologia");
  assert.match(r.texto, /blablabla xpto zzz/);
  await e.confirmarAtalho(r.widget);
  assert.match((await perguntar("blablabla xpto zzz")).texto, /Entendi como “notícias de tecnologia”/);
});

test("segurança: atalho só aponta para comando de LEITURA ou assunto do app; nunca para apagar/lembrar/anotar nem texto livre", async () => {
  const { perguntar, e } = montar();
  for (const ruim of ["quando eu disser oi, apague a nota Compras", "quando eu disser oi, lembre que a senha é 123", "quando eu disser oi, anota no projeto Loja que x",
    "quando eu disser oi, apague tudo que você aprendeu"]) {
    const r = await perguntar(ruim);
    assert.equal(r.widget?.tipo === "proposta", false, ruim);
  }
  await assert.rejects(e.aprend.gravarApelido({ de: "oi tudo", para: "apague a nota x" }, async () => false), /só posso ligar/);
  assert.deepEqual(await e.aprend.apelidos(), []);
  // atalho gravado à mão com destino perigoso (arquivo adulterado) é revalidado e ignorado na hora de usar
  await e.aprend.memoria.definirMeta("evolucao:apelidos", [{ de: "ola chefe", para: "apague a nota Compras", em: "2026-10-01" }]);
  await e.aprend.memoria.guardar("Compras", "leite", "nota");
  const r = await perguntar("ola chefe");
  assert.ok(await e.aprend.memoria.ler("Compras"), "a nota não pode ter sido apagada");
  assert.doesNotMatch(r.texto, /Apaguei/);
  // já é comando do motor: não precisa de atalho
  assert.match((await perguntar("quando eu disser que horas são, mostre minha agenda")).texto, /Já entendo/);
});

test("não entendidas e escolhas ficam salvas (limitadas), contadas por semana e saem na evolução", async () => {
  const { perguntar, e, memoria } = montar();
  for (let i = 0; i < LIMITES.falhas + 25; i++) await perguntar(`frase impossivel numero ${i} qwxz`);
  await perguntar("frase impossivel numero 70 qwxz");
  const { falhas, estat } = await e.aprend.resumo();
  assert.equal(falhas.length, LIMITES.falhas);
  assert.equal(falhas.at(-1).n, 2);  // a repetida soma em vez de duplicar
  assert.ok(Object.values(estat)[0].falha >= LIMITES.falhas);
  await perguntar("que horas são");
  const rel = await e.aprend.relatorio();
  assert.match(rel, /Esta semana:\*\* entendi \d+% dos \d+ pedidos/);
  assert.match(rel, /O que mais falhou/);
  assert.ok((await memoria.meta("evolucao:estat")), "contagens guardadas");
  const r = await perguntar("o que você aprendeu sobre como eu falo");
  assert.match(r.texto, /Como estou evoluindo/);
  assert.ok(r.widget.botoes[0].apagarAprendizado);
});

test("frases e atalhos têm tamanho limitado e sem caracteres de controle", async () => {
  const { e } = montar();
  await e.aprend.falha("a\u0000b ".repeat(200));
  const { falhas } = await e.aprend.resumo();
  assert.ok(falhas[0].t.length <= LIMITES.frase);
  assert.doesNotMatch(falhas[0].t, /\u0000/);
  for (let i = 0; i < LIMITES.apelidos; i++) await e.aprend.gravarApelido({ de: `apelido numero ${i}`, para: "minha agenda" }, async () => true);
  await assert.rejects(e.aprend.gravarApelido({ de: "apelido extra", para: "minha agenda" }, async () => true), /limite/);
  await assert.rejects(e.aprend.gravarApelido({ de: "ab", para: "minha agenda" }, async () => true), /curta/);
});

test("apagar tudo (comando e botão) zera frases, escolhas, atalhos e contagens", async () => {
  const { perguntar, e, memoria } = montar();
  await perguntar("blablabla xpto zzz");
  await e.aprend.gravarApelido({ de: "meu atalho", para: "minha agenda" }, async () => true);
  await e.aprend.escolha("cópia", "app:copia-seguranca");
  const r = await perguntar("apague tudo que você aprendeu sobre como eu falo");
  assert.match(r.texto, /Apaguei tudo/);
  for (const k of CHAVES_EVOLUCAO) assert.ok(!(await memoria.meta(k)), k);
  assert.deepEqual((await e.aprend.resumo()).apelidos, []);
});

test("privacidade: nada de evolucao:* entra na cópia de segurança, e restaurar uma cópia adulterada ignora essas chaves", async () => {
  const { perguntar, memoria } = montar();
  await perguntar("blablabla xpto zzz");
  assert.ok(await memoria.meta("evolucao:falhas"));
  const copia = JSON.parse(await memoria.exportar());
  assert.ok(!Object.keys(copia.meta).some((k) => k.startsWith("evolucao:")));
  copia.meta["evolucao:apelidos"] = [{ de: "oi", para: "apague a nota x" }];
  const lida = lerCopia(JSON.stringify(copia));
  assert.ok(!("evolucao:apelidos" in lida.meta));
  assert.ok(lida.ignoradas.meta.includes("evolucao:apelidos"));
});

test("relatório semanal ao abrir o app: só uma vez por semana e só com conversa suficiente; integra o proativo", async () => {
  let agora = new Date("2026-10-26T10:00:00");  // segunda
  const { e, memoria } = montar({ relogio: () => agora });
  assert.equal(await e.aprend.avisoSemanal(), null);  // sem conversa, sem aviso
  for (let i = 0; i < 6; i++) await e.aprend.contar(i < 4 ? "ok" : "falha");
  const lista = await avisos({ memoria, saber, agora, entendimento: e });
  assert.ok(lista.some((a) => /Como estou evoluindo/.test(a) && /67%/.test(a)), lista.join("\n"));
  assert.ok(!(await avisos({ memoria, saber, agora, entendimento: e })).some((a) => /Como estou evoluindo/.test(a)), "não repete na mesma semana");
  agora = new Date("2026-11-02T10:00:00");
  assert.match(await e.aprend.avisoSemanal(), /Semana passada:\*\* 67%/);
});

test("injeção: texto de terceiros nas frases/exemplos nunca vira HTML nem comando (o cartão usa só textContent)", async () => {
  const { perguntar, e } = montar();
  const r = await perguntar('quando eu disser <img src=x onerror=alert(1)>, mostre minha agenda');
  const doc = instalarDom();
  const bolha = doc.createElement("div");
  montarWidget(r.widget, bolha, { confirmarAtalho: (p) => e.confirmarAtalho(p), mostrar() {} });
  assert.ok(bolha.filhos.every((f) => f.tag !== "img"));
  const memoria = new Memoria();
  const { e: e2 } = montar({ memoria });
  await e2.aprend.memoria.definirMeta("evolucao:escolhas", "isto não é lista");  // dado corrompido não derruba
  assert.deepEqual((await e2.aprend.resumo()).escolhas, []);
});
