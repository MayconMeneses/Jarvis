// De onde vêm as manchetes no celular: feeds RSS por (1) CORS direto (Agência Brasil), (2) Worker do dono (/rss), (3) reserva frágil rss2json.
// Um portal fora do ar nunca derruba os outros. Tudo que chega é texto de terceiros (títulos viram texto na tela, links só http/https).
import { deRss2json, parse } from "./noticias-feed.js";
import { ErroRede, buscarComLimite, ehDireto, textoLimitado } from "./rede-proxy.js";
import { semAcento } from "./radar-texto.js";

export const FEEDS = {
  gerais: [
    { nome: "G1", url: "https://g1.globo.com/rss/g1/", nota: 7, tipo: "imprensa" },
    { nome: "BBC Brasil", url: "https://feeds.bbci.co.uk/portuguese/rss.xml", nota: 8, tipo: "imprensa" },
    { nome: "Agência Brasil", url: "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml", nota: 7, tipo: "oficial" },
  ],
  tecnologia: [
    { nome: "Tecnoblog", url: "https://tecnoblog.net/feed/", nota: 7, tipo: "imprensa" },
    { nome: "Canaltech", url: "https://canaltech.com.br/rss/", nota: 6, tipo: "imprensa" },
    { nome: "Olhar Digital", url: "https://olhardigital.com.br/feed/", nota: 6, tipo: "imprensa" },
  ],
};
const GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419";
const RSS2JSON = "https://api.rss2json.com/v1/api.json?rss_url=";
export const TTL_ASSUNTO_MS = 45 * 60000;
const cacheAssunto = new Map();

async function viaDireta(fonte, buscar) {
  return parse(await textoLimitado(await buscarComLimite(buscar, fonte.url, {}, 12000)), fonte.nome, fonte.nota, fonte.tipo);
}

async function viaReserva(fonte, buscar) {
  const r = await buscarComLimite(buscar, RSS2JSON + encodeURIComponent(fonte.url), {}, 12000);
  if (!r.ok) throw new ErroRede("http", `HTTP ${r.status}`);
  return deRss2json(await r.json(), fonte.nome, fonte.nota, fonte.tipo);
}

// { artigos, via: "direto" | "worker" | "reserva" }. Levanta ErroRede com o motivo curto se nada funcionou. Cada artigo leva o idioma da fonte.
export async function carregarFeed(fonte, ctx) {
  const r = await carregarBruto(fonte, ctx);
  r.artigos.forEach((a) => { a.idioma = fonte.idioma || ""; });
  return r;
}

async function carregarBruto(fonte, { buscar, proxy }) {
  const motivos = [];
  if (ehDireto(fonte.url)) {
    try { return { artigos: await viaDireta(fonte, buscar), via: "direto" }; } catch (e) { motivos.push(e.message); }
  } else if (proxy && await proxy.temRota("rss")) {
    try { return { artigos: parse(await proxy.rss(fonte.url), fonte.nome, fonte.nota, fonte.tipo), via: "worker" }; } catch (e) { motivos.push(`Worker: ${e.message}`); }
  } else motivos.push("sem Worker");
  try { return { artigos: await viaReserva(fonte, buscar), via: "reserva" }; } catch (e) { motivos.push(`reserva: ${e.message}`); }
  throw new ErroRede("feed", motivos.join("; "));
}

// Hacker News (API pública com CORS): manchetes de tecnologia do mundo, em inglês.
export async function hackerNews(buscar, quantas = 3) {
  const json = async (url) => { const r = await buscarComLimite(buscar, url, {}, 10000); if (!r.ok) throw new ErroRede("http", `HTTP ${r.status}`); return r.json(); };
  const ids = (await json("https://hacker-news.firebaseio.com/v0/topstories.json")).slice(0, quantas);
  const itens = await Promise.all(ids.map((id) => json(`https://hacker-news.firebaseio.com/v0/item/${Number(id)}.json`)));
  return itens.filter((i) => i && i.title).map((i) => ({ fonte: "Hacker News", titulo: String(i.title).slice(0, 200), quando: Number(i.time) || 0, resumo: "", autor: "", categorias: [],
    link: /^https?:\/\//.test(String(i.url)) ? i.url : `https://news.ycombinator.com/item?id=${Number(i.id)}`, notaFonte: 7, tipoFonte: "comunidade", idioma: "en" }));
}

// Manchetes mais recentes alternando os veículos para não repetir um só portal. { itens, avisos }.
export async function manchetes(tipo = "gerais", { buscar, proxy = null, limite = 5, fontes = null } = {}) {
  const porFonte = {}, avisos = [];
  const lista = fontes || FEEDS[tipo] || FEEDS.gerais;
  const tarefas = lista.map(async (f) => {
    try { porFonte[f.nome] = (await carregarFeed(f, { buscar, proxy })).artigos.sort((a, b) => b.quando - a.quando); } catch (e) { avisos.push(`${f.nome}: ${e.message}`); }
  });
  if (tipo === "tecnologia" && !fontes) tarefas.push(hackerNews(buscar).then((a) => { porFonte["Hacker News"] = a; }).catch((e) => { avisos.push(`Hacker News: ${e.message}`); }));
  await Promise.all(tarefas);
  const nomes = [...lista.map((f) => f.nome), "Hacker News"].filter((n) => porFonte[n]);
  const itens = [], vistos = new Set();
  while (itens.length < limite && nomes.some((n) => porFonte[n].length)) {
    for (const nome of nomes) {
      const a = porFonte[nome].shift();
      const chave = a && semAcento(a.titulo).slice(0, 60);
      if (a && itens.length < limite && !vistos.has(chave)) { vistos.add(chave); itens.push(a); }
    }
  }
  return { itens, avisos };
}

// O Google News entrega "Título - Fonte".
export function separarFonte(titulo) {
  const i = titulo.lastIndexOf(" - ");
  return i > 0 && titulo.length - i - 3 <= 40 ? [titulo.slice(0, i), titulo.slice(i + 3)] : [titulo, "Google News"];
}

// Manchetes de um assunto livre ("IA", "dólar"). Só com o Worker (o Google News não tem CORS). Cache de 45 minutos por assunto.
export async function porAssunto(assunto, { proxy, limite = 5, agora = () => Date.now() }) {
  assunto = String(assunto).replace(/\s+/g, " ").trim().slice(0, 80);
  if (!assunto) return { itens: [], avisos: ["diga o assunto"] };
  const chave = assunto.toLowerCase(), guardado = cacheAssunto.get(chave);
  if (guardado && agora() - guardado.quando < TTL_ASSUNTO_MS) return { itens: guardado.itens.slice(0, limite), avisos: [] };
  if (!proxy || !(await proxy.temRota("rss"))) return { itens: [], avisos: ["sem Worker"] };
  try {
    const artigos = parse(await proxy.rss(GOOGLE_NEWS.replace("{q}", encodeURIComponent(assunto))), "Google News", 5, "imprensa").sort((a, b) => b.quando - a.quando);
    const vistos = new Set(), itens = [];
    for (const a of artigos) {
      const [titulo, fonte] = separarFonte(a.titulo), k = semAcento(titulo).slice(0, 60);
      if (!vistos.has(k)) { vistos.add(k); itens.push({ ...a, titulo, fonte }); }
    }
    cacheAssunto.set(chave, { quando: agora(), itens });
    return { itens: itens.slice(0, limite), avisos: [] };
  } catch (e) { return { itens: [], avisos: [e.message] }; }
}
