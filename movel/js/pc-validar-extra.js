// Validação campo a campo das rotas novas do PC pareado (vitais, sessões, tarefas, uso, radar, agentes). Formato errado => null.
import { contagens, data, escolha, lista, num, numOuNulo, pct, simples, txt } from "./pc-sanear.js";

export const ESTADOS_SESSAO = ["permissao", "pergunta", "aguardando", "trabalhando", "nova", "desconhecido"];
export const ESTADOS_SUB = ["rodando", "concluido", "falhou", "parado", "inativo"];
export const STATUS_TAREFA = ["na_fila", "rodando", "concluida", "falhou"];
const MAX_ITENS = 5;

function vitais(d) {
  const gb = (v) => Math.min(num(v), 1e6);
  return { gerado: data(d.gerado), cpu: pct(d.cpu), ram: pct(d.ram), disco: pct(d.disco), ram_total_gb: gb(d.ram_total_gb), ram_usada_gb: gb(d.ram_usada_gb), disco_total_gb: gb(d.disco_total_gb), disco_livre_gb: gb(d.disco_livre_gb) };
}

function sessoes(d) {
  if (!simples(d.contagem)) return null;
  const sub = simples(d.subagentes) ? d.subagentes : {};
  return {
    gerado: data(d.gerado), total: num(d.total), contagem: contagens(d.contagem, ESTADOS_SESSAO),
    itens: lista(d.itens, MAX_ITENS).filter(simples).map((s) => ({ projeto: txt(s.projeto, 40) || "(sem nome)", estado: escolha(s.estado, ESTADOS_SESSAO, "desconhecido"), ha_s: numOuNulo(s.ha_s) })),
    subagentes: { total: num(sub.total), contagem: contagens(sub.contagem, ESTADOS_SUB),
      itens: lista(sub.itens, MAX_ITENS).filter(simples).map((a) => ({ projeto: txt(a.projeto, 40), tipo: txt(a.tipo, 30), estado: escolha(a.estado, ESTADOS_SUB, "inativo") })) },
  };
}

function tarefas(d) {
  if (!simples(d.contagem)) return null;
  return {
    gerado: data(d.gerado), total: num(d.total), contagem: contagens(d.contagem, STATUS_TAREFA),
    itens: lista(d.itens, MAX_ITENS).filter(simples).map((t) => ({ projeto: txt(t.projeto, 40), status: escolha(t.status, STATUS_TAREFA, "falhou"), modo: txt(t.modo, 16), tarefa: txt(t.tarefa, 80) })),
  };
}

const janela = (j) => {
  j = simples(j) ? j : {};
  const p = numOuNulo(j.pct);
  return { usado: num(j.usado), teto: numOuNulo(j.teto), pct: p === null ? null : Math.min(p, 999), ativa: j.ativa === true, alerta: j.alerta === true, msgs: num(j.msgs), fim: numOuNulo(j.fim), acaba_antes_do_reset: j.acaba_antes_do_reset === true };
};

function uso(d) {
  if (!simples(d.hoje) || !simples(d.cota)) return null;
  const h = d.hoje, c = d.cota;
  return {
    gerado: data(d.gerado),
    hoje: { msgs: num(h.msgs), tokens: num(h.tokens), custo_usd: num(h.custo_usd), estimado: true, custo_rotulo: txt(h.custo_rotulo, 120) || "custo estimado" },
    cota: { unidade: escolha(c.unidade, ["tokens", "mensagens"], "tokens"), plano: txt(c.plano, 24), janela_5h: janela(c.janela_5h), semana: janela(c.semana), aviso: txt(c.aviso, 160) },
  };
}

function radar(d) {
  if (d.vazio === true) return { gerado: data(d.gerado), vazio: true, dia: "", hora: "", total: 0, itens: [] };
  return {
    gerado: data(d.gerado), vazio: false, dia: txt(d.dia, 10), hora: txt(d.hora, 5), total: Math.min(num(d.total), 99),
    itens: lista(d.itens, 8).filter(simples).map((i) => ({ titulo: txt(i.titulo, 160) || "(sem título)", fonte: txt(i.fonte, 40), quando: txt(i.quando, 16) })),
  };
}

function agentes(d) {
  const sub = simples(d.subagentes) ? d.subagentes : null;
  const resumo = simples(d.resumo) ? Object.fromEntries(Object.entries(d.resumo).slice(0, 12).map(([k, v]) => [txt(k, 20), num(v)])) : {};
  return {
    server_now: numOuNulo(d.server_now), resumo,
    agentes: lista(d.agentes, 30).filter(simples).map((a) => ({ id: txt(a.id, 30), nome: txt(a.nome, 50), state: txt(a.state, 12), age_s: numOuNulo(a.age_s) })),
    subagentes: sub && simples(sub.contagem) ? sessoes({ contagem: {}, subagentes: sub }).subagentes : null,
  };
}

export const ROTAS_EXTRA = { vitais, sessoes, tarefas, uso, radar, agentes };
