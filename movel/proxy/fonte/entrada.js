// Entrada do Worker: decide a rota. Ordem: preflight estrito -> /saude (sem Origin) -> Origin obrigatório -> rotas novas -> NVIDIA/Brave.
import { agendado } from "./agendado.js";
import { cabecalhosCors } from "./cors.js";
import { proxyApi } from "./nvidia.js";
import { rotaNova, rotaSaude, ROTAS_NOVAS } from "./rotas-novas.js";
import { ORIGEM } from "./seguranca.js";

export async function tratar(pedido, opcoes = {}) {
  const cors = cabecalhosCors();
  const origemOk = pedido.headers.get("Origin") === ORIGEM;
  const url = new URL(pedido.url);
  if (pedido.method === "OPTIONS") return origemOk ? new Response(null, { status: 204, headers: cors }) : new Response("origem não permitida", { status: 403 });
  if (url.pathname === "/saude" && pedido.method === "GET") return rotaSaude(origemOk ? cors : {});
  if (!origemOk) return new Response("origem não permitida", { status: 403 });
  const nome = url.pathname.slice(1);
  if (ROTAS_NOVAS.includes(nome)) return rotaNova(nome, pedido, url, cors, opcoes);
  return proxyApi(pedido, url, cors);
}

export default {
  fetch: (pedido) => tratar(pedido),
  scheduled: (evento, env, ctx) => agendado(evento, env, ctx),
};
