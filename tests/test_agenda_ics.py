"""Leitor de iCalendar e recorrência: casos de fronteira."""

from datetime import date, datetime, timedelta, timezone

from jarvis.agenda import ics, ocorrencias

BRT = timezone(timedelta(hours=-3))


def cal(*eventos: str) -> str:
    return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n" + "".join(f"BEGIN:VEVENT\r\n{e}\r\nEND:VEVENT\r\n" for e in eventos) + "END:VCALENDAR\r\n"


def janela(texto: str, ini: str, fim: str):
    a, b = (datetime.fromisoformat(x).replace(tzinfo=BRT) for x in (ini, fim))
    return ocorrencias.ocorrencias(ics.ler(texto), a, b, BRT)


def dias(lista):
    return [o.inicio.strftime("%Y-%m-%d %H:%M") for o in lista]


def test_unfolding_e_texto_escapado():
    texto = cal("UID:1\r\nDTSTART:20261020T120000Z\r\nSUMMARY:Reuniao muito\r\n  longa\\, com virgula\\nlinha 2\r\nLOCATION:Sala\\;3")
    [e] = ics.ler(texto)
    assert e.titulo == "Reuniao muito longa, com virgula\nlinha 2"
    assert e.local == "Sala;3"


def test_utc_vira_hora_local_e_tzid_funciona():
    texto = cal("UID:1\r\nDTSTART:20261020T120000Z\r\nDTEND:20261020T130000Z\r\nSUMMARY:UTC",
                "UID:2\r\nDTSTART;TZID=America/Sao_Paulo:20261020T090000\r\nDTEND;TZID=America/Sao_Paulo:20261020T100000\r\nSUMMARY:SP",
                "UID:3\r\nDTSTART;TZID=E. South America Standard Time:20261020T140000\r\nSUMMARY:Windows",
                "UID:4\r\nDTSTART:20261020T150000\r\nSUMMARY:Flutuante")
    achadas = janela(texto, "2026-10-20T00:00", "2026-10-21T00:00")
    assert {o.titulo: o.inicio.strftime("%H:%M") for o in achadas} == {"UTC": "09:00", "SP": "09:00", "Windows": "14:00", "Flutuante": "15:00"}
    assert all(o.inicio.utcoffset() == timedelta(hours=-3) for o in achadas)


def test_dia_inteiro_tem_fim_exclusivo():
    texto = cal("UID:1\r\nDTSTART;VALUE=DATE:20261020\r\nDTEND;VALUE=DATE:20261022\r\nSUMMARY:Viagem")
    assert len(janela(texto, "2026-10-20T00:00", "2026-10-21T00:00")) == 1
    assert len(janela(texto, "2026-10-21T00:00", "2026-10-22T00:00")) == 1  # segundo dia
    assert janela(texto, "2026-10-22T00:00", "2026-10-23T00:00") == []      # o DTEND não conta
    [o] = janela(texto, "2026-10-20T00:00", "2026-10-21T00:00")
    assert o.dia_inteiro and o.fim - o.inicio == timedelta(days=2)


def test_dia_inteiro_sem_dtend_dura_um_dia():
    [e] = ics.ler(cal("UID:1\r\nDTSTART;VALUE=DATE:20261020\r\nSUMMARY:Feriado"))
    assert e.fim == date(2026, 10, 21)


def test_fronteiras_da_janela():
    texto = cal("UID:1\r\nDTSTART:20261020T210000Z\r\nDTEND:20261020T230000Z\r\nSUMMARY:Noite",  # 18h-20h locais
                "UID:2\r\nDTSTART:20261021T020000Z\r\nDTEND:20261021T040000Z\r\nSUMMARY:Madrugada")  # 23h-01h locais
    assert dias(janela(texto, "2026-10-20T20:00", "2026-10-21T00:00")) == ["2026-10-20 23:00"]  # acabou às 20h: fora; o outro começa antes do fim da janela
    assert dias(janela(texto, "2026-10-21T00:00", "2026-10-21T12:00")) == ["2026-10-20 23:00"]  # atravessa a meia-noite e aparece no dia seguinte
    assert janela(texto, "2026-10-20T20:00", "2026-10-20T23:00") == []                          # começa exatamente no fim da janela: fora


def test_diaria_com_contagem_e_exdate():
    texto = cal("UID:1\r\nDTSTART:20261020T120000Z\r\nRRULE:FREQ=DAILY;COUNT=4\r\nEXDATE:20261022T120000Z\r\nSUMMARY:Daily")
    assert dias(janela(texto, "2026-10-01T00:00", "2026-12-01T00:00")) == ["2026-10-20 09:00", "2026-10-21 09:00", "2026-10-23 09:00"]


def test_semanal_intervalo_e_byday():
    texto = cal("UID:1\r\nDTSTART:20261019T130000Z\r\nRRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE\r\nSUMMARY:Quinzenal")  # segunda 19/10
    assert dias(janela(texto, "2026-10-19T00:00", "2026-11-10T00:00")) == [
        "2026-10-19 10:00", "2026-10-21 10:00", "2026-11-02 10:00", "2026-11-04 10:00"]


def test_semanal_com_until_inclusivo():
    texto = cal("UID:1\r\nDTSTART:20261019T130000Z\r\nRRULE:FREQ=WEEKLY;UNTIL=20261102T130000Z\r\nSUMMARY:Ate")
    assert dias(janela(texto, "2026-10-01T00:00", "2027-01-01T00:00")) == ["2026-10-19 10:00", "2026-10-26 10:00", "2026-11-02 10:00"]


def test_mensal_ultima_sexta_e_dia_31_pula_meses_curtos():
    ultima = cal("UID:1\r\nDTSTART:20261030T130000Z\r\nRRULE:FREQ=MONTHLY;BYDAY=-1FR;COUNT=3\r\nSUMMARY:Ultima sexta")
    assert dias(janela(ultima, "2026-10-01T00:00", "2027-03-01T00:00")) == ["2026-10-30 10:00", "2026-11-27 10:00", "2026-12-25 10:00"]
    trinta_e_um = cal("UID:2\r\nDTSTART:20261031T130000Z\r\nRRULE:FREQ=MONTHLY;COUNT=3\r\nSUMMARY:Dia 31")
    assert dias(janela(trinta_e_um, "2026-10-01T00:00", "2027-06-01T00:00")) == ["2026-10-31 10:00", "2026-12-31 10:00", "2027-01-31 10:00"]


def test_mensal_primeira_segunda_e_bymonthday_negativo():
    texto = cal("UID:1\r\nDTSTART:20261005T130000Z\r\nRRULE:FREQ=MONTHLY;BYDAY=1MO\r\nSUMMARY:Primeira segunda",
                "UID:2\r\nDTSTART:20261031T130000Z\r\nRRULE:FREQ=MONTHLY;BYMONTHDAY=-1\r\nSUMMARY:Fim do mes")
    achadas = janela(texto, "2026-11-01T00:00", "2026-12-31T00:00")
    assert dias([o for o in achadas if o.titulo == "Primeira segunda"]) == ["2026-11-02 10:00", "2026-12-07 10:00"]
    assert dias([o for o in achadas if o.titulo == "Fim do mes"]) == ["2026-11-30 10:00"]


def test_anual_29_de_fevereiro_so_em_ano_bissexto():
    texto = cal("UID:1\r\nDTSTART;VALUE=DATE:20240229\r\nRRULE:FREQ=YEARLY\r\nSUMMARY:Bissexto")
    anos = [o.inicio.year for o in janela(texto, "2024-01-01T00:00", "2033-01-01T00:00")]
    assert anos == [2024, 2028, 2032]


def test_anual_com_bymonth():
    texto = cal("UID:1\r\nDTSTART:20260315T130000Z\r\nRRULE:FREQ=YEARLY;BYMONTH=3,9;BYMONTHDAY=15\r\nSUMMARY:Duas vezes")
    assert dias(janela(texto, "2026-01-01T00:00", "2027-12-31T00:00")) == [
        "2026-03-15 10:00", "2026-09-15 10:00", "2027-03-15 10:00", "2027-09-15 10:00"]


def test_recurrence_id_substitui_a_ocorrencia_e_cancelada_some():
    texto = cal("UID:a\r\nDTSTART:20261020T130000Z\r\nRRULE:FREQ=DAILY;COUNT=3\r\nSUMMARY:Serie",
                "UID:a\r\nRECURRENCE-ID:20261021T130000Z\r\nDTSTART:20261021T170000Z\r\nSUMMARY:Serie (movida)",
                "UID:a\r\nRECURRENCE-ID:20261022T130000Z\r\nDTSTART:20261022T130000Z\r\nSTATUS:CANCELLED\r\nSUMMARY:Serie")
    achadas = janela(texto, "2026-10-20T00:00", "2026-10-25T00:00")
    assert [(o.titulo, o.inicio.strftime("%d %H:%M")) for o in achadas] == [("Serie", "20 10:00"), ("Serie (movida)", "21 14:00")]


def test_alarme_dentro_do_evento_nao_vaza_propriedades():
    texto = cal("UID:1\r\nDTSTART:20261020T130000Z\r\nSUMMARY:Real\r\nBEGIN:VALARM\r\nACTION:DISPLAY\r\nSUMMARY:Falso\r\nDESCRIPTION:x\r\nEND:VALARM")
    [e] = ics.ler(texto)
    assert e.titulo == "Real"


def test_evento_malformado_nao_derruba_os_outros():
    texto = cal("UID:1\r\nSUMMARY:Sem data", "UID:2\r\nDTSTART:lixo\r\nSUMMARY:Data ruim",
                "UID:3\r\nDTSTART:20261020T130000Z\r\nRRULE:FREQ=SECONDLY\r\nSUMMARY:Regra nao suportada",
                "UID:4\r\nDTSTART:20261020T130000Z\r\nRRULE:FREQ=WEEKLY;BYDAY=XX\r\nSUMMARY:Regra quebrada")
    assert [e.titulo for e in ics.ler(texto)] == ["Regra nao suportada", "Regra quebrada"]
    assert len(janela(texto, "2026-10-20T00:00", "2026-10-21T00:00")) == 2  # vira evento único


def test_parametro_com_aspas_e_duracao():
    texto = cal('UID:1\r\nDTSTART;TZID="America/Sao_Paulo":20261020T090000\r\nDURATION:PT1H30M\r\nSUMMARY:Aspas: com dois pontos')
    [e] = ics.ler(texto)
    assert e.titulo == "Aspas: com dois pontos" and e.fim - e.inicio == timedelta(minutes=90)


def test_serie_antiga_nao_percorre_anos_a_toa():
    texto = cal("UID:1\r\nDTSTART:20100104T130000Z\r\nRRULE:FREQ=DAILY\r\nSUMMARY:Antiga")
    assert dias(janela(texto, "2026-10-20T00:00", "2026-10-22T00:00")) == ["2026-10-20 10:00", "2026-10-21 10:00"]
