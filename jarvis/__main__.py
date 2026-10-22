"""Ponto de entrada.

    python -m jarvis                     abre a janela com ícone na bandeja
    python -m jarvis --texto             conversa no terminal até digitar "sair"
    python -m jarvis "sua pergunta"      responde uma vez no terminal
    python -m jarvis --chave gemini      guarda a chave do Gemini no cofre do Windows
    python -m jarvis --chave nvidia      guarda a chave da NVIDIA no cofre do Windows
    python -m jarvis --conectar gmail    autoriza o Gmail no navegador
    python -m jarvis --conectar outlook  autoriza o Outlook/Hotmail no navegador
    python -m jarvis --desconectar gmail apaga o acesso salvo (idem para outlook)
    python -m jarvis --importar-obsidian PASTA   copia as notas Jarvis/ de um cofre para a memória
    python -m jarvis --exportar-memoria PASTA    grava uma cópia da memória em Markdown
"""

from __future__ import annotations

import argparse
import getpass
import sqlite3
import sys
from datetime import datetime

from jarvis import proc

proc.ocultar_consoles()  # antes dos demais imports: até o keyring/platform rodam `cmd /c ver` ao carregar

from jarvis import config, keys, log, memory_db, memory_obsidian  # noqa: E402
from jarvis.brains import NoBrainAvailable, build_router  # noqa: E402
from jarvis.chat import Conversation  # noqa: E402
from jarvis.llm import memoria_viva  # noqa: E402

WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


def system_prompt(cfg: config.Config) -> str:
    """Persona, perfil, memória e instruções de ferramentas (montado em jarvis/conversa/sistema.py)."""
    from jarvis.conversa import sistema

    return sistema.montar(cfg)


def new_conversation(cfg: config.Config) -> Conversation:
    # Recalcula a cada pergunta: hora atual, cidade e memórias novas.
    return Conversation(build_router(cfg), lambda: system_prompt(config.load()))


def store_key(provider: str) -> int:
    key = getpass.getpass(f"Cole a chave de API do {provider} (não aparece na tela): ")
    if not key.strip():
        print("Nenhuma chave informada.")
        return 1
    keys.set_key(provider, key)
    print(f"Chave do {provider} guardada no Gerenciador de Credenciais do Windows.")
    return 0


def connect_mail(cfg: config.Config, provider: str) -> int:
    from jarvis.mail.base import MailError

    try:
        if provider == "gmail":
            from jarvis.mail import gmail

            address = gmail.connect()
            cfg.email.gmail_ativo = True
        else:
            from jarvis.mail import outlook

            address = outlook.connect(cfg.email.outlook_client_id, cfg.email.outlook_authority)
            cfg.email.outlook_ativo = True
    except MailError as exc:
        print(f"Não foi possível conectar: {exc}\nVeja o guia em docs/CONFIGURAR-EMAIL.md")
        return 1
    config.save(cfg)
    print(f"{provider} conectado: {address}")
    return 0


def disconnect_mail(cfg: config.Config, provider: str) -> int:
    from jarvis import vault

    vault.delete(provider)
    setattr(cfg.email, f"{provider}_ativo", False)
    config.save(cfg)
    print(f"{provider} desconectado; o acesso salvo neste PC foi apagado.")
    return 0


def run_text(conversation: Conversation, once: str | None) -> int:
    def reply(prompt: str) -> int:
        try:
            answer = conversation.ask(prompt)
        except NoBrainAvailable as exc:
            print(f"[Jarvis] {exc}", file=sys.stderr)
            return 1
        print(f"Jarvis ({answer.brain}): {memoria_viva.extrair(answer.text).texto}")  # sem a linha [[SAVE]]
        return 0

    if once:
        return reply(once)

    print("Jarvis pronta. Digite 'sair' para encerrar.")
    while True:
        try:
            prompt = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if prompt.lower() in {"sair", "exit", "quit"}:
            return 0
        if prompt:
            reply(prompt)


def memory_tools(cfg: config.Config, import_from: str | None, export_to: str | None) -> int:
    mem = memory_db.open_memory(cfg)
    if import_from:
        count = memory_obsidian.import_obsidian(mem, import_from)
        print(f"{count} nota(s) copiada(s) de {import_from}/Jarvis (as que já existiam foram mantidas).")
    if export_to:
        count = memory_obsidian.export_markdown(mem, export_to)
        print(f"{count} nota(s) gravada(s) em {export_to} (notas de mesmo caminho foram sobrescritas).")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--mcp-server"]:  # usado pelo claude -p na versão instalada
        from jarvis.mcp_server import server

        log.setup()  # só arquivo: a saída padrão é o canal do MCP
        server.run("stdio")
        return 0

    for stream in (sys.stdout, sys.stderr):
        if stream is not None:  # pythonw não tem console
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="jarvis", description="Super Jarvis")
    parser.add_argument("pergunta", nargs="*", help="responde uma vez no terminal")
    parser.add_argument("--texto", action="store_true", help="conversa no terminal")
    parser.add_argument("--chave", choices=sorted(keys.ENV_NAMES), help="guarda uma chave de API")
    parser.add_argument("--conectar", choices=["gmail", "outlook"], help="conecta uma conta de e-mail")
    parser.add_argument("--desconectar", choices=["gmail", "outlook"], help="remove uma conta de e-mail")
    parser.add_argument("--importar-obsidian", metavar="COFRE", help="copia as notas Jarvis/ de um cofre do Obsidian")
    parser.add_argument("--exportar-memoria", metavar="PASTA", help="grava a memória como arquivos Markdown")
    args = parser.parse_args(argv)

    # Só a janela (sem argumentos) arquiva o log grande; terminal e MCP só anexam.
    terminal = (args.pergunta or args.texto or args.chave or args.conectar or args.desconectar
                or args.importar_obsidian or args.exportar_memoria)
    log.setup(archive=not terminal)
    if args.chave:
        return store_key(args.chave)

    cfg = config.load()
    if args.conectar:
        return connect_mail(cfg, args.conectar)
    if args.desconectar:
        return disconnect_mail(cfg, args.desconectar)
    if args.importar_obsidian or args.exportar_memoria:
        return memory_tools(cfg, args.importar_obsidian, args.exportar_memoria)
    conversation = new_conversation(cfg)
    if args.pergunta or args.texto:
        return run_text(conversation, " ".join(args.pergunta) or None)

    from jarvis.ui.app import run  # importa a interface só quando é usada

    return run(cfg, conversation)


if __name__ == "__main__":
    raise SystemExit(main())
