// Números por extenso em português do Brasil (cardinais e ordinais). Porte de jarvis/voice/numeros.py: mesma lógica, mesmos casos.
export const UNID = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze", "treze", "catorze", "quinze",
  "dezesseis", "dezessete", "dezoito", "dezenove"];
const DEZ = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"];
const CENT = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"];
const ESCALAS = [["mil", "mil"], ["milhão", "milhões"], ["bilhão", "bilhões"], ["trilhão", "trilhões"]];
const ORD = { 1: "primeiro", 2: "segundo", 3: "terceiro", 4: "quarto", 5: "quinto", 6: "sexto", 7: "sétimo", 8: "oitavo", 9: "nono", 10: "décimo" };
export const LIMITE = 10 ** 15;  // acima disso (ou com zeros à esquerda) lê-se dígito a dígito

const feminino = (n) => ({ 1: "uma", 2: "duas" })[n] || UNID[n];

function ate999(n, fem) {
  if (n === 100) return "cem";
  const c = Math.floor(n / 100), resto = n % 100, partes = [];
  if (c) partes.push(fem && c >= 2 ? CENT[c].slice(0, -2) + "as" : CENT[c]);
  if (resto < 20) {
    if (resto || !c) partes.push(fem ? feminino(resto) : UNID[resto]);
  } else {
    const d = Math.floor(resto / 10), u = resto % 10;
    partes.push(DEZ[d] + (u ? " e " + (fem ? feminino(u) : UNID[u]) : ""));
  }
  return partes.join(" e ");
}

// 1234 -> "mil duzentos e trinta e quatro". Negativos levam "menos".
export function porExtenso(n, fem = false) {
  if (n < 0) return "menos " + porExtenso(-n, fem);
  if (n >= LIMITE) return [...String(n)].map((d) => UNID[+d]).join(" ");
  if (n < 1000) return ate999(n, fem);
  const grupos = [];
  while (n) { grupos.push(n % 1000); n = Math.floor(n / 1000); }
  const partes = [];
  let ultimo = 0;
  for (let i = grupos.length - 1; i >= 0; i--) {
    const g = grupos[i];
    if (!g) continue;
    ultimo = g;
    if (i === 0) partes.push(ate999(g, fem));
    else if (i === 1) partes.push(g === 1 ? "mil" : ate999(g, fem) + " mil");
    else { const [sing, plur] = ESCALAS[i - 1]; partes.push(g === 1 ? `um ${sing}` : `${ate999(g, false)} ${plur}`); }
  }
  // "mil e cem", "dois mil e trezentos"; sem "e" quando sobra centena composta ("mil cento e um")
  if (partes.length > 1 && (ultimo < 100 || ultimo % 100 === 0)) return partes.slice(0, -1).join(" ") + " e " + partes[partes.length - 1];
  return partes.join(" ");
}

export const digitoADigito = (texto) => [...texto].filter((c) => c >= "0" && c <= "9").map((d) => UNID[+d]).join(" ");

// 1 -> primeiro/primeira; acima de 10 lê o cardinal (forma comum na fala).
export function ordinal(n, fem = false) {
  if (ORD[n]) return fem ? ORD[n].slice(0, -1) + "a" : ORD[n];
  return porExtenso(n, fem);
}

// Dígitos -> extenso. Zero à esquerda ou número gigante (telefone, protocolo) vira dígito a dígito.
export function numero(texto, fem = false) {
  if ((texto.length > 1 && texto.startsWith("0")) || texto.length > 15) return digitoADigito(texto);
  return porExtenso(parseInt(texto, 10), fem);
}

// "3", "14" -> "três vírgula catorze"; zeros à esquerda da fração são lidos um a um.
export function decimal(inteira, fracao) {
  const resto = fracao.replace(/^0+/, ""), zeros = fracao.length - resto.length;
  const cauda = [...Array(zeros).fill("zero"), ...(resto ? [porExtenso(parseInt(resto, 10))] : [])].join(" ");
  return `${numero(inteira)} vírgula ${cauda}`;
}
