"""Cérebro Claude via `claude -p`, usando a assinatura logada no Claude Code.

Nunca usa chave de API: as variáveis ANTHROPIC_* são removidas do ambiente do
processo filho, porque o CLI prefere uma chave herdada ao login da assinatura
e passaria a cobrar por uso sem avisar.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

from jarvis import environment
from jarvis.brains.base import Answer, BrainUnavailable, Message
from jarvis.config import ClaudeConfig, data_dir

log = logging.getLogger(__name__)

# Variáveis CLAUDE_CODE_* que o CLI precisa no Windows e podem ser herdadas.
_KEEP = {"CLAUDE_CODE_GIT_BASH_PATH"}


def child_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Ambiente sem chave de API e sem marcas de sessão aninhada do Claude Code."""
    env = dict(os.environ if env is None else env)
    for key in list(env):
        upper = key.upper()
        if upper.startswith("ANTHROPIC_") or upper == "CLAUDECODE":
            del env[key]
        elif upper.startswith("CLAUDE_CODE_") and upper not in _KEEP:
            del env[key]
    return env


class ClaudeCLI:
    name = "claude"

    def __init__(
        self, cfg: ClaudeConfig, workdir: Path | None = None, mcp_config: Path | None = None
    ) -> None:
        self.cfg = cfg
        # Pasta vazia própria: evita carregar CLAUDE.md e configurações de projetos.
        self.workdir = workdir or data_dir() / "claude-workspace"
        # Servidor MCP da Jarvis (ferramentas do PC); None = sem ferramentas.
        self.mcp_config = mcp_config

    def command(self, system: str) -> list[str]:
        exe = environment.find_claude(self.cfg.executable) or self.cfg.executable
        cmd = [
            exe, "-p",
            "--output-format", "json",
            "--tools", "",  # nenhuma ferramenta embutida (Bash, Edit...)
            "--strict-mcp-config",  # ignora os servidores MCP do usuário
            "--setting-sources", "project",
            "--no-session-persistence",
            "--system-prompt", system,
        ]
        if self.mcp_config:
            # Só as ferramentas da própria Jarvis ficam liberadas.
            cmd += ["--mcp-config", str(self.mcp_config), "--allowedTools", "mcp__jarvis"]
        if self.cfg.model:
            cmd += ["--model", self.cfg.model]
        return cmd

    def ask(self, messages: list[Message], system: str) -> Answer:
        self.workdir.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(
                self.command(system),
                input=render_prompt(messages),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.workdir,
                env=child_env(),
                timeout=self.cfg.timeout_seconds,
                # Sem janela de console piscando quando a Jarvis roda pela bandeja.
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError as exc:
            raise BrainUnavailable("Claude Code não está instalado ou fora do PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise BrainUnavailable("Claude demorou demais para responder") from exc

        return parse_output(proc.stdout, proc.stderr, proc.returncode)


def render_prompt(messages: list[Message]) -> str:
    """O `claude -p` recebe um único texto: o histórico vai como transcrição."""
    *history, current = messages
    if not history:
        return current["content"]
    names = {"user": "Usuário", "assistant": "Jarvis"}
    lines = [f"{names[m['role']]}: {m['content']}" for m in history]
    return (
        "Histórico recente da conversa:\n" + "\n".join(lines)
        + "\n\nResponda agora a esta mensagem do usuário:\n" + current["content"]
    )


def parse_output(stdout: str, stderr: str, returncode: int) -> Answer:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        log.warning("claude -p saiu com %s: %s", returncode, (stderr or stdout)[:500])
        raise BrainUnavailable(f"resposta inválida do Claude (código {returncode})") from exc

    if data.get("is_error") or returncode != 0:
        detail = str(data.get("result") or stderr)[:300]
        log.warning("claude -p retornou erro: %s", detail)
        raise BrainUnavailable(f"Claude indisponível: {detail}")

    return Answer(text=str(data.get("result", "")).strip(), brain="claude")
