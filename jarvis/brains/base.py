"""Contrato comum de todos os "cérebros" (Claude, Gemini, NVIDIA NIM...)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class BrainUnavailable(RuntimeError):
    """O cérebro não pode responder agora (limite, rede, não instalado).

    O roteador trata este erro passando para o próximo cérebro da lista.
    """


@dataclass
class Answer:
    text: str
    brain: str


class Brain(Protocol):
    name: str

    def ask(self, prompt: str, system: str) -> Answer: ...
