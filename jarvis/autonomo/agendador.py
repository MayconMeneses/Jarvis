"""Quando a Jarvis estuda sozinha: só com o PC parado, poucos assuntos por dia, e uma avaliação semanal do cérebro local."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime

from jarvis.autonomo import estudar, interesses

log = logging.getLogger(__name__)
OCIOSO_MINUTOS = 10
LIMITE_CPU = 60
LIMITE_RAM = 88


class Autonomo:
    def __init__(self, cfg_loader, mem, entregar: Callable[[str], None], pesquisar, formatar, saber_cita, *, ultimo_pedido: Callable[[], float],
                 agora: Callable[[], datetime] = datetime.now, carga: Callable[[], tuple[float, float]] | None = None, chave_brave=lambda: None,
                 avaliar_semana: Callable[[], str] | None = None) -> None:
        self._cfg_loader, self._mem, self._entregar = cfg_loader, mem, entregar
        self._pesquisar, self._formatar, self._saber_cita = pesquisar, formatar, saber_cita
        self._ultimo_pedido, self._agora, self._carga, self._brave = ultimo_pedido, agora, carga or self._carga_real, chave_brave
        self._avaliar_semana = avaliar_semana
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _carga_real() -> tuple[float, float]:
        import psutil

        return psutil.cpu_percent(interval=0.5), psutil.virtual_memory().percent

    def ocioso(self, agora: datetime) -> bool:
        """Sem pedido do usuário há 10 minutos e com CPU e memória sobrando: nunca atrapalha quem está usando o PC."""
        import time

        if time.time() - self._ultimo_pedido() < OCIOSO_MINUTOS * 60:
            return False
        cpu, ram = self._carga()
        return cpu < LIMITE_CPU and ram < LIMITE_RAM

    def _gasto_hoje(self, agora: datetime) -> int:
        return int(self._mem.meta(f"autonomo:dia:{agora:%Y-%m-%d}") or 0)

    def tick(self) -> list[str]:
        """Uma passada: no máximo UM assunto por vez. Devolve as notas criadas (referências)."""
        cfg, agora = self._cfg_loader(), self._agora()
        if not cfg.autonomo or not self.ocioso(agora):
            return []
        criadas: list[str] = []
        restante = cfg.autonomo_max_por_dia - self._gasto_hoje(agora)
        if restante > 0:
            assuntos = interesses.contar(interesses.pedidos_recentes(self._mem, hoje=agora.date()), self._saber_cita)
            for assunto in estudar.escolher(self._mem, assuntos, agora, cfg.autonomo_minimo, max(2, cfg.autonomo_minimo - 1), 1):
                try:
                    ref = estudar.estudar(self._mem, assunto, self._pesquisar, self._formatar, agora, self._brave())
                except Exception:  # sem internet ou site fora do ar: tenta de novo só depois do prazo
                    log.info("estudo de %s falhou", assunto.nome, exc_info=True)
                    self._mem.set_meta("autonomo:estudado:" + estudar.fold(assunto.nome), agora.isoformat(timespec="seconds"))
                    continue
                self._mem.set_meta(f"autonomo:dia:{agora:%Y-%m-%d}", str(self._gasto_hoje(agora) + 1))
                if ref:
                    criadas.append(ref)
                    self._entregar(f"📚 Acabei de estudar sozinha sobre **{assunto.nome}** (você perguntou {assunto.mencoes} vezes). Diga \"o que você aprendeu\" para ver.")
        if self._avaliar_semana and agora.weekday() == 6 and not self._mem.meta(f"autonomo:semana:{agora:%G-%V}"):
            self._mem.set_meta(f"autonomo:semana:{agora:%G-%V}", "feito")  # uma vez por semana, aconteça o que acontecer
            try:
                self._entregar("🧪 " + self._avaliar_semana())
            except Exception:  # noqa: BLE001
                log.info("avaliação semanal falhou", exc_info=True)
        return criadas

    def start(self, intervalo: float = 300.0) -> None:
        def laco() -> None:
            while not self._parar.wait(intervalo):
                try:
                    self.tick()
                except Exception:  # noqa: BLE001
                    log.warning("aprendizado autônomo falhou", exc_info=True)

        self._thread = threading.Thread(target=laco, daemon=True, name="jarvis-autonomo")
        self._thread.start()

    def stop(self) -> None:
        self._parar.set()
