"""Relatório em 8 seções, montado por modelo só com números já calculados em analise.analisar. Faltou dado: "n/d" e o motivo."""

from __future__ import annotations

import re


def num(v, casas: int = 2) -> str:
    return "n/d" if v is None else f"{v:.{casas}f}".replace(".", ",")


def pct(v) -> str:
    return "n/d" if v is None else f"{v * 100:.1f}%".replace(".", ",")


def legenda_inerte(texto: str, limite: int = 70) -> str:
    """Legenda é dado de terceiros: uma linha, sem marcação, entre aspas. Nunca é repassada como instrução."""
    return '"' + re.sub(r"[`*_#>\[\]]", "", " ".join(str(texto).split()))[:limite] + '"'


def _por_id(r: dict) -> dict:
    return {p["id"]: p for p in r["posts"]}


def recomendacoes(r: dict) -> list[str]:
    """Sempre priorizam o MAIOR alcance; sem views, o maior outlier de engajamento (e o texto diz isso)."""
    por = "alcance relativo (views por seguidor)" if r["ranking_por"] == "alcance" else "outliers de engajamento (não há views)"
    linhas = [f"Prioridade: {por}, do maior para o menor."]
    for nome, chave, rotulo in (("formatos", "formato", "Formato"), ("ganchos", "gancho", "Gancho")):
        topo = [g for g in r[nome] if g["n"] >= 2][:1] or r[nome][:1]
        if topo:
            g = topo[0]
            linhas.append(f"{rotulo} para repetir: **{g[chave]}** (alcance mediano {pct(g['alcance_mediano'])}, {g['n']} posts, {g['outliers']} outliers).")
    lacunas = [t for t in r["temas"] if not t["proprio"]][:3]
    if lacunas:
        linhas.append("Temas que os concorrentes usam e o seu perfil não: " + ", ".join(f"{t['rotulo']} ({t['posts']} posts)" for t in lacunas) + ".")
    return linhas


def montar(r: dict, nicho: str = "", rotulo_rodada: str = "") -> str:
    posts, por_id = r["posts"], _por_id(r)
    maduros = [p for p in posts if not p["imaturo"]]
    out = [f"# Análise de Instagram{' — ' + nicho if nicho else ''}{' (rodada ' + rotulo_rodada + ')' if rotulo_rodada else ''}", ""]
    out += ["## 1. Resumo e confiança", f"{len(posts)} posts lidos, {len(maduros)} maduros (48 h ou mais) e {len(posts) - len(maduros)} ainda em maturação (fora das medianas)."]
    for arroba, p in r["perfis"].items():
        out.append(f"- {arroba}{' (seu perfil)' if p['proprio'] else ''}: {p['n_maduros']} posts maduros, seguidores {p['seguidores'] if p['seguidores'] is not None else 'n/d'}, "
                   f"confiança {p['confianca']}")
    out += [f"- Aviso: {a}" for a in r["avisos"]]
    out += ["Amostras pequenas: isto mostra posts que superaram a mediana do formato, não prova que o gancho ou o tema causou o resultado.", ""]
    out += ["## 2. Medianas de engajamento (perfil e formato)"]
    out += [f"- {g['perfil']} / {g['formato']}: mediana {num(g['mediana'])} em {g['n']} posts" for g in r["grupos"]] or ["- n/d: nenhum post maduro com likes visíveis"]
    out += ["", "## 3. Outliers (engajamento 2,0 vezes a mediana ou mais)"]
    outs = sorted((p for p in maduros if p["outlier"]), key=lambda p: -p["score"])
    out += [f"- {p['perfil']} {p['formato']}: {num(p['score'])}x {legenda_inerte(p['legenda'])} {p['link']}".rstrip() for p in outs] or ["- nenhum outlier nesta rodada"]
    sem = [p for p in maduros if p["score"] is None and p["engajamento"] is not None]
    if sem:
        out.append(f"- {len(sem)} posts sem nota de outlier: {sem[0]['motivo_score']}")
    out += ["", "## 4. Ranking por alcance (maior primeiro)"]
    for n, id_ in enumerate(r["ranking"][:10], start=1):
        p = por_id[id_]
        out.append(f"{n}. {p['perfil']} {p['formato']}: alcance {pct(p['razao_alcance'])}"
                   f"{' (' + p['faixa'] + ')' if p['faixa'] else ''}{'' if p['razao_alcance'] is not None else ' — ' + p['motivo_alcance']}")
    imat = [p for p in posts if p["imaturo"]]
    out += [f"- {len(imat)} posts em maturação, fora do ranking."] if imat else []
    out += ["", "## 5. Taxa de comentário e selos"]
    marcados = [p for p in maduros if p["badge"]]
    out += [f"- {p['perfil']} {p['formato']}: {pct(p['taxa_comentario'])} — {p['badge']} {legenda_inerte(p['legenda'], 50)}" for p in marcados] or ["- nenhum post com taxa de comentário de 0,30 ou mais"]
    ocultos = sum(p["taxa_comentario"] is None for p in maduros)
    out += [f"- {ocultos} posts com taxa n/d ({maduros[[p['taxa_comentario'] for p in maduros].index(None)]['motivo_taxa']})"] if ocultos else []
    out += ["", "## 6. Ganchos"]
    out += [f"- {g['gancho']}: {g['n']} posts, alcance mediano {pct(g['alcance_mediano'])}, {g['outliers']} outliers" for g in r["ganchos"]] or ["- n/d"]
    out += ["", "## 7. Temas"]
    out += [f"- {t.get('nome') or t['rotulo']}: {t['posts']} posts, alcance mediano {pct(t['alcance_mediano'])}, em {', '.join(t['perfis'])}" for t in r["temas"]] or ["- sem temas repetidos em 2 posts ou mais"]
    out += ["", "## 8. Recomendações"] + [f"- {linha}" for linha in recomendacoes(r)]
    return "\n".join(out)
