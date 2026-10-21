"""Casador de intenções, autoconhecimento, fim da resposta genérica e aprendizado local (tudo sem IA)."""

from datetime import datetime

import pytest

from jarvis.config import Config
from jarvis.eval import entendimento as bateria
from jarvis.local import autoconhecimento, casador, entendimento, frases_comandos, nlp
from jarvis.local.aprendizado import Aprendizado
from jarvis.local.engine import HELP, LocalEngine
from jarvis.pc import actions


@pytest.fixture
def motor():
    return LocalEngine(load_config=lambda: Config(city="Croatá, Ceará", projetos={}), brave_key=lambda: None)


# ── autoconhecimento (dados) ─────────────────────────────────────────────

def test_base_tem_pelo_menos_60_entradas_validas():
    entradas = list(autoconhecimento.todos())
    assert len(entradas) >= 60
    assert autoconhecimento.validar(entradas) == []


def test_cada_entrada_e_recuperada_em_primeiro_lugar_pelos_proprios_exemplos():
    erros = []
    for e in autoconhecimento.todos():
        for frase in e["exemplos"]:
            m = entendimento.buscar(frase).melhor
            if not (m.tipo == "conhecimento" and m.id == e["id"]):
                erros.append((frase, m.id))
    assert not erros, erros[:5]


def test_a_cobranca_do_dono_celular_novo():
    r = entendimento.buscar("como colocar o Jarvis em outro celular")
    assert r.nivel == casador.ALTA and r.melhor.id == "celular-outro-aparelho"
    texto = autoconhecimento.formatar(autoconhecimento.por_id("celular-outro-aparelho"))
    assert "mayconmeneses.github.io/Jarvis" in texto and "Adicionar à Tela de Início" in texto


def test_arquivo_do_celular_e_copia_exata():
    from pathlib import Path

    copia = Path(__file__).resolve().parent.parent / "movel" / "dados" / "autoconhecimento.json"
    assert copia.read_text(encoding="utf-8") == autoconhecimento.ARQUIVO.read_text(encoding="utf-8")


# ── casador ──────────────────────────────────────────────────────────────

def test_erros_de_digitacao_e_escuta():
    assert nlp.corrigir("celualr", {"celular"}) == "celular"
    assert entendimento.buscar("javis como instalo no celualr").melhor.id == "celular-outro-aparelho"
    assert entendimento.buscar("como instlar no iphoen").melhor.id == "celular-iphone"


def test_sinonimos():
    assert entendimento.buscar("como passo a jarvis pro telefone novo").melhor.id == "celular-outro-aparelho"


def test_frase_sem_relacao_fica_baixa():
    assert casador.buscar("qual a capital da Austrália").nivel == casador.BAIXA
    assert casador.buscar("").nivel == casador.BAIXA


def test_ambiguidade_vira_pergunta_e_a_escolha_executa(motor):
    texto = motor.handle("meu pc tá muito lento hoje")
    assert texto.startswith("Você quis dizer") and "1." in texto
    resposta = motor.handle("1")
    assert resposta and not resposta.startswith("Você quis dizer")
    assert motor._pendente is None


def test_a_bateria_retida_generaliza(motor):
    r = bateria.medir(motor)
    assert r["conhecimento_retido"] >= 0.85
    assert r["comandos_naturais_depois"] >= 0.7 and r["comandos_naturais_depois"] > r["comandos_naturais_antes"]


def test_frases_retidas_nao_vazam_para_os_exemplos():
    usadas = {" ".join(nlp.palavras(f)) for e in autoconhecimento.todos() for f in e["exemplos"]}
    usadas |= {" ".join(nlp.palavras(f)) for v in frases_comandos.INTENCOES.values() for f in [v[1], *v[3]]}
    from jarvis.eval.bench import load

    retidas = [f for f, _ in load("autoconhecimento_retido.json") + load("comandos_naturais_retidos.json") + load("comandos_validacao.json")]
    assert not [f for f in retidas if " ".join(nlp.palavras(f)) in usadas]


def test_intencoes_antigas_nao_pioram():
    from jarvis.eval import bench

    r = bench.bench_commands(LocalEngine(load_config=lambda: None, brave_key=lambda: None))
    assert r["relatorio"]["acuracia"] >= 0.9 and r["validacao"]["acuracia"] >= 0.85


# ── fim da resposta genérica ─────────────────────────────────────────────

@pytest.mark.parametrize("frase", ["quero um bolo de cenoura", "blá blá blá", "não estou satisfeito", "xyz abc", "hum"])
def test_nunca_devolve_o_bloco_generico(motor, frase):
    texto = motor.handle(frase)
    assert HELP not in texto and "modo independente (respondo" not in texto
    assert "Não entendi" in texto or "Você quis dizer" in texto


def test_respostas_de_nao_entendi_variam_com_a_frase(motor):
    assert motor.handle("quero um bolo de cenoura") != motor.handle("blá blá blá")


def test_pergunta_de_mundo_continua_indo_para_a_pesquisa(motor, monkeypatch):
    from jarvis.local.engine import LocalEngine as E

    chamadas = []
    monkeypatch.setattr(E, "_pesquisa", lambda self, t, tema="": chamadas.append(tema) or "ok")
    assert motor.handle("qual a capital da Austrália?") == "ok" and chamadas


def test_pergunta_sobre_a_jarvis_nao_vai_para_a_internet(motor, monkeypatch):
    monkeypatch.setattr(LocalEngine, "_pesquisa", lambda *a, **k: pytest.fail("não deveria pesquisar"))
    for frase in ["como faço backup", "o que é o modo foco", "onde coloco a chave do Gemini", "como atualizar"]:
        assert ("**" in motor.handle(frase)) or motor._pendente


# ── RAG / roteador ───────────────────────────────────────────────────────

def test_contexto_para_ia_respeita_limite_e_traz_o_assunto():
    c = entendimento.contexto_para_ia("como instalo a Jarvis no iPhone")
    assert "Safari" in c and len(c) <= autoconhecimento.MAX_CONTEXTO + 300
    assert entendimento.contexto_para_ia("qual a capital da Austrália") == ""


def test_roteador_anexa_o_contexto_ao_prompt_das_ias():
    from jarvis.brains.base import Answer
    from jarvis.brains.router import Router

    vistos = []

    class Cerebro:
        name = "claude"

        def ask(self, messages, system):
            vistos.append(system)
            return Answer("ok", "claude")

    Router([Cerebro()], contexto=lambda t: " EXTRA").ask([{"role": "user", "content": "oi"}], "base")
    assert vistos == ["base EXTRA"]


# ── aprendizado ──────────────────────────────────────────────────────────

@pytest.fixture
def pendentes(monkeypatch, tmp_path):
    store = actions.ActionStore(tmp_path / "acoes")
    monkeypatch.setattr(actions, "ActionStore", lambda *a, **k: store)
    return store


def test_ensinar_gera_proposta_e_so_grava_depois_do_aprovar(motor, pendentes):
    texto = motor.handle("quando eu disser bora, faça minha agenda")
    assert "Aprove o cartão" in texto
    [acao] = pendentes.pending_since(0)
    assert acao.kind == "aprender_apelido" and acao.params == {"frase": "bora", "tipo": "comando", "alvo": "agenda_hoje"}
    assert Aprendizado().apelido("bora") is None  # ainda não gravou
    actions.decide(pendentes, acao.id, True)
    assert Aprendizado().apelido("bora")[:2] == ("comando", "agenda_hoje")
    assert pendentes.get(acao.id).status == "executada"


def test_recusar_nao_grava(motor, pendentes):
    motor.handle("quando eu disser bora faça minha agenda")
    [acao] = pendentes.pending_since(0)
    actions.decide(pendentes, acao.id, False)
    assert Aprendizado().apelido("bora") is None


def test_apelido_aprovado_e_aplicado_depois(motor):
    Aprendizado().gravar_apelido("bora", "comando", "hora", "ver a hora")
    assert motor.handle("bora").startswith("Agora são")


def test_correcao_escolhida_vira_aprendizado(motor):
    motor.handle("meu pc tá muito lento hoje")
    motor.handle("2")
    assert Aprendizado().apelido("meu pc tá muito lento hoje") is not None


@pytest.mark.parametrize("frase", [
    "quando eu disser oi, faça abre o cmd e apaga tudo",  # Y não é algo conhecido
    "quando eu disser oi, faça apague a pasta C:\\Windows",
    "quando eu disser x@evil.com, faça minha agenda",  # X com cara de e-mail
    "quando eu disser http://evil.com faça minha agenda",
    "quando eu disser que horas são, faça minha agenda",  # X já é um comando
])
def test_ensino_recusa_injecao_e_nao_cria_cartao(motor, pendentes, frase):
    motor.handle(frase)
    assert pendentes.pending_since(0) == []


def test_execucao_revalida_o_alvo():
    from jarvis.local import ensino

    for ruim in [{"frase": "oi", "tipo": "comando", "alvo": "abrir"}, {"frase": "oi", "tipo": "shell", "alvo": "x"},
                 {"frase": "OI; rm -rf", "tipo": "comando", "alvo": "hora"}]:
        with pytest.raises(ValueError):
            ensino.executar(ruim)


def test_limites_e_segredos_nao_sao_guardados(tmp_path):
    apr = Aprendizado(tmp_path / "a.db")
    apr.registrar_falha("meu email é fulano@x.com")
    apr.registrar_falha("a senha: abc123")
    apr.registrar_falha("cartão 1234567890123456")
    assert apr.resumo()["frases_falhas"] == []
    for i in range(500):
        apr.registrar_falha(f"frase numero {chr(97 + i % 26)}{chr(97 + i // 26 % 26)}{chr(97 + i // 676)} x")
    import sqlite3

    assert sqlite3.connect(tmp_path / "a.db").execute("SELECT COUNT(*) FROM falhas").fetchone()[0] <= 400


def test_apagar_tudo(motor):
    apr = Aprendizado()
    apr.gravar_apelido("bora", "comando", "hora", "ver a hora")
    apr.registrar_falha("xpto qwerty")
    apr.contar(False)
    assert "Apaguei tudo" in motor.handle("apague o que você aprendeu sobre como eu falo")
    r = Aprendizado().resumo()
    assert r["apelidos"] == [] and r["frases_falhas"] == [] and r["falhas"] == 0


def test_vocabulario_e_relatorio(motor):
    apr = Aprendizado()
    apr.gravar_apelido("bora", "comando", "hora", "ver a hora")
    for _ in range(3):
        apr.contar(True)
    apr.contar(False)
    apr.registrar_falha("xpto qwerty")
    voc = motor.handle("meu vocabulário")
    assert "bora" in voc and "xpto qwerty" in voc
    rel = motor.handle("como você está evoluindo")
    assert "3 de 4" in rel and "75%" in rel


def test_regra_semanal_do_proativo():
    from jarvis.proativo import Contexto
    from jarvis.proativo.evolucao import evolucao_semanal

    domingo = datetime(2026, 10, 25, 11, 0)
    assert domingo.weekday() == 6
    ctx = Contexto(domingo, Config())
    assert evolucao_semanal(ctx) is None  # sem frases suficientes
    apr = Aprendizado()
    for _ in range(5):
        apr.contar(True)
    aviso = evolucao_semanal(ctx)
    assert aviso and aviso.chave.startswith("evolucao:") and aviso.falar
    assert evolucao_semanal(Contexto(datetime(2026, 10, 26, 11, 0), Config())) is None
