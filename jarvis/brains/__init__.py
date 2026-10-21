import json
import sys
from pathlib import Path

from jarvis.brains.base import Answer, Brain, BrainUnavailable, Message
from jarvis.brains.claude_cli import ClaudeCLI
from jarvis.brains.claude_session import ClaudeSession
from jarvis.brains import perfis, policy
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
    claude_cfg = perfis.claude_config(cfg)
    claude_kind = ClaudeSession if cfg.claude.sessao_continua else ClaudeCLI
    available = {
        "claude": lambda: claude_kind(claude_cfg, mcp_config=mcp),
        "gemini": lambda: OpenAICompat("gemini", cfg.gemini, get_key),
        "nvidia": lambda: OpenAICompat("nvidia", cfg.nvidia, get_key),
    }
    brains = [available[name]() for name in cfg.brains if name in available]
    from jarvis import config as config_module
    from jarvis.llm.cerebro import LLMLocal
    from jarvis.local.engine import LocalEngine

    local, llm = LocalEngine(), LLMLocal(config_module.load)
    brains += [llm, local]  # o modelo local vem depois das IAs externas; o motor próprio é o último: nunca fica sem resposta

    def prefer(text: str) -> str | None:
        from jarvis import config

        if local.is_direct_command(text):
            return "local"  # comando direto: na hora, sem gastar limite de nenhuma IA
        from jarvis.local import entendimento

        if entendimento.rota_local(text):
            return "local"  # pergunta sobre a própria Jarvis com resposta certa no autoconhecimento: na hora e sem gastar IA
        found, now = local.classify(text), config.load()
        if found and (found[0] in ("criar_com_ia", "llm_instalar", "llm_status") or (now.llm_local and now.somente_independente)):
            return "local"  # gerenciar o cérebro local é com o motor próprio; sem IA externa, o motor só pega o que sabe fazer
        from jarvis.uso import servico

        return policy.preferred(text, config.load().uso_gemini, servico.cota_sob_pressao())  # lido a cada pedido: muda na hora

    seen = {"at": 0.0, "cfg": cfg}

    def visible(brain) -> bool:
        import time

        from jarvis import config

        if time.monotonic() - seen["at"] > 1.0:  # relê a cada pedido (não a cada cérebro): o botão vale na hora
            seen["at"], seen["cfg"] = time.monotonic(), config.load()
        current = seen["cfg"]
        if brain is llm:
            return current.llm_local
        if brain is local:
            return current.modo_independente or current.somente_independente
        return not current.somente_independente

    from jarvis.local import entendimento

    return Router(brains, prefer=prefer, visible=visible, contexto=entendimento.contexto_para_ia)


__all__ = [
    "Answer", "Brain", "BrainUnavailable", "ClaudeCLI", "Message",
    "NoBrainAvailable", "OpenAICompat", "Router", "build_router",
]
