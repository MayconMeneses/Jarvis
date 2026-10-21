"""Qualidade do áudio, parada limpa (barge-in), cache, falhas de placa/modelo e eco no ciclo de voz."""

import hashlib
import threading

import numpy as np
import pytest
from sd_falso import sd_falso

from jarvis.voice import audio, local, tts
from jarvis.voice.cache import CacheFrases
from jarvis.voice.loop import VoiceLoop
from jarvis.voice.nivel import envelope
from jarvis.voice.reprodutor import Reprodutor


def _tom(taxa=22050, s=0.5, amp=9000, f=220):
    t = np.arange(int(taxa * s)) / taxa
    return (amp * np.sin(2 * np.pi * f * t)).astype(np.int16)


class _Voz:
    sample_rate = 22050

    def __init__(self, falha=False):
        self.falha, self.chamadas = falha, []

    def synthesize(self, texto):
        self.chamadas.append(texto)
        if self.falha:
            raise RuntimeError("onnxruntime caiu")
        return _tom(s=0.3)


def _speaker(monkeypatch, sd, voz=None, **kw):
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", sd)
    s = tts.Speaker(motor="online", **kw)
    s.edge = voz or _Voz()
    return s


# ── qualidade do áudio ──────────────────────────────────────────────────

def test_volume_fica_parelho_entre_fala_baixa_e_alta():
    saidas = [audio.acabamento(_tom(amp=a), 22050) for a in (1500, 8000, 20000)]
    rms = [float(np.sqrt(np.mean((s / 32768.0) ** 2))) for s in saidas]
    assert max(rms) / min(rms) < 1.5
    assert all(np.abs(s).max() <= 0.9 * 32767 for s in saidas)  # folga contra clipping


def test_silencio_nao_e_amplificado_e_vazio_nao_quebra():
    assert not audio.acabamento(np.zeros(2000, dtype=np.int16), 22050).any()
    assert audio.acabamento(np.zeros(0, dtype=np.int16), 22050).size == 0


def test_fade_comeca_e_termina_em_zero_e_pausa_final_e_somada():
    pcm = np.full(22050, 12000, dtype=np.int16)  # onda cortada seca: onde o estalo nasce
    saida = audio.acabamento(pcm, 22050, pausa_final_ms=200)
    assert saida[0] == 0 and abs(int(saida[1])) < 1000 and saida[-1] == 0
    assert saida.size == 22050 + int(22050 * 0.2) and not saida[-int(22050 * 0.15):].any()
    assert np.abs(np.diff(saida[:22050].astype(int))).max() < 2500  # sem degrau brusco


def test_bipe_suave_sem_estalo():
    onda = audio.chime_wave()
    assert onda.dtype == np.float32 and 0.1 < len(onda) / audio.CHIME_RATE < 0.3
    assert abs(onda[0]) < 1e-3 and abs(onda[-1]) < 1e-3 and np.abs(onda).max() < 0.4


def test_envelope_acompanha_a_fala_com_reverb_e_acabamento():
    taxa = 22050
    palavra = _tom(taxa, 0.30, 12000, 180) * np.hanning(int(taxa * 0.30))
    pausa = np.zeros(int(taxa * 0.25))
    pcm = np.concatenate([palavra, pausa, palavra, pausa, palavra]).astype(np.int16)
    final = audio.acabamento(local.com_reverb_discreto(pcm, taxa), taxa, 200)
    env = np.array(envelope(final, taxa))
    for i in range(3):  # o envelope é alto dentro da palavra e zero no meio da pausa
        assert env[int((i * 0.55 + 0.15) / 0.04)] > 60
        if i < 2:
            assert env[int((i * 0.55 + 0.42) / 0.04)] == 0
    assert len(env) == int(np.ceil(final.size / int(taxa * 0.04)))


# ── cache e latência ────────────────────────────────────────────────────

def test_cache_lru_e_so_frases_curtas():
    c = CacheFrases(max_itens=2)
    for t in ("a", "b", "c"):
        c.guardar((t,), t, t)
    assert c.pegar(("a",)) is None and c.pegar(("c",)) == "c" and len(c) == 2
    c.guardar(("longo",), "x" * 200, 1)
    assert c.pegar(("longo",)) is None


def test_frase_repetida_sai_do_cache_sem_sintetizar(monkeypatch):
    sd, _ = sd_falso()
    voz = _Voz()
    s = _speaker(monkeypatch, sd, voz)
    s.say("Um momento.")
    s.say("Um momento.")
    assert voz.chamadas == ["Um momento."] and s.cache.acertos == 1


def test_mede_o_tempo_ate_o_primeiro_audio(monkeypatch):
    sd, _ = sd_falso()
    s = _speaker(monkeypatch, sd)
    assert s.ultima_latencia_ms is None
    s.say("Pronto.")
    assert 0 <= s.ultima_latencia_ms < 2000


# ── falhas: placa de som, dispositivo, síntese ──────────────────────────

def test_dispositivo_mudou_reenumera_e_toca(monkeypatch):
    sd, reg = sd_falso(falha_abrir=1)  # ex.: fone Bluetooth desligou; a 1ª abertura falha
    s = _speaker(monkeypatch, sd)
    falou = []
    monkeypatch.setattr(tts, "speak_sapi", lambda *a, **k: falou.append(a))
    s.say("Frase de teste.")
    assert reg.reinicios == 1 and reg.fluxos and reg.fluxos[0].escritos and not falou


def test_sem_placa_de_som_cai_na_voz_do_windows_e_nao_levanta(monkeypatch):
    sd, reg = sd_falso(falha_abrir=99)
    s = _speaker(monkeypatch, sd)
    falou = []
    monkeypatch.setattr(tts, "speak_sapi", lambda texto, registrar=None: falou.append(texto))
    s.say("Primeira frase longa o bastante para ficar sozinha na lista. Segunda frase também comprida o suficiente.")
    assert len(falou) == 1 and "Primeira" in falou[0] and "Segunda" in falou[0]


def test_nem_sapi_funciona_e_ainda_assim_nao_levanta(monkeypatch):
    sd, _ = sd_falso(falha_abrir=99)
    s = _speaker(monkeypatch, sd)

    def quebra(*a, **k):
        raise FileNotFoundError("powershell")

    monkeypatch.setattr(tts, "speak_sapi", quebra)
    s.say("Qualquer coisa.")  # não levanta
    s.on_visual = lambda p: 1 / 0
    s.say("De novo.")  # nem com o orbe quebrado


def test_erro_do_onnxruntime_usa_a_reserva_e_depois_a_sapi(monkeypatch):
    sd, reg = sd_falso()
    s = tts.Speaker()  # local por padrão
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", sd)
    s.local, s.edge = _Voz(falha=True), _Voz()
    s.say("Olá, tudo bem?")
    assert reg.fluxos[0].escritos  # a reserva online falou
    s.edge = _Voz(falha=True)
    falou = []
    monkeypatch.setattr(tts, "speak_sapi", lambda texto, registrar=None: falou.append(texto))
    s.say("Outra frase.")
    assert falou == ["Outra frase."]


def test_barge_in_para_no_meio_e_nao_toca_o_resto(monkeypatch):
    sd, reg = sd_falso()
    eventos = []
    s = _speaker(monkeypatch, sd, on_visual=eventos.append)
    original = sd.OutputStream.write

    def escreve_e_interrompe(self, bloco):
        original(self, bloco)
        if len(self.escritos) == 3:
            s.stop()  # a pessoa fala por cima

    monkeypatch.setattr(sd.OutputStream, "write", escreve_e_interrompe)
    s.say("Primeira frase longa o bastante para ficar sozinha. Segunda frase também comprida o suficiente. Terceira frase final.")
    assert len(reg.fluxos) == 1 and len(reg.fluxos[0].escritos) == 3 and reg.fluxos[0].abortou == 1
    assert eventos[-1] == {"tipo": "fim"}
    s.say("Nova fala depois de interromper.")  # a parada não "gruda"
    assert len(reg.fluxos[0].escritos) > 3


def test_reprodutor_levanta_se_a_placa_nao_volta():
    sd, reg = sd_falso(falha_abrir=5)
    r = Reprodutor()
    r._sd = sd
    with pytest.raises(OSError):
        r.tocar(_tom(s=0.1), 22050, threading.Event())
    assert reg.reinicios == 1


def test_chime_sem_placa_nao_levanta(monkeypatch):
    sd, _ = sd_falso()
    sd.play = lambda *a, **k: (_ for _ in ()).throw(OSError("sem saída"))
    _speaker(monkeypatch, sd).chime()


# ── modelo local: threads, catálogo, arquivo corrompido ─────────────────

def test_threads_padrao_limitadas_a_4(monkeypatch):
    monkeypatch.setattr(local.os, "cpu_count", lambda: 8)
    assert local.threads_padrao() == 4
    monkeypatch.setattr(local.os, "cpu_count", lambda: 2)
    assert local.threads_padrao() == 1 and local.PiperVoice(threads=3).threads == 3


def test_catalogo_de_vozes_tem_sha_e_url_oficial():
    for nome in ("cadu", "jeff"):
        _, url, arquivos = local.definicao(nome)
        assert url.startswith("https://huggingface.co/rhasspy/piper-voices/") and nome in url
        assert len(arquivos) == 2 and all(len(sha) == 64 for sha in arquivos.values())
    assert local.definicao("desconhecida") == (local.NOME, local.BASE, local.ARQUIVOS)


def test_baixa_voz_alternativa_com_sha(tmp_path, monkeypatch):
    conteudos = {"x.onnx": b"m", "x.onnx.json": b"{}"}
    monkeypatch.setitem(local.VOZES_ALTERNATIVAS, "cadu", ("x", {n: hashlib.sha256(c).hexdigest() for n, c in conteudos.items()}))
    urls = []

    def baixar(url, destino, on_status=None):
        urls.append(url)
        destino.write_bytes(conteudos[destino.name])

    local.baixar_voz(pasta=tmp_path, baixar=baixar, embutida=tmp_path / "vazio", modelo="cadu")
    assert all("/cadu/medium/" in u for u in urls) and local.voz_instalada(tmp_path, "cadu") and not local.voz_instalada(tmp_path)


def test_modelo_corrompido_e_apagado_para_baixar_de_novo(tmp_path, monkeypatch):
    for nome in local.ARQUIVOS:
        (tmp_path / nome).write_bytes(b"lixo")
    v = local.PiperVoice(pasta=tmp_path)
    monkeypatch.setattr(v, "_sessao", lambda *a: (_ for _ in ()).throw(RuntimeError("Protobuf parsing failed")))
    with pytest.raises(RuntimeError, match="corrompido"):
        v.synthesize("oi")
    assert not local.voz_instalada(tmp_path)  # o próximo preparar() baixa de novo


def test_erro_de_inferencia_com_arquivos_bons_nao_apaga_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(local, "ARQUIVOS", {"a.onnx": hashlib.sha256(b"ok").hexdigest()})
    (tmp_path / "a.onnx").write_bytes(b"ok")
    v = local.PiperVoice(pasta=tmp_path)
    monkeypatch.setattr(v, "_sessao", lambda *a: (_ for _ in ()).throw(RuntimeError("falta memória")))
    with pytest.raises(RuntimeError, match="memória"):
        v.synthesize("oi")
    assert (tmp_path / "a.onnx").exists()


# ── ciclo de voz: eco e barge-in ────────────────────────────────────────

class _Falante:
    def __init__(self, quebra=False):
        self.ditas, self.parou, self.quebra = [], 0, quebra

    def say(self, texto):
        if self.quebra:
            raise RuntimeError("placa sumiu")
        self.ditas.append(texto)

    def stop(self):
        self.parou += 1


def _loop(falante):
    return VoiceLoop(respond=lambda t: {"text": "ok"}, notify=lambda p: None, speaker=falante, transcriber=None)


def test_microfone_e_ignorado_enquanto_fala_e_depois_da_cauda(monkeypatch):
    from jarvis.voice import loop as modulo

    monkeypatch.setattr(modulo, "CAUDA_ECO_S", 0.05)
    falante = _Falante()
    lp = _loop(falante)
    frame = np.ones((1280, 1), dtype=np.int16)
    estados = []

    def diz(texto):
        lp._on_audio(frame, 1280, None, None)  # eco da própria voz durante a fala
        estados.append(lp._frames.qsize())

    falante.say = diz
    lp._frames.put(frame[:, 0])  # áudio velho de antes
    lp._falar("oi")
    assert estados == [1] and lp._frames.empty() and not lp._speaking.is_set()  # eco não entrou; o velho foi descartado
    lp._on_audio(frame, 1280, None, None)
    assert lp._frames.qsize() == 1  # voltou a ouvir


def test_falha_ao_falar_nao_derruba_a_thread_de_voz():
    lp = _loop(_Falante(quebra=True))
    lp._stop.set()  # sem espera da cauda
    lp._falar("oi")
    lp.speak("oi")
    assert not lp._speaking.is_set()


def test_botao_de_ouvir_interrompe_a_fala():
    falante = _Falante()
    lp = _loop(falante)
    lp.listen_now()
    assert falante.parou == 1 and lp._manual.is_set()
    lp.speaker = object()  # sem stop(): não quebra
    lp.interromper()
