"""Roteador: tenta os cérebros em ordem e cai para o próximo se um falhar."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from jarvis.brains.base import Answer, Brain, BrainUnavailable, Message

log = logging.getLogger(__name__)


class NoBrainAvailable(RuntimeError):
    pass


class Router:
    def __init__(self, brains: Sequence[Brain]) -> None:
        if not brains:
            raise ValueError("é preciso ao menos um cérebro")
        self.brains = list(brains)

    def warm_up(self, system: str) -> None:
        """Prepara os cérebros que suportam isso (ex.: abre a sessão do Claude)."""
        for brain in self.brains:
            if hasattr(brain, "warm_up"):
                try:
                    brain.warm_up(system)
                except BrainUnavailable as exc:
                    log.info("não foi possível preparar %s: %s", brain.name, exc)

    def stop(self) -> None:
        for brain in self.brains:
            if hasattr(brain, "stop"):
                brain.stop()

    def ask(self, messages: list[Message], system: str) -> Answer:
        failures = []
        for brain in self.brains:
            try:
                return brain.ask(messages, system)
            except BrainUnavailable as exc:
                log.info("cérebro %s indisponível: %s", brain.name, exc)
                failures.append(f"{brain.name}: {exc}")
        raise NoBrainAvailable("nenhum cérebro respondeu (" + "; ".join(failures) + ")")
