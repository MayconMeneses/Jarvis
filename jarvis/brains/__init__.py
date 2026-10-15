import json
import sys
from pathlib import Path

from jarvis.brains.base import Answer, Brain, BrainUnavailable, Message
from jarvis.brains.claude_cli import ClaudeCLI
from jarvis.brains.openai_compat import OpenAICompat
from jarvis.brains.router import NoBrainAvailable, Router
from jarvis.config import Config, data_dir
from jarvis.keys import get_key


def console_python() -> str:
    """python.exe ao lado do interpretador atual (o servidor MCP usa stdio)."""
    exe = Path(sys.executable)
    candidate = exe.with_name("python.exe")
    return str(candidate if candidate.exists() else exe)


def write_mcp_config(path: Path | None = None) -> Path:
    path = path or data_dir() / "mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    config = {"mcpServers": {"jarvis": {"command": console_python(), "args": ["-m", "jarvis.mcp_server"]}}}
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
