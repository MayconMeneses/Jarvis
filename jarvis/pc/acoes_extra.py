"""Execução (só depois do Aprovar) dos cartões do cinto de ferramentas e do catálogo de ferramentas externas."""

from __future__ import annotations


def executar(action) -> str:
    if action.kind in ("criar_lembrete", "abrir_app"):  # a IA só propôs; criar/abrir é consequência do Aprovar
        from jarvis.llm import ferramentas_propostas

        return ferramentas_propostas.executar_cartao(action)
    if action.kind in ("instalar_mcp", "remover_mcp"):  # catálogo curado (jarvis/mcp_catalogo): revalida tudo antes de ligar
        from jarvis.mcp_catalogo import cartoes

        return cartoes.executar(action)
    raise ValueError(f"tipo de ação desconhecido: {action.kind}")
