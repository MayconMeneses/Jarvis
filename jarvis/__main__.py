"""Ponto de entrada.

    python -m jarvis                     abre a janela com ícone na bandeja
    python -m jarvis --texto             conversa no terminal até digitar "sair"
    python -m jarvis "sua pergunta"      responde uma vez no terminal
    python -m jarvis --chave gemini      guarda a chave do Gemini no cofre do Windows
    python -m jarvis --chave nvidia      guarda a chave da NVIDIA no cofre do Windows
"""

from __future__ import annotations

import argparse
import getpass
import sys

from jarvis import config, keys, log
from jarvis.brains import NoBrainAvailable, build_router
from jarvis.chat import Conversation


def system_prompt(cfg: config.Config) -> str:
    return (
        f"Você é a Jarvis, assistente pessoal de {cfg.user_name}. "
        f"Responda em {cfg.language}, de forma direta e cordial. "
        "Se não souber algo, diga que não sabe."
    )


def new_conversation(cfg: config.Config) -> Conversation:
    return Conversation(build_router(cfg), system_prompt(cfg))


def store_key(provider: str) -> int:
    key = getpass.getpass(f"Cole a chave de API do {provider} (não aparece na tela): ")
    if not key.strip():
        print("Nenhuma chave informada.")
        return 1
    keys.set_key(provider, key)
    print(f"Chave do {provider} guardada no Gerenciador de Credenciais do Windows.")
    return 0


def run_text(conversation: Conversation, once: str | None) -> int:
    def reply(prompt: str) -> int:
        try:
            answer = conversation.ask(prompt)
        except NoBrainAvailable as exc:
            print(f"[Jarvis] {exc}", file=sys.stderr)
            return 1
        print(f"Jarvis ({answer.brain}): {answer.text}")
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


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:  # pythonw não tem console
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="jarvis", description="Super Jarvis")
    parser.add_argument("pergunta", nargs="*", help="responde uma vez no terminal")
    parser.add_argument("--texto", action="store_true", help="conversa no terminal")
    parser.add_argument("--chave", choices=sorted(keys.ENV_NAMES), help="guarda uma chave de API")
    args = parser.parse_args(argv)

    log.setup()
    if args.chave:
        return store_key(args.chave)

    cfg = config.load()
    conversation = new_conversation(cfg)
    if args.pergunta or args.texto:
        return run_text(conversation, " ".join(args.pergunta) or None)

    from jarvis.ui.app import run  # importa a interface só quando é usada

    return run(cfg, conversation)


if __name__ == "__main__":
    raise SystemExit(main())
