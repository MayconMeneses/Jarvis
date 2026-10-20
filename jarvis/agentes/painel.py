"""Monta o retrato dos agentes (a resposta de agents_status): catálogo + batimentos + estado + subagentes + uso.

Só LÊ: não roda nenhum agente, não usa rede nem IA, não devolve segredo.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from jarvis.agentes import estado as est
from jarvis.agentes.catalogo import CATALOGO, Agente
from jarvis.agentes.registro import DESLIGADO, OK, Registro
from jarvis.agentes.registro import registro as registro_global

MAX_DETALHE = 80


def _vivo(agente: Agente, registro: Registro, vivos: dict[str, bool | None]):
    if agente.cadencia_s is not None:
        return None
    if agente.id in vivos:
        return vivos[agente.id]
    b = registro.ler(agente.id)  # sem predicado vivo (cérebro local): vale o último evento gravado
    return None if b is None else (b.estado == OK if b.estado in (OK, DESLIGADO) else None)


def retrato(cfg, *, agora: float | None = None, registro: Registro | None = None, vivos: dict[str, bool | None] | None = None,
            catalogo: tuple[Agente, ...] = CATALOGO) -> dict:
    agora = time.time() if agora is None else agora
    registro, vivos = registro or registro_global, vivos or {}
    itens, estados = [], []
    for ag in catalogo:
        try:
            ligado = bool(ag.liga(cfg))
        except Exception:  # noqa: BLE001
            ligado = False
        b = registro.ler(ag.id)
        d = est.decidir(agora, ligado=ligado, cadencia=ag.cadencia_s, ultimo=b.ts if b else None,
                        ultimo_estado=b.estado if b else None, vivo=_vivo(ag, registro, vivos),
                        ocioso_legitimo=ag.ocioso_legitimo, ocupado=bool(ag.ocupado_tolera and b and b.detalhe == "executando"))
        estados.append(d.state)
        proximo = None if ag.cadencia_s is None or d.age_s is None else max(0.0, ag.cadencia_s - d.age_s)
        itens.append({"id": ag.id, "nome": ag.nome, "faz": ag.faz, "modo": ag.modo, "state": d.state, "cadencia_s": ag.cadencia_s,
                      "last_ts": b.ts if b else None, "age_s": d.age_s, "proximo_s": proximo, "phase": d.phase,
                      "detalhe": (b.detalhe if b else "")[:MAX_DETALHE], "acao": ag.id if ag.acao else None})
    return {"server_now": agora, "resumo": est.resumo(estados), "agentes": itens}


def subagentes_do_claude(listar: Callable[[], list]) -> dict:
    """{resumo, itens} dos subagentes do Claude Code; qualquer falha de leitura vira lista vazia (nunca erro na tela)."""
    from jarvis.dev import subagentes

    try:
        itens = listar()
    except Exception:  # noqa: BLE001
        itens = []
    return {"resumo": subagentes.resumo(itens), "itens": [i.publico() for i in itens]}
