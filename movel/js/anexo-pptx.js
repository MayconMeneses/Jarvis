// Texto de um .pptx: cada slide vira "--- slide N ---" com o texto de suas caixas.
import { abrirZip, ZipInvalido } from "./anexo-zip.js";
import { tokens } from "./anexo-xml.js";

export const MAX_SLIDES = 200;

export async function lerPptx(bytes) {
  const zip = abrirZip(bytes);
  const slides = zip.nomes().map((n) => /^ppt\/slides\/slide(\d+)\.xml$/.exec(n)).filter(Boolean).map((m) => [+m[1], m[0]]).sort((a, b) => a[0] - b[0]);
  if (!slides.length) throw new ZipInvalido("não parece uma apresentação PowerPoint (sem slides)");
  const partes = [], avisos = [];
  if (slides.length > MAX_SLIDES) avisos.push(`só os primeiros ${MAX_SLIDES} slides foram lidos (são ${slides.length})`);
  for (const [num, nome] of slides.slice(0, MAX_SLIDES)) {
    const linhas = [];
    let par = "", dentroT = false;
    for (const tk of tokens(await zip.texto(nome))) {
      if (tk.t === "texto") { if (dentroT) par += tk.texto; continue; }
      if (tk.t === "abre" && tk.nome === "a:t") dentroT = true;
      else if (tk.t === "abre" && tk.nome === "a:br") par += "\n";
      else if (tk.t === "fecha" && tk.nome === "a:t") dentroT = false;
      else if (tk.t === "fecha" && tk.nome === "a:p") { if (par.trim()) linhas.push(par.trim()); par = ""; }
    }
    partes.push(`--- slide ${num} ---\n${linhas.join("\n")}`);
  }
  return { texto: partes.join("\n\n"), avisos };
}
