"""Aprovações: executar ações propostas e manter/desfazer mudanças do Claude Code."""

from __future__ import annotations

import logging
import threading

from jarvis.pc import actions

log = logging.getLogger(__name__)


class ReviewMixin:
    """Aprovações do usuário: ações propostas e mudanças de código."""

    def decide(self, action_id: str, approve: bool) -> dict:
        try:
            action = actions.decide(self._store, str(action_id), bool(approve))
        except (ValueError, FileNotFoundError) as exc:
            return {"status": "falhou", "resultado": str(exc)}
        log.info("ação %s %s: %s", action.kind, action.status, action.resultado)
        self._diary(f"Ação {action.status}: {action.descricao} {action.resultado}")
        self._conversation.note(f"Ação '{action.descricao}' {action.status}. {action.resultado}")
        return {"status": action.status, "resultado": action.resultado}

    def review_run(self, run_id: str, keep: bool) -> dict:
        """Manter ou desfazer as mudanças que o Claude Code fez num projeto."""
        from jarvis.dev import runs

        try:
            run = runs.review(runs.RunStore(), str(run_id), bool(keep))
        except (ValueError, RuntimeError, OSError) as exc:
            return {"status": "falhou", "resultado": str(exc)}
        message = run.alteracoes.splitlines()[-1]
        self._diary(f"Mudanças no projeto {run.projeto}: {run.revisao}. {message}")
        self._conversation.note(f"Mudanças do Claude Code no projeto {run.projeto}: {run.revisao} "
                                f"pelo usuário. {message}")
        from jarvis import selfimprove

        if keep and run.projeto == selfimprove.PROJECT_NAME:
            threading.Thread(target=self._verify_self, args=(run,), daemon=True, name="jarvis-verificacao").start()
            message += " Rodando os testes e o benchmark para conferir…"
        return {"status": run.revisao, "resultado": message}

    def revert_run(self, run_id: str) -> dict:
        """Desfaz mudanças que já tinham sido mantidas (ex.: a verificação reprovou)."""
        from jarvis.dev import runs

        try:
            run = runs.revert(runs.RunStore(), str(run_id))
        except (ValueError, RuntimeError, OSError) as exc:
            return {"ok": False, "resultado": str(exc)}
        message = run.alteracoes.splitlines()[-1]
        self._conversation.note(f"Mudanças no projeto {run.projeto} desfeitas após a verificação. {message}")
        return {"ok": True, "resultado": message}
