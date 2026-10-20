// Analista de Instagram no celular, parte 2: fórmulas e a análise completa (pura). Igual a jarvis/instagram/{metricas,analise}.py.
import { CAMPOS_NUMERICOS, LIMITE_COMENTARIO_PCT, LIMITE_OUTLIER, MIN_POSTS_GRUPO, MIN_POSTS_PERFIL, PESOS_PADRAO, chavePost, classificarGancho,
  confianca, maturidade, temCtaComentario } from "./instagram-base.js";
import { mediana, temasPorFrequencia } from "./instagram-temas.js";

export { mediana };
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

export function quantil(ordenados, p) {
  const pos = (ordenados.length - 1) * p, baixo = Math.floor(pos), alto = Math.min(baixo + 1, ordenados.length - 1);
  return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (pos - baixo);
}

// Likes ocultos = n/d (nunca zero); campo ausente tem o peso ignorado e o motivo avisa.
export function engajamentoDetalhe(post, pesos = null) {
  pesos = { ...PESOS_PADRAO, ...(pesos || {}) };
  if (post.likes == null) return [null, "likes ocultos"];
  let total = pesos.likes * post.likes;
  const notas = [];
  for (const campo of ["comentarios", "salvamentos", "compartilhamentos"]) {
    if (post[campo] == null) notas.push(`sem ${campo}: peso ignorado`);
    else total += pesos[campo] * post[campo];
  }
  return [total, notas.join("; ")];
}
export const engajamento = (post, pesos) => engajamentoDetalhe(post, pesos)[0];

export function medianas(entradas) {  // entradas = [perfil, formato, engajamento] dos posts maduros
  const grupos = new Map();
  for (const [perfil, formato, eng] of entradas) { const k = `${perfil}|${formato}`; if (!grupos.has(k)) grupos.set(k, []); grupos.get(k).push(eng); }
  return Object.fromEntries([...grupos].map(([k, v]) => [k, { perfil: k.split("|")[0], formato: k.split("|")[1], n: v.length, mediana: mediana(v) }]));
}

export function outlierScore(eng, grupo) {
  if (eng == null) return [null, "engajamento n/d"];
  const n = grupo ? grupo.n : 0;
  if (n < MIN_POSTS_GRUPO) return [null, `amostra pequena (${n} de ${MIN_POSTS_GRUPO} posts do formato)`];
  if (!grupo.mediana) return [null, "mediana do formato é zero"];
  return [eng / grupo.mediana, ""];
}
export const ehOutlier = (score) => score != null && score >= LIMITE_OUTLIER;

export function alcanceRelativo(views, seguidores) {
  if (views == null) return [null, "views não informadas"];
  if (!seguidores) return [null, "seguidores do perfil não informados"];
  return [views / seguidores, ""];
}

export function cortesTercis(razoes) {
  if (razoes.length < 3) return null;
  const s = [...razoes].sort((a, b) => a - b);
  return [quantil(s, 1 / 3), quantil(s, 2 / 3)];
}
export const faixaAlcance = (razao, cortes) => (razao == null || !cortes ? null : razao < cortes[0] ? "baixo" : razao <= cortes[1] ? "médio" : "alto");

export function commentRate(post) {
  const { likes, comentarios } = post;
  if (likes == null || comentarios == null) return [null, likes == null ? "likes ocultos" : "comentários não informados"];
  return likes + comentarios ? [comentarios / (likes + comentarios), ""] : [null, "sem interações"];
}

// Taxa >= 0,30: GATE se a legenda pede comentário, senão POLÊMICA. Comparação em inteiros (0,30 já conta).
export function badge(post) {
  const { likes, comentarios } = post;
  if (likes == null || comentarios == null || likes + comentarios === 0 || comentarios * 100 < LIMITE_COMENTARIO_PCT * (likes + comentarios)) return null;
  return temCtaComentario(post.legenda) ? "GATE" : "POLÊMICA";
}

function resumo(itens, campo) {
  const grupos = new Map();
  for (const i of itens) { if (!grupos.has(i[campo])) grupos.set(i[campo], []); grupos.get(i[campo]).push(i); }
  const linhas = [...grupos].map(([nome, m]) => ({ [campo]: nome, n: m.length, outliers: m.filter((x) => x.outlier).length,
    alcance_mediano: mediana(m.filter((x) => x.razao_alcance != null).map((x) => x.razao_alcance)) }));
  return linhas.sort((a, b) => (a.alcance_mediano == null) - (b.alcance_mediano == null) || (b.alcance_mediano ?? 0) - (a.alcance_mediano ?? 0) || b.outliers - a.outliers || cmp(a[campo], b[campo]));
}

export function analisar(posts, seguidores = {}, pesos = null, agora = 0, proprio = "") {
  pesos = { ...PESOS_PADRAO, ...(pesos || {}) };
  const avisos = [];
  const itens = posts.map((p) => {
    const mat = maturidade(p, agora), [eng, motivoEng] = engajamentoDetalhe(p, pesos), [taxa, motivoTaxa] = commentRate(p);
    const [razao, motivoAlc] = alcanceRelativo(p.views, seguidores[p.perfil]);
    return { id: chavePost(p), perfil: p.perfil, formato: p.formato, data: p.data || "", link: p.link || "", legenda: p.legenda || "",
      gancho: classificarGancho(p.legenda), imaturo: mat === "imaturo", sem_data: mat === "sem_data", proprio: p.perfil === proprio, engajamento: eng,
      motivo_eng: motivoEng, razao_alcance: razao, motivo_alcance: motivoAlc, taxa_comentario: taxa, motivo_taxa: motivoTaxa, badge: badge(p),
      score: null, motivo_score: "", outlier: false, faixa: null };
  });
  const maduros = itens.filter((i) => !i.imaturo);
  const grupos = medianas(maduros.filter((i) => i.engajamento != null).map((i) => [i.perfil, i.formato, i.engajamento]));
  const cortes = cortesTercis(maduros.filter((i) => i.razao_alcance != null).map((i) => i.razao_alcance));
  for (const i of itens) {
    if (i.imaturo) { i.motivo_score = i.motivo_alcance = "post com menos de 48 h (fora das medianas)"; i.razao_alcance = null; continue; }
    [i.score, i.motivo_score] = outlierScore(i.engajamento, grupos[`${i.perfil}|${i.formato}`]);
    i.outlier = ehOutlier(i.score);
    i.faixa = faixaAlcance(i.razao_alcance, cortes);
  }
  const perfis = {};
  for (const arroba of [...new Set(itens.map((i) => i.perfil))].sort(cmp)) {
    const meus = itens.filter((i) => i.perfil === arroba), nMad = meus.filter((i) => !i.imaturo).length;
    perfis[arroba] = { seguidores: seguidores[arroba] ?? null, n_total: meus.length, n_maduros: nMad, n_imaturos: meus.length - nMad, confianca: confianca(nMad), proprio: arroba === proprio };
    if (nMad < MIN_POSTS_PERFIL) avisos.push(`${arroba}: só ${nMad} posts maduros (mínimo ${MIN_POSTS_PERFIL}): baixa confiança`);
  }
  if (itens.some((i) => i.engajamento == null)) avisos.push("Há posts com likes ocultos: engajamento n/d (nunca tratado como zero).");
  if (!cortes) avisos.push("Alcance relativo sem faixas: precisa de pelo menos 3 posts maduros com views e seguidores do perfil.");
  if (itens.some((i) => i.sem_data)) avisos.push("Há posts sem data legível: contados como maduros.");
  const ranking = [...maduros].sort((a, b) => (a.razao_alcance == null) - (b.razao_alcance == null) || (b.razao_alcance ?? 0) - (a.razao_alcance ?? 0) || (b.score ?? 0) - (a.score ?? 0) || cmp(a.id, b.id));
  return { agora, pesos, perfis, grupos: Object.values(grupos).sort((a, b) => cmp(a.perfil, b.perfil) || cmp(a.formato, b.formato)), posts: itens,
    ranking: ranking.map((i) => i.id), formatos: resumo(maduros, "formato"), ganchos: resumo(maduros, "gancho"), temas: temasPorFrequencia(maduros),
    ranking_por: maduros.some((i) => i.razao_alcance != null) ? "alcance" : "outlier", avisos };
}

export { CAMPOS_NUMERICOS };
