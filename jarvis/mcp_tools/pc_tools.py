"""Ferramentas do PC: leitura do sistema e ações propostas (com aprovação)."""

from __future__ import annotations

from jarvis.pc import actions, startup, system
from jarvis.mcp_tools.core import server, store, proposal


@server.tool()
def visao_geral() -> dict:
    """CPU, RAM, disco C:, bateria e tempo ligado do PC agora."""
    return system.overview()


@server.tool()
def processos_pesados(ordenar_por: str = "memoria", limite: int = 10) -> list[dict]:
    """Programas que mais consomem, agrupados por nome. ordenar_por: "memoria" ou "cpu"."""
    return system.top_processes(ordenar_por, limite)


@server.tool()
def programas_inicializacao() -> list[dict]:
    """Programas que iniciam com o Windows, se estão ativos e se podem ser desativados."""
    return [item.to_dict() for item in startup.list_items()]


@server.tool()
def uso_disco() -> dict:
    """Espaço livre no C: e tamanho de pastas que costumam acumular lixo (GB)."""
    return system.disk_summary()


@server.tool()
def propor_encerrar_processo(pid: int, motivo: str) -> str:
    """Propõe encerrar um processo pelo PID. Não executa: o usuário aprova na janela."""
    try:
        return proposal(actions.propose_kill(store, pid, motivo))
    except ValueError as exc:
        return f"Não é possível propor: {exc}"


@server.tool()
def propor_limpar_temporarios(motivo: str, dias: int = 1) -> str:
    """Propõe apagar arquivos da pasta TEMP mais antigos que `dias`. O usuário aprova na janela."""
    try:
        return proposal(actions.propose_clean_temp(store, dias, motivo))
    except ValueError as exc:
        return f"Não é possível propor: {exc}"


@server.tool()
def propor_desativar_inicializacao(nome: str, motivo: str) -> str:
    """Propõe impedir um programa (nome exato de programas_inicializacao) de iniciar com o Windows."""
    try:
        return proposal(actions.propose_disable_startup(store, nome, motivo))
    except ValueError as exc:
        return f"Não é possível propor: {exc}"
