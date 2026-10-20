"""Níveis de som para o orbe da janela: envelope da fala, nível do microfone e limitador de taxa.

Funções puras (sem janela, sem placa de som), para poderem ser testadas com áudio sintético.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import numpy as np

JANELA_MS = 40  # 25 valores por segundo de fala: ~500 bytes para uma frase de 5 s


def envelope(pcm, taxa: int, janela_ms: int = JANELA_MS) -> list[int]:
    """RMS a cada `janela_ms`, normalizado pelo percentil 95 e comprimido, em inteiros de 0 a 100."""
    bruto = np.asarray(pcm)
    if bruto.size == 0 or taxa <= 0:
        return []
    x = bruto.astype(np.float32)
    if np.issubdtype(bruto.dtype, np.integer):
        x = x / 32768.0
    passo = max(1, int(taxa * janela_ms / 1000))
    falta = (-x.size) % passo
    if falta:
        x = np.pad(x, (0, falta))
    rms = np.sqrt(np.mean(x.reshape(-1, passo) ** 2, axis=1))
    ref = float(np.percentile(rms, 95))
    if ref < 1e-4:  # silêncio
        return [0] * len(rms)
    valor = np.minimum(1.0, (rms / ref) ** 0.7)
    valor[rms < 0.02 * ref] = 0.0
    return [int(round(v * 100)) for v in valor]


def nivel_mic(rms: float, piso: float) -> float:
    """Volume do microfone entre 0 e 1, descontado o ruído de fundo medido (`piso`)."""
    baixo = max(piso, 1.0) * 1.2
    alto = max(piso * 10.0, 2500.0)
    if rms <= baixo:
        return 0.0
    return round(min(1.0, (rms - baixo) / (alto - baixo)), 2)


class LimitadorTaxa:
    """Deixa passar no máximo `hz` envios por segundo."""

    def __init__(self, hz: float = 20.0, relogio: Callable[[], float] = time.monotonic) -> None:
        self._intervalo = 1.0 / hz
        self._relogio = relogio
        self._ultimo = -1e9

    def permite(self) -> bool:
        agora = self._relogio()
        if agora - self._ultimo >= self._intervalo:
            self._ultimo = agora
            return True
        return False
