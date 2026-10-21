// Tela do modo FOCO: o orbe em tela cheia (o MESMO canvas do HUD é movido para cá), o que a Jarvis diz e um botão de microfone grande.
// Usa a Fullscreen API quando existe (iPad, desktop); no iPhone ela não existe para elementos, então só cobre a casca do app.
// Mantém a tela acesa (Wake Lock) quando o navegador deixa. O estado e o ponto de ligação com a voz estão em foco-estado.js.
import { Foco } from "./foco-estado.js";

const $ = (id) => document.getElementById(id);

export function ligarFoco({ orbe, foco = Foco, doc = document }) {
  const tela = $("foco"), alvo = $("foco-orbe"), palco = $("orbe-caixa"), canvas = $("orbe");
  if (!tela || !alvo || !palco || !canvas) return foco;
  let luz = null, anterior = null;

  const pedirLuz = async () => { try { luz = (await navigator.wakeLock?.request?.("screen")) || null; luz?.addEventListener?.("release", () => { luz = null; }); } catch { luz = null; } };
  const soltarLuz = () => { try { luz?.release?.(); } catch { /* já solta */ } luz = null; };

  function abrir() {
    anterior = doc.activeElement;
    alvo.prepend(canvas);  // o mesmo canvas: um só orbe desenhando
    tela.hidden = false;
    doc.documentElement.dataset.foco = "";
    $("foco-fechar").focus();
    try { tela.requestFullscreen?.()?.catch?.(() => {}); } catch { /* sem Fullscreen API: a tela já cobre o app */ }
    pedirLuz();
  }
  function fechar() {
    palco.prepend(canvas);
    tela.hidden = true;
    delete doc.documentElement.dataset.foco;
    try { if (doc.fullscreenElement) doc.exitFullscreen?.()?.catch?.(() => {}); } catch { /* ignorado */ }
    soltarLuz();
    anterior?.focus?.();
  }

  foco.aoMudar((s) => {
    if (s.aberto === !tela.hidden) { /* já está assim */ } else if (s.aberto) abrir(); else fechar();
    const mic = $("foco-mic");
    mic.setAttribute("aria-pressed", String(s.microfoneAtivo));
    mic.textContent = s.microfoneAtivo ? "Parar" : "Falar";
    $("foco-fala").textContent = s.fala;
    if (orbe && s.estado !== orbe.estadoAtual) orbe.definirEstado(s.estado);
  });
  orbe?.aoMudar((estado) => foco.definirEstado(estado));  // o orbe manda quando é a conversa que muda o estado

  $("foco-fechar").addEventListener("click", () => foco.fechar());
  $("foco-mic").addEventListener("click", () => foco.pressionarMicrofone());
  doc.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !tela.hidden) foco.fechar(); });
  doc.addEventListener("fullscreenchange", () => { if (!doc.fullscreenElement && !tela.hidden) foco.fechar(); });
  doc.addEventListener("visibilitychange", () => { if (!tela.hidden && !doc.hidden && !luz) pedirLuz(); });  // o Wake Lock cai quando a aba some

  // Sem ouvinte de microfone (voz ainda não ligada ao foco): usa "Conversar por voz" da conversa e espelha o estado dele.
  const voz = $("voz-modo");
  foco.aoFaltarMicrofone(() => voz?.click());
  if (voz && window.MutationObserver) new MutationObserver(() => { if (!foco.temMicrofone()) foco.definirMicrofone(voz.getAttribute("aria-pressed") === "true"); }).observe(voz, { attributes: true, attributeFilter: ["aria-pressed"] });

  // "O que a Jarvis diz": a última mensagem dela na conversa (texto simples).
  const msgs = $("mensagens");
  if (msgs && window.MutationObserver) {
    const ler = () => { const j = msgs.querySelectorAll(".msg.jarvis:not(.aviso)"), u = j[j.length - 1]; if (u) foco.definirFala(u.textContent.replace(/\s+/g, " ").trim()); };
    new MutationObserver(ler).observe(msgs, { childList: true, subtree: true, characterData: true });
  }
  return foco;
}
