// Casca do celular (HUD): ordem das caixas, cartão central, menu agrupado, modo foco, orbe de filamentos e segurança do DOM.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { CHAVE, PADRAO, anuncio, mover, podeMover, sanear } from "../js/hud-ordem.js";
import { ABAS, lembretesDeHoje, proximaAba, resumoAgenda, resumoEmails, resumoNoticias, saudacao } from "../js/hud-briefing.js";
import { GRUPOS, itemAtual, montarMenu, proximoItem } from "../js/menu-grupos.js";
import { criarEstadoFoco } from "../js/foco-estado.js";
import { criarGrade } from "../js/hud-grade.js";
import { No } from "./dom-falso.mjs";

const arq = (n) => readFileSync(new URL(`../${n}`, import.meta.url), "utf8");

// ── Ordem das caixas ──
test("ordem: lixo, repetição e ids desconhecidos viram uma ordem válida e completa", () => {
  assert.deepEqual(sanear(null), PADRAO);
  assert.deepEqual(sanear("x"), PADRAO);
  assert.deepEqual(sanear({ 0: "clima" }), PADRAO);
  const o = sanear(["vagas", "vagas", "hack", 5, null, "clima"]);
  assert.deepEqual(o.slice(0, 2), ["vagas", "clima"]);
  assert.equal(o.length, PADRAO.length);
  assert.equal(new Set(o).size, PADRAO.length);
  assert.equal(sanear(new Array(5000).fill("clima")).length, PADRAO.length, "lista gigante não trava");
});

test("ordem: mover troca com o vizinho, respeita os limites e pula caixas escondidas", () => {
  const o = ["a", "b", "c", "d"];
  assert.deepEqual(mover(o, "b", -1), ["b", "a", "c", "d"]);
  assert.deepEqual(mover(o, "a", -1), o, "no topo não faz nada");
  assert.deepEqual(mover(o, "d", 1), o, "no fim não faz nada");
  assert.deepEqual(mover(o, "x", 1), o);
  assert.deepEqual(mover(o, "a", 1, ["a", "c", "d"]), ["c", "b", "a", "d"], "b escondida: troca com c");
  assert.equal(podeMover(o, "a", -1), false);
  assert.equal(podeMover(o, "a", 1), true);
  assert.equal(podeMover(o, "d", 1, ["a", "d"]), false);
  assert.match(anuncio("Clima", o, "b"), /posição 2 de 4/);
  assert.equal(CHAVE, "hud_ordem");
});

// ── Grade (DOM falso) ──
class Item extends No {
  constructor(tag) { super(tag); this.className = ""; }
  toggleAttribute(k, v) { this.atributos[k] = v; }
  focus() { Item.foco = this; }
  prepend(...n) { this.filhos.unshift(...n); }
  append(...n) { this.filhos = this.filhos.filter((f) => !n.includes(f)); super.append(...n); }  // como o DOM de verdade: anexar de novo MOVE
}
const memoriaFalsa = () => { const m = new Map(); return { meta: async (k) => m.get(k), definirMeta: async (k, v) => { m.set(k, v); }, m }; };
function ambiente() { globalThis.document = { hidden: false, createElement: (t) => new Item(t), addEventListener() {}, getElementById: () => null }; }

test("grade: ▲/▼ reordenam, salvam, escondidas não contam e restaurar volta ao padrão", async () => {
  ambiente();
  const mem = memoriaFalsa(), avisos = [], cont = new Item("div");
  const g = criarGrade(cont, { memoria: mem, anunciar: (t) => avisos.push(t), ids: ["a", "b", "c"] });
  for (const id of ["a", "b", "c"]) g.registrar(id, id.toUpperCase(), new Item("section"), { visivel: id !== "b" });
  await g.carregar();
  assert.deepEqual(cont.filhos.map((n) => n.dataset.id), ["a", "b", "c"]);
  const botoes = (id) => cont.filhos.find((n) => n.dataset.id === id).filhos[0].filhos.filter((n) => n.tag === "button");
  const [sobeC] = botoes("c");
  assert.equal(botoes("a")[0].disabled, true, "primeira visível não sobe");
  await sobeC.clicar();
  assert.deepEqual(cont.filhos.map((n) => n.dataset.id), g.ordem);
  assert.equal(g.ordem.indexOf("c") < g.ordem.indexOf("a"), true, "c passou por cima de a (b está escondida)");
  assert.deepEqual(mem.m.get(CHAVE), g.ordem, "ordem salva");
  assert.match(avisos.at(-1), /posição 1 de 2/);
  await g.restaurar();
  assert.deepEqual(g.ordem, ["a", "b", "c"]);
  assert.equal(mem.m.get(CHAVE), null);
});

test("grade: ordem salva corrompida não quebra e sem armazenamento segue funcionando", async () => {
  ambiente();
  const ruim = { meta: async () => { throw new Error("modo privado"); }, definirMeta: async () => { throw new Error("cheio"); } };
  const cont = new Item("div"), g = criarGrade(cont, { memoria: ruim, ids: ["a", "b"] });
  g.registrar("a", "A", new Item("p")); g.registrar("b", "B", new Item("p"));
  await g.carregar();
  assert.deepEqual(g.ordem, ["a", "b"]);
  const desce = cont.filhos[0].filhos[0].filhos.find((n) => n.tag === "button" && n.atributos["aria-label"] === "Descer A");
  await desce.clicar();
  assert.deepEqual(g.ordem, ["b", "a"], "reordena na sessão mesmo sem poder salvar");
});

// ── Cartão central ──
test("briefing: saudação, agenda, e-mails e notícias (com dados de terceiros hostis)", () => {
  assert.equal(saudacao(8, "Maycon"), "Bom dia, Maycon");
  assert.equal(saudacao(15), "Boa tarde");
  assert.equal(saudacao(23, "A"), "Boa noite, A");
  assert.match(resumoAgenda(null).titulo, /sem PC/);
  assert.equal(resumoAgenda({ sem_agendas: false, hoje: [] }).titulo, "Nada na agenda hoje");
  const a = resumoAgenda({ hoje: [{ inicio: "2026-10-21T09:00:00", titulo: "x".repeat(300) }, { dia_inteiro: true, titulo: "Feriado" }, { titulo: "z" }] });
  assert.equal(a.titulo, "3 compromissos hoje");
  assert.ok(a.linhas.length === 2 && a.linhas.every((l) => l.length < 50));
  assert.equal(resumoAgenda(null, ["Pagar luz"]).titulo, "1 lembrete hoje");
  assert.equal(resumoEmails({ contagem: { acao: 2, info: 5, ruido: 9, suspeito: 1 } }).titulo, "2 pedem ação");
  assert.equal(resumoEmails({ contagem: { acao: 0, info: 0 } }).titulo, "Caixa em dia");
  assert.match(resumoEmails({ sem_contas: true }).linhas[0], /não tem conta/);
  const n = resumoNoticias([{ titulo: "<img src=x onerror=1> " + "y".repeat(200) }, { titulo: "b" }, { titulo: "c" }]);
  assert.equal(n.titulo, "3 manchetes");
  assert.ok(n.linhas[0].length <= 40);
  assert.equal(resumoNoticias([]).titulo, "Notícias");
  assert.deepEqual(lembretesDeHoje([{ corpo: "Para: 2026-10-20\nLigar" }, { corpo: "Para: 2099-01-01\nfuturo" }, null, { corpo: 5 }], "2026-10-21"), ["Ligar"]);
});

test("briefing: setas trocam de aba em círculo", () => {
  const ids = ABAS.map((x) => x.id);
  assert.deepEqual(ids, ["agenda", "emails", "noticias"]);
  assert.equal(proximaAba("noticias", "ArrowRight"), "agenda");
  assert.equal(proximaAba("agenda", "ArrowLeft"), "noticias");
  assert.equal(proximaAba("emails", "End"), "noticias");
  assert.equal(proximaAba("emails", "x"), null);
});

// ── Menu ──
const ABAS_REAIS = ["hud", "conversa", "memoria", "cerebro", "oficina", "instagram", "documentos", "noticias"].map((id) => ({ id, rotulo: id }));
test("menu: quatro grupos com todas as abas e painéis; abas novas caem em Saber e fazer", () => {
  const g = montarMenu(ABAS_REAIS);
  assert.deepEqual(g.map((x) => x.rotulo), ["Ver", "Saber e fazer", "Ajustes", "Conversa"]);
  const ids = g.flatMap((x) => x.itens.map((i) => i.id));
  for (const esperado of ["inicio", "conversa", "pc", "noticias", "memoria", "grafo", "oficina", "documentos", "instagram", "cerebro", "aparencia", "uso", "agentes", "pareado", "nova", "voz", "foco"]) assert.ok(ids.includes(esperado), esperado);
  const mais = montarMenu([...ABAS_REAIS, { id: "futura", rotulo: "Nova aba" }]);
  assert.ok(mais.find((x) => x.id === "saber").itens.some((i) => i.aba === "futura" && i.rotulo === "Nova aba"));
  const sem = montarMenu([{ id: "hud", rotulo: "Início" }]);
  assert.ok(sem.flatMap((x) => x.itens).every((i) => i.acao || i.aba === "hud"), "item de aba que não existe some");
  assert.equal(GRUPOS.length, 4);
});

test("menu: teclas e item atual", () => {
  assert.equal(proximoItem(-1, 5, "ArrowDown"), 0);
  assert.equal(proximoItem(4, 5, "ArrowDown"), 0);
  assert.equal(proximoItem(0, 5, "ArrowUp"), 4);
  assert.equal(proximoItem(2, 5, "End"), 4);
  assert.equal(proximoItem(2, 0, "End"), null);
  assert.equal(proximoItem(2, 5, "a"), null);
  const g = montarMenu(ABAS_REAIS);
  assert.equal(itemAtual(g, "cerebro"), "cerebro", "o painel Aparência não rouba o 'atual' do Cérebro");
  assert.equal(itemAtual(g, "hud"), "inicio");
  assert.equal(itemAtual(g, "nada"), null);
});

// ── Foco ──
test("foco: estado, microfone, ponto de ligação da voz e botão que não obedece volta atrás", async () => {
  const f = criarEstadoFoco(), vistos = [];
  f.aoMudar((s) => vistos.push(s));
  f.abrir(); f.abrir();
  assert.equal(vistos.length, 1);
  f.definirEstado("hack"); f.definirEstado("ouvindo");
  assert.equal(f.estado, "ouvindo");
  f.definirFala("x".repeat(1000));
  assert.equal(f.fala.length, 400);
  let pedido = null;
  const desligar = f.ligarMicrofone(async ({ ativo }) => { pedido = ativo; });
  assert.equal(await f.pressionarMicrofone(), true);
  assert.equal(pedido, true);
  assert.equal(await f.pressionarMicrofone(), false);
  desligar();
  f.ligarMicrofone(async () => false);
  assert.equal(await f.pressionarMicrofone(), false, "o ouvinte recusou: o botão não acende");
  f.ligarMicrofone(async () => { throw new Error("sem permissão"); });
  assert.equal(await f.pressionarMicrofone(), false, "erro também não acende");
  f.fechar();
  assert.equal(f.aberto, false);
});

test("foco: sem ouvinte de microfone, cai no recurso existente", async () => {
  const f = criarEstadoFoco(); let chamou = null;
  f.aoFaltarMicrofone(({ ativo }) => { chamou = ativo; });
  await f.pressionarMicrofone();
  assert.equal(chamou, true);
});

// ── Segurança e estrutura ──
test("a casca nunca monta HTML a partir de texto (sem innerHTML) e todo id usado existe no index.html", () => {
  const html = arq("index.html");
  for (const f of ["hud-central", "hud-cartao", "hud-grade", "caixas-celular", "menu-grupos", "navegacao", "foco", "foco-estado", "orbe-fil", "orbe-ui", "hud-briefing", "hud-ordem", "orbe-filamentos"]) {
    const src = arq(`js/${f}.js`);
    assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(/.test(src), f);
    assert.ok(src.split("\n").length <= 300, f + " passou de 300 linhas");
  }
  for (const f of ["hud-central", "foco", "orbe-ui"]) {
    for (const [, id] of arq(`js/${f}.js`).matchAll(/\$\("([\w-]+)"\)/g)) assert.ok(html.includes(`id="${id}"`) || id.startsWith("item-"), `${f}: #${id} não existe no index.html`);  // item-* nasce na grade
  }
  for (const id of ["abas", "app", "mensagens", "voz-modo", "nova-conversa", "ver-grafo", "painel-aparencia", "painel-uso", "painel-agentes", "orbe-modo"]) assert.ok(html.includes(`id="${id}"`), id);
  assert.ok(!/<script(?![^>]*\bsrc=)[^>]*>/.test(html), "sem script inline");
  assert.ok(html.includes('data-aba="hud"') && html.includes('id="barra-rapida"') === false, "a barra rápida nasce por JS");
});

test("service worker (cache 13) lista os arquivos novos da casca", () => {
  const sw = arq("sw.js");
  assert.ok(sw.includes('"jarvis-movel-13"'));
  for (const f of ["css/hud.css", "css/hud-menu.css", "js/orbe-fil.js", "js/orbe-filamentos.js", "js/hud-central.js", "js/hud-grade.js", "js/hud-ordem.js", "js/hud-briefing.js", "js/hud-cartao.js", "js/menu-grupos.js", "js/foco.js", "js/foco-estado.js", "js/caixas-celular.js"]) assert.ok(sw.includes(`"${f}"`), f);
});

test("temas continuam com --brilho e contraste do texto no cartão central (AA)", () => {
  const css = arq("css/tema.css") + arq("css/app.css");
  assert.equal((css.match(/--brilho:/g) || []).length, 4, "um brilho por tema");
  const lum = (h) => { const [r, g, b] = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const razao = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  assert.ok(razao("#3fd0ff", "#0a1626") >= 4.5, "acento do HUD sobre o painel");
  assert.ok(razao("#8fb0c4", "#0a1626") >= 4.5, "texto suave sobre o painel");
});

test("foco-voz: foco liga a escuta, botão grande inicia/para e estado da escuta move o orbe", async () => {
  const { ligarFocoVoz, ESTADO_DO_ORBE } = await import("../js/foco-voz.js");
  const f = criarEstadoFoco(), chamadas = []; let ouvinte = null, ok = true;
  const escuta = { entrarFoco: () => chamadas.push("entrar"), sairFoco: () => chamadas.push("sair"), iniciar: () => { chamadas.push("iniciar"); return ok; }, parar: () => chamadas.push("parar"), aoMudar: (fn) => { ouvinte = fn; } };
  ligarFocoVoz({ foco: f, escuta });
  f.abrir(); f.fechar();
  assert.deepEqual(chamadas, ["entrar", "sair"]);
  chamadas.length = 0;
  assert.equal(await f.pressionarMicrofone(), true);
  assert.equal(await f.pressionarMicrofone(), false);
  assert.deepEqual(chamadas, ["iniciar", "parar"]);
  ok = false;
  assert.equal(await f.pressionarMicrofone(), false, "sem suporte: o botão não acende");
  ouvinte("ouvindo"); assert.equal(f.estado, "ouvindo"); assert.equal(f.microfoneAtivo, true);
  ouvinte("processando"); assert.equal(f.estado, "pensando");
  ouvinte("desligado"); assert.equal(f.microfoneAtivo, false);
  assert.equal(ESTADO_DO_ORBE.aguardando, "ocioso");
});
