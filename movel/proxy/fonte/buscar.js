// Busca segura: só https público, redirecionamentos revalidados (máx. 3), tempo e tamanho limitados, só tipos de conteúdo esperados.
import { LIMITES, validarUrl } from "./seguranca.js";

export class ErroRota extends Error {
  constructor(status, mensagem) { super(mensagem); this.status = status; }
}
const falha = (status, msg) => new ErroRota(status, msg);

// não espera o cancelamento terminar (em respostas duplicadas ele só conclui quando as duas pontas cancelam)
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

// `entrada` já passou por validarUrl. `tipos` = lista de content-types aceitos. `buscar` = fetch (trocável nos testes).
export async function buscarSeguro(entrada, tipos, { buscar = (u, i) => fetch(u, i), tempoMs = LIMITES.tempoMs, maxBytes = LIMITES.maxBytes, accept = "*/*" } = {}) {
  const ctl = new AbortController();
  const aborto = new Promise((_, rej) => ctl.signal.addEventListener("abort", () => rej(falha(504, "tempo esgotado"))));
  aborto.catch(() => {});
  const timer = setTimeout(() => ctl.abort(), tempoMs);
  try {
    let url = entrada;
    for (let salto = 0; salto <= LIMITES.redirecionamentos; salto++) {
      let r;
      try {
        // cabeçalhos fixos: nada do usuário (Authorization, cookies) vai ao destino
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

export function decodificar(bytes, charset) {
  const tentativa = (c) => { try { return new TextDecoder(c || "utf-8").decode(bytes); } catch { return null; } };
  return tentativa(charset) ?? tentativa("utf-8");
}
