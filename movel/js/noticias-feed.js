// RSS 2.0 / Atom / RSS 1.0 (texto XML) -> lista de artigos. O XML vem da internet: é DADO de terceiros.
// Leitor tolerante em vez de DOMParser: um feed com um "&" solto ou uma tag torta faz o DOMParser devolver <parsererror> e perder tudo;
// aqui cada item é lido sozinho, entidades próprias (DOCTYPE/ENTITY) nunca são expandidas e dá para testar sem navegador.
// Artigo: { fonte, titulo, link, quando (epoch em SEGUNDOS, 0 = sem data), resumo, autor, categorias, notaFonte, tipoFonte }.
import { decodificar, limpar, linkValido } from "./radar-texto.js";

export const MAX_XML = 2_000_000;
export const MAX_ITENS = 100;

// Texto de um campo: CDATA fica como está; o resto tem as entidades XML decodificadas (depois `limpar` tira a marcação).
function conteudo(bruto) {
  const partes = String(bruto).split(/<!\[CDATA\[([\s\S]*?)\]\]>/);
  return partes.map((p, i) => (i % 2 ? p : decodificar(p))).join("");
}

function campo(bloco, ...nomes) {
  for (const nome of nomes) {
    const m = new RegExp(`<(?:[\\w.-]+:)?${nome}\\b[^>]*?(?:/>|>([\\s\\S]*?)</(?:[\\w.-]+:)?${nome}\\s*>)`, "i").exec(bloco);
    if (m && m[1] != null && m[1].trim()) return conteudo(m[1]).trim();
  }
  return "";
}

function atributo(attrs, nome) {
  const m = new RegExp(`${nome}\\s*=\\s*("([^"]*)"|'([^']*)')`, "i").exec(attrs);
  return m ? decodificar(m[2] ?? m[3]).trim() : "";
}

function link(bloco) {
  for (const m of bloco.matchAll(/<link\b([^>]*?)(?:\/>|>([\s\S]*?)<\/link\s*>)/gi)) {
    const href = atributo(m[1], "href"), rel = atributo(m[1], "rel") || "alternate";
    if (href && rel === "alternate") return href;
    const texto = conteudo(m[2] || "").trim();
    if (texto) return texto;
  }
  return "";
}

// RFC 822 (RSS), ISO 8601 (Atom, dc:date) -> epoch em segundos. Sem data válida: 0.
export function dataDoFeed(texto) {
  texto = String(texto || "").trim();
  if (!texto) return 0;
  const iso = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(texto) ? texto.replace(" ", "T") + "Z" : texto;  // sem fuso = UTC, como no PC
  const ms = Date.parse(iso);
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : 0;
}

function autor(bloco) {
  const a = /<author\b[^>]*>([\s\S]*?)<\/author\s*>/i.exec(bloco);
  if (a) return limpar(campo(a[1], "name") || conteudo(a[1]), 80);
  return limpar(campo(bloco, "creator"), 80);
}

// Corpo de cada <item>/<entry>, em tempo linear (um item sem fechamento não faz o resto do arquivo ser relido).
function* blocos(texto) {
  const baixo = texto.replace(/[A-Z]/g, (c) => c.toLowerCase()), abre = /<(item|entry)(?=[\s>/])/g;
  for (let m = abre.exec(baixo); m; m = abre.exec(baixo)) {
    const fimTag = baixo.indexOf(">", m.index), fecha = baixo.indexOf(`</${m[1]}`, m.index);
    if (fimTag < 0 || fecha < 0) return;
    if (fecha > fimTag) yield texto.slice(fimTag + 1, fecha);
    abre.lastIndex = fecha + 1;
  }
}

export function parse(xml, fonte, notaFonte = 5, tipoFonte = "imprensa") {
  const texto = String(xml || "").slice(0, MAX_XML).replace(/<!DOCTYPE[\s\S]*?(\]>|>)/i, "");
  const artigos = [];
  for (const bloco of blocos(texto)) {
    if (artigos.length >= MAX_ITENS) break;
    const titulo = limpar(campo(bloco, "title"), 200), endereco = link(bloco);
    if (!titulo || !linkValido(endereco)) continue;  // sem título ou com link que não é http(s): descartado
    const categorias = [...bloco.matchAll(/<category\b[^>]*>([\s\S]*?)<\/category\s*>/gi)].map((c) => limpar(conteudo(c[1]), 40)).filter(Boolean).slice(0, 5);
    artigos.push({ fonte, titulo, link: endereco.trim(), quando: dataDoFeed(campo(bloco, "pubDate", "published", "updated", "date")),
      resumo: limpar(campo(bloco, "description", "summary", "encoded", "content"), 300), autor: autor(bloco), categorias, notaFonte, tipoFonte });
  }
  return artigos;
}

// Reserva frágil (terceiro, pode dar 403): api.rss2json.com devolve JSON em vez de XML.
export function deRss2json(dados, fonte, notaFonte = 5, tipoFonte = "imprensa") {
  const itens = Array.isArray(dados?.items) ? dados.items : [];
  return itens.filter((i) => i && typeof i === "object").slice(0, MAX_ITENS).map((i) => ({ fonte, titulo: limpar(i.title, 200), link: String(i.link || "").trim(), quando: dataDoFeed(i.pubDate),
    resumo: limpar(i.description, 300), autor: "", categorias: [], notaFonte, tipoFonte })).filter((a) => a.titulo && linkValido(a.link));
}
