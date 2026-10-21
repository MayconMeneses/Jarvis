// Rotas novas: GET /rss, /ler, /ical (todas com ?url=https://...) e GET /saude. Respostas de erro são genéricas: nunca citam a URL pedida.
import { buscarSeguro, decodificar, ErroRota } from "./buscar.js";
import { erroJson, respostaOk } from "./cors.js";
import { dentroDoLimite } from "./limite.js";
import { LIMITES, validarUrl } from "./seguranca.js";
import { extrairTexto } from "./texto.js";

const TIPOS_RSS = ["application/xml", "text/xml", "application/rss+xml", "application/atom+xml", "application/rdf+xml", "application/x-rss+xml", "text/plain"];
const TIPOS_HTML = ["text/html", "application/xhtml+xml", "text/plain"];
const TIPOS_ICAL = ["text/calendar", "application/ics", "text/plain"];
export const ROTAS_NOVAS = ["rss", "ler", "ical"];

function xmlCharset(bytes) {
  const cabeca = new TextDecoder("latin1").decode(bytes.subarray(0, 200));
  return /^\s*<\?xml[^>]{0,150}encoding\s*=\s*["']([\w.:-]{1,40})/i.exec(cabeca)?.[1] || "";
}
const tratadores = {
  async rss(r, url, opcoes) {
    const b = await buscarSeguro(url, TIPOS_RSS, { ...opcoes, accept: "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.1" });
    const xml = decodificar(b.bytes, b.charset || xmlCharset(b.bytes));
    if (!/<(rss|feed|rdf:rdf)[\s>]/i.test(xml.slice(0, 4000))) throw new ErroRota(415, "tipo de conteúdo não aceito");
    return [xml, "application/xml; charset=utf-8"];
  },
  async ical(r, url, opcoes) {
    const b = await buscarSeguro(url, TIPOS_ICAL, { ...opcoes, accept: "text/calendar, text/plain;q=0.9" });
    const ics = decodificar(b.bytes, b.charset);
    if (!/^\ufeff?\s*BEGIN:VCALENDAR/i.test(ics.slice(0, 200))) throw new ErroRota(415, "tipo de conteúdo não aceito");
    return [ics, "text/calendar; charset=utf-8"];
  },
  async ler(r, url, opcoes) {
    const b = await buscarSeguro(url, TIPOS_HTML, { ...opcoes, accept: "text/html, application/xhtml+xml;q=0.9, text/plain;q=0.5" });
    const e = extrairTexto(decodificar(b.bytes, b.charset), LIMITES.textoMax);
    const corpo = { titulo: e.titulo, texto: e.texto, idioma: e.idioma, url_final: b.urlFinal.href, tamanho: b.bytes.byteLength };
    return [JSON.stringify(corpo), "application/json; charset=utf-8"];
  },
};

// `opcoes` só existe para os testes (fetch falso, tempo curto). Em produção é sempre {}.
export async function rotaNova(nome, pedido, url, cors, opcoes = {}) {
  if (pedido.method !== "GET") return erroJson(405, "método não permitido", cors, { Allow: "GET, OPTIONS" });
  const ip = pedido.headers.get("cf-connecting-ip") || "desconhecido";
  if (!dentroDoLimite(ip, LIMITES.porMinuto, opcoes.agora)) return erroJson(429, "muitos pedidos", cors, { "Retry-After": "60" });
  const alvos = url.searchParams.getAll("url");
  const alvo = alvos.length === 1 ? validarUrl(alvos[0]) : null;
  if (!alvo) return erroJson(400, "endereço não permitido", cors);
  try {
    const [corpo, tipo] = await tratadores[nome](pedido, alvo, opcoes);
    return respostaOk(corpo, tipo, cors);
  } catch (e) {
    return e instanceof ErroRota ? erroJson(e.status, e.message, cors) : erroJson(502, "falha ao buscar", cors);
  }
}

export function rotaSaude(cors) {
  return new Response(JSON.stringify({ rotas: [...ROTAS_NOVAS, "nvidia", "brave"], versao: 2 }), { status: 200, headers: { ...cors, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
}
