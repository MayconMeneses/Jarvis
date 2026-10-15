import json
import sys
from pathlib import Path

from jarvis.brains.base import Answer, Brain, BrainUnavailable, Message
from jarvis.brains.claude_cli import ClaudeCLI
from jarvis.brains.openai_compat import OpenAICompat
from jarvis.brains.router import NoBrainAvailable, Router
from jarvis.config import Config, data_dir
from jarvis.keys import get_key


def mcp_server_command() -> tuple[str, list[str]]:
    """Como iniciar o servidor MCP (stdio): precisa de um executável de console.

    Instalado (PyInstaller): jarvis-cli.exe --mcp-server, na mesma pasta do Jarvis.exe.
    Em desenvolvimento: python.exe -m jarvis.mcp_server.
    """
    exe = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return str(exe.with_name("jarvis-cli.exe")), ["--mcp-server"]
    candidate = exe.with_name("python.exe")
    return str(candidate if candidate.exists() else exe), ["-m", "jarvis.mcp_server"]


def write_mcp_config(path: Path | None = None) -> Path:
    path = path or data_dir() / "mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    command, args = mcp_server_command()
    config = {"mcpServers": {"jarvis": {"command": command, "args": args}}}
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def build_router(cfg: Config) -> Router:
    mcp = write_mcp_config() if cfg.ferramentas_pc else None
    available = {
        "claude": lambda: ClaudeCLI(cfg.claude, mcp_config=mcp),
        "gemini": lambda: OpenAICompat("gemini", cfg.gemini, get_key),
        "nvidia": lambda: OpenAICompat("nvidia", cfg.nvidia, get_key),
    }
    brains = [available[name]() for name in cfg.brains if name in available]
    return Router(brains)


__all__ = [
    "Answer", "Brain", "BrainUnavailable", "ClaudeCLI", "Message",
    "NoBrainAvailable", "OpenAICompat", "Router", "build_router",
]
