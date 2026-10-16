"""Cérebro generativo local: estado e proposta de instalação (a instalação em si exige aprovação no cartão)."""

from __future__ import annotations

from jarvis import config
from jarvis.llm import tarefas
from jarvis.local import llm_skills
from jarvis.mcp_tools.core import server


@server.tool()
def estado_do_cerebro_local() -> str:
    """Diz se o modelo de linguagem local (sem API, rodando no PC) está instalado e ligado, e o andamento de
    instalações e de criações de sistema em segundo plano."""
    return tarefas.resumo(config.load())


@server.tool()
def perfil_do_aparelho() -> str:
    """Memória, núcleos e placa NVIDIA deste aparelho, e qual modelo local ele aguenta (mais memória, modelo maior)."""
    from jarvis.llm import perfil

    return perfil.descrever()


@server.tool()
def propor_instalar_cerebro_local(modelo_maior: bool = False) -> str:
    """Cria um CARTÃO de aprovação para baixar o motor llama.cpp e o modelo local (cerca de 1,1 GB; o maior, 2,1 GB).
    Nada é baixado antes de o usuário aprovar na janela."""
    return llm_skills.instalar("maior" if modelo_maior else "", config.load())
