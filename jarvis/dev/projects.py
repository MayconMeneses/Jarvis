"""Projetos de código cadastrados e um resumo rápido do estado de cada um (sem IA)."""

from __future__ import annotations

import subprocess
import unicodedata
from pathlib import Path

from jarvis.config import Config


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def resolve(cfg: Config, name: str) -> tuple[str, Path]:
    """Acha o projeto pelo nome, ignorando maiúsculas e acentos."""
    for registered, folder in cfg.projetos.items():
        if _fold(registered) == _fold(name.strip()):
            path = Path(folder)
            if not path.is_dir():
                raise ValueError(f"a pasta do projeto '{registered}' não existe mais: {folder}")
            return registered, path
    known = ", ".join(cfg.projetos) or "nenhum"
    raise ValueError(f"projeto '{name}' não cadastrado (cadastrados: {known})")


def register(cfg: Config, name: str, folder: str) -> Path:
    path = Path(folder.strip().strip('"')).expanduser()
    if not path.is_absolute() or not path.is_dir():
        raise ValueError(f"pasta não encontrada: {folder}")
    name = name.strip()[:60]
    if not name:
        raise ValueError("informe um nome para o projeto")
    cfg.projetos[name] = str(path.resolve())
    return path


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=path, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git falhou")
    return result.stdout.strip()


def is_git_repo(path: Path) -> bool:
    try:
        return _git(path, "rev-parse", "--is-inside-work-tree") == "true"
    except (RuntimeError, OSError, subprocess.TimeoutExpired):
        return False


def status(cfg: Config, name: str) -> dict:
    registered, path = resolve(cfg, name)
    info: dict = {"projeto": registered, "pasta": str(path)}
    if not is_git_repo(path):
        info["git"] = "não é um repositório git"
        return info
    info["branch"] = _git(path, "branch", "--show-current") or "(sem branch)"
    changed = [line for line in _git(path, "status", "--porcelain").splitlines() if line.strip()]
    info["arquivos_alterados"] = len(changed)
    info["alteracoes"] = changed[:15]
    info["ultimos_commits"] = _git(path, "log", "-5", "--pretty=format:%h %ad %s", "--date=short").splitlines()
    return info


def diff_stat(path: Path) -> str:
    try:
        return _git(path, "diff", "--stat") or "nenhuma alteração em arquivos rastreados"
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        return f"não foi possível ler o diff: {exc}"
