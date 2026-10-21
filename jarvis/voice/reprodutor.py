"""Saída de som contínua (uma OutputStream por fala): sem falha entre frases e com parada limpa (barge-in).

Se a placa some ou o dispositivo muda (ex.: fone Bluetooth desligou), reenumera os dispositivos e tenta mais uma vez.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

log = logging.getLogger(__name__)

BLOCO_MS = 40  # a cada bloco confere o pedido de parada: a Jarvis cala em ~40 ms + latência da placa


class Reprodutor:
    def __init__(self) -> None:
        self._sd = None
        self._fluxo = None
        self._taxa = 0

    def _modulo(self):
        if self._sd is None:
            import sounddevice as sd

            self._sd = sd
        return self._sd

    def _reiniciar_portaudio(self) -> None:
        """Reenumera os dispositivos (a lista fica velha quando o Bluetooth conecta/desconecta)."""
        sd = self._modulo()
        try:
            self.fechar()
            sd._terminate()
            sd._initialize()
        except Exception:  # noqa: BLE001 - API privada do sounddevice; se mudar, só tentamos de novo
            log.debug("não consegui reiniciar o PortAudio", exc_info=True)

    def _abrir(self, taxa: int) -> None:
        if self._fluxo is not None and self._taxa == taxa:
            return
        self.fechar()
        fluxo = self._modulo().OutputStream(samplerate=taxa, channels=1, dtype="int16", latency="low")
        fluxo.start()
        self._fluxo, self._taxa = fluxo, taxa

    def fechar(self) -> None:
        fluxo, self._fluxo, self._taxa = self._fluxo, None, 0
        if fluxo is not None:
            try:
                fluxo.close()
            except Exception:  # noqa: BLE001
                log.debug("falha ao fechar a saída de som", exc_info=True)

    def tocar(self, pcm: np.ndarray, taxa: int, parar: threading.Event, ao_comecar=None) -> bool:
        """Toca e bloqueia até o fim. True se terminou, False se `parar` foi pedido. Levanta se a placa não funcionar."""
        for tentativa in (1, 2):
            try:
                self._abrir(taxa)
                if ao_comecar is not None:
                    ao_comecar()
                    ao_comecar = None
                return self._escrever(pcm, taxa, parar)
            except Exception as exc:  # noqa: BLE001 - PortAudioError varia por driver
                if parar.is_set():
                    return False
                log.warning("saída de som falhou (%s)%s", exc, "; reenumerando dispositivos" if tentativa == 1 else "")
                if tentativa == 2:
                    self.fechar()
                    raise
                self._reiniciar_portaudio()
        return False

    def _escrever(self, pcm: np.ndarray, taxa: int, parar: threading.Event) -> bool:
        bloco = max(1, int(taxa * BLOCO_MS / 1000))
        for i in range(0, pcm.size, bloco):
            if parar.is_set():
                self._cortar()
                return False
            self._fluxo.write(pcm[i:i + bloco].reshape(-1, 1))
        return True

    def _cortar(self) -> None:
        """Descarta o que ainda está no buffer da placa (calar na hora)."""
        try:
            self._fluxo.abort()
            self._fluxo.start()
        except Exception:  # noqa: BLE001
            self.fechar()
