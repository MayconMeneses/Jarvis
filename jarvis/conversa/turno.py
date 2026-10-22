"""O turno em andamento (pergunta, canal, resumo da conversa) para quem monta o contexto do cérebro.

Fica numa variável por thread: `Conversation.ask` e `Router.ask` rodam na mesma thread, então o roteador lê o turno sem
mudar a assinatura dos cérebros (que os testes e os cérebros externos conhecem).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

_estado = threading.local()


@dataclass
class Turno:
    texto: str
    canal: str = "texto"  # "texto" ou "voz"
    resumo: str = ""  # notas dos turnos antigos que saíram do histórico
    anteriores: list = field(default_factory=list)  # mensagens antes desta (para achar o assunto de um "e o outro?")


def definir(turno: Turno) -> None:
    _estado.turno = turno


def atual() -> Turno | None:
    return getattr(_estado, "turno", None)


def limpar() -> None:
    _estado.turno = None
