"""Gravação do comando por energia do som (sem microfone aqui: lógica pura, testável com áudio sintético)."""

from __future__ import annotations

from collections import deque

import numpy as np

from jarvis.voice.stt import SAMPLE_RATE

FRAME = 1280  # 80 ms a 16 kHz, o tamanho que o openWakeWord espera


class Recorder:
    """Decide quando a fala começou e terminou, pela energia do som.

    Lógica pura (sem microfone) para poder ser testada com áudio sintético.
    """

    def __init__(self, noise_floor: float, silence_s: float = 0.9,
                 max_s: float = 15.0, no_speech_s: float = 4.0) -> None:
        self.threshold = max(noise_floor * 3.0, 400.0)
        self.frames: list[np.ndarray] = []
        self.speech_started = False
        self.loud = 0  # quadros com voz
        self.done = False
        self._silent = 0
        self._silence_frames = int(silence_s * SAMPLE_RATE / FRAME)
        self._max_frames = int(max_s * SAMPLE_RATE / FRAME)
        self._no_speech_frames = int(no_speech_s * SAMPLE_RATE / FRAME)

    def feed(self, frame: np.ndarray) -> bool:
        """Retorna True quando a gravação deve terminar."""
        self.frames.append(frame)
        loud = rms(frame) > self.threshold
        if loud:
            self.loud += 1
            self.speech_started = True
            self._silent = 0
        elif self.speech_started:
            self._silent += 1
        self.done = ((not self.speech_started and len(self.frames) >= self._no_speech_frames)
                     or self._silent >= self._silence_frames or len(self.frames) >= self._max_frames)
        return self.done

    def audio(self) -> np.ndarray:
        if not self.speech_started:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self.frames).astype(np.float32) / 32768.0


def rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2))) if frame.size else 0.0


class PreRoll:
    """Últimos instantes de áudio (só na memória, nunca em disco): o que veio antes de a palavra de ativação disparar."""

    def __init__(self, frames: int = 12) -> None:  # 12 x 80 ms ~ 1 s
        self._buf: deque[np.ndarray] = deque(maxlen=max(1, frames))

    def add(self, frame: np.ndarray) -> None:
        self._buf.append(frame)

    def take(self) -> list[np.ndarray]:
        out = list(self._buf)
        self._buf.clear()
        return out
