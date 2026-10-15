"""Configuração da Jarvis.

Fica em %APPDATA%\\SuperJarvis\\config.json. Na primeira execução o arquivo é
criado com os valores padrão para o usuário editar.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

APP_NAME = "SuperJarvis"


def config_dir() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / APP_NAME


def data_dir() -> Path:
    """Dados locais que não devem sincronizar (logs, banco técnico)."""
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME


@dataclass
class ClaudeConfig:
    executable: str = "claude"
    model: str = ""  # vazio = modelo padrão da assinatura
    timeout_seconds: int = 180


@dataclass
class Config:
    user_name: str = "Maycon"
    language: str = "pt-BR"
    city: str = ""
    obsidian_vault: str = ""
    brains: list[str] = field(default_factory=lambda: ["claude"])
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)

    @classmethod
    def from_dict(cls, raw: dict) -> "Config":
        known = {f.name for f in fields(cls)}
        values = {k: v for k, v in raw.items() if k in known}
        if isinstance(values.get("claude"), dict):
            claude_known = {f.name for f in fields(ClaudeConfig)}
            values["claude"] = ClaudeConfig(
                **{k: v for k, v in values["claude"].items() if k in claude_known}
            )
        return cls(**values)


def load(path: Path | None = None) -> Config:
    path = path or config_dir() / "config.json"
    if not path.exists():
        cfg = Config()
        save(cfg, path)
        return cfg
    return Config.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save(cfg: Config, path: Path | None = None) -> None:
    path = path or config_dir() / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8"
    )
