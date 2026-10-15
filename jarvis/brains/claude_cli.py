"""Cérebro Claude via `claude -p`, usando a assinatura logada no Claude Code.

Nunca usa chave de API: as variáveis ANTHROPIC_* são removidas do ambiente do
processo filho, porque o CLI prefere uma chave herdada ao login da assinatura
e passaria a cobrar por uso sem avisar.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

from jarvis.brains.base import Answer, BrainUnavailable
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

    def __init__(self, cfg: ClaudeConfig, workdir: Path | None = None) -> None:
        self.cfg = cfg
        # Pasta vazia própria: evita carregar CLAUDE.md e configurações de projetos.
        self.workdir = workdir or data_dir() / "claude-workspace"

    def command(self, system: str) -> list[str]:
        exe = shutil.which(self.cfg.executable) or self.cfg.executable
        cmd = [
            exe, "-p",
            "--output-format", "json",
            "--tools", "",
            "--strict-mcp-config",
            "--setting-sources", "project",
            "--no-session-persistence",
            "--system-prompt", system,
        ]
        if self.cfg.model:
            cmd += ["--model", self.cfg.model]
        return cmd

    def ask(self, prompt: str, system: str) -> Answer:
        self.workdir.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(
                self.command(system),
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.workdir,
                env=child_env(),
                timeout=self.cfg.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise BrainUnavailable("Claude Code não está instalado ou fora do PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise BrainUnavailable("Claude demorou demais para responder") from exc

        return parse_output(proc.stdout, proc.stderr, proc.returncode)


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
