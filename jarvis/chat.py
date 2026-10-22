"""Uma conversa: guarda o histórico recente e pergunta ao roteador."""

from __future__ import annotations

import threading
from collections.abc import Callable

from jarvis.brains.base import Answer, Message
from jarvis.brains.router import Router
from jarvis.conversa import turno
from jarvis.conversa.resumo import Janela

MAX_HISTORY = 40  # mensagens (pergunta + resposta contam separadas); as mais antigas viram notas do resumo deslizante


class Conversation:
    def __init__(self, router: Router, system: str | Callable[[], str]) -> None:
        self.router = router
        # Função = recalculada a cada pergunta (hora atual, memórias novas).
        self.system = system
        self.history: list[Message] = []
        self.janela = Janela()  # notas dos turnos que já saíram do histórico
        self._lock = threading.Lock()  # a janela pode chamar de outra thread

    def _guardar(self, mensagens: list[Message]) -> None:
        """Fica com as últimas MAX_HISTORY; o que sai vira nota curta no resumo."""
        if len(mensagens) > MAX_HISTORY:
            self.janela.absorver(mensagens[:-MAX_HISTORY])
        self.history = mensagens[-MAX_HISTORY:]

    def ask(self, text: str, canal: str = "texto") -> Answer:
        with self._lock:
            messages = self.history + [Message(role="user", content=text)]
            turno.definir(turno.Turno(text, canal, self.janela.texto(), list(self.history)))
            try:
                answer = self.router.ask(messages, self._system())
            finally:
                turno.limpar()
            self._guardar(messages + [Message(role="assistant", content=answer.text)])
            return answer

    def _system(self) -> str:
        return self.system() if callable(self.system) else self.system

    def warm_up(self) -> None:
        self.router.warm_up(self._system())

    def remember_said(self, text: str) -> None:
        """Registra algo que a Jarvis disse por iniciativa própria (ex.: a saudação)."""
        with self._lock:
            self._guardar(self.history + [Message(role="assistant", content=text)])

    def note(self, text: str) -> None:
        """Registra um fato no histórico (ex.: resultado de uma ação aprovada)."""
        with self._lock:
            self._guardar(self.history + [Message(role="assistant", content=f"[Registro do sistema] {text}")])

    def replace_last_answer(self, text: str) -> None:
        """Troca o texto da última resposta guardada (ex.: sem a marcação [[SAVE]] da memória viva)."""
        with self._lock:
            if self.history and self.history[-1]["role"] == "assistant":
                self.history[-1] = Message(role="assistant", content=text)

    def reset(self) -> None:
        with self._lock:
            self.history = []
            self.janela.limpar()
