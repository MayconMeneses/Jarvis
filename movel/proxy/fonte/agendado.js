// Estrutura para tarefas agendadas (Cron Trigger) e Web Push: NADA roda por padrão. Para ativar no futuro seria preciso (1) registrar
// tarefas em TAREFAS_AGENDADAS, (2) criar o Cron na conta Cloudflare e (3) definir a variável JARVIS_CRON=sim. Hoje a lista é vazia.
export const TAREFAS_AGENDADAS = [];

export async function agendado(evento, env, ctx) {
  if (env?.JARVIS_CRON !== "sim") return;
  for (const tarefa of TAREFAS_AGENDADAS) ctx.waitUntil(tarefa(env));
}
