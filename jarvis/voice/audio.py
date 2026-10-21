"""Acabamento do áudio falado: volume parelho, entrada/saída sem estalo, pausas e o bipe de "estou ouvindo".

Funções puras sobre arrays (int16 ou float), testáveis sem placa de som.
"""

from __future__ import annotations

import numpy as np

CHIME_RATE = 24000
RMS_ALVO = 0.11     # ~ -19 dBFS: volume de fala confortável
PICO_MAX = 0.89     # ~ -1 dBFS: folga contra clipping no conversor
GANHO_MIN, GANHO_MAX = 0.25, 3.0


def nivelar(pcm: np.ndarray, rms_alvo: float = RMS_ALVO, pico_max: float = PICO_MAX) -> np.ndarray:
    """Leva a fala ao mesmo volume médio (RMS) sem passar do pico. Silêncio fica como está. Devolve float32."""
    x = pcm.astype(np.float32) / 32768.0 if np.issubdtype(pcm.dtype, np.integer) else pcm.astype(np.float32)
    pico = float(np.abs(x).max()) if x.size else 0.0
    if pico < 1e-4:
        return x
    rms = float(np.sqrt(np.mean(x ** 2)))
    ganho = float(np.clip(rms_alvo / max(rms, 1e-6), GANHO_MIN, GANHO_MAX))
    return x * min(ganho, pico_max / pico)


def fade(x: np.ndarray, taxa: int, entrada_ms: float = 6.0, saida_ms: float = 25.0) -> np.ndarray:
    """Rampa curta no começo e no fim: some o 'tic' de cortar a onda no meio."""
    x = x.copy()
    n_in = min(int(taxa * entrada_ms / 1000), x.size // 2)
    n_out = min(int(taxa * saida_ms / 1000), x.size // 2)
    if n_in:
        x[:n_in] *= np.linspace(0.0, 1.0, n_in, dtype=np.float32)
    if n_out:
        x[-n_out:] *= np.linspace(1.0, 0.0, n_out, dtype=np.float32)
    return x


def acabamento(pcm: np.ndarray, taxa: int, pausa_final_ms: int = 0) -> np.ndarray:
    """int16 mono -> int16 mono: volume parelho, fades e silêncio final."""
    if pcm.size == 0:
        return pcm.astype(np.int16)
    x = fade(nivelar(pcm), taxa)
    if pausa_final_ms > 0:
        x = np.concatenate([x, np.zeros(int(taxa * pausa_final_ms / 1000), dtype=np.float32)])
    return np.round(np.clip(x, -1.0, 1.0) * 32767).astype(np.int16)


def chime_wave() -> np.ndarray:
    """Dois tons ascendentes suaves (sino curto), com ataque e saída sem estalo."""
    def tom(freq: float, segundos: float) -> np.ndarray:
        t = np.arange(int(CHIME_RATE * segundos)) / CHIME_RATE
        ataque = np.minimum(1.0, t / 0.008)                  # 8 ms: sem clique
        queda = np.exp(-t * 22.0) * np.minimum(1.0, (segundos - t) / 0.02)
        onda = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 2 * freq * t)
        return 0.16 * ataque * queda * onda
    return np.concatenate([tom(880, 0.09), tom(1320, 0.12)]).astype(np.float32)
