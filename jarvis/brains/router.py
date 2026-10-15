"""Roteador: tenta os cérebros em ordem e cai para o próximo se um falhar."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from jarvis.brains.base import Answer, Brain, BrainUnavailable

log = logging.getLogger(__name__)


class NoBrainAvailable(RuntimeError):
    pass


class Router:
    def __init__(self, brains: Sequence[Brain]) -> None:
        if not brains:
            raise ValueError("é preciso ao menos um cérebro")
        self.brains = list(brains)

    def ask(self, prompt: str, system: str) -> Answer:
        failures = []
        for brain in self.brains:
            try:
                return brain.ask(prompt, system)
            except BrainUnavailable as exc:
                log.info("cérebro %s indisponível: %s", brain.name, exc)
                failures.append(f"{brain.name}: {exc}")
        raise NoBrainAvailable("nenhum cérebro respondeu (" + "; ".join(failures) + ")")
