// Ativação por "Jarvis" no fim da frase (já existia no celular) + limitador de ativações por minuto (novo, porte da 0.31.0 do PC) +
// os casos de escuta errada do Whisper do PC (tests/dados/ativacao_pc.json), que NÃO valem no celular (ele usa o reconhecimento do navegador).
// Prova a lógica no Node com reconhecimento FALSO; NÃO prova o iPhone/Safari nem o microfone reais.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";
import { EscutaContinua } from "../js/escuta.js";
import { LimitadorAtivacao } from "../js/limitador-ativacao.js";
import { ehSaudacao, responderSaudacao } from "../js/saudacao.js";
import { extrairChamada } from "../js/voz-ativacao.js";

test("limitador: no máximo n por janela, libera depois dela", () => {
  let t = 0;
  const lim = new LimitadorAtivacao({ n: 2, janelaMs: 60000, agora: () => t });
  assert.deepEqual([lim.permite(), lim.permite(), lim.permite()], [true, true, false]);
  t = 60001;
  assert.equal(lim.permite(), true);
  assert.equal(new LimitadorAtivacao().n, 5, "padrão do PC: 5 por minuto");
});

test("vocativo no fim e saudação pura (mesmos exemplos da 0.31.0)", () => {
  assert.equal(extrairChamada("que horas são Jarvis"), "que horas são");
  assert.equal(extrairChamada("boa noite, Jarvis"), "boa noite");
  assert.equal(extrairChamada("falei com o Jarvis ontem"), null);
  assert.ok(ehSaudacao("boa noite, Jarvis"));
  const r = responderSaudacao("boa noite, Jarvis", new Date(2026, 9, 31, 21, 0));
  assert.match(r, /^Boa noite! .*Em que posso ajudar/);
  assert.doesNotMatch(r, /resumo|agenda|notícia/i, "saudação pura não despeja o resumo do dia");
});

class Rec {
  static todas = [];
  constructor() { Rec.todas.push(this); }
  start() { this.onstart?.(); }
  abort() {}
  dizer(texto, indice) { this.res ||= []; this.res[indice] = Object.assign([{ transcript: texto }], { isFinal: true }); this.onresult?.({ resultIndex: indice, results: this.res }); }
}

test("escuta: a 6ª ativação em 1 minuto é ignorada; depois da janela volta a valer", async () => {
  Rec.todas = [];
  let t = 1000;
  const comandos = [];
  const escuta = new EscutaContinua({ Reconhecimento: Rec, agora: () => t, esperar: () => ({}), cancelar() {} });
  escuta.configurar({ aoComando: (c) => { comandos.push(c); } });
  escuta.iniciar();
  const rec = Rec.todas.at(-1);
  const falar = async (texto, i) => { rec.dizer(texto, i); await new Promise((r) => setImmediate(r)); };
  for (let i = 0; i < 7; i++) await falar("que horas são, Jarvis", i);
  assert.equal(comandos.length, 5, "limite de 5 ativações por minuto");
  assert.equal(escuta.estado, "aguardando", "ignorar a rajada não deixa a escuta presa");
  t += 61000;
  await falar("Jarvis, que dia é hoje", 7);
  assert.deepEqual(comandos.at(-1), "que dia é hoje");
  assert.equal(comandos.length, 6);
  await falar("falei com o Jarvis ontem", 8);
  assert.equal(comandos.length, 6, "menção sem vocativo continua não ativando");
});

const caminhoPc = new URL("../../tests/dados/ativacao_pc.json", import.meta.url);
test("casos do Whisper do PC: nenhuma frase rejeitada lá ativa o celular; os erros de escuta só do PC não são aceitos aqui", { skip: !existsSync(caminhoPc) }, () => {
  const pc = JSON.parse(readFileSync(caminhoPc, "utf8"));
  for (const frase of pc.rejeitar) assert.equal(extrairChamada(frase), null, frase);
  // "Aviso/Caviso/Avos" são erros do Whisper small com voz sintética; o navegador do iPhone não os produz, e aceitá-los aqui só criaria falso positivo.
  for (const frase of ["Aviso que horas são", "Avise que horas são.", "É viz que horas são", "Boa noite, Caviso."]) assert.equal(extrairChamada(frase), null, frase);
  // Os que o celular já entende pelo mesmo caminho do PC (a lista de escutas erradas no COMEÇO da frase já existia em voz-ativacao.js):
  assert.equal(extrairChamada("Avos, que horas são"), "que horas são");
  assert.equal(extrairChamada("Veja Jarvis, que dia é hoje"), "que dia é hoje");
  assert.equal(extrairChamada("Garvis, abre o bloco de notas"), "abre o bloco de notas");
});
