"""Projetos de código: cadastro, ficha, análise, plano, execução e sessões do Claude Code."""

from __future__ import annotations

from jarvis import config
from jarvis.dev import projects, runs, sessions
from jarvis.pc import actions
from jarvis.mcp_tools.core import mem, proposal, server, store


@server.tool()
def listar_projetos() -> dict:
    """Projetos de código cadastrados (nome → pasta)."""
    return config.load().projetos


@server.tool()
def registrar_projeto(nome: str, pasta: str) -> str:
    """Cadastra um projeto de código pela pasta que o usuário informou (caminho completo)."""
    cfg = config.load()
    try:
        path = projects.register(cfg, nome, pasta)
    except ValueError as exc:
        return str(exc)
    config.save(cfg)
    return f"Projeto '{nome}' cadastrado em {path}."


@server.tool()
def esquecer_projeto(projeto: str) -> str:
    """Tira um projeto da lista da Jarvis. Não apaga a pasta nem nenhum arquivo."""
    cfg = config.load()
    try:
        name = projects.unregister(cfg, projeto)
    except ValueError as exc:
        return str(exc)
    config.save(cfg)
    return f"Projeto '{name}' removido da lista. A pasta e a ficha na memória continuam onde estavam."


@server.tool()
def anotar_projeto(projeto: str, informacao: str, secao: str = "Anotações") -> str:
    """Grava uma informação na ficha do projeto, na memória da Jarvis.

    secao: Descrição (substitui a anterior), Stack, Objetivos, Decisões, Pendências ou
    Anotações (as outras acumulam com data). A ficha vai como contexto nas tarefas do
    Claude Code. Não altera a pasta do projeto. Nunca grave senhas ou chaves.
    """
    try:
        cfg = config.load()
        projects.add_info(cfg, mem(), projeto, informacao, secao)
    except ValueError as exc:
        return f"Não foi possível anotar: {exc}"
    return f"Anotado em {secao} na ficha do projeto."


@server.tool()
def ficha_projeto(projeto: str) -> str:
    """Lê a ficha do projeto na memória da Jarvis: descrição, stack, objetivos, decisões e pendências."""
    try:
        text = projects.read_info(config.load(), mem(), projeto)
    except ValueError as exc:
        return str(exc)
    return text or "Este projeto ainda não tem ficha. Use anotar_projeto para começar."


@server.tool()
def propor_criar_projeto(nome: str, pasta_pai: str, descricao: str, motivo: str) -> str:
    """Propõe criar um projeto NOVO: pasta <pasta_pai>/<nome> com README.md e git init (sem commit).

    Não executa: o usuário aprova na janela. pasta_pai é o caminho completo de uma pasta que
    já existe (pergunte ao usuário se ele não disse). Depois de criado, use
    propor_executar_tarefa para o Claude Code montar a estrutura inicial.
    """
    try:
        return proposal(actions.propose_new_project(store, config.load(), nome, pasta_pai, descricao, motivo))
    except ValueError as exc:
        return f"Não é possível propor: {exc}"


@server.tool()
def estado_projeto(projeto: str) -> dict | str:
    """Resumo rápido do projeto sem IA: branch, arquivos alterados e últimos commits."""
    try:
        return projects.status(config.load(), projeto)
    except (ValueError, RuntimeError) as exc:
        return str(exc)


def _enqueue(projeto: str, modo: str, tarefa: str) -> str:
    try:
        run = runs.enqueue(runs.RunStore(), config.load(), projeto, modo, tarefa)
    except ValueError as exc:
        return f"Não foi possível: {exc}"
    return (f"{runs.LABELS[modo]} do projeto {run.projeto} entrou na fila do Claude Code (id {run.id}). "
            "Leva alguns minutos; o resultado aparece na janela da Jarvis e fica na memória.")


@server.tool()
def analisar_codigo(projeto: str, pergunta: str) -> str:
    """Pede ao Claude Code para LER o projeto e responder a uma pergunta. Somente leitura; roda em segundo plano."""
    return _enqueue(projeto, "analisar", pergunta)


@server.tool()
def planejar_tarefa(projeto: str, tarefa: str) -> str:
    """Pede ao Claude Code um plano de implementação (arquivos, passos, riscos, testes). Somente leitura."""
    return _enqueue(projeto, "planejar", tarefa)


@server.tool()
def propor_executar_tarefa(projeto: str, tarefa: str, motivo: str) -> str:
    """Propõe deixar o Claude Code ALTERAR o código do projeto. Só roda se o usuário aprovar na janela.

    Exige projeto git. Não faz commit nem push. Prefira planejar_tarefa antes, e descreva a
    tarefa de forma completa (de preferência com o plano aprovado).
    """
    try:
        return proposal(actions.propose_dev_task(store, config.load(), projeto, tarefa, motivo))
    except ValueError as exc:
        return f"Não é possível propor: {exc}"


@server.tool()
def tarefas_de_codigo(limite: int = 5) -> list[dict]:
    """Últimas tarefas do Claude Code (status e começo do resultado)."""
    recent = runs.RunStore().all()[-max(1, min(limite, 20)):]
    return [{"id": r.id, "projeto": r.projeto, "modo": r.modo, "status": r.status,
             "tarefa": r.tarefa[:150], "resultado": r.resultado[:600]} for r in reversed(recent)]


@server.tool()
def sessoes_claude_code(apenas_esperando: bool = False) -> dict:
    """Sessões do Claude Code abertas no PC e se alguma está esperando o usuário
    (permissão, pergunta ou turno encerrado). Somente leitura. Motivos que começam
    com "talvez" são estimativa, não certeza."""
    found = sessions.SessionReader().sessions()
    waiting = [s for s in found if s.esperando]
    shown = waiting if apenas_esperando else found
    return {"esperando": len(waiting), "total": len(found), "sessoes": [s.to_dict() for s in shown]}
