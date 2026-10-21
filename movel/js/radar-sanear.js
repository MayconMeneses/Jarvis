// Saneamento de texto de terceiros e alerta de injeção de prompt. Porte de jarvis/radar/sanear.py (+ jarvis/mail/rules.texto_suspeito).
// A segurança NÃO depende deste detector: o texto de notícia nunca chega a uma IA com ferramentas e nada do que ele diz vira ação.
// O detector é uma camada de ALERTA (o item é marcado ⚠ e não vai à IA nem à voz).
import { limpar, semAcento } from "./radar-texto.js";

const PARES = { "а": "a", "в": "b", "е": "e", "ё": "e", "з": "3", "и": "u", "і": "i", "ј": "j", "к": "k", "м": "m", "н": "h", "о": "o", "п": "n", "р": "p", "с": "c", "т": "t", "у": "y",
  "х": "x", "ѕ": "s", "ԁ": "d", "ԛ": "q", "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "χ": "x" };
const INJECAO = [
  /ignor\w*\s+(as\s+|todas\s+as\s+)?(instru|regras|orienta)/i,
  /ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)/i,
  /(system|sistema)\s*prompt/i,
  /\b(you are|você é) (now |agora )?(an? |uma? )?(ai|ia|assistant|assistente)\b/i,
  /\b(jarvis|claude|assistant|assistente)\s*[,:]\s*(apague|delete|envie|send|execute|run|encaminhe|forward)/i,
  /(apague|delete|remova)\s+(todos|todas|all)\b/i,
];
const EXTRAS = [
  /(desconsider|esquec|ignor)\w*\s+(tudo|todas?|isso|o que|as|os)\b.{0,40}\b(antes|anterior|acima|dito|regras|instrucoes)/,
  /(ignore|disregard|forget)\s+(all|everything|the)\b.{0,30}\b(above|previous|prior|instructions|rules)/,
  /(ignora|olvida)\s+las?\s+instrucciones/,
  /\b(novo|nova)\s+(objetivo|missao|tarefa|instrucao)\s*:/,
  /\b(copi|envi|mand|encaminh|revel|vaz)\w*\s+(as\s+|os\s+|a\s+|o\s+|seu\s+|sua\s+|todos\s+os\s+)?(senhas?|chaves?|tokens?|credenciais|prompt|memoria|dados)\b/,
  /(you are now|developer mode|jailbreak|modo desenvolvedor|modo deus)/,
  /(responda|reply|answer)\s+(apenas|only)\s+com/,
  /\b(jarvis|assistente|assistant)\s*[,:]\s*(adicione|acesse|abra|visite|instale|baixe|add|open|visit|install|download)\b/,
  /(new system prompt|system prompt|prompt de sistema|prompt do sistema)/,
  /(chame|call|invoke|execute|use)\s+(a\s+)?(ferramenta|tool|function|funcao)\b/,
  /<\/?\s*(system|assistant|user)\s*>/,
  /(que|that)\s+(o\s+)?(assistente|assistant|ia|ai)\s+(deve|devera|should|must)\s+(ignorar|ignore|enviar|send|apagar|delete)/,
];

// NFKC (largura total vira normal), sem caracteres invisíveis/de controle, homóglifos trocados por letras latinas.
export function normalizar(texto) {
  const limpo = String(texto || "").normalize("NFKC").replace(/[\p{Cf}\p{Co}\p{Cn}]/gu, "").replace(/(?![\n\t])\p{Cc}/gu, "");
  return [...limpo].map((c) => PARES[c] ?? c).join("");
}

// "i-g-n-o-r-e" e "i.g.n.o.r.e" voltam a ser "ignore".
export const desofuscar = (texto) =>
  texto.replace(/(?<![\p{L}\p{N}_])(?:\p{L}[\-._*]){1,}\p{L}(?![\p{L}\p{N}_])/gu, (m) => m.replace(/[\-._*]/g, ""));

// HTML/script/comentário fora, invisíveis fora, tamanho limitado. É o que qualquer parte do Radar pode usar.
export const limparTerceiros = (texto, limite = 4000) => limpar(normalizar((texto || "").replace(/<!--[\s\S]*?-->/g, " ")), limite);

// Motivo, se o texto tenta dar ordens à IA (ou ao Radar); null se parece uma notícia normal.
export function suspeito(texto) {
  const limpo = normalizar(texto);
  for (const variante of [limpo, desofuscar(limpo)]) {
    for (const padrao of INJECAO) {
      const achou = padrao.exec(variante);
      if (achou) return `contém texto que tenta dar ordens à IA: “${achou[0].slice(0, 60)}”`;
    }
    const dobrado = semAcento(variante);
    for (const padrao of EXTRAS) {
      const achou = padrao.exec(dobrado);
      if (achou) return `contém texto que tenta dar ordens à IA: “${achou[0].slice(0, 60)}”`;
    }
  }
  return null;
}
