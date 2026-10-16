"""Aprendizado: nota de qualidade de cada resposta e caderno de melhorias."""

from __future__ import annotations

import json
import logging
import time

log = logging.getLogger(__name__)


class LearningMixin:
    """Avalia cada resposta e anota no caderno o que não foi bem."""

    def _evaluate(self, question: str, answer, seconds: float) -> dict | None:
        """Critérios de qualidade de toda resposta (heurísticas leves, sem modelo) + registro."""
        from jarvis.eval import quality

        try:
            result = quality.evaluate(question, answer.text)
        except Exception:
            log.debug("avaliação da resposta falhou", exc_info=True)
            return None
        try:
            from jarvis.config import data_dir

            record = {"quando": time.time(), "cerebro": answer.brain, "segundos": round(seconds, 2),
                      "media": result["media"], "notas": result["notas"], "pergunta": question[:200]}
            with (data_dir() / "avaliacoes.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return result

    def _learn_from(self, question: str, answer, quality_result: dict | None) -> None:
        """Anota no caderno o que a Jarvis não fez bem (para "melhore-se" depois)."""
        from jarvis.local.engine import HELP

        if answer.brain == "local" and answer.text.startswith(HELP[:40]) and len(question.split()) >= 3:
            self._note_idea(f"Entender e atender o pedido: \"{question[:120]}\"", "pedido não entendido")
        elif quality_result and quality_result.get("media") is not None and quality_result["media"] < 6:
            notes = {k: v for k, v in quality_result["notas"].items() if v is not None}
            weakest = min(notes, key=notes.get)
            self._note_idea(f"Melhorar a resposta para \"{question[:100]}\" (nota {quality_result['media']}, "
                            f"pior critério: {weakest})", "qualidade baixa")

    def _note_idea(self, idea: str, origin: str) -> None:
        from jarvis import selfimprove

        try:
            if selfimprove.add_idea(idea, origin, self._memory):
                log.info("melhoria anotada (%s): %s", origin, idea[:120])
        except OSError:
            log.debug("não foi possível anotar a melhoria", exc_info=True)
