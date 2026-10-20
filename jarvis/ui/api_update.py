"""Atualização automática da Jarvis instalada: procura, baixa e instala versões novas do GitHub."""

from __future__ import annotations

import logging
import sys
import threading

from jarvis import updater
from jarvis.agentes import registro as agentes
from jarvis.config import data_dir

log = logging.getLogger(__name__)

CHECK_EVERY_SECONDS = 6 * 3600


class UpdateMixin:
    """Usa self._cfg, self._push e self._quit (definidos em Api)."""

    _update_stop: threading.Event | None = None

    def _updates_dir(self):
        return data_dir() / "atualizacoes"

    def start_update_loop(self) -> None:
        """Só na versão instalada: confere ao abrir e a cada 6 horas. Na abertura, instala sozinha."""
        if not getattr(sys, "frozen", False) or not self._cfg.atualizacao_automatica:
            agentes.marcar("atualizador", agentes.DESLIGADO, "só na versão instalada")
            return
        self._update_stop = threading.Event()
        threading.Thread(target=self._update_loop, daemon=True, name="jarvis-atualizar").start()

    def stop_update_loop(self) -> None:
        if self._update_stop is not None:
            self._update_stop.set()

    def _update_loop(self) -> None:
        first = True
        while True:
            try:
                if first and updater.pending(self._updates_dir()) and self.install_update()["ok"]:
                    return  # um instalador já baixado e conferido: atualiza agora, na abertura
                self.check_update()
            except Exception as exc:
                agentes.erro("atualizador", exc)
                log.exception("falha na checagem de atualização")
            first = False
            if self._update_stop.wait(CHECK_EVERY_SECONDS):
                return

    def check_update(self) -> dict:
        """Procura e baixa a versão nova; avisa a janela quando ela está pronta."""
        result = updater.check(self._updates_dir())
        agentes.marcar("atualizador", agentes.OK, str(result.get("estado", ""))[:30])
        if result["estado"] == "pronta":
            self._push({"update": {"versao": result["versao"], "notas": result.get("notas", "")}})
        return result

    def install_update(self) -> dict:
        """Roda o instalador já conferido; ele fecha esta Jarvis e abre a nova."""
        if not updater.install(self._updates_dir()):
            return {"ok": False}
        if self._quit is not None:
            threading.Timer(1.5, self._quit).start()
        return {"ok": True}
