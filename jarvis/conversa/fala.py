"""Resposta falada: um resumo curto e natural; o detalhe completo fica só na tela.

Quando o pedido veio por voz, o contexto já pede ao modelo no máximo 3 frases. Aqui fica a segunda garantia: se mesmo assim a
resposta saiu longa, com lista ou código, a voz lê só o começo e avisa que os detalhes estão na janela.
"""

from __future__ import annotations

import re

from jarvis.voice.normalizar import limpar_marcacao

MAX_FALADO = 240
MAX_FRASES = 3
AVISO = "Os detalhes estão na janela."


def falado(texto: str) -> str:
    """O que a voz deve dizer. Texto curto e simples passa como está (a limpeza de Markdown é feita por quem fala)."""
    limpo = re.sub(r"\s+", " ", limpar_marcacao(texto or "")).strip()
    tem_codigo = "```" in (texto or "")
    if not limpo:
        return ""
    if len(limpo) <= MAX_FALADO and not tem_codigo:
        return limpo
    frases = [f for f in re.split(r"(?<=[.!?…])\s+", limpo) if f]
    escolhidas: list[str] = []
    for frase in frases:
        if len(escolhidas) >= MAX_FRASES or len(" ".join([*escolhidas, frase])) > MAX_FALADO:
            break
        escolhidas.append(frase)
    resumo = " ".join(escolhidas) or limpo[:MAX_FALADO].rsplit(" ", 1)[0].rstrip(",;:") + "."
    return f"{resumo} {AVISO}"
