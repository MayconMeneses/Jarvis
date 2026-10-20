"""Recorrência (RRULE): DAILY, WEEKLY, MONTHLY e YEARLY com INTERVAL, BYDAY, BYMONTHDAY, BYMONTH, COUNT, UNTIL e EXDATE.

A conta é feita na hora "de parede" do fuso do evento (uma reunião às 9h continua às 9h depois da troca de horário).
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta, tzinfo

_DIAS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
_FREQ = ("DAILY", "WEEKLY", "MONTHLY", "YEARLY")
MAX_PERIODOS = 20000


def ler_regra(texto: str, tzid: str | None = None) -> dict | None:
    """Texto do RRULE -> dict, ou None se a regra não é suportada (o evento vale então uma vez só)."""
    from jarvis.agenda import ics

    bruto = {}
    for parte in texto.split(";"):
        chave, _, valor = parte.partition("=")
        bruto[chave.strip().upper()] = valor.strip()
    if bruto.get("FREQ", "").upper() not in _FREQ:
        return None
    try:
        regra = {"freq": bruto["FREQ"].upper(), "intervalo": max(1, int(bruto.get("INTERVAL") or 1)),
                 "contagem": int(bruto["COUNT"]) if bruto.get("COUNT") else None, "ate": None,
                 "dia_mes": [int(x) for x in bruto.get("BYMONTHDAY", "").split(",") if x],
                 "mes": [int(x) for x in bruto.get("BYMONTH", "").split(",") if x], "dia_semana": []}
        for item in (x for x in bruto.get("BYDAY", "").split(",") if x):
            m = re.fullmatch(r"([+-]?\d{1,2})?(MO|TU|WE|TH|FR|SA|SU)", item.strip().upper())
            if not m:
                return None
            regra["dia_semana"].append((int(m.group(1) or 0), _DIAS[m.group(2)]))
    except ValueError:
        return None
    if bruto.get("UNTIL"):
        regra["ate"] = ics.ler_data(bruto["UNTIL"], {"TZID": tzid} if tzid else {})
        if regra["ate"] is None:
            return None
    return regra


def _dias_do_mes(ano: int, mes: int, regra: dict, base: datetime) -> list[date]:
    ultimo = calendar.monthrange(ano, mes)[1]
    if regra["dia_mes"]:
        dias = {d if d > 0 else ultimo + d + 1 for d in regra["dia_mes"]}
        return [date(ano, mes, d) for d in sorted(dias) if 1 <= d <= ultimo]
    if regra["dia_semana"]:
        achados = set()
        for ordem, dia in regra["dia_semana"]:
            todos = [date(ano, mes, d) for d in range(1, ultimo + 1) if date(ano, mes, d).weekday() == dia]
            if ordem == 0:
                achados.update(todos)
            elif 0 < abs(ordem) <= len(todos):
                achados.add(todos[ordem - 1] if ordem > 0 else todos[ordem])
        return sorted(achados)
    return [date(ano, mes, base.day)] if base.day <= ultimo else []  # dia 31 pula os meses curtos


def _periodo(base: datetime, regra: dict, n: int) -> list[datetime]:
    freq, passo, hora = regra["freq"], regra["intervalo"], base.time()
    if freq == "DAILY":
        dia = base.date() + timedelta(days=n * passo)
        permitidos = {d for _, d in regra["dia_semana"]}
        dias = [dia] if not permitidos or dia.weekday() in permitidos else []
    elif freq == "WEEKLY":
        segunda = base.date() - timedelta(days=base.weekday()) + timedelta(weeks=n * passo)
        semana = sorted({d for _, d in regra["dia_semana"]}) or [base.weekday()]
        dias = [segunda + timedelta(days=d) for d in semana]
    elif freq == "MONTHLY":
        ano, mes = divmod(base.year * 12 + base.month - 1 + n * passo, 12)
        dias = _dias_do_mes(ano, mes + 1, regra, base)
    else:
        ano = base.year + n * passo
        dias = [d for mes in (regra["mes"] or [base.month]) for d in _dias_do_mes(ano, mes, regra, base)]
    return [x for x in (datetime.combine(d, hora) for d in dias) if x >= base]


def _primeiro_periodo(base: datetime, regra: dict, alvo: datetime) -> int:
    """Primeiro período que pode tocar a janela (só vale sem COUNT, que exige contar desde o início)."""
    freq, passo = regra["freq"], regra["intervalo"]
    if alvo <= base:
        return 0
    if freq == "DAILY":
        n = (alvo.date() - base.date()).days // passo
    elif freq == "WEEKLY":
        n = ((alvo.date() - base.date()).days // 7) // passo
    elif freq == "MONTHLY":
        n = ((alvo.year - base.year) * 12 + alvo.month - base.month) // passo
    else:
        n = (alvo.year - base.year) // passo
    return max(0, n - 1)


def _gerar(base: datetime, regra: dict, primeiro: int) -> Iterator[datetime]:
    for n in range(primeiro, primeiro + MAX_PERIODOS):
        yield from _periodo(base, regra, n)


def _naive(valor: datetime | date, zona: tzinfo | None, fim_do_dia: bool = False) -> datetime:
    if isinstance(valor, datetime):
        return valor.astimezone(zona).replace(tzinfo=None) if valor.tzinfo and zona else valor.replace(tzinfo=None)
    return datetime.combine(valor, time(23, 59, 59) if fim_do_dia else time(0))


def expandir(inicio: datetime | date, regra: dict | None, ini: datetime, fim: datetime, excecoes=(),
             duracao: timedelta = timedelta(0), zona_local: tzinfo | None = None) -> list[datetime | date]:
    """Inícios das ocorrências que tocam [ini, fim). `ini` e `fim` são aware. Dia inteiro devolve `date`."""
    dia_inteiro = not isinstance(inicio, datetime)
    zona = zona_local if dia_inteiro else (inicio.tzinfo or zona_local)
    base = _naive(inicio, zona)
    janela_ini, janela_fim = _naive(ini, zona), _naive(fim, zona)
    ex_dt = {_naive(e, zona) for e in excecoes if isinstance(e, datetime)}
    ex_dias = {e for e in excecoes if not isinstance(e, datetime)}
    ate = _naive(regra["ate"], zona, fim_do_dia=True) if regra and regra["ate"] is not None else None
    if regra is None:
        candidatos: Iterator[datetime] = iter([base])
    else:
        primeiro = 0 if regra["contagem"] else _primeiro_periodo(base, regra, janela_ini - duracao)
        candidatos = _gerar(base, regra, primeiro)
    achados: list[datetime | date] = []
    for n, ocorrencia in enumerate(candidatos, start=1):
        if regra and regra["contagem"] and n > regra["contagem"]:
            break
        if (ate is not None and ocorrencia > ate) or ocorrencia >= janela_fim:
            break
        if (ocorrencia >= janela_ini or ocorrencia + duracao > janela_ini) \
                and ocorrencia not in ex_dt and ocorrencia.date() not in ex_dias:
            achados.append(ocorrencia.date() if dia_inteiro else ocorrencia.replace(tzinfo=zona))
    return achados
