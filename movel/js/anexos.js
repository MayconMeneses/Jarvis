// Lê um arquivo escolhido pelo usuário (seletor de arquivos ou "Compartilhar" do iOS) e devolve o TEXTO dele.
// Tudo o que vem de dentro do arquivo é dado de terceiros: este módulo só extrai texto, nunca interpreta como comando.
import { lerDocx } from "./anexo-docx.js";
import { descreverImagem } from "./anexo-imagem.js";
import { lerPdf } from "./anexo-pdf.js";
import { lerPptx } from "./anexo-pptx.js";
import { lerXlsx } from "./anexo-xlsx.js";

export const MAX_BYTES = 25 * 1024 * 1024, MAX_CHARS = 200000;
const TEXTOS = "txt md markdown csv tsv json xml html htm css js mjs ts tsx jsx py java c h cpp cs go rs rb php sh sql yaml yml toml ini cfg log env svg tex".split(" ");
const IMAGENS = ["png", "jpg", "jpeg", "gif", "webp", "heic", "heif", "bmp"];
const LEITORES = { docx: lerDocx, xlsx: lerXlsx, pptx: lerPptx, pdf: lerPdf };
const ANTIGOS = { doc: "Word antigo (.doc)", xls: "Excel antigo (.xls)", ppt: "PowerPoint antigo (.ppt)" };

export const extensao = (nome) => (/\.([A-Za-z0-9]+)$/.exec(nome || "")?.[1] || "").toLowerCase();

export function decodificarTexto(bytes) {
  try { return new TextDecoder("utf-8", { fatal: true }).decode(bytes).replace(/^﻿/, ""); } catch { return new TextDecoder("windows-1252").decode(bytes); }
}
const pareceBinario = (bytes) => bytes.subarray(0, 4096).includes(0);

export async function lerAnexo(arquivo, { nuvem, buscar, reduzir } = {}) {
  const nome = String(arquivo.name || "anexo").slice(0, 120), ext = extensao(nome);
  if (arquivo.size > MAX_BYTES) throw new Error(`"${nome}" tem ${Math.round(arquivo.size / 1048576)} MB; o limite é ${MAX_BYTES / 1048576} MB`);
  if (ANTIGOS[ext]) throw new Error(`${ANTIGOS[ext]} não é suportado: salve como .${ext}x e anexe de novo`);
  if (IMAGENS.includes(ext) || String(arquivo.type).startsWith("image/")) {
    const descricao = await descreverImagem(arquivo, { nuvem, buscar, reduzir });
    return { nome, tipo: "imagem", tamanho: arquivo.size, texto: descricao, avisos: ["descrição gerada pelo Gemini; pode conter erros"] };
  }
  const bytes = new Uint8Array(await arquivo.arrayBuffer());
  let r;
  if (LEITORES[ext]) {
    try { r = await LEITORES[ext](bytes); } catch (e) { throw new Error(`não consegui abrir "${nome}": ${e.message}`); }
  } else if (TEXTOS.includes(ext) || ((!ext || String(arquivo.type).startsWith("text/")) && !pareceBinario(bytes))) {
    r = { texto: decodificarTexto(bytes), avisos: [] };
  } else throw new Error(`não sei ler arquivos .${ext || "sem extensão"} (aceito: texto/código, PDF, Word, Excel, PowerPoint e imagens)`);
  const avisos = [...r.avisos];
  let texto = r.texto.replace(/\r\n?/g, "\n");
  if (texto.length > MAX_CHARS) { avisos.push(`lido só o começo: ${MAX_CHARS} de ${texto.length} caracteres`); texto = texto.slice(0, MAX_CHARS); }
  return { nome, tipo: ext || "texto", tamanho: arquivo.size, texto, avisos };
}
