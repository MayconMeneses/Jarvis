"""Iniciativa própria: cada aviso aparece uma vez no período certo, respeita o silêncio e não derruba nada."""

import subprocess
from datetime import datetime

import pytest

from jarvis import memory_db
from jarvis.config import Config
from jarvis.proativo import LEITURAS_RAM, projetos_sem_commit
from jarvis.proativo.agendador import Agendador


def agendador(cfg, relogio, ram=lambda: 10, **kw):
    entregues = []
    ag = Agendador(lambda: cfg, memory_db.open_memory(cfg), lambda aviso, falar: entregues.append((aviso, falar)), ram,
                   agora=lambda: relogio["t"], **kw)
    return ag, entregues


@pytest.fixture
def relogio():
    return {"t": datetime(2026, 10, 19, 8, 30)}  # segunda-feira, 8h30


BRIEF = lambda: {"text": "Bom dia! Hoje faz sol.", "speak": "Bom dia!"}  # noqa: E731


def test_good_morning_comes_once_a_day_only_after_the_set_hour(relogio):
    cfg = Config(proativo_hora=8)
    ag, saiu = agendador(cfg, relogio, briefing=BRIEF)
    relogio["t"] = datetime(2026, 10, 19, 7, 0)
    assert ag.tick() == []
    relogio["t"] = datetime(2026, 10, 19, 8, 30)
    assert [a.chave for a in ag.tick()] == ["bomdia:2026-10-19"] and ag.tick() == []  # só uma vez
    relogio["t"] = datetime(2026, 10, 20, 8, 30)
    assert len(ag.tick()) == 1  # no dia seguinte volta
    relogio["t"] = datetime(2026, 10, 20, 13, 0)
    ag2, _ = agendador(Config(), relogio, briefing=BRIEF)
    assert ag2.tick() == []  # depois do meio-dia não faz sentido


def test_warm_greeting_already_given_suppresses_the_morning_notice(relogio):
    cfg = Config()
    ag, saiu = agendador(cfg, relogio, briefing=BRIEF)
    memory_db.open_memory(cfg).set_meta("proativo:bomdia:2026-10-19", "saudacao")
    assert ag.tick() == [] and saiu == []


def test_weekly_training_on_monday_only(relogio):
    ag, _ = agendador(Config(), relogio, treino=lambda: "Treino: testes")
    relogio["t"] = datetime(2026, 10, 19, 10, 0)
    assert [a.chave for a in ag.tick()] == ["treino:2026-43"] and ag.tick() == []
    relogio["t"] = datetime(2026, 10, 21, 10, 0)  # quarta
    assert ag.tick() == []


def test_high_memory_needs_several_readings_in_a_row(relogio):
    leituras = iter([95, 95, 40, 95, 95, 95, 95])
    ag, _ = agendador(Config(), relogio, ram=lambda: next(leituras))
    achados = [ag.tick() for _ in range(LEITURAS_RAM + 3)]
    assert achados[0] == achados[1] == achados[2] == []  # 95, 95, 40: a sequência quebrou
    assert any("95%" in a.texto for lote in achados for a in lote)
    assert sum(len(lote) for lote in achados) == 1  # e não repete na mesma janela de 3 horas


def test_voice_only_when_enabled_and_never_at_night(relogio):
    ag, saiu = agendador(Config(proativo_voz=True), relogio, briefing=BRIEF)
    ag.tick()
    assert saiu[0][1] is True
    assert ag.pode_falar(Config(proativo_voz=True), datetime(2026, 10, 19, 23, 0)) is False
    assert ag.pode_falar(Config(proativo_voz=True), datetime(2026, 10, 19, 6, 0)) is False
    assert ag.pode_falar(Config(proativo_voz=False), datetime(2026, 10, 19, 12, 0)) is False


def test_switch_off_and_failing_rules_do_not_break_anything(relogio):
    ag, saiu = agendador(Config(proativo=False), relogio, briefing=BRIEF)
    assert ag.tick() == []

    def quebrado():
        raise RuntimeError("sem rede")

    relogio["t"] = datetime(2026, 10, 19, 10, 0)
    ag, saiu = agendador(Config(), relogio, briefing=quebrado, treino=lambda: "Treino")
    assert [a.chave.split(":")[0] for a in ag.tick()] == ["treino"]  # a regra do bom dia falhou, as outras seguiram


def test_idle_projects_are_found_by_the_last_commit(tmp_path):
    def repo(nome, data):
        pasta = tmp_path / nome
        pasta.mkdir()
        env = {"GIT_AUTHOR_DATE": data, "GIT_COMMITTER_DATE": data, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "PATH": __import__("os").environ["PATH"]}
        for cmd in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "x"]):
            subprocess.run(["git", *cmd], cwd=pasta, check=True, capture_output=True, env=env)
        return str(pasta)

    velho, novo = repo("velho", "2026-01-01T10:00:00"), repo("novo", "2026-10-18T10:00:00")
    agora = datetime(2026, 10, 19).timestamp()
    achados = projetos_sem_commit({"Velho": velho, "Novo": novo, "SemGit": str(tmp_path)}, agora=agora)
    assert [n for n, _ in achados] == ["Velho"] and achados[0][1] > 200
