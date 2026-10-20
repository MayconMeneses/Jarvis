// Orbe reativo: estados, fps, pausa, modos de movimento e a animação da fala/escuta (sem navegador: contexto de desenho falso).
import assert from "node:assert/strict";
import test from "node:test";
import { FPS, FPS_SUAVE, Orbe, modoEfetivo } from "../js/orbe.js";
import { analisadorMicrofone, contarSilabas, criarPlano, ligarEscuta, ligarFala } from "../js/orbe-voz.js";

function ctxFalso() {
  const chamadas = [];
  const alvo = { chamadas, createRadialGradient: () => ({ addColorStop() {} }) };
  return new Proxy(alvo, { get: (o, k) => (k in o ? o[k] : (...a) => { chamadas.push(k); }), set: () => true });
}
const canvasFalso = () => ({ width: 56, height: 56, getContext: () => ctxFalso() });
function orbeDe(op = {}) {
  const o = new Orbe(canvasFalso(), { raf: () => 1, cancelar() {}, oculto: () => false, ...op });
  o.redimensionar(56, 56, 3);
  return o;
}

test("DPR é limitado a 2", () => { assert.equal(orbeDe().dpr, 2); });

test("modo: a chave manual vence; sem escolha, 'reduzir movimento' do sistema vira suave", () => {
  assert.equal(modoEfetivo("auto", false), "completo");
  assert.equal(modoEfetivo("auto", true), "suave");
  assert.equal(modoEfetivo("completo", true), "completo");
  assert.equal(modoEfetivo("desligado", false), "desligado");
});

test("fps: 15 parado, 30 em atividade, 10 no modo suave", () => {
  const o = orbeDe();
  assert.equal(o.quadro(1000), true);
  assert.equal(o.quadro(1040), false);  // 40 ms < 66 ms: pula
  assert.equal(o.quadro(1070), true);   // ocioso = 15 fps
  o.definirEstado("falando");
  assert.equal(o.quadro(1105), true);   // 30 fps: 35 ms depois já desenha
  o.definirModo("suave");
  assert.equal(o.quadro(1140), false);
  assert.equal(o.quadro(1210), true);
  assert.deepEqual([FPS.ocioso, FPS.falando, FPS_SUAVE], [15, 30, 10]);
});

test("pausa com a aba oculta e retoma ao voltar", () => {
  let oculto = false, agendados = 0, cancelados = 0;
  const o = orbeDe({ raf: () => ++agendados, cancelar: () => { cancelados++; }, oculto: () => oculto });
  o.iniciar();
  assert.equal(agendados, 1);
  oculto = true;
  o._visivel();
  assert.equal(cancelados, 1);
  oculto = false;
  o._visivel();
  assert.equal(agendados, 2);
  o.parar();
});

test("modo desligado não agenda quadros", () => {
  let agendados = 0;
  const o = orbeDe({ raf: () => ++agendados });
  o.definirModo("desligado");
  o.iniciar();
  assert.equal(agendados, 0);
});

test("nível sobe rápido e cai devagar; pulso decai", () => {
  const o = orbeDe();
  o.definirEstado("falando");
  o.fonte = () => 1;
  for (let i = 0; i < 3; i++) o.atualizar(0.033);
  const subiu = o.nivel;
  assert.ok(subiu > 0.6);
  o.fonte = () => 0;
  o.atualizar(0.033);
  assert.ok(o.nivel > subiu * 0.7, "queda lenta");
  o.pulso(1); const antes = o.pulsoVal; o.atualizar(0.15);
  assert.ok(o.pulsoVal < antes * 0.5);
});

test("sílabas em português e plano de tempo: pausa em pontuação, rate acelera", () => {
  assert.equal(contarSilabas("casa"), 2);
  assert.equal(contarSilabas("Jarvis"), 2);
  assert.equal(contarSilabas("123"), 1);
  const lento = criarPlano("Olá, tudo bem? Estou aqui.", 1), rapido = criarPlano("Olá, tudo bem? Estou aqui.", 2);
  assert.ok(rapido.total < lento.total * 0.6);
  const p = lento.palavras[0];
  assert.ok(lento.nivelEm(p.t0 + (p.t1 - p.t0) / 4) > 0.2);   // dentro da palavra
  assert.ok(lento.nivelEm(p.t1 + 20) < 0.1);                    // pausa depois da vírgula
  assert.equal(lento.nivelEm(lento.total + 10), 0);             // acabou
  for (let ms = 0; ms < lento.total; ms += 25) { const n = lento.nivelEm(ms); assert.ok(n >= 0 && n <= 1); }
  assert.equal(lento.tempoDoChar(lento.palavras[2].ini), lento.palavras[2].t0);
});

test("fala: onstart abre, onboundary pulsa e reajusta o relógio, onend fecha", () => {
  const o = orbeDe();
  let agora = 1000;
  const texto = "um dois três quatro cinco seis sete";
  const v = ligarFala(o, texto, 1, () => agora);
  v.inicio();
  assert.equal(o.estadoAtual, "falando");
  assert.equal(typeof o.fonte, "function");
  agora = 1100;
  v.limite({ name: "word", charIndex: texto.indexOf("cinco") });
  assert.ok(o.pulsoVal > 0.8);
  const t = v.plano.tempoDoChar(texto.indexOf("cinco"));
  assert.ok(Math.abs(o.fonte(1100) - v.plano.nivelEm(t)) < 1e-9, "relógio reajustado");
  o.pulsoVal = 0;
  v.limite({ name: "sentence", charIndex: 0 });
  assert.equal(o.pulsoVal, 0, "só limites de palavra");
  v.fim();
  assert.equal(o.fonte, null);
  assert.equal(o.estadoAtual, "ocioso");
});

function recFalso() {
  const ouvintes = {};
  return { addEventListener: (n, f) => { (ouvintes[n] ||= []).push(f); }, emitir: async (n) => { for (const f of ouvintes[n] || []) await f(); } };
}

test("escuta: start/speechstart/result/end guiam o orbe; microfone real fica desligado por padrão", async () => {
  const o = orbeDe(), rec = recFalso();
  let analisadores = 0;
  ligarEscuta(o, rec, { criarAnalisador: async () => { analisadores++; return { nivel: () => 0.5, parar() {} }; } });
  await rec.emitir("start");
  assert.equal(o.estadoAtual, "ouvindo");
  await rec.emitir("speechstart");
  assert.ok(o.pulsoVal >= 0.9);
  await rec.emitir("end");
  assert.equal(o.estadoAtual, "ocioso");
  assert.equal(analisadores, 0, "sem getUserMedia por padrão");
});

test("microfone real (opção): usa o analisador e libera a trilha no fim", async () => {
  const o = orbeDe(), rec = recFalso();
  let parou = false;
  ligarEscuta(o, rec, { micReal: true, criarAnalisador: async () => ({ nivel: () => 0.42, parar() { parou = true; } }) });
  await rec.emitir("start");
  assert.equal(o.fonte(), 0.42);
  await rec.emitir("end");
  assert.ok(parou);
  const pedidos = [];
  const mic = await analisadorMicrofone({
    getUserMedia: async (c) => { pedidos.push(c); return { getTracks: () => [{ stop() {} }] }; },
    Contexto: class { createAnalyser() { return { getByteTimeDomainData: (d) => d.fill(192) }; } createMediaStreamSource() { return { connect() {} }; } close() {} },
  });
  assert.deepEqual(pedidos, [{ audio: true }]);
  assert.ok(mic.nivel() > 0.5);
  mic.parar();
});
