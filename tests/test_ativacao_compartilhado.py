"""Paridade PC x celular da palavra de ativação: movel/testes/dados/ativacao_python.json guarda a saída de extrair_comando para os mesmos
textos que movel/testes/escuta.test.mjs confere. Se alguém mudar a lógica do PC, este teste falha e o arquivo precisa ser gerado de novo."""

import json
from pathlib import Path

import pytest

from jarvis.voice.ativacao import extrair_comando

CASOS = json.loads((Path(__file__).resolve().parent.parent / "movel" / "testes" / "dados" / "ativacao_python.json").read_text(encoding="utf-8"))


def test_casos_do_celular_batem_com_o_python():
    assert len(CASOS) >= 40
    for entrada, esperado in CASOS:
        assert extrair_comando(entrada) == esperado, entrada
