"""Ponto de entrada do módulo de uso: um registro por processo, coleta com intervalo mínimo e gravação do que o roteador respondeu.

Tudo aqui é "melhor esforço": falha ao registrar uso nunca pode atrapalhar uma resposta.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from jarvis.uso import coletor_claude
from jarvis.uso.registro import Registro, caminho_padrao

log = logging.getLogger(__name__)
_trava = threading.Lock()
_estado: dict = {"reg": None, "caminho": None, "coleta": 0.0}


def registro() -> Registro:
    caminho = caminho_padrao()
    with _trava:
        if _estado["reg"] is None or _estado["caminho"] != caminho:  # o caminho muda só nos testes (pasta temporária)
            if _estado["reg"] is not None:
                _estado["reg"].fechar()
            _estado.update(reg=Registro(caminho), caminho=caminho, coleta=0.0)
        return _estado["reg"]


def atualizar(intervalo: float = 20.0, raiz: Path | None = None, forcar: bool = False) -> Registro:
    """Coleta o que há de novo nos arquivos do Claude Code, no máximo uma vez a cada `intervalo` segundos."""
    reg = registro()
    if forcar or time.monotonic() - _estado["coleta"] >= intervalo:
        _estado["coleta"] = time.monotonic()
        try:
            coletor_claude.coletar(reg, raiz)
        except Exception:
            log.warning("não foi possível atualizar o uso de IA", exc_info=True)
    return reg


def registrar_resposta(resposta) -> None:
    """Chamado pelo roteador a cada resposta: uma linha por chamada (as locais entram com zero, para medir a economia)."""
    try:
        registro().ao_vivo(resposta.brain, getattr(resposta, "modelo", "") or "", getattr(resposta, "usage", None),
                           getattr(resposta, "custo_usd", None))
    except Exception:
        log.warning("não foi possível registrar o uso desta resposta", exc_info=True)


_pressao = {"em": 0.0, "valor": False}


def cota_sob_pressao(intervalo: float = 60.0) -> bool:
    """True quando a cota estimada do Claude (5 h ou semana) já passou do limiar de alerta. Com cache curto: roda a cada pedido."""
    if time.monotonic() - _pressao["em"] < intervalo:
        return _pressao["valor"]
    _pressao["em"] = time.monotonic()
    try:
        from jarvis.uso import cota

        estado = cota.estado(atualizar(), time.time())
        _pressao["valor"] = bool(estado["janela_5h"]["alerta"] or estado["semana"]["alerta"])
    except Exception:
        _pressao["valor"] = False
    return _pressao["valor"]
