// PC pareado (somente leitura): fetch falso, nenhum PC real. Pareamento, timeout, offline com cópia datada, 401 e comandos de chat.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { Memoria } from "../js/memoria.js";
import { Motor } from "../js/motor.js";
import { textoAgenda, textoEmails } from "../js/motor-pc.js";
import { OFFLINE, PcPareado, normalizarUrl } from "../js/pc-pareado.js";
import { Saber } from "../js/saber.js";

const saber = new Saber(JSON.parse(readFileSync(new URL("../dados/saber.json", import.meta.url), "utf8")));
const json = (corpo, status = 200) => ({ ok: status < 400, status, json: async () => corpo });
const AGENDA = { sem_agendas: false, avisos: [], hoje: [{ titulo: "Dentista", inicio: "2026-10-20T14:00:00-03:00", fim: "2026-10-20T15:00:00-03:00", dia_inteiro: false, local: "Centro", suspeito: false }],
  semana: [], proximo: { titulo: "Dentista", inicio: "2026-10-20T14:00:00-03:00", fim: "2026-10-20T15:00:00-03:00", dia_inteiro: false, local: "", suspeito: false } };
const EMAILS = { sem_contas: false, contagem: { acao: 1, info: 0, ruido: 2, suspeito: 1 }, baldes: { acao: [{ de: "Ana", assunto: "Prazo amanhã", resumo: "" }], info: [], ruido: [] } };

function cenario(rotas = {}) {
  const chamadas = [];
  const memoria = new Memoria();
  const buscar = async (url, op = {}) => {
    chamadas.push({ url, op });
    const rota = new URL(url).pathname;
    if (rotas.cair) throw new TypeError("Failed to fetch");
    return rotas[rota] ? rotas[rota](op) : json({}, 404);
  };
  const pc = new PcPareado({ armazem: memoria.armazem, buscar, agora: () => new Date("2026-10-20T12:00:00Z"), timeoutMs: 50 });
  const motor = new Motor({ saber, memoria, buscar: async () => json({}), agora: () => new Date("2026-10-20T09:00:00") });
  motor.pc = pc;
  return { pc, motor, memoria, chamadas, rotas };
}

test("só aceita endereço https e guarda só a origem", () => {
  assert.equal(normalizarUrl(" https://pc.tail.ts.net:8765/qualquer?x=1 "), "https://pc.tail.ts.net:8765");
  for (const ruim of ["http://192.168.0.2:8765", "pc.local", "ftp://x", "https://u:p@x.com", ""]) assert.throws(() => normalizarUrl(ruim), ruim);
});

test("parear troca o código pelo token, guarda no IndexedDB (armazém) e nunca na cópia de segurança", async () => {
  const c = cenario({ "/api/parear": () => json({ token: "TOKEN-SECRETO" }) });
  await assert.rejects(c.pc.parear("https://pc.ts.net:8765", "12ab"), /6 dígitos/);
  await c.pc.parear("https://pc.ts.net:8765/x", "123456");
  const post = c.chamadas[0];
  assert.equal(post.url, "https://pc.ts.net:8765/api/parear");
  assert.equal(JSON.parse(post.op.body).codigo, "123456");
  assert.equal(post.op.credentials, "omit");
  assert.equal((await c.pc.pareamento()).token, "TOKEN-SECRETO");
  assert.ok(!(await c.memoria.exportar()).includes("TOKEN-SECRETO"));
  await c.pc.desparear();
  assert.equal(await c.pc.pareado(), false);
});

test("código errado, PC desligado e resposta estranha dão mensagens amigáveis", async () => {
  await assert.rejects(cenario({ "/api/parear": () => json({}, 403) }).pc.parear("https://a.ts.net", "123456"), /inválido, vencido/);
  await assert.rejects(cenario({ cair: true }).pc.parear("https://a.ts.net", "123456"), new RegExp(OFFLINE.replace(".", "\.")));
  await assert.rejects(cenario({ "/api/parear": () => json({ token: 5 }) }).pc.parear("https://a.ts.net", "123456"), /inesperada/);
});

async function pareada(rotas) {
  const c = cenario({ "/api/parear": () => json({ token: "T" }), ...rotas });
  await c.pc.parear("https://pc.ts.net:8765", "123456");
  return c;
}

test("obter manda o Bearer, guarda cópia datada e, offline, devolve a cópia marcada", async () => {
  const c = await pareada({ "/api/agenda": () => json(AGENDA) });
  const r = await c.pc.obter("agenda");
  assert.ok(r.ok && !r.doCache);
  assert.equal(c.chamadas.at(-1).op.headers.Authorization, "Bearer T");
  c.rotas.cair = true;
  const off = await c.pc.obter("agenda");
  assert.ok(off.ok && off.doCache && off.quando === "2026-10-20T12:00:00.000Z" && off.erro === OFFLINE);
  assert.deepEqual((await c.pc.obter("emails")), { ok: false, erro: OFFLINE });  // sem cópia: só o aviso
});

test("tempo esgotado vira offline; 401 pede novo pareamento", async () => {
  const c = await pareada({ "/api/emails": (op) => new Promise((_, rej) => op.signal.addEventListener("abort", () => rej(new Error("abort")))) });
  assert.equal((await c.pc.obter("emails")).erro, OFFLINE);
  const d = await pareada({ "/api/agenda": () => json({}, 401) });
  assert.match((await d.pc.obter("agenda")).erro, /Pareie de novo/);
});

test("sem PC pareado: comandos explicam, e 'bom dia' vira só uma saudação local (sem rede)", async () => {
  const c = cenario();
  for (const t of ["minha agenda", "próximo compromisso", "meus e-mails"]) assert.match(await c.motor.responder(t), /precisa do PC pareado/);
  assert.match(await c.motor.responder("bom dia"), /^(Bom dia|Boa tarde|Boa noite)!.*Em que posso ajudar/);  // saudação local: nunca silêncio
  assert.equal(c.chamadas.length, 0);  // nenhum pedido de rede
  assert.match(await c.motor.responder("que horas são"), /Agora são/);  // o resto do motor segue igual
});

test("com PC pareado: agenda, próximo, e-mails e bom dia; offline mostra a cópia com a hora", async () => {
  const c = await pareada({ "/api/agenda": () => json(AGENDA), "/api/emails": () => json(EMAILS), "/api/briefing": () => json({ texto: "Bom dia, Maycon!\nNenhum compromisso hoje." }) });
  assert.match(await c.motor.responder("Minha agenda"), /Hoje \(1\)[\s\S]*Dentista \(Centro\)/);
  assert.match(await c.motor.responder("qual o próximo compromisso?"), /Próximo compromisso[\s\S]*Dentista/);
  const em = await c.motor.responder("meus e-mails");
  assert.match(em, /1 de ação[\s\S]*1 suspeitos \(omitidos\)[\s\S]*Ana: Prazo amanhã/);
  assert.match(await c.motor.responder("bom dia"), /^Bom dia, Maycon!/);
  c.rotas.cair = true;
  assert.match(await c.motor.responder("minha agenda"), /Cópia de .*PC desligado ou fora da rede/);
  assert.match(await c.motor.responder("bom dia"), /Cópia de/);
});

test("textos de terceiros não são interpretados: só texto puro", () => {
  const t = textoAgenda({ dados: { ...AGENDA, hoje: [{ ...AGENDA.hoje[0], titulo: "<img src=x onerror=alert(1)>" }] } });
  assert.ok(t.includes("<img src=x onerror=alert(1)>"));  // chega como texto; md.js e textContent nunca criam HTML
  assert.match(textoEmails({ dados: { ...EMAILS, sem_contas: true } }), /ainda não tem conta/);
});

test("resposta hostil do PC: formato errado cai no cache/erro, texto vira só texto limpo e limitado", async () => {
  const c = cenario({ "/api/parear": () => json({ token: "tok123" }), "/api/agenda": () => json(AGENDA) });
  await c.pc.parear("https://pc.exemplo.ts.net:8765", "123456");
  assert.equal((await c.pc.obter("agenda")).ok, true);
  for (const lixo of [null, "texto", 7, [], { hoje: null }, { sem_agendas: false, hoje: "x", semana: { a: 1 }, proximo: 5 }]) {
    c.rotas["/api/agenda"] = () => json(lixo);
    const r = await c.pc.obter("agenda");
    if (r.ok) textoAgenda(r); else assert.match(r.erro, /inesperado|PC/);
  }
  c.rotas["/api/agenda"] = () => json(null);
  const r = await c.pc.obter("agenda");   // resposta inválida: usa a última cópia boa, marcada como cópia
  assert.equal(r.ok, true); assert.equal(r.doCache, true); assert.match(r.erro, /inesperado/);
  c.rotas["/api/emails"] = () => json({ sem_contas: false, contagem: { acao: "9", info: -1, ruido: 1e99 }, baldes: { acao: [null, 3, { de: { x: 1 }, assunto: "A".repeat(5000) + "\u0007" }], info: "x", ruido: [] } });
  const e = await c.pc.obter("emails");
  assert.equal(e.ok, true);
  assert.equal(e.dados.contagem.acao, 0); assert.equal(e.dados.contagem.ruido, 1e9);
  assert.equal(e.dados.baldes.acao.length, 1); assert.equal(e.dados.baldes.acao[0].assunto.length, 300); assert.equal(e.dados.baldes.acao[0].de, "");
  assert.doesNotThrow(() => textoEmails(e));
});

test("cache corrompido no IndexedDB não derruba: vira erro", async () => {
  const c = cenario({ "/api/parear": () => json({ token: "tok123" }), cair: true });
  await c.pc.parear("https://pc.exemplo.ts.net:8765", "123456").catch(() => {});
  await c.memoria.armazem.gravar("pc:pareado", { url: "https://pc.exemplo.ts.net:8765", token: "t", desde: "x" });
  await c.memoria.armazem.gravar("pc:cache:agenda", { quando: "x", dados: "lixo" });
  const r = await c.pc.obter("agenda");
  assert.equal(r.ok, false);
});

test("token do pareamento absurdo é recusado", async () => {
  for (const token of ["x".repeat(600), "com espaço", "quebra\nlinha", ""]) {
    const c = cenario({ "/api/parear": () => json({ token }) });
    await assert.rejects(c.pc.parear("https://pc.exemplo.ts.net:8765", "123456"), /inesperada/);
    assert.equal(await c.pc.pareado(), false);
  }
});
