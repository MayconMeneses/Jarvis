// Monta o contexto compartilhado das caixas, do Radar e do "Ler para mim" (o `ctx` que cada caixa recebe em montar(container, ctx)).
// { memoria, buscar, proxy, leitor, radar, tradutor, noticias: { ultima }, ouvir(item, opcoes), avisar(texto), aoLeitura(fn) }.
// Os cérebros (`ia`) são os que o app já tem (aparelho ou nuvem do usuário): nenhum texto sai para um provedor que a pessoa não cadastrou.
import { Leitor } from "./leitor.js";
import { criarFala } from "./leitor-fala.js";
import { Tradutor } from "./leitor-traducao.js";
import { Proxy, baseDoProxy } from "./rede-proxy.js";
import { Radar } from "./radar.js";

// Item de notícia (artigo) -> o que o Leitor precisa. `completo` baixa o artigo pelo Worker; senão lê título + trecho do feed.
export const paraLeitor = (n, { completo = false, original = false, resumir = false } = {}) =>
  ({ titulo: String(n.titulo || ""), trecho: String(n.resumo || ""), url: completo ? String(n.link || "") : "", completo, idioma: n.idioma || "", original, resumir });

export function criarContexto({ memoria, nuvem, ia = null, buscar = (...a) => fetch(...a), avisar = () => {}, agora = () => new Date(), fala = criarFala() }) {
  const proxy = new Proxy({ base: () => baseDoProxy(nuvem), buscar });
  const tradutor = new Tradutor({ ia, buscar });
  const ouvintes = [];
  const ctx = { memoria, buscar, proxy, tradutor, avisar, noticias: { ultima: [] }, ultimoLido: null };
  ctx.leitor = new Leitor({
    fala, tradutor,
    baixar: async (url) => { const r = await proxy.ler(url); return { texto: r.texto, idioma: r.idioma }; },
    aoMudar: (estado) => ouvintes.forEach((fn) => { try { fn(estado); } catch { /* tela */ } }),
  });
  ctx.radar = new Radar({ memoria, buscar, proxy, ia, agora });
  ctx.aoLeitura = (fn) => ouvintes.push(fn);
  // Começa a ler um item. `depoisDaResposta`: dá tempo de a resposta do chat ser falada antes do artigo.
  ctx.ouvir = (item, opcoes = {}) => {
    ctx.ultimoLido = { item, opcoes };
    return ctx.leitor.iniciar(paraLeitor(item, opcoes), { atrasoMs: opcoes.depoisDaResposta ? 1200 : 0 });
  };
  ctx.ouvirTexto = (texto, opcoes = {}) => ctx.leitor.iniciar({ titulo: "", trecho: texto, url: "", completo: false, idioma: "pt", original: false, resumir: false }, { atrasoMs: opcoes.depoisDaResposta ? 1200 : 0 });
  return ctx;
}
