"""Regras de estrutura do projeto: sem "god files".

Cada arquivo de código tem uma responsabilidade e no máximo MAX_LINES linhas. Quando um
arquivo cresce além disso, divida por assunto (veja jarvis/ui/api_*.py e jarvis/mcp_tools/).
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MAX_LINES = 300
EXTENSIONS = {".py", ".html", ".css", ".js"}
FOLDERS = ("jarvis", "tests", "packaging")
# Arquivos GERADOS (build de outro projeto), não escritos à mão: fora da regra e fora do Git.
GENERATED = {"jarvis/dashboard/painel.html"}


def source_files():
    for folder in FOLDERS:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.suffix in EXTENSIONS and "__pycache__" not in path.parts:
                relative = path.relative_to(ROOT).as_posix()
                if relative not in GENERATED:
                    yield relative, path


def test_no_god_files():
    too_big = []
    for relative, path in source_files():
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > MAX_LINES:
            too_big.append(f"{relative}: {count} linhas (limite {MAX_LINES})")
    assert not too_big, "Divida estes arquivos por assunto:\n" + "\n".join(too_big)


@pytest.mark.parametrize("module", ["jarvis.ui.api", "jarvis.mcp_server", "jarvis.dev.runs", "jarvis.dev.sessions"])
def test_split_modules_keep_their_public_names(module):
    """Dividir arquivos não pode quebrar quem os importa."""
    import importlib

    imported = importlib.import_module(module)
    expected = {
        "jarvis.ui.api": ["Api"],
        "jarvis.mcp_server": ["server"],
        "jarvis.dev.runs": ["Run", "RunStore", "MODES", "LEVELS", "LABELS", "enqueue", "execute", "review", "RunWorker"],
        "jarvis.dev.sessions": ["SessionReader", "SessionWatcher", "Session", "DESCRICAO", "read_tail"],
    }[module]
    assert all(hasattr(imported, name) for name in expected)
