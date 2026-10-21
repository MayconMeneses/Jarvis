// Proxy do Super Jarvis para Cloudflare Workers (plano grátis). ARQUIVO GERADO por movel/proxy/montar.mjs a partir de movel/proxy/fonte/*.js: não edite aqui.
// Rotas: /v1/... (NVIDIA), /brave/res/v1/... (Brave), GET /rss?url=, /ler?url=, /ical?url= (https público, só para a ORIGEM) e GET /saude (sem Origin).
// Não guarda chave nenhuma. Como reimplantar: docs/CELULAR-INDEPENDENTE.md.
const ORIGEM = "https://mayconmeneses.github.io";
const LIMITES = Object.freeze({ tempoMs: 8000, maxBytes: 1500000, redirecionamentos: 3, textoMax: 6000, porMinuto: 30 });
const TLD_BLOQUEADO = new Set(["localhost", "local", "internal", "localdomain", "lan", "home", "corp", "intranet", "private", "arpa", "test", "example", "invalid", "onion"]);
const DOMINIO_BLOQUEADO = ["nip.io", "sslip.io", "xip.io", "localtest.me", "lvh.me", "traefik.me"];
function hostProibido(h) {
  if (!h || h.length > 253 || h.includes(":") || h.includes("[")) return true;      // literal IPv6
  const rotulos = h.split(".");
  if (rotulos.length < 2) return true;                                                // sem ponto: nome interno
  const tld = rotulos[rotulos.length - 1];
  if (!/^(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})$/.test(tld)) return true;               // TLD numérico = IPv4 literal (qualquer notação)
  if (TLD_BLOQUEADO.has(tld)) return true;
  if (!rotulos.every((r) => /^[a-z0-9_-]{1,63}$/.test(r))) return true;
  return DOMINIO_BLOQUEADO.some((d) => h === d || h.endsWith("." + d));
}
function validarUrl(bruto) {
  if (typeof bruto !== "string" || bruto.length === 0 || bruto.length > 2048) return null;
  if (/[\u0000-\u0020\u007f-\u009f\\]/.test(bruto)) return null;
  let u;
  try { u = new URL(bruto); } catch { return null; }
  if (u.protocol !== "https:" || u.username || u.password || u.port) return null;
  if (hostProibido(u.hostname.toLowerCase().replace(/\.$/, ""))) return null;
  u.hash = "";
  return u;
}
function cabecalhosCors() {
  return {
    "Access-Control-Allow-Origin": ORIGEM,
    "Access-Control-Allow-Headers": "authorization,content-type,x-subscription-token,accept",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Max-Age": "600",
    Vary: "Origin",
  };
}
const FIXOS = { "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Content-Security-Policy": "default-src 'none'; sandbox" };
function erroJson(status, mensagem, cors, extra = {}) {
  return new Response(JSON.stringify({ erro: mensagem }), { status, headers: { ...cors, ...FIXOS, ...extra, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
}
function respostaOk(corpo, tipo, cors) {
  return new Response(corpo, { status: 200, headers: { ...cors, ...FIXOS, "Content-Type": tipo, "Cache-Control": "private, max-age=300" } });
}
class ErroRota extends Error {
  constructor(status, mensagem) { super(mensagem); this.status = status; }
}
const falha = (status, msg) => new ErroRota(status, msg);
function descartar(r) { try { r.body?.cancel().catch(() => {}); } catch { /* sem corpo para descartar */ } }
async function lerLimitado(r, max, aborto) {
  const tamanho = Number(r.headers.get("content-length"));
  if (Number.isFinite(tamanho) && tamanho > max) { descartar(r); throw falha(413, "conteúdo grande demais"); }
  if (!r.body) return new Uint8Array(0);
  const leitor = r.body.getReader();
  const partes = [];
  let total = 0;
  for (;;) {
    const { done, value } = await Promise.race([leitor.read(), aborto]);
    if (done) break;
    total += value.byteLength;
    if (total > max) { leitor.cancel().catch(() => {}); throw falha(413, "conteúdo grande demais"); }
    partes.push(value);
  }
  const bytes = new Uint8Array(total);
  let pos = 0;
  for (const p of partes) { bytes.set(p, pos); pos += p.byteLength; }
  return bytes;
}
async function buscarSeguro(entrada, tipos, { buscar = (u, i) => fetch(u, i), tempoMs = LIMITES.tempoMs, maxBytes = LIMITES.maxBytes, accept = "*/*" } = {}) {
  const ctl = new AbortController();
  const aborto = new Promise((_, rej) => ctl.signal.addEventListener("abort", () => rej(falha(504, "tempo esgotado"))));
  aborto.catch(() => {});
  const timer = setTimeout(() => ctl.abort(), tempoMs);
  try {
    let url = entrada;
    for (let salto = 0; salto <= LIMITES.redirecionamentos; salto++) {
      let r;
      try {
        r = await Promise.race([buscar(url.href, { method: "GET", redirect: "manual", signal: ctl.signal, headers: { accept, "user-agent": "Mozilla/5.0 (compatible; SuperJarvis/1.0)" } }), aborto]);
      } catch (e) {
        throw e instanceof ErroRota ? e : falha(ctl.signal.aborted ? 504 : 502, ctl.signal.aborted ? "tempo esgotado" : "falha ao buscar");
      }
      if (r.status >= 300 && r.status < 400 && r.status !== 304) {
        descartar(r);
        let prox = null;
        try { prox = validarUrl(new URL(r.headers.get("location") || "", url).href); } catch { prox = null; }
        if (!prox || salto === LIMITES.redirecionamentos) throw falha(502, "redirecionamento não permitido");
        url = prox;
        continue;
      }
      if (r.status !== 200) { descartar(r); throw falha(502, "falha ao buscar"); }
      const ct = r.headers.get("content-type") || "";
      const tipo = ct.split(";")[0].trim().toLowerCase();
      if (!tipos.includes(tipo)) { descartar(r); throw falha(415, "tipo de conteúdo não aceito"); }
      const charset = /charset\s*=\s*"?([\w.:-]{1,40})/i.exec(ct)?.[1] || "";
      try { return { bytes: await lerLimitado(r, maxBytes, aborto), charset, urlFinal: url }; }
      catch (e) { throw e instanceof ErroRota ? e : falha(ctl.signal.aborted ? 504 : 502, ctl.signal.aborted ? "tempo esgotado" : "falha ao buscar"); }
    }
    throw falha(502, "redirecionamento não permitido");
  } finally { clearTimeout(timer); ctl.abort(); }
}
function decodificar(bytes, charset) {
  const tentativa = (c) => { try { return new TextDecoder(c || "utf-8").decode(bytes); } catch { return null; } };
  return tentativa(charset) ?? tentativa("utf-8");
}
const janelas = new Map();
function dentroDoLimite(ip, maximo, agora = Date.now()) {
  if (janelas.size > 5000) { for (const [k, v] of janelas) if (agora - v.inicio > 60000) janelas.delete(k); if (janelas.size > 5000) janelas.clear(); }
  let j = janelas.get(ip);
  if (!j || agora - j.inicio > 60000) { j = { inicio: agora, n: 0 }; janelas.set(ip, j); }
  j.n += 1;
  return j.n <= maximo;
}
function zerarLimites() { janelas.clear(); }
const BLOCO = new Set(["p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article", "main", "blockquote", "pre", "table", "hr", "dd", "dt", "figcaption"]);
const BRUTO = new Set(["script", "style", "noscript", "template", "iframe", "svg", "object", "embed", "textarea", "select"]);
const ESTRUTURA = ["nav", "footer", "form", "aside"];
const VAZIA = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "source", "track", "wbr"]);
const NOMES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", ndash: "–", mdash: "—", hellip: "…", laquo: "«", raquo: "»", lsquo: "‘", rsquo: "’", ldquo: "“", rdquo: "”", copy: "©", bull: "•" };
function entidades(s) {
  if (!s.includes("&")) return s;
  return s.replace(/&(#x[0-9a-f]{1,6}|#[0-9]{1,7}|[a-z]{2,8});/gi, (m, g) => {
    if (g[0] !== "#") return Object.hasOwn(NOMES, g.toLowerCase()) ? NOMES[g.toLowerCase()] : m;
    const cp = g[1] === "x" || g[1] === "X" ? parseInt(g.slice(2), 16) : parseInt(g.slice(1), 10);
    return cp > 0 && cp <= 0x10ffff && !(cp >= 0xd800 && cp <= 0xdfff) ? String.fromCodePoint(cp) : "";
  });
}
function limparTexto(s) {
  const t = s.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]/g, "").replace(/[ \t\r\f\v\u00a0]+/g, " ");
  const linhas = [];
  for (const l of t.split("\n").map((x) => x.trim())) if (l || (linhas.length && linhas[linhas.length - 1])) linhas.push(l);
  return linhas.join("\n").trim();
}
function cortar(s, max) {
  if (s.length <= max) return s;
  const c = s.charCodeAt(max - 1);
  return s.slice(0, c >= 0xd800 && c <= 0xdbff ? max - 1 : max);
}
function varrer(html, ignorarEstrutura) {
  const min = html.replace(/[A-Z]/g, (c) => c.toLowerCase());   // só ASCII: mantém os índices iguais
  const tudo = [], artigo = [], main = [];
  const prof = { article: 0, main: 0, nav: 0, footer: 0, form: 0, aside: 0 };
  let titulo = "", lang = "", i = 0;
  const n = html.length;
  const juntar = (s) => {
    if (ignorarEstrutura && ESTRUTURA.some((e) => prof[e] > 0)) return;
    tudo.push(s);
    if (prof.article > 0) artigo.push(s);
    if (prof.main > 0) main.push(s);
  };
  while (i < n) {
    const lt = html.indexOf("<", i);
    const fim = lt < 0 ? n : lt;
    if (fim > i) juntar(entidades(html.slice(i, fim)));
    if (lt < 0) break;
    if (html.startsWith("<!--", lt)) { const e = html.indexOf("-->", lt + 4); if (e < 0) break; i = e + 3; continue; }
    const c = html[lt + 1] || "";
    if (!/[A-Za-z/!?]/.test(c)) { juntar("<"); i = lt + 1; continue; }     // "<" solto é texto
    const f = html.indexOf(">", lt + 1);
    if (f < 0) break;
    i = f + 1;
    if (c === "!" || c === "?") continue;
    const corpo = html.slice(lt + 1, f);
    const m = /^\/?\s*([a-zA-Z][a-zA-Z0-9:-]*)/.exec(corpo);
    if (!m) continue;
    const nome = m[1].toLowerCase();
    const fecha = c === "/";
    if (!fecha && nome === "html" && !lang) lang = /\blang\s*=\s*["']?([a-zA-Z]{2,3})/.exec(corpo)?.[1]?.toLowerCase() || "";
    if (!fecha && (BRUTO.has(nome) || nome === "title")) {
      const e = min.indexOf("</" + nome, i);
      if (nome === "title" && !titulo) titulo = limparTexto(entidades(html.slice(i, e < 0 ? Math.min(n, i + 500) : Math.min(e, i + 500))).replace(/\n/g, " "));
      if (e < 0) break;
      const g = html.indexOf(">", e);
      i = g < 0 ? n : g + 1;
      continue;
    }
    if (Object.hasOwn(prof, nome) && !VAZIA.has(nome)) prof[nome] = fecha ? Math.max(0, prof[nome] - 1) : prof[nome] + 1;
    if (BLOCO.has(nome)) juntar("\n");
  }
  return { titulo, lang, tudo: limparTexto(tudo.join("")), artigo: limparTexto(artigo.join("")), main: limparTexto(main.join("")) };
}
const MINIMO = 200;
const melhor = (r) => (r.artigo.length >= MINIMO ? r.artigo : r.main.length >= MINIMO ? r.main : r.tudo);
function extrairTexto(html, limite = 6000) {
  let r = varrer(html, true);
  let texto = melhor(r);
  if (texto.length < MINIMO) { const r2 = varrer(html, false); const t2 = melhor(r2); if (t2.length > texto.length) { r = r2; texto = t2; } }   // <nav> sem fechar não pode engolir a página
  return { titulo: cortar(r.titulo, 300), texto: cortar(texto, limite), idioma: r.lang, truncado: texto.length > limite };
}
const TIPOS_RSS = ["application/xml", "text/xml", "application/rss+xml", "application/atom+xml", "application/rdf+xml", "application/x-rss+xml", "text/plain"];
const TIPOS_HTML = ["text/html", "application/xhtml+xml", "text/plain"];
const TIPOS_ICAL = ["text/calendar", "application/ics", "text/plain"];
const ROTAS_NOVAS = ["rss", "ler", "ical"];
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
async function rotaNova(nome, pedido, url, cors, opcoes = {}) {
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
function rotaSaude(cors) {
  return new Response(JSON.stringify({ rotas: [...ROTAS_NOVAS, "nvidia", "brave"], versao: 2 }), { status: 200, headers: { ...cors, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
}
const ROTAS = [
  { prefixo: "/v1/", destino: "https://integrate.api.nvidia.com", cabecalhos: ["authorization", "content-type"], tira: "" },
  { prefixo: "/brave/res/v1/", destino: "https://api.search.brave.com", cabecalhos: ["x-subscription-token", "accept"], tira: "/brave" },
];
async function proxyApi(pedido, url, cors) {
  const rota = ROTAS.find((r) => url.pathname.startsWith(r.prefixo));
  if (!rota) return new Response("caminho não permitido", { status: 404, headers: cors });
  const cabecalhos = {};
  for (const nome of rota.cabecalhos) if (pedido.headers.get(nome)) cabecalhos[nome] = pedido.headers.get(nome);
  cabecalhos["content-type"] ||= "application/json";
  const resposta = await fetch(rota.destino + url.pathname.slice(rota.tira.length) + url.search, {
    method: pedido.method, headers: cabecalhos, body: pedido.method === "POST" ? await pedido.text() : undefined,
  });
  return new Response(resposta.body, { status: resposta.status, headers: { ...cors, "Content-Type": resposta.headers.get("Content-Type") || "application/json" } });
}
const TAREFAS_AGENDADAS = [];
async function agendado(evento, env, ctx) {
  if (env?.JARVIS_CRON !== "sim") return;
  for (const tarefa of TAREFAS_AGENDADAS) ctx.waitUntil(tarefa(env));
}
async function tratar(pedido, opcoes = {}) {
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
