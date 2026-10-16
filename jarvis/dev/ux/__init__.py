"""UI/UX: tópicos de design de interface e ferramentas de cálculo (contraste, paleta, escalas, tokens)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jarvis.dev import topicos

BASE = Path(__file__).parent


@lru_cache(maxsize=1)
def itens() -> tuple[dict, ...]:
    return topicos.carregar(*sorted((BASE / "dados").glob("*.json")))


def topico(termo: str) -> dict | None:
    return topicos.procurar(itens(), termo)


def mencionados(texto: str) -> list[dict]:
    return topicos.mencionados(itens(), texto)


def visao_geral() -> str:
    return topicos.visao_geral("UI/UX e design de interfaces que eu explico:", itens())
