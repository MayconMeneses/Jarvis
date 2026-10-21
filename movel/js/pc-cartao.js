// Peças comuns dos cartões do painel "PC": cada cartão (pc-vitais.js etc.) exporta montar(container, ctx) e devolve { id, titulo, atualizar }.
// ctx = { pc } (PcPareado). Tudo usa textContent: o que vem do PC é texto de terceiros.
import { OFFLINE } from "./pc-pareado.js";

export const el = (tag, props = {}, ...filhos) => { const n = Object.assign(document.createElement(tag), props); n.append(...filhos); return n; };
export const hora = (d = new Date()) => d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

export function criarCartao(container, { id, titulo }) {
  const corpo = el("div", { className: "msg jarvis", id: `${id}-corpo` }), rodape = el("p", { className: "nota", id: `${id}-rodape`, role: "status" });
  const raiz = el("section", { id }, el("h3", { textContent: titulo }), corpo, rodape);
  container.append(raiz);
  return { raiz, corpo, rodape };
}

export function linhas(alvo, texto) {
  for (const l of String(texto).split("\n")) alvo.append(el("p", { textContent: l.replace(/\*\*/g, "") }));
}

export function barra(alvo, rotulo, valor) {
  alvo.append(el("label", { textContent: `${rotulo}: ${valor}%` }), el("progress", { max: 100, value: valor, "aria-label": rotulo }));
}

// Lê a rota e desenha. Sem PC / offline sem cópia: só o aviso amigável. Offline com cópia: a cópia, datada.
export async function carregarCartao(cartao, ctx, rota, desenhar) {
  let r;
  try { r = await ctx.pc.obter(rota); } catch { r = { ok: false, erro: OFFLINE }; }
  cartao.corpo.replaceChildren();
  if (!r.ok) {
    cartao.corpo.append(el("p", { textContent: r.erro || OFFLINE }));
    cartao.rodape.textContent = "";
    return r;
  }
  try { desenhar(cartao.corpo, r.dados, { ...r, doCache: false }); } catch { cartao.corpo.append(el("p", { textContent: "Não consegui mostrar esta leitura." })); }
  cartao.rodape.textContent = r.doCache ? `${r.erro || OFFLINE} Mostrando a cópia de ${new Date(r.quando).toLocaleString("pt-BR")}.` : `Atualizado às ${hora()}.`;
  return r;
}

export function modulo(container, ctx, { id, titulo, rota, desenhar }) {
  const cartao = criarCartao(container, { id, titulo });
  return { id, titulo, cartao, atualizar: () => carregarCartao(cartao, ctx, rota, desenhar) };
}
