// Cria um .docx (Word) válido a partir de blocos de Markdown, com os XMLs mínimos escritos à mão e o ZIP do zip.js.
import { esc, trechos, titulo } from "./doc-markdown.js";
import { zip } from "./zip.js";

const NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"';
const CABECA = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';

const corridas = (linha, extra = "") => trechos(linha).map((p) => `<w:r><w:rPr>${p.b || extra ? "<w:b/>" : ""}</w:rPr><w:t xml:space="preserve">${esc(p.t)}</w:t></w:r>`).join("");
const par = (linha, estilo = "", num = 0, extra = "") =>
  `<w:p><w:pPr>${estilo ? `<w:pStyle w:val="${estilo}"/>` : ""}${num ? `<w:numPr><w:ilvl w:val="0"/><w:numId w:val="${num}"/></w:numPr>` : ""}</w:pPr>${corridas(linha, extra)}</w:p>`;

function tabela(linhas) {
  const cols = Math.max(...linhas.map((l) => l.length));
  const larg = Math.floor(9000 / cols);
  const borda = ["top", "left", "bottom", "right", "insideH", "insideV"].map((b) => `<w:${b} w:val="single" w:sz="4" w:space="0" w:color="808080"/>`).join("");
  const grade = Array.from({ length: cols }, () => `<w:gridCol w:w="${larg}"/>`).join("");
  const rows = linhas.map((l, i) => `<w:tr>${Array.from({ length: cols }, (_, c) =>
    `<w:tc><w:tcPr><w:tcW w:w="${larg}" w:type="dxa"/></w:tcPr>${par(l[c] || "", "", 0, i === 0 ? "b" : "")}</w:tc>`).join("")}</w:tr>`).join("");
  return `<w:tbl><w:tblPr><w:tblW w:w="${larg * cols}" w:type="dxa"/><w:tblBorders>${borda}</w:tblBorders></w:tblPr><w:tblGrid>${grade}</w:tblGrid>${rows}</w:tbl><w:p/>`;
}

const ESTILOS = `${CABECA}<w:styles ${NS}><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="22"/><w:lang w:val="pt-BR"/></w:rPr></w:rPrDefault>`
  + '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
  + '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
  + [[1, 36], [2, 30], [3, 26], [4, 24]].map(([n, s]) => `<w:style w:type="paragraph" w:styleId="Heading${n}"><w:name w:val="heading ${n}"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="${n - 1}"/></w:pPr><w:rPr><w:b/><w:sz w:val="${s}"/></w:rPr></w:style>`).join("")
  + "</w:styles>";

function numeracao(listasOrdenadas) {
  const nivel = (fmt, txt) => `<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="${fmt}"/><w:lvlText w:val="${txt}"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl>`;
  let x = `${CABECA}<w:numbering ${NS}><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/>${nivel("bullet", "•")}</w:abstractNum>`
    + `<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="singleLevel"/>${nivel("decimal", "%1.")}</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>`;
  for (let i = 0; i < listasOrdenadas; i++) x += `<w:num w:numId="${i + 2}"><w:abstractNumId w:val="1"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>`;
  return x + "</w:numbering>";
}

export function criarDocx(bs, agora = new Date()) {
  let ordenadas = 0;
  const corpo = bs.map((b) => {
    if (b.t === "h") return par(b.texto, `Heading${b.n}`);
    if (b.t === "p") return par(b.texto);
    if (b.t === "ul") return b.itens.map((i) => par(i, "", 1)).join("");
    if (b.t === "ol") { const id = 2 + ordenadas++; return b.itens.map((i) => par(i, "", id)).join(""); }
    return tabela(b.tabela || b.linhas);
  }).join("") || par("");
  const ct = `${CABECA}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>`
    + '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    + '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    + '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
    + '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>';
  const R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
  return zip({
    "[Content_Types].xml": ct,
    "_rels/.rels": `${CABECA}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${R}/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>`,
    "word/_rels/document.xml.rels": `${CABECA}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${R}/styles" Target="styles.xml"/><Relationship Id="rId2" Type="${R}/numbering" Target="numbering.xml"/></Relationships>`,
    "word/document.xml": `${CABECA}<w:document ${NS}><w:body>${corpo}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>`,
    "word/styles.xml": ESTILOS,
    "word/numbering.xml": numeracao(ordenadas),
    "docProps/core.xml": `${CABECA}<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${esc(titulo(bs))}</dc:title><dc:creator>Jarvis</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">${agora.toISOString().slice(0, 19)}Z</dcterms:created></cp:coreProperties>`,
  }, agora);
}
