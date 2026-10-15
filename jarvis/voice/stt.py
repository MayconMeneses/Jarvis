"""Transcrição local com faster-whisper (CPU, int8). Nada de áudio sai do PC."""

from __future__ import annotations

import threading

import numpy as np

SAMPLE_RATE = 16000


class Transcriber:
    def __init__(self, model_size: str = "base", user_name: str = "") -> None:
        self.model_size = model_size
        # Ajuda o modelo a acertar nomes próprios que aparecem com frequência.
        self.hint = f"Jarvis, {user_name}." if user_name else "Jarvis."
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model

    def warm_up(self) -> None:
        self._load()

    def transcribe(self, audio: np.ndarray) -> str:
        """audio: float32 mono 16 kHz entre -1 e 1."""
        if audio.size < SAMPLE_RATE // 4:
            return ""
        segments, _ = self._load().transcribe(
            audio, language="pt", beam_size=1, initial_prompt=self.hint, vad_filter=True
        )
        return " ".join(s.text.strip() for s in segments).strip()
