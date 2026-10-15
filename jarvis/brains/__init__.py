from jarvis.brains.base import Answer, Brain, BrainUnavailable, Message
from jarvis.brains.claude_cli import ClaudeCLI
from jarvis.brains.openai_compat import OpenAICompat
from jarvis.brains.router import NoBrainAvailable, Router
from jarvis.config import Config
from jarvis.keys import get_key


def build_router(cfg: Config) -> Router:
    available = {
        "claude": lambda: ClaudeCLI(cfg.claude),
        "gemini": lambda: OpenAICompat("gemini", cfg.gemini, get_key),
        "nvidia": lambda: OpenAICompat("nvidia", cfg.nvidia, get_key),
    }
    brains = [available[name]() for name in cfg.brains if name in available]
    return Router(brains)


__all__ = [
    "Answer", "Brain", "BrainUnavailable", "ClaudeCLI", "Message",
    "NoBrainAvailable", "OpenAICompat", "Router", "build_router",
]
