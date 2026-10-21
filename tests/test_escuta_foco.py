"""Escuta do modo foco: "Jarvis, comando" na mesma frase, estados do microfone, pré-áudio, config e ponte."""

import json
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from jarvis import config
from jarvis.voice.ativacao import (AGUARDANDO, DESLIGADO, FALANDO, OUVINDO, PROCESSANDO, FocoEscuta,
                                   LimitadorTranscricao, Segmentador, estado_base, extrair_comando)
from jarvis.voice.gravador import FRAME, PreRoll, Recorder
from jarvis.voice.loop import VoiceLoop


def silencio(n=1):
    return [np.zeros(FRAME, dtype=np.int16) for _ in range(n)]


def fala(n=1):
    t = np.arange(FRAME) / 16000
    return [(6000 * np.sin(2 * np.pi * 220 * t)).astype(np.int16) for _ in range(n)]


# ── extração do comando ──────────────────────────────────────────────────

@pytest.mark.parametrize("texto,esperado", [
    ("Jarvis, abre o bloco de notas", "abre o bloco de notas"),
    ("jarvis que horas são?", "que horas são?"),
    ("Hey Jarvis, que horas são", "que horas são"),
    ("Ei, Jarvis. Abre o Chrome", "Abre o Chrome"),
    ("E aí Jarvis, tudo bem?", "tudo bem?"),
    ("Járvis, liga a luz", "liga a luz"),
    ("Garvis abre o e-mail", "abre o e-mail"),
    ("Avós, que horas são?", "que horas são?"),  # como o Whisper ouviu o "Jarvis" sintético
    ("Veja, Jarvis, que horas são.", "que horas são."),
    ("Jarvis", ""),
    ("Hey, Jarvis!", ""),
])
def test_extrai_o_comando_depois_do_nome(texto, esperado):
    assert extrair_comando(texto) == esperado


@pytest.mark.parametrize("texto", [
    "", "que horas são", "o Jarvis é muito legal", "eu falei com o jarvis ontem",
    "Travis, abre a porta", "Jarbas, vem cá", "Jarvis é um filme do Homem de Ferro",
    "bom dia a todos, hoje vamos falar do Jarvis",
])
def test_nao_ativa_sem_chamar_pelo_nome_no_comeco(texto):
    assert extrair_comando(texto) is None


def test_virgula_depois_do_nome_indica_que_falam_com_ele():
    assert extrair_comando("Jarvis, é hora de dormir?") == "é hora de dormir?"


# ── segmentador, pré-áudio e limites ─────────────────────────────────────

def test_segmentador_entrega_a_frase_ao_fim_da_pausa_com_o_comeco_incluido():
    seg = Segmentador(ruido=50)
    saidas = [seg.feed(f, 6000.0 if f.any() else 0.0) for f in silencio(5) + fala(8) + silencio(15)]
    audio = [s for s in saidas if s is not None]
    assert len(audio) == 1 and audio[0].dtype == np.float32
    assert audio[0].size >= (8 + 3) * FRAME  # 8 de voz + 3 quadros de pré-áudio
    assert not seg.falando


def test_segmentador_ignora_estalo_curto_e_silencio():
    seg = Segmentador(ruido=50)
    assert all(seg.feed(f, 0.0) is None for f in silencio(40))
    saidas = [seg.feed(f, 6000.0 if f.any() else 0.0) for f in fala(1) + silencio(15)]
    assert all(s is None for s in saidas)


def test_segmentador_corta_fala_muito_longa():
    seg = Segmentador(ruido=50, max_s=2.0)
    saidas = [seg.feed(f, 6000.0) for f in fala(60)]
    assert any(s is not None for s in saidas)


def test_pre_audio_guarda_so_o_final_e_esvazia_ao_pegar():
    pre = PreRoll(frames=3)
    for i in range(10):
        pre.add(np.full(FRAME, i, dtype=np.int16))
    assert [int(f[0]) for f in pre.take()] == [7, 8, 9] and pre.take() == []


def test_limitador_de_transcricoes():
    t = [0.0]
    lim = LimitadorTranscricao(n=2, janela_s=10, relogio=lambda: t[0])
    assert lim.permite() and lim.permite() and not lim.permite()
    t[0] = 11.0
    assert lim.permite()


def test_gravador_conta_quadros_com_voz():
    rec = Recorder(noise_floor=50)
    for f in silencio(2) + fala(5) + silencio(2):
        rec.feed(f)
    assert rec.loud == 5 and not rec.done


# ── estado do microfone e modo foco ──────────────────────────────────────

def test_estado_base():
    assert estado_base(False) == AGUARDANDO
    assert estado_base(True) == DESLIGADO and estado_base(False, ligado=False) == DESLIGADO


def test_foco_liga_a_escuta_e_devolve_o_estado_do_usuario_ao_sair():
    foco = FocoEscuta(auto=True)
    assert foco.entrar(pausada=True) is False and foco.ativo
    assert foco.entrar(pausada=False) is False  # reentrada não sobrescreve o "antes"
    assert foco.sair() is True and not foco.ativo
    assert foco.sair() is None


def test_foco_sem_auto_nao_liga_o_microfone():
    foco = FocoEscuta(auto=False)
    assert foco.entrar(pausada=True) is True
    assert foco.sair() is True


# ── ciclo com peças falsas ───────────────────────────────────────────────

class Transcritor:
    def __init__(self, *textos):
        self.textos = list(textos)
        self.chamadas = 0

    def warm_up(self):
        pass

    def transcribe(self, audio):
        self.chamadas += 1
        return self.textos.pop(0) if self.textos else ""


class Voz:
    def __init__(self):
        self.ditos = []

    def say(self, texto):
        self.ditos.append(texto)


def montar(*textos, **kw):
    eventos, voz = [], Voz()
    loop = VoiceLoop(respond=lambda t: {"text": f"ok {t}", "brain": "x", "actions": []}, notify=eventos.append,
                     speaker=voz, transcriber=Transcritor(*textos), **kw)
    loop._noise = 50
    return loop, eventos, voz


def estados(eventos):
    return [e["escuta"] for e in eventos if "escuta" in e]


def test_comando_na_mesma_frase_e_respondido_e_falado_sem_novo_bipe():
    loop, eventos, voz = montar("Hey Jarvis, que horas são")
    semente = fala(6)
    for f in fala(8) + silencio(15):
        loop._frames.put(f)
    loop._turno_com_comando(loop._comando_na_frase(semente))
    assert {"user": "que horas são", "status": "Pensando…"} in eventos
    assert voz.ditos == ["ok que horas são"]
    assert estados(eventos) == [OUVINDO, PROCESSANDO, PROCESSANDO, FALANDO, AGUARDANDO, AGUARDANDO]


def test_so_o_nome_nao_transcreve_e_cai_no_fluxo_do_bipe():
    loop, _, _ = montar()
    for f in silencio(20):
        loop._frames.put(f)
    assert loop._comando_na_frase(fala(6)) == "" and loop.transcriber.chamadas == 0


def test_modelo_disparou_mas_transcricao_sem_o_nome_nao_responde_a_conversa_alheia():
    loop, _, _ = montar("a gente vai ao mercado amanhã")
    for f in fala(8) + silencio(15):
        loop._frames.put(f)
    assert loop._comando_na_frase(fala(6)) == ""


def test_chamada_por_texto_ignora_conversa_e_age_so_quando_comeca_com_jarvis():
    loop, eventos, voz = montar("o jarvis é legal", "Jarvis, abre o bloco de notas")
    assert loop._chamada_por_texto(np.zeros(8000, np.float32)) is False
    assert eventos == [] and voz.ditos == []
    assert loop._chamada_por_texto(np.zeros(8000, np.float32)) is True
    assert voz.ditos == ["ok abre o bloco de notas"]


def test_chamada_por_texto_respeita_o_limite_de_transcricoes():
    loop, _, _ = montar("x", "x", "x")
    loop._limite = LimitadorTranscricao(n=1, janela_s=999)
    loop._chamada_por_texto(np.zeros(8000, np.float32))
    loop._chamada_por_texto(np.zeros(8000, np.float32))
    assert loop.transcriber.chamadas == 1


def test_pausar_mostra_microfone_desligado_e_retomar_mostra_aguardando():
    loop, eventos, _ = montar()
    loop.set_paused(True)
    loop.set_paused(False)
    assert estados(eventos) == [DESLIGADO, AGUARDANDO] and loop.estado == AGUARDANDO


def test_por_texto_so_liga_se_a_config_permitir():
    loop, _, _ = montar(por_texto=False)
    loop.set_por_texto(True)
    assert not loop._por_texto.is_set()
    loop2, _, _ = montar()
    loop2.set_por_texto(True)
    assert loop2._por_texto.is_set()


# ── configuração e ponte ─────────────────────────────────────────────────

def test_config_antiga_ganha_os_campos_novos_com_padrao_seguro():
    antigo = {"voz": {"ativa": True, "sensibilidade": 0.4}}
    cfg = config.Config.from_dict(antigo)
    assert cfg.voz.foco_escuta_auto is True and cfg.voz.ativacao_por_texto is True and cfg.voz.sensibilidade == 0.4


def test_config_salva_e_relida(tmp_path):
    cfg = config.Config()
    cfg.voz.foco_escuta_auto = False
    caminho = tmp_path / "c.json"
    config.save(cfg, caminho)
    assert json.loads(caminho.read_text(encoding="utf-8"))["voz"]["foco_escuta_auto"] is False
    assert config.Config.from_dict(json.loads(caminho.read_text(encoding="utf-8"))).voz.foco_escuta_auto is False


class VozFalsa:
    def __init__(self, pausada=False):
        self.paused = threading.Event()
        if pausada:
            self.paused.set()
        self.estado, self.por_texto = AGUARDANDO, None

    def set_paused(self, p):
        (self.paused.set if p else self.paused.clear)()
        self.estado = DESLIGADO if p else AGUARDANDO

    def set_por_texto(self, v):
        self.por_texto = v


def ponte(voz, auto=True):
    from jarvis.ui.api_escuta import EscutaMixin

    api = EscutaMixin()
    api._voice = voz
    api._cfg = SimpleNamespace(voz=SimpleNamespace(foco_escuta_auto=auto))
    return api


def test_ponte_entrar_no_foco_liga_e_sair_restaura():
    voz = VozFalsa(pausada=True)
    api = ponte(voz)
    info = api.escuta_foco(True)
    assert info == {"disponivel": True, "estado": AGUARDANDO, "pausada": False} and voz.por_texto is True
    info = api.escuta_foco(False)
    assert info["pausada"] is True and voz.por_texto is False


def test_ponte_nao_desliga_a_escuta_que_ja_estava_ligada_ao_sair():
    voz = VozFalsa(pausada=False)
    api = ponte(voz)
    api.escuta_foco(True)
    assert api.escuta_foco(False)["pausada"] is False


def test_ponte_um_clique_desliga_e_liga():
    voz = VozFalsa()
    api = ponte(voz)
    assert api.escuta_definir(False)["estado"] == DESLIGADO
    assert api.escuta_definir(True)["pausada"] is False


def test_ponte_sem_voz_informa_indisponivel_e_nao_quebra():
    api = ponte(None)
    assert api.escuta_foco(True)["disponivel"] is False
    assert api.escuta_definir(True)["disponivel"] is False
    assert api.escuta_foco(False)["estado"] == DESLIGADO


def test_pagina_inclui_o_microfone_do_foco():
    from jarvis.ui import web

    html = web.page()
    assert 'id="foco-mic"' in html and "window.FocoMic" in html and "foco-mic-botao" in html
