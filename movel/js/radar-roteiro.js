// Boletim -> roteiro feito para o OUVIDO (não para o olho), dentro de um orçamento de palavras. Porte de jarvis/radar/roteiro.py.
// Abertura (3 manchetes) -> notícias ("Segundo o veículo...") -> conexões (só com IA) -> encerramento. Itens suspeitos (⚠) nunca são narrados.
import { MESES } from "./voz-normalizar.js";
import { falarTexto } from "./radar-numeros.js";

export const MAX_PALAVRAS_ITEM = 130;
export const ENCERRAMENTO = "Isso é tudo. Os links estão no boletim escrito de hoje.";

export const saudacao = (hora) => (hora < 12 ? "Bom dia" : hora < 18 ? "Boa tarde" : "Boa noite");
const contar = (t) => t.split(/\s+/).filter(Boolean).length;
const ponto = (l) => (/[.!?…]$/.test(l.trimEnd()) ? l.trimEnd() : l.trimEnd() + ".");

function limitar(frases, maximo) {
  const saida = [];
  let total = 0;
  for (const f of frases) {
    total += contar(f);
    if (saida.length && total > maximo) break;
    saida.push(f);
  }
  return saida;
}

export function falaDoItem(item, posicao, total, nicho, comIa) {
  const a = item.artigo;
  const abertura = posicao === 0 ? "" : posicao === total - 1 ? "Pra fechar. " : posicao % 2 ? "Próxima. " : `Ainda em ${nicho}. `;
  const frases = [`Segundo o ${a.fonte}, ${item.manchete.replace(/\.+$/, "")}.`, ...item.linhas.slice(0, 2).map(ponto)];
  if (comIa && item.porQue) frases.push(item.porQue);
  if (item.tambemEm.length) frases.push("Também publicado por " + item.tambemEm.slice(0, 2).join(" e ") + ".");
  if (item.rotulo === "opinião") frases.push("É um texto de opinião.");
  else if (item.rotulo === "possível paywall") frases.push("Resumo parcial: o conteúdo completo é pago.");
  return abertura + limitar(frases, MAX_PALAVRAS_ITEM).join(" ");
}

// Devolve { texto, itens (os falados), cortados, palavras }. Se estourar o orçamento, saem os de menor nota.
export function montar(boletim, maxPalavras = 900, agora = new Date()) {
  const candidatos = boletim.itens.filter((i) => !i.suspeito).sort((a, b) => b.nota - a.nota);
  const cortados = [];
  const compor = (itens) => {
    const manchetes = itens.slice(0, 3).map((i) => i.manchete.replace(/\.+$/, "")).join(". ");
    const partes = [`${boletim.atrasado ? "Este é o boletim atrasado de hoje. " : ""}${saudacao(agora.getHours())}. `
      + `Aqui é o seu radar de ${boletim.nicho}, ${agora.getDate()} de ${MESES[agora.getMonth()]}. Hoje: ${manchetes}.`];
    partes.push(...itens.map((i, n) => falaDoItem(i, n, itens.length, boletim.nicho, boletim.comIa)));
    if (boletim.conexoes.length) partes.push("Conexões do dia. " + boletim.conexoes.slice(0, 3).map((c) => c.replace(/\.+$/, "") + ".").join(" "));
    partes.push(ENCERRAMENTO);
    return falarTexto(partes.join("\n"));
  };
  let texto = compor(candidatos);
  while (contar(texto) > maxPalavras && candidatos.length > 1) { cortados.push(candidatos.pop()); texto = compor(candidatos); }
  return { texto, itens: candidatos, cortados, palavras: contar(texto) };
}

// Confere o roteiro final: sem URL, Markdown, emoji, colchetes, hashtag nem a palavra "bullet".
export const limpoParaVoz = (texto) => !/https?:\/\/|www\.|[*_`#>|[\]]|bullet|[\u{1F000}-\u{1FAFF}]/iu.test(texto);
