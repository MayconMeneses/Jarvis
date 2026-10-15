"""Ações que mudam o PC.

A IA só consegue PROPOR uma ação (grava um arquivo pendente). A execução
acontece apenas quando o usuário clica em "Aprovar" na janela, e cada ação é
validada de novo nesse momento, porque o PC pode ter mudado desde a proposta.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

import psutil

from jarvis.config import data_dir
from jarvis.pc import startup

KINDS = ("encerrar_processo", "limpar_temporarios", "desativar_inicializacao")

# Encerrar estes derruba o Windows ou a sessão.
CRITICAL = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "svchost.exe", "dwm.exe", "fontdrvhost.exe",
    "memory compression", "secure system", "lsaiso.exe", "explorer.exe",
    "msmpeng.exe", "securityhealthservice.exe",
}
# Pastas dentro do TEMP que nunca são limpas (sessões ativas do Claude Code).
TEMP_KEEP = {"claude"}


@dataclass
class Action:
    kind: str
    params: dict
    descricao: str
    motivo: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    criada_em: float = field(default_factory=time.time)
    status: str = "pendente"  # pendente | executada | recusada | falhou
    resultado: str = ""


class ActionStore:
    def __init__(self, folder: Path | None = None) -> None:
        self.folder = folder or data_dir() / "acoes"

    def _path(self, action_id: str) -> Path:
        if not action_id.isalnum():
            raise ValueError("id de ação inválido")
        return self.folder / f"{action_id}.json"

    def save(self, action: Action) -> Action:
        self.folder.mkdir(parents=True, exist_ok=True)
        self._path(action.id).write_text(json.dumps(asdict(action), ensure_ascii=False), encoding="utf-8")
        return action

    def get(self, action_id: str) -> Action:
        return Action(**json.loads(self._path(action_id).read_text(encoding="utf-8")))

    def pending_since(self, since: float) -> list[Action]:
        if not self.folder.is_dir():
            return []
        found = [Action(**json.loads(p.read_text(encoding="utf-8"))) for p in self.folder.glob("*.json")]
        return sorted((a for a in found if a.status == "pendente" and a.criada_em >= since),
                      key=lambda a: a.criada_em)


# ── validação (usada ao propor E ao executar) ─────────────────────────────

def check_process(pid: int, nome: str | None = None) -> psutil.Process:
    try:
        proc = psutil.Process(int(pid))
        real_name = proc.name()
    except (psutil.NoSuchProcess, ValueError) as exc:
        raise ValueError(f"processo {pid} não existe mais") from exc
    except psutil.AccessDenied as exc:
        raise ValueError(f"sem permissão para acessar o processo {pid}") from exc
    if real_name.lower() in CRITICAL:
        raise ValueError(f"{real_name} é essencial para o Windows e não pode ser encerrado")
    if nome and real_name.lower() != nome.lower():
        raise ValueError(f"o PID {pid} agora pertence a {real_name}, não a {nome}")
    protected = {os.getpid()} | {p.pid for p in psutil.Process().parents()}
    if proc.pid in protected:
        raise ValueError("não é possível encerrar a própria Jarvis por aqui")
    return proc


def temp_candidates(days: int, temp: Path | None = None) -> tuple[list[Path], int]:
    temp = temp or Path(os.environ["TEMP"])
    cutoff = time.time() - max(0, days) * 86400
    files, total = [], 0
    for entry in temp.iterdir():
        if entry.name.lower() in TEMP_KEEP:
            continue
        paths = [entry] if entry.is_file() else [p for p in entry.rglob("*") if p.is_file()]
        for path in paths:
            try:
                st = path.lstat()
            except OSError:
                continue
            if st.st_mtime < cutoff:
                files.append(path)
                total += st.st_size
    return files, total


# ── propor ────────────────────────────────────────────────────────────────

def propose_kill(store: ActionStore, pid: int, motivo: str) -> Action:
    proc = check_process(pid)
    name = proc.name()
    mem = proc.memory_info().rss / 1024**2
    return store.save(Action(
        "encerrar_processo", {"pid": proc.pid, "nome": name},
        f"Encerrar {name} (PID {proc.pid}, {mem:.0f} MB). Trabalho não salvo nesse programa será perdido.",
        motivo,
    ))


def propose_clean_temp(store: ActionStore, dias: int, motivo: str, temp: Path | None = None) -> Action:
    files, total = temp_candidates(dias, temp)
    if not files:
        raise ValueError(f"não há arquivos temporários com mais de {dias} dia(s)")
    return store.save(Action(
        "limpar_temporarios", {"dias": dias},
        f"Apagar {len(files)} arquivos temporários com mais de {dias} dia(s) (cerca de {total / 1024**3:.2f} GB). "
        "Arquivos em uso são pulados.",
        motivo,
    ))


def propose_disable_startup(store: ActionStore, nome: str, motivo: str, reg=None, folders=None) -> Action:
    item = startup.find_disableable(nome, reg, folders)
    return store.save(Action(
        "desativar_inicializacao", {"nome": item.nome},
        f"Impedir que '{item.nome}' inicie com o Windows (o programa continua instalado).",
        motivo,
    ))


# ── executar (só depois da aprovação do usuário) ──────────────────────────

def execute(action: Action, temp: Path | None = None, reg=None, folders=None) -> str:
    if action.kind == "encerrar_processo":
        proc = check_process(action.params["pid"], action.params["nome"])
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
        return f"{action.params['nome']} foi encerrado."

    if action.kind == "limpar_temporarios":
        files, _ = temp_candidates(int(action.params["dias"]), temp)
        freed = removed = 0
        for path in files:
            try:
                size = path.lstat().st_size
                path.unlink()
                freed += size
                removed += 1
            except OSError:
                pass  # em uso ou sem permissão: pula
        base = temp or Path(os.environ["TEMP"])
        for entry in base.iterdir():  # remove pastas que ficaram vazias
            if entry.is_dir() and entry.name.lower() not in TEMP_KEEP and not any(entry.rglob("*")):
                shutil.rmtree(entry, ignore_errors=True)
        return f"{removed} arquivos apagados, {freed / 1024**3:.2f} GB liberados."

    if action.kind == "desativar_inicializacao":
        return startup.disable(action.params["nome"], reg, folders)

    raise ValueError(f"tipo de ação desconhecido: {action.kind}")


def decide(store: ActionStore, action_id: str, approve: bool, **execute_kwargs) -> Action:
    action = store.get(action_id)
    if action.status != "pendente":
        raise ValueError("esta ação já foi decidida")
    if not approve:
        action.status, action.resultado = "recusada", "Recusada pelo usuário."
        return store.save(action)
    try:
        action.resultado = execute(action, **execute_kwargs)
        action.status = "executada"
    except (ValueError, OSError, psutil.Error) as exc:
        action.status, action.resultado = "falhou", f"Não foi possível: {exc}"
    return store.save(action)
