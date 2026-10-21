// Deduplicação: o mesmo link com enfeites e a mesma notícia em vários veículos viram um item só. Porte de jarvis/radar/dedup.py.
import { semAcento } from "./radar-texto.js";

const RASTREIO = /^(utm_.*|fbclid|gclid|mc_.*|ref|ref_src|igshid|cmpid|ncid|source|xtor)$/i;
const STOP = new Set(`a o as os um uma uns umas de da do das dos em na no nas nos para por pra com sem e ou que se
ao aos à às é são foi ser após apos sobre entre mais menos já não the of and to in is for on at by`.split(/\s+/));
export const LIMIAR_PARECIDO = 0.6;  // Jaccard entre as palavras de dois títulos

// Tira rastreio (utm_*, fbclid...), #fragmento, www., /amp e a barra final; sempre https.
export function normalizarUrl(url) {
  let u;
  try { u = new URL(String(url).trim()); } catch { return String(url).trim(); }
  const consulta = [...u.searchParams].filter(([k, v]) => v !== "" && !RASTREIO.test(k)).sort((a, b) => (a[0] === b[0] ? (a[1] < b[1] ? -1 : 1) : a[0] < b[0] ? -1 : 1));
  const caminho = u.pathname.replace(/\/amp\/?$/, "").replace(/\/+$/, "");
  return `https://${u.host.replace(/^www\./, "")}${caminho}${consulta.length ? "?" + new URLSearchParams(consulta) : ""}`;
}

export const palavras = (titulo) => (semAcento(titulo).match(/[a-z0-9]{3,}/g) || []).filter((w) => !STOP.has(w));

function hash(texto) {  // cyrb53: identidade estável e curta (não é segurança)
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
  for (let i = 0; i < texto.length; i++) {
    const c = texto.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 2654435761); h2 = Math.imul(h2 ^ c, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16).padStart(14, "0");
}
export const idDoArtigo = (a) => hash(normalizarUrl(a.link) + "|" + palavras(a.titulo).join(" "));

export function parecidos(a, b, limiar = LIMIAR_PARECIDO) {
  const x = new Set(palavras(a)), y = new Set(palavras(b));
  if (!x.size || !y.size) return false;
  let dentro = 0;
  for (const p of x) if (y.has(p)) dentro++;
  return dentro / (x.size + y.size - dentro) >= limiar;
}

// Agrupa links iguais e títulos parecidos. Devolve [representante, [outros veículos]].
// O representante é o de maior nota de fonte (empate: o mais recente). Veículos repetidos aparecem uma vez.
export function agrupar(artigos) {
  const ordem = [...artigos].sort((a, b) => b.notaFonte - a.notaFonte || b.quando - a.quando);
  const grupos = [];
  for (const artigo of ordem) {
    const grupo = grupos.find(([p]) => normalizarUrl(p.link) === normalizarUrl(artigo.link) || parecidos(p.titulo, artigo.titulo));
    if (!grupo) grupos.push([artigo, []]);
    else if (artigo.fonte !== grupo[0].fonte && !grupo[1].includes(artigo.fonte)) grupo[1].push(artigo.fonte);
  }
  return grupos;
}
