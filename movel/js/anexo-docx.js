// Texto de um .docx: parágrafos, títulos (viram "#") e tabelas (linhas "a | b"). Só lê word/document.xml.
import { abrirZip, ZipInvalido } from "./anexo-zip.js";
import { tokens } from "./anexo-xml.js";

export async function lerDocx(bytes) {
  const zip = abrirZip(bytes);
  const xml = await zip.texto("word/document.xml");
  if (xml === null) throw new ZipInvalido("não parece um documento Word (falta word/document.xml)");
  const linhas = [];
  let par = null, estilo = "", dentroT = false, celula = null, linha = null;
  for (const tk of tokens(xml)) {
    if (tk.t === "texto") { if (dentroT && par !== null) par += tk.texto; continue; }
    const n = tk.nome;
    if (tk.t === "abre") {
      if (n === "w:p") { par = ""; estilo = ""; }
      else if (n === "w:pStyle") estilo = tk.attrs["w:val"] || "";
      else if (n === "w:t") dentroT = true;
      else if (n === "w:tab" && par !== null) par += "\t";
      else if (n === "w:br" && par !== null) par += "\n";
      else if (n === "w:tr") linha = [];
      else if (n === "w:tc") celula = [];
    } else if (n === "w:t") dentroT = false;
    else if (n === "w:p" && par !== null) {
      const texto = par.trim();
      const nivel = /^(?:Heading|Ttulo|Título)\s*(\d)$/i.exec(estilo);
      if (celula) { if (texto) celula.push(texto); }
      else if (texto) linhas.push(nivel ? `${"#".repeat(Math.min(6, +nivel[1]))} ${texto}` : texto);
      par = null;
    } else if (n === "w:tc") { if (linha && celula) linha.push(celula.join(" ")); celula = null; }
    else if (n === "w:tr") { if (linha?.some(Boolean)) linhas.push(linha.join(" | ")); linha = null; }
  }
  return { texto: linhas.join("\n"), avisos: zip.ignoradas.length ? ["entradas com caminho suspeito foram ignoradas"] : [] };
}
