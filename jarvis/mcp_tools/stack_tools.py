"""Conhecimento de programação: tecnologias de front end, back end e full stack, e modelos de projeto."""

from __future__ import annotations

from jarvis.dev import conhecimento, modelos
from jarvis.mcp_tools.core import server


@server.tool()
def consultar_tecnologia(nome: str) -> str:
    """Descreve uma linguagem, framework, banco ou stack que a Jarvis conhece (React, FastAPI, Python,
    PostgreSQL, MERN...): o que é, usos, pontos fortes e fracos, quando escolher e como começar.
    Base curada e offline; se não conhecer, diz e sugere pesquisar na internet."""
    entry = conhecimento.lookup(nome)
    if entry is None:
        return f"Não tenho \"{nome}\" na minha base. Use listar_tecnologias ou pesquise na internet."
    return conhecimento.describe(entry)


@server.tool()
def listar_tecnologias(area: str = "full stack") -> str:
    """Lista o que a Jarvis conhece numa área: "front end", "back end", "full stack", "mobile",
    "bancos de dados" ou "linguagens"."""
    return conhecimento.overview(area)


@server.tool()
def comparar_tecnologias(a: str, b: str) -> str:
    """Compara duas tecnologias lado a lado (ex.: React e Vue, Django e FastAPI, Python e Node.js)."""
    first, second = conhecimento.lookup(a), conhecimento.lookup(b)
    if first is None or second is None:
        missing = a if first is None else b
        return f"Não tenho \"{missing}\" na minha base. Use listar_tecnologias."
    return conhecimento.compare(first, second)


@server.tool()
def recomendar_stack(sistema: str) -> str:
    """Recomenda front-end, back-end e banco para um tipo de sistema descrito em linguagem natural
    (loja virtual, sistema de gestão, API, dashboard, app de celular, chat, site...), com o porquê e alternativas."""
    return conhecimento.recommend(sistema)


@server.tool()
def modelos_de_projeto() -> str:
    """Modelos de sistema inicial que a Jarvis cria prontos para rodar (back-end FastAPI ou Express,
    front-end React ou HTML/JS). Use o id em propor_criar_projeto(modelo=...)."""
    combos = [f"{b}+{f}" for b in modelos.BACKS for f in modelos.FRONTS] + list(modelos.BACKS) + list(modelos.FRONTS)
    return ("Modelos prontos (cada um traz exemplo de CRUD, testes e README):\n"
            + "\n".join(f"- `{c}`: {modelos.descricao(c)}" for c in combos))
