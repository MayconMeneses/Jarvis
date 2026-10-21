// Entende quando o usuário ENSINA um atalho: "quando eu disser X, mostre minha agenda", "X significa notícias", "isso significa Y".
// Só reconhece a frase; quem decide se vale (e pede aprovação no cartão Guardar/Descartar) é o Entendimento. Texto sem acento e em minúsculas.
import { normalizar } from "./intencao-texto.js";

const ASPAS = /["“”'`]/g;
const PERGUNTA = /^(o que|que|qual|quais|quem|como|quando|onde|por que|porque)\b/;

const limpar = (t) => t.replace(ASPAS, "").replace(/^[\s,:;-]+|[\s,:;.!?-]+$/g, "").trim();

// Devolve { de, para, explicito, deAnterior } ou null. `deAnterior` = true quando "isso significa Y" (o X é a última frase não entendida).
export function lerEnsinamento(texto) {
  const bruto = String(texto).trim();
  if (bruto.length > 200 || bruto.includes("\n")) return null;
  const t = normalizar(bruto.replace(ASPAS, " "));
  let m = /^(?:ei |ok )?quando eu (?:disser|falar|digitar|escrever|pedir|mandar)\s+(.{3,60}?)\s*,?\s+(?:voce\s+)?(?:faca|faz|fazer|responda|responde|mostre|mostra|execute|rode|entenda como|entende como|me mostre|me mostra|me de|abra|abre)\s+(.{3,80})$/.exec(t);
  if (m) return { de: limpar(m[1]), para: limpar(m[2]), explicito: true, deAnterior: false };
  m = /^(?:isso|essa frase|aquilo|o que eu (?:disse|falei|pedi)) (?:significa|quer dizer|e o mesmo que|era)\s+(.{3,80})$/.exec(t);
  if (m) return { de: "", para: limpar(m[1]), explicito: false, deAnterior: true };
  m = /^(.{3,60}?)\s+(?:significa|quer dizer|e o mesmo que|equivale a)\s+(.{3,80})$/.exec(t);
  if (m && !PERGUNTA.test(m[1])) return { de: limpar(m[1]), para: limpar(m[2]), explicito: false, deAnterior: false };
  return null;
}

const SIM = /^(sim|isso|isso mesmo|e isso|e esse|esse|esse mesmo|pode ser|claro|exato|exatamente|ok|certo|a primeira|primeira|1|um|pode|isso ai)$/;
const SEGUNDA = /^(a segunda|segunda|2|dois|o segundo|segundo|a outra)$/, TERCEIRA = /^(a terceira|terceira|3|tres|o terceiro|terceiro)$/;
const NAO = /^(nao|nenhum|nenhuma|nao e isso|errado|nenhuma delas|cancela|cancelar|deixa|deixa pra la)$/;

// Resposta curta a "Você quis dizer ...?": 0, 1, 2 (qual opção), -1 (nenhuma) ou null (era outra frase).
export function respostaCurta(texto) {
  const t = normalizar(texto);
  if (SIM.test(t)) return 0;
  if (SEGUNDA.test(t)) return 1;
  if (TERCEIRA.test(t)) return 2;
  if (NAO.test(t)) return -1;
  return null;
}
