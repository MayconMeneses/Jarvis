"""Batimento (heartbeat) dos processos do Jarvis: cada um avisa "estou vivo" a cada passada.

Fica em memória (thread-safe). Quando a memória do Jarvis é ligada, também grava `agente:<id>:ultimo`
(ISO), `agente:<id>:estado` (ok | erro | desligado) e `agente:<id>:detalhe`, no máximo 1x por minuto por
agente (ou na hora, se o estado mudou). Nunca grava em config.json nem guarda texto de erro: só o NOME da exceção.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

log = logging.getLogger(__name__)
OK, ERRO, DESLIGADO = "ok", "erro", "desligado"
ESTADOS = (OK, ERRO, DESLIGADO)
INTERVALO_GRAVACAO_S = 60.0
MAX_DETALHE = 80


@dataclass(frozen=True)
class Batida:
    ts: float          # segundos desde 1970 (relógio do PC)
    estado: str        # ok | erro | desligado
    detalhe: str = ""  # curto, escrito pelo próprio Jarvis (nunca texto de terceiros)


class Registro:
    def __init__(self, relogio: Callable[[], float] = time.time, intervalo_gravacao: float = INTERVALO_GRAVACAO_S) -> None:
        self._relogio, self._intervalo = relogio, intervalo_gravacao
        self._lock = threading.Lock()
        self._batidas: dict[str, Batida] = {}
        self._gravadas: dict[str, Batida] = {}
        self._mem = None

    def ligar_memoria(self, mem) -> None:
        self._mem = mem

    def marcar(self, agente: str, estado: str, detalhe: str = "") -> None:
        """Nunca levanta exceção: um defeito no painel não pode derrubar o processo que ele observa."""
        try:
            if estado not in ESTADOS:
                raise ValueError(f"estado inválido: {estado!r}")
            batida = Batida(self._relogio(), estado, str(detalhe)[:MAX_DETALHE])
            with self._lock:
                antes = self._gravadas.get(agente)
                self._batidas[agente] = batida
                gravar = self._mem is not None and (antes is None or antes.estado != estado or antes.detalhe != batida.detalhe
                                                   or batida.ts - antes.ts >= self._intervalo)
                if gravar:
                    self._gravadas[agente] = batida
            if gravar:
                self._gravar(agente, batida)
        except Exception:  # noqa: BLE001
            log.debug("não foi possível marcar o batimento de %s", agente, exc_info=True)

    def _gravar(self, agente: str, b: Batida) -> None:
        try:
            self._mem.set_meta(f"agente:{agente}:ultimo", datetime.fromtimestamp(b.ts).isoformat(timespec="seconds"))
            self._mem.set_meta(f"agente:{agente}:estado", b.estado)
            self._mem.set_meta(f"agente:{agente}:detalhe", b.detalhe)
        except Exception:  # noqa: BLE001
            log.debug("não foi possível gravar o batimento de %s", agente, exc_info=True)

    def ler(self, agente: str) -> Batida | None:
        """Último batimento (memória primeiro; depois o que ficou gravado de uma abertura anterior). Só leitura."""
        with self._lock:
            batida = self._batidas.get(agente)
        if batida is not None or self._mem is None:
            return batida
        try:
            ultimo, estado = self._mem.meta(f"agente:{agente}:ultimo"), self._mem.meta(f"agente:{agente}:estado")
            if not ultimo or estado not in ESTADOS:
                return None
            return Batida(datetime.fromisoformat(ultimo).timestamp(), estado, self._mem.meta(f"agente:{agente}:detalhe") or "")
        except Exception:  # noqa: BLE001
            return None


registro = Registro()


def marcar(agente: str, estado: str, detalhe: str = "") -> None:
    registro.marcar(agente, estado, detalhe)


def erro(agente: str, exc: BaseException, detalhe: str = "") -> None:
    """Marca erro guardando só o nome da exceção (a mensagem pode conter caminhos ou endereços)."""
    registro.marcar(agente, ERRO, (detalhe + " " if detalhe else "") + type(exc).__name__)
