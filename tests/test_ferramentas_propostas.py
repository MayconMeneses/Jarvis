"""Propostas do cinto: criam só um cartão pendente; a execução acontece apenas no Aprovar e revalida tudo. Também as ferramentas de consulta."""

from datetime import datetime, timedelta

import pytest

from jarvis import memory_db
from jarvis.llm import ferramentas_cinto, ferramentas_dados, ferramentas_propostas as fp
from jarvis.pc import actions, launcher
from jarvis.proativo import Contexto
from jarvis.proativo.lembretes import lembretes_vencidos


def amanha(horas=24):
    return (datetime.now() + timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M")


@pytest.fixture
def sem_execucao(monkeypatch):
    abertos = []
    monkeypatch.setattr(launcher, "app_index", lambda: {"Calculadora": "app.id"})
    monkeypatch.setattr(launcher, "open_app", lambda nome, *a, **k: abertos.append(nome) or f"{nome} aberto.")
    return abertos


def pendentes():
    return actions.ActionStore().pending_since(0)


def test_proposing_an_app_creates_a_card_and_opens_nothing(sem_execucao):
    cinto = ferramentas_cinto.padrao()
    r = cinto.chamar("propor_abrir_app", {"nome": "calculadora"})
    assert r.ok and "NÃO diga que já foi aberto" in r.texto and sem_execucao == []
    (cartao,) = pendentes()
    assert cartao.kind == "abrir_app" and cartao.params == {"nome": "Calculadora"} and cartao.status == "pendente"


def test_unknown_app_is_refused_without_a_card(sem_execucao):
    assert not ferramentas_cinto.padrao().chamar("propor_abrir_app", {"nome": "programa-que-nao-existe-xyz"}).ok
    assert pendentes() == []


def test_approving_the_card_opens_the_app_and_declining_does_not(sem_execucao):
    ferramentas_cinto.padrao().chamar("propor_abrir_app", {"nome": "calculadora"})
    loja = actions.ActionStore()
    cartao = pendentes()[0]
    assert actions.decide(loja, cartao.id, approve=False).status == "recusada" and sem_execucao == []
    ferramentas_cinto.padrao().chamar("propor_abrir_app", {"nome": "calculadora"})
    novo = [a for a in pendentes() if a.status == "pendente"][0]
    assert actions.decide(loja, novo.id, approve=True).resultado == "Calculadora aberto." and sem_execucao == ["Calculadora"]


def test_reminder_validation_and_card():
    cinto = ferramentas_cinto.padrao()
    for args in ({"texto": "x", "quando": "ontem"}, {"texto": "x", "quando": "2020-01-01 10:00"}, {"texto": "", "quando": amanha()},
                 {"texto": "x" * 200, "quando": amanha()}, {"texto": "x", "quando": amanha(24 * 400)}, {"texto": "x", "quando": "2026-13-45 99:99"}):
        assert not cinto.chamar("propor_lembrete", args).ok, args
    assert pendentes() == [] and fp.ler_lembretes() == []
    assert cinto.chamar("propor_lembrete", {"texto": "ligar para o dentista", "quando": amanha()}).ok
    assert [a.kind for a in pendentes()] == ["criar_lembrete"] and fp.ler_lembretes() == []  # nada criado antes do Aprovar


def test_approved_reminder_is_stored_revalidated_and_fires_once_due():
    ferramentas_cinto.padrao().chamar("propor_lembrete", {"texto": "tomar água", "quando": amanha(1)})
    cartao = pendentes()[0]
    assert actions.decide(actions.ActionStore(), cartao.id, approve=True).status == "executada"
    (lembrete,) = fp.ler_lembretes()
    assert lembrete["texto"] == "tomar água"
    depois = datetime.now() + timedelta(hours=2)
    aviso = lembretes_vencidos(Contexto(depois, None))
    assert aviso and "tomar água" in aviso.texto and aviso.voz and aviso.chave == f"lembrete:{lembrete['id']}"
    assert lembretes_vencidos(Contexto(datetime.now(), None)) is None  # ainda não chegou a hora
    assert lembretes_vencidos(Contexto(datetime.now() + timedelta(days=5), None)) is None  # muito antigo: não fala


def test_tampered_card_is_revalidated_on_approval():
    cartao = actions.ActionStore().save(actions.Action("criar_lembrete", {"texto": "x" * 500, "quando": amanha()}, "d", "m"))
    assert actions.decide(actions.ActionStore(), cartao.id, approve=True).status == "falhou"
    ruim = actions.ActionStore().save(actions.Action("criar_lembrete", {"texto": "ok", "quando": "2001-01-01 10:00"}, "d", "m"))
    assert actions.decide(actions.ActionStore(), ruim.id, approve=True).status == "falhou"


def test_memory_proposal_goes_through_the_existing_card_and_warns_after_third_party_content(monkeypatch):
    cinto = ferramentas_cinto.padrao()
    cinto.terceiros_lidos = True
    assert cinto.chamar("propor_memoria", {"area": "metas", "titulo": "Meta de leitura", "fato": "Ler 12 livros em 2027."}).ok
    (cartao,) = pendentes()
    assert cartao.kind == "guardar_memoria" and "conteúdo de" in cartao.descricao
    assert not cinto.chamar("propor_memoria", {"area": "inventada", "titulo": "x", "fato": "y"}).ok
    assert len(pendentes()) == 1


def test_consultation_tools_use_the_existing_services(monkeypatch):
    monkeypatch.setattr("jarvis.info.news.por_assunto", lambda a, n: {"manchetes": [{"titulo": "T", "fonte": "F", "link": "https://x.y/1"}], "avisos": []})
    assert "- T (F) https://x.y/1" in ferramentas_dados.noticias("ia", 3)
    monkeypatch.setattr("jarvis.info.news.por_assunto", lambda a, n: {"manchetes": [], "avisos": ["fora do ar"]})
    with pytest.raises(RuntimeError):
        ferramentas_dados.noticias("ia", 3)
    assert "bateria" in ferramentas_dados.estado_do_pc() or "CPU" in ferramentas_dados.estado_do_pc()
    with pytest.raises(ValueError):
        ferramentas_dados.clima("")  # cidade do usuário não configurada
    with pytest.raises(ValueError):
        ferramentas_dados.conhecimento("assunto-que-nao-existe-qqq")
    assert ferramentas_dados.buscar_notas("nada-por-aqui-zzz") == "Nenhuma nota encontrada sobre isso."


def test_notes_search_reads_memory_and_is_filtered_like_third_party_text(monkeypatch):
    from jarvis import config

    memory_db.open_memory(config.load()).put("Notas/exemplo", "O projeto Zeta usa Python e SQLite.", "nota", "Zeta")
    assert "Zeta" in ferramentas_dados.buscar_notas("Zeta")
    assert next(f for f in ferramentas_dados.FERRAMENTAS if f.nome == "buscar_notas").externo is True  # notas podem guardar texto colado de e-mail ou site: passam pelo filtro de ordens
