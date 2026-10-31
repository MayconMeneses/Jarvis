"""Conjunto RETIDO de comandos (nunca usado para ajustar os padrões) e casos de roteamento corrigidos."""

import pytest

from jarvis.eval import bench
from jarvis.local.engine import LocalEngine

MOTOR = LocalEngine()


def _frase(texto):
    return bench.predict(MOTOR, texto)


def test_retido_nao_repete_frases_de_ajuste_nem_validacao():
    usadas = {t.lower() for n in ("comandos.json", "comandos_validacao.json") for t, _ in bench.load(n)}
    retido = bench.load("comandos_retidos2.json")
    assert len(retido) >= 40
    assert not [t for t, _ in retido if t.lower() in usadas]


def test_acuracia_no_retido():
    dados = bench.load("comandos_retidos2.json")
    acertos = sum(_frase(t) == e for t, e in dados)
    assert acertos / len(dados) >= 0.90


@pytest.mark.parametrize("texto,intencao", [
    ("abre o VS Code pra mim", "abrir"),
    ("me fala as horas", "hora"),
    ("hoje é que dia?", "data"),
    ("fale sobre a teoria da relatividade", "pesquisa"),
    ("o que você sabe fazer?", "ajuda"),
    ("mostra as notícias de hoje", "noticias"),
    ("escreva um e-mail para o meu chefe", "nenhum"),
    ("revise o código do login", "nenhum"),
    ("revise o projeto MeuApp", "avaliar_projeto"),
    ("registra que a entrega é na sexta", "lembrar"),
])
def test_roteamento_corrigido(texto, intencao):
    assert _frase(texto) == intencao


def test_fale_sobre_tecnologia_conhecida_explica_sem_internet():
    assert "Dockerfile" in MOTOR.handle("fale sobre docker")


def test_redigir_texto_sem_ia_explica_como_ligar_um_cerebro():
    resposta = MOTOR.ask([{"role": "user", "content": "escreva um e-mail para o fornecedor"}]).text
    assert "cérebro generativo" in resposta
