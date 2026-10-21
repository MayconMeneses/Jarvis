// Normalização pt-BR do texto antes da fala: números, horas, datas, moedas, siglas, unidades e símbolos.
// Porte de jarvis/voice/normalizar.py (funções puras). A ordem importa: formas estruturadas primeiro, números soltos por último.
// No JavaScript \w e \b só enxergam ASCII; por isso as bordas usam letras e números Unicode (B = "não vem depois de letra", E = "não vem antes de letra").
import { decimal, digitoADigito, numero, ordinal, porExtenso } from "./voz-numeros.js";

export const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const W = "[\\p{L}\\p{N}_]", B = "(?<![\\p{L}\\p{N}_])", E = "(?![\\p{L}\\p{N}_])";
const NUM = "\\d{1,3}(?:\\.\\d{3})+|\\d+";  // 1.234.567 ou 1234

export const SIGLAS = {
  PC: "pê cê", CPU: "cê pê u", GPU: "gê pê u", RAM: "rám", SSD: "ésse ésse dê", HD: "agá dê", USB: "u ésse bê", IA: "i á", API: "á pê i", URL: "u érre éle",
  PDF: "pê dê éfe", CPF: "cê pê éfe", CNPJ: "cê ene pê jota", SMS: "ésse eme ésse", GPS: "gê pê ésse", TV: "tê vê", PIX: "pix", LGPD: "éle gê pê dê",
  MCP: "ême cê pê", TTS: "tê tê ésse", HTML: "agá tê eme éle", CSS: "cê ésse ésse", SQL: "ésse quê éle", LLM: "éle éle eme", OK: "ôquei",
  "WI-FI": "uaifai", WIFI: "uaifai", ID: "i dê", "E-MAIL": "i-meio",
};
export const UNIDADES = {  // sigla -> [singular, plural]
  GB: ["gigabyte", "gigabytes"], MB: ["megabyte", "megabytes"], KB: ["quilobyte", "quilobytes"], TB: ["terabyte", "terabytes"], GHZ: ["gigahertz", "gigahertz"],
  MHZ: ["megahertz", "megahertz"], MS: ["milissegundo", "milissegundos"], KM: ["quilômetro", "quilômetros"], KG: ["quilo", "quilos"], MIN: ["minuto", "minutos"],
  SEG: ["segundo", "segundos"], H: ["hora", "horas"], M: ["metro", "metros"], CM: ["centímetro", "centímetros"], MM: ["milímetro", "milímetros"],
  G: ["grama", "gramas"], W: ["watt", "watts"],
};
const ABREVIACOES = [
  [`${B}Dr\\.`, "doutor"], [`${B}Dra\\.`, "doutora"], [`${B}Sr\\.`, "senhor"], [`${B}Sra\\.`, "senhora"], [`${B}Prof\\.`, "professor"],
  [`${B}Profa\\.`, "professora"], [`${B}Av\\.`, "avenida"], [`${B}Tel\\.`, "telefone"], [`${B}pág\\.`, "página"], [`${B}obs\\.`, "observação"],
  [`${B}p\\. ?ex\\.`, "por exemplo"], [`${B}ex\\.`, "por exemplo"], [`${B}nº\\s*`, "número "], [`${B}n\\.º\\s*`, "número "], [`${B}vs\\.?`, "versus"],
  [`${B}porcent\\.`, "por cento"], [`${B}apt\\.`, "apartamento"], [`${B}pq${E}\\.?`, "porque"], [`${B}vc${E}`, "você"], [`${B}vcs${E}`, "vocês"],
].map(([p, t]) => [new RegExp(p, "giu"), t]);
const EMOJI = /[\u{1F000}-\u{1FAFF}\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u20E3\u2190-\u21FF]+/gu;
const inteiro = (t) => parseInt(t.replace(/\./g, ""), 10);
const re = (padrao, flags = "gu") => new RegExp(padrao, flags);

function moeda(_, v, c, e) {
  const reais = inteiro(v), centavos = parseInt((c || "0").padEnd(2, "0").slice(0, 2), 10), escala = (e || "").toLowerCase();
  if (escala) return `${porExtenso(reais)} ${escala} de reais`;
  const partes = [];
  if (reais || !centavos) partes.push(`${porExtenso(reais)} ${reais === 1 ? "real" : "reais"}`);
  if (centavos) partes.push(`${porExtenso(centavos)} ${centavos === 1 ? "centavo" : "centavos"}`);
  return partes.join(" e ");
}
const horaExtenso = (h) => (h === 1 || h === 2 ? porExtenso(h, true) : porExtenso(h));
function hora(todo, hh, mm) {
  const h = parseInt(hh, 10), mi = parseInt(mm || "0", 10);
  if (h > 23 || mi > 59) return todo;
  if (h === 0 && mi === 0) return "meia-noite";
  if (h === 12 && mi === 0) return "meio-dia";
  if (mi === 0) return `${horaExtenso(h)} ${h === 1 ? "hora" : "horas"}`;
  return `${horaExtenso(h)} e ${porExtenso(mi)}`;
}
function data(todo, d, m, ano) {
  const dia = +d, mes = +m;
  if (!(dia >= 1 && dia <= 31 && mes >= 1 && mes <= 12)) return todo;
  let texto = `${dia === 1 ? "primeiro" : porExtenso(dia)} de ${MESES[mes - 1]}`;
  if (ano) texto += ` de ${porExtenso(+ano + (ano.length === 2 ? 2000 : 0))}`;
  return texto;
}
const percentual = (_, i, f) => `${f ? decimal(i.replace(/\./g, ""), f) : numero(i.replace(/\./g, ""))} por cento`;
function comUnidade(_, i, f, sigla) {
  const inteira = i.replace(/\./g, ""), [sing, plur] = UNIDADES[sigla.toUpperCase()], fem = ["H", "G"].includes(sigla.toUpperCase());
  return `${f ? decimal(inteira, f) : numero(inteira, fem)} ${!f && +inteira === 1 ? sing : plur}`;
}
function sigla(palavra) {
  if (SIGLAS[palavra]) return SIGLAS[palavra];
  if (SIGLAS[palavra.toUpperCase()] && palavra === palavra.toUpperCase()) return SIGLAS[palavra.toUpperCase()];
  if (!/[AEIOUÁÉÍÓÚÂÊÔÃÕ]/.test(palavra)) return [...palavra].join(" ");  // sem vogal não é pronunciável: soletra
  return palavra;
}

export function numerosESimbolos(t) {
  t = t.replace(re(`R\\$\\s*(${NUM})(?:,(\\d{1,2}))?(?:\\s+(mil|milhão|milhões|bilhão|bilhões)${E})?`), moeda);
  t = t.replace(re("(?<![\\d:])(\\d{1,2}):(\\d{2})(?![\\d:])"), hora);
  t = t.replace(re(`(?<![\\d:])(\\d{1,2})\\s?h(?:(\\d{2}))?${E}`), hora);
  t = t.replace(re("(?<![\\d/])(\\d{1,2})/(\\d{1,2})(?:/(\\d{4}|\\d{2}))?(?![\\d/])"), data);
  t = t.replace(re(`(${NUM})(?:,(\\d+))?\\s?%`), percentual);
  t = t.replace(re(`(?<!${W}|[.,])(-?)(\\d+)\\s?[\\u00b0\\u00ba]\\s?C${E}`), (_, n, v) => (n ? "menos " : "") + numero(v) + " graus Celsius");
  t = t.replace(re(`${B}(\\d{4,5})-(\\d{4})${E}`), (_, a, b) => digitoADigito(a) + ", " + digitoADigito(b));
  const unidades = Object.keys(UNIDADES).sort((a, b) => b.length - a.length).join("|");
  t = t.replace(re(`(?<!${W}|[.,])(${NUM})(?:,(\\d+))?\\s?(${unidades})${E}`, "giu"), comUnidade);
  t = t.replace(re(`(?<!${W}|[.,])(\\d+)([ºª])`), (_, n, s) => ordinal(+n, s === "ª"));
  t = t.replace(re(`(?<!${W}|[.,])(${NUM}),(\\d+)(?![\\d])`), (_, i, f) => decimal(i.replace(/\./g, ""), f));
  t = t.replace(re(`(?<!${W}|[.,])(\\d{1,3}(?:\\.\\d{3})+|\\d+)${E}`), (_, n) => numero(n.replace(/\./g, "")));
  return t;
}

export function simbolosESiglas(t) {
  for (const [padrao, troca] of ABREVIACOES) t = t.replace(padrao, troca);
  t = t.replace(re(`${B}e\\.g\\.`), "por exemplo");
  t = t.replaceAll("&", " e ").replaceAll("→", ", ").replaceAll("->", ", ").replaceAll("=>", ", ").replaceAll("≥", " maior ou igual a ");
  t = t.replace(/\s\+\s/g, " mais ").replace(/\s=\s/g, " igual a ");
  t = t.replace(re(`(?<=${W})/(?=${W})`), " ");
  t = t.replace(re(`${B}[A-Za-z]:?\\\\[\\p{L}\\p{N}_\\\\.-]+`), "um caminho de arquivo");  // C:\pasta\arq.txt
  t = t.replace(re(`${B}[A-ZÁÉÍÓÚÂÊÔÃÕ][A-ZÁÉÍÓÚÂÊÔÃÕ0-9-]{1,}${E}`), sigla);
  t = t.replace(re(`${B}wi-?fi${E}`, "giu"), "uaifai");
  t = t.replace(re(`${B}e-?mail(s?)${E}`, "giu"), (_, s) => "i-meio" + s);
  return t;
}

// Markdown, código, links, e-mails, emojis e listas -> texto corrido, com ponto no fim de cada linha.
export function limparMarcacao(t) {
  t = t.replace(/```[\s\S]*?```/g, " (código na janela) ");
  t = t.replace(/`([^`]*)`/g, "$1");
  t = t.replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1");  // [texto](url) -> texto
  t = t.replace(/https?:\/\/\S+|www\.\S+/gi, "link");
  t = t.replace(re("[\\p{L}\\p{N}_.+-]+@[\\p{L}\\p{N}_-]+(?:\\.[\\p{L}\\p{N}_-]+)+"), "um endereço de e-mail");
  t = t.replace(EMOJI, " ");
  t = t.replace(/^\s*(?:[-•*·▪]|\d{1,2}[.)])\s+/gm, "");  // marcadores de lista
  t = t.replace(/^\s*#{1,6}\s*/gm, "");
  t = t.replace(/^[ \t]*[-=_*]{3,}[ \t]*$/gm, "");  // linhas horizontais
  t = t.replace(re("(?<![\\p{L}\\p{N}_$])[*_#>|~]+|[*_~|]+(?![\\p{L}\\p{N}_])"), "");
  t = t.replace(re("(?<=[^\\s.!?…:;,])[ \\t]*\\n+"), ". ");  // quebra de linha sem pontuação vira pausa
  return t;
}

// Pontuação que ajuda a cadência: travessão e parênteses viram vírgula, repetições são colapsadas.
export function pausas(t) {
  t = t.replace(/\s[—–-]\s/g, ", ");
  t = t.replace(/\s*[()[\]{}]\s*/g, ", ");
  t = t.replace(/\.{3,}|…/g, "…");
  t = t.replace(/([!?]){2,}/g, "$1");
  t = t.replace(/\s+([,.;:!?…])/g, "$1");
  t = t.replace(/,\s*(?=[,.;:!?])/g, "");
  t = t.replace(/([.!?…:;]),/g, "$1");
  t = t.replace(/^[,\s]+/, "");
  return t.replace(/\s+/g, " ").trim();
}

export const normalizar = (texto) => pausas(simbolosESiglas(numerosESimbolos(texto)));
