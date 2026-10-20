// Importar posts colados (CSV, TSV ou JSON) no celular. Igual a jarvis/instagram/importar.py: só métricas públicas e o começo da legenda.
import { CAMPOS_NUMERICOS, chavePost, epoch, iso, limparLegenda, limparLink, normalizarFormato, normalizarPerfil, numero } from "./instagram-base.js";
import { fold } from "./util.js";

export const MAX_TEXTO = 3_000_000, MAX_LINHAS = 3000;
const SINONIMOS = {
  perfil: "perfil arroba username usuario user profile conta handle ownerusername", link: "link url permalink linkdopost posturl",
  data: "data date datadepublicacao publicadoem publicado timestamp postedat createdat datetime", formato: "formato tipo type mediatype producttype format",
  legenda: "legenda caption texto text descricao", likes: "likes curtidas like likescount", comentarios: "comentarios comments comentario commentscount comment",
  views: "views visualizacoes visualizacao plays reproducoes videoviewcount videoplaycount", salvamentos: "salvamentos saves salvos saved salvamento",
  compartilhamentos: "compartilhamentos shares compartilhados envios compartilhamento", seguidores: "seguidores followers followerscount seguidor",
};
const CABECALHOS = Object.fromEntries(Object.entries(SINONIMOS).flatMap(([campo, nomes]) => nomes.split(" ").map((n) => [n, campo])));
const VAZIOS = new Set(["", "-", "--", "n/d", "nd", "na", "n/a", "oculto", "ocultos", "hidden", "null", "none", "nan", "?"]);

// Leitor de CSV com aspas (campos com quebra de linha e "" dentro de aspas).
export function lerCsv(texto, delim) {
  const linhas = [];
  let linha = [], campo = "", aspas = false;
  for (let i = 0; i < texto.length; i++) {
    const c = texto[i];
    if (aspas) {
      if (c === '"' && texto[i + 1] === '"') { campo += '"'; i++; } else if (c === '"') aspas = false; else campo += c;
    } else if (c === '"') aspas = true;
    else if (c === delim) { linha.push(campo); campo = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && texto[i + 1] === "\n") i++; linha.push(campo); linhas.push(linha); linha = []; campo = ""; }
    else campo += c;
  }
  if (campo !== "" || linha.length) { linha.push(campo); linhas.push(linha); }
  return linhas.filter((l) => l.some((c) => c.trim()));
}

function tabela(texto) {
  const avisos = [], cru = texto.trim().replace(/^﻿/, "");
  if (cru[0] === "[" || cru[0] === "{") {
    const dados = JSON.parse(cru);
    const itens = Array.isArray(dados) ? dados : dados.posts || [];
    return [itens.filter((i) => i && typeof i === "object").map((i) => ({ ...i })), avisos];
  }
  const cab = cru.split(/\r?\n/)[0] || "";
  const conta = (d) => cab.split(d).length - 1;
  const delim = [";", "\t", ",", "|"].reduce((melhor, d) => (conta(d) > conta(melhor) ? d : melhor));
  const todas = lerCsv(cru, delim);
  if (!todas.length) return [[], avisos];
  const [cabecalho, ...resto] = todas, saida = [];
  resto.forEach((linhaOriginal, k) => {
    let linha = linhaOriginal;
    while (linha.length > cabecalho.length && !linha.at(-1).trim()) linha = linha.slice(0, -1);
    if (linha.length !== cabecalho.length) { avisos.push(`linha ${k + 2} ignorada: ${linha.length} colunas em vez de ${cabecalho.length}`); return; }
    saida.push(Object.fromEntries(cabecalho.map((nome, i) => [nome, linha[i]])));
  });
  return [saida, avisos];
}

export function ler(texto, perfilPadrao = "") {
  texto = String(texto ?? "").slice(0, MAX_TEXTO);
  let linhas, avisos;
  try { [linhas, avisos] = tabela(texto); } catch (e) { throw new Error(`não consegui ler o texto como CSV nem JSON (${e.message})`); }
  if (!linhas.length) throw new Error("não achei nenhuma linha de posts (a primeira linha precisa ser o cabeçalho das colunas)");
  const mapa = Object.fromEntries(Object.keys(linhas[0]).map((nome) => [nome, CABECALHOS[fold(nome).replace(/[^a-z0-9]/g, "")]]));
  if (!Object.values(mapa).some(Boolean)) throw new Error("não reconheci as colunas (use nomes como perfil, link, data, formato, legenda, likes, comentarios, views)");
  const padrao = normalizarPerfil(perfilPadrao), posts = [], vistos = new Set(), seguidores = {};
  let ignoradas = 0;
  linhas.slice(0, MAX_LINHAS).forEach((bruto, k) => {
    const n = k + 2, linha = {};
    for (const [nome, campo] of Object.entries(mapa)) if (campo) linha[campo] = bruto[nome];
    const perfil = normalizarPerfil(linha.perfil) || padrao, link = limparLink(linha.link), dataTxt = String(linha.data ?? "").trim(), data = epoch(dataTxt);
    if (!perfil || !(link || dataTxt)) { ignoradas++; avisos.push(`linha ${n} ignorada: sem ${!perfil ? "perfil" : "link nem data"}`); return; }
    if (dataTxt && data == null) avisos.push(`linha ${n}: data "${dataTxt.slice(0, 20)}" ilegível (post sem data)`);
    const post = { perfil, link, data: data != null ? iso(data) : "", formato: normalizarFormato(linha.formato), legenda: limparLegenda(linha.legenda) };
    for (const campo of CAMPOS_NUMERICOS) {
      const brutoNum = linha[campo];
      post[campo] = numero(brutoNum);
      if (post[campo] == null && !VAZIOS.has(fold(brutoNum ?? "").trim())) avisos.push(`linha ${n}: ${campo} "${String(brutoNum).slice(0, 15)}" ilegível (n/d)`);
    }
    const chave = chavePost(post);
    if (vistos.has(chave)) { ignoradas++; avisos.push(`linha ${n} ignorada: post repetido`); return; }
    vistos.add(chave);
    posts.push(post);
    const seg = numero(linha.seguidores);
    if (seg) seguidores[perfil] = seg;
  });
  if (linhas.length > MAX_LINHAS) avisos.push(`só as primeiras ${MAX_LINHAS} linhas foram lidas`);
  return { posts, seguidores, avisos, ignoradas };
}
