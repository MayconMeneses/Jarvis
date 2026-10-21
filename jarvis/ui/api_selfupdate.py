"""Autoatualização: testes e benchmark depois de manter uma melhoria; reinício."""

from __future__ import annotations

import json
import logging
import threading

log = logging.getLogger(__name__)


class SelfUpdateMixin:
    """Verifica melhorias no próprio código e reinicia a Jarvis."""

    def _verify_self(self, run) -> None:
        """Depois de manter uma mudança no próprio código: testes + benchmark + aviso na janela."""
        import re
        from pathlib import Path

        from jarvis import selfimprove

        checks = selfimprove.verify(Path(run.pasta))
        idea = re.search(r"Ideia: (.+)$", run.tarefa, re.S)
        if checks["aprovado"] and idea:
            selfimprove.mark_done(idea.group(1).strip(), self._memory)
        self._diary(f"Verificação da melhoria: {'aprovada' if checks['aprovado'] else 'reprovada'}. {checks['testes']}")
        payload = {"id": run.id, "aprovado": checks["aprovado"], "testes": checks["testes"],
                   "pioras": checks["pioras"], "benchmark": checks.get("benchmark"),
                   "gate": checks.get("gate"), "limitacoes": checks.get("limitacoes", [])}
        self._push({"verify": payload})
        if self._voice is not None:
            self._voice.speak("A melhoria passou nos testes. Posso reiniciar para aplicar." if checks["aprovado"]
                              else "A melhoria não passou na verificação. Veja os detalhes na janela.")

    def _push(self, payload: dict) -> None:
        if self._window is None:
            return
        try:
            self._window.evaluate_js(f"window.onVoice({json.dumps(payload, ensure_ascii=False)})")
        except Exception:
            log.debug("janela indisponível", exc_info=True)

    def restart_jarvis(self) -> dict:
        """Abre uma Jarvis nova (com o código atualizado) e fecha esta."""
        import os
        import sys

        from jarvis import proc as processos

        command = [sys.executable] + ([] if getattr(sys, "frozen", False) else ["-m", "jarvis"])
        env = dict(os.environ, JARVIS_REINICIO="1")  # a nova espera esta liberar a instância única
        processos.abrir_visivel(command, cwd=os.getcwd(), env=env, creationflags=processos.DETACHED_PROCESS)  # nova Jarvis independente desta
        if self._quit is not None:
            threading.Timer(0.5, self._quit).start()
        return {"ok": True}
