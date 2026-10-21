// Indicador de microfone: SEMPRE visível enquanto a escuta está ativa, com botão para desligar com um toque. Cria o próprio elemento e o
// próprio estilo (não depende do index.html nem dos CSS da casca). Texto sempre por textContent.
const TEXTOS = {
  aguardando: "Microfone ligado: diga “Jarvis…”",
  ouvindo: "Ouvindo…",
  processando: "Pensando…",
  falando: "Falando…",
};
const MOTIVOS = {
  permissao: "O microfone está bloqueado. Libere em Ajustes do iPhone > Safari > Microfone (ou toque em Permitir) e ligue de novo.",
  microfone: "Não encontrei um microfone disponível. Escuta desligada.",
  idioma: "O reconhecimento de fala não aceita português neste aparelho. Escuta desligada.",
  instavel: "O reconhecimento de fala ficou instável e eu desliguei a escuta. Toque para ligar de novo.",
  "sem-suporte": "Este navegador não tem reconhecimento de fala (precisa de HTTPS e do Safari/Chrome atualizado).",
};
const CSS = `#escuta-indicador{position:fixed;left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom,0px));z-index:50;display:flex;align-items:center;gap:10px;
max-width:520px;margin:0 auto;padding:10px 12px;border-radius:14px;background:rgba(20,22,28,.94);color:#fff;font:600 15px/1.3 system-ui,sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.35)}
#escuta-indicador[hidden]{display:none}
#escuta-indicador .ponto{flex:none;width:12px;height:12px;border-radius:50%;background:#ff9f0a;box-shadow:0 0 0 0 rgba(255,159,10,.6)}
#escuta-indicador[data-estado=ouvindo] .ponto{background:#30d158;animation:escuta-pulso 1.1s infinite}
#escuta-indicador[data-estado=processando] .ponto{background:#64d2ff}
#escuta-indicador[data-estado=falando] .ponto{background:#bf5af2}
#escuta-indicador .texto{flex:1;min-width:0}
#escuta-indicador button{flex:none;min-height:44px;min-width:44px;padding:0 14px;border-radius:10px;border:1px solid rgba(255,255,255,.35);background:transparent;color:inherit;font:inherit}
@keyframes escuta-pulso{70%{box-shadow:0 0 0 9px rgba(48,209,88,0)}100%{box-shadow:0 0 0 0 rgba(48,209,88,0)}}
@media (prefers-reduced-motion:reduce){#escuta-indicador .ponto{animation:none!important}}`;

// `escuta`: EscutaContinua (aoMudar/estado/parar). `aoFalar(msg)` opcional para o aviso anunciado também na conversa.
export function montarIndicador(escuta, { doc = globalThis.document, aoFalar = null } = {}) {
  if (!doc?.createElement) return null;
  const caixa = doc.createElement("div"), ponto = doc.createElement("span"), texto = doc.createElement("span"), botao = doc.createElement("button");
  caixa.id = "escuta-indicador"; caixa.hidden = true;
  caixa.setAttribute("role", "status"); caixa.setAttribute("aria-live", "polite");
  ponto.className = "ponto"; ponto.setAttribute("aria-hidden", "true"); texto.className = "texto";
  botao.type = "button";
  caixa.append(ponto, texto, botao);
  let avisoAte = null;
  const mostrarAviso = (msg) => {
    caixa.hidden = false; caixa.dataset.estado = "aviso"; texto.textContent = msg; botao.textContent = "Fechar";
    botao.setAttribute("aria-label", "Fechar o aviso"); botao.onclick = () => { caixa.hidden = true; };
    clearTimeout(avisoAte); avisoAte = setTimeout(() => { caixa.hidden = true; }, 15000);
    aoFalar?.(msg);
  };
  escuta.aoMudar((estado, info = {}) => {
    if (estado === "desligado") {
      const msg = MOTIVOS[info.motivo];
      if (msg) mostrarAviso(msg); else if (caixa.dataset.estado !== "aviso") caixa.hidden = true;
      return;
    }
    if (info.evento === "sem-suporte") { mostrarAviso(MOTIVOS["sem-suporte"]); return; }
    clearTimeout(avisoAte);
    caixa.hidden = false; caixa.dataset.estado = estado; texto.textContent = TEXTOS[estado] || estado;
    botao.textContent = "Desligar"; botao.setAttribute("aria-label", "Desligar o microfone");
    botao.onclick = () => escuta.parar();
  });
  const estilo = doc.createElement("style");
  estilo.textContent = CSS;
  (doc.head || doc.body)?.append(estilo);
  doc.body?.append(caixa);
  return caixa;
}
