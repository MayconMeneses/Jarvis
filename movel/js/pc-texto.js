// Textos curtos (português) das leituras do PC pareado: servem ao chat e aos cartões. Tudo vem do PC e é dado de terceiros: só vira texto.
export const marca = (r) => (r.doCache ? `\n(Cópia de ${new Date(r.quando).toLocaleString("pt-BR")}: ${r.erro})` : "");
const n1 = (v) => Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const n0 = (v) => Math.round(Number(v)).toLocaleString("pt-BR");
const DESC_SESSAO = { permissao: "esperando sua permissão", pergunta: "com uma pergunta para você", aguardando: "esperando sua resposta", trabalhando: "trabalhando", nova: "aberta, sem conversa", desconhecido: "estado desconhecido" };
const DESC_TAREFA = { na_fila: "na fila", rodando: "rodando", concluida: "concluída", falhou: "falhou" };
const DESC_SUB = { rodando: "rodando", concluido: "concluído", falhou: "falhou", parado: "parado", inativo: "inativo" };
const partes = (c, nomes) => Object.keys(nomes).filter((k) => c[k]).map((k) => `${c[k]} ${nomes[k]}`).join(", ");
const ha = (s) => (s === null ? "" : s < 90 ? ` (há ${s} s)` : s < 5400 ? ` (há ${Math.round(s / 60)} min)` : ` (há ${Math.round(s / 3600)} h)`);

export function textoVitais(r) {
  const v = r.dados;
  return `**CPU:** ${v.cpu}%\n**RAM:** ${v.ram}% (${n1(v.ram_usada_gb)} de ${n1(v.ram_total_gb)} GB)\n**Disco:** ${v.disco}% usado (${n1(v.disco_livre_gb)} GB livres)${marca(r)}`;
}

export function textoSessoes(r) {
  const s = r.dados, esp = s.contagem.permissao + s.contagem.pergunta + s.contagem.aguardando;
  let t = s.total ? `**Sessões do Claude Code:** ${s.total} (${partes(s.contagem, DESC_SESSAO)})${esp ? `. ${esp} esperando por você` : ""}.` : "Nenhuma sessão do Claude Code aberta no PC.";
  if (s.itens.length) t += "\n" + s.itens.map((i) => `- ${i.projeto}: ${DESC_SESSAO[i.estado]}${ha(i.ha_s)}`).join("\n");
  if (s.subagentes.total) t += `\n**Subagentes:** ${s.subagentes.total} (${partes(s.subagentes.contagem, DESC_SUB)}).`;
  return t + marca(r);
}

export function textoTarefas(r) {
  const t = r.dados;
  if (!t.total) return "Nenhuma tarefa de código registrada no PC." + marca(r);
  return `**Tarefas do PC:** ${t.total} (${partes(t.contagem, DESC_TAREFA)}).\n` + t.itens.map((i) => `- ${i.projeto}: ${DESC_TAREFA[i.status]}${i.tarefa ? ` — ${i.tarefa}` : ""}`).join("\n") + marca(r);
}

const textoJanela = (nome, j, unidade) => {
  const un = unidade === "mensagens" ? "mensagens" : "tokens ponderados";
  return j.pct === null ? `${nome}: ${n0(j.usado)} ${un} (teto não calibrado)` : `${nome}: ${n1(j.pct)}% usado${j.alerta ? " (atenção)" : ""}${j.acaba_antes_do_reset ? ", deve acabar antes de renovar" : ""}`;
};

export function textoUso(r) {
  const u = r.dados, h = u.hoje, c = u.cota;
  return `**Hoje:** ${h.msgs} respostas, ${n0(h.tokens)} tokens. Custo ${h.custo_rotulo}: US$ ${n1(h.custo_usd)}.\n` +
    `**Cota do Claude (estimada):** ${textoJanela("janela de 5 h", c.janela_5h, c.unidade)}; ${textoJanela("semana", c.semana, c.unidade)}.\n${c.aviso}${marca(r)}`;
}

export function textoRadar(r) {
  const d = r.dados;
  if (d.vazio) return "O Radar do PC ainda não gerou nenhum boletim." + marca(r);
  return `**Boletim do Radar do PC** (${d.dia}${d.hora ? `, às ${d.hora}` : ""}): ${d.total} escolhidas.\n` + d.itens.map((i) => `- ${i.titulo} (${i.fonte})`).join("\n") + marca(r);
}
