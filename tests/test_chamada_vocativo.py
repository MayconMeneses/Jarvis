"""Paridade PC x celular do vocativo e da saudação: lê os MESMOS casos de movel/testes/dados/ (o teste node do celular lê os mesmos arquivos)."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from jarvis.voice.chamada import LimitadorAtivacao, e_saudacao, extrair_chamada, responder_saudacao

DADOS = Path(__file__).resolve().parent.parent / "movel" / "testes" / "dados"
VOCATIVO = json.loads((DADOS / "ativacao_vocativo.json").read_text(encoding="utf-8"))
SAUDACOES = json.loads((DADOS / "saudacoes.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("frase,esperado", VOCATIVO["aceitar"])
def test_vocativo_aceita(frase, esperado):
    assert extrair_chamada(frase) == esperado


@pytest.mark.parametrize("frase", VOCATIVO["rejeitar"])
def test_vocativo_rejeita(frase):
    assert extrair_chamada(frase) is None


@pytest.mark.parametrize("frase", SAUDACOES["sim"])
def test_saudacao_pura(frase):
    assert e_saudacao(frase)
    assert responder_saudacao(frase, datetime(2026, 1, 1, 21)).startswith("Boa noite")


@pytest.mark.parametrize("frase", SAUDACOES["nao"])
def test_nao_e_saudacao(frase):
    assert not e_saudacao(frase)
    assert responder_saudacao(frase) is None


def test_limitador_de_ativacoes():
    t = [0.0]
    lim = LimitadorAtivacao(n=2, janela_s=60, relogio=lambda: t[0])
    assert lim.permite() and lim.permite() and not lim.permite()
    t[0] = 61
    assert lim.permite()


# ── ligação com o ciclo de voz ───────────────────────────────────────────
import numpy as np  # noqa: E402

from tests.test_escuta_foco import montar  # noqa: E402

AUDIO = np.zeros(8000, np.float32)


def test_loop_vocativo_no_fim_e_respondido_e_falado():
    loop, _, voz = montar("que horas são, Jarvis")
    assert loop._chamada_por_texto(AUDIO) is True
    assert voz.ditos == ["ok que horas são"]


def test_loop_saudacao_pura_e_respondida_sem_ia():
    loop, eventos, voz = montar("oi, boa noite, Jarvis")
    assert loop._chamada_por_texto(AUDIO) is True
    assert len(voz.ditos) == 1 and "Em que posso ajudar" in voz.ditos[0] and not voz.ditos[0].startswith("ok")
    assert any(e.get("answer", {}).get("brain") == "local" for e in eventos)


def test_loop_mencao_no_fim_nao_ativa():
    loop, eventos, voz = montar("falei com o Jarvis ontem")
    assert loop._chamada_por_texto(AUDIO) is False and voz.ditos == []


def test_loop_limita_ativacoes_por_minuto():
    loop, _, voz = montar(*["Jarvis, que horas são"] * 8)
    loop._limite_chamadas = LimitadorAtivacao(n=2, janela_s=999)
    resultados = [loop._chamada_por_texto(AUDIO) for _ in range(4)]
    assert resultados == [True, True, False, False] and len(voz.ditos) == 2


# ── erros de escuta do Whisper (só PC) ───────────────────────────────────
PC = json.loads((Path(__file__).resolve().parent / "dados" / "ativacao_pc.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("frase,esperado", PC["aceitar"])
def test_escuta_errada_aceita(frase, esperado):
    assert extrair_chamada(frase) == esperado


@pytest.mark.parametrize("frase", PC["rejeitar"])
def test_escuta_errada_rejeita(frase):
    assert extrair_chamada(frase) is None
