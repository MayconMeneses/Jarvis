// Peças fixas de um .pptx mínimo e válido: tema, slide mestre e um layout "Título e conteúdo" (16:9).
export const CABECA = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';
export const NS = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"';
export const LARGURA = 12192000, ALTURA = 6858000;
const grupo = '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>';
const quadro = (x, y, w, h) => `<a:xfrm><a:off x="${x}" y="${y}"/><a:ext cx="${w}" cy="${h}"/></a:xfrm>`;
export const TITULO_QUADRO = [609600, 365760, 10972800, 1127760], CORPO_QUADRO = [609600, 1645920, 10972800, 4572000];

export const TEMA = `${CABECA}<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Jarvis"><a:themeElements><a:clrScheme name="Jarvis">`
  + '<a:dk1><a:srgbClr val="1A1A1A"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F3A5F"/></a:dk2><a:lt2><a:srgbClr val="EEF2F7"/></a:lt2>'
  + '<a:accent1><a:srgbClr val="0B7285"/></a:accent1><a:accent2><a:srgbClr val="E8590C"/></a:accent2><a:accent3><a:srgbClr val="2F9E44"/></a:accent3><a:accent4><a:srgbClr val="7048E8"/></a:accent4><a:accent5><a:srgbClr val="C2255C"/></a:accent5><a:accent6><a:srgbClr val="495057"/></a:accent6>'
  + '<a:hlink><a:srgbClr val="0B7285"/></a:hlink><a:folHlink><a:srgbClr val="7048E8"/></a:folHlink></a:clrScheme>'
  + '<a:fontScheme name="Jarvis"><a:majorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
  + '<a:fmtScheme name="Jarvis"><a:fillStyleLst>' + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'.repeat(3) + '</a:fillStyleLst><a:lnStyleLst>'
  + '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'.repeat(3) + '</a:lnStyleLst><a:effectStyleLst>' + "<a:effectStyle><a:effectLst/></a:effectStyle>".repeat(3)
  + '</a:effectStyleLst><a:bgFillStyleLst>' + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'.repeat(3) + '</a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>';

const marcador = (id, nome, tipo, [x, y, w, h], extra = "") =>
  `<p:sp><p:nvSpPr><p:cNvPr id="${id}" name="${nome}"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph ${tipo}/></p:nvPr></p:nvSpPr><p:spPr>${quadro(x, y, w, h)}</p:spPr>${extra}</p:sp>`;
const texto = (rotulo) => `<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="pt-BR"/><a:t>${rotulo}</a:t></a:r></a:p></p:txBody>`;

export const MESTRE = `${CABECA}<p:sldMaster ${NS}><p:cSld><p:bg><p:bgPr><a:solidFill><a:schemeClr val="bg1"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree>${grupo}`
  + marcador(2, "Título", 'type="title"', TITULO_QUADRO, texto("Título")) + marcador(3, "Conteúdo", 'type="body" idx="1"', CORPO_QUADRO, texto("Texto"))
  + '</p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
  + '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
  + '<p:txStyles><p:titleStyle><a:lvl1pPr algn="l"><a:defRPr sz="3600" b="1"><a:solidFill><a:schemeClr val="tx2"/></a:solidFill><a:latin typeface="+mj-lt"/></a:defRPr></a:lvl1pPr></p:titleStyle>'
  + '<p:bodyStyle><a:lvl1pPr marL="342900" indent="-342900"><a:spcBef><a:spcPts val="900"/></a:spcBef><a:buFont typeface="Arial"/><a:buChar char="&#8226;"/><a:defRPr sz="2200"><a:solidFill><a:schemeClr val="tx1"/></a:solidFill><a:latin typeface="+mn-lt"/></a:defRPr></a:lvl1pPr></p:bodyStyle>'
  + '<p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:otherStyle></p:txStyles></p:sldMaster>';

export const LAYOUT = `${CABECA}<p:sldLayout ${NS} type="obj" preserve="1"><p:cSld name="Título e conteúdo"><p:spTree>${grupo}`
  + `<p:sp><p:nvSpPr><p:cNvPr id="2" name="Título"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>${texto("Título")}</p:sp>`
  + `<p:sp><p:nvSpPr><p:cNvPr id="3" name="Conteúdo"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph idx="1"/></p:nvPr></p:nvSpPr><p:spPr/>${texto("Texto")}</p:sp>`
  + '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>';
