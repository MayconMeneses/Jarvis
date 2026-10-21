"""Paridade PC x celular: movel/testes/dados/casos_python.json guarda a saída do Python para os mesmos textos que os testes de JavaScript
conferem (movel/testes/voz.test.mjs). Se alguém mudar a normalização do PC, este teste falha e o arquivo precisa ser gerado de novo."""

import json
from pathlib import Path

import pytest

from jarvis.info.leitor_idioma import detectar
from jarvis.radar.numeros_pt import falar_texto
from jarvis.voice.normalizar import normalizar
from jarvis.voice.numeros import por_extenso
from jarvis.voice.texto import clean_for_speech, dividir_para_fala

CASOS = json.loads((Path(__file__).resolve().parent.parent / "movel" / "testes" / "dados" / "casos_python.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("secao, funcao", [
    ("normalizar", normalizar), ("por_extenso", por_extenso), ("falar_radar", falar_texto),
    ("limpar_para_fala", clean_for_speech), ("dividir_para_fala", dividir_para_fala), ("idioma", detectar),
])
def test_casos_do_celular_batem_com_o_python(secao, funcao):
    assert CASOS[secao], secao
    for entrada, esperado in CASOS[secao]:
        assert funcao(entrada) == esperado, entrada


def test_partes_da_leitura_batem_com_o_python():
    leitor = pytest.importorskip("jarvis.info.leitor")  # importa os cérebros (precisa do keyring instalado)
    for entrada, esperado in CASOS["partes"]:
        assert leitor.partes(entrada) == esperado
