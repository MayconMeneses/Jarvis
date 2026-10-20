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

from jarvis.agentes import registro as agentes
from jarvis.voice.nivel import LimitadorTaxa, nivel_mic
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
        self._mostrar_mic = threading.Event()  # ligado só enquanto grava a fala (o orbe "ouve")
        self._nivel_mic: queue.Queue[float] = queue.Queue(maxsize=1)

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
            threading.Thread(target=self._enviar_nivel_mic, daemon=True, name="jarvis-visual").start()
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                blocksize=FRAME, callback=self._on_audio):
                self.notify({"status": "Diga “Hey Jarvis”"})
                agentes.marcar("voz", agentes.OK, "escutando")
                self._listen(wake)
            agentes.marcar("voz", agentes.DESLIGADO, "parada")
        except Exception as exc:
            agentes.erro("voz", exc)
            log.exception("voz indisponível")
            self.notify({"status": f"Voz indisponível: {exc}"})

    def _on_audio(self, data, _frames, _time, _status) -> None:
        frame = data[:, 0].copy()
        try:
            self._frames.put_nowait(frame)
        except queue.Full:
            pass  # pensando ou falando: áudio descartado
        if self._mostrar_mic.is_set():  # fila de tamanho 1; nada de janela/IPC aqui dentro
            try:
                self._nivel_mic.get_nowait()
            except queue.Empty:
                pass
            try:
                self._nivel_mic.put_nowait(nivel_mic(rms(frame), self._noise))
            except queue.Full:
                pass

    def _enviar_nivel_mic(self) -> None:
        """Thread própria: manda o volume do microfone ao orbe a ~20 Hz, fora do callback de áudio."""
        limite = LimitadorTaxa(20.0)
        while not self._stop.is_set():
            try:
                nivel = self._nivel_mic.get(timeout=0.25)
            except queue.Empty:
                continue
            if self._mostrar_mic.is_set() and limite.permite():
                self.notify({"tipo": "mic", "n": nivel})

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
        self.notify({"status": "Ouvindo…", "listening": True})
        if hasattr(self.speaker, "chime"):
            try:
                self.speaker.chime()  # avisa na hora que está ouvindo
            except Exception:
                log.debug("não foi possível tocar o bipe", exc_info=True)
            self._drain()  # descarta só o próprio bipe; a pessoa fala depois dele
        recorder = Recorder(self._noise)
        empty_waits = 0
        self._mostrar_mic.set()
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
        self._mostrar_mic.clear()
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
