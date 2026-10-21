// Escuta contínua por "Jarvis" com SpeechRecognition FALSO (sequência de eventos como a do Safari), relógio falso e fala falsa.
// Prova a lógica (reinício, anti-eco, extração do comando, falsos positivos, permissão negada). NÃO prova o iPhone real.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { CAUDA_ECO_MS, EscutaContinua, JANELA_COMANDO_MS, MAX_FALHAS } from "../js/escuta.js";
import { comandoDeControle, extrairComando, razao } from "../js/voz-ativacao.js";

const casos = JSON.parse(readFileSync(new URL("./dados/ativacao_python.json", import.meta.url), "utf8"));
test(`paridade com o Python: extrair_comando (${casos.length} casos)`, () => { for (const [t, esperado] of casos) assert.equal(extrairComando(t), esperado, JSON.stringify(t)); });

test("razão de semelhança igual ao difflib e tolerância a erros de escuta", () => {
  assert.equal(razao("garvis", "jarvis").toFixed(4), "0.8333");
  assert.equal(razao("javis", "jarvis").toFixed(4), "0.9091");
  for (const t of ["Javis, que horas são", "Arvis abre", "Jarvi liga", "Járvis, oi", "Garvis abre"]) assert.notEqual(extrairComando(t), null, t);
  for (const t of ["Travis abre", "Jarbas vem", "o Jarvis é legal", "falei com o jarvis", "Jarvis é um filme", "Dervis abre", "abre o jarvis"]) assert.equal(extrairComando(t), null, t);
  assert.equal(extrairComando(null), null);
});

test("pedidos de controle da própria escuta", () => {
  assert.equal(comandoDeControle("para"), "parar-fala");
  assert.equal(comandoDeControle("Silêncio!"), "parar-fala");
  assert.equal(comandoDeControle("tchau"), "desligar");
  assert.equal(comandoDeControle("desligar o microfone"), "desligar");
  assert.equal(comandoDeControle("que horas são"), null);
  assert.equal(comandoDeControle("para de fazer isso e abre o chrome"), null);
});

// ── infraestrutura falsa ──────────────────────────────────────────────────
class Rec {
  static todas = [];
  constructor() { this.abortada = false; this.iniciada = false; Rec.todas.push(this); }
  start() { if (Rec.falharStart) throw new Error("InvalidStateError"); this.iniciada = true; this.onstart?.(); }
  abort() { this.abortada = true; }
  // Safari: a cada resultado vem a lista cumulativa da sessão e resultIndex aponta para o novo.
  dizer(texto, final = true, resultIndex = 0) {
    this.res ||= [];
    this.res[resultIndex] = Object.assign([{ transcript: texto }], { isFinal: final });
    this.onresult?.({ resultIndex, results: this.res });
  }
  erro(codigo) { this.onerror?.({ error: codigo }); }
  fim() { this.onend?.(); }
}

function montar(extra = {}) {
  Rec.todas = []; Rec.falharStart = false;
  let t = 1000; const timers = [];
  const rel = {
    agora: () => t,
    esperar: (f, ms) => { const x = { f, em: t + ms, vivo: true }; timers.push(x); return x; },
    cancelar: (x) => { if (x) x.vivo = false; },
    avancar(ms) { const alvo = t + ms; for (;;) { const p = timers.filter((x) => x.vivo && x.em <= alvo).sort((a, b) => a.em - b.em)[0]; if (!p) break; p.vivo = false; t = Math.max(t, p.em); p.f(); } t = alvo; },
  };
  const escuta = new EscutaContinua({ Reconhecimento: Rec, ...rel, ...extra });
  const log = { comandos: [], estados: [], cortes: 0 };
  let liberar = null;
  escuta.configurar({
    aoComando: (c) => { log.comandos.push(c); return log.segurar ? new Promise((r) => { liberar = r; }) : undefined; },
    interromper: () => { log.cortes++; },
    textoFalado: () => log.falado || "",
  });
  escuta.aoMudar((e) => log.estados.push(e));
  return { escuta, rel, log, rec: () => Rec.todas.at(-1), soltar: () => liberar?.() };
}
const drenar = () => new Promise((r) => setImmediate(r));

test("inicia com continuous, interim e pt-BR; fica aguardando", () => {
  const { escuta, rec } = montar();
  assert.equal(escuta.iniciar(), true);
  assert.equal(rec().continuous, true); assert.equal(rec().interimResults, true); assert.equal(rec().lang, "pt-BR");
  assert.equal(escuta.estado, "aguardando");
});

test("'Jarvis, que horas são' na mesma frase entrega só o comando; estados aguardando > processando > aguardando", async () => {
  const { escuta, rec, log } = montar();
  escuta.iniciar();
  rec().dizer("Jarvis, que horas são", false);
  assert.equal(escuta.estado, "ouvindo");  // já mostra que ouviu o nome
  rec().dizer("Jarvis, que horas são", true);
  assert.equal(escuta.estado, "processando");
  await drenar();
  assert.deepEqual(log.comandos, ["que horas são"]);
  assert.deepEqual(log.estados, ["aguardando", "ouvindo", "processando", "aguardando"]);
});

test("'Jarvis' sozinho abre uma janela de ~6 s para o comando na frase seguinte", async () => {
  const { escuta, rec, log, rel } = montar();
  escuta.iniciar();
  rec().dizer("Jarvis", true);
  assert.equal(escuta.estado, "ouvindo");
  rel.avancar(JANELA_COMANDO_MS - 500);
  rec().dizer("abre o chrome", true, 1);
  await drenar();
  assert.deepEqual(log.comandos, ["abre o chrome"]);
});

test("passou da janela: a frase seguinte sem o nome é ignorada", async () => {
  const { escuta, rec, log, rel } = montar();
  escuta.iniciar();
  rec().dizer("Jarvis", true);
  rel.avancar(JANELA_COMANDO_MS + 100);
  assert.equal(escuta.estado, "aguardando");
  rec().dizer("abre o chrome", true, 1);
  await drenar();
  assert.deepEqual(log.comandos, []);
});

test("menções e nomes parecidos não ativam (anti falso-positivo)", async () => {
  const { escuta, rec, log } = montar();
  escuta.iniciar();
  for (const [i, t] of ["o Jarvis é legal", "Travis, abre a porta", "Jarbas vem cá", "que horas são", "ontem falei com o jarvis"].entries()) rec().dizer(t, true, i);
  await drenar();
  assert.deepEqual(log.comandos, []);
  assert.equal(escuta.estado, "aguardando");
});

test("interim com o nome mas final sem comando volta a aguardando", () => {
  const { escuta, rec } = montar();
  escuta.iniciar();
  rec().dizer("Jarvis é um", false);
  rec().dizer("Jarvis é um filme muito bom", true);
  assert.equal(escuta.estado, "aguardando");
});

test("o Safari encerra a sessão sozinho: abre uma sessão NOVA e continua ouvindo", async () => {
  const { escuta, rec, rel, log } = montar();
  escuta.iniciar();
  const primeira = rec();
  rel.avancar(5000);
  primeira.erro("no-speech");  // silêncio: não é falha
  primeira.fim();
  rel.avancar(200);
  assert.equal(Rec.todas.length, 2);
  assert.notEqual(rec(), primeira);
  rec().dizer("Jarvis, que dia é hoje", true);
  await drenar();
  assert.deepEqual(log.comandos, ["que dia é hoje"]);
  primeira.dizer("Jarvis, ignorada", true);  // sessão velha não conversa mais com a gente
  assert.equal(log.comandos.length, 1);
});

test("sessões que morrem na hora: espera crescente e desiste (instavel) depois de muitas falhas", () => {
  const { escuta, rec, rel } = montar();
  const vistos = [];
  escuta.aoMudar((e, info) => vistos.push([e, info.motivo]));
  escuta.iniciar();
  for (let i = 0; i < MAX_FALHAS + 2 && escuta.ativa; i++) {
    rec().fim();  // a sessão morreu assim que abriu
    for (let n = Rec.todas.length, k = 0; escuta.ativa && Rec.todas.length === n && k < 200; k++) rel.avancar(50);
  }
  assert.equal(escuta.ativa, false);
  assert.equal(escuta.motivo, "instavel");
  assert.ok(Rec.todas.length <= MAX_FALHAS + 1, `sessões: ${Rec.todas.length}`);
  assert.deepEqual(vistos.at(-1), ["desligado", "instavel"]);
});

test("start() que lança também conta como falha e não derruba nada", () => {
  const { escuta, rel } = montar();
  Rec.falharStart = true;
  escuta.iniciar();
  rel.avancar(60000);
  assert.equal(escuta.ativa, false);
  assert.equal(escuta.motivo, "instavel");
});

test("permissão negada desliga de vez e não tenta reabrir", () => {
  const { escuta, rec, rel } = montar();
  escuta.iniciar();
  rec().erro("not-allowed");
  rec().fim();
  rel.avancar(10000);
  assert.equal(escuta.estado, "desligado"); assert.equal(escuta.motivo, "permissao"); assert.equal(Rec.todas.length, 1);
  const outra = montar();
  outra.escuta.iniciar(); outra.rec().erro("service-not-allowed");
  assert.equal(outra.escuta.motivo, "permissao");
});

test("sem microfone / idioma sem suporte desligam com o motivo certo; sem API de reconhecimento não liga", () => {
  const a = montar(); a.escuta.iniciar(); a.rec().erro("audio-capture"); assert.equal(a.escuta.motivo, "microfone");
  const b = montar(); b.escuta.iniciar(); b.rec().erro("language-not-supported"); assert.equal(b.escuta.motivo, "idioma");
  const c = new EscutaContinua({ Reconhecimento: undefined }); assert.equal(c.iniciar(), false); assert.equal(c.motivo, "sem-suporte");
  const d = new EscutaContinua({ Reconhecimento: Rec, seguro: false }); assert.equal(d.iniciar(), false);
});

test("anti-eco: enquanto a Jarvis fala e por ~0,5 s depois, o que o microfone ouve é ignorado", async () => {
  const { escuta, rec, rel, log } = montar();
  escuta.iniciar();
  escuta.marcarFala(true);
  assert.equal(escuta.estado, "falando");
  rec().dizer("Jarvis abre o chrome", true);  // a própria voz voltando pelo microfone
  escuta.marcarFala(false);
  assert.equal(escuta.estado, "aguardando");
  rel.avancar(CAUDA_ECO_MS - 100);
  assert.equal(Rec.todas.length, 1);  // a sessão contaminada ainda está fechada
  rel.avancar(150);
  assert.equal(Rec.todas.length, 2);  // sessão limpa: o que o eco deixou pendente foi descartado
  rec().dizer("Jarvis, que horas são", true);
  await drenar();
  assert.deepEqual(log.comandos, ["que horas são"]);
});

test("final que chega dentro da cauda do eco é descartado", async () => {
  const { escuta, rec, rel, log } = montar();
  escuta.iniciar();
  escuta.marcarFala(true); escuta.marcarFala(false);
  const antiga = rec();
  rel.avancar(100);
  antiga.dizer("Jarvis, apague tudo", true);  // sessão fechada: ninguém escuta
  await drenar();
  assert.deepEqual(log.comandos, []);
});

test("barge-in: ouvir 'Jarvis' (que não é eco) corta a fala e o comando é aceito", async () => {
  const { escuta, rec, log } = montar();
  log.falado = "claro, são três e meia da tarde";
  escuta.iniciar();
  escuta.marcarFala(true);
  rec().dizer("Jarvis para", false);
  assert.equal(log.cortes, 1);
  rec().dizer("Jarvis para", true);
  await drenar();
  assert.deepEqual(log.comandos, ["para"]);
});

test("barge-in não dispara quando 'Jarvis' é a própria fala dela (eco)", () => {
  const { escuta, rec, log } = montar();
  log.falado = "Jarvis aqui. Tudo certo por aqui.";
  escuta.iniciar();
  escuta.marcarFala(true);
  rec().dizer("Jarvis aqui", false);
  assert.equal(log.cortes, 0);
});

test("ditado/conversa por voz: suspender solta o microfone e religa depois, uma vez só", async () => {
  const { escuta, rec, rel } = montar();
  escuta.iniciar();
  const primeira = rec();
  const p = escuta.suspender();
  rel.avancar(300);
  const retomar = await p;
  assert.equal(primeira.abortada, true);
  rel.avancar(2000);
  assert.equal(Rec.todas.length, 1);
  retomar(); retomar();
  rel.avancar(500);
  assert.equal(Rec.todas.length, 2);
});

test("tela oculta fecha o microfone; ao voltar, reabre", () => {
  const { escuta, rec, rel } = montar();
  escuta.iniciar();
  const antes = rec();
  escuta.visibilidade(false);
  assert.equal(antes.abortada, true);
  rel.avancar(5000);
  assert.equal(Rec.todas.length, 1);
  escuta.visibilidade(true);
  assert.equal(Rec.todas.length, 2);
});

test("um pedido por vez: o mais recente espera a vez; parar() limpa tudo", async () => {
  const { escuta, rec, log, soltar } = montar();
  log.segurar = true;
  escuta.iniciar();
  rec().dizer("Jarvis, primeiro", true);
  rec().dizer("Jarvis, segundo", true, 1);
  rec().dizer("Jarvis, terceiro", true, 2);
  await drenar();
  assert.deepEqual(log.comandos, ["primeiro"]);
  soltar(); await drenar();
  assert.deepEqual(log.comandos, ["primeiro", "terceiro"]);
  soltar(); await drenar();
  assert.equal(escuta.estado, "aguardando");
  escuta.parar();
  assert.equal(escuta.estado, "desligado"); assert.equal(rec().abortada, true);
});

test("ouvinte com defeito não derruba; aoMudar devolve como cancelar; erro no comando não trava", async () => {
  const { escuta, rec, log } = montar();
  escuta.aoMudar(() => { throw new Error("ruim"); });
  const off = escuta.aoMudar((e) => log.estados.push("x" + e));
  escuta.configurar({ aoComando: async () => { throw new Error("falhou"); } });
  escuta.iniciar();
  off();
  rec().dizer("Jarvis, teste", true);
  await drenar();
  assert.equal(escuta.estado, "aguardando");
  assert.ok(!log.estados.includes("xprocessando"));
});

test("modo foco: liga ao entrar (se voz_foco_auto), devolve o estado do usuário ao sair", () => {
  const a = montar();
  assert.equal(a.escuta.entrarFoco(), true); assert.equal(a.escuta.ativa, true);
  a.escuta.sairFoco(); assert.equal(a.escuta.ativa, false);
  const b = montar(); b.escuta.iniciar();
  b.escuta.entrarFoco(); b.escuta.sairFoco(); assert.equal(b.escuta.ativa, true);  // já estava ligada pelo usuário
  const c = montar(); c.escuta.configurar({ focoAuto: false });
  assert.equal(c.escuta.entrarFoco(), false); assert.equal(c.escuta.ativa, false);
});
