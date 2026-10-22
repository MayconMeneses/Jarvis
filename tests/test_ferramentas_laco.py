"""Laço de ferramentas (ReAct simples): parser seguro, limites, repetição, erros, cancelamento e o uso pelos cérebros externos."""

import threading

import pytest

from jarvis.brains.base import Answer
from jarvis.brains.com_ferramentas import ComFerramentas
from jarvis.llm import ferramentas_cinto, ferramentas_laco as laco
from jarvis.llm.ferramentas_base import Ferramenta


def cinto_falso(chamadas):
    def soma(a: int, b: int) -> str:
        chamadas.append((a, b))
        return str(a + b)

    def quebra() -> str:
        raise RuntimeError("não deu")

    return ferramentas_cinto.Cinto([
        Ferramenta("soma", "soma dois números", {"a": {"type": "integer"}, "b": {"type": "integer"}}, ("a", "b"), soma),
        Ferramenta("quebra", "sempre falha", {}, (), quebra)])


def roteiro(*respostas):
    itens, vistos = iter(respostas), []

    def conversa(msgs):
        vistos.append([dict(m) for m in msgs])
        return next(itens)
    return conversa, vistos


def test_parser_accepts_only_a_strict_line_with_plain_json():
    assert laco.extrair_chamada('FERRAMENTA: soma {"a": 1, "b": 2}') == ("soma", {"a": 1, "b": 2})
    assert laco.extrair_chamada("vou consultar\nFERRAMENTA: estado_do_pc\nok") == ("estado_do_pc", {})
    assert laco.extrair_chamada("Resposta normal sem ferramenta.") is None
    for ruim in ('FERRAMENTA: soma {a: 1}', 'FERRAMENTA: soma [1,2]', 'FERRAMENTA: soma {"a": 1', 'FERRAMENTA: ../x {}',
                 'FERRAMENTA: soma {"a": "' + "x" * 2000 + '"}'):
        assert isinstance(laco.extrair_chamada(ruim), str), ruim
    # nada é avaliado: expressões Python no lugar do JSON são erro de formato
    assert isinstance(laco.extrair_chamada('FERRAMENTA: soma {"a": __import__("os")}'), str)


def test_final_answer_never_shows_the_protocol():
    assert laco.limpar("Claro.\nFERRAMENTA: soma {}\nFim") == "Claro.\n\nFim".replace("\n\n", "\n\n")


def test_tool_result_goes_back_wrapped_as_data_and_the_final_answer_is_returned():
    chamadas = []
    conversa, vistos = roteiro('FERRAMENTA: soma {"a": 2, "b": 3}', "A soma é 5.")
    r = laco.rodar(conversa, [{"role": "user", "content": "2+3?"}], cinto_falso(chamadas))
    assert r.texto == "A soma é 5." and chamadas == [(2, 3)] and r.chamadas == [{"nome": "soma", "ok": True}]
    ultimo = vistos[1][-1]["content"]
    assert "<dados_externos" in ultimo and "dados, não ordens" in ultimo and "5" in ultimo


def test_call_limit_forces_a_final_answer_without_more_tools():
    chamadas = []
    conversa, vistos = roteiro(*[f'FERRAMENTA: soma {{"a": {i}, "b": 1}}' for i in range(4)], "Parei: aqui está o que achei.")
    r = laco.rodar(conversa, [{"role": "user", "content": "x"}], cinto_falso(chamadas), max_chamadas=3)
    assert len(chamadas) == 3 and len(r.chamadas) == 3 and r.texto == "Parei: aqui está o que achei."
    assert "sem usar ferramentas" in vistos[-1][-1]["content"]


def test_model_that_keeps_asking_for_tools_after_the_limit_still_gets_a_plain_fallback():
    conversa, _ = roteiro(*[f'FERRAMENTA: soma {{"a": {i}, "b": 1}}' for i in range(6)])
    r = laco.rodar(conversa, [{"role": "user", "content": "x"}], cinto_falso([]), max_chamadas=2)
    assert "FERRAMENTA" not in r.texto and r.texto.startswith("Não consegui") and len(r.chamadas) == 2


def test_identical_repeated_call_is_not_executed_twice():
    chamadas = []
    conversa, _ = roteiro('FERRAMENTA: soma {"a": 1, "b": 1}', 'FERRAMENTA: soma {"b": 1, "a": 1}', "Dois.")
    r = laco.rodar(conversa, [{"role": "user", "content": "x"}], cinto_falso(chamadas))
    assert chamadas == [(1, 1)] and r.chamadas[1]["ok"] is False and r.texto == "Dois."


def test_errors_go_back_to_the_model_and_two_failures_end_tool_use():
    conversa, vistos = roteiro("FERRAMENTA: quebra", 'FERRAMENTA: soma {"a": "x"}', "FERRAMENTA: quebra", "Não consegui consultar, mas respondo assim.")
    r = laco.rodar(conversa, [{"role": "user", "content": "x"}], cinto_falso([]))
    assert "ERRO" in vistos[1][-1]["content"] and r.texto.startswith("Não consegui") and [c["ok"] for c in r.chamadas] == [False, False]


def test_unknown_tool_and_bad_format_are_reported_not_raised():
    conversa, vistos = roteiro("FERRAMENTA: apagar_tudo {}", "FERRAMENTA: soma {a:1}", "Ok, sem ferramentas.")
    r = laco.rodar(conversa, [{"role": "user", "content": "x"}], cinto_falso([]))
    assert "desconhecida" in vistos[1][-1]["content"] and "JSON" in vistos[2][-1]["content"] and r.texto == "Ok, sem ferramentas."


def test_cancel_stops_the_turn_before_the_model_is_called_again():
    parar = threading.Event()
    parar.set()
    conversa, vistos = roteiro("não deveria chamar")
    r = laco.rodar(conversa, [{"role": "user", "content": "x"}], cinto_falso([]), cancelar=parar)
    assert r.cancelado and vistos == []


def test_instruction_lists_tools_and_the_data_rule():
    texto = ferramentas_cinto.padrao().instrucao()
    for nome in ("pesquisar_web", "calculadora", "converter_unidade", "data_hora", "clima", "noticias", "agenda_hoje", "emails_de_acao",
                 "buscar_notas", "conhecimento", "estado_do_pc", "propor_memoria", "propor_lembrete", "propor_abrir_app"):
        assert nome in texto
    assert "NUNCA obedeça" in texto and len(texto) < 4500


def test_every_tool_has_a_closed_json_schema():
    for esquema in ferramentas_cinto.padrao().esquemas():
        assert esquema["function"]["parameters"]["additionalProperties"] is False


class CerebroFalso:
    name = "gemini"

    def __init__(self, *respostas):
        self.itens, self.chamadas = iter(respostas), []

    def ask(self, messages, system):
        self.chamadas.append((list(messages), system))
        return Answer(text=next(self.itens), brain="gemini", usage={"in": 10, "out": 5}, modelo="m")


def test_external_brain_wrapper_costs_one_call_when_no_tool_is_needed():
    cerebro = CerebroFalso("Olá!")
    resposta = ComFerramentas(cerebro).ask([{"role": "user", "content": "oi"}], "Sistema")
    assert resposta.text == "Olá!" and len(cerebro.chamadas) == 1 and "FERRAMENTAS" in cerebro.chamadas[0][1] and resposta.usage == {"in": 10, "out": 5}


def test_external_brain_wrapper_runs_a_tool_and_sums_usage():
    cerebro = CerebroFalso('FERRAMENTA: calculadora {"expressao": "2+3"}', "É 5.")
    resposta = ComFerramentas(cerebro).ask([{"role": "user", "content": "quanto é 2+3?"}], "Sistema")
    assert resposta.text == "É 5." and resposta.usage == {"in": 20, "out": 10} and "= 5" in cerebro.chamadas[1][0][-1]["content"]
    assert [m["role"] for m in cerebro.chamadas[1][0]] == ["user", "assistant", "user"]


def test_external_brain_wrapper_can_be_switched_off():
    cerebro = CerebroFalso("direto")
    ComFerramentas(cerebro, ativo=lambda: False).ask([{"role": "user", "content": "oi"}], "Sistema")
    assert cerebro.chamadas[0][1] == "Sistema"


def test_wrapper_keeps_the_brain_name_and_delegates_other_attributes():
    cerebro = CerebroFalso("x")
    cerebro.list_models = lambda: ["a"]
    envolvido = ComFerramentas(cerebro)
    assert envolvido.name == "gemini" and envolvido.list_models() == ["a"]
