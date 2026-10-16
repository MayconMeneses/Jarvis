"""Habilidades de programador: avaliar projetos, ver o que melhorar e acompanhar a evolução."""

from __future__ import annotations

from jarvis import config
from jarvis.dev import habilidades
from jarvis.dev.habilidades import evolucao
from jarvis.mcp_tools.core import mem, server


@server.tool()
def habilidades_de_programador() -> str:
    """As 18 habilidades de um bom programador que a Jarvis acompanha (lógica, linguagens, estruturas de dados,
    testes, depuração, código limpo, segurança, bancos, APIs, arquitetura, versionamento, automação, desempenho,
    logs, acessibilidade, documentação, organização e aprendizado contínuo), cada uma com níveis e práticas."""
    return habilidades.visao_geral()


@server.tool()
def avaliar_projeto(projeto: str) -> str:
    """Avalia um projeto cadastrado (ou uma pasta com caminho completo) em 9 aspectos, SOMENTE LEITURA: testes,
    documentação, versionamento, segurança, código limpo, automação, logs, acessibilidade e organização.
    Dá nota de 0 a 100 por aspecto, o que achou e o que melhorar, e compara com a avaliação anterior para mostrar
    a evolução. São heurísticas, não um veredito. Para a própria Jarvis ("Super Jarvis"), anota as melhorias no
    caderno de melhorias."""
    try:
        return evolucao.avaliar(config.load(), mem(), projeto)
    except ValueError as exc:
        return str(exc)


@server.tool()
def proxima_habilidade(projeto: str = "") -> str:
    """Qual habilidade praticar agora: a mais fraca da última avaliação do projeto, com plano, o que estudar e um
    treino. Sem projeto, sugere a base (lógica e algoritmos)."""
    try:
        return evolucao.proxima(config.load(), mem(), projeto)
    except ValueError as exc:
        return str(exc)


@server.tool()
def treino_da_semana() -> str:
    """O treino pequeno da semana: uma das 18 habilidades por semana, em rodízio, com o que estudar. É a rotina que
    faz a Jarvis (e o usuário) evoluírem sempre."""
    return habilidades.treino_da_semana()


@server.tool()
def checklist_de_revisao(aspecto: str) -> str:
    """Checklist de práticas de uma habilidade para revisar código ou um projeto (ex.: segurança, testes,
    código limpo, APIs, banco de dados, acessibilidade), com os três níveis de domínio."""
    return habilidades.checklist(aspecto)


@server.tool()
def plano_de_evolucao(habilidade: str) -> str:
    """Plano para evoluir uma habilidade: o que fazer, o que estudar na base da Jarvis e um treino da semana."""
    return habilidades.plano(habilidade)
