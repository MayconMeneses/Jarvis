// Cria um .xlsx (Excel) válido: cada tabela do Markdown vira uma planilha (sem tabela: uma coluna com as linhas do texto).
// Textos são sempre texto (inlineStr): uma célula "=1+1" digitada pelo usuário nunca vira fórmula.
import { esc, semMarcas } from "./doc-markdown.js";
import { zip } from "./zip.js";

const CABECA = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';
const R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
export const MAX_LINHAS = 5000, MAX_COLUNAS = 50;

export const letraDaColuna = (i) => { let s = ""; for (i++; i > 0; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + ((i - 1) % 26)) + s; return s; };

export function nomePlanilha(nome, usados) {
  let base = String(nome || "Planilha").replace(/[\[\]:*?/\\]/g, " ").replace(/^'+|'+$/g, "").replace(/\s+/g, " ").trim().slice(0, 31) || "Planilha";
  let n = base, k = 1;
  while (usados.has(n.toLowerCase())) n = `${base.slice(0, 28)} ${++k}`;
  usados.add(n.toLowerCase());
  return n;
}

// "12", "-3.5", "1234,56" viram número; "007", telefones e textos longos continuam texto.
export function valor(celula) {
  const t = String(celula).trim();
  if (/^-?(0|[1-9]\d{0,14})([.,]\d{1,10})?$/.test(t)) return { n: Number(t.replace(",", ".")) };
  return { s: String(celula) };
}

function planilhaXml(linhas) {
  const colunas = Math.min(MAX_COLUNAS, Math.max(1, ...linhas.map((l) => l.length)));
  const larguras = Array.from({ length: colunas }, (_, c) => Math.min(60, Math.max(10, ...linhas.slice(0, 200).map((l) => String(l[c] ?? "").length + 2))));
  const cols = larguras.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join("");
  const rows = linhas.slice(0, MAX_LINHAS).map((l, r) => {
    const cels = l.slice(0, colunas).map((c, i) => {
      const ref = `${letraDaColuna(i)}${r + 1}`, v = r === 0 ? { s: String(c) } : valor(c);
      if (String(c) === "") return "";
      return v.n !== undefined ? `<c r="${ref}"><v>${v.n}</v></c>` : `<c r="${ref}" t="inlineStr"${r === 0 ? ' s="1"' : ""}><is><t xml:space="preserve">${esc(v.s)}</t></is></c>`;
    }).join("");
    return `<row r="${r + 1}">${cels}</row>`;
  }).join("");
  return `${CABECA}<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>${cols}</cols><sheetData>${rows}</sheetData></worksheet>`;
}

// blocos -> [{ nome, linhas }]
export function planilhasDe(bs) {
  const usados = new Set(), lista = [];
  let ultimoTitulo = "";
  for (const b of bs) {
    if (b.t === "h") ultimoTitulo = b.texto;
    else if (b.t === "tabela") lista.push({ nome: nomePlanilha(ultimoTitulo || `Tabela ${lista.length + 1}`, usados), linhas: b.linhas });
  }
  if (!lista.length) {
    const linhas = bs.flatMap((b) => (b.t === "h" || b.t === "p" ? [b.texto] : b.itens || [])).map((t) => [semMarcas(t)]);
    lista.push({ nome: nomePlanilha("Planilha", usados), linhas: linhas.length ? [["Conteúdo"], ...linhas] : [["Conteúdo"]] });
  }
  return lista;
}

export function criarXlsx(bs, agora = new Date()) {
  const folhas = planilhasDe(bs).slice(0, 20);
  const arquivos = {
    "[Content_Types].xml": `${CABECA}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>`
      + '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
      + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
      + folhas.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join("") + "</Types>",
    "_rels/.rels": `${CABECA}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${R}/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
    "xl/workbook.xml": `${CABECA}<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="${R}"><sheets>`
      + folhas.map((f, i) => `<sheet name="${esc(f.nome)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join("") + "</sheets></workbook>",
    "xl/_rels/workbook.xml.rels": `${CABECA}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">`
      + folhas.map((_, i) => `<Relationship Id="rId${i + 1}" Type="${R}/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join("")
      + `<Relationship Id="rId${folhas.length + 1}" Type="${R}/styles" Target="styles.xml"/></Relationships>`,
    "xl/styles.xml": `${CABECA}<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Arial"/></font><font><b/><sz val="11"/><name val="Arial"/></font></fonts>`
      + '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
      + '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
  };
  folhas.forEach((f, i) => { arquivos[`xl/worksheets/sheet${i + 1}.xml`] = planilhaXml(f.linhas); });
  return zip(arquivos, agora);
}
