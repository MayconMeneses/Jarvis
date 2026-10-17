// Tela de conversa: mensagens, voz (ditado e leitura) e estado visual.
import { renderizar } from "./md.js";

const $ = (id) => document.getElementById(id);

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

export function pensando(sim, texto = "pensando…") {
  $("orb").classList.toggle("pensando", sim);
  $("estado").textContent = sim ? texto : "pronta";
  $("enviar").disabled = sim;
}

export function falar(texto) {
  if (!$("falar").checked || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const fala = new SpeechSynthesisUtterance(texto.replace(/[`*#]/g, "").slice(0, 600));
  fala.lang = "pt-BR";
  window.speechSynthesis.speak(fala);
}

// Ditado por voz (o Safari só libera o microfone em HTTPS; no GitHub Pages isso já vale).
export function ligarDitado(aoOuvir) {
  const Reconhecimento = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Reconhecimento || !window.isSecureContext) return;
  $("mic").hidden = false;
  $("mic").addEventListener("click", () => {
    const rec = new Reconhecimento();
    rec.lang = "pt-BR";
    rec.interimResults = false;
    $("mic").classList.add("ativo");
    rec.onresult = (ev) => aoOuvir(ev.results[0][0].transcript);
    rec.onend = rec.onerror = () => $("mic").classList.remove("ativo");
    rec.start();
  });
}
