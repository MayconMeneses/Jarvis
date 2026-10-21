"""Voz local (Piper): download com SHA-256, interface igual à da EdgeVoice e ordem das reservas no Speaker."""

import hashlib

import numpy as np
import pytest

from jarvis.voice import local, tts


def _falso_baixar(conteudos):
    def baixar(url, destino, on_status=None):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudos[destino.name])
    return baixar


def _trocar_hashes(monkeypatch, conteudos):
    monkeypatch.setattr(local, "ARQUIVOS", {n: hashlib.sha256(c).hexdigest() for n, c in conteudos.items()})


def test_baixa_confere_sha_e_reaproveita(tmp_path, monkeypatch):
    conteudos = {"a.onnx": b"modelo", "a.onnx.json": b"{}"}
    _trocar_hashes(monkeypatch, conteudos)
    chamadas = []
    base = _falso_baixar(conteudos)
    local.baixar_voz(pasta=tmp_path, baixar=lambda *a: (chamadas.append(a[1].name), base(*a)))
    assert sorted(chamadas) == ["a.onnx", "a.onnx.json"]
    chamadas.clear()
    local.baixar_voz(pasta=tmp_path, baixar=lambda *a: chamadas.append(a))
    assert chamadas == []  # já estava lá, não baixa de novo
    assert local.voz_instalada(tmp_path)


def test_voz_embutida_no_instalador_e_copiada_sem_baixar(tmp_path, monkeypatch):
    conteudos = {"a.onnx": b"modelo", "a.onnx.json": b"{}"}
    _trocar_hashes(monkeypatch, conteudos)
    embutida = tmp_path / "app"
    embutida.mkdir()
    for nome, c in conteudos.items():
        (embutida / nome).write_bytes(c)
    local.baixar_voz(pasta=tmp_path / "dados", baixar=lambda *a: pytest.fail("não deveria baixar"), embutida=embutida)
    assert local.voz_instalada(tmp_path / "dados")


def test_download_corrompido_e_recusado_e_apagado(tmp_path, monkeypatch):
    _trocar_hashes(monkeypatch, {"a.onnx": b"certo"})
    with pytest.raises(RuntimeError, match="SHA-256"):
        local.baixar_voz(pasta=tmp_path, baixar=_falso_baixar({"a.onnx": b"errado"}))
    assert not (tmp_path / "a.onnx").exists()


def test_voz_nao_instalada_levanta_erro_claro(tmp_path):
    with pytest.raises(RuntimeError, match="não foi baixada"):
        local.PiperVoice(pasta=tmp_path).synthesize("oi")


def test_piper_devolve_int16_e_aplica_reverb_sem_mudar_tamanho(tmp_path, monkeypatch):
    class Trecho:
        audio_int16_array = (3000 * np.sin(np.arange(2205) / 5)).astype(np.int16)

    class Falsa:
        class config:
            sample_rate = 22050

        def synthesize(self, texto):
            return [Trecho(), Trecho()]

    voz = local.PiperVoice(efeito=True, pasta=tmp_path)
    voz._voz = Falsa()
    monkeypatch.setattr(local, "voz_instalada", lambda pasta=None: True)
    pcm = voz.synthesize("teste")
    assert pcm.dtype == np.int16 and pcm.size == 4410 + 3087 + 1323 and voz.sample_rate == 22050
    seco = local.PiperVoice(efeito=False, pasta=tmp_path)
    seco._voz = Falsa()
    assert not np.array_equal(pcm, seco.synthesize("teste"))


def test_reverb_nao_estoura_o_volume_e_nao_corta_o_eco():
    pcm = np.full(5000, 32000, dtype=np.int16)
    saida = local.com_reverb_discreto(pcm, 22050)
    assert np.abs(saida).max() <= 32000
    assert saida.size == 5000 + 1323 and np.abs(saida[5000:5000 + 500]).max() > 0  # o eco continua depois do fim da fala


class _Voz:
    def __init__(self, ok, taxa=1000):
        self.ok, self.sample_rate, self.chamadas = ok, taxa, 0

    def synthesize(self, texto):
        self.chamadas += 1
        if not self.ok:
            raise RuntimeError("fora")
        return np.zeros(10, dtype=np.int16)


def test_speaker_local_e_o_padrao_e_edge_so_reserva():
    s = tts.Speaker()
    assert s.motor == "local" and s.vozes == [s.local]
    s.local, s.edge = _Voz(True, 22050), _Voz(True, 24000)
    assert s._sintetizar("oi")[1] == 22050 and s.edge.chamadas == 0
    s.local.ok = False  # ex.: voz ainda baixando
    assert s._sintetizar("outra")[1] == 24000


def test_speaker_online_nao_toca_na_voz_local():
    s = tts.Speaker(motor="online")
    assert s.motor == "online" and s.vozes == [s.edge] and s.local is None
    s.edge = _Voz(True)
    assert s._sintetizar("oi")[1] == 1000


def test_speaker_sem_nenhuma_voz_levanta_para_cair_no_sapi():
    s = tts.Speaker()
    s.local, s.edge = _Voz(False), _Voz(False)
    with pytest.raises(RuntimeError):
        s._sintetizar("oi")


def test_config_padrao_usa_voz_local():
    from jarvis.config import VoiceConfig
    assert VoiceConfig().voz_motor == "local"
