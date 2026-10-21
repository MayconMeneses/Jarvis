// Texto de um .xlsx: cada planilha vira "--- planilha X ---" e linhas "a | b | c" (valores já calculados; datas aparecem como número de série).
import { abrirZip, ZipInvalido } from "./anexo-zip.js";
import { tokens } from "./anexo-xml.js";

export const MAX_LINHAS = 2000, MAX_COLUNAS = 60, MAX_PLANILHAS = 20;

const colunaDe = (ref) => [...(/^[A-Z]+/.exec(ref)?.[0] || "A")].reduce((n, c) => n * 26 + c.charCodeAt(0) - 64, 0) - 1;

async function textosCompartilhados(zip) {
  const xml = await zip.texto("xl/sharedStrings.xml");
  const lista = [];
  if (!xml) return lista;
  let atual = null, dentroT = false, fantasia = 0;
  for (const tk of tokens(xml)) {
    if (tk.t === "abre" && tk.nome === "si") atual = "";
    else if (tk.t === "abre" && tk.nome === "rPh") fantasia++;  // leitura fonética (japonês): não é o texto da célula
    else if (tk.t === "fecha" && tk.nome === "rPh") fantasia--;
    else if (tk.t === "abre" && tk.nome === "t") dentroT = true;
    else if (tk.t === "fecha" && tk.nome === "t") dentroT = false;
    else if (tk.t === "texto" && dentroT && atual !== null && !fantasia) atual += tk.texto;
    else if (tk.t === "fecha" && tk.nome === "si") { lista.push(atual ?? ""); atual = null; }
  }
  return lista;
}

async function planilhas(zip) {
  const wb = await zip.texto("xl/workbook.xml");
  if (wb === null) throw new ZipInvalido("não parece uma planilha Excel (falta xl/workbook.xml)");
  const rels = {};
  for (const tk of tokens((await zip.texto("xl/_rels/workbook.xml.rels")) || "")) if (tk.t === "abre" && tk.nome === "Relationship") rels[tk.attrs.Id] = tk.attrs.Target;
  const lista = [];
  for (const tk of tokens(wb)) {
    if (tk.t !== "abre" || tk.nome !== "sheet") continue;
    let alvo = rels[tk.attrs["r:id"]] || `worksheets/sheet${lista.length + 1}.xml`;
    alvo = alvo.startsWith("/") ? alvo.slice(1) : "xl/" + alvo;
    lista.push({ nome: tk.attrs.name || `Planilha ${lista.length + 1}`, alvo });
  }
  return lista;
}

function lerPlanilha(xml, compartilhados) {
  const linhas = [];
  let linha = null, ref = "", tipo = "", valor = "", dentro = "", proxima = 0, truncou = false;
  for (const tk of tokens(xml)) {
    if (tk.t === "abre") {
      if (tk.nome === "row") { proxima = (+tk.attrs.r || proxima + 1); linha = []; if (proxima > MAX_LINHAS) truncou = true; }
      else if (tk.nome === "c") { ref = tk.attrs.r || ""; tipo = tk.attrs.t || "n"; valor = ""; }
      else if (tk.nome === "v" || tk.nome === "t") dentro = tk.nome;
    } else if (tk.t === "fecha") {
      if (tk.nome === "v" || tk.nome === "t") dentro = "";
      else if (tk.nome === "c" && linha) {
        const col = colunaDe(ref);
        if (col < MAX_COLUNAS) linha[col] = tipo === "s" ? compartilhados[+valor] ?? "" : tipo === "b" ? (valor === "1" ? "VERDADEIRO" : "FALSO") : valor;
      } else if (tk.nome === "row" && linha) { if (!truncou && linha.some((c) => c !== undefined && c !== "")) linhas.push(Array.from(linha, (c) => c ?? "").join(" | ").replace(/( \| )+$/, "")); linha = null; }
    } else if (dentro && linha) valor += tk.texto;
  }
  return { linhas, truncou };
}

export async function lerXlsx(bytes) {
  const zip = abrirZip(bytes);
  const compartilhados = await textosCompartilhados(zip);
  const todas = await planilhas(zip), avisos = [];
  if (todas.length > MAX_PLANILHAS) avisos.push(`só as primeiras ${MAX_PLANILHAS} planilhas foram lidas`);
  const partes = [];
  for (const p of todas.slice(0, MAX_PLANILHAS)) {
    const xml = await zip.texto(p.alvo);
    if (xml === null) continue;
    const { linhas, truncou } = lerPlanilha(xml, compartilhados);
    if (truncou) avisos.push(`a planilha "${p.nome}" foi cortada em ${MAX_LINHAS} linhas`);
    partes.push(`--- planilha ${p.nome} ---\n${linhas.join("\n")}`);
  }
  return { texto: partes.join("\n\n"), avisos };
}
