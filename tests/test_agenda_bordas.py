"""Recorrência: BYMONTH em qualquer frequência, ordem dos meses e horário de verão."""

import zoneinfo
from datetime import datetime, timedelta, timezone

from jarvis.agenda import ics, ocorrencias

BRT = timezone(timedelta(hours=-3))


def _cal(evento: str) -> str:
    return f"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:1\r\n{evento}\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"


def _dias(texto: str, ini: str, fim: str, zona=BRT) -> list[str]:
    a, b = (datetime.fromisoformat(x).replace(tzinfo=zona) for x in (ini, fim))
    return [o.inicio.strftime("%Y-%m-%d %H:%M") for o in ocorrencias.ocorrencias(ics.ler(texto), a, b, zona)]


def test_anual_com_meses_fora_de_ordem_nao_perde_ocorrencia():
    texto = _cal("DTSTART:20240115T100000\r\nRRULE:FREQ=YEARLY;BYMONTH=12,1;BYMONTHDAY=15\r\nSUMMARY:x")
    assert _dias(texto, "2024-01-01T00:00", "2026-03-01T00:00") == [
        "2024-01-15 10:00", "2024-12-15 10:00", "2025-01-15 10:00", "2025-12-15 10:00", "2026-01-15 10:00"]


def test_bymonth_tambem_limita_a_regra_mensal():
    texto = _cal("DTSTART:20260305T080000\r\nRRULE:FREQ=MONTHLY;BYMONTH=3,9;BYMONTHDAY=5\r\nSUMMARY:x")
    assert _dias(texto, "2026-01-01T00:00", "2027-01-01T00:00") == ["2026-03-05 08:00", "2026-09-05 08:00"]


def test_bymonth_limita_a_regra_diaria_e_semanal():
    diaria = _cal("DTSTART:20260130T080000\r\nRRULE:FREQ=DAILY;BYMONTH=2;COUNT=3\r\nSUMMARY:x")
    assert _dias(diaria, "2026-01-01T00:00", "2026-04-01T00:00") == ["2026-02-01 08:00", "2026-02-02 08:00", "2026-02-03 08:00"]
    semanal = _cal("DTSTART:20260105T080000\r\nRRULE:FREQ=WEEKLY;BYDAY=MO;BYMONTH=2\r\nSUMMARY:x")
    assert _dias(semanal, "2026-01-01T00:00", "2026-03-01T00:00") == [
        "2026-02-02 08:00", "2026-02-09 08:00", "2026-02-16 08:00", "2026-02-23 08:00"]


def test_horario_de_verao_mantem_a_hora_de_parede():
    zona = zoneinfo.ZoneInfo("America/New_York")  # tzdata é dependência do projeto: sem skip
    texto = _cal("DTSTART;TZID=America/New_York:20261027T090000\r\nRRULE:FREQ=WEEKLY;COUNT=3\r\nSUMMARY:x")
    a, b = datetime(2026, 10, 1, tzinfo=zona), datetime(2026, 12, 1, tzinfo=zona)
    achadas = ocorrencias.ocorrencias(ics.ler(texto), a, b, zona)
    assert [o.inicio.strftime("%m-%d %H:%M") for o in achadas] == ["10-27 09:00", "11-03 09:00", "11-10 09:00"]
    assert [int(o.inicio.utcoffset().total_seconds() // 3600) for o in achadas] == [-4, -5, -5]  # a troca é em 1/11
