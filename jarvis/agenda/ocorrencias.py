"""Eventos de um arquivo iCal -> ocorrências concretas numa janela, em hora local."""

from __future__ import annotations

import time as relogio
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

from jarvis.agenda import rrule
from jarvis.agenda.ics import Evento


@dataclass
class Ocorrencia:
    titulo: str
    inicio: datetime  # aware, na hora local
    fim: datetime
    dia_inteiro: bool = False
    local: str = ""
    agenda: str = ""
    cor: str = ""

    def to_dict(self) -> dict:
        return {"titulo": self.titulo, "inicio": self.inicio.isoformat(), "fim": self.fim.isoformat(),
                "dia_inteiro": self.dia_inteiro, "local": self.local, "agenda": self.agenda, "cor": self.cor}


def _como_local(valor: datetime | date, zona: tzinfo) -> datetime:
    if not isinstance(valor, datetime):
        return datetime.combine(valor, time(0), zona)
    return valor.replace(tzinfo=zona) if valor.tzinfo is None else valor.astimezone(zona)


def _normalizar(valor, zona: tzinfo):
    """Evento flutuante (sem fuso) vale na hora local."""
    return valor.replace(tzinfo=zona) if isinstance(valor, datetime) and valor.tzinfo is None else valor


ORCAMENTO_S = 5.0  # a agenda vem de fora: evento com recorrência absurda não pode prender o PC


def ocorrencias(eventos: list[Evento], ini: datetime, fim: datetime, zona: tzinfo, agenda: str = "", cor: str = "") -> list[Ocorrencia]:
    prazo = relogio.monotonic() + ORCAMENTO_S
    trocados: dict[str, list] = {}
    for e in eventos:
        if e.recorrencia_id is not None and e.uid:
            trocados.setdefault(e.uid, []).append(_normalizar(e.recorrencia_id, zona))
    achadas: list[Ocorrencia] = []
    for e in eventos:
        if e.cancelado:
            continue
        inicio, ate = _normalizar(e.inicio, zona), _normalizar(e.fim, zona)
        dia_inteiro = not isinstance(inicio, datetime)
        duracao = ate - inicio if type(ate) is type(inicio) else timedelta(0)
        regra = e.regra if e.recorrencia_id is None else None
        excecoes = [_normalizar(x, zona) for x in e.excecoes] + (trocados.get(e.uid, []) if regra else [])
        if relogio.monotonic() > prazo:
            break
        try:
            comecos = rrule.expandir(inicio, regra, ini, fim, excecoes, duracao, zona)
        except (ValueError, OverflowError):  # recorrência fora do calendário: só esse evento é ignorado
            continue
        for comeco in comecos:
            a = _como_local(comeco, zona)
            b = a + duracao
            achadas.append(Ocorrencia(e.titulo, a, b, dia_inteiro, e.local, agenda, cor))
    return achadas


def mesclar(listas: list[list[Ocorrencia]]) -> list[Ocorrencia]:
    """Timeline única: ordenada por início, sem repetir o mesmo compromisso presente em duas agendas."""
    vistos, unico = set(), []
    for o in sorted((o for lista in listas for o in lista), key=lambda o: (o.inicio, o.titulo)):
        chave = (o.titulo.lower(), o.inicio, o.fim)
        if chave not in vistos:
            vistos.add(chave)
            unico.append(o)
    return unico
