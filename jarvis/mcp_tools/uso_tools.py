"""Uso de IA, SOMENTE LEITURA: totais, custo equivalente e cota estimada do Claude (sem conteúdo de conversas)."""

from __future__ import annotations

from jarvis.local import uso_skills
from jarvis.mcp_tools.core import server


@server.tool()
def uso_ia_resumo(periodo: str = "mes") -> str:
    """Resumo do uso de IA (respostas, tokens, valor equivalente em API, por modelo, orçamento).
    periodo: hoje, semana, mes ou tudo. Valores em dólar são estimativas pela tabela de preços editável."""
    nomes = {"hoje": "hoje", "semana": "esta semana", "tudo": "tudo"}
    return uso_skills.responder(f"uso de ia {nomes.get(periodo, 'este mes')}")


@server.tool()
def cota_claude_estimada() -> str:
    """Estimativa de quanto da cota do Claude (janela de 5 h e semanal) já foi usada. É estimativa: o Claude não expõe a cota."""
    return uso_skills.responder("cota do claude")
