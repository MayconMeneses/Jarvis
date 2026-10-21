// Cria um .pptx (PowerPoint) válido a partir de blocos de Markdown: "# Título" vira a capa e cada "## Seção" vira um slide com tópicos.
import { esc, semMarcas } from "./doc-markdown.js";
import { CABECA, LAYOUT, MESTRE, NS, TEMA } from "./doc-pptx-base.js";
import { zip } from "./zip.js";

export const MAX_TOPICOS = 7, MAX_SLIDES = 60, MAX_TEXTO = 150;
const R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";

// blocos -> [{ titulo, topicos: [], capa }]
export function slidesDe(bs) {
  const slides = [];
  let atual = null;
  const novo = (titulo, capa = false) => { atual = { titulo, topicos: [], capa }; slides.push(atual); };
  for (const b of bs) {
    if (b.t === "h" && b.n === 1 && !slides.length) novo(b.texto, true);
    else if (b.t === "h") novo(b.texto);
    else {
      if (!atual) novo("Apresentação", true);
      const itens = b.t === "p" ? [b.texto] : b.t === "tabela" ? b.linhas.map((l) => l.join(" | ")) : b.itens;
      atual.topicos.push(...itens.map((i) => semMarcas(i)));
    }
  }
  const saida = [];
  for (const s of slides) {
    if (s.capa) { saida.push({ ...s, topicos: s.topicos.slice(0, 2) }); continue; }
    for (let i = 0; i === 0 || i < s.topicos.length; i += MAX_TOPICOS) saida.push({ titulo: i ? `${s.titulo} (cont.)` : s.titulo, topicos: s.topicos.slice(i, i + MAX_TOPICOS) });
  }
  return saida.slice(0, MAX_SLIDES);
}

const paragrafo = (t, capa) => `<a:p>${capa ? '<a:pPr marL="0" indent="0"><a:buNone/></a:pPr>' : ""}<a:r><a:rPr lang="pt-BR"${capa ? ' sz="2400"' : ""}/><a:t>${esc(t.length > MAX_TEXTO ? t.slice(0, MAX_TEXTO - 1) + "…" : t)}</a:t></a:r></a:p>`;

function slideXml(s) {
  const quadro = '<a:xfrm><a:off x="609600" y="2286000"/><a:ext cx="10972800" cy="1371600"/></a:xfrm>';
  const sp = (id, nome, ph, geo, corpo) => `<p:sp><p:nvSpPr><p:cNvPr id="${id}" name="${nome}"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph ${ph}/></p:nvPr></p:nvSpPr><p:spPr>${geo}</p:spPr><p:txBody><a:bodyPr><a:normAutofit/></a:bodyPr><a:lstStyle/>${corpo}</p:txBody></p:sp>`;
  const titulo = sp(2, "Título", 'type="title"', s.capa ? quadro : "", paragrafo(s.titulo, false));
  const corpo = s.capa
    ? (s.topicos.length ? sp(3, "Subtítulo", 'idx="1"', '<a:xfrm><a:off x="609600" y="3840480"/><a:ext cx="10972800" cy="1371600"/></a:xfrm>', s.topicos.map((t) => paragrafo(t, true)).join("")) : "")
    : sp(3, "Conteúdo", 'idx="1"', "", s.topicos.length ? s.topicos.map((t) => paragrafo(t, false)).join("") : "<a:p><a:endParaRPr lang=\"pt-BR\"/></a:p>");
  return `${CABECA}<p:sld ${NS}><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>${titulo}${corpo}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>`;
}

export function criarPptx(bs, agora = new Date()) {
  const slides = slidesDe(bs);
  if (!slides.length) slides.push({ titulo: "Apresentação", topicos: [], capa: true });
  const rels = (itens) => `${CABECA}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${itens}</Relationships>`;
  const arquivos = {
    "[Content_Types].xml": `${CABECA}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>`
      + '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
      + '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
      + '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
      + '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
      + slides.map((_, i) => `<Override PartName="/ppt/slides/slide${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`).join("") + "</Types>",
    "_rels/.rels": rels(`<Relationship Id="rId1" Type="${R}/officeDocument" Target="ppt/presentation.xml"/>`),
    "ppt/presentation.xml": `${CABECA}<p:presentation ${NS}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>`
      + slides.map((_, i) => `<p:sldId id="${256 + i}" r:id="rId${i + 2}"/>`).join("") + '</p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>',
    "ppt/_rels/presentation.xml.rels": rels(`<Relationship Id="rId1" Type="${R}/slideMaster" Target="slideMasters/slideMaster1.xml"/>`
      + slides.map((_, i) => `<Relationship Id="rId${i + 2}" Type="${R}/slide" Target="slides/slide${i + 1}.xml"/>`).join("")),
    "ppt/slideMasters/slideMaster1.xml": MESTRE,
    "ppt/slideMasters/_rels/slideMaster1.xml.rels": rels(`<Relationship Id="rId1" Type="${R}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="${R}/theme" Target="../theme/theme1.xml"/>`),
    "ppt/slideLayouts/slideLayout1.xml": LAYOUT,
    "ppt/slideLayouts/_rels/slideLayout1.xml.rels": rels(`<Relationship Id="rId1" Type="${R}/slideMaster" Target="../slideMasters/slideMaster1.xml"/>`),
    "ppt/theme/theme1.xml": TEMA,
  };
  slides.forEach((s, i) => {
    arquivos[`ppt/slides/slide${i + 1}.xml`] = slideXml(s);
    arquivos[`ppt/slides/_rels/slide${i + 1}.xml.rels`] = rels(`<Relationship Id="rId1" Type="${R}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>`);
  });
  return zip(arquivos, agora);
}
