"""Ícones PNG do app (um anel ciano sobre fundo escuro), gerados na hora só com a biblioteca padrão."""

from __future__ import annotations

import math
import struct
import zlib
from functools import lru_cache

FUNDO, CIANO = (4, 7, 12), (0, 229, 255)


def _bloco(tipo: bytes, dados: bytes) -> bytes:
    return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)


@lru_cache(maxsize=8)
def png(tamanho: int) -> bytes:
    centro, raio = (tamanho - 1) / 2, tamanho * 0.30
    espessura = max(2.0, tamanho * 0.055)
    linhas = bytearray()
    for y in range(tamanho):
        linhas.append(0)
        for x in range(tamanho):
            d = abs(math.hypot(x - centro, y - centro) - raio)
            t = max(0.0, min(1.0, 1.0 - (d - espessura / 2) / 1.5))  # borda suave
            nucleo = math.hypot(x - centro, y - centro) < tamanho * 0.06
            t = 1.0 if nucleo else t
            linhas += bytes(round(f + (c - f) * t) for f, c in zip(FUNDO, CIANO))
    cabecalho = struct.pack(">IIBBBBB", tamanho, tamanho, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _bloco(b"IHDR", cabecalho) + _bloco(b"IDAT", zlib.compress(bytes(linhas), 9)) + _bloco(b"IEND", b"")
