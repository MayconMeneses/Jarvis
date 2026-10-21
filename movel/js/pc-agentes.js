// Cartão "Agentes do PC": estado dos agentes da Jarvis e resumo dos subagentes do Claude Code. Só leitura (sem "Rodar agora").
import { linhas, modulo } from "./pc-cartao.js";

const ROTULO = { ok: "ok", atencao: "atenção", off: "desligados", total: "no total" };
const ESTADO = { ok: "ok", stale: "parado", error: "com erro", idle: "ocioso", off: "desligado" };

export function textoAgentes(d) {
  const resumo = Object.entries(d.resumo).filter(([k]) => ROTULO[k]).map(([k, v]) => `${v} ${ROTULO[k]}`).join(", ");
  if (!d.agentes.length) return "Nenhum agente informado pelo PC.";
  const linhas = [`**Agentes:** ${resumo || d.agentes.length}.`, ...d.agentes.map((a) => `- ${a.nome || a.id}: ${ESTADO[a.state] || a.state}`)];
  if (d.subagentes && d.subagentes.total) linhas.push(`**Subagentes do Claude Code:** ${d.subagentes.total} (${d.subagentes.contagem.rodando} rodando).`);
  return linhas.join("\n");
}

export const montar = (container, ctx) => modulo(container, ctx, { id: "pc-agentes", titulo: "Agentes do PC", rota: "agentes", desenhar: (corpo, d) => linhas(corpo, textoAgentes(d)) });
