// Ferramentas de limpeza para respostas do PC pareado (dado de terceiros): cada valor é reconstruído com tipo e tamanho conferidos.
export const simples = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
export const txt = (v, max) => (typeof v === "string" ? v.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "").slice(0, max) : "");
export const num = (v) => (Number.isFinite(v) && v >= 0 ? Math.min(v, 1e9) : 0);
export const numOuNulo = (v) => (Number.isFinite(v) && v >= 0 ? Math.min(v, 1e12) : null);
export const pct = (v) => (Number.isFinite(v) ? Math.max(0, Math.min(100, Math.round(v))) : 0);
export const data = (v) => (typeof v === "string" && v.length <= 40 && !Number.isNaN(Date.parse(v)) ? v : null);
export const lista = (v, max) => (Array.isArray(v) ? v.slice(0, max) : []);
// Só chaves conhecidas, cada uma com um número; o resto é ignorado.
export const contagens = (v, chaves) => Object.fromEntries(chaves.map((k) => [k, simples(v) ? num(v[k]) : 0]));
export const escolha = (v, validos, padrao) => (validos.includes(v) ? v : padrao);
