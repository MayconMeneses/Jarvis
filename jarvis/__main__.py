"""Interface de texto da Fase 0.

    python -m jarvis "sua pergunta"    responde uma vez
    python -m jarvis                   conversa até digitar "sair"
"""

from __future__ import annotations

import sys

from jarvis import config, log
from jarvis.brains import NoBrainAvailable, build_router


def system_prompt(cfg: config.Config) -> str:
    return (
        f"Você é a Jarvis, assistente pessoal de {cfg.user_name}. "
        f"Responda em {cfg.language}, de forma direta e cordial. "
        "Se não souber algo, diga que não sabe."
    )


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    log.setup()
    cfg = config.load()
    router = build_router(cfg)
    system = system_prompt(cfg)

    def reply(prompt: str) -> int:
        try:
            answer = router.ask(prompt, system)
        except NoBrainAvailable as exc:
            print(f"[Jarvis] {exc}", file=sys.stderr)
            return 1
        print(f"Jarvis ({answer.brain}): {answer.text}")
        return 0

    if argv:
        return reply(" ".join(argv))

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


if __name__ == "__main__":
    raise SystemExit(main())
