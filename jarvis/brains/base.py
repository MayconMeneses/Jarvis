"""Contrato comum de todos os "cérebros" (Claude, Gemini, NVIDIA NIM...)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, TypedDict


class Message(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class BrainUnavailable(RuntimeError):
    """O cérebro não pode responder agora (limite, rede, sem chave, não instalado).

    O roteador trata este erro passando para o próximo cérebro da lista.
    """


@dataclass
class Answer:
    text: str
    brain: str
    usage: dict | None = None  # {in, out, cw, cw1h, cr} em tokens (ver jarvis/uso/normaliza.py)
    custo_usd: float | None = None  # custo informado pelo provedor, quando houver
    modelo: str = ""


class Brain(Protocol):
    name: str

    def ask(self, messages: list[Message], system: str) -> Answer:
        """Responde à última mensagem, considerando as anteriores como histórico."""
        ...
