// PC pareado ampliado (vitais, sessões, tarefas, uso, radar, agentes): validação hostil campo a campo, offline com cópia datada,
// cartões montar(container, ctx), atualização só com aba visível e comandos de chat. Fetch e DOM falsos; nenhum PC real.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { Memoria } from "../js/memoria.js";
import { Motor } from "../js/motor.js";
import { Atualizador } from "../js/pc-atualizador.js";
import { OFFLINE, PcPareado } from "../js/pc-pareado.js";
import { validarResposta } from "../js/pc-validar.js";
import { Saber } from "../js/saber.js";

const saber = new Saber(JSON.parse(readFileSync(new URL("../dados/saber.json", import.meta.url), "utf8")));
const json = (corpo, status = 200) => ({ ok: status < 400, status, json: async () => corpo });
const J = { usado: 120.5, teto: 500, pct: 24.1, ativa: true, alerta: false, msgs: 4, fim: 1.8e9, acaba_antes_do_reset: false };
const DADOS = {
  vitais: { gerado: "2026-10-21T09:00:00+00:00", cpu: 12, ram: 40, disco: 70, ram_total_gb: 16, ram_usada_gb: 6.4, disco_total_gb: 500, disco_livre_gb: 150 },
  sessoes: { gerado: "2026-10-21T09:00:00+00:00", total: 3, contagem: { permissao: 1, pergunta: 0, aguardando: 1, trabalhando: 1, nova: 0, desconhecido: 0 },
    itens: [{ projeto: "jarvis", estado: "permissao", ha_s: 30 }], subagentes: { total: 2, contagem: { rodando: 1, concluido: 1, falhou: 0, parado: 0, inativo: 0 }, itens: [{ projeto: "jarvis", tipo: "Explore", estado: "rodando" }] } },
  tarefas: { gerado: "2026-10-21T09:00:00+00:00", total: 2, contagem: { na_fila: 1, rodando: 1, concluida: 0, falhou: 0 }, itens: [{ projeto: "site", status: "rodando", modo: "executar", tarefa: "corrigir o rodapé" }] },
  uso: { gerado: "2026-10-21T09:00:00+00:00", hoje: { msgs: 10, tokens: 123456, custo_usd: 1.234, estimado: true, custo_rotulo: "equivalente estimado em API" }, cota: { unidade: "tokens", plano: "max", janela_5h: J, semana: { ...J, pct: null, teto: null }, aviso: "Estimativa: o Claude não informa a cota." } },
  radar: { gerado: "2026-10-21T09:00:00+00:00", vazio: false, dia: "2026-10-21", hora: "07:00", total: 2, itens: [{ titulo: "Manchete", fonte: "Fonte A", quando: "21/10 06:00" }] },
  agentes: { server_now: 5, resumo: { total: 2, ok: 2 }, agentes: [{ id: "voz", nome: "Voz", state: "ok", age_s: 3 }], subagentes: { total: 1, contagem: { rodando: 1 }, itens: [] } },
};
const CAMINHO = { vitais: "/api/vitais", sessoes: "/api/sessoes", tarefas: "/api/tarefas", uso: "/api/uso", radar: "/api/radar", agentes: "/api/agents" };

async function cenario(rotas = {}) {
  const chamadas = [], memoria = new Memoria(), estado = { cair: false };
  const padrao = Object.fromEntries(Object.entries(CAMINHO).map(([k, c]) => [c, () => json(DADOS[k])]));
  const buscar = async (url, op = {}) => {
    chamadas.push({ url, op });
    if (estado.cair) throw new TypeError("Failed to fetch");
    const f = { "/api/parear": () => json({ token: "T" }), ...padrao, ...rotas }[new URL(url).pathname];
    return f ? f(op) : json({}, 404);
  };
  const pc = new PcPareado({ armazem: memoria.armazem, buscar, agora: () => new Date("2026-10-21T12:00:00Z"), timeoutMs: 50 });
  await pc.parear("https://pc.ts.net:8765", "123456");
  const motor = new Motor({ saber, memoria, buscar: async () => json({}), agora: () => new Date("2026-10-21T09:00:00") });
  motor.pc = pc;
  return { pc, motor, chamadas, estado, memoria };
}

test("cada rota nova válida passa e todas ficam só com campos conhecidos", () => {
  for (const [rota, d] of Object.entries(DADOS)) {
    const r = validarResposta(rota, { ...d, extra: "<script>", segredo: "tok" });
    assert.ok(r, rota);
    assert.ok(!("extra" in r) && !("segredo" in r), rota);
  }
  assert.equal(validarResposta("sessoes", DADOS.sessoes).itens[0].ha_s, 30);
});

test("resposta hostil: tipos errados, números absurdos, estados inventados, listas gigantes e texto longo", () => {
  for (const rota of Object.keys(DADOS)) {
    for (const lixo of [null, "x", 7, [], {}, { contagem: "x", hoje: 5, cota: [] }]) {
      const r = validarResposta(rota, lixo);
      assert.ok(r === null || typeof r === "object", rota);
    }
  }
  const v = validarResposta("vitais", { cpu: 1e99, ram: -5, disco: "9", ram_total_gb: Infinity, ram_usada_gb: NaN, disco_total_gb: 1e300 });
  assert.deepEqual([v.cpu, v.ram, v.disco, v.ram_total_gb, v.ram_usada_gb], [100, 0, 0, 0, 0]);
  assert.ok(v.disco_total_gb <= 1e6);
  const grande = Array.from({ length: 500 }, () => ({ projeto: "A".repeat(5000) + "\u0007", estado: "<img onerror=x>", ha_s: -1 }));
  const s = validarResposta("sessoes", { contagem: { permissao: 1e99, "<b>": 5 }, itens: grande, subagentes: { itens: grande, contagem: { x: 1 } } });
  assert.equal(s.itens.length, 5); assert.equal(s.itens[0].projeto.length, 40); assert.equal(s.itens[0].estado, "desconhecido"); assert.equal(s.itens[0].ha_s, null);
  assert.equal(s.contagem.permissao, 1e9); assert.ok(!("<b>" in s.contagem)); assert.equal(s.subagentes.itens.length, 5); assert.equal(s.subagentes.itens[0].estado, "inativo");
  const t = validarResposta("tarefas", { contagem: {}, itens: [{ status: "rm -rf", tarefa: "t".repeat(999) }, 3, null] });
  assert.equal(t.itens.length, 1); assert.equal(t.itens[0].status, "falhou"); assert.equal(t.itens[0].tarefa.length, 80);
  const u = validarResposta("uso", { hoje: { msgs: -1, tokens: "x", custo_usd: 1e99 }, cota: { unidade: "bananas", janela_5h: { pct: 1e99, teto: -3 }, semana: 5 } });
  assert.equal(u.cota.unidade, "tokens"); assert.equal(u.cota.janela_5h.pct, 999); assert.equal(u.cota.janela_5h.teto, null); assert.equal(u.hoje.estimado, true); assert.equal(u.hoje.msgs, 0);
  const rd = validarResposta("radar", { itens: Array.from({ length: 99 }, () => ({ titulo: "T".repeat(999) })), total: 1e9 });
  assert.equal(rd.itens.length, 8); assert.equal(rd.itens[0].titulo.length, 160); assert.equal(rd.total, 99);
  const ag = validarResposta("agentes", { resumo: { ok: "x", ["a".repeat(99)]: 1 }, agentes: [{ id: {}, nome: 5 }], subagentes: { total: 3, contagem: { rodando: 2 } } });
  assert.equal(ag.agentes[0].id, ""); assert.ok(Object.keys(ag.resumo).every((k) => k.length <= 20)); assert.equal(ag.subagentes.contagem.rodando, 2);
});

test("rotas novas: Bearer, cópia datada quando offline, 401 pede novo pareamento, sem cópia só o aviso", async () => {
  const c = await cenario();
  for (const rota of Object.keys(DADOS)) {
    const r = await c.pc.obter(rota);
    assert.ok(r.ok && !r.doCache, rota);
    assert.equal(c.chamadas.at(-1).url, "https://pc.ts.net:8765" + CAMINHO[rota]);
    assert.equal(c.chamadas.at(-1).op.headers.Authorization, "Bearer T");
    assert.equal(c.chamadas.at(-1).op.credentials, "omit");
  }
  c.estado.cair = true;
  for (const rota of Object.keys(DADOS)) {
    const off = await c.pc.obter(rota);
    assert.ok(off.ok && off.doCache && off.erro === OFFLINE && off.quando === "2026-10-21T12:00:00.000Z", rota);
  }
  const limpa = await cenario({ "/api/uso": () => json({}, 401) });
  assert.match((await limpa.pc.obter("uso")).erro, /Pareie de novo/);
  const semCopia = await cenario();
  semCopia.estado.cair = true;
  assert.deepEqual(await semCopia.pc.obter("radar"), { ok: false, erro: OFFLINE });
  await c.pc.desparear();
  assert.ok(!(await c.memoria.armazem.ler("pc:cache:sessoes")));  // despareado apaga as cópias das rotas novas
});

test("cache corrompido de uma rota nova não derruba", async () => {
  const c = await cenario();
  c.estado.cair = true;
  await c.memoria.armazem.gravar("pc:cache:sessoes", { quando: "x", dados: "lixo" });
  assert.equal((await c.pc.obter("sessoes")).ok, false);
});

test("comandos de chat locais com e sem PC pareado", async () => {
  const c = await cenario();
  assert.match(await c.motor.responder("Como está meu PC?"), /CPU:\*\* 12%[\s\S]*RAM:\*\* 40% \(6,4 de 16,0 GB\)[\s\S]*Disco/);
  assert.match(await c.motor.responder("sessões do Claude"), /3 \(1 esperando sua permissão[\s\S]*jarvis: esperando sua permissão \(há 30 s\)[\s\S]*Subagentes:\*\* 2/);
  assert.match(await c.motor.responder("minha cota"), /Cota do Claude \(estimada\):\*\* janela de 5 h: 24,1% usado; semana: 121 tokens ponderados \(teto não calibrado\)/);
  assert.match(await c.motor.responder("tarefas do PC"), /2 \(1 na fila, 1 rodando\)[\s\S]*site: rodando — corrigir o rodapé/);
  assert.match(await c.motor.responder("radar do pc"), /Manchete \(Fonte A\)/);
  c.estado.cair = true;
  assert.match(await c.motor.responder("como está meu pc"), /Cópia de .*PC desligado ou fora da rede/);
  const vazio = await cenario();
  await vazio.pc.desparear();
  for (const t of ["como está meu pc", "sessões do claude", "minha cota", "tarefas do pc"]) assert.match(await vazio.motor.responder(t), /precisa do PC pareado/);
});

// DOM mínimo para montar os cartões.
class No {
  constructor(tag) { this.tag = tag; this.filhos = []; this.dataset = {}; this._eventos = {}; }
  append(...f) { this.filhos.push(...f); }
  replaceChildren(...f) { this.filhos = f; }
  addEventListener(n, fn) { this._eventos[n] = fn; }
  set textContent(v) { this.filhos = [String(v)]; }
  get textContent() { return this.filhos.map((f) => (typeof f === "string" ? f : f.textContent)).join(""); }
}
const instalarDom = () => { globalThis.document = { createElement: (tag) => new No(tag), visibilityState: "visible" }; };

test("cartões: montar(container, ctx) desenha só texto, mostra cópia datada e aviso offline", async () => {
  instalarDom();
  const { montar, CARTOES } = await import("../js/painel-pc-geral.js");
  assert.equal(CARTOES.length, 8);
  for (const m of CARTOES) assert.equal(typeof m.montar, "function");
  const c = await cenario({ "/api/sessoes": () => json({ ...DADOS.sessoes, itens: [{ projeto: "<img src=x onerror=alert(1)>", estado: "permissao", ha_s: 5 }] }) });
  const container = new No("div");
  const painel = montar(container, { pc: c.pc });
  assert.equal(painel.cartoes.length, 8);
  await painel.atualizar();
  const sess = painel.cartoes.find((x) => x.id === "pc-sessoes");
  assert.match(sess.cartao.corpo.textContent, /<img src=x onerror=alert\(1\)>/);  // chega como texto; nunca vira elemento
  assert.match(sess.cartao.rodape.textContent, /^Atualizado às/);
  assert.ok(!container.filhos.some((f) => f.tag === "script" || f.tag === "img"));
  c.estado.cair = true;
  await painel.atualizar();
  assert.match(sess.cartao.rodape.textContent, /PC desligado ou fora da rede\. Mostrando a cópia de/);
  assert.match(container.filhos[0].textContent, /Mostrando as últimas cópias/);
  const sozinho = new No("div");
  const um = (await import("../js/pc-vitais.js")).montar(sozinho, { pc: c.pc });
  assert.equal(um.id, "pc-vitais");
});

test("PC offline sem cópia: aviso amigável; sem pareamento: convite para parear, sem pedir nada à rede", async () => {
  instalarDom();
  const { montar } = await import("../js/painel-pc-geral.js");
  const c = await cenario();
  c.estado.cair = true;
  const p = montar(new No("div"), { pc: c.pc });
  await p.atualizar();
  assert.match(p.cartoes[0].cartao.corpo.textContent, /PC desligado ou fora da rede/);
  await c.pc.desparear();
  const antes = c.chamadas.length;
  await p.atualizar();
  assert.equal(c.chamadas.length, antes);
});

test("atualização automática: só com aba visível, ativa e PC pareado; sem sobreposição; para ao pedir", async () => {
  let chamadas = 0, visivel = true, ativo = true, pareado = true, liberar;
  const ag = { agendados: [] };
  const a = new Atualizador({ atualizar: () => { chamadas++; return new Promise((ok) => { liberar = ok; }); }, visivel: () => visivel, ativo: () => ativo, pareado: async () => pareado,
    agendar: (f, ms) => { ag.agendados.push(ms); return 7; }, cancelar: (id) => { ag.cancelado = id; } });
  visivel = false; assert.equal(await a.tick(), false);
  visivel = true; ativo = false; assert.equal(await a.tick(), false);
  ativo = true; pareado = false; assert.equal(await a.tick(), false);
  assert.equal(chamadas, 0);
  pareado = true;
  const t1 = a.tick();
  await new Promise((ok) => setTimeout(ok, 5));
  assert.equal(await a.tick(), false);  // ainda rodando: não empilha
  liberar(); assert.equal(await t1, true);
  assert.equal(chamadas, 1);
  a.iniciar(); a.iniciar();
  assert.deepEqual(ag.agendados, [30000]);
  a.parar(); assert.equal(ag.cancelado, 7);
  const falha = new Atualizador({ atualizar: async () => { throw new Error("x"); }, visivel: () => true, ativo: () => true, pareado: async () => true });
  assert.equal(await falha.tick(), true); assert.equal(falha.rodando, false);  // erro não trava o próximo ciclo
});

test("nada no painel executa ação no PC: só rotas GET de leitura", async () => {
  const c = await cenario();
  for (const rota of Object.keys(DADOS)) await c.pc.obter(rota);
  const gets = c.chamadas.filter((x) => !x.url.endsWith("/api/parear"));
  assert.ok(gets.length >= 6 && gets.every((x) => !x.op.method || x.op.method === "GET"));
  for (const arq of ["pc-vitais", "pc-sessoes", "pc-tarefas", "pc-uso", "pc-radar", "pc-agentes", "painel-pc-geral"]) {
    const fonte = readFileSync(new URL(`../js/${arq}.js`, import.meta.url), "utf8");
    assert.ok(!/aprovar|POST|innerHTML/i.test(fonte), arq);
  }
});
