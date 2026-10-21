"""Texto que a Jarvis fala: limpeza, normalização pt-BR e divisão em frases (a 1ª sempre curta)."""

from __future__ import annotations

import re

from jarvis.voice.normalizar import limpar_marcacao, normalizar

MAX_SPOKEN = 600  # caracteres; o resto fica só na janela
PRIMEIRA_MAX = 90  # a 1ª parte passa de ~90 caracteres? corta na primeira vírgula: o som começa antes


def clean_for_speech(text: str) -> str:
    """Tira Markdown, código, links e emojis; encurta respostas longas; escreve números, horas, moedas e siglas por extenso."""
    text = limpar_marcacao(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_SPOKEN:
        cut = text[:MAX_SPOKEN]
        end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        text = (cut[: end + 1] if end > 200 else cut) + " Os detalhes estão na janela."
    return normalizar(text)


def split_sentences(text: str, min_chars: int = 40) -> list[str]:
    """Divide em frases, juntando as muito curtas (cada parte é uma chamada de síntese)."""
    pieces = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", text) if p.strip()]
    parts: list[str] = []
    for piece in pieces:
        if parts and len(parts[-1]) < min_chars:
            parts[-1] += " " + piece
        else:
            parts.append(piece)
    return parts


def dividir_para_fala(text: str) -> list[str]:
    """Frases para a síntese em fluxo. Se a 1ª for longa, sai só até a vírgula/ponto e vírgula: menos espera até o 1º som."""
    parts = split_sentences(text)
    if parts and len(parts[0]) > PRIMEIRA_MAX:
        corte = next((m.end() for m in re.finditer(r"[,;:]\s", parts[0]) if m.end() >= 12), 0)
        if 0 < corte < len(parts[0]) - 15:
            parts[0:1] = [parts[0][:corte].strip(), parts[0][corte:].strip()]
    return parts


def pausa_ms(parte: str) -> int:
    """Silêncio depois da parte: ponto e interrogação respiram mais que vírgula."""
    fim = parte.rstrip()[-1:]
    return {".": 220, "!": 240, "?": 260, "…": 280}.get(fim, 90)
