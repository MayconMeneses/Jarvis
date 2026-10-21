// Cliente do Worker do dono (movel/proxy): feeds sem CORS (/rss), texto de página (/ler) e a lista de rotas (/saude).
// Contrato: GET {base}/rss?url=<https> -> XML; GET {base}/ler?url=<https> -> JSON { titulo, texto, idioma, url_final, tamanho }; GET {base}/saude -> { rotas: [...] }.
// Sem Worker (ou com um Worker antigo, sem a rota) tudo aqui falha com ErroRede e quem chamou usa a reserva. Nada é enviado além da URL pedida:
// sem cookies, sem cabeçalhos próprios (requisição simples, sem preflight) e sem chave.
export const MAX_RESPOSTA = 3_000_000;
export const MAX_URL = 2048;
export const HOSTS_DIRETOS = new Set(["agenciabrasil.ebc.com.br", "api.open-meteo.com", "geocoding-api.open-meteo.com", "remotive.com", "api.github.com",
  "pt.wikipedia.org", "hacker-news.firebaseio.com", "api.mymemory.translated.net", "translate.googleapis.com"]);

export class ErroRede extends Error {
  constructor(codigo, mensagem) { super(mensagem); this.name = "ErroRede"; this.codigo = codigo; }
}

// Só https, sem usuário e senha, tamanho limitado. Devolve a URL limpa ou levanta ErroRede.
export function urlSegura(url) {
  let u;
  try { u = new URL(String(url).trim()); } catch { throw new ErroRede("url", "endereço inválido"); }
  if (u.protocol !== "https:" || u.username || u.password || String(url).length > MAX_URL) throw new ErroRede("url", "só endereços https, sem usuário e senha");
  return u.href;
}

export const ehDireto = (url) => { try { return HOSTS_DIRETOS.has(new URL(url).host); } catch { return false; } };

// Base do Worker já cadastrada no app (o proxy do Brave, sem /v1; ou o da NVIDIA, com /v1 no fim). null se não houver.
export async function baseDoProxy(nuvem) {
  try {
    const brave = await nuvem?.brave?.();
    const nvidia = brave?.base ? null : await nuvem?.armazem?.ler?.("segredo:nvidia");
    const base = String(brave?.base || nvidia?.base || "").replace(/\/+$/, "").replace(/\/v1$/, "");
    return /^https:\/\/[^\s/]+$/.test(base) ? base : null;
  } catch { return null; }
}

// fetch com limite de tempo (o Safari pode ficar pendurado em rede ruim). Devolve a resposta ou levanta ErroRede.
export async function buscarComLimite(buscar, url, opcoes = {}, timeoutMs = 12000) {
  const ctl = typeof AbortController === "function" ? new AbortController() : null;
  let timer;
  const prazo = new Promise((_, rejeitar) => { timer = setTimeout(() => { ctl?.abort(); rejeitar(new ErroRede("tempo", "demorou demais")); }, timeoutMs); });
  try {
    return await Promise.race([buscar(url, { credentials: "omit", ...opcoes, signal: ctl?.signal }), prazo]);
  } catch (e) {
    throw e instanceof ErroRede ? e : new ErroRede("rede", "sem conexão");
  } finally { clearTimeout(timer); }
}

export async function textoLimitado(r, max = MAX_RESPOSTA) {
  if (!r.ok) throw new ErroRede("http", `HTTP ${r.status}`);
  const t = await r.text();
  if (t.length > max) throw new ErroRede("tamanho", "resposta grande demais");
  return t;
}

export class Proxy {
  constructor({ base, buscar = (...a) => fetch(...a), timeoutMs = 12000, agora = () => Date.now(), ttlMs = 600000 }) {
    Object.assign(this, { _base: base, buscar, timeoutMs, agora, ttlMs, _saude: null });
  }

  async base() { return (await this._base()) || null; }

  // Conjunto de rotas que o Worker anuncia, ou null se não há Worker / ele não respondeu. Guardado por 10 minutos (1 minuto se falhou).
  async rotas() {
    const base = await this.base();
    if (!base) return null;
    if (this._saude && this._saude.base === base && this.agora() < this._saude.ate) return this._saude.rotas;
    let rotas = null;
    try {
      const r = await buscarComLimite(this.buscar, `${base}/saude`, {}, 6000);
      if (r.ok) { const d = await r.json(); if (Array.isArray(d?.rotas)) rotas = new Set(d.rotas.map((x) => String(x).replace(/^\//, ""))); }
    } catch { /* Worker ausente ou antigo */ }
    this._saude = { base, rotas, ate: this.agora() + (rotas ? this.ttlMs : 60000) };
    return rotas;
  }

  async temRota(nome) { return Boolean((await this.rotas())?.has(nome)); }

  async _pedir(rota, url) {
    const base = await this.base();
    if (!base) throw new ErroRede("sem_proxy", "sem Worker cadastrado");
    return buscarComLimite(this.buscar, `${base}/${rota}?url=${encodeURIComponent(urlSegura(url))}`, {}, this.timeoutMs);
  }

  async rss(url) { return textoLimitado(await this._pedir("rss", url)); }

  // { titulo, texto, idioma, urlFinal, tamanho }. Tudo é texto de terceiros: tipos e tamanhos conferidos aqui.
  async ler(url) {
    const r = await this._pedir("ler", url);
    if (!r.ok) throw new ErroRede("http", `HTTP ${r.status}`);
    let d;
    try { d = await r.json(); } catch { throw new ErroRede("formato", "resposta fora do contrato"); }
    if (!d || typeof d.texto !== "string" || !d.texto.trim()) throw new ErroRede("formato", "o Worker não achou texto legível");
    let urlFinal = "";
    try { const u = new URL(String(d.url_final)); if (/^https?:$/.test(u.protocol)) urlFinal = u.href; } catch { /* sem url final */ }
    return { titulo: typeof d.titulo === "string" ? d.titulo.slice(0, 300) : "", texto: d.texto.slice(0, 20000),
      idioma: typeof d.idioma === "string" && /^[a-z]{2,3}(-[a-zA-Z]{2,4})?$/.test(d.idioma) ? d.idioma.slice(0, 2).toLowerCase() : "", urlFinal, tamanho: Number(d.tamanho) || d.texto.length };
  }
}
