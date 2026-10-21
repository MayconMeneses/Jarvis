// CORS e respostas: sempre só para a ORIGEM do app; nenhuma resposta repassa cabeçalhos ou cookies do destino.
import { ORIGEM } from "./seguranca.js";
export function cabecalhosCors() {
  return {
    "Access-Control-Allow-Origin": ORIGEM,
    "Access-Control-Allow-Headers": "authorization,content-type,x-subscription-token,accept",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Max-Age": "600",
    Vary: "Origin",
  };
}
const FIXOS = { "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Content-Security-Policy": "default-src 'none'; sandbox" };

export function erroJson(status, mensagem, cors, extra = {}) {
  return new Response(JSON.stringify({ erro: mensagem }), { status, headers: { ...cors, ...FIXOS, ...extra, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
}
export function respostaOk(corpo, tipo, cors) {
  return new Response(corpo, { status: 200, headers: { ...cors, ...FIXOS, "Content-Type": tipo, "Cache-Control": "private, max-age=300" } });
}
