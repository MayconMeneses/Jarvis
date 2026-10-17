"""Aprendizado autônomo: descobre os assuntos mais perguntados, estuda sozinha só com o PC parado e dentro de limites."""

from datetime import datetime

import pytest

from jarvis import config, memory_db
from jarvis.autonomo import estudar, interesses
from jarvis.autonomo.agendador import Autonomo
from jarvis.config import Config
from jarvis.dev import conhecimento, saber
from jarvis.local.engine import LocalEngine
from jarvis.local.websearch import Result

HOJE = datetime(2026, 10, 19, 14, 0)  # segunda-feira


def cita(texto):
    return [i for _, i in saber.citados(texto)] + list(conhecimento.mentioned(texto))


def memoria(tmp_path, pedidos, dia="2026-10-19"):
    mem = memory_db.open_memory(Config(memoria_db=str(tmp_path / "m.db")))
    for hora, texto in enumerate(pedidos):
        mem.diary(f"Pedido: {texto}")
    # o diário usa a data real; copia o corpo para o dia simulado
    real = f"Diário/{datetime.now():%Y-%m-%d}"
    corpo = mem.get(real) or ""
    mem.put(f"Diário/{dia}", corpo, "diario")
    if real != f"Diário/{dia}":
        mem.delete(real)  # só o dia simulado fica no diário
    return mem


PEDIDOS = ["o que é kubernetes", "explique kubernetes para iniciantes", "como usar kubernetes", "o que é SOLID", "explique SOLID",
           "me explica SOLID", "explique o padrão Observer", "que horas são", "o que é isso", "explique zig"]


def test_counts_known_and_unknown_subjects_from_the_diary(tmp_path):
    mem = memoria(tmp_path, PEDIDOS)
    pedidos = interesses.pedidos_recentes(mem, hoje=HOJE.date())
    assert len(pedidos) == len(PEDIDOS)
    assuntos = {a.nome: a for a in interesses.contar(pedidos, cita)}
    kube = next(a for n, a in assuntos.items() if "Kubernetes" in n)
    assert kube.mencoes == 3 and kube.conhecido  # já está na base curada
    solid = next(a for a in assuntos.values() if "SOLID" in a.nome)
    assert solid.mencoes == 3 and solid.conhecido
    assert "zig" in assuntos and assuntos["zig"].mencoes == 1 and "isso" not in assuntos and "que horas são" not in assuntos


def test_only_frequent_and_not_recently_studied_subjects_are_chosen(tmp_path):
    mem = memoria(tmp_path, ["o que é quasares", "explique quasares", "como usar quasares", "o que é ferrofluido", "explique zig"])
    assuntos = interesses.contar(interesses.pedidos_recentes(mem, hoje=HOJE.date()), cita)
    escolhidos = estudar.escolher(mem, assuntos, HOJE)
    assert [a.nome for a in escolhidos] == ["quasares"]  # 3 menções; "ferrofluido" (1) e "zig" (1) ficam de fora
    mem.set_meta("autonomo:estudado:quasares", HOJE.isoformat())
    assert estudar.escolher(mem, assuntos, HOJE) == []  # estudado há pouco: não repete
    assert [a.nome for a in estudar.escolher(mem, assuntos, datetime(2026, 11, 20))] == ["quasares"]  # passado o prazo, volta


def achado(vazio=False):
    return {"fontes": [] if vazio else [Result("Quasares", "https://quasares.dev")], "lidos": 1, "resumo": [("Quasares compila componentes.", 1)], "trechos": []}


def pesquisador(vazio=False, falha=False):
    def pesquisar(consulta, n, brave_key=None):
        pesquisar.consultas.append(consulta)
        if falha:
            raise OSError("sem internet")
        return achado(vazio)
    pesquisar.consultas = []
    return pesquisar


def formatar(consulta, resultado):
    return f"Resumo de {consulta}: " + " ".join(f for f, _ in resultado["resumo"])


def autonomo(tmp_path, pedidos, pesquisa, *, cfg=None, parado=True, carga=(10.0, 40.0), agora=HOJE, entregues=None, semana=None):
    mem = memoria(tmp_path, pedidos)
    cfg = cfg or Config(autonomo=True)
    return Autonomo(lambda: cfg, mem, (entregues if entregues is not None else []).append, pesquisa, formatar, cita,
                    ultimo_pedido=lambda: 0.0 if parado else __import__("time").time(), agora=lambda: agora, carga=lambda: carga,
                    avaliar_semana=semana), mem


def test_it_is_off_by_default_and_never_studies_while_the_user_is_busy_or_the_pc_is_loaded(tmp_path):
    p = pesquisador()
    pedidos = ["o que é quasares"] * 3
    assert config.Config().autonomo is False
    assert autonomo(tmp_path, pedidos, p, cfg=Config(autonomo=False))[0].tick() == [] and p.consultas == []
    assert autonomo(tmp_path, pedidos, p, parado=False)[0].tick() == []  # o usuário acabou de pedir algo
    assert autonomo(tmp_path, pedidos, p, carga=(95.0, 40.0))[0].tick() == []  # CPU alta
    assert autonomo(tmp_path, pedidos, p, carga=(10.0, 97.0))[0].tick() == [] and p.consultas == []  # memória cheia


def test_studies_one_subject_saves_a_reviewable_note_and_tells_the_user(tmp_path):
    p, entregues = pesquisador(), []
    ag, mem = autonomo(tmp_path, ["o que é quasares", "explique quasares", "como usar quasares"], p, entregues=entregues)
    criadas = ag.tick()
    assert criadas == ["Aprendizado/Autônomo/quasares"] and p.consultas == ["quasares"]
    nota = mem.get(criadas[0])
    assert "não foi verificado" in nota and "3 vezes" in nota and "Quasares compila componentes" in nota
    assert entregues and "quasares" in entregues[0] and "o que você aprendeu" in entregues[0]
    assert "quasares" in estudar.resumo(mem, marcar_visto=False) and "não verificado" in estudar.resumo(mem)
    assert "Ainda não estudei nada novo" in estudar.resumo(mem)  # depois de visto, não repete a novidade


def test_known_subjects_are_enriched_with_best_practices_and_the_daily_limit_holds(tmp_path):
    p = pesquisador()
    ag, mem = autonomo(tmp_path, ["explique SOLID", "o que é SOLID", "me explica SOLID", "o que é quasares", "explique quasares"], p, cfg=Config(autonomo=True, autonomo_max_por_dia=1))
    assert len(ag.tick()) == 1 and p.consultas[0] == "quasares"
    assert ag.tick() == [] and len(p.consultas) == 1  # limite de 1 por dia


def test_failures_do_not_loop_and_empty_results_are_not_saved(tmp_path):
    p = pesquisador(falha=True)
    ag, mem = autonomo(tmp_path, ["o que é quasares"] * 3, p)
    assert ag.tick() == [] and len(p.consultas) == 1
    assert ag.tick() == [] and len(p.consultas) == 1  # sem internet: só tenta de novo depois do prazo
    vazio = pesquisador(vazio=True)
    ag2, mem2 = autonomo(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path, ["o que é quasares"] * 3, vazio)
    assert ag2.tick() == [] and mem2.get("Aprendizado/Autônomo/quasares") is None


def test_weekly_self_evaluation_runs_once_on_sunday_when_idle(tmp_path):
    entregues, chamadas = [], []
    domingo = datetime(2026, 10, 18, 3, 0)
    ag, mem = autonomo(tmp_path, [], pesquisador(), agora=domingo, entregues=entregues, semana=lambda: chamadas.append(1) or "Nota do cérebro local: 83/100.")
    ag.tick()
    ag.tick()
    assert len(chamadas) == 1 and entregues == ["🧪 Nota do cérebro local: 83/100."]
    segunda, _ = autonomo(tmp_path / "y" if (tmp_path / "y").mkdir() is None else tmp_path, [], pesquisador(), agora=HOJE, semana=lambda: chamadas.append(1) or "x")
    segunda.tick()
    assert len(chamadas) == 1  # só aos domingos


def test_commands_in_the_engine_and_the_window_switch(tmp_path):
    config.save(Config())
    motor = LocalEngine()
    assert motor.classify("o que você aprendeu")[0] == "llm_status" and motor.classify("ligar aprendizado automático")[0] == "llm_status"
    assert "Ainda não estudei" in motor.handle("o que você aprendeu")
    assert "Ligado" in motor.handle("aprenda sozinha") and config.load().autonomo is True
    assert "Desligado" in motor.handle("desligar aprendizado automático") and config.load().autonomo is False

    from jarvis.ui.api_brains import BrainsMixin

    class Ponte(BrainsMixin):
        def _diary(self, t):
            pass

    assert Ponte().set_autonomo(True)["ligado"] is True and Ponte().brains_status()["autonomo"] is True
    assert Ponte().set_autonomo(False)["ligado"] is False
