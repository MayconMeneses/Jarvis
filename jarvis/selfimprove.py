"""Autoaperfeiçoamento: caderno de melhorias, mudança no próprio código e verificação.

1. Caderno: a nota "Melhorias" da memória da Jarvis (checklist que o usuário também edita na janela Memória).
   Ideias entram sozinhas (comando não entendido, resposta com nota baixa, todos os
   cérebros falharam) ou a pedido ("Jarvis, anota uma melhoria: ...").
2. "Melhore-se": vira uma tarefa "executar" do Claude Code no repositório da própria
   Jarvis, que só roda depois que o usuário aprova o cartão (e é revisada com o diff).
3. Verificação: depois de "Manter", roda os testes e o benchmark em outro processo
   (com o código novo) e compara com a última verificação aprovada.
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
import time
import unicodedata
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from jarvis import proc as processos
from jarvis import verification
from jarvis.config import data_dir

PROJECT_NAME = "Super Jarvis"
NOTEBOOK = "Melhorias"  # referência da nota na memória
HEADER = ("# Melhorias da Jarvis\n\nIdeias para a Jarvis melhorar a si mesma. Marque [x] o que já foi feito; "
          "apague o que não quiser. Diga \"Jarvis, melhore-se\" para ela propor a próxima.\n\n")
_LINE = re.compile(r"^- \[(?P<done>[ xX])\] (?P<day>\d{4}-\d{2}-\d{2}) — (?P<idea>.+?)(?: _\((?P<origin>[^)]*)\)_)?$")


# ── caderno ──────────────────────────────────────────────────────────────

def _plain(text: str) -> str:
    """Minúsculas, sem acentos e sem pontuação, para comparar ideias."""
    folded = "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", "", folded)


def _memory(mem=None):
    if mem is not None:
        return mem
    from jarvis import memory_db

    return memory_db.open_memory()


def list_ideas(mem=None, include_done: bool = False) -> list[dict]:
    text = _memory(mem).get(NOTEBOOK)
    if not text:
        return []
    ideas = []
    for line in text.splitlines():
        match = _LINE.match(line.strip())
        if match and (include_done or match["done"] == " "):
            ideas.append({"ideia": match["idea"].strip(), "dia": match["day"], "feita": match["done"] != " ",
                          "origem": match["origin"] or ""})
    return ideas


def add_idea(idea: str, origin: str = "pedido do usuário", mem=None) -> bool:
    """Anota uma ideia nova. Retorna False se já existe uma quase igual (não duplica)."""
    idea = " ".join(idea.split())[:300]
    if len(idea) < 8:
        return False
    for existing in list_ideas(mem, include_done=True):
        # Só barra textos quase idênticos (acento, caixa, pontuação). Pedidos diferentes que
        # compartilham o começo ("Entender o pedido: ...") são ideias diferentes.
        if difflib.SequenceMatcher(None, _plain(existing["ideia"]), _plain(idea)).ratio() > 0.93:
            return False
    notes = _memory(mem)
    text = notes.get(NOTEBOOK) or HEADER
    if not text.endswith("\n"):
        text += "\n"
    text += f"- [ ] {date.today().isoformat()} — {idea} _({origin})_\n"
    notes.put(NOTEBOOK, text, "caderno")
    return True


def mark_done(idea: str, mem=None) -> bool:
    notes = _memory(mem)
    text = notes.get(NOTEBOOK)
    if not text:
        return False
    lines, changed = text.splitlines(), False
    for i, line in enumerate(lines):
        match = _LINE.match(line.strip())
        if match and match["done"] == " " and match["idea"].strip() == idea.strip():
            lines[i] = line.replace("- [ ]", "- [x]", 1)
            changed = True
            break
    if changed:
        notes.put(NOTEBOOK, "\n".join(lines) + "\n", "caderno")
    return changed


# ── o próprio projeto ────────────────────────────────────────────────────

def own_repo() -> Path | None:
    """Pasta do código da Jarvis, se esta for a cópia de desenvolvimento (git)."""
    if getattr(sys, "frozen", False):
        return None  # versão instalada: o código empacotado não se altera
    root = Path(__file__).resolve().parent.parent
    return root if (root / ".git").exists() and (root / "pyproject.toml").exists() else None


def ensure_registered(cfg) -> str:
    """Cadastra o repositório da Jarvis como projeto (para o Claude Code poder alterá-lo)."""
    root = own_repo()
    if root is None:
        raise ValueError("a versão instalada não altera o próprio código; use a cópia de desenvolvimento")
    if cfg.projetos.get(PROJECT_NAME) != str(root):
        cfg.projetos[PROJECT_NAME] = str(root)
    return PROJECT_NAME


TASK = (
    "Melhore a própria Jarvis (este repositório) implementando a ideia abaixo.\n"
    "Regras: siga as convenções do código existente; mudança mínima e coerente; adicione ou ajuste "
    "testes em tests/ para cobrir a mudança; NÃO altere config.json, chaves, tokens nem dados do usuário; "
    "NÃO faça commit. Ao final, diga em português o que mudou e por quê.\n\nIdeia: {idea}"
)


def task_for(idea: str) -> str:
    return TASK.format(idea=idea.strip())


# ── verificação depois de "Manter" ───────────────────────────────────────

def _python(root: Path) -> str:
    candidate = Path(sys.executable).with_name("python.exe")
    return str(candidate if candidate.exists() else sys.executable)


def _run(runner, command: list[str], cwd: Path, log: list[dict]):
    """Roda um comando da verificação e registra o que foi pedido (sem a saída, que pode ter dados)."""
    started = time.time()
    label = " ".join([Path(command[0]).name, *command[1:]])
    try:
        done = runner(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                      timeout=900)
    except (OSError, subprocess.SubprocessError) as exc:  # tempo esgotado, programa ausente: não deu para medir
        log.append({"comando": label,
                    "codigo_saida": None, "erro": type(exc).__name__, "duracao_s": round(time.time() - started, 1)})
        return None
    log.append({"comando": label,
                "codigo_saida": done.returncode, "duracao_s": round(time.time() - started, 1)})
    return done


def run_checks(root: Path, runner=processos.executar) -> dict:
    """Testes (pytest) e benchmark offline num processo novo, com o código já alterado."""
    python, log = _python(root), []
    tests = _run(runner, [python, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"], root, log)
    if tests is None:
        result = {"testes_rodaram": False, "testes_ok": False, "testes": "os testes não puderam rodar (tempo esgotado ou erro)"}
    else:
        summary = (tests.stdout or tests.stderr).strip().splitlines()[-1:] or ["sem saída"]
        result = {"testes_rodaram": True, "testes_ok": tests.returncode == 0, "testes": summary[0][:300]}
    out = data_dir() / "verificacao_bench.json"
    out.unlink(missing_ok=True)  # nunca aproveitar o resultado de uma verificação anterior
    bench = _run(runner, [python, "-m", "jarvis.eval", "--sem-semantica", "--json", str(out)], root, log)
    try:
        result["benchmark"] = json.loads(out.read_text(encoding="utf-8")) if bench is not None and bench.returncode == 0 else None
    except (OSError, ValueError):
        result["benchmark"] = None
    result["comandos"] = log
    return result


def baseline_path() -> Path:
    return data_dir() / "benchmark_base.json"


def compare(current: dict | None, base: dict | None, tolerance: float = 0.02) -> list[str]:
    """Métricas que pioraram mais que a tolerância em relação à última verificação aprovada."""
    if not current or not base:
        return []
    worse = []
    for key, value in current.items():
        old = base.get(key)
        if isinstance(value, (int, float)) and isinstance(old, (int, float)) and value < old - tolerance:
            worse.append(f"{key}: {old:.3f} → {value:.3f}")
    return worse


def verify(root: Path, runner=processos.executar, isolate: bool = True) -> dict:
    """Roda a verificação (em cópia limpa do código, se houver Git), compara e grava o registro."""
    started = time.time()
    with verification.clean_copy(root) if isolate else _in_place(root) as (where, isolated):
        checks = run_checks(where, runner)
    try:
        base = json.loads(baseline_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        base = None
    limitations = [] if isolated else ["ambiente não isolado: a verificação rodou na própria pasta do projeto"]
    if base is None:
        limitations.append("sem verificação anterior aprovada para comparar o benchmark")
    checks["pioras"] = compare(checks.get("benchmark"), base)
    checks["adversarial_falhas"] = list((checks.get("benchmark") or {}).get("adversarial_falhas", []))
    checks["limitacoes"] = limitations
    checks["gate"] = verification.gate_of(checks)
    checks["aprovado"] = checks["gate"] == verification.PASS
    if checks["aprovado"]:
        baseline_path().write_text(json.dumps(checks["benchmark"]), encoding="utf-8")  # nova referência
    registro = verification.write_record(root, checks, checks["comandos"], isolated, started)
    checks["registro"] = str(registro) if registro else None
    checks["quando"] = time.time()
    return checks


@contextmanager
def _in_place(root: Path):
    yield root, False
