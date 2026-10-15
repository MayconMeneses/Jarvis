"""Formato comum de e-mail e contrato das contas (Gmail, Outlook)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

# Categorias que a Jarvis aplica (marcadores no Gmail, categorias no Outlook).
CATEGORIES = (
    "Importante",
    "Financeiro",
    "Trabalho e vagas",
    "Promoções",
    "Notificações",
    "Ler depois",
    "Suspeito",
)


class MailError(RuntimeError):
    """Falha ao falar com o provedor (rede, token expirado, permissão)."""


@dataclass
class Mail:
    id: str  # "<conta>:<id do provedor>"
    conta: str
    remetente: str
    assunto: str
    data: str
    previa: str
    nao_lido: bool

    def to_dict(self) -> dict:
        return asdict(self)


def split_id(mail_id: str) -> tuple[str, str]:
    account, sep, native = mail_id.partition(":")
    if not sep or not native or account not in ("gmail", "outlook"):
        raise ValueError(f"id de e-mail inválido: {mail_id!r}")
    return account, native


class MailAccount(Protocol):
    name: str

    def list_recent(self, limit: int, unread_only: bool) -> list[Mail]: ...

    def apply_category(self, native_ids: list[str], category: str) -> None:
        """Só adiciona marcador/categoria. Nunca apaga, move para a lixeira ou envia."""
        ...
