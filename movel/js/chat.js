// Tela de conversa: mensagens, voz (ditado, leitura e conversa por voz contínua) e estado visual.
import { renderizar } from "./md.js";
import { ligarEscuta, ligarFala } from "./orbe-voz.js";

const $ = (id) => document.getElementById(id);
const Reconhecimento = window.SpeechRecognition || window.webkitSpeechRecognition;

export function adicionar(texto, quem = "jarvis", nota = "") {
  const bolha = document.createElement("div");
  bolha.className = "msg " + quem;
  if (quem === "eu") bolha.textContent = texto;
  else renderizar(texto, bolha);
  if (nota) { const n = document.createElement("small"); n.textContent = nota; bolha.appendChild(n); }
  $("mensagens").appendChild(bolha);
  $("mensagens").scrollTop = $("mensagens").scrollHeight;
  return bolha;
}

export function atualizar(bolha, texto) {
  bolha.replaceChildren();
  renderizar(texto, bolha);
  $("mensagens").scrollTop = $("mensagens").scrollHeight;
}

// O orbe (canvas) mostra o estado; o texto em #estado diz o mesmo para quem não vê a animação.
let orbe = null;
export const usarOrbe = (o) => { orbe = o; };

export function pensando(sim, texto = "pensando…") {
  if (sim) orbe?.definirEstado("pensando"); else if (orbe?.estadoAtual === "pensando") orbe.definirEstado("ocioso");
  $("estado").textContent = sim ? texto : "pronta";
  $("enviar").disabled = sim;
}

// ── fala ────────────────────────────────────────────────────────────────
// O iPhone só libera a fala depois de um toque do usuário: "destrava" no primeiro toque na tela.
let destravada = false;
export function destravarFala() {
  if (destravada || !("speechSynthesis" in window)) return;
  destravada = true;
  const mudo = new SpeechSynthesisUtterance(" ");
  mudo.volume = 0;
  window.speechSynthesis.speak(mudo);
}

function escolherVoz() {
  const vozes = window.speechSynthesis.getVoices();
  return vozes.find((v) => /pt[-_]BR/i.test(v.lang)) || vozes.find((v) => /^pt/i.test(v.lang)) || null;
}

export const textoParaFala = (texto) => texto.replace(/```[\s\S]*?```/g, " código omitido. ").replace(/[`*#_>-]+/g, " ").replace(/https?:\/\/\S+/g, " link ").replace(/\s+/g, " ").trim().slice(0, 500);

// Devolve uma promessa que termina quando a fala acaba (para a conversa por voz só voltar a ouvir depois).
export function falar(texto, forcar = false) {
  if ((!forcar && !$("falar").checked) || !("speechSynthesis" in window)) return Promise.resolve();
  const limpo = textoParaFala(texto);
  if (!limpo) return Promise.resolve();
  return new Promise((resolver) => {
    window.speechSynthesis.cancel();
    const fala = new SpeechSynthesisUtterance(limpo);
    fala.lang = "pt-BR";
    const voz = escolherVoz();
    if (voz) fala.voice = voz;
    const visual = orbe ? ligarFala(orbe, limpo, fala.rate) : null;  // anima pelo ritmo do texto, não pelo som real
    const terminar = () => { visual?.fim(); if ($("estado").textContent === "falando…") $("estado").textContent = "pronta"; resolver(); };
    fala.onstart = () => { visual?.inicio(); $("estado").textContent = "falando…"; };
    fala.onboundary = (ev) => visual?.limite(ev);
    fala.onend = fala.onerror = terminar;
    window.speechSynthesis.speak(fala);
    setTimeout(terminar, 30000);  // nunca trava a conversa se o navegador não avisar o fim da fala
  });
}

export const vozDisponivel = () => Boolean(Reconhecimento) && window.isSecureContext;

function ouvirUmaVez() {
  return new Promise((resolver, rejeitar) => {
    const rec = new Reconhecimento();
    rec.lang = "pt-BR";
    rec.interimResults = false;
    if (orbe) ligarEscuta(orbe, rec);
    let ouvido = "";
    rec.onresult = (ev) => { ouvido = ev.results[0][0].transcript; };
    rec.onerror = (ev) => rejeitar(new Error(ev.error || "microfone"));
    rec.onend = () => resolver(ouvido);
    rec.start();
  });
}

// Ditado de uma frase.
export function ligarDitado(aoOuvir) {
  if (!vozDisponivel()) return;
  $("mic").hidden = false;
  $("mic").addEventListener("click", async () => {
    $("mic").classList.add("ativo");
    try { const t = await ouvirUmaVez(); if (t) aoOuvir(t); } catch { /* sem permissão: nada a fazer */ } finally { $("mic").classList.remove("ativo"); }
  });
}

const PARAR = /^(tchau|parar|encerrar|pode parar|chega|desligar)( conversa)?\.?$/i;

// Conversa por voz contínua: ouve, responde (falando) e volta a ouvir, até você tocar de novo ou dizer "tchau".
export function ligarConversaPorVoz(responder) {
  const botao = $("voz-modo");
  if (!vozDisponivel()) {
    botao.hidden = true;
    $("dica-voz").hidden = false;
    return;
  }
  let ativo = false;
  const estado = (t) => { $("estado").textContent = t; };
  async function laco() {
    while (ativo) {
      let texto = "";
      try { estado("ouvindo…"); texto = (await ouvirUmaVez()).trim(); } catch (e) {
        adicionar("Não consegui usar o microfone (" + e.message + "). Confira a permissão do Safari para este site.", "jarvis erro");
        break;
      }
      if (!texto) continue;  // silêncio: volta a ouvir
      if (PARAR.test(texto)) { adicionar("Conversa por voz encerrada.", "jarvis aviso"); break; }
      adicionar(texto, "eu");
      estado("pensando…");
      const resposta = await responder(texto);
      estado("falando…");
      await falar(resposta, true);
    }
    ativo = false;
    botao.setAttribute("aria-pressed", "false");
    botao.textContent = "🎙️ Conversar por voz";
    estado("pronta");
  }
  botao.addEventListener("click", () => {
    destravarFala();
    ativo = !ativo;
    botao.setAttribute("aria-pressed", String(ativo));
    botao.textContent = ativo ? "⏹ Parar conversa por voz" : "🎙️ Conversar por voz";
    if (ativo) laco();
  });
}
