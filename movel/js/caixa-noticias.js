// Caixa Últimas notícias (G1, BBC Brasil, Agência Brasil) e, com outro tipo, Notícias de tecnologia (Tecnoblog, Canaltech, Olhar Digital, Hacker News).
// Feeds pelo CORS direto, pelo Worker do dono (/rss) ou pela reserva rss2json. Título e resumo são texto de terceiros: só textContent; link só http/https.
import { criarCaixa, el, idade, linkSeguro } from "./caixa-base.js";
import { manchetes } from "./noticias-fontes.js";

const TITULOS = { gerais: "Últimas notícias", tecnologia: "Notícias de tecnologia" };
const LIMITE = 8;

function desenhar(d, corpo, ctx) {
  ctx.noticias.ultima = d.itens;  // "ler notícia 3" no chat lê o terceiro item desta lista
  const lista = el("ol", { className: "caixa-lista" });
  d.itens.forEach((n) => {
    const ouvir = el("button", { type: "button", textContent: "Ler para mim", className: "mini" });
    ouvir.setAttribute("aria-label", `Ler para mim o trecho: ${n.titulo}`);
    ouvir.addEventListener("click", () => ctx.ouvir?.(n, { completo: false }));
    const completo = el("button", { type: "button", textContent: "Artigo completo", className: "mini" });
    completo.setAttribute("aria-label", `Ouvir o artigo completo: ${n.titulo}`);
    completo.addEventListener("click", () => ctx.ouvir?.(n, { completo: true }));
    lista.append(el("li", {}, linkSeguro(n.titulo, n.link), el("small", { className: "nota", textContent: ` ${n.fonte}${n.quando ? " · " + idade(n.quando, ctx.agora?.()) : ""}` }),
      el("div", { className: "linha" }, ouvir, completo)));
  });
  corpo.append(lista);
  if (d.avisos?.length) corpo.append(el("p", { className: "nota", textContent: "Algumas fontes não carregaram. As que não têm acesso direto precisam do Worker do proxy (aba Cérebro)." }));
}

export function montarNoticias(container, ctx, tipo = "gerais") {
  return criarCaixa(container, ctx, {
    id: `noticias-${tipo}`, titulo: TITULOS[tipo] || TITULOS.gerais,
    async carregar() {
      const { itens, avisos } = await manchetes(tipo, { buscar: ctx.buscar, proxy: ctx.proxy, limite: LIMITE });
      if (!itens.length && avisos.length) throw new Error(avisos[0]);
      return { dados: { itens, avisos }, avisos: [] };
    },
    desenhar,
  });
}

export const montar = (container, ctx) => montarNoticias(container, ctx, "gerais");
