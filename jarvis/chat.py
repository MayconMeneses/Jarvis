"""Uma conversa: guarda o histórico recente e pergunta ao roteador."""

from __future__ import annotations

import threading

from jarvis.brains.base import Answer, Message
from jarvis.brains.router import Router

MAX_HISTORY = 20  # mensagens (pergunta + resposta contam separadas)


class Conversation:
    def __init__(self, router: Router, system: str) -> None:
        self.router = router
        self.system = system
        self.history: list[Message] = []
        self._lock = threading.Lock()  # a janela pode chamar de outra thread

    def ask(self, text: str) -> Answer:
        with self._lock:
            messages = self.history + [Message(role="user", content=text)]
            answer = self.router.ask(messages, self.system)
            self.history = (
                messages + [Message(role="assistant", content=answer.text)]
            )[-MAX_HISTORY:]
            return answer

    def note(self, text: str) -> None:
        """Registra um fato no histórico (ex.: resultado de uma ação aprovada)."""
        with self._lock:
            self.history = (
                self.history + [Message(role="assistant", content=f"[Registro do sistema] {text}")]
            )[-MAX_HISTORY:]

    def reset(self) -> None:
        with self._lock:
            self.history = []
