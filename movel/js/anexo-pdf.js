// Leitor MÍNIMO de PDF com texto (sem pdf.js: nada de CDN, funciona offline e cabe na CSP). Lê os objetos, descomprime os fluxos
// FlateDecode e extrai os operadores de texto (Tj, TJ, ', "). Não cobre: PDF escaneado (imagem), fontes com codificação própria
// (Type0/Identity-H sem tabela legível), objetos dentro de ObjStm e PDF com senha. Nesses casos avisa em vez de inventar texto.
import { decodificarWin1252 } from "./texto-win1252.js";
export const MAX_BYTES_PDF = 15 * 1024 * 1024, MAX_PAGINAS = 200, MAX_FLUXO = 12 * 1024 * 1024;

const binario = (bytes) => { let s = ""; for (let i = 0; i < bytes.length; i += 32768) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 32768)); return s; };
const paraBytes = (s) => Uint8Array.from(s, (c) => c.charCodeAt(0));

async function inflar(bytes) {
  const ds = new DecompressionStream("deflate");
  const w = ds.writable.getWriter();
  w.write(bytes).then(() => w.close()).catch(() => {});
  const r = ds.readable.getReader(), partes = [];
  let total = 0;
  for (;;) {
    const { done, value } = await r.read();
    if (done) break;
    total += value.length;
    if (total > MAX_FLUXO) { await r.cancel().catch(() => {}); throw new Error("fluxo grande demais"); }
    partes.push(value);
  }
  const s = new Uint8Array(total);
  let p = 0;
  for (const x of partes) { s.set(x, p); p += x.length; }
  return s;
}

function objetos(texto) {
  const mapa = new Map();
  for (const m of texto.matchAll(/(\d+)\s+(\d+)\s+obj\b([\s\S]*?)\bendobj/g)) {
    const corpo = m[3], i = corpo.indexOf("stream");
    let dic = corpo, fluxo = null;
    if (i >= 0 && /^\s*<</.test(corpo)) {
      dic = corpo.slice(0, i);
      const ini = i + 6 + (corpo[i + 6] === "\r" ? 2 : 1), fim = corpo.lastIndexOf("endstream");
      if (fim > ini) fluxo = corpo.slice(ini, fim);
    }
    mapa.set(+m[1], { dic, fluxo });
  }
  return mapa;
}

export function ascii85(texto) {
  const t = texto.replace(/\s/g, "").replace(/^<~/, "").replace(/~>.*$/, ""), saida = [];
  let grupo = [];
  const fechar = (n) => { let v = 0; for (let i = 0; i < 5; i++) v = v * 85 + ((grupo[i] ?? 117) - 33); for (let i = 0; i < n - 1; i++) saida.push((v >>> (24 - 8 * i)) & 255); grupo = []; };
  for (const ch of t) {
    if (ch === "z" && !grupo.length) { saida.push(0, 0, 0, 0); continue; }
    grupo.push(ch.charCodeAt(0));
    if (grupo.length === 5) fechar(5);
  }
  if (grupo.length > 1) fechar(grupo.length);
  return Uint8Array.from(saida);
}

const hexa = (texto) => Uint8Array.from((texto.replace(/>.*$/s, "").replace(/\s/g, "").match(/../g) || []).map((h) => parseInt(h, 16) || 0));

// Aplica a cadeia /Filter do fluxo (ASCII85, ASCIIHex, Flate). Outros filtros (imagens, LZW) não interessam ao texto.
async function decodificar(dic, fluxo) {
  const f = /\/Filter\s*(\[[^\]]*\]|\/\w+)/.exec(dic);
  const nomes = f ? [...f[1].matchAll(/\/(\w+)/g)].map((m) => m[1]) : [];
  let dados = paraBytes(fluxo);
  for (const n of nomes) {
    if (n === "ASCII85Decode" || n === "A85") dados = ascii85(binario(dados));
    else if (n === "ASCIIHexDecode" || n === "AHx") dados = hexa(binario(dados));
    else if (n === "FlateDecode" || n === "Fl") dados = await inflar(dados);
    else throw new Error("filtro não suportado");
  }
  return binario(dados);
}

const refs = (s) => [...s.matchAll(/(\d+)\s+\d+\s+R/g)].map((m) => +m[1]);

function ordemPaginas(mapa) {
  const paginas = [];
  const visitar = (n, fundo) => {
    const o = mapa.get(n);
    if (!o || fundo > 20 || paginas.length > MAX_PAGINAS) return;
    if (/\/Type\s*\/Pages\b/.test(o.dic)) { const k = /\/Kids\s*\[([^\]]*)\]/.exec(o.dic); if (k) refs(k[1]).forEach((f) => visitar(f, fundo + 1)); }
    else if (/\/Type\s*\/Page\b/.test(o.dic)) paginas.push(n);
  };
  const raiz = [...mapa].find(([, o]) => /\/Type\s*\/Pages\b/.test(o.dic) && !/\/Parent\b/.test(o.dic));
  if (raiz) visitar(raiz[0], 0);
  return paginas;
}

function cadeia(s, i) {  // lê "( ... )" a partir do "(" em s[i]; devolve [bytesComoTexto, próximoÍndice]
  let nivel = 1, out = "";
  for (i++; i < s.length && nivel > 0; i++) {
    const c = s[i];
    if (c === "\\") {
      const n = s[++i];
      if (n >= "0" && n <= "7") { let o = n; while (o.length < 3 && s[i + 1] >= "0" && s[i + 1] <= "7") o += s[++i]; out += String.fromCharCode(parseInt(o, 8) & 255); }
      else if (n === "\r" || n === "\n") { if (n === "\r" && s[i + 1] === "\n") i++; }
      else out += { n: "\n", r: "\r", t: "\t", b: "\b", f: "\f" }[n] ?? n;
    } else if (c === "(") { nivel++; out += c; }
    else if (c === ")") { if (--nivel > 0) out += c; }
    else out += c;
  }
  return [out, i];
}

const latim = (s) => decodificarWin1252(paraBytes(s));

export function textoDoFluxo(s) {
  let saida = "", pilha = [], yAnterior = null;
  const quebra = () => { if (saida && !saida.endsWith("\n")) saida += "\n"; };
  for (let i = 0; i < s.length;) {
    const c = s[i];
    if (c === "(") { const [t, f] = cadeia(s, i); pilha.push(t); i = f; }
    else if (c === "<" && s[i + 1] !== "<") {
      const f = s.indexOf(">", i), hex = s.slice(i + 1, f < 0 ? s.length : f).replace(/\s/g, "");
      const t = (hex.match(/../g) || []).map((h) => String.fromCharCode(parseInt(h, 16) || 0)).join("");
      const lixo = [...t].filter((ch) => ch.charCodeAt(0) < 9 || (ch.charCodeAt(0) > 13 && ch.charCodeAt(0) < 32)).length;
      pilha.push(/^[0-9a-fA-F]*$/.test(hex) && lixo <= t.length * 0.3 ? t : "");  // fonte de 2 bytes: ilegível, ignora
      i = f < 0 ? s.length : f + 1;
    } else if (c === "[") { pilha.push("["); i++; }
    else if (c === "]") { let a = pilha.length - 1; while (a >= 0 && pilha[a] !== "[") a--; if (a >= 0) { pilha.splice(a, pilha.length - a, { arr: pilha.slice(a + 1) }); } i++; }
    else if (/[A-Za-z'"*]/.test(c)) {
      let f = i + 1;
      while (f < s.length && /[A-Za-z0-9'"*]/.test(s[f])) f++;
      const op = s.slice(i, f);
      if (op === "Tj" || op === "'" || op === '"') { if (op !== "Tj") quebra(); const t = pilha.findLast((x) => typeof x === "string"); if (t !== undefined) saida += latim(t); }
      else if (op === "TJ") {
        const a = pilha.at(-1);
        for (const x of a?.arr || []) { if (typeof x === "string") saida += latim(x); else if (typeof x === "number" && x < -200) saida += " "; }
      } else if (op === "T*") quebra();
      else if (op === "Td" || op === "TD") { if (Math.abs(pilha.at(-1)) > 0.01 && typeof pilha.at(-1) === "number") quebra(); else saida += saida && !/\s$/.test(saida) ? " " : ""; }
      else if (op === "Tm") { const y = pilha.at(-1); if (y !== yAnterior) quebra(); yAnterior = y; }
      else if (op === "ET") quebra();
      pilha = [];
      i = f;
    } else if (/[-+.\d]/.test(c)) {
      let f = i + 1;
      while (f < s.length && /[-+.\d]/.test(s[f])) f++;
      pilha.push(parseFloat(s.slice(i, f)));
      i = f;
    } else i++;
  }
  return saida.replace(/[ \t]+\n/g, "\n").trim();
}

export async function lerPdf(bytes) {
  if (bytes.length > MAX_BYTES_PDF) throw new Error(`PDF grande demais (${Math.round(bytes.length / 1048576)} MB; limite ${MAX_BYTES_PDF / 1048576} MB)`);
  const texto = binario(bytes);
  if (!texto.startsWith("%PDF-") && !texto.slice(0, 1024).includes("%PDF-")) throw new Error("não parece um PDF");
  if (/\/Encrypt\b/.test(texto.slice(-4096)) || /trailer[\s\S]{0,400}\/Encrypt/.test(texto)) throw new Error("PDF protegido por senha");
  const mapa = objetos(texto), avisos = [];
  const conteudo = async (n) => {
    const o = mapa.get(n);
    if (!o?.fluxo || /\/Subtype\s*\/Image|\/XRef|\/ObjStm|\/FontFile/.test(o.dic)) return "";
    try {
      return await decodificar(o.dic, o.fluxo);
    } catch { avisos.push("um trecho do PDF não pôde ser descomprimido"); return ""; }
  };
  let paginas = ordemPaginas(mapa).slice(0, MAX_PAGINAS);
  const partes = [];
  if (paginas.length) {
    for (const [i, p] of paginas.entries()) {
      const c = /\/Contents\s*(\[[^\]]*\]|\d+\s+\d+\s+R)/.exec(mapa.get(p).dic);
      const fluxos = c ? refs(c[1]) : [];
      const t = textoDoFluxo((await Promise.all(fluxos.map(conteudo))).join("\n"));
      partes.push(`--- página ${i + 1} ---\n${t}`);
    }
  } else {
    avisos.push("não consegui montar a ordem das páginas; o texto vem na ordem do arquivo");
    let k = 0;
    for (const n of mapa.keys()) { const t = textoDoFluxo(await conteudo(n)); if (t && ++k <= MAX_PAGINAS) partes.push(`--- trecho ${k} ---\n${t}`); }
  }
  const util = partes.join("").replace(/--- (página|trecho) \d+ ---/g, "").trim();
  if (!util) avisos.push("sem texto extraível: o PDF pode ser escaneado (imagem) ou usar fonte codificada; tire um print e anexe como imagem");
  return { texto: partes.join("\n\n"), avisos };
}
