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
class ProviderConfig:
    """Provedor com API compatível com OpenAI. A chave fica no cofre do Windows."""

    base_url: str = ""
    model: str = ""
    timeout_seconds: int = 60


def _gemini() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        model="gemini-flash-latest",
    )


def _nvidia() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://integrate.api.nvidia.com/v1",
        model="meta/llama-3.3-70b-instruct",
    )


def _only_known(kind: type, raw: dict) -> dict:
    known = {f.name for f in fields(kind)}
    return {k: v for k, v in raw.items() if k in known}


@dataclass
class Config:
    user_name: str = "Maycon"
    language: str = "pt-BR"
    city: str = ""
    obsidian_vault: str = ""
    # Ordem de tentativa; quem falhar ou estiver sem chave é pulado.
    brains: list[str] = field(default_factory=lambda: ["claude", "gemini", "nvidia"])
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    gemini: ProviderConfig = field(default_factory=_gemini)
    nvidia: ProviderConfig = field(default_factory=_nvidia)

    @classmethod
    def from_dict(cls, raw: dict) -> "Config":
        values = _only_known(cls, raw)
        nested = {"claude": ClaudeConfig, "gemini": ProviderConfig, "nvidia": ProviderConfig}
        defaults = cls()
        for name, kind in nested.items():
            if isinstance(values.get(name), dict):
                base = asdict(getattr(defaults, name))
                base.update(_only_known(kind, values[name]))
                values[name] = kind(**base)
        return cls(**values)


def load(path: Path | None = None) -> Config:
    path = path or config_dir() / "config.json"
    if not path.exists():
        cfg = Config()
        save(cfg, path)
        return cfg
    raw = json.loads(path.read_text(encoding="utf-8"))
    cfg = Config.from_dict(raw)
    if asdict(cfg) != raw:  # completa o arquivo com campos novos de versões recentes
        save(cfg, path)
    return cfg


def save(cfg: Config, path: Path | None = None) -> None:
    path = path or config_dir() / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8"
    )
