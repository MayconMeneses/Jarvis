"""Análise completa (pura, sem I/O): junta higiene, métricas, ganchos e temas num resultado JSON.

O ranking e as recomendações priorizam SEMPRE o maior alcance (views / seguidores). As faixas baixo/médio/alto
são tercis dos próprios dados. Sem views, o ranking cai para o outlier de engajamento e o resultado avisa.
"""

from __future__ import annotations

from jarvis.instagram import MIN_POSTS_PERFIL, PESOS_PADRAO
from jarvis.instagram.ganchos import classificar_gancho
from jarvis.instagram.higiene import confianca, maturidade
from jarvis.instagram.importar import chave_post
from jarvis.instagram.metricas import (alcance_relativo, badge, comment_rate, cortes_tercis, eh_outlier, engajamento_detalhe,
                                       faixa_alcance, mediana, medianas, outlier_score)
from jarvis.instagram.temas import temas_por_frequencia


def _resumo(itens: list[dict], campo: str) -> list[dict]:
    """Agrupa posts maduros por formato ou gancho; ordena pelo maior alcance mediano (sem alcance, por outliers)."""
    grupos: dict[str, list[dict]] = {}
    for i in itens:
        grupos.setdefault(i[campo], []).append(i)
    linhas = []
    for nome, membros in grupos.items():
        alc = [m["razao_alcance"] for m in membros if m["razao_alcance"] is not None]
        linhas.append({campo: nome, "n": len(membros), "alcance_mediano": mediana(alc), "outliers": sum(m["outlier"] for m in membros)})
    return sorted(linhas, key=lambda g: (g["alcance_mediano"] is None, -(g["alcance_mediano"] or 0), -g["outliers"], g[campo]))


def analisar(posts: list[dict], seguidores: dict | None = None, pesos: dict | None = None, agora: int = 0, proprio: str = "") -> dict:
    pesos, seguidores, avisos = {**PESOS_PADRAO, **(pesos or {})}, seguidores or {}, []
    itens = []
    for p in posts:
        mat = maturidade(p, agora)
        eng, motivo_eng = engajamento_detalhe(p, pesos)
        taxa, motivo_taxa = comment_rate(p)
        razao, motivo_alc = alcance_relativo(p.get("views"), seguidores.get(p["perfil"]))
        itens.append({"id": chave_post(p), "perfil": p["perfil"], "formato": p["formato"], "data": p.get("data", ""), "link": p.get("link", ""),
                      "legenda": p.get("legenda", ""), "gancho": classificar_gancho(p.get("legenda")), "imaturo": mat == "imaturo",
                      "sem_data": mat == "sem_data", "proprio": p["perfil"] == proprio, "engajamento": eng, "motivo_eng": motivo_eng,
                      "razao_alcance": razao, "motivo_alcance": motivo_alc, "taxa_comentario": taxa, "motivo_taxa": motivo_taxa,
                      "badge": badge(p), "score": None, "motivo_score": "", "outlier": False, "faixa": None})
    maduros = [i for i in itens if not i["imaturo"]]
    grupos = medianas([(i["perfil"], i["formato"], i["engajamento"]) for i in maduros if i["engajamento"] is not None])
    cortes = cortes_tercis([i["razao_alcance"] for i in maduros if i["razao_alcance"] is not None])
    for i in itens:
        if i["imaturo"]:
            i["motivo_score"] = i["motivo_alcance"] = "post com menos de 48 h (fora das medianas)"
            i["razao_alcance"] = None
            continue
        i["score"], i["motivo_score"] = outlier_score(i["engajamento"], grupos.get(f"{i['perfil']}|{i['formato']}"))
        i["outlier"] = eh_outlier(i["score"])
        i["faixa"] = faixa_alcance(i["razao_alcance"], cortes)
    perfis = {}
    for arroba in sorted({i["perfil"] for i in itens}):
        mine = [i for i in itens if i["perfil"] == arroba]
        n_mad = sum(not i["imaturo"] for i in mine)
        perfis[arroba] = {"seguidores": seguidores.get(arroba), "n_total": len(mine), "n_maduros": n_mad, "n_imaturos": len(mine) - n_mad,
                          "confianca": confianca(n_mad), "proprio": arroba == proprio}
        if n_mad < MIN_POSTS_PERFIL:
            avisos.append(f"{arroba}: só {n_mad} posts maduros (mínimo {MIN_POSTS_PERFIL}): baixa confiança")
    if any(i["engajamento"] is None for i in itens):
        avisos.append("Há posts com likes ocultos: engajamento n/d (nunca tratado como zero).")
    if cortes is None:
        avisos.append("Alcance relativo sem faixas: precisa de pelo menos 3 posts maduros com views e seguidores do perfil.")
    if any(i["sem_data"] for i in itens):
        avisos.append("Há posts sem data legível: contados como maduros.")
    ranking = sorted((i for i in maduros), key=lambda i: (i["razao_alcance"] is None, -(i["razao_alcance"] or 0), -(i["score"] or 0), i["id"]))
    return {"agora": agora, "pesos": pesos, "perfis": perfis, "grupos": sorted(grupos.values(), key=lambda g: (g["perfil"], g["formato"])),
            "posts": itens, "ranking": [i["id"] for i in ranking], "formatos": _resumo(maduros, "formato"), "ganchos": _resumo(maduros, "gancho"),
            "temas": temas_por_frequencia(maduros), "ranking_por": "alcance" if any(i["razao_alcance"] is not None for i in maduros) else "outlier",
            "avisos": avisos}
