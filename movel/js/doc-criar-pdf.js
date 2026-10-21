// Cria um PDF simples (A4) só com texto, nas fontes padrão do PDF (Helvetica e Courier, codificação WinAnsi): sem fontes embutidas.
// Quebra de linha e de página automáticas; tabelas em Courier (colunas alinhadas). Letras fora do WinAnsi viram "?".
import { semMarcas } from "./doc-markdown.js";
import { byteWin1252 } from "./texto-win1252.js";

const L = 595, A = 842, MARGEM = 56, LARGURA_UTIL = L - 2 * MARGEM;
export const MAX_PAGINAS = 100;

export function winAnsi(texto) {
  let s = "";
  for (const ch of String(texto).replace(/\t/g, "    ")) {
    s += String.fromCharCode(byteWin1252(ch) ?? 63);
  }
  return s.replace(/[\\()]/g, "\\$&");
}

// Largura aproximada em pontos (Helvetica); um pouco larga de propósito, para nunca passar da margem.
export function largura(texto, tam, negrito = false) {
  let w = 0;
  for (const ch of texto) w += /[ijlt.,;:'!|()\[\]fI ]/.test(ch) ? 0.3 : /[mwMW@%]/.test(ch) ? 0.9 : /[A-Z0-9]/.test(ch) ? 0.68 : 0.56;
  return w * tam * (negrito ? 1.06 : 1.02);
}

function quebrar(texto, tam, negrito, maximo, medir = largura) {
  const linhas = [];
  let atual = "";
  for (const palavra of String(texto).split(/\s+/).filter(Boolean)) {
    let p = palavra;
    while (medir(p, tam, negrito) > maximo) {  // palavra gigante (URL): corta
      let k = p.length;
      while (k > 1 && medir(p.slice(0, k), tam, negrito) > maximo) k--;
      if (atual) { linhas.push(atual); atual = ""; }
      linhas.push(p.slice(0, k));
      p = p.slice(k);
    }
    const tentativa = atual ? `${atual} ${p}` : p;
    if (medir(tentativa, tam, negrito) <= maximo) atual = tentativa; else { linhas.push(atual); atual = p; }
  }
  if (atual) linhas.push(atual);
  return linhas.length ? linhas : [""];
}

// Cada item: { fonte: "F1"|"F2"|"F3", tam, x, texto, antes } já quebrado em linhas.
function disposicao(bs) {
  const itens = [];
  const adicionar = (texto, fonte, tam, { recuo = 0, antes = 0, prefixo = "" } = {}) => {
    const maximo = LARGURA_UTIL - recuo;
    quebrar(texto, tam, fonte === "F2", maximo).forEach((linha, i) => itens.push({ fonte, tam, x: MARGEM + recuo + (i && prefixo ? 14 : 0), texto: (i === 0 ? prefixo : "") + linha, antes: i === 0 ? antes : 0 }));
  };
  for (const b of bs) {
    if (b.t === "h") adicionar(b.texto, "F2", [0, 20, 16, 13, 12][b.n], { antes: 12 });
    else if (b.t === "p") adicionar(semMarcas(b.texto), "F1", 11, { antes: 6 });
    else if (b.t === "ul" || b.t === "ol") b.itens.forEach((it, i) => adicionar(semMarcas(it), "F1", 11, { recuo: 14, antes: i ? 2 : 6, prefixo: b.t === "ul" ? "• " : `${i + 1}. ` }));
    else {
      const colunas = Math.max(...b.linhas.map((l) => l.length));
      const caracteres = Math.floor(LARGURA_UTIL / (9 * 0.6));
      const largCol = Math.max(4, Math.floor((caracteres - 3 * (colunas - 1)) / colunas));
      b.linhas.forEach((l, r) => {
        const texto = Array.from({ length: colunas }, (_, c) => String(l[c] ?? "").slice(0, largCol).padEnd(largCol)).join(" | ").trimEnd();
        itens.push({ fonte: "F3", tam: 9, x: MARGEM, texto, antes: r ? 0 : 8 });
      });
    }
  }
  return itens;
}

export function criarPdf(bs, titulo = "Documento") {
  const paginas = [[]];
  let y = A - MARGEM;
  for (const it of disposicao(bs)) {
    const alt = it.tam * 1.35;
    if (y - it.antes - alt < MARGEM) { if (paginas.length >= MAX_PAGINAS) break; paginas.push([]); y = A - MARGEM; }
    y -= (paginas.at(-1).length ? it.antes : 0) + alt;
    paginas.at(-1).push(`BT /${it.fonte} ${it.tam} Tf ${it.x} ${y.toFixed(1)} Td (${winAnsi(it.texto)}) Tj ET`);
  }
  // objetos: 1 catálogo, 2 páginas, 3-5 fontes, 6 info, depois (página, conteúdo) por página
  const objs = [];
  const fonte = (nome) => `<< /Type /Font /Subtype /Type1 /BaseFont /${nome} /Encoding /WinAnsiEncoding >>`;
  const ids = paginas.map((_, i) => 7 + i * 2);
  objs[1] = "<< /Type /Catalog /Pages 2 0 R >>";
  objs[2] = `<< /Type /Pages /Kids [${ids.map((n) => `${n} 0 R`).join(" ")}] /Count ${ids.length} >>`;
  objs[3] = fonte("Helvetica"); objs[4] = fonte("Helvetica-Bold"); objs[5] = fonte("Courier");
  objs[6] = `<< /Title (${winAnsi(titulo).slice(0, 120)}) /Producer (Jarvis) >>`;
  paginas.forEach((linhas, i) => {
    const fluxo = linhas.join("\n") + `\nBT /F1 8 Tf ${L / 2 - 6} 28 Td (${i + 1}) Tj ET`;
    objs[ids[i]] = `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${L} ${A}] /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> /Contents ${ids[i] + 1} 0 R >>`;
    objs[ids[i] + 1] = `<< /Length ${fluxo.length} >>\nstream\n${fluxo}\nendstream`;
  });
  let pdf = "%PDF-1.4\n%âãÏÓ\n";
  const pos = [];
  for (let n = 1; n < objs.length; n++) { pos[n] = pdf.length; pdf += `${n} 0 obj\n${objs[n]}\nendobj\n`; }
  const xref = pdf.length;
  pdf += `xref\n0 ${objs.length}\n0000000000 65535 f \n` + pos.slice(1).map((p) => `${String(p).padStart(10, "0")} 00000 n \n`).join("");
  pdf += `trailer\n<< /Size ${objs.length} /Root 1 0 R /Info 6 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Uint8Array.from(pdf, (c) => c.charCodeAt(0));  // tudo é Latin-1: 1 caractere = 1 byte
}
