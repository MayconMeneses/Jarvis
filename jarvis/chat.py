"""Uma conversa: guarda o histórico recente e pergunta ao roteador."""

from __future__ import annotations

import threading
from collections.abc import Callable

from jarvis.brains.base import Answer, Message
from jarvis.brains.router import Router

MAX_HISTORY = 20  # mensagens (pergunta + resposta contam separadas)


class Conversation:
    def __init__(self, router: Router, system: str | Callable[[], str]) -> None:
        self.router = router
        # Função = recalculada a cada pergunta (hora atual, memórias novas).
        self.system = system
        self.history: list[Message] = []
        self._lock = threading.Lock()  # a janela pode chamar de outra thread

    def ask(self, text: str) -> Answer:
        with self._lock:
            messages = self.history + [Message(role="user", content=text)]
            system = self.system() if callable(self.system) else self.system
            answer = self.router.ask(messages, system)
            self.history = (
                messages + [Message(role="assistant", content=answer.text)]
            )[-MAX_HISTORY:]
            return answer

    def remember_said(self, text: str) -> None:
        """Registra algo que a Jarvis disse por iniciativa própria (ex.: a saudação)."""
        with self._lock:
            self.history = (self.history + [Message(role="assistant", content=text)])[-MAX_HISTORY:]

    def note(self, text: str) -> None:
        """Registra um fato no histórico (ex.: resultado de uma ação aprovada)."""
        with self._lock:
            self.history = (
                self.history + [Message(role="assistant", content=f"[Registro do sistema] {text}")]
            )[-MAX_HISTORY:]

    def reset(self) -> None:
        with self._lock:
            self.history = []
