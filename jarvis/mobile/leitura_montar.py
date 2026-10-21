"""Liga as leituras extras do PC (vitais, sessões, tarefas, uso, radar, subagentes) às fontes reais, com cache curto.

Todas as fontes são injetáveis (testes) e só LEEM. Falha numa fonte vira erro genérico no servidor (502), sem detalhe.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime

from jarvis.mobile import leitura_pc, leitura_uso

TTL_VITAIS, TTL_SESSOES, TTL_TAREFAS, TTL_USO, TTL_RADAR = 5.0, 5.0, 5.0, 30.0, 60.0


def montar_extra(relogio: Callable[[], float] = time.monotonic, agora: Callable[[], datetime] = datetime.now,
                 epoch: Callable[[], float] = time.time, vitais: Callable[[], dict] | None = None, leitor_sessoes=None,
                 loja_tarefas=None, registro: Callable[[], object] | None = None,
                 radar: Callable[[], tuple[dict | None, list[dict]]] | None = None) -> dict[str, Callable[[], dict]]:
    from jarvis.mobile.leitura import _Cache

    estado: dict = {"leitor": leitor_sessoes}

    def leitor():
        if estado["leitor"] is None:
            from jarvis.dev import sessions

            estado["leitor"] = sessions.SessionReader()
        return estado["leitor"]

    def sub_vitais() -> dict:
        return leitura_pc.vitais_publicos((vitais or leitura_pc.ler_vitais)(), agora().astimezone())

    def subagentes() -> list:
        try:
            return list(leitor().subagentes())
        except Exception:  # noqa: BLE001  (subagentes são enfeite: sem eles as sessões ainda funcionam)
            return []

    def sub_sessoes() -> dict:
        return leitura_pc.sessoes_publicas(list(leitor().sessions()), subagentes(), epoch(), agora().astimezone())

    def sub_tarefas() -> dict:
        from jarvis.dev import runs_store

        return leitura_pc.tarefas_publicas((loja_tarefas or runs_store.RunStore()).all(), agora().astimezone())

    def sub_uso() -> dict:
        from jarvis.uso import cota, servico

        reg = registro() if registro else servico.atualizar()
        agora_e = epoch()
        dt = datetime.fromtimestamp(agora_e)
        zero = dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        return leitura_uso.uso_publico(reg.linhas(desde=zero), cota.estado(reg, agora_e), agora().astimezone())

    def sub_radar() -> dict:
        execucao, artigos = (radar or leitura_uso.ler_titulos_radar)()
        return leitura_uso.radar_publico(execucao, artigos, agora().astimezone())

    return {"vitais": _Cache(sub_vitais, TTL_VITAIS, relogio), "sessoes": _Cache(sub_sessoes, TTL_SESSOES, relogio),
            "tarefas": _Cache(sub_tarefas, TTL_TAREFAS, relogio), "uso": _Cache(sub_uso, TTL_USO, relogio),
            "radar": _Cache(sub_radar, TTL_RADAR, relogio), "_subagentes": subagentes}
