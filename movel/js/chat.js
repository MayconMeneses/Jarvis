// Tela de conversa: mensagens, voz (ditado, leitura e conversa por voz contínua) e estado visual.
import { erroHumano } from "./erros.js";
import { renderizar } from "./md.js";
import { ligarEscuta } from "./orbe-voz.js";
import { Escuta } from "./escuta.js";
import { saida } from "./voz-saida.js";

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
export const usarOrbe = (o) => { orbe = o; saida.usarOrbe(o); };

export function pensando(sim, texto = "pensando…") {
  if (sim) orbe?.definirEstado("pensando"); else if (orbe?.estadoAtual === "pensando") orbe.definirEstado("ocioso");
  $("estado").textContent = sim ? texto : "pronta";
  $("enviar").disabled = sim;
}

// ── fala ────────────────────────────────────────────────────────────────
// A voz (aparelho ou Gemini, com reserva) está em voz-saida.js. O iPhone só libera fala e áudio depois de um toque: "destrava" no primeiro toque.
export const destravarFala = () => saida.destravar();
saida.aoMudar((e) => { if (e === "falando") $("estado").textContent = "falando…"; else if ($("estado").textContent === "falando…") $("estado").textContent = "pronta"; });

export const textoParaFala = (texto) => texto.replace(/```[\s\S]*?```/g, " código omitido. ").replace(/[`*#_>-]+/g, " ").replace(/https?:\/\/\S+/g, " link ").replace(/\s+/g, " ").trim().slice(0, 500);

// Devolve uma promessa que termina quando a fala acaba (para a conversa por voz só voltar a ouvir depois).
export function falar(texto, forcar = false) {
  if (!forcar && !$("falar").checked) return Promise.resolve();
  return saida.falar(texto);
}

export const vozDisponivel = () => Boolean(Reconhecimento) && window.isSecureContext;

// Só existe UM reconhecimento por vez no iOS: a escuta contínua se solta enquanto o ditado/conversa usa o microfone e volta depois.
async function ouvirUmaVez() {
  const retomar = await Escuta.suspender();
  try {
    return await new Promise((resolver, rejeitar) => {
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
  } finally { retomar(); }
}

// Ditado de uma frase.
export function ligarDitado(aoOuvir) {
  if (!vozDisponivel()) return;
  $("mic").hidden = false;
  $("mic").addEventListener("click", async () => {
    $("mic").classList.add("ativo");
    try { const t = await ouvirUmaVez(); if (t) aoOuvir(t); } catch (e) { if (!/no-speech|aborted/.test(e.message)) adicionar(erroHumano(e), "jarvis erro"); } finally { $("mic").classList.remove("ativo"); }
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
        adicionar(erroHumano(e), "jarvis erro");
        break;
      }
      if (!texto) continue;  // silêncio: volta a ouvir
      if (PARAR.test(texto)) { adicionar("Conversa por voz encerrada.", "jarvis aviso"); break; }
      adicionar(texto, "eu");
      estado("pensando…");
      const resposta = await responder(texto);
      estado("falando…");
      await falar(resposta, true);
      await new Promise((r) => setTimeout(r, 500));  // anti-eco: o microfone só reabre depois da cauda da fala
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
