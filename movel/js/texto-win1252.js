// Windows-1252 EXPLÍCITO, igual em qualquer motor. O TextDecoder("windows-1252") não é confiável: em alguns Node/ICU
// (ex.: Node 20 no Linux) ele age como Latin-1 e deixa os bytes 0x80-0x9F como controles (• vira \x95).
// Bytes 0x81, 0x8D, 0x8F, 0x90 e 0x9D não têm caractere: viram U+FFFD (mesma regra do padrão WHATWG usa U+0081 etc.; aqui preferimos o aviso visível).
const ALTO = "€\uFFFD‚ƒ„…†‡ˆ‰Š‹Œ\uFFFDŽ\uFFFD\uFFFD‘’“”•–—˜™š›œ\uFFFDžŸ";

export function decodificarWin1252(bytes) {
  let saida = "";
  for (let i = 0; i < bytes.length; i += 4096) {
    const lote = Array.from(bytes.subarray(i, i + 4096), (b) => (b >= 0x80 && b <= 0x9f ? ALTO[b - 0x80] : String.fromCharCode(b)));
    saida += lote.join("");
  }
  return saida;
}

// Caminho inverso: caractere -> byte WinAnsi; null se não existir (controles, emoji, letras fora da tabela).
export function byteWin1252(ch) {
  const c = ch.codePointAt(0);
  if ((c >= 0x20 && c < 0x7f) || (c >= 0xa0 && c <= 0xff)) return c;
  if (c < 0x80) return null;  // controles não vão para o PDF
  const i = ALTO.indexOf(ch);
  return i >= 0 && ch !== "\uFFFD" ? 0x80 + i : null;
}
