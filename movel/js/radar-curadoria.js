// Curadoria: o que entra na disputa (filtros) e quais itens vão para o boletim (5 principais + 2 de radar). Porte de jarvis/radar/curadoria.py.
import { ehPatrocinado, tem } from "./radar-pontuar.js";
import { semAcento } from "./radar-texto.js";

export const BLOQUEIOS_PADRAO = ["publieditorial", "patrocinado", "oferta", "cupom", "promocao", "black friday", "sorteio"];

export const novoItem = (artigo, nota = 0, motivos = [], tambemEm = []) => ({ artigo, nota, motivos, tambemEm, papel: "principal", manchete: "", linhas: [],
  porQue: "", rotulo: "não classificado", origem: "rss", palavras: 0, suspeito: "", jargao: "", angulo: "", textoFonte: "" });

// Descarta o que está fora da janela, sem data, patrocinado ou que bate nos bloqueios. Conta os motivos. `agora` em segundos.
export function filtrar(artigos, bloqueios, janelaHoras, agora = Date.now() / 1000) {
  const aceitos = [], descartes = { fora_da_janela: 0, sem_data: 0, patrocinado: 0, bloqueado: 0 };
  for (const a of artigos) {
    if (!a.quando) descartes.sem_data++;  // regra do Radar: todo item leva data de publicação
    else if (!(agora - a.quando >= 0 && agora - a.quando <= janelaHoras * 3600)) descartes.fora_da_janela++;
    else if (ehPatrocinado(a)) descartes.patrocinado++;
    else if (bloqueios.some((b) => tem(semAcento(`${a.titulo} ${a.resumo}`), b))) descartes.bloqueado++;
    else aceitos.push(a);
  }
  return { aceitos, descartes };
}

// Maiores notas primeiro (empate: mais recente), com teto por fonte e nota mínima. Os últimos viram "radar".
export function escolher(itens, { principais = 5, radar = 2, maxPorFonte = 2, notaMinima = 30 } = {}) {
  const ordenados = itens.filter((i) => i.nota >= notaMinima).sort((a, b) => b.nota - a.nota || b.artigo.quando - a.artigo.quando);
  const porFonte = {}, escolhidos = [];
  for (const item of ordenados) {
    if ((porFonte[item.artigo.fonte] || 0) >= maxPorFonte) continue;
    porFonte[item.artigo.fonte] = (porFonte[item.artigo.fonte] || 0) + 1;
    escolhidos.push(item);
    if (escolhidos.length === principais + radar) break;
  }
  escolhidos.forEach((item, n) => { item.papel = n < principais ? "principal" : "radar"; });
  return escolhidos;
}
