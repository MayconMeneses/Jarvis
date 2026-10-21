// Texto de terceiros (feed, página) -> texto simples e curto. Porte de feed_parse.limpar do PC.
// O resultado só vai para a tela por textContent e para a voz: nada aqui é interpretado como HTML nem como pedido.
const NOMEADAS = Object.fromEntries(("amp:&,lt:<,gt:>,quot:\",apos:',nbsp: ,ndash:–,mdash:—,hellip:…,lsquo:‘,rsquo:’,ldquo:“,rdquo:”,laquo:«,raquo:»,bull:•,"
  + "middot:·,copy:©,reg:®,trade:™,euro:€,ordm:º,ordf:ª,deg:°,"
  + "aacute:á,Aacute:Á,agrave:à,Agrave:À,acirc:â,Acirc:Â,atilde:ã,Atilde:Ã,auml:ä,ccedil:ç,Ccedil:Ç,eacute:é,Eacute:É,egrave:è,ecirc:ê,Ecirc:Ê,"
  + "iacute:í,Iacute:Í,oacute:ó,Oacute:Ó,ocirc:ô,Ocirc:Ô,otilde:õ,Otilde:Õ,ouml:ö,uacute:ú,Uacute:Ú,uuml:ü,ntilde:ñ").split(",").map((p) => [p.slice(0, p.indexOf(":")), p.slice(p.indexOf(":") + 1)]));

export function decodificar(texto) {
  return String(texto).replace(/&(#x[0-9a-f]+|#\d+|[a-z][a-z0-9]*);/gi, (m, e) => {
    if (e[0] === "#") {
      const n = e[1].toLowerCase() === "x" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return n > 0 && n <= 0x10ffff && !(n >= 0xd800 && n <= 0xdfff) ? String.fromCodePoint(n) : " ";
    }
    return NOMEADAS[e] ?? m;
  });
}

// HTML -> texto simples e curto. Remove script/style com o conteúdo, tags, entidades e espaços em excesso.
export function limpar(texto, limite) {
  const semBlocos = String(texto ?? "").replace(/<(script|style)\b[\s\S]*?<\/\1\s*>/gi, " ");
  return decodificar(semBlocos.replace(/<[^>]+>/g, " ")).replace(/\s+/g, " ").trim().slice(0, limite);
}

export const semAcento = (t) => String(t).toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");

// http/https com endereço; qualquer outra coisa (javascript:, file:, data:) não é link.
export function linkValido(link) {
  try { const u = new URL(String(link).trim()); return (u.protocol === "https:" || u.protocol === "http:") && Boolean(u.host); } catch { return false; }
}
