// Relatório de 8 seções e comparação de rodadas no celular: só números já calculados; faltou dado = "n/d" e o motivo.
export const num = (v, casas = 2) => (v == null ? "n/d" : v.toFixed(casas).replace(".", ","));
export const pct = (v) => (v == null ? "n/d" : (v * 100).toFixed(1).replace(".", ",") + "%");
// Legenda é dado de terceiros: uma linha, sem marcação, entre aspas, nunca instrução.
export const legendaInerte = (texto, limite = 70) => '"' + String(texto).replace(/[`*_#>[\]]/g, "").split(/\s+/).filter(Boolean).join(" ").slice(0, limite) + '"';

export function recomendacoes(r) {
  const por = r.ranking_por === "alcance" ? "alcance relativo (views por seguidor)" : "outliers de engajamento (não há views)";
  const linhas = [`Prioridade: ${por}, do maior para o menor.`];
  for (const [nome, chave, rotulo] of [["formatos", "formato", "Formato"], ["ganchos", "gancho", "Gancho"]]) {
    const g = r[nome].find((x) => x.n >= 2) || r[nome][0];
    if (g) linhas.push(`${rotulo} para repetir: **${g[chave]}** (alcance mediano ${pct(g.alcance_mediano)}, ${g.n} posts, ${g.outliers} outliers).`);
  }
  const lacunas = r.temas.filter((t) => !t.proprio).slice(0, 3);
  if (lacunas.length) linhas.push("Temas que os concorrentes usam e o seu perfil não: " + lacunas.map((t) => `${t.rotulo} (${t.posts} posts)`).join(", ") + ".");
  return linhas;
}

export function montar(r, nicho = "", rotulo = "") {
  const porId = Object.fromEntries(r.posts.map((p) => [p.id, p])), maduros = r.posts.filter((p) => !p.imaturo);
  const out = [`# Análise de Instagram${nicho ? " — " + nicho : ""}${rotulo ? ` (rodada ${rotulo})` : ""}`, ""];
  out.push("## 1. Resumo e confiança", `${r.posts.length} posts lidos, ${maduros.length} maduros (48 h ou mais) e ${r.posts.length - maduros.length} ainda em maturação (fora das medianas).`);
  for (const [arroba, p] of Object.entries(r.perfis)) out.push(`- ${arroba}${p.proprio ? " (seu perfil)" : ""}: ${p.n_maduros} posts maduros, seguidores ${p.seguidores ?? "n/d"}, confiança ${p.confianca}`);
  out.push(...r.avisos.map((a) => `- Aviso: ${a}`), "Amostras pequenas: isto mostra posts que superaram a mediana do formato, não prova que o gancho ou o tema causou o resultado.", "");
  out.push("## 2. Medianas de engajamento (perfil e formato)", ...(r.grupos.map((g) => `- ${g.perfil} / ${g.formato}: mediana ${num(g.mediana)} em ${g.n} posts`)));
  if (!r.grupos.length) out.push("- n/d: nenhum post maduro com likes visíveis");
  out.push("", "## 3. Outliers (engajamento 2,0 vezes a mediana ou mais)");
  const outs = maduros.filter((p) => p.outlier).sort((a, b) => b.score - a.score);
  out.push(...(outs.length ? outs.map((p) => `- ${p.perfil} ${p.formato}: ${num(p.score)}x ${legendaInerte(p.legenda)} ${p.link}`.trimEnd()) : ["- nenhum outlier nesta rodada"]));
  const sem = maduros.filter((p) => p.score == null && p.engajamento != null);
  if (sem.length) out.push(`- ${sem.length} posts sem nota de outlier: ${sem[0].motivo_score}`);
  out.push("", "## 4. Ranking por alcance (maior primeiro)");
  r.ranking.slice(0, 10).forEach((id, n) => {
    const p = porId[id];
    out.push(`${n + 1}. ${p.perfil} ${p.formato}: alcance ${pct(p.razao_alcance)}${p.faixa ? ` (${p.faixa})` : ""}${p.razao_alcance != null ? "" : " — " + p.motivo_alcance}`);
  });
  const imat = r.posts.filter((p) => p.imaturo).length;
  if (imat) out.push(`- ${imat} posts em maturação, fora do ranking.`);
  out.push("", "## 5. Taxa de comentário e selos");
  const marcados = maduros.filter((p) => p.badge);
  out.push(...(marcados.length ? marcados.map((p) => `- ${p.perfil} ${p.formato}: ${pct(p.taxa_comentario)} — ${p.badge} ${legendaInerte(p.legenda, 50)}`) : ["- nenhum post com taxa de comentário de 0,30 ou mais"]));
  const ocultos = maduros.filter((p) => p.taxa_comentario == null);
  if (ocultos.length) out.push(`- ${ocultos.length} posts com taxa n/d (${ocultos[0].motivo_taxa})`);
  out.push("", "## 6. Ganchos", ...(r.ganchos.length ? r.ganchos.map((g) => `- ${g.gancho}: ${g.n} posts, alcance mediano ${pct(g.alcance_mediano)}, ${g.outliers} outliers`) : ["- n/d"]));
  out.push("", "## 7. Temas", ...(r.temas.length ? r.temas.map((t) => `- ${t.rotulo}: ${t.posts} posts, alcance mediano ${pct(t.alcance_mediano)}, em ${t.perfis.join(", ")}`) : ["- sem temas repetidos em 2 posts ou mais"]));
  out.push("", "## 8. Recomendações", ...recomendacoes(r).map((l) => `- ${l}`));
  return out.join("\n");
}

export function comparar(anterior, atual) {
  const ant = Object.fromEntries(anterior.grupos.map((g) => [`${g.perfil}|${g.formato}`, g]));
  const medianas = atual.grupos.map((g) => {
    const antes = ant[`${g.perfil}|${g.formato}`], antesV = antes ? antes.mediana : null;
    return { perfil: g.perfil, formato: g.formato, antes: antesV, agora: g.mediana, variacao: antesV ? (g.mediana - antesV) / antesV : null, motivo: antes ? "" : "formato novo nesta rodada" };
  });
  const outA = new Set(anterior.posts.filter((p) => p.outlier).map((p) => p.id)), outB = new Set(atual.posts.filter((p) => p.outlier).map((p) => p.id));
  const ganchosA = Object.fromEntries(anterior.ganchos.map((g) => [g.gancho, g.outliers]));
  const vencedor = (r) => r.formatos[0]?.formato ?? null;
  return { medianas, outliers_novos: [...outB].filter((x) => !outA.has(x)).sort(), outliers_sumidos: [...outA].filter((x) => !outB.has(x)).sort(),
    formato_antes: vencedor(anterior), formato_agora: vencedor(atual), formato_mudou: vencedor(anterior) !== vencedor(atual),
    ganchos_subiram: atual.ganchos.filter((g) => g.outliers > (ganchosA[g.gancho] ?? 0)).map((g) => ({ gancho: g.gancho, antes: ganchosA[g.gancho] ?? 0, agora: g.outliers })) };
}

export function textoComparacao(d, a = "anterior", b = "atual") {
  const linhas = [`**Comparação: rodada ${a} x rodada ${b}**`, "", "**Mediana de engajamento por perfil e formato**"];
  for (const m of d.medianas) {
    const v = m.variacao == null ? "n/d" : `${m.variacao >= 0 ? "+" : ""}${(m.variacao * 100).toFixed(0)}%`;
    linhas.push(`- ${m.perfil} / ${m.formato}: ${num(m.antes)} -> ${num(m.agora)} (${v}${m.motivo ? "; " + m.motivo : ""})`);
  }
  linhas.push("", `Outliers novos: ${d.outliers_novos.length}. Outliers que saíram: ${d.outliers_sumidos.length}.`);
  linhas.push(d.formato_mudou ? `Formato com maior alcance mudou: ${d.formato_antes || "n/d"} -> ${d.formato_agora || "n/d"}.` : `Formato com maior alcance continua: ${d.formato_agora || "n/d"}.`);
  if (d.ganchos_subiram.length) linhas.push("Ganchos com mais outliers: " + d.ganchos_subiram.map((g) => `${g.gancho} (${g.antes} -> ${g.agora})`).join(", ") + ".");
  return linhas.join("\n");
}
