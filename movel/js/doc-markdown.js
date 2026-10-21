// Markdown simples -> blocos (o mesmo modelo do PC, jarvis/documents.py): títulos #, listas "-" e "1.", tabelas |a|b|, **negrito**.
// Todos os escritores de documento (docx, xlsx, pptx, pdf) partem destes blocos. Texto de entrada é sempre tratado como TEXTO.
export const MAX_ENTRADA = 120000, MAX_BLOCOS = 4000;

// Caracteres que o XML não aceita (e que quebrariam o arquivo) saem antes de tudo.
export const sanear = (t) => String(t).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f￾￿]/g, "").replace(/\r\n?/g, "\n");

export function esc(t) {
  return sanear(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// "texto **forte** texto" -> [{ t, b }]
export function trechos(linha) {
  const partes = [];
  linha.split(/\*\*(.+?)\*\*/g).forEach((p, i) => { if (p) partes.push({ t: p.replace(/`/g, ""), b: i % 2 === 1 }); });
  return partes.length ? partes : [{ t: "", b: false }];
}
export const semMarcas = (t) => trechos(t).map((p) => p.t).join("");

export function blocos(markdown) {
  const saida = [];
  let paragrafo = [];
  const fechar = () => { if (paragrafo.length) saida.push({ t: "p", texto: paragrafo.join(" ") }); paragrafo = []; };
  const lista = (tipo, item) => { const u = saida.at(-1); if (u?.t === tipo) u.itens.push(item); else saida.push({ t: tipo, itens: [item] }); };
  for (const bruta of sanear(markdown).slice(0, MAX_ENTRADA).split("\n")) {
    if (saida.length >= MAX_BLOCOS) break;
    const l = bruta.trim();
    let m;
    if (!l) fechar();
    else if ((m = /^(#{1,4})\s+(.*)$/.exec(l))) { fechar(); saida.push({ t: "h", n: m[1].length, texto: semMarcas(m[2]).trim() }); }
    else if ((m = /^[-*•]\s+(.*)$/.exec(l))) { fechar(); lista("ul", m[1]); }
    else if ((m = /^\d+[.)]\s+(.*)$/.exec(l))) { fechar(); lista("ol", m[1]); }
    else if (l.startsWith("|") && l.endsWith("|") && l.length > 2) {
      fechar();
      const celulas = l.slice(1, -1).split("|").map((c) => semMarcas(c).trim());
      if (celulas.every((c) => /^:?-{2,}:?$/.test(c))) continue;
      const u = saida.at(-1);
      if (u?.t === "tabela") u.linhas.push(celulas); else saida.push({ t: "tabela", linhas: [celulas] });
    } else paragrafo.push(l);
  }
  fechar();
  return saida;
}

// Tira a cerca ```...``` e conversa de abertura que modelos costumam colocar em volta do documento.
export function limparResposta(texto) {
  let t = sanear(texto).trim();
  const cerca = /```(?:markdown|md)?[ \t]*\n([\s\S]*?)\n```/i.exec(t);
  if (cerca) t = cerca[1].trim();
  const primeiro = t.search(/^#{1,4}\s|^\|/m);
  return primeiro > 0 && primeiro < 300 ? t.slice(primeiro) : t;
}

export const titulo = (bs, padrao = "Documento") => bs.find((b) => b.t === "h")?.texto || padrao;
export const nomeArquivo = (t) => (t.normalize("NFD").replace(/\p{M}/gu, "").replace(/[^A-Za-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40) || "documento");
