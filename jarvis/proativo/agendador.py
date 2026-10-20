"""Agendador das iniciativas: confere as regras a cada minuto e entrega cada aviso uma única vez."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime

from jarvis.agentes import registro as agentes
from jarvis.proativo import REGRAS, Aviso, Contexto

log = logging.getLogger(__name__)
SILENCIO = (22, 7)  # entre 22h e 7h a Jarvis não fala sozinha (o texto ainda aparece, se a janela estiver aberta)


class Agendador:
    def __init__(self, cfg_loader, mem, entregar: Callable[[Aviso, bool], None], ram: Callable[[], int],
                 briefing=None, treino=None, projetos_parados=None, agora: Callable[[], datetime] = datetime.now,
                 uso=None) -> None:
        self._cfg_loader, self._mem, self._entregar, self._ram = cfg_loader, mem, entregar, ram
        self._briefing, self._treino, self._parados, self._agora = briefing, treino, projetos_parados, agora
        self._uso = uso
        self._seguidas = 0
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def pode_falar(self, cfg, agora: datetime, forcar: bool = False) -> bool:
        return bool(cfg.proativo_voz or forcar) and not (agora.hour >= SILENCIO[0] or agora.hour < SILENCIO[1])

    def tick(self) -> list[Aviso]:
        """Uma passada pelas regras. Devolve os avisos entregues agora."""
        cfg, agora = self._cfg_loader(), self._agora()
        if not cfg.proativo:
            agentes.marcar("proativo", agentes.DESLIGADO)
            return []
        from jarvis.proativo import LIMITE_RAM

        ram = self._ram()
        self._seguidas = self._seguidas + 1 if ram >= LIMITE_RAM else 0
        contexto = Contexto(agora, cfg, ram, self._seguidas, self._briefing, self._treino,
                            (lambda: self._parados(cfg.projetos)) if self._parados else None, uso=self._uso)
        entregues, falhou = [], False
        for regra in REGRAS:
            try:
                aviso = regra(contexto)
            except Exception:  # uma regra com defeito não derruba as outras
                log.warning("regra %s falhou", regra.__name__, exc_info=True)
                falhou = True
                continue
            if aviso is None or self._mem.meta("proativo:" + aviso.chave):
                continue
            self._mem.set_meta("proativo:" + aviso.chave, agora.isoformat(timespec="seconds"))
            self._entregar(aviso, self.pode_falar(cfg, agora, aviso.voz))
            entregues.append(aviso)
        agentes.marcar("proativo", agentes.ERRO if falhou else agentes.OK, "regra com defeito" if falhou else "")
        return entregues

    def start(self, intervalo: float = 60.0) -> None:
        def laco() -> None:
            while not self._parar.wait(intervalo):
                try:
                    self.tick()
                except Exception as exc:
                    agentes.erro("proativo", exc)
                    log.warning("agendador falhou", exc_info=True)

        self._thread = threading.Thread(target=laco, daemon=True, name="jarvis-proativo")
        self._thread.start()

    def stop(self) -> None:
        self._parar.set()
