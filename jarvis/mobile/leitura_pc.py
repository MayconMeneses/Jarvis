"""Leitura do estado do PC para o celular pareado (vitais, sessões do Claude Code, tarefas). SOMENTE LEITURA, sem IA, sem rede.

Regra de ouro: sessões e tarefas podem ter caminhos, títulos e conversas. Aqui só saem contagens, o estado e um nome curto de
projeto (sem caminho). Nome de projeto/tarefa é texto de terceiros: sem controle, sem links, truncado, e o suspeito é omitido.
"""

from __future__ import annotations

import os

from jarvis.mobile.leitura import OMITIDO, limpo
from jarvis.radar import sanear

MAX_ITENS = 5
ESTADOS_SESSAO = ("permissao", "pergunta", "aguardando", "trabalhando", "nova", "desconhecido")
STATUS_TAREFA = ("na_fila", "rodando", "concluida", "falhou")
ESTADOS_SUB = ("rodando", "concluido", "falhou", "parado", "inativo")


def suspeito_texto(texto) -> bool:
    """Detector do Radar (o mais forte do projeto: homóglifos, letras separadas, várias línguas)."""
    return sanear.suspeito(str(texto or "")) is not None


def texto_seguro(texto, limite: int) -> str:
    return OMITIDO if suspeito_texto(texto) else limpo(texto, limite)


def _pct(v) -> int:
    return max(0, min(100, round(float(v)))) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def _gb(v) -> float:
    return round(max(0.0, float(v)) / 1e9, 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def nome_seguro(texto, limite: int) -> str:
    """Nome curto de projeto: caminho vira só o último trecho; suspeito vira aviso fixo."""
    bruto = str(texto or "").replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return texto_seguro(bruto, limite) if bruto else "(sem nome)"


def ler_vitais() -> dict:
    """Valores brutos do psutil (injetável nos testes)."""
    import psutil

    mem, disco = psutil.virtual_memory(), psutil.disk_usage(os.path.abspath(os.sep))
    return {"cpu": psutil.cpu_percent(interval=0.1), "ram": mem.percent, "ram_total": mem.total, "ram_usada": mem.used,
            "disco": disco.percent, "disco_total": disco.total, "disco_livre": disco.free}


def vitais_publicos(bruto: dict, agora) -> dict:
    return {"gerado": agora.isoformat(), "cpu": _pct(bruto.get("cpu")), "ram": _pct(bruto.get("ram")), "disco": _pct(bruto.get("disco")),
            "ram_total_gb": _gb(bruto.get("ram_total")), "ram_usada_gb": _gb(bruto.get("ram_usada")),
            "disco_total_gb": _gb(bruto.get("disco_total")), "disco_livre_gb": _gb(bruto.get("disco_livre"))}


def sessoes_publicas(sessoes: list, subagentes: list, agora_epoch: float, agora) -> dict:
    """`sessoes` = Session; `subagentes` = Subagente. Nada de nome/título da sessão, motivo, pasta, descrição ou transcrito."""
    estado = lambda s: s.estado if s.estado in ESTADOS_SESSAO else "desconhecido"  # noqa: E731
    contagem = {e: 0 for e in ESTADOS_SESSAO}
    for s in sessoes:
        contagem[estado(s)] += 1
    ordem = {e: i for i, e in enumerate(ESTADOS_SESSAO)}
    visiveis = sorted(sessoes, key=lambda s: (ordem[estado(s)], -float(s.atualizada_em or 0)))
    itens = [{"projeto": nome_seguro(s.projeto, 24), "estado": estado(s),
              "ha_s": max(0, round(agora_epoch - float(s.atualizada_em))) if s.atualizada_em else None} for s in visiveis[:MAX_ITENS]]
    sub_estado = lambda a: a.estado if a.estado in ESTADOS_SUB else "inativo"  # noqa: E731
    sub = {e: 0 for e in ESTADOS_SUB}
    for a in subagentes:
        sub[sub_estado(a)] += 1
    return {"gerado": agora.isoformat(), "total": len(sessoes), "contagem": contagem, "itens": itens,
            "subagentes": {"total": len(subagentes), "contagem": sub,
                           "itens": [{"projeto": nome_seguro(a.projeto, 24), "tipo": texto_seguro(a.tipo, 24), "estado": sub_estado(a)}
                                     for a in subagentes[:MAX_ITENS]]}}


def tarefas_publicas(runs: list, agora) -> dict:
    """`runs` = Run. Sai: projeto, status, modo e o início da tarefa pedida. Nunca resultado, diff, pasta nem erro."""
    status = lambda r: r.status if r.status in STATUS_TAREFA else "falhou"  # noqa: E731
    contagem = {e: 0 for e in STATUS_TAREFA}
    for r in runs:
        contagem[status(r)] += 1
    recentes = sorted(runs, key=lambda r: r.criada_em, reverse=True)[:MAX_ITENS]
    return {"gerado": agora.isoformat(), "total": len(runs), "contagem": contagem,
            "itens": [{"projeto": nome_seguro(r.projeto, 24), "status": status(r), "modo": limpo(r.modo, 12),
                       "tarefa": texto_seguro(r.tarefa, 60)} for r in recentes]}
