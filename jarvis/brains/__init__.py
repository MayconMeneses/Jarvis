from jarvis.brains.base import Answer, Brain, BrainUnavailable
from jarvis.brains.claude_cli import ClaudeCLI
from jarvis.brains.router import NoBrainAvailable, Router
from jarvis.config import Config


def build_router(cfg: Config) -> Router:
    available = {"claude": lambda: ClaudeCLI(cfg.claude)}
    brains = [available[name]() for name in cfg.brains if name in available]
    return Router(brains)


__all__ = [
    "Answer", "Brain", "BrainUnavailable", "ClaudeCLI",
    "NoBrainAvailable", "Router", "build_router",
]
