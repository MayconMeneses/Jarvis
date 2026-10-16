"""Autoaperfeiçoamento: caderno de melhorias, mudança no próprio código e verificação.

1. Caderno: <cofre>/Jarvis/Melhorias.md (checklist Markdown que o usuário também edita).
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
from datetime import date
from pathlib import Path

from jarvis.config import data_dir

PROJECT_NAME = "Super Jarvis"
NOTEBOOK = "Melhorias.md"
HEADER = ("# Melhorias da Jarvis\n\nIdeias para a Jarvis melhorar a si mesma. Marque [x] o que já foi feito; "
          "apague o que não quiser. Diga \"Jarvis, melhore-se\" para ela propor a próxima.\n\n")
_LINE = re.compile(r"^- \[(?P<done>[ xX])\] (?P<day>\d{4}-\d{2}-\d{2}) — (?P<idea>.+?)(?: _\((?P<origin>[^)]*)\)_)?$")


# ── caderno ──────────────────────────────────────────────────────────────

def _plain(text: str) -> str:
    """Minúsculas, sem acentos e sem pontuação, para comparar ideias."""
    folded = "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", "", folded)


def notebook_path(vault=None) -> Path:
    return (vault.home if vault is not None else data_dir()) / NOTEBOOK


def list_ideas(vault=None, include_done: bool = False) -> list[dict]:
    path = notebook_path(vault)
    if not path.exists():
        return []
    ideas = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _LINE.match(line.strip())
        if match and (include_done or match["done"] == " "):
            ideas.append({"ideia": match["idea"].strip(), "dia": match["day"], "feita": match["done"] != " ",
                          "origem": match["origin"] or ""})
    return ideas


def add_idea(idea: str, origin: str = "pedido do usuário", vault=None) -> bool:
    """Anota uma ideia nova. Retorna False se já existe uma quase igual (não duplica)."""
    idea = " ".join(idea.split())[:300]
    if len(idea) < 8:
        return False
    for existing in list_ideas(vault, include_done=True):
        # Só barra textos quase idênticos (acento, caixa, pontuação). Pedidos diferentes que
        # compartilham o começo ("Entender o pedido: ...") são ideias diferentes.
        if difflib.SequenceMatcher(None, _plain(existing["ideia"]), _plain(idea)).ratio() > 0.93:
            return False
    path = notebook_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else HEADER
    if not text.endswith("\n"):
        text += "\n"
    text += f"- [ ] {date.today().isoformat()} — {idea} _({origin})_\n"
    path.write_text(text, encoding="utf-8")
    return True


def mark_done(idea: str, vault=None) -> bool:
    path = notebook_path(vault)
    if not path.exists():
        return False
    lines, changed = path.read_text(encoding="utf-8").splitlines(), False
    for i, line in enumerate(lines):
        match = _LINE.match(line.strip())
        if match and match["done"] == " " and match["idea"].strip() == idea.strip():
            lines[i] = line.replace("- [ ]", "- [x]", 1)
            changed = True
            break
    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
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


def run_checks(root: Path, runner=subprocess.run) -> dict:
    """Testes (pytest) e benchmark offline num processo novo, com o código já alterado."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    python = _python(root)
    tests = runner([python, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"], cwd=root,
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, creationflags=flags)
    summary = (tests.stdout or tests.stderr).strip().splitlines()[-1:] or ["sem saída"]
    result = {"testes_ok": tests.returncode == 0, "testes": summary[0][:300]}
    out = data_dir() / "verificacao_bench.json"
    bench = runner([python, "-m", "jarvis.eval", "--sem-semantica", "--json", str(out)], cwd=root,
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, creationflags=flags)
    try:
        result["benchmark"] = json.loads(out.read_text(encoding="utf-8")) if bench.returncode == 0 else None
    except (OSError, ValueError):
        result["benchmark"] = None
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


def verify(root: Path, runner=subprocess.run) -> dict:
    checks = run_checks(root, runner)
    try:
        base = json.loads(baseline_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        base = None
    checks["pioras"] = compare(checks.get("benchmark"), base)
    checks["aprovado"] = checks["testes_ok"] and not checks["pioras"]
    if checks["aprovado"] and checks.get("benchmark"):
        baseline_path().write_text(json.dumps(checks["benchmark"]), encoding="utf-8")  # nova referência
    checks["quando"] = time.time()
    return checks
