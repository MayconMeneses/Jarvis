"""Autoconhecimento da Jarvis: a base editável (dados/autoconhecimento.json) sobre ela mesma, sem IA.

Esquema de cada entrada: {id, titulo, exemplos[], palavras[], resposta, passos[], plataformas[], relacionados[]}.
O mesmo arquivo é copiado para movel/dados/autoconhecimento.json (movel/gerar_dados.py) e usado pelo celular.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ARQUIVO = Path(__file__).with_name("dados") / "autoconhecimento.json"
CAMPOS = ("id", "titulo", "exemplos", "palavras", "resposta", "passos", "plataformas", "relacionados")
MAX_CONTEXTO = 1600  # caracteres de autoconhecimento que vão como contexto para uma IA (cabe em qualquer janela)


@lru_cache(maxsize=1)
def todos() -> tuple[dict, ...]:
    return tuple(json.loads(ARQUIVO.read_text(encoding="utf-8")))


def por_id(id_: str) -> dict | None:
    return next((e for e in todos() if e["id"] == id_), None)


def validar(entradas: list[dict]) -> list[str]:
    """Problemas do arquivo (vazio = ok): campos, ids repetidos e relacionados que não existem."""
    erros, ids = [], [e.get("id") for e in entradas]
    for e in entradas:
        faltam = [c for c in CAMPOS if c not in e]
        if faltam:
            erros.append(f"{e.get('id')}: faltam {faltam}")
        elif not e["resposta"].strip() or len(e["exemplos"]) < 3:
            erros.append(f"{e['id']}: resposta vazia ou menos de 3 exemplos")
    erros += [f"id repetido: {i}" for i in set(ids) if ids.count(i) > 1]
    erros += [f"{e['id']}: relacionado inexistente {r}" for e in entradas for r in e.get("relacionados", []) if r not in ids]
    return erros


def formatar(entrada: dict, com_relacionados: bool = True) -> str:
    linhas = [f"**{entrada['titulo']}**", entrada["resposta"]]
    if entrada["passos"]:
        linhas.append("")
        linhas += [f"{n}. {p}" for n, p in enumerate(entrada["passos"], 1)]
    rel = [por_id(r) for r in entrada["relacionados"][:3]]
    if com_relacionados and any(rel):
        linhas += ["", "Veja também: " + "; ".join(r["titulo"] for r in rel if r) + "."]
    return "\n".join(linhas)


def contexto_para_ia(ids: list[str]) -> str:
    """Trechos fiéis ao código para a IA responder sobre a própria Jarvis (RAG), dentro do limite de contexto."""
    partes, usado = [], 0
    for i in ids:
        e = por_id(i)
        if not e:
            continue
        trecho = f"- {e['titulo']}: {e['resposta']} " + " ".join(f"({n}) {p}" for n, p in enumerate(e["passos"], 1))
        if usado + len(trecho) > MAX_CONTEXTO:
            break
        partes.append(trecho)
        usado += len(trecho)
    return "\n".join(partes)
