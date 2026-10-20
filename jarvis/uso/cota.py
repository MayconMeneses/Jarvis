"""Cota da assinatura do Claude, ESTIMADA: o Claude não a expõe por API.

Soma o uso das janelas de 5 h (a 1ª mensagem abre a janela, que dura 5 h) e da semana, em tokens
ponderados (ou mensagens). O teto vem do dono ou da calibração ("cheguei em 80% agora"); sem teto,
mostra só o consumo. Tudo aqui é aproximação: serve para se organizar, não para prever o corte exato.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from jarvis.uso import configuracao
from jarvis.uso.registro import Registro

JANELA = 5 * 3600
SEMANA = 7 * 86400
MIN_PROJECAO = 600  # com menos de 10 min de janela, projetar é chute


def peso(linha: dict, cfg: dict) -> float:
    if cfg["unidade"] == "mensagens":
        return 1.0
    return linha["tin"] + linha["tout"] + linha["cw"] + linha["cr"] * cfg["peso_cr"]


def janelas_5h(linhas: list[dict], cfg: dict) -> list[dict]:
    """Janelas de 5 h de início fixo: a próxima mensagem depois do fim abre outra."""
    janelas: list[dict] = []
    for l in linhas:
        if not janelas or l["ts"] >= janelas[-1]["fim"]:
            janelas.append({"inicio": l["ts"], "fim": l["ts"] + JANELA, "usado": 0.0, "msgs": 0})
        janelas[-1]["usado"] += peso(l, cfg)
        janelas[-1]["msgs"] += 1
    return janelas


def inicio_semana(agora: datetime, cfg: dict) -> datetime:
    marco = agora.replace(hour=cfg["semana_hora"], minute=0, second=0, microsecond=0)
    marco -= timedelta(days=(marco.weekday() - cfg["semana_dow"]) % 7)
    return marco - timedelta(days=7) if marco > agora else marco


def _medida(nome: str, inicio: float, fim: float, usado: float, msgs: int, teto, agora: float, alerta: int) -> dict:
    pct = round(100 * usado / teto, 1) if teto else None
    decorrido = max(agora - inicio, 0.0)
    acaba, eta = False, None
    if teto and usado > 0 and decorrido >= MIN_PROJECAO and agora < fim:
        taxa = usado / decorrido
        acaba = usado + taxa * (fim - agora) > teto
        eta = agora + max(teto - usado, 0) / taxa if acaba else None
    return {"nome": nome, "inicio": inicio, "fim": fim, "usado": round(usado, 1), "msgs": msgs, "teto": teto, "pct": pct,
            "alerta": bool(pct is not None and pct >= alerta), "acaba_antes_do_reset": acaba, "acaba_em": eta}


def estado(reg: Registro, agora: float, cfg: dict | None = None) -> dict:
    cfg = cfg or configuracao.carregar(reg)
    ini_sem = inicio_semana(datetime.fromtimestamp(agora), cfg).timestamp()
    linhas = reg.linhas(desde=min(ini_sem, agora - 2 * JANELA), provedor="claude")
    sem = [l for l in linhas if l["ts"] >= ini_sem]
    atual = next((j for j in reversed(janelas_5h(linhas, cfg)) if j["fim"] > agora), None)
    if atual:
        j5 = _medida("5h", atual["inicio"], atual["fim"], atual["usado"], atual["msgs"], cfg["teto_5h"], agora, cfg["alerta_pct"]) | {"ativa": True}
    else:  # nenhuma janela aberta: a próxima mensagem abre uma nova
        j5 = _medida("5h", agora, agora + JANELA, 0.0, 0, cfg["teto_5h"], agora, cfg["alerta_pct"]) | {"ativa": False}
    semana = _medida("semana", ini_sem, ini_sem + SEMANA, sum(peso(l, cfg) for l in sem), len(sem), cfg["teto_semana"], agora, cfg["alerta_pct"])
    return {"unidade": cfg["unidade"], "plano": cfg["plano"], "janela_5h": j5, "semana": semana,
            "estimativa": True, "aviso": "Estimativa: o Claude não informa a cota por API. Calibre o teto quando ele avisar."}


def calibrar(reg: Registro, agora: float, janela: str, pct: float) -> dict:
    """Estou em `pct`% da janela agora (100 = bati o limite): o teto passa a ser o consumo atual / pct."""
    if janela not in ("5h", "semana") or not 1 <= pct <= 100:
        raise ValueError("informe a janela (5h ou semana) e um percentual entre 1 e 100")
    medida = estado(reg, agora)["janela_5h" if janela == "5h" else "semana"]
    if medida["usado"] <= 0:
        raise ValueError("ainda não há uso registrado nessa janela para calibrar")
    teto = round(medida["usado"] / (pct / 100), 1)
    configuracao.salvar(reg, {"teto_5h" if janela == "5h" else "teto_semana": teto})
    return {"janela": janela, "teto": teto}
