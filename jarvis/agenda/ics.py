"""Leitor de iCalendar (RFC 5545) para agendas pessoais. O texto vem da internet: é só dado, nunca é executado."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from jarvis.agenda import rrule, tz

MAX_BYTES = 5_000_000
MAX_EVENTOS = 5000


@dataclass
class Evento:
    uid: str
    titulo: str
    inicio: datetime | date
    fim: datetime | date
    local: str = ""
    regra: dict | None = None
    excecoes: list = field(default_factory=list)
    recorrencia_id: datetime | date | None = None
    cancelado: bool = False


def desdobrar(texto: str) -> list[str]:
    """Junta as linhas dobradas (a continuação começa com espaço ou tab)."""
    return re.sub(r"\r?\n[ \t]", "", texto.replace("\r\n", "\n").replace("\r", "\n")).split("\n")


def _fora_de_aspas(texto: str, separador: str) -> list[str]:
    partes, atual, aspas = [], [], False
    for c in texto:
        if c == '"':
            aspas = not aspas
        if c == separador and not aspas:
            partes.append("".join(atual))
            atual = []
        else:
            atual.append(c)
    partes.append("".join(atual))
    return partes


def ler_linha(linha: str) -> tuple[str, dict, str] | None:
    """NOME;PARAM=valor:valor -> (NOME, {PARAM: valor}, valor)."""
    aspas = False
    for i, c in enumerate(linha):
        if c == '"':
            aspas = not aspas
        elif c == ":" and not aspas:
            nome, *params = _fora_de_aspas(linha[:i], ";")
            dados = {}
            for p in params:
                chave, _, v = p.partition("=")
                dados[chave.upper()] = v.strip('"')
            return nome.strip().upper(), dados, linha[i + 1:]
    return None


def texto_de(valor: str) -> str:
    return re.sub(r"\\([nN,;\\])", lambda m: "\n" if m.group(1) in "nN" else m.group(1), valor)


def ler_data(valor: str, params: dict) -> datetime | date | None:
    """Dia inteiro (date), UTC (Z), com TZID ou flutuante (naive: vale na hora local)."""
    valor = valor.strip()
    try:
        if params.get("VALUE") == "DATE" or (len(valor) == 8 and valor.isdigit()):
            return datetime.strptime(valor[:8], "%Y%m%d").date()
        momento = datetime.strptime(valor.rstrip("Z"), "%Y%m%dT%H%M%S")
    except ValueError:
        return None
    if valor.endswith("Z"):
        return momento.replace(tzinfo=timezone.utc)
    zona = tz.resolver(params.get("TZID"))
    return momento.replace(tzinfo=zona) if zona else momento


def ler_duracao(valor: str) -> timedelta | None:
    m = re.fullmatch(r"([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", valor.strip())
    if not m:
        return None
    sinal, sem, dia, h, mi, s = m.groups()
    total = timedelta(weeks=int(sem or 0), days=int(dia or 0), hours=int(h or 0), minutes=int(mi or 0), seconds=int(s or 0))
    return -total if sinal == "-" else total


def _montar(props: dict[str, list[tuple[dict, str]]]) -> Evento | None:
    def um(nome: str) -> tuple[dict, str] | None:
        return props[nome][0] if props.get(nome) else None

    ini = um("DTSTART")
    inicio = ler_data(ini[1], ini[0]) if ini else None
    if inicio is None:
        return None
    fim = None
    if um("DTEND"):
        fim = ler_data(um("DTEND")[1], um("DTEND")[0])
    elif um("DURATION") and (d := ler_duracao(um("DURATION")[1])) is not None:
        fim = inicio + d
    if fim is None or isinstance(fim, datetime) != isinstance(inicio, datetime) or _antes(fim, inicio):
        fim = inicio if isinstance(inicio, datetime) else inicio + timedelta(days=1)
    excecoes = []
    for params, valor in props.get("EXDATE", []):
        excecoes += [d for parte in valor.split(",") if (d := ler_data(parte, params)) is not None]
    rid = um("RECURRENCE-ID")
    return Evento(
        uid=texto_de(um("UID")[1]) if um("UID") else "",
        titulo=texto_de(um("SUMMARY")[1]).strip() if um("SUMMARY") else "(sem título)",
        inicio=inicio, fim=fim,
        local=texto_de(um("LOCATION")[1]).strip() if um("LOCATION") else "",
        regra=rrule.ler_regra(um("RRULE")[1], ini[0].get("TZID")) if um("RRULE") else None,
        excecoes=excecoes,
        recorrencia_id=ler_data(rid[1], rid[0]) if rid else None,
        cancelado=bool(um("STATUS") and um("STATUS")[1].strip().upper() == "CANCELLED"),
    )


def _antes(a, b) -> bool:
    try:
        return a < b
    except TypeError:  # naive contra aware
        return False


def ler(texto: str) -> list[Evento]:
    """Todos os VEVENT do arquivo. Evento malformado é ignorado, não derruba a leitura."""
    eventos: list[Evento] = []
    props: dict[str, list[tuple[dict, str]]] | None = None
    fundo = 0  # componentes dentro do VEVENT (VALARM...): as propriedades deles não são do evento
    for linha in desdobrar(texto[:MAX_BYTES]):
        item = ler_linha(linha)
        if item is None:
            continue
        nome, params, valor = item
        if nome == "BEGIN":
            if props is None and valor.strip().upper() == "VEVENT":
                props, fundo = {}, 0
            elif props is not None:
                fundo += 1
        elif nome == "END" and props is not None:
            if fundo > 0:
                fundo -= 1
                continue
            try:
                evento = _montar(props)
            except (ValueError, OverflowError):
                evento = None
            if evento is not None:
                eventos.append(evento)
            props = None
            if len(eventos) >= MAX_EVENTOS:
                break
        elif props is not None and fundo == 0:
            props.setdefault(nome, []).append((params, valor))
    return eventos
