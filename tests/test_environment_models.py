import sys
import types
from pathlib import Path

import pytest

from jarvis import environment
from jarvis.config import ClaudeConfig, Config
from jarvis.voice import models


# ── Claude Code e git ────────────────────────────────────────────────────

def test_find_claude_uses_path_then_the_official_install_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(environment.shutil, "which", lambda name: r"C:\bin\claude.exe" if name == "claude" else None)
    assert environment.find_claude("claude") == r"C:\bin\claude.exe"

    monkeypatch.setattr(environment.shutil, "which", lambda name: None)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert environment.find_claude() is None
    exe = tmp_path / ".local" / "bin" / "claude.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"x")
    assert environment.find_claude() == str(exe)
    assert environment.find_claude("outro-nome") is None  # o atalho vale só para o executável padrão


def test_notices_explain_what_is_missing_and_stay_silent_when_all_is_there(monkeypatch):
    monkeypatch.setattr(environment, "find_claude", lambda exe="claude": None)
    monkeypatch.setattr(environment, "find_git", lambda: None)
    both = environment.notices(Config())
    assert len(both) == 2 and environment.CLAUDE_URL in both[0] and environment.GIT_URL in both[1]
    assert "só entende comandos simples" in both[0]
    assert "Gemini ou a NVIDIA" in environment.notices(Config(), has_other_brain=True)[0]

    monkeypatch.setattr(environment, "find_claude", lambda exe="claude": "claude.exe")
    monkeypatch.setattr(environment, "find_git", lambda: "git.exe")
    assert environment.notices(Config()) == []


def test_claude_commands_use_the_detected_executable(monkeypatch):
    from jarvis.brains.claude_cli import ClaudeCLI

    monkeypatch.setattr(environment, "find_claude", lambda exe="claude": r"C:\Users\x\.local\bin\claude.exe")
    assert ClaudeCLI(ClaudeConfig()).command("sistema")[0] == r"C:\Users\x\.local\bin\claude.exe"
    monkeypatch.setattr(environment, "find_claude", lambda exe="claude": None)
    assert ClaudeCLI(ClaudeConfig()).command("sistema")[0] == "claude"  # sem achar, o erro vem claro ao executar


# ── modelo de voz ────────────────────────────────────────────────────────

def make_model(folder: Path) -> Path:
    folder.mkdir(parents=True)
    (folder / "model.bin").write_bytes(b"m")
    (folder / "config.json").write_text("{}", encoding="utf-8")
    return folder


@pytest.fixture
def roots(tmp_path, monkeypatch):
    bundled, own = tmp_path / "app" / "modelos", tmp_path / "dados" / "modelos"
    monkeypatch.setattr(models, "bundled_root", lambda: bundled)
    monkeypatch.setattr(models, "own_root", lambda: own)
    return bundled, own


def no_cache(size, **kw):
    raise FileNotFoundError("não está no cache")


def test_bundled_model_wins_and_nothing_is_downloaded(roots):
    bundled, own = roots
    make_model(bundled / "whisper-small")
    make_model(own / "whisper-small")
    got = models.resolve_whisper("small", download=lambda *a, **k: pytest.fail("não deve baixar"))
    assert got == str(bundled / "whisper-small")


def test_own_folder_is_used_when_the_installer_has_no_model(roots):
    _, own = roots
    make_model(own / "whisper-base")
    assert models.resolve_whisper("base", download=no_cache) == str(own / "whisper-base")


def test_half_copied_model_is_not_trusted(roots):
    bundled, own = roots
    (bundled / "whisper-small").mkdir(parents=True)
    (bundled / "whisper-small" / "config.json").write_text("{}", encoding="utf-8")  # sem model.bin
    calls = []

    def download(size, **kw):
        calls.append(kw)
        if kw.get("local_files_only"):
            raise FileNotFoundError
        return str(own / "baixado")

    assert models.resolve_whisper("small", download=download) == str(own / "baixado")
    assert calls[-1] == {"output_dir": str(own / "whisper-small")}


def test_existing_user_cache_is_reused_but_never_written(roots):
    seen = []

    def download(size, **kw):
        seen.append(kw)
        return r"C:\Users\x\.cache\huggingface\hub\snapshots\abc"

    assert models.resolve_whisper("small", download=download).endswith("abc")
    assert seen == [{"local_files_only": True}]


def test_download_goes_to_own_folder_and_warns_the_user(roots):
    _, own = roots
    said = []

    def download(size, **kw):
        if kw.get("local_files_only"):
            raise FileNotFoundError
        return kw["output_dir"]

    got = models.resolve_whisper("small", said.append, download)
    assert got == str(own / "whisper-small") and len(said) == 1 and "465 MB" in said[0] and "primeira vez" in said[0]


def test_download_failure_explains_what_to_do(roots):
    def download(size, **kw):
        raise OSError("sem internet")

    with pytest.raises(RuntimeError, match="sem internet.*internet e abra a Jarvis de novo"):
        models.resolve_whisper("small", download=download)


def test_a_folder_path_in_the_config_is_used_as_is(tmp_path):
    assert models.resolve_whisper(str(tmp_path), download=lambda *a, **k: pytest.fail("não deve baixar")) == str(tmp_path)


def test_transcriber_loads_the_resolved_folder_and_reports_status(monkeypatch):
    from jarvis.voice.stt import Transcriber

    created = []
    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = lambda path, **kw: created.append((path, kw)) or "modelo"
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    monkeypatch.setattr(models, "resolve_whisper", lambda size, on_status: (on_status("baixando"), r"D:\modelo")[1])
    said = []
    t = Transcriber("small", on_status=said.append)
    t.warm_up()
    t.warm_up()  # carrega uma vez só
    assert said == ["baixando"] and len(created) == 1
    assert created[0][0] == r"D:\modelo" and created[0][1]["device"] == "cpu" and created[0][1]["compute_type"] == "int8"


def test_default_roots_point_next_to_the_app_and_into_the_user_data(monkeypatch, tmp_path):
    monkeypatch.setattr(models.sys, "frozen", True, raising=False)
    monkeypatch.setattr(models.sys, "executable", str(tmp_path / "Jarvis.exe"))
    assert models.bundled_root() == tmp_path / "modelos"
    monkeypatch.undo()
    assert models.bundled_root().parts[-2:] == ("packaging", "modelos")
    assert models.own_root().parts[-2:] == ("SuperJarvis", "modelos")


# ── janela e instalador ──────────────────────────────────────────────────

def test_window_api_reports_notices(monkeypatch):
    pytest.importorskip("webview")
    from jarvis import keys
    from jarvis.ui.app import Api

    monkeypatch.setattr(environment, "find_claude", lambda exe="claude": None)
    monkeypatch.setattr(environment, "find_git", lambda: "git.exe")
    monkeypatch.setattr(keys, "get_key", lambda p: "chave" if p == "gemini" else None)
    api = Api(Config(), conversation=None)
    [notice] = api.environment_notices()
    assert "Claude Code" in notice and "Gemini" in notice


def test_installer_script_ships_the_optional_model_and_keeps_user_data():
    iss = (Path(__file__).resolve().parents[1] / "packaging" / "installer.iss").read_text(encoding="utf-8")
    assert r'Source: "modelos\*"; DestDir: "{app}\modelos"' in iss and "skipifsourcedoesntexist" in iss
    assert "memória da Jarvis" in iss and "Obsidian" not in iss
    assert not any(ord(c) < 32 and c not in "\r\n\t" for c in iss)  # nenhum caractere de controle por engano
