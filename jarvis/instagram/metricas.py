"""Métricas puras (sem I/O). Fórmulas iguais às de movel/js/instagram-metricas.js; os casos em tests/dados/instagram_casos.json."""

from __future__ import annotations

import math

from jarvis.instagram import LIMITE_COMENTARIO_PCT, LIMITE_OUTLIER, MIN_POSTS_GRUPO, PESOS_PADRAO
from jarvis.instagram.ganchos import tem_cta_comentario


def mediana(valores: list[float]) -> float | None:
    s = sorted(valores)
    if not s:
        return None
    meio = len(s) // 2
    return s[meio] if len(s) % 2 else (s[meio - 1] + s[meio]) / 2


def quantil(ordenados: list[float], p: float) -> float:
    """Percentil com interpolação linear (os cortes dos tercis usam p = 1/3 e 2/3)."""
    pos = (len(ordenados) - 1) * p
    baixo = math.floor(pos)
    alto = min(baixo + 1, len(ordenados) - 1)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (pos - baixo)


def engajamento_detalhe(post: dict, pesos: dict | None = None) -> tuple[float | None, str]:
    """salvamentos*3 + compartilhamentos*3 + comentários*2 + likes*1 (pesos da entrevista).

    Likes ocultos = n/d (nunca zero). Campo ausente tem o peso ignorado, e o motivo avisa."""
    pesos = {**PESOS_PADRAO, **(pesos or {})}
    if post.get("likes") is None:
        return None, "likes ocultos"
    total, notas = pesos["likes"] * post["likes"], []
    for campo in ("comentarios", "salvamentos", "compartilhamentos"):
        if post.get(campo) is None:
            notas.append(f"sem {campo}: peso ignorado")
        else:
            total += pesos[campo] * post[campo]
    return total, "; ".join(notas)


def engajamento(post: dict, pesos: dict | None = None) -> float | None:
    return engajamento_detalhe(post, pesos)[0]


def medianas(entradas: list[tuple[str, str, float]]) -> dict[str, dict]:
    """entradas = (perfil, formato, engajamento) dos posts maduros. Chave "perfil|formato"."""
    grupos: dict[str, list[float]] = {}
    for perfil, formato, eng in entradas:
        grupos.setdefault(f"{perfil}|{formato}", []).append(eng)
    return {k: {"perfil": k.split("|")[0], "formato": k.split("|")[1], "n": len(v), "mediana": mediana(v)} for k, v in grupos.items()}


def outlier_score(eng: float | None, grupo: dict | None) -> tuple[float | None, str]:
    """engajamento / mediana(perfil, formato). Com menos de 3 posts do formato, ou mediana zero: sem nota e o motivo."""
    if eng is None:
        return None, "engajamento n/d"
    n = grupo["n"] if grupo else 0
    if n < MIN_POSTS_GRUPO:
        return None, f"amostra pequena ({n} de {MIN_POSTS_GRUPO} posts do formato)"
    if not grupo["mediana"]:
        return None, "mediana do formato é zero"
    return eng / grupo["mediana"], ""


def eh_outlier(score: float | None) -> bool:
    return score is not None and score >= LIMITE_OUTLIER


def alcance_relativo(views: int | None, seguidores: int | None) -> tuple[float | None, str]:
    """views / seguidores. Sem views ou sem seguidores: n/d com motivo."""
    if views is None:
        return None, "views não informadas"
    if not seguidores:
        return None, "seguidores do perfil não informados"
    return views / seguidores, ""


def cortes_tercis(razoes: list[float]) -> tuple[float, float] | None:
    """Limites entre baixo/médio/alto por tercis dos próprios dados (precisa de 3 ou mais posts com views)."""
    if len(razoes) < 3:
        return None
    s = sorted(razoes)
    return quantil(s, 1 / 3), quantil(s, 2 / 3)


def faixa_alcance(razao: float | None, cortes: tuple[float, float] | None) -> str | None:
    if razao is None or cortes is None:
        return None
    return "baixo" if razao < cortes[0] else "médio" if razao <= cortes[1] else "alto"


def comment_rate(post: dict) -> tuple[float | None, str]:
    """comentários / (likes + comentários). Likes ocultos ou total zero: n/d."""
    likes, coment = post.get("likes"), post.get("comentarios")
    if likes is None or coment is None:
        return None, "likes ocultos" if likes is None else "comentários não informados"
    return (coment / (likes + coment), "") if likes + coment else (None, "sem interações")


def badge(post: dict) -> str | None:
    """Taxa >= 0,30: GATE se a legenda pede comentário, senão POLÊMICA. Comparado em inteiros (0,30 já conta)."""
    likes, coment = post.get("likes"), post.get("comentarios")
    if likes is None or coment is None or likes + coment == 0 or coment * 100 < LIMITE_COMENTARIO_PCT * (likes + coment):
        return None
    return "GATE" if tem_cta_comentario(post.get("legenda")) else "POLÊMICA"
