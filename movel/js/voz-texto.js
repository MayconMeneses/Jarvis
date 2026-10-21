// Texto que a Jarvis fala: limpeza, normalização pt-BR e divisão em frases (a 1ª sempre curta). Porte de jarvis/voice/texto.py.
import { limparMarcacao, normalizar } from "./voz-normalizar.js";

export const MAX_FALADO = 600;   // caracteres; o resto fica só na tela
export const PRIMEIRA_MAX = 90;  // a 1ª parte passa de ~90 caracteres? corta na primeira vírgula: o som começa antes

// Tira Markdown, código, links e emojis; encurta respostas longas; escreve números, horas, moedas e siglas por extenso.
export function limparParaFala(texto) {
  texto = limparMarcacao(texto).replace(/\s+/g, " ").trim();
  if (texto.length > MAX_FALADO) {
    const corte = texto.slice(0, MAX_FALADO), fim = Math.max(corte.lastIndexOf(". "), corte.lastIndexOf("! "), corte.lastIndexOf("? "));
    texto = (fim > 200 ? corte.slice(0, fim + 1) : corte) + " Os detalhes estão na janela.";
  }
  return normalizar(texto);
}

// Divide em frases, juntando as muito curtas (cada parte é uma fala).
export function dividirFrases(texto, minChars = 40) {
  const partes = [];
  for (const p of texto.split(/(?<=[.!?…])\s+/).map((x) => x.trim()).filter(Boolean)) {
    if (partes.length && partes[partes.length - 1].length < minChars) partes[partes.length - 1] += " " + p;
    else partes.push(p);
  }
  return partes;
}

// Se a 1ª frase for longa, sai só até a vírgula/ponto e vírgula: menos espera até o 1º som.
export function dividirParaFala(texto) {
  const partes = dividirFrases(texto);
  if (partes.length && partes[0].length > PRIMEIRA_MAX) {
    const m = [...partes[0].matchAll(/[,;:]\s/g)].map((x) => x.index + x[0].length).find((fim) => fim >= 12) || 0;
    if (m > 0 && m < partes[0].length - 15) partes.splice(0, 1, partes[0].slice(0, m).trim(), partes[0].slice(m).trim());
  }
  return partes;
}

// Silêncio depois da parte: ponto e interrogação respiram mais que vírgula.
export function pausaMs(parte) {
  return ({ ".": 220, "!": 240, "?": 260, "…": 280 })[parte.trimEnd().slice(-1)] ?? 90;
}
