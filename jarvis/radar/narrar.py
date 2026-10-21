"""Roteiro → arquivo de áudio (.wav) com a voz local da Jarvis (Piper), reserva SAPI do Windows. Tudo offline.

O áudio é gerado e GUARDADO; tocar é sempre sob comando ("ouvir radar"). WAV com a stdlib, sem ffmpeg.
Não usa clean_for_speech (que corta em 600 caracteres): o boletim inteiro é falado, frase por frase.
"""

from __future__ import annotations

import os
import wave
from pathlib import Path

import numpy as np

from jarvis import proc as processos
from jarvis.voice import tts

PAUSA_S = 0.30  # silêncio entre frases
_SAPI = ("[Console]::InputEncoding = [System.Text.Encoding]::UTF8; Add-Type -AssemblyName System.Speech; "
         "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.SetOutputToWaveFile($env:JARVIS_WAV); "
         "$s.Speak([Console]::In.ReadToEnd()); $s.Dispose()")


def duracao_s(pcm: np.ndarray, taxa: int) -> float:
    return len(pcm) / float(taxa)


def sintetizar(texto: str, voz, progresso=None) -> tuple[np.ndarray, int]:
    """Frase por frase (cada uma é uma chamada de síntese), com uma pausa curta entre elas."""
    frases = tts.split_sentences(texto, min_chars=60)
    if not frases:
        raise ValueError("o roteiro está vazio")
    partes = []
    for n, frase in enumerate(frases, 1):
        partes.append(np.asarray(voz.synthesize(frase), dtype=np.int16))
        partes.append(np.zeros(int(voz.sample_rate * PAUSA_S), dtype=np.int16))
        if progresso:
            progresso(n, len(frases))
    return np.concatenate(partes[:-1]), int(voz.sample_rate)


def gravar_wav(caminho: Path, pcm: np.ndarray, taxa: int) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(np.asarray(pcm, dtype="<i2").tobytes())
    return caminho


def sapi_para_arquivo(texto: str, destino: Path, rodar=processos.executar) -> Path:
    """Reserva sem Piper: voz do Windows gravando direto em .wav. O texto vai pela entrada padrão, nunca no comando."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    rodar(["powershell", "-NoProfile", "-NonInteractive", "-Command", _SAPI], input=texto, text=True, encoding="utf-8",
          timeout=600, env={**os.environ, "JARVIS_WAV": str(destino)}, check=True)
    if not destino.exists() or destino.stat().st_size < 1000:
        raise RuntimeError("a voz do Windows não gerou o áudio")
    return destino


def voz_local(efeito: bool = True):
    from jarvis.voice import local

    if not local.voz_instalada():
        raise RuntimeError("a voz local (Piper) ainda não está instalada")
    return local.PiperVoice(efeito=efeito)


def narrar(texto: str, destino: Path, voz=None, progresso=None, sapi=sapi_para_arquivo) -> dict:
    """Gera o .wav. Piper se estiver instalado; senão a voz do Windows. Devolve {caminho, duracao_s, motor}."""
    try:
        voz = voz or voz_local()
        pcm, taxa = sintetizar(texto, voz, progresso)
        gravar_wav(destino, pcm, taxa)
        return {"caminho": str(destino), "duracao_s": duracao_s(pcm, taxa), "motor": "piper"}
    except (RuntimeError, ImportError):
        sapi(texto, destino)
        with wave.open(str(destino)) as w:
            return {"caminho": str(destino), "duracao_s": w.getnframes() / float(w.getframerate()), "motor": "windows"}
