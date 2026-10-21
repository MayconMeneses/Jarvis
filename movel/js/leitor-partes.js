// Texto -> partes curtas para a fala (parar corta no máximo uma parte) e resumo barato sem IA. Porte de jarvis/info/leitor.py.
export const PARTE_MAX = 350;   // caracteres por fala
export const RESUMO_MAX = 900;
export const TEXTO_MAX = 6000;

// Partes de até `limite` caracteres, cortando em fim de frase (ou em espaço, se a frase for enorme).
export function partes(texto, limite = PARTE_MAX) {
  const saida = [];
  for (const bloco of String(texto).split(/\n+/)) {
    let atual = "";
    for (let frase of bloco.trim().split(/(?<=[.!?…])\s+/)) {
      while (frase.length > limite) {
        const achado = frase.lastIndexOf(" ", limite - 1), corte = achado > 0 ? achado : limite;
        if (atual) { saida.push(atual); atual = ""; }
        saida.push(frase.slice(0, corte).trim());
        frase = frase.slice(corte).trim();
      }
      if (atual && atual.length + 1 + frase.length > limite) { saida.push(atual); atual = ""; }
      atual = `${atual} ${frase}`.trim();
    }
    if (atual) saida.push(atual);
  }
  return saida.filter(Boolean);
}

// As primeiras frases até o limite (sem IA).
export function resumir(texto, limite = RESUMO_MAX) {
  texto = String(texto).replace(/\s+/g, " ").trim();
  if (texto.length <= limite) return texto;
  const corte = texto.slice(0, limite), fim = Math.max(corte.lastIndexOf(". "), corte.lastIndexOf("! "), corte.lastIndexOf("? "));
  return fim > Math.floor(limite / 3) ? corte.slice(0, fim + 1) : corte.replace(/\s+\S*$/, "") + "…";
}
