"""Projetos de código cadastrados, um resumo rápido do estado de cada um (sem IA),
a ficha de informações de cada projeto na memória da Jarvis e a criação de projetos novos.

A ficha é a nota "Projetos/<nome>/Sobre" do banco de memória (jarvis/memory_db.py).
A pasta do projeto só é criada por uma ação aprovada pelo usuário na janela.
"""

from __future__ import annotations

import re
import subprocess
import unicodedata
from datetime import date
from pathlib import Path

from jarvis import memory_db
from jarvis.config import Config
from jarvis.dev import modelos


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
    try:
        info["ultimos_commits"] = _git(path, "log", "-5", "--pretty=format:%h %ad %s", "--date=short").splitlines()
    except RuntimeError:  # repositório novo, ainda sem commits
        info["ultimos_commits"] = []
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


def unregister(cfg: Config, name: str) -> str:
    """Tira o projeto da lista. Não apaga nenhum arquivo (nem a pasta, nem a ficha)."""
    for registered in list(cfg.projetos):
        if _fold(registered) == _fold(name.strip()):
            del cfg.projetos[registered]
            return registered
    raise ValueError(f"projeto '{name}' não cadastrado")


# ── ficha do projeto na memória da Jarvis ────────────────────────────────

INFO_NAME = "Sobre"
SECTIONS = ("Descrição", "Stack", "Objetivos", "Decisões", "Pendências", "Anotações")
MAX_CONTEXT_CHARS = 3000


def project_folder(name: str) -> str:
    """Prefixo das notas do projeto na memória (ex.: Projetos/Comandiva)."""
    return "Projetos/" + (memory_db.clean_title(name) or "projeto")


def info_ref(name: str) -> str:
    return f"{project_folder(name)}/{INFO_NAME}"


def _section(name: str) -> str:
    for known in SECTIONS:
        if _fold(known) == _fold(name.strip()):
            return known
    known = ", ".join(SECTIONS)
    raise ValueError(f"seção inválida: {name} (use {known})")


def _parse_info(text: str) -> dict[str, list[str]]:
    parts: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            parts.setdefault(current, [])
        elif current is not None and line.strip():
            parts[current].append(line.rstrip())
    return parts


def _render_info(name: str, parts: dict[str, list[str]]) -> str:
    out = [f"# {name}", "", "Ficha do projeto mantida pela Jarvis. Pode editar à vontade.", ""]
    order = list(SECTIONS) + [k for k in parts if k not in SECTIONS]
    for key in order:
        if parts.get(key):
            out += [f"## {key}", *parts[key], ""]
    return "\n".join(out)


def add_info(cfg: Config, mem, name: str, text: str, section: str = "Anotações") -> str:
    """Acrescenta uma informação à ficha. "Descrição" substitui a anterior; o resto acumula."""
    registered, _ = resolve(cfg, name)
    key = _section(section)
    text = " ".join(text.split())[:1500]
    if not text:
        raise ValueError("escreva a informação")
    ref = info_ref(registered)
    parts = _parse_info(mem.get(ref) or "")
    if key == "Descrição":
        parts[key] = [text]
    else:
        parts.setdefault(key, []).append(f"- {date.today().isoformat()}: {text}")
    return mem.put(ref, _render_info(registered, parts), "projeto", title=registered)


def read_info(cfg: Config, mem, name: str) -> str:
    """Texto da ficha, ou "" se ainda não houver."""
    registered, _ = resolve(cfg, name)
    return mem.get(info_ref(registered)) or ""


# ── projeto novo (só executado depois da aprovação) ──────────────────────

_BAD_FOLDER = re.compile(r'[\\/:*?"<>|]')


def plan_new(cfg: Config, name: str, parent: str) -> Path:
    """Valida e devolve a pasta que será criada. Chamado ao propor E ao executar."""
    name = name.strip()[:60]
    folder_name = _BAD_FOLDER.sub("", name).strip().rstrip(".")
    if not folder_name:
        raise ValueError("informe um nome para o projeto")
    if any(_fold(n) == _fold(name) for n in cfg.projetos):
        raise ValueError(f"já existe um projeto cadastrado com o nome '{name}'")
    base = Path(parent.strip().strip('"')).expanduser()
    if not base.is_absolute() or not base.is_dir():
        raise ValueError(f"pasta onde criar o projeto não encontrada: {parent}")
    target = base.resolve() / folder_name
    if target.exists():
        raise ValueError(f"já existe uma pasta em {target}")
    return target


def create(cfg: Config, name: str, parent: str, description: str = "", git: bool = True, modelo: str = "") -> Path:
    """Cria a pasta (README, ou um modelo pronto de sistema), git init sem commit, e cadastra o projeto."""
    target = plan_new(cfg, name, parent)
    modelo = modelos.normalize(modelo) if modelo else ""  # modelo inválido falha ANTES de criar a pasta
    target.mkdir()
    if modelo:
        modelos.generate(target, modelo, name, description)
    else:
        (target / "README.md").write_text(f"# {name.strip()}\n" + (f"\n{description.strip()}\n" if description.strip() else ""), encoding="utf-8")
    if git:
        _git(target, "init", "-q", "-b", "main")
    cfg.projetos[name.strip()[:60]] = str(target)
    return target
