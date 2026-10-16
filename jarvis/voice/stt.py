"""Transcrição local com faster-whisper (CPU, int8). Nada de áudio sai do PC.

Medido neste PC (frases com ruído de sala): "base" errava ~60% das palavras e
"small" com vocabulário ~11%, ao custo de ~4 s a mais por frase.
"""

from __future__ import annotations

import os
import threading

import numpy as np

SAMPLE_RATE = 16000
# Palavras que a Jarvis ouve com frequência e o modelo costuma errar.
BASE_VOCABULARY = ["Jarvis", "Claude", "Obsidian", "Gmail", "Outlook", "e-mail", "vagas",
                   "projeto", "memória RAM", "notícias", "clima"]


def vocabulary_hint(user_name: str = "", city: str = "", projects=()) -> str:
    words = [w for w in [user_name, city.split(",")[0], *projects] if w] + BASE_VOCABULARY
    return ", ".join(dict.fromkeys(words)) + "."


class Transcriber:
    def __init__(self, model_size: str = "small", hint: str = "", on_status=None) -> None:
        self.model_size = model_size
        self.on_status = on_status  # avisa a janela quando o modelo precisa ser baixado
        self.hint = hint or vocabulary_hint()
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                from jarvis.voice import models

                path = models.resolve_whisper(self.model_size, self.on_status)
                threads = max(1, (os.cpu_count() or 2) // 2)  # núcleos físicos
                self._model = WhisperModel(path, device="cpu", compute_type="int8",
                                           cpu_threads=threads)
        return self._model

    def warm_up(self) -> None:
        self._load()

    def transcribe(self, audio: np.ndarray) -> str:
        """audio: float32 mono 16 kHz entre -1 e 1."""
        if audio.size < SAMPLE_RATE // 4:
            return ""
        segments, _ = self._load().transcribe(
            audio.astype(np.float32, copy=False), language="pt", beam_size=1,
            initial_prompt=self.hint, vad_filter=True,
            without_timestamps=True, condition_on_previous_text=False,
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return "" if is_hallucination(text, audio.size / SAMPLE_RATE) else text


# Frases que o Whisper "inventa" em silêncio ou ruído (vêm de legendas de vídeos).
_HALLUCINATIONS = ("amara.org", "inscreva-se", "legendas pela", "legendado por", "transcrição por")
_SHORT_FILLERS = {"obrigado", "obrigada", "tchau", "valeu", "e aí", "ok", "hum"}


def is_hallucination(text: str, seconds: float) -> bool:
    low = text.lower().strip(" .!?…")
    if any(h in low for h in _HALLUCINATIONS):
        return True
    return seconds < 1.5 and low in _SHORT_FILLERS
