// Texto escrito -> texto para a voz do boletim (dinheiro, porcentagem, datas, siglas). Porte de jarvis/radar/numeros_pt.py.
// Nunca sobra URL, Markdown, emoji, colchete, hashtag nem a palavra "bullet".
import { MESES } from "./voz-normalizar.js";
import { UNID, digitoADigito, porExtenso } from "./voz-numeros.js";

const PRONUNCIAVEIS = new Set(["PIX", "ONU", "NASA", "OPEP", "BRICS", "SUS", "FIFA", "UNESCO", "OTAN", "UOL", "ENEM", "PROCON"]);
const EMOJI = /[\u{1F000}-\u{1FAFF}☀-➿️‍]/gu;
const B = "(?<![\\p{L}\\p{N}_])", E = "(?![\\p{L}\\p{N}_])";
const inteiro = (t) => parseInt(t.replace(/\./g, ""), 10);
const ext = (t) => (t.replace(/\./g, "").length > 15 ? digitoADigito(t) : porExtenso(inteiro(t)));

function decimalFalado(i, f) {
  const parte = ext(i) + " vírgula ";
  return f.startsWith("0") || f.length > 2 ? parte + [...f].map((d) => UNID[+d]).join(" ") : parte + porExtenso(parseInt(f, 10));
}
const numero = (_, i, f) => (f ? decimalFalado(i, f) : ext(i));

function dinheiro(_, valor, escala) {
  escala = (escala || "").trim().toLowerCase();
  const [i, f = ""] = valor.split(",");
  if (escala) return `${f ? decimalFalado(i, f) : ext(i)} ${escala} de reais`;
  const reais = inteiro(i);
  let texto = `${porExtenso(reais)} ${reais === 1 ? "real" : "reais"}`;
  if (f && parseInt(f, 10) > 0) {
    const c = parseInt((f + "0").slice(0, 2), 10);
    texto += ` e ${porExtenso(c)} ${c === 1 ? "centavo" : "centavos"}`;
  }
  return texto;
}
const sigla = (s) => (PRONUNCIAVEIS.has(s) || s.length > 5 ? s : [...s.toLowerCase()].join("-"));

export function falarTexto(texto) {
  let t = texto.replace(/https?:\/\/\S+|www\.\S+/g, " ").replace(EMOJI, " ");
  t = t.replace(/\[[^\]]*\]|\([^)]*https?[^)]*\)/g, " ");
  t = t.replace(/[*_`#>|~]+|^\s*[-•]\s+/gm, " ").replace(/\bbullets?\b/gi, " ");
  t = t.replace(new RegExp(`R\\$\\s*(\\d[\\d.]*(?:,\\d+)?)(\\s*(?:mil|milh[ãa]o|milh[õo]es|bilh[ãa]o|bilh[õo]es|trilh[ãa]o|trilh[õo]es))?${E}`, "giu"), dinheiro);
  t = t.replace(/(\d[\d.]*)(?:,(\d+))?\s*%/g, (_, i, f) => numero(_, i, f) + " por cento");
  t = t.replace(/\b(\d{1,2})\/(\d{1,2})\b/g, (todo, d, m) => (+m >= 1 && +m <= 12 && +d >= 1 && +d <= 31 ? `${porExtenso(+d)} de ${MESES[+m - 1]}` : todo));
  t = t.replace(new RegExp(`${B}(\\d{1,2})º${E}`, "gu"), (_, n) => (n === "1" ? "primeiro" : porExtenso(+n)));
  t = t.replace(new RegExp(`${B}(\\d{1,3}(?:\\.\\d{3})+|\\d+)(?:,(\\d+))?${E}`, "gu"), numero);
  t = t.replace(new RegExp(`${B}[A-ZÀ-Ú]{2,5}${E}`, "gu"), sigla);
  return t.replace(/\s+/g, " ").trim();
}
