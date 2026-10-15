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
    return _git_raw(path, *args).strip()


def _git_raw(path: Path, *args: str) -> str:
    """Saída sem cortar espaços: no `git status --porcelain` o 1º caractere faz parte do código."""
    result = subprocess.run(
        ["git", *args], cwd=path, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git falhou")
    return result.stdout


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


# ── retrato antes/depois de uma execução (para revisar e desfazer) ─────────

def _file_hash(path: Path) -> str | None:
    import hashlib

    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()
    except OSError:
        return None


def status_map(path: Path) -> dict[str, str]:
    """{arquivo: código XY do git status}, incluindo arquivos novos dentro de pastas novas."""
    out = _git_raw(path, "status", "--porcelain=v1", "-uall", "-z")
    entries, items = {}, out.split("\0")
    i = 0
    while i < len(items):
        item = items[i]
        if len(item) > 3:
            code, name = item[:2], item[3:]
            entries[name] = code
            if code[0] in "RC":  # renomeado: o próximo item é o nome antigo
                i += 1
        i += 1
    return entries


def snapshot(path: Path) -> dict:
    """Estado antes da execução: arquivos já alterados (com hash) e um commit de stash do worktree."""
    before = {name: [code, _file_hash(path / name)] for name, code in status_map(path).items()}
    base = _git(path, "stash", "create")  # não altera nada; vazio se não há mudanças rastreadas
    return {"base": base, "antes": before}


def changes_since(path: Path, snap: dict) -> list[dict]:
    """Arquivos que a execução criou, alterou ou apagou (comparando com o retrato)."""
    before, after = snap["antes"], status_map(path)
    changed = []
    for name in sorted(set(before) | set(after)):
        old = before.get(name)  # [código, hash] ou None (arquivo estava limpo)
        new_code, new_hash = after.get(name), _file_hash(path / name)
        if old is not None and old[0] == new_code and old[1] == new_hash:
            continue  # não mudou durante a execução
        if old is not None and old[0] == "??":
            kind = "modificado_sem_backup"  # não rastreado que já existia: o git não tem cópia
        elif new_hash is None:
            kind = "apagado"
        elif old is None and new_code == "??":
            kind = "novo"
        else:
            kind = "modificado"
        changed.append({"arquivo": name, "tipo": kind})
    return changed


def diff_text(path: Path, snap: dict, changes: list[dict], limit: int = 20000) -> str:
    tracked = [c["arquivo"] for c in changes if c["tipo"] in ("modificado", "apagado")]
    parts = []
    if tracked:
        parts.append(_git(path, "diff", snap["base"] or "HEAD", "--", *tracked))
    for change in changes:
        if change["tipo"] == "novo":
            try:
                lines = (path / change["arquivo"]).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            body = "\n".join("+" + line for line in lines[:300])
            parts.append(f"--- (arquivo novo)\n+++ {change['arquivo']}\n{body}")
    text = "\n\n".join(p for p in parts if p)
    return text[:limit] + ("\n... (diff cortado)" if len(text) > limit else "")


def undo_changes(path: Path, snap: dict, changes: list[dict]) -> str:
    """Volta cada arquivo ao estado de antes da execução (não mexe no que já era seu)."""
    reverted, skipped = 0, []
    source = snap["base"] or "HEAD"
    for change in changes:
        name, kind = change["arquivo"], change["tipo"]
        target = path / name
        if kind == "novo":
            target.unlink(missing_ok=True)
            reverted += 1
        elif kind == "modificado_sem_backup":
            skipped.append(name)
        else:
            try:
                _git(path, "restore", f"--source={source}", "--worktree", "--", name)
                reverted += 1
            except RuntimeError:
                skipped.append(name)
    message = f"{reverted} arquivo(s) voltaram ao estado anterior."
    if skipped:
        message += " Não foi possível desfazer (sem cópia anterior): " + ", ".join(skipped)
    return message


def diff_stat(path: Path) -> str:
    try:
        return _git(path, "diff", "--stat") or "nenhuma alteração em arquivos rastreados"
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        return f"não foi possível ler o diff: {exc}"
