"""Ciclo de voz: "Hey Jarvis" (ou botão) → gravar → transcrever → responder → falar.

Roda numa thread própria. Enquanto a Jarvis fala ou pensa, o microfone é
ignorado para ela não ouvir a si mesma.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable

import numpy as np

from jarvis.voice.stt import SAMPLE_RATE, Transcriber

log = logging.getLogger(__name__)

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
        self._silent = 0
        self._silence_frames = int(silence_s * SAMPLE_RATE / FRAME)
        self._max_frames = int(max_s * SAMPLE_RATE / FRAME)
        self._no_speech_frames = int(no_speech_s * SAMPLE_RATE / FRAME)

    def feed(self, frame: np.ndarray) -> bool:
        """Retorna True quando a gravação deve terminar."""
        self.frames.append(frame)
        loud = rms(frame) > self.threshold
        if loud:
            self.speech_started = True
            self._silent = 0
        elif self.speech_started:
            self._silent += 1
        if not self.speech_started and len(self.frames) >= self._no_speech_frames:
            return True
        return self._silent >= self._silence_frames or len(self.frames) >= self._max_frames

    def audio(self) -> np.ndarray:
        if not self.speech_started:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self.frames).astype(np.float32) / 32768.0


def rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2))) if frame.size else 0.0


class VoiceLoop(threading.Thread):
    def __init__(
        self,
        respond: Callable[[str], dict],
        notify: Callable[[dict], None],
        speaker,
        transcriber: Transcriber,
        sensitivity: float = 0.5,
        speak_answers: bool = True,
    ) -> None:
        super().__init__(daemon=True, name="jarvis-voz")
        self.respond = respond
        self.notify = notify
        self.speaker = speaker
        self.transcriber = transcriber
        self.sensitivity = sensitivity
        self.speak_answers = speak_answers
        self.paused = threading.Event()
        self._manual = threading.Event()
        self._stop = threading.Event()
        self._speaking = threading.Event()
        self._frames: queue.Queue[np.ndarray] = queue.Queue(maxsize=200)
        self._noise = 300.0

    # chamados pela janela/bandeja
    def listen_now(self) -> None:
        self._manual.set()

    def set_paused(self, paused: bool) -> None:
        (self.paused.set if paused else self.paused.clear)()
        self.notify({"status": "Escuta pausada" if paused else "Diga “Hey Jarvis”"})

    def stop(self) -> None:
        self._stop.set()

    def speak(self, text: str) -> None:
        """Fala por iniciativa própria (ex.: saudação) sem ouvir a si mesma."""
        self._speaking.set()
        try:
            self.speaker.say(text)
        except Exception:
            log.exception("falha ao falar")
        finally:
            self._drain()
            self._speaking.clear()

    # ── thread ───────────────────────────────────────────────────────────
    def run(self) -> None:
        try:
            import sounddevice as sd
            from openwakeword.model import Model

            self.notify({"status": "Preparando a voz…"})
            wake = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            self.transcriber.warm_up()
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                blocksize=FRAME, callback=self._on_audio):
                self.notify({"status": "Diga “Hey Jarvis”"})
                self._listen(wake)
        except Exception as exc:
            log.exception("voz indisponível")
            self.notify({"status": f"Voz indisponível: {exc}"})

    def _on_audio(self, data, _frames, _time, _status) -> None:
        try:
            self._frames.put_nowait(data[:, 0].copy())
        except queue.Full:
            pass  # pensando ou falando: áudio descartado

    def _next_frame(self) -> np.ndarray | None:
        try:
            return self._frames.get(timeout=0.5)
        except queue.Empty:
            return None

    def _drain(self) -> None:
        while not self._frames.empty():
            self._frames.get_nowait()

    def _listen(self, wake) -> None:
        while not self._stop.is_set():
            frame = self._next_frame()
            if frame is None:
                continue
            if self._speaking.is_set():
                continue  # falando a saudação: não ouvir a própria voz
            manual = self._manual.is_set()  # o botão funciona mesmo com a escuta pausada
            if self.paused.is_set() and not manual:
                continue
            self._noise = 0.95 * self._noise + 0.05 * rms(frame)
            if manual or max(wake.predict(frame).values()) >= self.sensitivity:
                self._manual.clear()
                self._handle_turn()
                wake.reset()
                self._drain()
                if not self.paused.is_set():
                    self.notify({"status": "Diga “Hey Jarvis”"})

    def _handle_turn(self) -> None:
        # Não descarta a fila aqui: ela já tem o começo da frase dita logo após "Hey Jarvis".
        self.notify({"status": "Ouvindo…", "listening": True})
        recorder = Recorder(self._noise)
        empty_waits = 0
        while not self._stop.is_set():
            frame = self._next_frame()
            if frame is None:
                empty_waits += 1
                if empty_waits >= 10:  # 5 s sem áudio: microfone parou
                    break
                continue
            empty_waits = 0
            if recorder.feed(frame):
                break
        self.notify({"status": "Transcrevendo…", "listening": False})
        text = self.transcriber.transcribe(recorder.audio())
        if not text:
            self.notify({"status": "Não entendi. Tente de novo."})
            return
        self.notify({"user": text, "status": "Pensando…"})
        result = self.respond(text)
        self.notify({"answer": result})
        if self.speak_answers:
            self.notify({"status": "Falando…"})
            self.speaker.say(result.get("text") or "Não consegui responder agora.")
