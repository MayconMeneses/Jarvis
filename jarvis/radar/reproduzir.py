"""Tocar o áudio do boletim sob comando ("ouvir radar") e parar. Nunca toca sozinho."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def ultimo_audio(base: Path) -> Path | None:
    """O boletim.wav mais recente (pasta com data mais nova)."""
    achados = sorted(base.glob("*/boletim.wav")) if base.exists() else []
    return max(achados, key=lambda p: p.stat().st_mtime) if achados else None


def tocar(caminho: Path, sd=None) -> float:
    """Começa a tocar sem travar a conversa. Devolve a duração em segundos."""
    if sd is None:
        import sounddevice as sd  # noqa: PLC0415 (só quando o usuário pede para ouvir)
    with wave.open(str(caminho)) as w:
        taxa, quadros = w.getframerate(), w.readframes(w.getnframes())
    pcm = np.frombuffer(quadros, dtype="<i2")
    sd.play(pcm, taxa)
    return len(pcm) / float(taxa)


def parar(sd=None) -> None:
    if sd is None:
        import sounddevice as sd  # noqa: PLC0415
    sd.stop()
