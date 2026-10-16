"""Tópicos de conhecimento: o mesmo formato para lógica, engenharia, arquitetura, sistemas e UI/UX.

Cada tópico (JSON) tem id, nome, aliases, resumo, passos, analogia, exemplo, erros e exercicios. Este módulo
carrega, procura (nome e id antes dos apelidos), acha os citados num texto e descreve em Markdown.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def carregar(*arquivos: Path) -> tuple[dict, ...]:
    itens: list[dict] = []
    for arquivo in arquivos:
        itens += json.loads(Path(arquivo).read_text(encoding="utf-8"))
    return tuple(itens)


def _nomes(item: dict) -> set[str]:
    return {fold(item["id"]), fold(item["nome"])}


def procurar(itens: tuple[dict, ...], termo: str) -> dict | None:
    """O tópico pelo nome ou id; só depois pelos apelidos (para um apelido não roubar o nome de outro)."""
    limpo = re.sub(r"^(a|o|as|os|um|uma)\s+", "", fold(termo).strip(" ?!."))
    for item in itens:
        if limpo in _nomes(item):
            return item
    for item in itens:
        if limpo in {fold(a) for a in item.get("aliases", [])}:
            return item
    return None


def mencionados(itens: tuple[dict, ...], texto: str) -> list[dict]:
    """Tópicos citados no texto (palavra inteira), na ordem em que aparecem."""
    baixo, achados = fold(texto), []
    for item in itens:
        casos = [(m.start(), -len(nome)) for nome in _nomes(item) | {fold(a) for a in item.get("aliases", [])}
                 if (m := re.search(rf"(?<!\w){re.escape(nome)}(?!\w)", baixo))]
        if casos:
            achados.append((min(casos), item))  # primeiro no texto; no empate, o nome mais longo (mais específico)
    return [item for _, item in sorted(achados, key=lambda a: a[0])]


def descrever(item: dict) -> str:
    saida = [f"**{item['nome']}**", item["resumo"], "", "**Como aplicar:**"]
    saida += [f"- {p}" for p in item["passos"]]
    saida += ["", f"**Analogia:** {item['analogia']}", "", f"**{item.get('rotulo_exemplo', 'Exemplo')}:**", "```", item["exemplo"], "```",
              "**Erros comuns:** " + "; ".join(item["erros"]), "**Para praticar:** " + " · ".join(item["exercicios"])]
    return "\n".join(saida)


def comparar(a: dict, b: dict) -> str:
    return (f"**{a['nome']} × {b['nome']}**\n"
            f"- **{a['nome']}:** {a['resumo']}\n  - Analogia: {a['analogia']}\n"
            f"- **{b['nome']}:** {b['resumo']}\n  - Analogia: {b['analogia']}\n"
            f"- **Erros comuns** — {a['nome']}: {'; '.join(a['erros'])} | {b['nome']}: {'; '.join(b['erros'])}")


def visao_geral(titulo: str, itens: tuple[dict, ...]) -> str:
    return f"**{titulo}**\n" + "\n".join(f"- **{i['nome']}**: {i['resumo'].split('. ')[0].rstrip('.')}." for i in itens)
