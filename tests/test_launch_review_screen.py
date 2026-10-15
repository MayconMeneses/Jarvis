import io
import json
import subprocess
import types

import pytest

from jarvis.config import ClaudeConfig, Config
from jarvis.dev import projects, runs
from jarvis.pc import launcher, screen

APPS = {"WhatsApp": "5319275A.WhatsAppDesktop!App", "Visual Studio Code": "Microsoft.VisualStudioCode",
        "Google Chrome": "Chrome", "Paint": "Microsoft.Paint!App"}


class Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)


# ── abrir programas, sites, pastas, projetos ─────────────────────────────

@pytest.mark.parametrize("query,expected", [
    ("whatsapp", "WhatsApp"), ("VS Code", "Visual Studio Code"), ("zap", "WhatsApp"), ("visual studio", "Visual Studio Code"),
    ("chrome", "Google Chrome"), ("paimt", "Paint"), ("excel", None),
])
def test_find_app_exact_partial_and_fuzzy(query, expected):
    found = launcher.find_app(query, APPS)
    assert (found[0] if found else None) == expected


def test_open_app_uses_start_menu_id_or_builtin():
    rec = Recorder()
    assert launcher.open_app("WhatsApp", APPS, runner=rec) == "WhatsApp aberto."
    assert rec.calls[-1] == ["explorer.exe", "shell:AppsFolder\\5319275A.WhatsAppDesktop!App"]
    launcher.open_app("calculadora", APPS, runner=rec)
    assert rec.calls[-1] == ["calc.exe"]
    with pytest.raises(ValueError, match="não encontrei"):
        launcher.open_app("programa-inexistente-xyz", APPS, runner=rec)


def test_browser_word_opens_default_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    launcher.open_app("navegador", APPS, runner=Recorder())
    assert opened == ["https://www.google.com"]


def test_open_site_only_http(monkeypatch):
    opened = []
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    launcher.open_site("github.com/maycon")
    launcher.open_site("http://localhost:3000")
    assert opened == ["https://github.com/maycon", "http://localhost:3000"]
    for bad in ("javascript:alert(1)", "abre aquele site", "file"):
        with pytest.raises(ValueError):
            launcher.open_site(bad)


def test_open_folder_special_absolute_and_missing(tmp_path, monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(launcher, "special_folders", lambda: {"downloads": tmp_path})
    launcher.open_folder("Downloads", runner=rec)
    launcher.open_folder(str(tmp_path), runner=rec)
    assert rec.calls == [["explorer.exe", str(tmp_path)]] * 2
    for bad in ("pasta-que-nao-existe", str(tmp_path / "nao"), "relativa\\pasta"):
        with pytest.raises(ValueError):
            launcher.open_folder(bad, runner=rec)


def test_open_project_in_vscode_and_terminal(tmp_path, monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(launcher.shutil, "which", lambda name: f"C:/bin/{name}")
    msg = launcher.open_project(Config(projetos={"Comandiva": str(tmp_path)}), "comandiva", True, runner=rec)
    assert rec.calls == [["C:/bin/code", str(tmp_path)], ["wt", "-d", str(tmp_path)]]
    assert "VS Code" in msg and "Terminal" in msg


def test_app_index_is_cached_for_a_day(tmp_path):
    calls = []

    def loader():
        calls.append(1)
        return dict(APPS)

    cache = tmp_path / "apps.json"
    assert launcher.app_index(cache, loader, now=1000.0) == APPS
    launcher.app_index(cache, loader, now=1000.0 + 3600)
    assert len(calls) == 1
    launcher.app_index(cache, loader, now=1000.0 + 25 * 3600)
    assert len(calls) == 2


# ── revisão das mudanças do Claude Code ──────────────────────────────────

def git(path, *args):
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "app"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "t@t")
    git(path, "config", "user.name", "t")
    for name, text in {"a.py": "a = 1\n", "b.py": "b = 1\n", "d.py": "d = 1\n"}.items():
        (path / name).write_text(text)
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "base")
    (path / "a.py").write_text("a = 1\nminha_mudanca = True\n")  # trabalho do usuário, sem commit
    (path / "e.txt").write_text("rascunho do usuário\n")          # não rastreado, já existia
    return path


def claude_edits(path):
    (path / "a.py").write_text("a = 2\nminha_mudanca = True\n")
    (path / "b.py").write_text("b = 2\n")
    (path / "novo").mkdir()
    (path / "novo" / "c.py").write_text("c = 1\n")
    (path / "d.py").unlink()
    (path / "e.txt").write_text("rascunho alterado\n")


def test_changes_are_detected_and_undo_restores_the_users_own_version(repo):
    snap = projects.snapshot(repo)
    claude_edits(repo)
    changes = {c["arquivo"]: c["tipo"] for c in projects.changes_since(repo, snap)}
    assert changes == {"a.py": "modificado", "b.py": "modificado", "novo/c.py": "novo",
                       "d.py": "apagado", "e.txt": "modificado_sem_backup"}
    diff = projects.diff_text(repo, snap, projects.changes_since(repo, snap))
    assert "-a = 1" in diff and "+a = 2" in diff and "+c = 1" in diff

    message = projects.undo_changes(repo, snap, projects.changes_since(repo, snap))
    assert (repo / "a.py").read_text() == "a = 1\nminha_mudanca = True\n"  # a mudança do usuário ficou
    assert (repo / "b.py").read_text() == "b = 1\n"
    assert (repo / "d.py").read_text() == "d = 1\n"
    assert not (repo / "novo" / "c.py").exists()
    assert "e.txt" in message  # avisa que esse não tinha cópia


def test_execution_records_preview_and_review_keep_or_undo(repo, tmp_path):
    store = runs.RunStore(tmp_path / "runs")
    cfg = Config(projetos={"App": str(repo)})
    run = runs.enqueue(store, cfg, "App", "executar", "mudar b")

    def runner(cmd, **kw):
        (repo / "b.py").write_text("b = 99\n")
        return types.SimpleNamespace(returncode=0, stdout=json.dumps({"result": "Alterei b.py"}), stderr="")

    done = runs.execute(run, store, ClaudeConfig(executable="x"), runner=runner)
    assert done.revisao == "pendente" and done.mudancas == [{"arquivo": "b.py", "tipo": "modificado"}]
    assert "+b = 99" in done.diff and "a.py" not in done.diff  # mudança prévia do usuário fica fora

    undone = runs.review(store, done.id, keep=False)
    assert undone.revisao == "desfeita" and (repo / "b.py").read_text() == "b = 1\n"
    with pytest.raises(ValueError, match="já foi decidida"):
        runs.review(store, done.id, keep=True)


def test_execution_without_changes_needs_no_review(repo, tmp_path):
    store = runs.RunStore(tmp_path / "runs")
    run = runs.enqueue(store, Config(projetos={"App": str(repo)}), "App", "executar", "nada")
    runner = lambda cmd, **kw: types.SimpleNamespace(returncode=0, stdout=json.dumps({"result": "Nada a fazer"}), stderr="")  # noqa: E731
    assert runs.execute(run, store, ClaudeConfig(executable="x"), runner=runner).revisao == ""


# ── olhar a tela ─────────────────────────────────────────────────────────

def test_capture_returns_resized_png():
    from PIL import Image

    png = screen.capture(grab=lambda: Image.new("RGB", (3840, 1080), "blue"), hide=False)
    with Image.open(io.BytesIO(png)) as img:
        assert img.format == "PNG" and img.size[0] == 1568 and img.size[1] in (441, 442)
