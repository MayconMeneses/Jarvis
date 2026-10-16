"""Leitor das bibliotecas de código em Markdown (algoritmos e padrões de projeto).

Formato: cabeçalho `chave: valor`, uma linha em branco e seções `## Ideia`, `## Pseudocódigo`, `## Código`
(blocos ```python, ```javascript...). Campos opcionais não geram erro; quem usa decide o que é obrigatório.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from jarvis.dev.topicos import fold

CAMPOS = ("nome", "aliases", "problema", "complexidade", "funcoes", "casos", "go_teste", "go_saida")
NOMES_LINGUAGEM = {"python": "Python", "javascript": "JavaScript", "go": "Go", "java": "Java", "csharp": "C#"}
TESTADAS = ("python", "javascript", "go")


def parse_md(path: Path) -> dict:
    texto = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    cabecalho, _, corpo = texto.partition("\n\n")
    dados: dict = {"id": path.stem}
    for linha in cabecalho.splitlines():
        chave, _, valor = linha.partition(":")
        if chave.strip() in CAMPOS:
            dados[chave.strip()] = valor.strip()
    dados["aliases"] = [a.strip() for a in dados.get("aliases", "").split(",") if a.strip()]
    dados["funcoes"] = dict(p.strip().split("=") for p in dados.get("funcoes", "").split(";") if "=" in p)
    dados["casos"] = json.loads(dados.get("casos", "[]"))
    for secao in re.split(r"^## ", corpo, flags=re.M)[1:]:
        titulo, _, conteudo = secao.partition("\n")
        titulo = titulo.strip()
        if titulo == "Ideia":
            dados["ideia"] = [l[2:].strip() for l in conteudo.splitlines() if l.startswith("- ")]
        elif titulo.startswith("Pseudoc"):
            achado = re.search(r"```\n(.*?)\n```", conteudo, re.S)
            dados["pseudocodigo"] = achado.group(1) if achado else ""
        elif titulo.startswith("C"):
            dados["codigo"] = {m.group(1): m.group(2) for m in re.finditer(r"```(\w+)\n(.*?)\n```", conteudo, re.S)}
    return dados


def achar(itens: tuple[dict, ...], texto: str) -> dict | None:
    """O item cujo nome, id ou apelido aparece no texto (o nome mais longo vence)."""
    baixo = fold(texto)
    melhor, tamanho = None, 0
    for item in itens:
        for nome in [item["nome"], item["id"].replace("_", " "), *item["aliases"]]:
            nome = fold(nome)
            if len(nome) > tamanho and re.search(rf"(?<!\w){re.escape(nome)}(?!\w)", baixo):
                melhor, tamanho = item, len(nome)
    return melhor
