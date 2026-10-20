"""Resumo do uso para a janela, o chat e o MCP: totais, por dia/modelo/provedor/projeto/sessão, cota e orçamento."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from jarvis.uso import configuracao, cota, orcamento
from jarvis.uso.registro import Registro

PERIODOS = {"hoje": "hoje", "7d": "últimos 7 dias", "30d": "últimos 30 dias", "mes": "este mês", "tudo": "todo o período"}


def inicio_periodo(periodo: str, agora: float) -> float:
    dt = datetime.fromtimestamp(agora)
    zero = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if periodo == "hoje":
        return zero.timestamp()
    if periodo == "7d":
        return (zero - timedelta(days=6)).timestamp()
    if periodo == "30d":
        return (zero - timedelta(days=29)).timestamp()
    if periodo == "mes":
        return orcamento.inicio_mes(dt).timestamp()
    return 0.0


def _soma(linhas: list[dict]) -> dict:
    return {"msgs": len(linhas), "tin": sum(l["tin"] for l in linhas), "tout": sum(l["tout"] for l in linhas),
            "cw": sum(l["cw"] for l in linhas), "cr": sum(l["cr"] for l in linhas),
            "custo": round(sum(l["custo"] for l in linhas), 4), "estimado": any(l["estimado"] for l in linhas)}


def _agrupar(linhas: list[dict], chave, limite: int | None = None) -> list[dict]:
    grupos: dict = defaultdict(list)
    for l in linhas:
        grupos[chave(l)].append(l)
    itens = [{"nome": k[0] if isinstance(k, tuple) else k, "provedor": l0[0]["provedor"], "preco_ok": all(x["preco_ok"] for x in l0), **_soma(l0)}
             for k, l0 in grupos.items()]
    itens.sort(key=lambda i: (-i["custo"], -(i["tin"] + i["tout"] + i["cw"] + i["cr"])))
    return itens[:limite] if limite else itens


def _por_dia(linhas: list[dict]) -> list[dict]:
    if not linhas:
        return []
    soma: dict = defaultdict(lambda: {"custo": 0.0, "tokens": 0, "msgs": 0})
    for l in linhas:
        d = soma[l["dia"]]
        d["custo"] += l["custo"]
        d["tokens"] += l["tin"] + l["tout"] + l["cw"] + l["cr"]
        d["msgs"] += 1
    dia, fim = datetime.strptime(linhas[0]["dia"], "%Y-%m-%d"), datetime.strptime(linhas[-1]["dia"], "%Y-%m-%d")
    saida = []
    while dia <= fim and len(saida) < 400:
        chave = dia.strftime("%Y-%m-%d")
        saida.append({"dia": chave, **{k: (round(v, 4) if k == "custo" else v) for k, v in soma.get(chave, {"custo": 0.0, "tokens": 0, "msgs": 0}).items()}})
        dia += timedelta(days=1)
    return saida


def resumo(reg: Registro, periodo: str = "mes", agora: float | None = None, filtros: dict | None = None) -> dict:
    agora = agora or datetime.now().timestamp()
    periodo = periodo if periodo in PERIODOS else "mes"
    filtros = {k: v for k, v in (filtros or {}).items() if k in ("provedor", "modelo", "projeto", "sessao", "sub") and v not in (None, "")}
    linhas = reg.linhas(desde=inicio_periodo(periodo, agora), **filtros)
    ia = [l for l in linhas if l["provedor"] != "local"]
    locais = len(linhas) - len(ia)
    subs = [l for l in ia if l["sub"]]
    todas = reg.linhas(desde=0.0)
    cfg = configuracao.carregar(reg)
    return {
        "periodo": periodo, "rotulo": PERIODOS[periodo], "filtros": filtros, "totais": _soma(ia),
        "por_dia": _por_dia(ia), "por_modelo": _agrupar(ia, lambda l: (l["modelo"] or l["provedor"], l["provedor"])),
        "por_provedor": _agrupar(ia, lambda l: l["provedor"]), "por_projeto": _agrupar(ia, lambda l: l["projeto"] or "(sem projeto)", 10),
        "por_sessao": [{**i, "nome": i["nome"][:8]} for i in _agrupar([l for l in ia if l["sessao"]], lambda l: l["sessao"], 10)],
        "subagentes": {**_soma(subs), "pct": round(100 * len(subs) / len(ia), 1) if ia else 0.0},
        "locais": {"local": locais, "ia": len(ia), "pct_local": round(100 * locais / len(linhas), 1) if linhas else 0.0},
        "sem_preco": sorted({l["modelo"] for l in ia if not l["preco_ok"] and l["modelo"]}),
        "opcoes": {"modelos": sorted({l["modelo"] for l in todas if l["modelo"]}), "projetos": sorted({l["projeto"] for l in todas if l["projeto"]}),
                   "provedores": sorted({l["provedor"] for l in todas})},
        "cota": cota.estado(reg, agora, cfg), "orcamento": orcamento.mes(reg, agora, cfg), "config": cfg, "vazio": not todas,
    }
