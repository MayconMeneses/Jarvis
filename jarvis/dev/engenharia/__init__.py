"""Engenharia de software, arquitetura, sistemas e padrões de projeto (base curada, sem IA e sem internet).

- dados/*.json: tópicos (engenharia, arquitetura, sistemas) no formato de `jarvis.dev.topicos`.
- padroes/*.md: padrões de projeto com ideia, pseudocódigo e código em Python e JavaScript (executados nos testes).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jarvis.dev import topicos
from jarvis.dev.biblioteca import NOMES_LINGUAGEM, achar, parse_md

BASE = Path(__file__).parent


@lru_cache(maxsize=1)
def itens() -> tuple[dict, ...]:
    return topicos.carregar(*sorted((BASE / "dados").glob("*.json")))


def topico(termo: str) -> dict | None:
    return topicos.procurar(itens(), termo)


def mencionados(texto: str) -> list[dict]:
    return topicos.mencionados(itens(), texto)


@lru_cache(maxsize=1)
def padroes() -> tuple[dict, ...]:
    return tuple(parse_md(p) for p in sorted((BASE / "padroes").glob("*.md")))


@lru_cache(maxsize=1)
def estruturas() -> tuple[dict, ...]:
    """Estruturas de dados (pilha, fila, lista ligada, hash, árvore de busca, heap, grafo, trie, union-find), em Python e JavaScript."""
    return tuple(parse_md(p) for p in sorted((BASE / "estruturas").glob("*.md")))


def padrao(texto: str) -> dict | None:
    return achar(padroes(), texto)


def estrutura(texto: str) -> dict | None:
    return achar(estruturas(), texto)


def mostrar_padrao(item: dict, lang: str = "python") -> str:
    saida = [f"**{item['nome']}**", item["problema"], *([f"- **Complexidade:** {item['complexidade']}"] if item.get("complexidade") else []), "", "**Ideia:**"] + [f"- {p}" for p in item["ideia"]]
    saida += ["", "**Pseudocódigo:**", "```", item["pseudocodigo"], "```"]
    codigo = item["codigo"].get(lang)
    if codigo is None:
        return "\n".join(saida) + f"\n\nTenho este padrão em: {', '.join(NOMES_LINGUAGEM[l] for l in item['codigo'])}."
    saida += ["", f"**Em {NOMES_LINGUAGEM.get(lang, lang)}:**", f"```{lang}", codigo, "```"]
    return "\n".join(saida)


def visao_padroes() -> str:
    return "**Padrões de projeto que eu sei escrever (Python e JavaScript):**\n" + "\n".join(
        f"- **{p['nome']}**: {p['problema'].removeprefix('Quando usar: ').split(';')[0].rstrip('.')}." for p in padroes())


def visao_estruturas() -> str:
    return "**Estruturas de dados que eu sei escrever (Python e JavaScript):**\n" + "\n".join(
        f"- **{e['nome']}**: {e['problema'].split('. ')[0].rstrip('.')}." for e in estruturas())


def visao_geral() -> str:
    return topicos.visao_geral("Engenharia de software, arquitetura e sistemas que eu explico:", itens())
