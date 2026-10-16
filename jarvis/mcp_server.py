"""Servidor MCP da Jarvis (stdio). O `claude -p` o inicia como processo filho.

    python -m jarvis.mcp_server

Ferramentas de leitura respondem na hora. Ferramentas "propor_*" só criam uma
proposta pendente: quem executa é o usuário, clicando em "Aprovar" na janela.
As ferramentas ficam em jarvis/mcp_tools/, uma por assunto; importar o módulo as registra.
"""

from __future__ import annotations

from jarvis.mcp_tools import (  # noqa: F401  (importar registra as ferramentas)
    document_tools,
    habilidades_tools,
    improve_tools,
    info_tools,
    launch_tools,
    logica_tools,
    mail_tools,
    notes_tools,
    pc_tools,
    project_tools,
    stack_tools,
)
from jarvis.mcp_tools.core import server

if __name__ == "__main__":
    from jarvis import log

    log.setup()  # só arquivo: a saída padrão é o canal do MCP
    server.run("stdio")
