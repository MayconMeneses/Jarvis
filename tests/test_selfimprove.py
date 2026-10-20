import json
import subprocess
import types
from pathlib import Path

import pytest

from jarvis import selfimprove, verification
from jarvis.config import Config
from jarvis.dev import runs
from jarvis.memory_db import MemoryDB


@pytest.fixture
def vault(tmp_path):
    return MemoryDB(tmp_path / "memoria.db")


# ── caderno de melhorias ─────────────────────────────────────────────────

def test_notebook_adds_lists_and_marks_done(vault):
    assert selfimprove.add_idea("Entender o pedido: \"abre a pasta de fotos\"", "pedido não entendido", vault)
    assert selfimprove.add_idea("Falar mais devagar nas notícias", "pedido do usuário", vault)
    ideas = selfimprove.list_ideas(vault)
    assert [i["ideia"] for i in ideas] == ["Entender o pedido: \"abre a pasta de fotos\"", "Falar mais devagar nas notícias"]
    assert ideas[0]["origem"] == "pedido não entendido" and not ideas[0]["feita"]

    assert selfimprove.mark_done("Falar mais devagar nas notícias", vault)
    assert [i["ideia"] for i in selfimprove.list_ideas(vault)] == ["Entender o pedido: \"abre a pasta de fotos\""]
    assert len(selfimprove.list_ideas(vault, include_done=True)) == 2
    text = vault.get(selfimprove.NOTEBOOK)
    assert text.startswith("# Melhorias da Jarvis") and "- [x] " in text


def test_similar_or_tiny_ideas_are_not_duplicated(vault):
    assert selfimprove.add_idea("Melhorar a resposta sobre o clima de amanhã", "qualidade baixa", vault)
    assert not selfimprove.add_idea("Melhorar a resposta sobre o clima de amanha", "qualidade baixa", vault)
    assert not selfimprove.add_idea("oi", "pedido do usuário", vault)
    assert len(selfimprove.list_ideas(vault)) == 1


def test_user_edits_in_the_memory_window_are_respected(vault):
    selfimprove.add_idea("Ideia que o usuário vai apagar do caderno", "teste", vault)
    selfimprove.add_idea("Ideia que o usuário vai manter no caderno", "teste", vault)
    lines = [l for l in vault.get(selfimprove.NOTEBOOK).splitlines() if "apagar" not in l]
    vault.edit(selfimprove.NOTEBOOK, "\n".join(lines) + "\n")
    assert [i["ideia"] for i in selfimprove.list_ideas(vault)] == ["Ideia que o usuário vai manter no caderno"]


def test_notebook_uses_the_default_memory_when_none_is_given(tmp_path, monkeypatch):
    from jarvis import config

    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)
    assert selfimprove.add_idea("Ideia anotada sem memória informada", "teste", None)
    assert [i["ideia"] for i in selfimprove.list_ideas()] == ["Ideia anotada sem memória informada"]
    assert (tmp_path / "memoria.db").exists()


# ── o próprio projeto ────────────────────────────────────────────────────

def test_task_has_safety_rules_and_the_idea():
    task = selfimprove.task_for("  Entender 'abre a pasta de fotos'  ")
    assert task.endswith("Ideia: Entender 'abre a pasta de fotos'")
    for rule in ("NÃO faça commit", "config.json", "testes em tests/"):
        assert rule in task


def test_installed_version_never_edits_itself(monkeypatch):
    monkeypatch.setattr(selfimprove.sys, "frozen", True, raising=False)
    assert selfimprove.own_repo() is None
    with pytest.raises(ValueError, match="versão instalada"):
        selfimprove.ensure_registered(Config())


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Uma 'cópia de desenvolvimento' de mentira: não depende de haver .git na pasta onde os testes rodam."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    monkeypatch.setattr(selfimprove, "__file__", str(tmp_path / "jarvis" / "selfimprove.py"))
    return tmp_path


def test_dev_copy_is_registered_as_a_project(fake_repo):
    root = selfimprove.own_repo()
    assert root is not None and (root / ".git").exists()
    cfg = Config()
    assert selfimprove.ensure_registered(cfg) == "Super Jarvis" and cfg.projetos["Super Jarvis"] == str(root)


# ── verificação ──────────────────────────────────────────────────────────

BASE = {"comandos_acuracia": 1.0, "validacao_acuracia": 0.947, "resumo_rougeL": 0.35}


def test_compare_flags_only_real_regressions():
    assert selfimprove.compare({"comandos_acuracia": 1.0, "validacao_acuracia": 0.95, "resumo_rougeL": 0.34}, BASE) == []
    worse = selfimprove.compare({"comandos_acuracia": 1.0, "validacao_acuracia": 0.90, "resumo_rougeL": 0.35}, BASE)
    assert worse == ["validacao_acuracia: 0.947 → 0.900"]
    assert selfimprove.compare(None, BASE) == [] and selfimprove.compare(BASE, None) == []


def fake_runner(tests_ok=True, bench=None, tmp=None):
    def runner(cmd, **kw):
        if "pytest" in cmd:
            return types.SimpleNamespace(returncode=0 if tests_ok else 1, stdout="..\n316 passed in 40s\n", stderr="")
        Path(cmd[cmd.index("--json") + 1]).write_text(json.dumps(bench or BASE), encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    return runner


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(selfimprove, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(verification, "data_dir", lambda: tmp_path)
    return tmp_path


def test_first_verification_becomes_the_baseline(data):
    result = selfimprove.verify(data, fake_runner())
    assert result["aprovado"] and result["testes"] == "316 passed in 40s" and result["pioras"] == []
    assert json.loads(selfimprove.baseline_path().read_text(encoding="utf-8")) == BASE


def test_failing_tests_or_worse_benchmark_reject_and_keep_the_baseline(data):
    selfimprove.verify(data, fake_runner())
    broken = selfimprove.verify(data, fake_runner(tests_ok=False))
    assert not broken["aprovado"] and not broken["testes_ok"]

    worse = selfimprove.verify(data, fake_runner(bench={**BASE, "validacao_acuracia": 0.80}))
    assert not worse["aprovado"] and worse["pioras"] == ["validacao_acuracia: 0.947 → 0.800"]
    assert json.loads(selfimprove.baseline_path().read_text(encoding="utf-8")) == BASE  # não vira referência


# ── desfazer o que já foi mantido ────────────────────────────────────────

def git(path, *args):
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


def test_kept_changes_can_be_reverted_after_a_failed_verification(tmp_path):
    repo = tmp_path / "app"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "a.py").write_text("a = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "base")

    store = runs.RunStore(tmp_path / "runs")
    cfg = Config(projetos={"App": str(repo)})
    run = runs.enqueue(store, cfg, "App", "executar", "mudar a")
    runner = lambda cmd, **kw: (  # noqa: E731
        (repo / "a.py").write_text("a = 2\n"),
        types.SimpleNamespace(returncode=0, stdout=json.dumps({"result": "ok"}), stderr=""))[1]
    done = runs.execute(run, store, runs.ClaudeConfig(executable="x"), runner=runner)

    with pytest.raises(ValueError, match="só dá para desfazer"):
        runs.revert(store, done.id)  # ainda pendente: o caminho é Manter ou Desfazer
    runs.review(store, done.id, keep=True)
    assert (repo / "a.py").read_text() == "a = 2\n"
    reverted = runs.revert(store, done.id)
    assert reverted.revisao == "desfeita" and (repo / "a.py").read_text() == "a = 1\n"
    with pytest.raises(ValueError):
        runs.revert(store, done.id)


# ── janela: ideias automáticas, reinício e verificação ───────────────────

@pytest.fixture
def api(tmp_path, monkeypatch):
    pytest.importorskip("webview")
    from jarvis.ui.api import Api
    from jarvis.chat import Conversation
    from jarvis.brains.router import Router

    monkeypatch.setattr(selfimprove, "data_dir", lambda: tmp_path)
    instance = Api(Config(), Conversation(Router([types.SimpleNamespace(name="x", ask=lambda m, s: None)]), "s"))
    instance._memory = MemoryDB(tmp_path / "memoria.db")
    return instance


def test_unrecognized_request_and_low_quality_answers_become_ideas(api):
    from jarvis.brains.base import Answer
    from jarvis.local.engine import HELP

    api._learn_from("organiza minhas fotos por data", Answer(HELP + "\n\n_(modo independente)_", "local"), None)
    api._learn_from("explica o motor", Answer("ok", "claude"),
                    {"media": 4.2, "notas": {"coerencia": 3.0, "clareza": 6.0, "relevancia": 5.0, "fidelidade": None, "fluidez": 7.0}})
    api._learn_from("tudo bem?", Answer("Tudo ótimo, e você?", "claude"), {"media": 9.0, "notas": {}})
    ideas = [i["ideia"] for i in selfimprove.list_ideas(api._memory)]
    assert len(ideas) == 2
    assert "organiza minhas fotos por data" in ideas[0] and "pior critério: coerencia" in ideas[1]


def test_restart_starts_a_new_process_and_closes_this_one(api, monkeypatch):
    started, closed = [], []
    monkeypatch.setattr("subprocess.Popen", lambda cmd, **kw: started.append((cmd, kw)))
    api._quit = lambda: closed.append(True)
    assert api.restart_jarvis() == {"ok": True}
    command, kwargs = started[0]
    assert command[-2:] == ["-m", "jarvis"] and kwargs["env"]["JARVIS_REINICIO"] == "1"
    import time
    time.sleep(0.8)
    assert closed == [True]


def test_new_instance_waits_for_the_old_one_after_restart():
    import ctypes
    import time
    from jarvis.ui.window import claim_single_instance

    name = "Local\\SuperJarvisTesteReinicio"
    first = claim_single_instance(name)
    assert first is not None
    assert claim_single_instance(name) is None  # sem espera: recusa na hora

    import threading
    threading.Timer(0.5, lambda: ctypes.windll.kernel32.CloseHandle(first)).start()
    start = time.time()
    second = claim_single_instance(name, wait_seconds=5)
    assert second is not None and 0.3 < time.time() - start < 4
    ctypes.windll.kernel32.CloseHandle(second)


def test_verification_after_keep_marks_the_idea_done_and_notifies(api, monkeypatch):
    selfimprove.add_idea("Reconhecer 'me fala as horas' como pedido de hora", "teste", api._memory)
    run = runs.Run("Super Jarvis", ".", "executar", selfimprove.task_for("Reconhecer 'me fala as horas' como pedido de hora"))
    pushed = []
    api._push = pushed.append
    api._voice = None
    monkeypatch.setattr(selfimprove, "verify", lambda root: {
        "aprovado": True, "testes_ok": True, "testes": "316 passed", "pioras": [], "benchmark": BASE})
    api._verify_self(run)
    assert pushed[0]["verify"]["aprovado"] and pushed[0]["verify"]["id"] == run.id
    assert selfimprove.list_ideas(api._memory) == []  # marcada como feita


def test_failed_verification_keeps_the_idea_open(api, monkeypatch):
    selfimprove.add_idea("Ideia que ainda não passou na verificação", "teste", api._memory)
    run = runs.Run("Super Jarvis", ".", "executar", selfimprove.task_for("Ideia que ainda não passou na verificação"))
    api._push, api._voice = (lambda payload: None), None
    monkeypatch.setattr(selfimprove, "verify", lambda root: {
        "aprovado": False, "testes_ok": False, "testes": "2 failed", "pioras": [], "benchmark": None})
    api._verify_self(run)
    assert len(selfimprove.list_ideas(api._memory)) == 1


def test_mcp_tools_for_improvement(tmp_path, monkeypatch, fake_repo):
    from jarvis.mcp_tools import improve_tools
    from jarvis.pc import actions

    monkeypatch.setattr(selfimprove, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(improve_tools, "mem", lambda: MemoryDB(tmp_path / "memoria.db"))
    monkeypatch.setattr(improve_tools, "store", actions.ActionStore(tmp_path / "acoes"))
    monkeypatch.setattr("jarvis.config.load", lambda: Config())
    monkeypatch.setattr("jarvis.config.save", lambda cfg: None)
    assert "anotada" in improve_tools.anotar_melhoria("Responder mais rápido às perguntas simples")
    assert "já está" in improve_tools.anotar_melhoria("Responder mais rápido às perguntas simples")
    assert improve_tools.listar_melhorias()[0]["ideia"] == "Responder mais rápido às perguntas simples"
    answer = improve_tools.propor_melhorar_se()
    assert "aguardando aprovação" in answer and "Super Jarvis" in answer
    [pending] = improve_tools.store.pending_since(0)
    assert pending.kind == "executar_tarefa" and "Ideia: Responder mais rápido" in pending.params["tarefa"]


def test_different_requests_with_the_same_prefix_are_different_ideas(vault):
    assert selfimprove.add_idea('Entender e atender o pedido: "abre a pasta de fotos"', "pedido não entendido", vault)
    assert selfimprove.add_idea('Entender e atender o pedido: "abre a pasta de downloads"', "pedido não entendido", vault)
    assert len(selfimprove.list_ideas(vault)) == 2
