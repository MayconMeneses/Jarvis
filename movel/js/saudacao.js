// Saudações puras ("oi", "boa noite", "oi, boa noite, Jarvis", "e aí"): respondidas SEM IA, com o horário certo. Nunca ficam sem resposta.
// Regra compartilhada com o PC: testes/dados/saudacoes.json. Só vale se a frase INTEIRA for saudação (até 6 palavras, ignorando o nome).
import { saudacao } from "./hud-briefing.js";
import { eJarvis, semAcento } from "./voz-ativacao.js";

const NUCLEO = new Set(["oi", "ola", "opa", "ei", "hey", "hei", "eai", "salve", "beleza", "blz"]);
const NUCLEO_FRASE = /(bom dia|boa tarde|boa noite|(^| )e ai($| ))/;
const ENFEITE = new Set(["bom", "boa", "dia", "tarde", "noite", "e", "ai", "tudo", "bem", "como", "vai", "voce", "vc", "tranquilo", "fala", "ae", "jarvis"]);
const PERGUNTA = /\b(tudo bem|como vai|como voce esta|tudo certo)\b/;

export function ehSaudacao(texto) {
  const palavras = semAcento(texto).split(/[^\p{L}\p{N}]+/u).filter(Boolean).filter((p) => !eJarvis(p) && p !== "jarvis");
  const todas = palavras.every((p) => NUCLEO.has(p) || ENFEITE.has(p));
  return palavras.length > 0 && palavras.length <= 6 && todas && (palavras.some((p) => NUCLEO.has(p)) || NUCLEO_FRASE.test(palavras.join(" ")));
}

// `agora`: Date. `nome`: como chamar a pessoa ("" = sem nome). Devolve null se a frase não for só uma saudação.
export function responderSaudacao(texto, agora, nome = "") {
  if (!ehSaudacao(texto)) return null;
  const quando = saudacao(agora.getHours(), nome);
  const meio = PERGUNTA.test(semAcento(texto)) ? " Tudo bem por aqui, e com você?" : "";
  return `${quando}!${meio} Estou aqui. Em que posso ajudar?`;
}
