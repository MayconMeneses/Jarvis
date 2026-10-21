"""Fala da Jarvis: voz local offline (Piper) por padrão; edge-tts online opcional; reserva SAPI do Windows.

Nada aqui levanta para quem chamou: se tudo falhar, a Jarvis fica muda e o motivo vai para o log.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import subprocess
import threading
import time

import numpy as np

from jarvis.voice.audio import CHIME_RATE, acabamento, chime_wave  # noqa: F401 - reexportados
from jarvis.voice.cache import FRASES_COMUNS, CacheFrases
from jarvis.voice.reprodutor import Reprodutor
from jarvis.voice.texto import MAX_SPOKEN, clean_for_speech, dividir_para_fala, pausa_ms, split_sentences  # noqa: F401

log = logging.getLogger(__name__)


class EdgeVoice:
    """Voz neural da Microsoft via edge-tts (precisa de internet, sem custo)."""

    sample_rate = 24000

    def __init__(self, voice: str = "pt-BR-FranciscaNeural") -> None:
        self.voice = voice

    def synthesize(self, text: str) -> np.ndarray:
        import edge_tts
        import miniaudio

        async def fetch() -> bytes:
            audio = bytearray()
            async for chunk in edge_tts.Communicate(text, self.voice).stream():
                if chunk["type"] == "audio":
                    audio += chunk["data"]
            return bytes(audio)

        mp3 = asyncio.run(fetch())
        if not mp3:
            raise RuntimeError("edge-tts não retornou áudio")
        decoded = miniaudio.decode(
            mp3, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=self.sample_rate
        )
        return np.frombuffer(decoded.samples, dtype=np.int16)


# Lê o texto da entrada padrão: o texto nunca é montado dentro do comando.
_SAPI_SCRIPT = (
    "Add-Type -AssemblyName System.Speech;"
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    "$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | Select-Object -First 1;"
    "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) };"
    "$s.Speak([Console]::In.ReadToEnd())"
)


def speak_sapi(text: str, registrar=None) -> None:
    """Fala pela voz do Windows. `registrar(proc)` deixa quem chamou encerrar o processo (barge-in)."""
    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _SAPI_SCRIPT],
        stdin=subprocess.PIPE, text=True, encoding="utf-8",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if registrar:
        registrar(proc)
    try:
        proc.communicate(text, timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
    finally:
        if registrar:
            registrar(None)


class Speaker:
    """Fala frase a frase. Ordem: voz local (padrão) -> edge-tts (só se escolhido "online") -> SAPI do Windows."""

    def __init__(self, voice: str = "pt-BR-FranciscaNeural", motor: str = "local", efeito: bool = True,
                 on_visual=None, atraso_ms: int = 80, modelo_local: str = "faber", threads: int = 0) -> None:
        self.edge = EdgeVoice(voice)
        self.local = None
        self.efeito = efeito
        self.modelo_local = modelo_local
        self.threads = threads
        self.on_visual = on_visual  # recebe {"tipo": "fala"|"fim", ...} para o orbe da janela (opcional)
        self.atraso_ms = atraso_ms  # tempo entre mandar o envelope e o som sair de fato
        self.cache = CacheFrases()
        self.ultima_latencia_ms: float | None = None  # pedido de fala -> primeiro áudio saindo
        self._saida = Reprodutor()
        self._parar = threading.Event()
        self._fala = threading.Lock()  # uma fala por vez
        self._sapi: subprocess.Popen | None = None
        self.definir_motor(motor)

    def definir_motor(self, motor: str) -> None:
        """"local" (padrão, offline) ou "online" (edge-tts). Vale já na próxima frase."""
        self.motor = "online" if motor == "online" else "local"
        if self.motor == "local" and self.local is None:
            from jarvis.voice.local import PiperVoice

            self.local = PiperVoice(self.efeito, modelo=self.modelo_local, threads=self.threads)

    @property
    def vozes(self) -> list:
        return [self.edge] if self.motor == "online" else [self.local]

    def preparar(self, on_status=None) -> None:
        """Em segundo plano: baixa a voz local (uma vez), aquece e guarda no cache as frases mais comuns."""
        if self.motor != "local":
            return

        def trabalho() -> None:
            from jarvis.voice.local import baixar_voz, voz_instalada

            for tentativa in (1, 2):  # a 2ª cobre modelo corrompido: o 1º erro apaga os arquivos e baixa de novo
                try:
                    if not voz_instalada(modelo=self.modelo_local):
                        baixar_voz(on_status, modelo=self.modelo_local)
                    self.local.aquecer()
                    break
                except Exception as exc:  # noqa: BLE001
                    log.warning("voz local indisponível (tentativa %d): %s", tentativa, exc)
            else:
                return
            for frase in FRASES_COMUNS:
                if self.motor != "local":
                    break
                try:
                    self._sintetizar(frase)
                except Exception:  # noqa: BLE001
                    log.debug("não consegui pré-sintetizar %r", frase, exc_info=True)
                    break

        threading.Thread(target=trabalho, daemon=True, name="jarvis-voz-local").start()

    def _sintetizar(self, texto: str):
        """(pcm, taxa) pela 1ª voz que funcionar (frases curtas repetidas vêm do cache); levanta se nenhuma funcionar."""
        candidatas = list(self.vozes)
        if self.motor == "local":
            candidatas.append(self.edge)  # reserva online só quando a local falha (ex.: ainda baixando)
        erro: Exception | None = None
        for voz in candidatas:
            chave = (type(voz).__name__, getattr(voz, "modelo", ""), texto)
            if (guardado := self.cache.pegar(chave)) is not None:
                return guardado
            try:
                inicio = time.monotonic()
                pcm, taxa = voz.synthesize(texto), voz.sample_rate
                dur = pcm.size / taxa if taxa else 0
                log.debug("síntese %.2fs para %.2fs de fala (%d caracteres)", time.monotonic() - inicio, dur, len(texto))
                self.cache.guardar(chave, texto, (pcm, taxa))
                return pcm, taxa
            except Exception as exc:  # noqa: BLE001 - onnxruntime, rede, modelo corrompido...
                erro = exc
                log.info("%s indisponível (%s)", type(voz).__name__, exc)
        raise erro or RuntimeError("nenhuma voz disponível")

    def _visual(self, payload: dict) -> None:
        if self.on_visual is None:
            return
        try:
            self.on_visual(payload)
        except Exception:  # o efeito visual nunca pode atrapalhar a fala
            log.debug("falha ao avisar o orbe", exc_info=True)

    def _tocar(self, pcm, taxa: int, t0: float | None) -> bool:
        """Toca uma frase. True se terminou; False se foi interrompida. Levanta se a placa de som não funciona."""
        def ao_comecar() -> None:
            if self.on_visual is not None:
                from jarvis.voice.nivel import JANELA_MS, envelope

                self._visual({"tipo": "fala", "env": envelope(pcm, taxa), "dt": JANELA_MS, "atraso_ms": self.atraso_ms})
            if t0 is not None:
                self.ultima_latencia_ms = (time.monotonic() - t0) * 1000
                log.info("primeiro áudio em %.0f ms", self.ultima_latencia_ms)

        return self._saida.tocar(pcm, taxa, self._parar, ao_comecar)

    def _registrar_sapi(self, proc) -> None:
        self._sapi = proc

    def _falar_sapi(self, texto: str) -> None:
        self._visual({"tipo": "fala", "env": [], "dt": 40, "atraso_ms": 0})  # sem envelope: o orbe simula
        try:
            if not self._parar.is_set():
                speak_sapi(texto, self._registrar_sapi)
        except Exception:  # noqa: BLE001 - sem PowerShell/voz: fica mudo, sem derrubar a thread
            log.exception("a voz do Windows também falhou")

    def say(self, text: str) -> None:
        """A 1ª frase começa enquanto as próximas ainda são sintetizadas. Nunca levanta exceção."""
        with self._fala:
            self._parar.clear()
            try:
                self._dizer(text)
            except Exception:  # noqa: BLE001
                log.exception("falha inesperada ao falar")
            finally:
                self._visual({"tipo": "fim"})

    def _dizer(self, text: str) -> None:
        t0 = time.monotonic()
        parts = dividir_para_fala(clean_for_speech(text))
        if not parts:
            return
        ready: queue.Queue = queue.Queue()
        sem_placa = threading.Event()  # a placa falhou: o resto vai pela voz do Windows, o produtor para

        def produce() -> None:
            for i, part in enumerate(parts):
                if self._parar.is_set() or sem_placa.is_set():
                    break
                try:
                    pcm, taxa = self._sintetizar(part)
                    ready.put(("pcm", i, (acabamento(pcm, taxa, pausa_ms(part)), taxa)))
                except Exception as exc:  # noqa: BLE001 - nada funcionou: voz do Windows no resto
                    log.info("vozes neurais indisponíveis (%s); usando a voz do Windows", exc)
                    ready.put(("sapi", i, None))
                    break
            ready.put(None)

        threading.Thread(target=produce, daemon=True, name="jarvis-sintese").start()
        while (item := ready.get()) is not None:
            tipo, i, dado = item
            if self._parar.is_set() or sem_placa.is_set():
                continue  # esvazia a fila até o produtor terminar
            if tipo == "sapi":
                self._falar_sapi(" ".join(parts[i:]))
                continue
            try:
                self._tocar(dado[0], dado[1], t0 if i == 0 else None)
            except Exception as exc:  # noqa: BLE001 - sem placa de som, driver caiu
                log.warning("não consegui tocar o áudio (%s); tentando a voz do Windows", exc)
                sem_placa.set()
                self._falar_sapi(" ".join(parts[i:]))

    def chime(self) -> None:
        """Bipe curto (~0,2 s) para avisar que a Jarvis começou a ouvir. Sem som disponível, simplesmente não toca."""
        try:
            import sounddevice as sd

            sd.play(chime_wave(), CHIME_RATE)
            sd.wait()
        except Exception:  # noqa: BLE001
            log.debug("bipe indisponível", exc_info=True)

    def stop(self) -> None:
        """Interrompe a fala na hora (barge-in): corta o som, encerra a voz do Windows e avisa o orbe."""
        self._parar.set()
        proc = self._sapi
        if proc is not None:
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001
                log.debug("não consegui encerrar a voz do Windows", exc_info=True)
        self._visual({"tipo": "fim"})
