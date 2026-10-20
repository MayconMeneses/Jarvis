"""Uso de IA ligado ao resto: cérebros, roteador, política, chat, MCP, proativo e ponte da janela."""

import json
import time
from jarvis.brains import claude_cli, policy
from jarvis.brains.base import Answer
from jarvis.brains.claude_session import ClaudeSession
from jarvis.brains.router import Router
from jarvis.config import ClaudeConfig
from jarvis.uso import alertas, configuracao, servico

RESULTADO = {"result": "oi", "is_error": False, "total_cost_usd": 0.42, "modelUsage": {"claude-opus-5-5": {"outputTokens": 9}, "claude-haiku-5-5": {"outputTokens": 1}},
             "usage": {"input_tokens": 3, "output_tokens": 9, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 500}}


def test_claude_cli_leva_usage_e_custo():
    r = claude_cli.parse_output(json.dumps(RESULTADO), "", 0)
    assert r.usage == {"in": 3, "out": 9, "cw": 100, "cw1h": 0, "cr": 500} and r.custo_usd == 0.42 and r.modelo == "claude-opus-5-5"


def test_claude_session_custo_cumulativo_vira_por_turno():
    sessao = ClaudeSession(ClaudeConfig())
    a = sessao._com_uso("a", {**RESULTADO, "total_cost_usd": 1.0})
    b = sessao._com_uso("b", {**RESULTADO, "total_cost_usd": 1.5})
    assert (a.custo_usd, b.custo_usd) == (1.0, 0.5)


def test_roteador_grava_uma_linha_por_resposta_e_nunca_falha():
    class Cerebro:
        name = "claude"

        def ask(self, m, s):
            return Answer("ok", "claude", usage={"in": 1, "out": 2, "cw": 0, "cw1h": 0, "cr": 0}, custo_usd=0.1, modelo="claude-opus-5-5")

    Router([Cerebro()]).ask([{"role": "user", "content": "oi"}], "s")
    linhas = servico.registro().linhas()
    assert len(linhas) == 1 and linhas[0]["custo"] == 0.1 and linhas[0]["estimado"] is False
    servico.registrar_resposta(object())  # resposta estranha: só ignora


def test_politica_economiza_quando_a_cota_aperta_e_aceita_textos_de_transformacao():
    assert policy.preferred("conta uma piada", "reserva") is None
    assert policy.preferred("conta uma piada", "reserva", economizar=True) == "gemini"
    assert policy.preferred("como está meu PC?", "reserva", economizar=True) is None
    texto = "traduz para inglês: " + "bom dia. " * 100
    assert policy.preferred(texto, "simples") == "gemini"
    assert policy.preferred("explique " + "x" * 400, "simples") is None  # texto longo que não é transformação segue com o Claude


def test_cota_sob_pressao_liga_a_politica(monkeypatch):
    reg = servico.registro()
    configuracao.salvar(reg, {"teto_5h": 100})
    reg.inserir(ts=time.time() - 60, fonte="ao_vivo", provedor="claude", modelo="m", uso={"in": 0, "out": 95, "cw": 0, "cw1h": 0, "cr": 0})
    monkeypatch.setitem(servico._pressao, "em", 0.0)
    assert servico.cota_sob_pressao() is True


def test_comando_de_chat_local_sem_ia():
    from jarvis.local.engine import LocalEngine

    motor = LocalEngine()
    for frase in ("quanto gastei este mês?", "cota do claude", "uso de IA hoje"):
        assert motor.classify(frase)[0] == "uso_ia" and motor.is_direct_command(frase)
    assert "Ainda não há uso" in motor.handle("quanto gastei")
    servico.registro().inserir(ts=time.time() - 30, fonte="jsonl", provedor="claude", modelo="claude-opus-5-5", uso={"in": 1, "out": 1000, "cw": 0, "cw1h": 0, "cr": 0}, chave="a|b")
    texto = motor.handle("cota do claude")
    assert "ESTIMATIVA" in texto and "janela de 5 h" in texto
    assert "US$" in motor.handle("quanto gastei hoje")


def test_ferramentas_mcp_somente_leitura():
    from jarvis.mcp_tools import uso_tools

    assert "Cota do Claude" not in uso_tools.uso_ia_resumo("hoje")  # vazio: só a mensagem de sem uso
    assert isinstance(uso_tools.cota_claude_estimada(), str)


def test_alerta_proativo_uma_vez_por_janela():
    from jarvis.proativo import Contexto, uso_de_ia

    reg = servico.registro()
    configuracao.salvar(reg, {"teto_5h": 100})
    agora = time.time()
    reg.inserir(ts=agora - 60, fonte="ao_vivo", provedor="claude", modelo="m", uso={"in": 0, "out": 90, "cw": 0, "cw1h": 0, "cr": 0})
    avisos = alertas.verificar(agora, reg)
    assert any(k.startswith("uso:cota:5h:") for k, _ in avisos)
    assert avisos == alertas.verificar(agora + 5, reg)  # mesma chave: o agendador não repete
    c = Contexto(agora=None, cfg=None, uso=lambda: avisos)
    assert uso_de_ia(c).chave == avisos[0][0] and uso_de_ia(Contexto(agora=None, cfg=None)) is None


def test_ponte_da_janela(monkeypatch):
    from jarvis.ui.api_uso import UsoMixin

    api = UsoMixin()
    r = api.uso_resumo("mes", {"modelo": ""})
    assert r["vazio"] is True and r["cota"]["estimativa"] is True
    assert api.uso_salvar_config({"orcamento_mensal": "50"})["orcamento_mensal"] == 50
    assert api.uso_salvar_precos({"modelos": {"zz": {"in": 1, "out": 2}}})["modelos"]["zz"]["out"] == 2
    assert "error" in api.uso_calibrar("5h", 80)  # sem uso ainda
    assert api.uso_sessao("nada")["origem"] == "nenhum"
    assert api.uso_exportar("json") == {"error": "janela indisponível"}


def test_pagina_da_janela_tem_a_aba_e_nao_usa_innerhtml():
    from jarvis.ui import web

    pagina = web.page()
    assert 'id="open-uso"' in pagina and 'id="uso"' in pagina and "UsoGraficos" in pagina
    codigo = "".join((web.BASE / "js" / f"{n}.js").read_text(encoding="utf-8") for n in ("uso", "uso-config", "uso-graficos"))
    assert "innerHTML" not in codigo and "cdn" not in codigo.lower()

