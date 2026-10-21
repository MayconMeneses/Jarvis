// Molde das caixas (Clima, Vagas, Notícias, Notícias de tecnologia): estados carregando / vazio / erro / ok, cópia guardada, atualização a cada ~15 min.
// Cada caixa é um módulo com montar(container, ctx). Tudo que vem da internet entra por textContent; links só http/https.
// ctx = { memoria, buscar, proxy, leitor, radar, noticias: { ultima }, avisar(texto), agora?(), agendar?(fn, ms) -> cancelar }.
import { linkValido } from "./radar-texto.js";

export const QUINZE_MIN = 15 * 60000;

export const el = (tag, props = {}, ...filhos) => { const n = Object.assign(document.createElement(tag), props); n.append(...filhos); return n; };

// Link seguro: só http/https, abre fora do app, sem enviar o endereço de origem. Sem link válido vira texto simples.
export function linkSeguro(texto, url, props = {}) {
  if (!linkValido(url)) return el("span", { textContent: texto, ...props });
  const a = el("a", { textContent: texto, href: url, target: "_blank", rel: "noopener noreferrer", ...props });
  return a;
}

export const horaCurta = (ms) => new Date(ms).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

// Idade curta em português a partir de epoch em SEGUNDOS ("há 5 min", "há 3 h", "há 2 d"); vazio se não há data.
export function idade(segundos, agoraMs = Date.now()) {
  if (!segundos) return "";
  const min = Math.max(0, Math.round((agoraMs / 1000 - segundos) / 60));
  return min < 1 ? "agora" : min < 60 ? `há ${min} min` : min < 1440 ? `há ${Math.round(min / 60)} h` : `há ${Math.round(min / 1440)} d`;
}

/**
 * Cria a caixa e a põe em `container`. `carregar(ctx)` devolve { dados, vazio?, avisos? } ou levanta Error;
 * `desenhar(dados, corpo, ctx)` monta nós do DOM, nunca HTML em texto. Devolve { atualizar(forcar), estado(), parar(), el }.
 */
export function criarCaixa(container, ctx, { id, titulo, carregar, desenhar, vazio = "Nada por aqui agora.", ttlMs = QUINZE_MIN, extra = null }) {
  const agora = ctx.agora || (() => Date.now());
  const estadoEl = el("p", { className: "nota caixa-estado", role: "status" });
  const corpo = el("div", { className: "caixa-corpo" });
  const botao = el("button", { type: "button", textContent: "Atualizar", className: "caixa-atualizar" });
  botao.setAttribute("aria-label", `Atualizar ${titulo}`);
  const raiz = el("section", { className: "caixa", id: `caixa-${id}` }, el("div", { className: "linha" }, el("h3", { textContent: titulo }), botao), estadoEl, corpo);
  raiz.setAttribute("aria-label", titulo);
  raiz.dataset.estado = "carregando";
  container.append(raiz);
  if (extra) raiz.append(extra(() => atualizar(true)));

  let ultimo = 0, emCurso = null, vivo = true, cancelar = null;
  const marcar = (estado, texto) => { raiz.dataset.estado = estado; estadoEl.textContent = texto; };

  async function copia() { try { return await ctx.memoria.meta(`cx:${id}`); } catch { return null; } }
  async function guardar(dados) { try { await ctx.memoria.definirMeta(`cx:${id}`, { quando: agora(), dados }); } catch { /* sem espaço: segue sem cópia */ } }

  function mostrar(dados, vazioAgora, quando, aviso = "") {
    corpo.replaceChildren();
    if (vazioAgora) { marcar("vazio", typeof vazioAgora === "string" ? vazioAgora : vazio); return; }
    desenhar(dados, corpo, ctx);
    marcar("ok", `${aviso || "Atualizado"} às ${horaCurta(quando)}.`);
  }

  async function executar() {
    marcar("carregando", "Carregando…");
    botao.disabled = true;
    try {
      const r = await carregar(ctx);
      ultimo = agora();
      if (!r || r.vazio || (Array.isArray(r.dados?.itens) && !r.dados.itens.length)) mostrar(null, r?.vazio || true, ultimo);
      else { mostrar(r.dados, false, ultimo); await guardar(r.dados); }
      if (r?.avisos?.length) estadoEl.textContent += ` Fora do ar: ${r.avisos.join("; ")}.`;
    } catch (e) {
      const c = await copia();
      if (c?.dados) { mostrar(c.dados, false, c.quando, "Sem conexão agora; cópia guardada"); raiz.dataset.estado = "erro"; }
      else marcar("erro", `Não consegui carregar (${e.message}). Toque em Atualizar para tentar de novo.`);
    } finally { botao.disabled = false; emCurso = null; }
  }

  // Recarrega se passou do prazo (ou se `forcar`). Chamadas ao mesmo tempo viram uma só.
  function atualizar(forcar = false) {
    if (!vivo) return Promise.resolve();
    if (!forcar && ultimo && agora() - ultimo < ttlMs) return Promise.resolve();
    return (emCurso ||= executar());
  }

  botao.addEventListener("click", () => atualizar(true));
  const aoVoltar = () => { if (!document.hidden) atualizar(); };
  document.addEventListener?.("visibilitychange", aoVoltar);
  cancelar = (ctx.agendar || ((fn, ms) => { const t = setInterval(fn, ms); return () => clearInterval(t); }))(() => { if (!document.hidden) atualizar(); }, ttlMs);

  // Mostra a cópia na hora (se houver) e depois busca a versão nova.
  const inicio = copia().then((c) => { if (c?.dados && vivo) { ultimo = 0; mostrar(c.dados, false, c.quando, "Cópia guardada"); } }).then(() => atualizar(true));

  return { el: raiz, atualizar, estado: () => raiz.dataset.estado, pronto: inicio,
    parar() { vivo = false; cancelar?.(); document.removeEventListener?.("visibilitychange", aoVoltar); } };
}
