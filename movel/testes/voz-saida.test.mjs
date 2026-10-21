// Voz de saída: escolha da melhor voz pt-BR, Gemini TTS com fetch falso (formato PCM/WAV, cache, chave só no cabeçalho), reserva para SpeechSynthesis,
// indicador de microfone e painel Cérebro > Voz. Tudo com peças falsas: o som real e o iPhone ficam fora destes testes.
import assert from "node:assert/strict";
import test from "node:test";
import { achar, instalarDom, No } from "./dom-falso.mjs";
import { EscutaContinua } from "../js/escuta.js";
import { montarIndicador } from "../js/escuta-ui.js";
import { AVISO_GEMINI, montarPainelVoz } from "../js/painel-voz.js";
import { criarGemini, decodificarAudio, MAX_TEXTO } from "../js/voz-gemini.js";
import { escolherVoz, listarVozesPt } from "../js/voz-escolha.js";
import { prepararPartes, quebrar, Saida } from "../js/voz-saida.js";

const v = (name, lang, extra = {}) => ({ name, lang, voiceURI: extra.uri || name, localService: true, ...extra });
const b64 = (bytes) => Buffer.from(bytes).toString("base64");
const pcmBytes = (...amostras) => { const b = Buffer.alloc(amostras.length * 2); amostras.forEach((a, i) => b.writeInt16LE(a, 2 * i)); return b; };
function wav(amostras, taxa = 24000) {
  const dados = pcmBytes(...amostras), h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + dados.length, 4); h.write("WAVEfmt ", 8); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
  h.writeUInt32LE(taxa, 24); h.writeUInt32LE(taxa * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34); h.write("data", 36); h.writeUInt32LE(dados.length, 40);
  return Buffer.concat([h, dados]);
}

test("melhor voz pt-BR: Aprimorada > Luciana > Felipe > outras; fora do português nunca; preferida do usuário vence", () => {
  const vozes = [v("Samantha", "en-US"), v("Eddy (Português (Brasil))", "pt-BR"), v("Joana", "pt-PT"), v("Felipe", "pt-BR"), v("Luciana", "pt-BR"),
    v("Luciana (Aprimorada)", "pt_BR", { uri: "com.apple.voice.enhanced.pt-BR.Luciana" }), v("Thomas", "fr-FR")];
  const lista = listarVozesPt(vozes).map((x) => x.name);
  assert.deepEqual(lista, ["Luciana (Aprimorada)", "Luciana", "Felipe", "Eddy (Português (Brasil))", "Joana"]);
  assert.equal(escolherVoz(vozes).name, "Luciana (Aprimorada)");
  assert.equal(escolherVoz(vozes, "Felipe").name, "Felipe");
  assert.equal(escolherVoz(vozes, "sumiu").name, "Luciana (Aprimorada)");  // preferida que não existe mais
  assert.equal(escolherVoz([v("Samantha", "en-US")]), null);
  assert.equal(escolherVoz([]), null);
  assert.equal(escolherVoz(undefined), null);
});

test("Gemini: decodifica PCM cru e WAV; formato estranho vira erro", () => {
  const a = decodificarAudio(b64(pcmBytes(1, -2, 300)), "audio/L16;codec=pcm;rate=16000");
  assert.deepEqual([...a.pcm], [1, -2, 300]); assert.equal(a.taxa, 16000);
  const b = decodificarAudio(b64(pcmBytes(5, 6)), "");
  assert.equal(b.taxa, 24000);
  const c = decodificarAudio(b64(wav([10, 20, 30, -40], 22050)), "audio/wav");
  assert.deepEqual([...c.pcm], [10, 20, 30, -40]); assert.equal(c.taxa, 22050);
  assert.throws(() => decodificarAudio(b64(Buffer.alloc(0)), ""), /vazio/);
  const estereo = wav([1, 2]); estereo.writeUInt16LE(2, 22);
  assert.throws(() => decodificarAudio(b64(estereo), "audio/wav"), /inesperado/);
});

function fetchGemini(respostas, chamadas) {
  return async (url, opcoes) => {
    chamadas.push({ url, opcoes, corpo: JSON.parse(opcoes.body) });
    const r = respostas.shift();
    return { ok: r.status === undefined, status: r.status ?? 200, json: async () => r.json };
  };
}
const audioOk = (amostras = [1, 2, 3]) => ({ json: { candidates: [{ content: { parts: [{ inlineData: { mimeType: "audio/L16;codec=pcm;rate=24000", data: b64(pcmBytes(...amostras)) } }] } }] } });

test("Gemini TTS: pedido correto, chave só no cabeçalho, cache curto, modelo encerrado passa ao próximo", async () => {
  const chamadas = [];
  const g = criarGemini({ chave: async () => "CHAVE-SECRETA-123", buscar: fetchGemini([{ status: 404 }, audioOk([7, 8])], chamadas) });
  const r = await g.sintetizar("Olá, tudo bem?", { voz: "Puck" });
  assert.deepEqual([...r.pcm], [7, 8]);
  assert.equal(chamadas.length, 2);
  const c = chamadas[1];
  assert.match(c.url, /^https:\/\/generativelanguage\.googleapis\.com\/v1beta\/models\/.+:generateContent$/);
  assert.ok(!chamadas.some((x) => x.url.includes("CHAVE-SECRETA")), "a chave não pode ir na URL");
  assert.equal(c.opcoes.headers["x-goog-api-key"], "CHAVE-SECRETA-123");
  assert.deepEqual(c.corpo.generationConfig.responseModalities, ["AUDIO"]);
  assert.equal(c.corpo.generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName, "Puck");
  assert.equal(c.corpo.contents[0].parts[0].text, "Olá, tudo bem?");
  await g.sintetizar("Olá, tudo bem?", { voz: "Puck" });  // cache: sem nova chamada
  assert.equal(chamadas.length, 2);
  await assert.rejects(g.sintetizar("x".repeat(MAX_TEXTO + 1)), /longo demais/);
  await assert.rejects(g.sintetizar("  "), /vazio/);
});

test("Gemini TTS: chave recusada/cota/sem áudio/sem chave dão erro claro, sem vazar a chave e sem tentar outro modelo à toa", async () => {
  for (const [status, esperado] of [[403, /chave recusada/], [429, /limite de uso/]]) {
    const chamadas = [];
    const g = criarGemini({ chave: async () => "CHAVE-SECRETA-123", buscar: fetchGemini([{ status }, audioOk()], chamadas) });
    await assert.rejects(g.sintetizar("oi"), (e) => esperado.test(e.message) && !e.message.includes("CHAVE"));
    assert.equal(chamadas.length, 1);
  }
  const g2 = criarGemini({ chave: async () => "CHAVE-SECRETA-123", buscar: fetchGemini([{ json: { candidates: [{ content: { parts: [{ text: "oi" }] } }] } }], []) });
  await assert.rejects(g2.sintetizar("oi"), /não devolveu áudio/);
  const g3 = criarGemini({ chave: async () => null, buscar: async () => { throw new Error("não devia chamar"); } });
  await assert.rejects(g3.sintetizar("oi"), /sem chave/);
  assert.equal(await g3.disponivel(), false);
});

// ── Saida ─────────────────────────────────────────────────────────────────
class Fala { constructor(texto) { this.text = texto; } }
function montarSaida({ vozes = [v("Luciana", "pt-BR")], gemini = null, tocador = null } = {}) {
  const falas = [];
  const sintese = { getVoices: () => vozes, cancel() { this.cancelou = (this.cancelou || 0) + 1; }, speak(u) { falas.push(u); setImmediate(() => { u.onstart?.(); u.onend?.(); }); } };
  const s = new Saida({ sintese, Fala, esperar: async () => {} });
  if (gemini) s.usarGemini(gemini, tocador);
  const eventos = [], avisos = [];
  s.aoMudar((e) => eventos.push(e)); s.aoAviso((m) => avisos.push(m));
  return { s, falas, eventos, avisos, sintese };
}
const tocadorFalso = (log, { falha = false } = {}) => ({ disponivel: () => true, destravar() { log.push("destravar"); }, parar() { log.push("parar"); }, async tocar(a) { if (falha) throw new Error("áudio bloqueado"); log.push(["tocou", a.pcm.length]); } });

test("texto longo vira frases de no máximo 350 caracteres, normalizadas em pt-BR, sem Markdown nem link", () => {
  const longo = "Uma frase sem ponto final " + "palavra ".repeat(45);
  const partes = prepararPartes(longo + ". Custa R$ 5,00 às 14:30. **Veja** https://x.org/a?b=1");
  assert.ok(partes.length >= 3 && partes.every((p) => p.length <= MAX_TEXTO), JSON.stringify(partes.map((p) => p.length)));
  const junto = partes.join(" ");
  assert.match(junto, /cinco reais/); assert.match(junto, /duas e trinta|catorze e trinta/);
  assert.ok(!/\*\*|https?:/.test(junto));
  assert.deepEqual(quebrar("a".repeat(800), 350).map((p) => p.length), [350, 350, 100]);
  assert.deepEqual(prepararPartes(""), []);
  assert.deepEqual(prepararPartes(null), []);
});

test("voz do aparelho: fala frase a frase com a melhor voz pt-BR e avisa falando/pronta", async () => {
  const { s, falas, eventos } = montarSaida({ vozes: [v("Samantha", "en-US"), v("Felipe", "pt-BR"), v("Luciana (Aprimorada)", "pt-BR", { uri: "enh" })] });
  await s.falar("Primeira frase bem comprida para não juntar com a seguinte aqui. Segunda frase também comprida para ficar separada.");
  assert.ok(falas.length >= 2);
  assert.ok(falas.every((f) => f.lang === "pt-BR" && f.voice.voiceURI === "enh"));
  assert.deepEqual(eventos, ["falando", "pronta"]);
  assert.equal(s.falando, false);
});

test("Gemini ligado: toca o áudio do Gemini, pede a próxima frase adiantado e não usa a voz do aparelho", async () => {
  const pedidos = [], log = [];
  const gemini = { sintetizar: async (t) => { pedidos.push(t); return { pcm: new Int16Array(240), taxa: 24000 }; } };
  const { s, falas } = montarSaida({ gemini, tocador: tocadorFalso(log) });
  s.configurar({ provedor: "gemini", vozGemini: "Puck" });
  await s.falar("Primeira frase bem comprida para não juntar com a seguinte aqui. Segunda frase também comprida para ficar separada.");
  assert.equal(pedidos.length, 2);
  assert.equal(log.filter((x) => Array.isArray(x)).length, 2);
  assert.equal(falas.length, 0);
});

test("Gemini falha: cai na voz do aparelho, avisa UMA vez e continua falando; 3 falhas seguidas descansam o Gemini", async () => {
  const pedidos = [];
  const gemini = { sintetizar: async (t) => { pedidos.push(t); throw new Error("limite de uso do Gemini atingido"); } };
  const { s, falas, avisos } = montarSaida({ gemini, tocador: tocadorFalso([]) });
  s.configurar({ provedor: "gemini" });
  await s.falar("Primeira frase bem comprida para não juntar com a seguinte aqui. Segunda frase também comprida para ficar separada.");
  assert.ok(falas.length >= 2, "a fala não pode sumir");
  assert.equal(avisos.length, 1); assert.match(avisos[0], /limite de uso/);
  await s.falar("Terceira. "); await s.falar("Quarta frase bem comprida para forçar mais uma tentativa no Gemini.");
  const antes = pedidos.length;
  await s.falar("Quinta frase bem comprida depois do descanso do Gemini, que não deve ser chamado de novo.");
  assert.equal(pedidos.length, antes);
});

test("Gemini com áudio bloqueado pelo iOS: reserva na voz do aparelho", async () => {
  const gemini = { sintetizar: async () => ({ pcm: new Int16Array(100), taxa: 24000 }) };
  const { s, falas } = montarSaida({ gemini, tocador: tocadorFalso([], { falha: true }) });
  s.configurar({ provedor: "gemini" });
  await s.falar("Uma frase para testar a reserva quando o áudio está bloqueado.");
  assert.equal(falas.length, 1);
});

test("provedor 'navegador' nunca chama o Gemini (nada sai do aparelho); parar() corta e libera", async () => {
  const gemini = { sintetizar: async () => { throw new Error("não devia chamar"); } };
  const log = [];
  const { s, eventos, sintese } = montarSaida({ gemini, tocador: tocadorFalso(log) });
  await s.falar("Frase de teste para o provedor do aparelho.");
  s.parar();
  assert.ok(sintese.cancelou >= 1); assert.ok(log.includes("parar"));
  assert.deepEqual(eventos, ["falando", "pronta"]);
  s.destravar(); s.destravar();
  assert.ok(log.filter((x) => x === "destravar").length >= 2);  // o áudio é retomado a cada toque
});

test("nova fala corta a anterior sem deixar o estado preso em 'falando'", async () => {
  const { s, eventos } = montarSaida();
  const a = s.falar("Primeira fala bem longa para ser cortada pela segunda fala que chega depois dela.");
  const b = s.falar("Segunda fala.");
  await Promise.all([a, b]);
  assert.equal(s.falando, false);
  assert.equal(eventos.at(-1), "pronta");
});

test("sem SpeechSynthesis e sem Gemini: falar não lança", async () => {
  const s = new Saida({ sintese: undefined, Fala: undefined });
  await s.falar("oi, tudo bem por aí?");
  s.destravar(); s.parar();
});

// ── indicador e painel ────────────────────────────────────────────────────
function docFalso() {
  const doc = instalarDom();
  doc.body = new No("body"); doc.head = new No("head");
  return doc;
}

test("indicador de microfone: visível quando ativo, desliga com um toque, mostra o motivo se foi bloqueado", () => {
  const doc = docFalso();
  const escuta = new EscutaContinua({ Reconhecimento: class { start() {} abort() {} } });
  const caixa = montarIndicador(escuta, { doc });
  assert.equal(caixa.hidden, true);
  escuta.iniciar();
  assert.equal(caixa.hidden, false);
  assert.match(caixa.textContent, /Microfone ligado/);
  const botao = achar(caixa, (n) => n.tag === "button")[0];
  assert.equal(botao.textContent, "Desligar");
  botao.onclick();
  assert.equal(escuta.ativa, false); assert.equal(caixa.hidden, true);
  escuta.iniciar(); escuta._erro("not-allowed");
  assert.equal(caixa.hidden, false); assert.match(caixa.textContent, /bloqueado/);
  assert.equal(achar(caixa, (n) => n.tag === "button")[0].textContent, "Fechar");
});

function memoriaFalsa(inicial = {}) {
  const m = new Map(Object.entries(inicial));
  return { meta: async (k) => m.get(k), definirMeta: async (k, x) => { m.set(k, x); }, m };
}
const disparar = async (no, tipo = "change") => { for (const f of no.ouvintes[tipo] || []) await f({}); };

test("Cérebro > Voz: Gemini exige chave e confirmação clara; recusar mantém a voz do aparelho e não grava nada", async () => {
  const doc = docFalso();
  const saida = new Saida({ sintese: { getVoices: () => [v("Luciana", "pt-BR")] }, Fala });
  const escuta = new EscutaContinua({ Reconhecimento: undefined });
  const memoria = memoriaFalsa();
  let chave = null, perguntas = [], resposta = false;
  const nuvem = { chaveGemini: async () => chave };
  const pai = new No("div");
  const p = await montarPainelVoz(pai, { saida, escuta, memoria, nuvem, doc, confirmar: (t) => { perguntas.push(t); return resposta; } });
  p.selProvedor.value = "gemini"; await disparar(p.selProvedor);
  assert.equal(p.selProvedor.value, "navegador"); assert.match(p.status.textContent, /Cadastre primeiro/); assert.equal(perguntas.length, 0);
  chave = "k".repeat(30);
  p.selProvedor.value = "gemini"; await disparar(p.selProvedor);
  assert.equal(perguntas.length, 1); assert.equal(perguntas[0], AVISO_GEMINI);
  assert.match(AVISO_GEMINI, /TEXTO.*Google/s);
  assert.equal(p.selProvedor.value, "navegador"); assert.equal(saida.config.provedor, "navegador"); assert.equal(memoria.m.has("voz_provedor"), false);
  resposta = true;
  p.selProvedor.value = "gemini"; await disparar(p.selProvedor);
  assert.equal(saida.config.provedor, "gemini"); assert.equal(memoria.m.get("voz_provedor"), "gemini");
  p.selGemini.value = "Puck"; await disparar(p.selGemini);
  assert.equal(saida.config.vozGemini, "Puck");
});

test("Cérebro > Voz: lembra as escolhas (voz do aparelho, foco automático) e o Gemini salvo só vale se a chave ainda existe", async () => {
  const doc = docFalso();
  const saida = new Saida({ sintese: { getVoices: () => [v("Luciana", "pt-BR"), v("Felipe", "pt-BR")] }, Fala });
  const escuta = new EscutaContinua({ Reconhecimento: undefined });
  const memoria = memoriaFalsa({ voz_provedor: "gemini", voz_navegador_voz: "Felipe", voz_foco_auto: false });
  const p = await montarPainelVoz(new No("div"), { saida, escuta, memoria, nuvem: { chaveGemini: async () => null }, doc });
  assert.equal(saida.config.provedor, "navegador");  // sem chave: volta à voz do aparelho
  assert.equal(saida.config.vozURI, "Felipe"); assert.equal(p.chkFoco.checked, false);
  p.selAparelho.value = "Luciana"; await disparar(p.selAparelho);
  assert.equal(memoria.m.get("voz_navegador_voz"), "Luciana");
  p.chkFoco.checked = true; await disparar(p.chkFoco);
  assert.equal(memoria.m.get("voz_foco_auto"), true); assert.equal(escuta.entrarFoco(), false);  // sem reconhecimento neste "aparelho"
});
