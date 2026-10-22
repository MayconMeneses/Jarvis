"""Resumo deslizante: turnos antigos viram notas curtas, sem gastar IA (barato e determinístico).

O histórico recente vai inteiro para o cérebro; o que sai dele (mais velho que MAX_HISTORY) é guardado aqui como uma nota
por mensagem, com limite de tamanho. O resumo vai no contexto de cada pergunta, então a conversa longa não perde o fio.
"""

from __future__ import annotations

import re

LIMITE_NOTA_USUARIO = 160
LIMITE_NOTA_JARVIS = 110
LIMITE_RESUMO = 1800  # caracteres (~450 tokens)
MAX_NOTAS = 80
_MARCAS = re.compile(r"[*_`#>]+|\[\[.*?\]\]|https?://\S*[^\s.,;:!?)]")


def _primeira_frase(texto: str, limite: int) -> str:
    texto = _MARCAS.sub("", texto)
    texto = re.sub(r"\s+([.!?])", lambda m: m.group(1), re.sub(r"\s+", " ", texto)).strip()
    frase = re.split(r"(?<=[.!?])\s", texto, maxsplit=1)[0]
    return frase if len(frase) <= limite else frase[:limite].rsplit(" ", 1)[0] + "…"


def nota(mensagem: dict) -> str:
    """Uma linha curta no lugar da mensagem."""
    usuario = mensagem["role"] == "user"
    limite = LIMITE_NOTA_USUARIO if usuario else LIMITE_NOTA_JARVIS
    return f"- {'Usuário' if usuario else 'Jarvis'}: {_primeira_frase(str(mensagem['content']), limite)}"


class Janela:
    """Notas dos turnos que já saíram do histórico."""

    def __init__(self) -> None:
        self.notas: list[str] = []

    def absorver(self, mensagens: list[dict]) -> None:
        self.notas += [nota(m) for m in mensagens]
        self.notas = self.notas[-MAX_NOTAS:]

    def texto(self, limite: int = LIMITE_RESUMO) -> str:
        """As notas mais recentes que cabem no limite (as mais antigas somem primeiro)."""
        if not self.notas:
            return ""
        escolhidas: list[str] = []
        total = 0
        for linha in reversed(self.notas):
            if total + len(linha) + 1 > limite:
                break
            escolhidas.append(linha)
            total += len(linha) + 1
        corpo = "\n".join(reversed(escolhidas))
        return corpo if len(escolhidas) == len(self.notas) else "(turnos mais antigos omitidos)\n" + corpo

    def limpar(self) -> None:
        self.notas = []
