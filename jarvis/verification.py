"""Verificação de uma mudança: estados do resultado, cópia limpa do código e registro por execução.

Estados (nesta ordem de gravidade): FAIL > BLOCKED > NOT_RUN > PASS. Só PASS aprova;
BLOCKED (não deu para medir) e NOT_RUN (nem tentou) nunca contam como aprovação.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from jarvis import __version__
from jarvis.config import data_dir

PASS, FAIL, BLOCKED, NOT_RUN = "PASS", "FAIL", "BLOCKED", "NOT_RUN"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def gate_of(checks: dict) -> str:
    """Resultado geral: um critério reprovado vence qualquer média; sem medição não há aprovação."""
    ran = checks.get("testes_rodaram", True)
    if (ran and not checks.get("testes_ok")) or checks.get("pioras") or checks.get("adversarial_falhas"):
        return FAIL
    if not ran or checks.get("benchmark") is None:
        return BLOCKED
    return PASS


def _git(root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60, creationflags=_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


@contextmanager
def clean_copy(root: Path):
    """Cópia só do que o Git conhece (rastreado + novo não ignorado), numa pasta temporária.

    Assim a verificação não depende de arquivo local ignorado (cache, build, painel.html).
    Sem Git, devolve a própria pasta e quem chamou registra que o ambiente não foi isolado.
    """
    listed = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if listed is None:
        yield root, False
        return
    with tempfile.TemporaryDirectory(prefix="jarvis-verificacao-") as tmp:
        for rel in filter(None, listed.split("\0")):
            source = root / rel
            if source.is_file():
                target = Path(tmp) / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        yield Path(tmp), True


def environment(root: Path, isolated: bool) -> dict:
    status = _git(root, "status", "--porcelain")
    return {
        "versao": __version__,
        "commit": (_git(root, "rev-parse", "HEAD") or "").strip() or None,
        "alteracoes_locais": bool(status and status.strip()),
        "python": platform.python_version(),
        "sistema": platform.platform(),
        "copia_limpa": isolated,
    }


def records_dir() -> Path:
    return data_dir() / "verificacoes"


def write_record(root: Path, checks: dict, commands: list[dict], isolated: bool, started: float) -> Path | None:
    """Um JSON por verificação (sem segredos): o que rodou, em que ambiente e com que resultado."""
    gate = checks["gate"]
    record = {
        "run_id": uuid.uuid4().hex[:12],
        "quando_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "duracao_s": round(time.time() - started, 1),
        "ambiente": environment(root, isolated),
        "comandos": commands,
        "avaliadores": [
            {"nome": "pytest", "resultado": PASS if checks.get("testes_ok") else FAIL, "evidencia": checks.get("testes", "")},
            {"nome": "benchmark", "resultado": BLOCKED if checks.get("benchmark") is None else (FAIL if checks.get("pioras") else PASS),
             "evidencia": "; ".join(checks.get("pioras") or []) or "sem piora"},
            {"nome": "adversarial", "resultado": FAIL if checks.get("adversarial_falhas") else PASS,
             "evidencia": "; ".join(checks.get("adversarial_falhas") or []) or "sem falha"},
        ],
        "gate_result": gate,
        "limitacoes": checks.get("limitacoes", []),
    }
    try:
        folder = records_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime(started))}-{record['run_id']}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except OSError:
        return None
