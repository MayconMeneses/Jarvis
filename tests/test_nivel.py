"""Orbe da janela: envelope da fala, volume do microfone, limitador de taxa, envio pela fala e pelo microfone."""

import queue
import threading
import types

import numpy as np

from jarvis.config import Config
from jarvis.voice import nivel, tts
from jarvis.voice.loop import VoiceLoop
from jarvis.ui import api_visual, workers


def _tom(taxa, segundos, amp):
    t = np.arange(int(taxa * segundos)) / taxa
    return (amp * np.sin(2 * np.pi * 220 * t)).astype(np.int16)


def test_envelope_tem_valores_inteiros_de_0_a_100_a_cada_40ms():
    taxa = 22050
    pcm = np.concatenate([_tom(taxa, 1.0, 12000), np.zeros(taxa, dtype=np.int16), _tom(taxa, 1.0, 3000)])
    env = nivel.envelope(pcm, taxa)
    assert len(env) == 75  # 3 s / 40 ms
    assert all(isinstance(v, int) and 0 <= v <= 100 for v in env)
    assert max(env[:25]) == 100 and max(env[25:50]) == 0  # trecho alto cheio; silêncio zero
    assert 0 < max(env[50:]) <= 100
    assert len(env) < 600  # frase curta cabe em ~500 bytes


def test_envelope_vazio_e_silencio():
    assert nivel.envelope(np.zeros(0, dtype=np.int16), 22050) == []
    assert set(nivel.envelope(np.zeros(22050, dtype=np.int16), 22050)) == {0}


def test_envelope_aceita_float():
    env = nivel.envelope(_tom(16000, 0.5, 8000).astype(np.float32) / 32768, 16000)
    assert len(env) == 13 and max(env) == 100


def test_nivel_mic_desconta_o_ruido_de_fundo():
    assert nivel.nivel_mic(300, 300) == 0.0
    assert nivel.nivel_mic(100, 300) == 0.0
    meio = nivel.nivel_mic(1500, 300)
    assert 0 < meio < 1
    assert nivel.nivel_mic(30000, 300) == 1.0
    assert nivel.nivel_mic(1500, 300) < nivel.nivel_mic(2000, 300)


def test_limitador_de_taxa():
    agora = [0.0]
    lim = nivel.LimitadorTaxa(20, relogio=lambda: agora[0])
    assert lim.permite()
    agora[0] = 0.02
    assert not lim.permite()
    agora[0] = 0.06
    assert lim.permite()


def test_fala_avisa_o_orbe_antes_de_tocar_e_no_fim(monkeypatch):
    ordem = []
    fake_sd = types.SimpleNamespace(play=lambda pcm, taxa: ordem.append("play"), wait=lambda: None, stop=lambda: ordem.append("stop"))
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", fake_sd)

    class Voz:
        sample_rate = 22050

        def synthesize(self, texto):
            return _tom(22050, 0.4, 9000)

    eventos = []
    s = tts.Speaker(motor="online", on_visual=lambda p: (eventos.append(p), ordem.append(p["tipo"])), atraso_ms=120)
    s.edge = Voz()
    s.say("Uma frase simples.")
    assert ordem == ["fala", "play", "fim"]
    fala = eventos[0]
    assert fala["dt"] == 40 and fala["atraso_ms"] == 120 and len(fala["env"]) == 10
    s.stop()
    assert eventos[-1] == {"tipo": "fim"}


def test_erro_no_orbe_nao_atrapalha_a_fala(monkeypatch):
    tocou = []
    monkeypatch.setitem(__import__("sys").modules, "sounddevice",
                        types.SimpleNamespace(play=lambda *a: tocou.append(1), wait=lambda: None, stop=lambda: None))

    class Voz:
        sample_rate = 22050

        def synthesize(self, texto):
            return _tom(22050, 0.2, 9000)

    def quebra(_):
        raise RuntimeError("janela fechou")

    s = tts.Speaker(motor="online", on_visual=quebra)
    s.edge = Voz()
    s.say("Frase que precisa ser falada.")
    assert tocou == [1]


def test_microfone_entra_na_fila_de_tamanho_1_e_sai_a_20hz():
    eventos = []
    loop = VoiceLoop(respond=lambda t: {}, notify=eventos.append, speaker=None, transcriber=None)
    loop._noise = 300.0
    frame = (np.ones((1280, 1), dtype=np.int16) * 2000)
    loop._on_audio(frame, 1280, None, None)  # fora da gravação: nada na fila
    assert loop._nivel_mic.empty()
    loop._mostrar_mic.set()
    for _ in range(5):
        loop._on_audio(frame, 1280, None, None)
    assert loop._nivel_mic.qsize() == 1  # descarta o antigo, nunca acumula
    t = threading.Thread(target=loop._enviar_nivel_mic, daemon=True)
    t.start()
    for _ in range(100):
        if eventos:
            break
        threading.Event().wait(0.02)
    loop.stop()
    t.join(1)
    assert eventos and eventos[0]["tipo"] == "mic" and 0 < eventos[0]["n"] <= 1


def test_enviar_visual_usa_o_window_onvoice_existente():
    chamadas = []
    janela = types.SimpleNamespace(evaluate_js=chamadas.append)
    workers.enviar_visual(janela, {"tipo": "mic", "n": 0.5})
    assert chamadas == ['window.onVoice({"tipo": "mic", "n": 0.5})']


def test_chave_de_efeitos_visuais_salva_na_config(tmp_path, monkeypatch):
    salvos = []
    monkeypatch.setattr(api_visual.config, "save", lambda cfg: salvos.append(cfg.efeitos_visuais))

    class Ponte(api_visual.VisualMixin):
        _cfg = Config()

    p = Ponte()
    assert p.efeitos_visuais() == "completo"
    assert p.definir_efeitos_visuais("suave") == "suave" and p.efeitos_visuais() == "suave"
    assert p.definir_efeitos_visuais("louco") == "completo"
    assert salvos == ["suave", "completo"]
    assert Config.from_dict({"efeitos_visuais": "desligado"}).efeitos_visuais == "desligado"
