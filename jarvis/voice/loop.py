"""Ciclo de voz: "Hey Jarvis" (ou botão) → gravar → transcrever → responder → falar.

Roda numa thread própria; enquanto ela fala ou pensa, o microfone é ignorado.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable

import numpy as np

from jarvis.agentes import registro as agentes
from jarvis.voice.ativacao import (FALANDO, OUVINDO, PROCESSANDO, LimitadorTranscricao, Segmentador, estado_base,
                                   extrair_comando)
from jarvis.voice.chamada import LimitadorAtivacao, extrair_chamada, responder_saudacao
from jarvis.voice.gravador import FRAME, PreRoll, Recorder, rms  # noqa: F401  (FRAME/Recorder também importados daqui)
from jarvis.voice.nivel import LimitadorTaxa, nivel_mic
from jarvis.voice.stt import SAMPLE_RATE, Transcriber

log = logging.getLogger(__name__)

CAUDA_ECO_S = 0.35  # depois de falar, espera o eco da sala morrer antes de voltar a ouvir


class VoiceLoop(threading.Thread):
    def __init__(
        self,
        respond: Callable[[str], dict],
        notify: Callable[[dict], None],
        speaker,
        transcriber: Transcriber,
        sensitivity: float = 0.5,
        speak_answers: bool = True,
        por_texto: bool = True,
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
        self.por_texto_permitido = por_texto  # config voz.ativacao_por_texto
        self._por_texto = threading.Event()   # "Jarvis, ..." lido na transcrição: só ligado no modo foco
        self._pre = PreRoll()
        self._limite = LimitadorTranscricao()
        self._limite_chamadas = LimitadorAtivacao()  # ativações por texto por minuto
        self.estado = estado_base(False, ligado=False)  # o que o botão do microfone mostra

    def _estado(self, estado: str) -> None:
        self.estado = estado
        self.notify({"escuta": estado})

    def _base(self) -> None:
        self._estado(estado_base(self.paused.is_set()))

    def set_por_texto(self, ligado: bool) -> None:
        (self._por_texto.set if ligado and self.por_texto_permitido else self._por_texto.clear)()

    # chamados pela janela/bandeja
    def listen_now(self) -> None:
        self.interromper()  # apertar o botão enquanto ela fala também a faz calar
        self._manual.set()

    def interromper(self) -> None:
        """Barge-in: corta a fala em andamento (o som para em ~40 ms)."""
        stop = getattr(self.speaker, "stop", None)
        if stop is not None:
            try:
                stop()
            except Exception:
                log.debug("falha ao interromper a fala", exc_info=True)

    def set_paused(self, paused: bool) -> None:
        (self.paused.set if paused else self.paused.clear)()
        self._base()
        self.notify({"status": "Escuta pausada" if paused else "Diga “Jarvis” e o comando"})

    def stop(self) -> None:
        self._stop.set()

    def speak(self, text: str) -> None:
        """Fala por iniciativa própria (ex.: saudação) sem ouvir a si mesma."""
        self._falar(text)

    def _falar(self, text: str) -> None:
        """Toda fala passa por aqui: o microfone é ignorado durante e um instante depois, e o áudio velho é descartado."""
        self._speaking.set()
        self._estado(FALANDO)
        try:
            self.speaker.say(text)
        except Exception:
            log.exception("falha ao falar")
        finally:
            self._stop.wait(CAUDA_ECO_S)  # eco da sala; sai mais cedo se o app está fechando
            self._drain()
            self._speaking.clear()
            self._base()

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
                self.notify({"status": "Diga “Jarvis” e o comando"})
                self._base()
                agentes.marcar("voz", agentes.OK, "escutando")
                self._listen(wake)
            agentes.marcar("voz", agentes.DESLIGADO, "parada")
            self._estado(estado_base(True))
        except Exception as exc:
            agentes.erro("voz", exc)
            log.exception("voz indisponível")
            self.notify({"status": f"Voz indisponível: {exc}"})
            self._estado(estado_base(True))

    def _on_audio(self, data, _frames, _time, _status) -> None:
        if self._speaking.is_set():
            return  # a Jarvis está falando: nada do que o microfone pega (o eco dela) entra na fila
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
        while True:
            try:
                self._frames.get_nowait()
            except queue.Empty:
                return

    def _listen(self, wake) -> None:
        seg = Segmentador(self._noise)
        while not self._stop.is_set():
            frame = self._next_frame()
            if frame is None:
                continue
            manual = self._manual.is_set()  # o botão funciona mesmo com a escuta pausada
            if self._speaking.is_set() or (self.paused.is_set() and not manual):
                seg.reiniciar()  # falando (não ouvir a própria voz) ou pausada
                continue
            energia = rms(frame)
            self._noise = 0.95 * self._noise + 0.05 * energia
            self._pre.add(frame)
            if manual or max(wake.predict(frame).values()) >= self.sensitivity:
                self._manual.clear()
                self._turno(manual)
                wake.reset()
                seg.reiniciar()
            elif self._por_texto.is_set():
                seg.limiar = max(self._noise * 3.0, 400.0)
                if self._chamada_por_texto(seg.feed(frame, energia)):
                    wake.reset()
                    seg.reiniciar()

    def _chamada_por_texto(self, audio) -> bool:
        """Transcreve uma frase ouvida ao fundo; só age se ela chama "Jarvis" (no começo ou, em frase curta, no fim). O texto não é guardado."""
        if audio is None or not self._limite.permite():
            return False
        comando = extrair_chamada(self.transcriber.transcribe(audio))
        if comando is None or not self._limite_chamadas.permite():
            return False
        self._turno_com_comando(comando)
        return True

    def _turno(self, manual: bool) -> None:
        """Palavra de ativação ou botão. Se o comando veio na mesma frase ("Hey Jarvis, que horas são"), usa-o direto."""
        self._turno_com_comando("" if manual else self._comando_na_frase(self._pre.take()))

    def _turno_com_comando(self, comando: str) -> None:
        self._pre.take()
        saudacao = responder_saudacao(comando) if comando else None
        if saudacao:  # "oi", "boa noite": cumprimento puro nunca fica sem resposta, e não gasta IA
            self._responder_pronto(comando, saudacao)
        elif comando:
            self._responder(comando)
        else:
            self._handle_turn()
        self._drain()
        if not self.paused.is_set():
            self.notify({"status": "Diga “Jarvis” e o comando"})
        self._base()

    def _comando_na_frase(self, semente: list) -> str:
        """Continua gravando a frase em que a palavra de ativação disparou e devolve o que veio depois do nome."""
        self._estado(OUVINDO)
        rec = Recorder(self._noise)
        for f in semente:  # o áudio de antes do disparo (só na memória)
            if rec.feed(f):
                break
        antes, vazios = rec.loud, 0
        while not self._stop.is_set() and not rec.done:
            f = self._next_frame()
            if f is None:
                vazios += 1
                if vazios >= 10:
                    break
                continue
            vazios = 0
            rec.feed(f)
        if rec.loud - antes < 4:  # nada além do nome: só chamou
            return ""
        self._estado(PROCESSANDO)
        audio = rec.audio()
        comando = extrair_comando(self.transcriber.transcribe(audio))
        if comando is None:  # o modelo disparou mas a transcrição não trouxe o nome
            return ""
        return comando

    def _handle_turn(self) -> None:
        self.notify({"status": "Ouvindo…", "listening": True})
        self._estado(OUVINDO)
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
        self._estado(PROCESSANDO)
        text = self.transcriber.transcribe(recorder.audio())
        if not text:
            self.notify({"status": "Não entendi. Tente de novo."})
            return
        self._responder(text)

    def _responder_pronto(self, pedido: str, resposta: str) -> None:
        """Responde sem IA (saudação pura): mostra e fala."""
        self.notify({"user": pedido})
        self.notify({"answer": {"text": resposta, "falado": resposta, "brain": "local"}})
        if self.speak_answers:
            self._falar(resposta)

    def _responder(self, text: str) -> None:
        self.notify({"user": text, "status": "Pensando…"})
        self._estado(PROCESSANDO)
        result = self.respond(text)
        self.notify({"answer": result})
        if self.speak_answers:
            self.notify({"status": "Falando…"})
            self._falar(result.get("falado") or result.get("text") or "Não consegui responder agora.")
