"""Normalização pt-BR do texto falado: números, horas, datas, moedas, siglas, unidades, markdown e robustez."""

import random
import re
import string

import pytest

from jarvis.voice.normalizar import normalizar
from jarvis.voice.numeros import ordinal, por_extenso
from jarvis.voice.texto import MAX_SPOKEN, clean_for_speech, dividir_para_fala, pausa_ms


@pytest.mark.parametrize("n, esperado", [
    (0, "zero"), (1, "um"), (15, "quinze"), (21, "vinte e um"), (100, "cem"), (101, "cento e um"),
    (200, "duzentos"), (999, "novecentos e noventa e nove"), (1000, "mil"), (1001, "mil e um"),
    (1100, "mil e cem"), (1234, "mil duzentos e trinta e quatro"), (2026, "dois mil e vinte e seis"),
    (21000, "vinte e um mil"), (100000, "cem mil"), (1000000, "um milhão"), (1001000, "um milhão e mil"),
    (2500000, "dois milhões e quinhentos mil"), (3000000000, "três bilhões"), (-5, "menos cinco"),
])
def test_numeros_por_extenso(n, esperado):
    assert por_extenso(n) == esperado


def test_feminino_e_ordinais():
    assert por_extenso(2, feminino=True) == "duas" and por_extenso(201, feminino=True) == "duzentas e uma"
    assert ordinal(1) == "primeiro" and ordinal(2, feminino=True) == "segunda" and ordinal(15) == "quinze"


@pytest.mark.parametrize("texto, esperado", [
    ("às 14:30", "às catorze e trinta"), ("às 9:05", "às nove e cinco"), ("14:00", "catorze horas"),
    ("1:00", "uma hora"), ("2h", "duas horas"), ("8h30", "oito e trinta"), ("12:00", "meio-dia"), ("00:00", "meia-noite"),
    ("25:99", "vinte e cinco:noventa e nove"),   # não é hora: lê os números
    ("20/10/2026", "vinte de outubro de dois mil e vinte e seis"), ("01/05", "primeiro de maio"),
    ("5/3/26", "cinco de março de dois mil e vinte e seis"),
    ("R$ 1.234,56", "mil duzentos e trinta e quatro reais e cinquenta e seis centavos"),
    ("R$ 5", "cinco reais"), ("R$ 1", "um real"), ("R$ 0,50", "cinquenta centavos"), ("R$ 2 milhões", "dois milhões de reais"),
    ("95%", "noventa e cinco por cento"), ("12,5%", "doze vírgula cinco por cento"),
    ("3,14", "três vírgula catorze"), ("0,05", "zero vírgula zero cinco"),
    ("8 GB", "oito gigabytes"), ("1 GB", "um gigabyte"), ("2,4 GHz", "dois vírgula quatro gigahertz"),
    ("120 ms", "cento e vinte milissegundos"), ("5km", "cinco quilômetros"),
    ("36°C", "trinta e seis graus Celsius"), ("-3°C", "menos três graus Celsius"),
    ("1º lugar", "primeiro lugar"), ("2ª vez", "segunda vez"), ("1.500 itens", "mil e quinhentos itens"),
    ("tel 99999-0000", "tel nove nove nove nove nove, zero zero zero zero"), ("000123", "zero zero zero um dois três"),
])
def test_numeros_horas_datas_moedas(texto, esperado):
    assert normalizar(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("o PC e a CPU", "o pê cê e a cê pê u"), ("8 GB de RAM", "oito gigabytes de rám"), ("uma IA no SSD", "uma i á no ésse ésse dê"),
    ("Dr. Silva", "doutor Silva"), ("Sra. Lima, Av. Brasil nº 45", "senhora Lima, avenida Brasil número quarenta e cinco"),
    ("ex.: isso", "por exemplo: isso"), ("e/ou", "e ou"), ("A & B", "A e B"), ("2 + 2 = 4", "dois mais dois igual a quatro"),
    ("BRL", "B R L"),                      # sigla sem vogal é soletrada
    ("ATENÇÃO agora", "ATENÇÃO agora"),    # palavra em caixa alta com vogal fica
    ("wi-fi e e-mail", "uaifai e i-meio"),
])
def test_siglas_abreviacoes_simbolos(texto, esperado):
    assert normalizar(texto) == esperado


def test_marcacao_links_emojis_listas_e_codigo():
    texto = ("# Título\n- primeiro item\n- segundo item\n1. passo um\n**negrito** e _itálico_ 🙂🚀\n"
             "veja [o site](https://exemplo.com/a?b=1) ou https://x.org e escreva a fulano@exemplo.com\n```py\nprint(1)\n```\n"
             r"arquivo C:\Users\a\b.txt")
    falado = clean_for_speech(texto)
    for lixo in ("#", "*", "_", "http", "@", "🙂", "🚀", "print", "[", "]", "```", "\\"):
        assert lixo not in falado, lixo
    assert "o site" in falado and "código na janela" in falado and "um endereço de i-meio" in falado
    assert falado.count(".") >= 4  # cada linha de lista/título virou uma pausa
    assert re.search(r"Título\. primeiro item\. segundo item\. passo um\.", falado)


def test_texto_longo_e_cortado_e_depois_normalizado():
    longo = "A RAM está em 95% agora. " * 80
    falado = clean_for_speech(longo)
    assert falado.endswith("Os detalhes estão na janela.") and not re.search(r"\d", falado)
    assert len(clean_for_speech("Esta é uma frase de teste. " * 60)) <= MAX_SPOKEN + 40


def test_normalizar_e_idempotente_e_nao_deixa_digitos():
    for frase in ("São 14:30 do dia 20/10/2026, R$ 1.234,56 (12,5%)", "RAM 8 GB, CPU 45%, 3 e-mails", "Dr. Silva 1º lugar"):
        uma = normalizar(frase)
        assert not re.search(r"\d", uma) and normalizar(uma) == uma


def test_entradas_estranhas_nunca_levantam():
    r = random.Random(7)
    alfabeto = string.printable + "ãéçº°ª€→…🙂\u200d\ufe0f"
    for _ in range(300):
        lixo = "".join(r.choice(alfabeto) for _ in range(r.randint(0, 80)))
        assert isinstance(clean_for_speech(lixo), str)
    for caso in ("", "   ", "\n\n", "99999999999999999999999999 reais", "R$ " + "9" * 40, "0" * 50, "..,,;;"):
        assert isinstance(clean_for_speech(caso), str)


def test_primeira_frase_e_curta_e_pausas_por_pontuacao():
    longa = ("Claro, Maycon, vou olhar isso agora mesmo e te conto tudo que encontrar na sua agenda de hoje, "
             "incluindo as reuniões. Depois eu aviso.")
    partes = dividir_para_fala(longa)
    assert len(partes[0]) <= 60 and len(partes) == 3 and " ".join(partes).replace(" ", "") == longa.replace(" ", "")
    assert dividir_para_fala("Oi.") == ["Oi."] and dividir_para_fala("") == []
    assert pausa_ms("Fim.") > pausa_ms("segue,") and pausa_ms("Certo?") >= pausa_ms("Fim.")
