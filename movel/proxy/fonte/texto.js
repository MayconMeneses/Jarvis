// Extração de texto de uma página HTML, sem bibliotecas e em UMA passada linear (sem regex que possa travar com HTML malicioso).
// O resultado é só texto puro: nenhuma tag sobrevive e nada é interpretado. Tratar SEMPRE como dado de terceiros.
const BLOCO = new Set(["p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article", "main", "blockquote", "pre", "table", "hr", "dd", "dt", "figcaption"]);
const BRUTO = new Set(["script", "style", "noscript", "template", "iframe", "svg", "object", "embed", "textarea", "select"]);
const ESTRUTURA = ["nav", "footer", "form", "aside"];
const VAZIA = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "source", "track", "wbr"]);
const NOMES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", ndash: "–", mdash: "—", hellip: "…", laquo: "«", raquo: "»", lsquo: "‘", rsquo: "’", ldquo: "“", rdquo: "”", copy: "©", bull: "•" };

function entidades(s) {
  if (!s.includes("&")) return s;
  return s.replace(/&(#x[0-9a-f]{1,6}|#[0-9]{1,7}|[a-z]{2,8});/gi, (m, g) => {
    if (g[0] !== "#") return Object.hasOwn(NOMES, g.toLowerCase()) ? NOMES[g.toLowerCase()] : m;
    const cp = g[1] === "x" || g[1] === "X" ? parseInt(g.slice(2), 16) : parseInt(g.slice(1), 10);
    return cp > 0 && cp <= 0x10ffff && !(cp >= 0xd800 && cp <= 0xdfff) ? String.fromCodePoint(cp) : "";
  });
}
export function limparTexto(s) {
  const t = s.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]/g, "").replace(/[ \t\r\f\v\u00a0]+/g, " ");
  const linhas = [];
  for (const l of t.split("\n").map((x) => x.trim())) if (l || (linhas.length && linhas[linhas.length - 1])) linhas.push(l);
  return linhas.join("\n").trim();
}
function cortar(s, max) {
  if (s.length <= max) return s;
  const c = s.charCodeAt(max - 1);
  return s.slice(0, c >= 0xd800 && c <= 0xdbff ? max - 1 : max);
}

function varrer(html, ignorarEstrutura) {
  const min = html.replace(/[A-Z]/g, (c) => c.toLowerCase());   // só ASCII: mantém os índices iguais
  const tudo = [], artigo = [], main = [];
  const prof = { article: 0, main: 0, nav: 0, footer: 0, form: 0, aside: 0 };
  let titulo = "", lang = "", i = 0;
  const n = html.length;
  const juntar = (s) => {
    if (ignorarEstrutura && ESTRUTURA.some((e) => prof[e] > 0)) return;
    tudo.push(s);
    if (prof.article > 0) artigo.push(s);
    if (prof.main > 0) main.push(s);
  };
  while (i < n) {
    const lt = html.indexOf("<", i);
    const fim = lt < 0 ? n : lt;
    if (fim > i) juntar(entidades(html.slice(i, fim)));
    if (lt < 0) break;
    if (html.startsWith("<!--", lt)) { const e = html.indexOf("-->", lt + 4); if (e < 0) break; i = e + 3; continue; }
    const c = html[lt + 1] || "";
    if (!/[A-Za-z/!?]/.test(c)) { juntar("<"); i = lt + 1; continue; }     // "<" solto é texto
    const f = html.indexOf(">", lt + 1);
    if (f < 0) break;
    i = f + 1;
    if (c === "!" || c === "?") continue;
    const corpo = html.slice(lt + 1, f);
    const m = /^\/?\s*([a-zA-Z][a-zA-Z0-9:-]*)/.exec(corpo);
    if (!m) continue;
    const nome = m[1].toLowerCase();
    const fecha = c === "/";
    if (!fecha && nome === "html" && !lang) lang = /\blang\s*=\s*["']?([a-zA-Z]{2,3})/.exec(corpo)?.[1]?.toLowerCase() || "";
    if (!fecha && (BRUTO.has(nome) || nome === "title")) {
      const e = min.indexOf("</" + nome, i);
      if (nome === "title" && !titulo) titulo = limparTexto(entidades(html.slice(i, e < 0 ? Math.min(n, i + 500) : Math.min(e, i + 500))).replace(/\n/g, " "));
      if (e < 0) break;
      const g = html.indexOf(">", e);
      i = g < 0 ? n : g + 1;
      continue;
    }
    if (Object.hasOwn(prof, nome) && !VAZIA.has(nome)) prof[nome] = fecha ? Math.max(0, prof[nome] - 1) : prof[nome] + 1;
    if (BLOCO.has(nome)) juntar("\n");
  }
  return { titulo, lang, tudo: limparTexto(tudo.join("")), artigo: limparTexto(artigo.join("")), main: limparTexto(main.join("")) };
}
const MINIMO = 200;
const melhor = (r) => (r.artigo.length >= MINIMO ? r.artigo : r.main.length >= MINIMO ? r.main : r.tudo);

export function extrairTexto(html, limite = 6000) {
  let r = varrer(html, true);
  let texto = melhor(r);
  if (texto.length < MINIMO) { const r2 = varrer(html, false); const t2 = melhor(r2); if (t2.length > texto.length) { r = r2; texto = t2; } }   // <nav> sem fechar não pode engolir a página
  return { titulo: cortar(r.titulo, 300), texto: cortar(texto, limite), idioma: r.lang, truncado: texto.length > limite };
}
