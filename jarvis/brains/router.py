"""Roteador: tenta os cérebros em ordem e cai para o próximo se um falhar."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

from jarvis.brains.base import Answer, Brain, BrainUnavailable, Message

log = logging.getLogger(__name__)


class NoBrainAvailable(RuntimeError):
    pass


class Router:
    def __init__(self, brains: Sequence[Brain], prefer: Callable[[str], str | None] | None = None,
                 visible: Callable[[Brain], bool] | None = None, contexto: Callable[[str], str] | None = None) -> None:
        if not brains:
            raise ValueError("é preciso ao menos um cérebro")
        self.brains = list(brains)
        # Avaliado a cada pedido: cérebro invisível não é chamado nem preparado (ex.: modo sem IA).
        self.visible = visible
        # Recebe o texto do pedido e diz qual cérebro tentar primeiro (ver policy.py).
        self.prefer = prefer
        # Recebe o texto do pedido e devolve fatos extras para o prompt de sistema das IAs (RAG do autoconhecimento da Jarvis).
        self.contexto = contexto

    def order(self, messages: list[Message]) -> list[Brain]:
        brains = [b for b in self.brains if self.visible is None or self.visible(b)]
        first = self.prefer(messages[-1]["content"]) if self.prefer and messages else None
        if first is None:
            return brains
        return sorted(brains, key=lambda b: b.name != first)  # estável: o resto mantém a ordem

    def warm_up(self, system: str) -> None:
        """Prepara os cérebros que suportam isso (ex.: abre a sessão do Claude)."""
        for brain in self.brains:
            if self.visible is not None and not self.visible(brain):
                continue  # sem IA: não abre a sessão do Claude nem gasta memória à toa
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
        if self.contexto and messages:
            try:
                system += self.contexto(messages[-1]["content"])
            except Exception:  # melhor esforço: sem o contexto extra a IA ainda responde
                log.info("contexto extra indisponível", exc_info=True)
        for brain in self.order(messages):
            try:
                resposta = brain.ask(messages, system)
                from jarvis.uso import servico

                servico.registrar_resposta(resposta)  # uso de IA: melhor esforço, nunca atrapalha a resposta
                return resposta
            except BrainUnavailable as exc:
                log.info("cérebro %s indisponível: %s", brain.name, exc)
                failures.append(f"{brain.name}: {exc}")
        raise NoBrainAvailable("nenhum cérebro respondeu (" + "; ".join(failures) + ")")
