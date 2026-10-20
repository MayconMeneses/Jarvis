"""Orçamento mensal (USD) e projeção do gasto até o fim do mês.

O gasto do Claude por assinatura é "valor equivalente em API" (não é o que a assinatura cobra):
ajuda a comparar modelos e a ver o peso de cada sessão. Modelo sem preço entra em `sem_preco`.
"""

from __future__ import annotations

import calendar
from datetime import datetime

from jarvis.uso import configuracao
from jarvis.uso.registro import Registro


def inicio_mes(agora: datetime) -> datetime:
    return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def mes(reg: Registro, agora: float, cfg: dict | None = None) -> dict:
    cfg = cfg or configuracao.carregar(reg)
    dt = datetime.fromtimestamp(agora)
    linhas = reg.linhas(desde=inicio_mes(dt).timestamp())
    gasto = sum(l["custo"] for l in linhas)
    dias_mes = calendar.monthrange(dt.year, dt.month)[1]
    decorridos = max((agora - inicio_mes(dt).timestamp()) / 86400, 1.0)  # no 1º dia, não multiplica por 30
    projecao = gasto / decorridos * dias_mes
    teto = cfg["orcamento_mensal"]
    pct = round(100 * gasto / teto, 1) if teto else None
    return {
        "gasto": round(gasto, 2), "projecao": round(projecao, 2), "orcamento": teto, "pct": pct,
        "alerta": bool(pct is not None and pct >= cfg["alerta_pct"]),
        "projecao_estoura": bool(teto and projecao > teto), "dias_mes": dias_mes, "dias_decorridos": round(decorridos, 1),
        "sem_preco": sorted({l["modelo"] for l in linhas if not l["preco_ok"] and l["modelo"]}),
        "estimado": any(l["estimado"] for l in linhas), "cotacao_brl": cfg["cotacao_brl"],
    }
