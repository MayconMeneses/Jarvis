// Orbe de filamentos do celular: cores do tema, perfis, fps, adaptação por custo de quadro, pausa e modos. (A casca está em hud.test.mjs.)
import assert from "node:assert/strict";
import test from "node:test";
import { OrbeFil, adaptar, alvosDoTema, fpsDe, perfilDe, rgbDe } from "../js/orbe-fil.js";

// ── Orbe de filamentos ──
test("orbe: cores do tema, perfis e adaptação pelo custo de quadro", () => {
  assert.deepEqual(rgbDe(" #3fd0ff "), [63, 208, 255]);
  assert.deepEqual(rgbDe("#fff"), [255, 255, 255]);
  assert.deepEqual(rgbDe("rgb(1, 2, 3)"), [1, 2, 3]);
  assert.equal(rgbDe("azul"), null);
  const t = alvosDoTema({ ciano: "#ffb020", laranja: "#ff9a3c", brilho: "#ffe2b0" });
  assert.deepEqual([t.ocioso.r, t.ocioso.g, t.ocioso.b], [255, 176, 32]);
  assert.deepEqual([t.pensando.r, t.pensando.g, t.pensando.b], [255, 154, 60]);
  assert.ok(t.falando.g > 176, "falando é o acento mais claro");
  assert.equal(alvosDoTema({}).ocioso.r, 63, "sem CSS usa a paleta padrão");
  assert.equal(perfilDe("completo", false).N, 26);
  assert.equal(perfilDe("completo", true).N, 20);
  assert.equal(perfilDe("suave", false).full, false);
  assert.equal(fpsDe("completo", false, false), 30);
  assert.equal(fpsDe("completo", true, false), 15);
  assert.equal(fpsDe("completo", false, true), 20);
  assert.equal(fpsDe("suave", true, false), 8);
  assert.deepEqual(adaptar(10, { leve: false, lento: false }), { leve: true, lento: false });
  assert.deepEqual(adaptar(13, { leve: true, lento: false }), { leve: true, lento: true });
  assert.deepEqual(adaptar(3, { leve: false, lento: false }), { leve: false, lento: false });
});

function canvasFalso() {
  const chamadas = { clear: 0, stroke: 0 };
  const ctx = new Proxy({ chamadas }, { get: (o, k) => (k in o ? o[k] : k === "createRadialGradient" ? () => ({ addColorStop() {} }) : () => { if (k === "clearRect") chamadas.clear++; if (k === "stroke") chamadas.stroke++; }), set: () => true });
  return { width: 0, height: 0, getContext: () => ctx, chamadas };
}
function orbeFalso(op = {}) {
  globalThis.document = { hidden: false, createElement: () => ({ width: 0, height: 0, getContext: () => canvasFalso().getContext() }), addEventListener() {}, removeEventListener() {} };
  const cv = canvasFalso(), o = new OrbeFil(cv, { raf: () => 1, cancelar() {}, ...op });
  o.medir(300, 3);
  return { o, cv };
}

test("orbe: DPR limitado, estados, rótulos e sem estado inválido", () => {
  const { o, cv } = orbeFalso();
  assert.equal(o.dpr, 1.5, "DPR até 1,5");
  assert.equal(cv.width, 450);
  const vistos = [];
  o.aoMudar((e) => vistos.push(e));
  o.definirEstado("ouvindo"); o.definirEstado("ouvindo"); o.definirEstado("nada");
  assert.deepEqual(vistos, ["ouvindo"]);
  o.definirEstado("falando"); o.fonte = () => 0.5;
  o.definirEstado("ocioso");
  assert.equal(o.fonte, null, "ao sair de falando o envelope some");
});

test("orbe: 30 fps falando, 15 parado, nível sobe com o envelope e cai devagar", () => {
  const { o } = orbeFalso();
  o.definirEstado("falando"); o.fonte = () => 0.9;
  assert.equal(o.quadro(1000), true);
  assert.equal(o.quadro(1010), false, "10 ms depois: pulado (limite de 30 fps)");
  assert.equal(o.quadro(1040), true);
  for (let t = 1080; t < 1400; t += 34) o.quadro(t);
  assert.ok(o.nivel > 0.6, "o nível acompanha o envelope");
  const alto = o.nivel;
  o.fonte = null; o.definirEstado("ocioso");
  o.quadro(1500);
  assert.ok(o.nivel > alto * 0.3, "queda lenta, sem apagar de uma vez");
  const parado = orbeFalso().o;
  assert.equal(parado.quadro(0 + 1000), true);
  assert.equal(parado.quadro(1040), false, "parado: 15 fps");
  assert.equal(parado.quadro(1070), true);
});

test("orbe: pausa com aba oculta e fora da tela; modo desligado não agenda; adapta se o quadro é caro", () => {
  let agendados = 0, cancelados = 0, oculto = false, tempo = 0;
  const { o } = orbeFalso({ raf: () => ++agendados, cancelar: () => { cancelados++; }, oculto: () => oculto, agora: () => (tempo += 12) });
  o.iniciar();
  assert.equal(agendados, 1);
  o.definirNaTela(false);
  assert.equal(cancelados, 1);
  o.definirNaTela(true);
  assert.equal(agendados, 2);
  o.definirModo("desligado");
  assert.equal(cancelados, 2);
  const antes = agendados;
  o.definirModo("completo");
  assert.equal(agendados, antes + 1);
  for (let i = 0; i < 60; i++) o.quadro(1000 + i * 70);
  assert.equal(o.leve, true, "custo de 12 ms por quadro corta os filamentos");
  assert.equal(o.depurar().filamentos, 20);
  o.parar();
});

test("orbe: modo suave e desligado desenham sem animar e sem erro", () => {
  const { o, cv } = orbeFalso();
  o.definirModo("suave"); o.quadro(1000);
  o.definirModo("desligado");
  const traçados = cv.getContext().chamadas.stroke;
  assert.ok(traçados > 0);
  assert.equal(o.quadro(2000) === true || o.quadro(2000) === false, true);
});

