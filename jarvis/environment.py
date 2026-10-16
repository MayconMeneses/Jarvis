"""O que a Jarvis precisa que exista fora do instalador: Claude Code e git.

Nenhum dos dois pode ir dentro do pacote: o Claude Code usa a assinatura e o login do
próprio usuário, e o git é uma ferramenta do sistema. A Jarvis procura os dois e, se
faltarem, explica na janela o que muda e como resolver em vez de quebrar.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from jarvis.config import Config

CLAUDE_URL = "https://claude.com/claude-code"
GIT_URL = "https://git-scm.com/download/win"


def find_claude(executable: str = "claude") -> str | None:
    """Caminho do Claude Code: no PATH ou na pasta onde o instalador oficial o coloca."""
    found = shutil.which(executable)
    if found:
        return found
    fallback = Path.home() / ".local" / "bin" / "claude.exe"
    return str(fallback) if executable == "claude" and fallback.is_file() else None


def find_git() -> str | None:
    return shutil.which("git")


def notices(cfg: Config, has_other_brain: bool = False) -> list[str]:
    """Avisos para mostrar na janela quando algo externo está faltando (lista vazia = tudo certo)."""
    found = []
    if not find_claude(cfg.claude.executable):
        tail = ("Enquanto isso, ela responde com o Gemini ou a NVIDIA." if has_other_brain
                else "Sem ele e sem chave do Gemini ou da NVIDIA, ela só entende comandos simples "
                     "(abrir programas, clima, notícias, vagas, memória).")
        found.append(
            "O Claude Code não foi encontrado neste PC. Ele é o cérebro principal da Jarvis e usa a sua "
            f"assinatura do Claude: instale em {CLAUDE_URL} e faça login uma vez no terminal com `claude`. {tail}")
    if not find_git():
        found.append(
            "O git não foi encontrado neste PC. Sem ele, a Jarvis não mostra o estado dos projetos, não cria "
            f"repositórios nem revisa o que o Claude Code mudou. Instale em {GIT_URL} (o resto funciona normalmente).")
    return found
