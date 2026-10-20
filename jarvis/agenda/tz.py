"""Fusos horários dos eventos. Sem o pacote tzdata (comum no Windows) usa deslocamentos fixos conhecidos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

# Nomes do Windows/Outlook que aparecem em TZID.
_WINDOWS = {
    "E. South America Standard Time": "America/Sao_Paulo",
    "Brasilia Standard Time": "America/Sao_Paulo",
    "Central Brazilian Standard Time": "America/Cuiaba",
    "SA Eastern Standard Time": "America/Fortaleza",
    "Tocantins Standard Time": "America/Araguaina",
    "UTC": "UTC",
    "Coordinated Universal Time": "UTC",
}
# O Brasil não tem horário de verão desde 2019: deslocamento fixo é exato para eventos atuais.
_FIXOS = {
    "America/Sao_Paulo": -3, "America/Fortaleza": -3, "America/Recife": -3, "America/Bahia": -3,
    "America/Belem": -3, "America/Araguaina": -3, "America/Maceio": -3, "America/Cuiaba": -4,
    "America/Manaus": -4, "America/Campo_Grande": -4, "America/Rio_Branco": -5, "America/Noronha": -2,
}


def local() -> tzinfo:
    return datetime.now().astimezone().tzinfo or timezone.utc


def resolver(tzid: str | None) -> tzinfo | None:
    """Fuso do TZID, ou None se for desconhecido (o evento passa a valer na hora local)."""
    if not tzid:
        return None
    nome = _WINDOWS.get(tzid.strip('"'), tzid.strip('"'))
    if nome.upper() in ("UTC", "GMT", "Z"):
        return timezone.utc
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(nome)
    except Exception:  # sem tzdata ou nome inválido
        horas = _FIXOS.get(nome)
        return timezone(timedelta(hours=horas)) if horas is not None else None
