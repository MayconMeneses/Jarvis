// Leitor de XML minúsculo para extrair TEXTO de .docx/.xlsx/.pptx. Não usa DOMParser (não existe no Node e não é preciso):
// recusa DOCTYPE/ENTITY (nada de "bilhão de risadas" nem entidade externa) e só decodifica as 5 entidades padrão e as numéricas.
export const MAX_XML = 12 * 1024 * 1024;
export class XmlInvalido extends Error {}

const PADRAO = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };

export function decodificar(texto) {
  return texto.replace(/&(#x[0-9a-fA-F]{1,6}|#\d{1,7}|[a-z]{2,4});/g, (tudo, e) => {
    if (e[0] !== "#") return PADRAO[e] ?? tudo;
    const n = e[1] === "x" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
    const proibido = n > 0x10ffff || (n >= 0xd800 && n < 0xe000) || (n < 32 && ![9, 10, 13].includes(n));
    return proibido ? "" : String.fromCodePoint(n);
  });
}

const ATRIBUTO = /([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;
export function atributos(trecho) {
  const a = {};
  for (const m of trecho.matchAll(ATRIBUTO)) a[m[1]] = decodificar(m[2] ?? m[3]);
  return a;
}

// Tokens: { t: "abre", nome, attrs, auto } | { t: "fecha", nome } | { t: "texto", texto }. Quem chama decide o que é texto útil.
export function* tokens(xml) {
  if (xml.length > MAX_XML) throw new XmlInvalido("XML grande demais");
  if (/<!DOCTYPE|<!ENTITY/i.test(xml)) throw new XmlInvalido("XML com declaração de entidades (recusado por segurança)");
  const limpo = xml.replace(/<!--[\s\S]*?-->/g, "").replace(/<\?[\s\S]*?\?>/g, "")
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, (_, c) => c.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"));
  const re = /<(\/?)([\w:.-]+)((?:[^>"']|"[^"]*"|'[^']*')*?)(\/?)>|([^<]+)/g;
  let n = 0;
  for (const m of limpo.matchAll(re)) {
    if (++n > 3_000_000) throw new XmlInvalido("XML com elementos demais");
    if (m[5] !== undefined) { yield { t: "texto", texto: decodificar(m[5]) }; continue; }
    if (m[1]) { yield { t: "fecha", nome: m[2] }; continue; }
    yield { t: "abre", nome: m[2], attrs: m[3] ? atributos(m[3]) : {}, auto: Boolean(m[4]) };
    if (m[4]) yield { t: "fecha", nome: m[2] };
  }
}
