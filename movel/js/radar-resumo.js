// Resumo SEM IA: título limpo, lead e frases com número/data do próprio texto, rótulos de origem e "por que entrou".
// Porte de jarvis/radar/resumo.py. Nunca mais de 3 frases copiadas por item; sem IA não há manchete própria nem ângulo (omitido, não inventado).
import { suspeito } from "./radar-sanear.js";
import { semAcento } from "./radar-texto.js";

export const MAX_FRASES = 3;
export const MAX_FRASE = 240;
const SUFIXO = /\s+[-–—|]\s+[^-–—|]{2,40}$/;
const OPINIAO = /\/(opiniao|opinion|opinioes|coluna|colunas|colunistas|editorial|blog|artigo-de-opiniao)\//i;
const PAYWALL = /assine para|conteudo exclusivo|exclusivo para assinantes|ja e assinante|subscribe to (continue|read)|paywall|assinantes? (podem|tem acesso)/i;

// Tira o " - Veículo" do fim quando o título veio com ele.
export const manchete = (titulo, fonte) => (titulo.slice(-45).toLowerCase().includes(fonte.toLowerCase().slice(0, 6)) ? titulo.replace(SUFIXO, "").trim() : titulo.trim());

export function rotuloDe(item, paywall) {
  if (paywall) return "possível paywall";
  const a = item.artigo;
  if (OPINIAO.test(a.link) || a.categorias.some((c) => /opini|coluna/i.test(c))) return "opinião";
  return "não classificado";
}

export const pareceParede = (texto, resumoDoFeed) => (PAYWALL.test(semAcento(texto)) && texto.length < 1500) || (texto.length < 300 && resumoDoFeed.length >= 150);

// Frases de 40 a 320 caracteres que começam em maiúscula, número ou aspas (como websearch.sentences do PC).
export const frases = (texto) => {
  const achadas = texto.replace(/\n/g, " ").split(/(?<=[.!?])\s+(?=[A-ZÀ-Ú0-9"“])/).map((p) => p.trim()).filter((p) => p.length >= 40 && p.length <= 320);
  return achadas.length ? achadas : texto.trim().length >= 20 ? [texto.trim()] : [];
};
const curta = (f) => (f.length <= MAX_FRASE ? f : f.slice(0, MAX_FRASE).replace(/\s+\S*$/, "") + "…");

// Lead (até 2 frases) + a frase seguinte com mais números/datas. No máximo 3 no total.
export function escolherFrases(texto) {
  const todas = frases(texto), escolhidas = todas.slice(0, 2);
  const resto = todas.slice(2).filter((f) => /\d/.test(f));
  if (resto.length) escolhidas.push(resto.reduce((m, f) => ((f.match(/\d+/g) || []).length > (m.match(/\d+/g) || []).length ? f : m)));
  return escolhidas.slice(0, MAX_FRASES).map(curta);
}

export const porQueEntrou = (motivos) => "Entrou na lista porque " + motivos.filter((m) => !m.includes("clickbait")).join("; ") + ".";

// Preenche o item sem IA. Texto que tenta dar ordens (injeção) é marcado ⚠ e não é resumido.
export function resumir(item, textoPagina = "", paywall = false) {
  const a = item.artigo;
  item.manchete = manchete(a.titulo, a.fonte);
  item.porQue = porQueEntrou(item.motivos);
  item.rotulo = rotuloDe(item, paywall);
  const motivo = suspeito(`${a.titulo}\n${a.resumo}\n${textoPagina.slice(0, 2000)}`);
  if (motivo) { item.suspeito = motivo; item.linhas = []; return item; }
  const usarPagina = Boolean(textoPagina) && !paywall;
  item.origem = usarPagina ? "artigo" : "rss";
  item.palavras = usarPagina ? textoPagina.split(/\s+/).filter(Boolean).length : 0;
  item.linhas = escolherFrases(usarPagina ? textoPagina : a.resumo);
  item.textoFonte = (usarPagina ? textoPagina : a.resumo).slice(0, 3000);
  return item;
}

// Todo número e todo nome próprio de um texto gerado precisa existir no texto-fonte (barreira contra invenção).
export function fundamentado(saida, fonte) {
  const base = semAcento(fonte), solto = (t) => t.replace(/[.,]/g, ""), faltando = [];
  for (const numero of saida.match(/\d[\d.,]*\d|\d/g) || []) {
    if (!fonte.includes(numero.replace(/[.,]+$/, "")) && !solto(base).includes(solto(numero))) faltando.push(numero);
  }
  for (const frase of saida.split(/(?<=[.!?])\s+/)) {
    for (const nome of frase.match(/(?<=\s)[A-ZÀ-Ú][\p{L}\p{N}_]{2,}/gu) || []) if (!base.includes(semAcento(nome))) faltando.push(nome);
  }
  return [faltando.length === 0, faltando];
}
