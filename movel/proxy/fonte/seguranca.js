// Regras de segurança das rotas novas (/rss, /ler, /ical): o Worker só busca endereços públicos, em https, e nunca devolve nada do destino além do corpo.
export const ORIGEM = "https://mayconmeneses.github.io";
export const LIMITES = Object.freeze({ tempoMs: 8000, maxBytes: 1500000, redirecionamentos: 3, textoMax: 6000, porMinuto: 30 });
// sufixos que nunca são internet pública (rede interna, teste, nomes que apontam para 127.0.0.1 por DNS)
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

// Devolve a URL já normalizada (sem fragmento) ou null se não for permitida. Mesma função para o pedido e para cada redirecionamento.
export function validarUrl(bruto) {
  if (typeof bruto !== "string" || bruto.length === 0 || bruto.length > 2048) return null;
  if (/[\u0000-\u0020\u007f-\u009f\\]/.test(bruto)) return null;
  let u;
  try { u = new URL(bruto); } catch { return null; }
  if (u.protocol !== "https:" || u.username || u.password || u.port) return null;
  if (hostProibido(u.hostname.toLowerCase().replace(/\.$/, ""))) return null;
  u.hash = "";
  return u;
}
