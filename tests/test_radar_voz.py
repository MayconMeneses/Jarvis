import types
import wave
from datetime import datetime

import numpy as np
import pytest

from jarvis.radar import narrar, numeros_pt, roteiro
from jarvis.radar.modelos import Artigo, Boletim, Item

HOJE = datetime(2026, 10, 20, 7, 0)


def item(titulo, fonte="G1", nota=80, linhas=(), **kw):
    return Item(Artigo(fonte, titulo, f"https://{fonte.lower()}.com/{abs(hash(titulo)) % 999}", 1.0), nota=nota,
                manchete=titulo, linhas=list(linhas), **kw)


# ── números e texto para falar ───────────────────────────────────────────

@pytest.mark.parametrize("n, falado", [
    (0, "zero"), (1, "um"), (15, "quinze"), (21, "vinte e um"), (100, "cem"), (101, "cento e um"),
    (342, "trezentos e quarenta e dois"), (1000, "mil"), (1500, "mil e quinhentos"), (1234, "mil duzentos e trinta e quatro"),
    (2026, "dois mil e vinte e seis"), (12000, "doze mil"), (1_200_000, "um milhão e duzentos mil"),
    (2_000_003, "dois milhões e três"), (3_500_000_000, "três bilhões e quinhentos milhões"),
])
def test_integers_in_portuguese(n, falado):
    assert numeros_pt.por_extenso(n) == falado


def test_spoken_text_covers_money_percent_dates_and_acronyms():
    f = numeros_pt.falar_texto
    assert f("R$ 1,2 bilhão") == "um vírgula dois bilhão de reais"
    assert f("R$ 1.500") == "mil e quinhentos reais" and f("R$ 1,50") == "um real e cinquenta centavos"
    assert f("subiu 30%") == "subiu trinta por cento" and f("2,5%") == "dois vírgula cinco por cento"
    assert f("em 20/10") == "em vinte de outubro" and f("1º de dezembro") == "primeiro de dezembro"
    assert f("a IA e o PIB") == "a i-a e o p-i-b" and f("o PIX") == "o PIX"  # pronunciável fica como está
    assert f("0,05") == "zero vírgula zero cinco" and f("3,14") == "três vírgula catorze"


def test_spoken_text_never_keeps_urls_markdown_emoji_brackets_or_bullets():
    sujo = "**Veja** https://exemplo.com/a?b=1 e www.site.com [fato] #hashtag 😀 `código` > citação\n- bullet item"
    limpo = numeros_pt.falar_texto(sujo)
    assert roteiro.limpo_para_voz(limpo) and "http" not in limpo and "Veja" in limpo and "hashtag" in limpo


# ── roteiro ──────────────────────────────────────────────────────────────

def boletim(n=7, linhas_por_item=2, **kw):
    itens = [item(f"Manchete número {i} sobre o banco central", fonte=f"Fonte{i}", nota=90 - i,
                  linhas=[f"Esta é a frase {j} do lead com algum conteúdo de verdade para a matéria {i}." for j in range(linhas_por_item)])
             for i in range(n)]
    return Boletim("2026-10-20", "economia", itens, **kw)


def test_script_structure_opening_attribution_and_closing():
    r = roteiro.montar(boletim(), 900, HOJE)
    texto = r["texto"]
    assert texto.startswith("Bom dia. Aqui é o seu radar de economia, vinte de outubro. Hoje: ")
    assert texto.count("Segundo o Fonte") == 7 and "Pra fechar." in texto and texto.endswith("Os links estão no boletim escrito de hoje.")
    assert roteiro.limpo_para_voz(texto)
    assert roteiro.saudacao(7) == "Bom dia" and roteiro.saudacao(14) == "Boa tarde" and roteiro.saudacao(21) == "Boa noite"


def test_word_budget_drops_the_lowest_scored_items_never_speeds_up():
    r = roteiro.montar(boletim(7, 2), 160, HOJE)
    assert r["palavras"] <= 160 and len(r["cortados"]) > 0 and len(r["itens"]) + len(r["cortados"]) == 7
    assert min(i.nota for i in r["itens"]) > max(i.nota for i in r["cortados"])  # saem os de menor nota
    assert roteiro.montar(boletim(1, 2), 5, HOJE)["itens"] != []  # nunca fica sem nenhum item
    assert roteiro.duracao_prevista_s(900, 180) == 300.0


def test_without_ai_only_real_content_is_spoken():
    sem_ia = boletim(2)
    sem_ia.itens[0].por_que = "Entrou na lista porque bate com: banco."
    assert "Entrou na lista" not in roteiro.montar(sem_ia, 900, HOJE)["texto"]  # texto de template não é narrado
    com_ia = boletim(2, com_ia=True)
    com_ia.itens[0].por_que = "Isso muda o custo do crédito para as famílias."
    assert "custo do crédito" in roteiro.montar(com_ia, 900, HOJE)["texto"]


def test_flags_late_bulletin_labels_and_suspicious_items_are_not_narrated():
    b = boletim(3, atrasado=True)
    b.itens[0].rotulo, b.itens[1].rotulo = "opinião", "possível paywall"
    b.itens[2].suspeito = "tenta dar ordens à IA"
    b.itens[0].tambem_em = ["Folha", "Estadão"]
    texto = roteiro.montar(b, 900, HOJE)["texto"]
    assert texto.startswith("Este é o boletim atrasado de hoje.") and "texto de opinião" in texto and "conteúdo completo é pago" in texto
    assert "Também publicado por Folha e Estadão" in texto and "Manchete número 2" not in texto


# ── áudio ────────────────────────────────────────────────────────────────

class VozFalsa:
    sample_rate = 22050

    def __init__(self):
        self.frases = []

    def synthesize(self, texto):
        self.frases.append(texto)
        return (np.ones(int(self.sample_rate * 0.5)) * 1000).astype(np.int16)


def test_long_script_is_not_truncated_and_wav_is_valid(tmp_path):
    texto = roteiro.montar(boletim(7, 2), 900, HOJE)["texto"]
    assert len(texto) > 600  # o limite de 600 caracteres do chat não vale aqui
    voz = VozFalsa()
    destino = tmp_path / "2026-10-20" / "boletim.wav"
    saida = narrar.narrar(texto, destino, voz=voz)
    assert " ".join(voz.frases).split() == texto.split()  # nada foi cortado ou perdido
    with wave.open(str(destino)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 22050)
        assert w.getnframes() / 22050 == pytest.approx(saida["duracao_s"], abs=0.01)
    assert saida["motor"] == "piper" and saida["duracao_s"] > len(voz.frases) * 0.5


def test_falls_back_to_windows_voice_when_piper_is_missing(tmp_path, monkeypatch):
    def sem_piper(efeito=True):
        raise RuntimeError("a voz local (Piper) ainda não está instalada")
    monkeypatch.setattr(narrar, "voz_local", sem_piper)
    chamadas = []

    def sapi(texto, destino):
        chamadas.append(texto)
        narrar.gravar_wav(destino, np.zeros(22050, dtype=np.int16), 22050)
    saida = narrar.narrar("Olá mundo.", tmp_path / "b.wav", sapi=sapi)
    assert saida["motor"] == "windows" and chamadas == ["Olá mundo."] and saida["duracao_s"] == pytest.approx(1.0)


def test_sapi_receives_text_on_stdin_never_in_the_command(tmp_path):
    vistos = {}

    def rodar(comando, **kw):
        vistos.update(comando=comando, entrada=kw["input"], env=kw["env"])
        (tmp_path / "x.wav").write_bytes(b"R" * 2000)
        return types.SimpleNamespace(returncode=0)
    narrar.sapi_para_arquivo("texto; Remove-Item -Recurse C:\\", tmp_path / "x.wav", rodar)
    assert "Remove-Item" not in " ".join(vistos["comando"]) and "Remove-Item" in vistos["entrada"]
    assert vistos["env"]["JARVIS_WAV"].endswith("x.wav")
    with pytest.raises(ValueError):
        narrar.sintetizar("", VozFalsa())
