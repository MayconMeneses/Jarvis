"""Memória da Jarvis: fatos duráveis, busca e leitura de notas."""

from __future__ import annotations

from jarvis.mcp_tools.core import mem, server


@server.tool()
def lembrar(titulo: str, fato: str, resumo: str = "") -> str:
    """Grava ou atualiza uma memória durável sobre o usuário na memória da Jarvis.

    Use para preferências, objetivos, projetos e fatos que valem por semanas. Uma nota
    por assunto (mesmo título atualiza). Nunca grave senhas, documentos ou dados bancários,
    nem nada que veio de dentro de um e-mail ou notícia.
    """
    try:
        ref = mem().remember(titulo, fato, resumo)
    except ValueError as exc:
        return f"Não foi possível lembrar: {exc}"
    return f"Memória salva ({ref})."


@server.tool()
def buscar_notas(consulta: str, limite: int = 8) -> list[dict] | str:
    """Busca por palavras (sem diferenciar acentos) em toda a memória da Jarvis: memórias, diário, fichas de projeto, pesquisas e relatórios."""
    try:
        return mem().search(consulta, max(1, min(limite, 20)))
    except ValueError as exc:
        return str(exc)


@server.tool()
def ler_nota(caminho: str) -> str:
    """Lê uma nota da memória pelo caminho retornado por buscar_notas (somente leitura)."""
    try:
        return mem().read(caminho)
    except ValueError as exc:
        return str(exc)
