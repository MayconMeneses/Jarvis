// Boletim -> Markdown (o app mostra com o renderizador seguro de md.js; todo texto vem de terceiros e só vira texto). Porte de jarvis/radar/render.py.
import { linkValido } from "./radar-texto.js";

export const SEM_IA = "_Resumos extrativos: frases do próprio texto da fonte. Sem IA não há manchete própria, tradução de jargão, ângulo, conexões nem comparação entre fontes: isso é omitido, nunca inventado._";

export const novoBoletim = (dia, nicho, itens = []) => ({ dia, nicho, itens, conexoes: [], observar: [], varridos: 0, falhas: [], avisos: [], comIa: false, atrasado: false });

const dataBr = (s) => new Date(s * 1000).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });

function meta(item) {
  const partes = [item.artigo.fonte, item.artigo.quando ? dataBr(item.artigo.quando) : "sem data"];
  partes.push(item.origem === "artigo" && item.palavras ? `leitura ${Math.max(1, Math.round(item.palavras / 200))} min` : "resumo baseado só no RSS");
  partes.push(`[${item.rotulo}]`);
  return partes.join(" · ");
}

export function cabecalho(b) {
  const l = [`Data: ${b.dia} · Nicho: ${b.nicho} · Artigos varridos: ${b.varridos} · Modo: ${b.comIa ? "com IA" : "sem IA"}`];
  l.push("Fontes que falharam: " + (b.falhas.length ? b.falhas.join("; ") : "nenhuma"));
  l.push(...b.avisos.map((a) => `Aviso: ${a}`));
  if (b.atrasado) l.push("Aviso: este é o boletim atrasado de hoje.");
  return l;
}

export function markdown(b) {
  const o = [`# Radar de ${b.nicho} — ${b.dia}`, "", ...cabecalho(b).map((l) => `- ${l}`), ""];
  if (!b.comIa) o.push(SEM_IA, "");
  b.itens.forEach((item, n) => {
    o.push(`## ${n + 1}. ${item.manchete}`, `*${meta(item)}* · nota ${item.nota}/100`);
    if (item.suspeito) o.push(`⚠ Este item tem texto que tenta dar ordens à IA (${item.suspeito}). Mostrado só com o título; abra por sua conta e risco.`);
    o.push(...item.linhas.map((l) => `- ${l}`));
    if (b.comIa && item.porQue) o.push(`**Por que isso importa:** ${item.porQue}`);
    else if (item.porQue && !item.suspeito) o.push(`_${item.porQue}_`);
    if (b.comIa && item.jargao) o.push(`**Tradução do jargão:** ${item.jargao}`);
    if (b.comIa && item.angulo) o.push(`**Ângulo para usar:** ${item.angulo}`);
    if (item.tambemEm.length) o.push(`Também em: ${item.tambemEm.join(", ")}`);
    o.push(linkValido(item.artigo.link) ? `Link: ${item.artigo.link}` : "Link indisponível", "");
  });
  if (b.conexoes.length) o.push("## Conexões do dia", ...b.conexoes.map((c) => `- ${c}`), "");
  if (b.observar.length) o.push("## O que observar amanhã", ...b.observar.map((x) => `- ${x}`), "");
  if (!b.itens.length) o.push("Nenhum item passou nos filtros hoje.", "");
  return o.join("\n");
}

// O renderizador seguro do app (md.js) não tem títulos nem itálico: títulos viram negrito e as linhas _em itálico_ ficam normais.
export const paraTela = (md) => md.replace(/^#{1,3}\s+(.*)$/gm, "**$1**").replace(/^_(.+)_$/gm, "$1").replace(/^\*([^*]+)\*( · nota .*)$/gm, "$1$2");
