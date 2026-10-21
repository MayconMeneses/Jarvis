import types
from datetime import datetime

import numpy as np
import pytest

from jarvis.config import Config
from jarvis.memory_db import MemoryDB
from jarvis.radar import narrar, reproduzir
from jarvis.radar.agendador import RadarAgendador, hora_de
from jarvis.radar.ajustes import RadarConfig

TERCA = datetime(2026, 10, 20, 7, 5)  # terça-feira
SABADO = datetime(2026, 10, 24, 9, 0)


@pytest.fixture
def mem(tmp_path):
    return MemoryDB(tmp_path / "memoria.db")


def cfg_com(**kw):
    c = Config()
    c.radar = RadarConfig(ativo=True, nicho="economia", **kw)
    return c


class Fake:
    def __init__(self, resultados):
        self.resultados, self.chamadas, self.avisos = list(resultados), [], []

    def rodar(self, radar_cfg, hist, mem, agora, progresso=None, atrasado=False, avisos_iniciais=None, melhorar=None):
        self.chamadas.append({"atrasado": atrasado, "avisos": avisos_iniciais})
        return self.resultados.pop(0)


def historico_falso():
    return types.SimpleNamespace(fechar=lambda: None)


def agendador(mem, cfg, fake, agora, entregues=None):
    entregues = entregues if entregues is not None else []
    return RadarAgendador(lambda: cfg, mem, entregues.append, fake.rodar, historico_falso, lambda: agora), entregues


OK = {"ok": True, "itens": 7, "duracao_s": 312.0, "audio": "x.wav"}
FALHA = {"ok": False, "erro": "sem internet"}


def test_hour_parsing_is_forgiving():
    assert hora_de("07:00") == (7, 0) and hora_de("18:45") == (18, 45)
    assert hora_de("25:00") == (7, 0) and hora_de("abc") == (7, 0) and hora_de("") == (7, 0)


def test_runs_once_per_weekday_after_the_hour_and_marks_the_day(mem):
    fake = Fake([OK])
    ag, entregues = agendador(mem, cfg_com(), fake, TERCA)
    assert ag.devido(cfg_com(), datetime(2026, 10, 20, 6, 59)) == (False, False)  # antes da hora
    assert ag.tick() == OK and len(fake.chamadas) == 1 and fake.chamadas[0]["atrasado"] is False
    mem.set_meta("radar:2026-10-20", "1")  # o executar() real grava isto
    assert ag.tick() is None and len(fake.chamadas) == 1  # uma vez por dia
    assert "Radar pronto: 7 notícias, 5.2 min de áudio" in entregues[0] and "ouvir radar" in entregues[0]


def test_weekends_disabled_and_missing_niche_do_not_run(mem):
    fake = Fake([OK, OK])
    ag, _ = agendador(mem, cfg_com(), fake, SABADO)
    assert ag.tick() is None
    ag2, _ = agendador(mem, cfg_com(dias_uteis=False), fake, SABADO)
    assert ag2.tick() == OK  # sábado liberado pelo usuário
    desligado = Config()
    desligado.radar = RadarConfig(ativo=False, nicho="x")
    assert agendador(mem, desligado, fake, TERCA)[0].devido(desligado, TERCA) == (False, False)
    sem_nicho = Config()
    sem_nicho.radar = RadarConfig(ativo=True)
    assert agendador(mem, sem_nicho, fake, TERCA)[0].devido(sem_nicho, TERCA) == (False, False)


def test_late_start_runs_on_next_open_and_is_flagged(mem):
    fake = Fake([OK])
    tarde = datetime(2026, 10, 20, 14, 30)  # o PC estava desligado às 7h
    ag, _ = agendador(mem, cfg_com(), fake, tarde)
    assert ag.devido(cfg_com(), tarde) == (True, True)
    ag.tick()
    assert fake.chamadas[0]["atrasado"] is True


def test_failure_retries_after_30_minutes_and_counts_one_failure_per_day(mem):
    fake = Fake([FALHA, FALHA, FALHA])
    relogio = {"agora": TERCA}
    ag = RadarAgendador(lambda: cfg_com(), mem, lambda t: None, fake.rodar, historico_falso, lambda: relogio["agora"])
    assert ag.tick() == FALHA
    relogio["agora"] = datetime(2026, 10, 20, 7, 20)
    assert ag.tick() is None  # falhou há pouco: espera
    relogio["agora"] = datetime(2026, 10, 20, 7, 40)
    assert ag.tick() == FALHA
    assert mem.meta("radar:falhas_seguidas") == "1"  # duas tentativas no mesmo dia = 1 falha


def test_two_failed_days_in_a_row_put_a_warning_in_the_next_bulletin(mem):
    mem.set_meta("radar:falhas_seguidas", "2")
    fake = Fake([OK])
    ag, _ = agendador(mem, cfg_com(), fake, TERCA)
    ag.tick()
    assert "falhou nos últimos dias" in fake.chamadas[0]["avisos"][0]
    assert mem.meta("radar:falhas_seguidas") == "0"  # sucesso zera a contagem


def test_never_runs_twice_at_the_same_time(mem):
    ag, _ = agendador(mem, cfg_com(), Fake([OK]), TERCA)
    ag._trava.acquire()
    assert "já está rodando" in ag.executar()["erro"]


# ── reproduzir ───────────────────────────────────────────────────────────

def test_play_and_stop_use_the_saved_wav(tmp_path):
    antigo, novo = tmp_path / "2026-10-19", tmp_path / "2026-10-20"
    for pasta in (antigo, novo):
        narrar.gravar_wav(pasta / "boletim.wav", np.zeros(22050 * 2, dtype=np.int16), 22050)
    import os
    os.utime(antigo / "boletim.wav", (1, 1))
    assert reproduzir.ultimo_audio(tmp_path) == novo / "boletim.wav" and reproduzir.ultimo_audio(tmp_path / "nada") is None
    chamadas = []
    sd = types.SimpleNamespace(play=lambda pcm, taxa: chamadas.append(("play", len(pcm), taxa)), stop=lambda: chamadas.append(("stop",)))
    assert reproduzir.tocar(novo / "boletim.wav", sd) == pytest.approx(2.0)
    reproduzir.parar(sd)
    assert chamadas == [("play", 44100, 22050), ("stop",)]
