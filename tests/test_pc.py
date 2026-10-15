import os
import subprocess
import sys
import time

import psutil
import pytest

from jarvis.brains.claude_cli import ClaudeCLI
from jarvis.brains.router import Router
from jarvis.chat import Conversation
from jarvis.config import ClaudeConfig, Config
from jarvis.pc import actions, startup, system
from jarvis.brains.base import Answer


class FakeRegistry:
    def __init__(self):
        self.data = {
            ("HKCU", startup.RUN): {"Spotify": "spotify.exe", "Discord": "discord.exe"},
            ("HKCU", startup.APPROVED + r"\Run"): {"Discord": bytes([3]) + bytes(11)},
            ("HKLM", startup.RUN): {"SecurityHealth": "health.exe"},
        }

    def values(self, hive, path):
        return dict(self.data.get((hive, path), {}))

    def set_binary(self, hive, path, name, data):
        self.data.setdefault((hive, path), {})[name] = data


@pytest.fixture
def reg():
    return FakeRegistry()


def by_name(items):
    return {i.nome: i for i in items}


# ── inicialização ────────────────────────────────────────────────────────

def test_startup_lists_items_with_status_and_origin(reg, tmp_path):
    (tmp_path / "Atalho.lnk").write_text("x")
    (tmp_path / "desktop.ini").write_text("x")
    items = by_name(startup.list_items(reg, folders=[("usuario", "HKCU", tmp_path)]))
    assert items["Spotify"].ativo and items["Spotify"].pode_desativar
    assert not items["Discord"].ativo
    assert not items["SecurityHealth"].pode_desativar
    assert "Atalho.lnk" in items and "desktop.ini" not in items


def test_disable_writes_task_manager_flag_for_user_item(reg):
    msg = startup.disable("spotify", reg, folders=[])
    assert "Spotify" in msg
    assert reg.data[("HKCU", startup.APPROVED + r"\Run")]["Spotify"] == startup.DISABLED_FLAG
    assert not by_name(startup.list_items(reg, folders=[]))["Spotify"].ativo


@pytest.mark.parametrize("name,error", [
    ("SecurityHealth", "administrador"),
    ("Discord", "já está desativado"),
    ("NaoExiste", "não encontrado"),
])
def test_disable_refuses_machine_wide_disabled_or_missing(reg, name, error):
    with pytest.raises(ValueError, match=error):
        startup.disable(name, reg, folders=[])


# ── ações com aprovação ──────────────────────────────────────────────────

@pytest.fixture
def store(tmp_path):
    return actions.ActionStore(tmp_path / "acoes")


@pytest.fixture
def sleeper():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    yield proc
    if proc.poll() is None:
        proc.kill()


def test_kill_only_happens_after_approval(store, sleeper):
    action = actions.propose_kill(store, sleeper.pid, "teste")
    assert action.status == "pendente"
    time.sleep(0.3)
    assert sleeper.poll() is None  # propor não encerra nada

    done = actions.decide(store, action.id, approve=True)
    assert done.status == "executada"
    sleeper.wait(timeout=5)


def test_refused_action_does_nothing_and_cannot_be_decided_twice(store, sleeper):
    action = actions.propose_kill(store, sleeper.pid, "teste")
    assert actions.decide(store, action.id, approve=False).status == "recusada"
    assert sleeper.poll() is None
    with pytest.raises(ValueError, match="já foi decidida"):
        actions.decide(store, action.id, approve=True)


def test_kill_fails_safely_if_pid_now_belongs_to_other_program(store, sleeper):
    action = actions.propose_kill(store, sleeper.pid, "teste")
    action.params["nome"] = "outro.exe"
    store.save(action)
    result = actions.decide(store, action.id, approve=True)
    assert result.status == "falhou" and "outro.exe" in result.resultado
    assert sleeper.poll() is None


def test_critical_processes_and_jarvis_itself_are_refused(store, monkeypatch):
    with pytest.raises(ValueError, match="própria Jarvis"):
        actions.propose_kill(store, os.getpid(), "teste")
    monkeypatch.setattr(psutil.Process, "name", lambda self: "lsass.exe")
    with pytest.raises(ValueError, match="essencial"):
        actions.check_process(os.getpid())


def test_clean_temp_removes_only_old_files_and_keeps_claude(store, tmp_path):
    temp = tmp_path / "Temp"
    (temp / "velha").mkdir(parents=True)
    (temp / "claude").mkdir()
    old = time.time() - 3 * 86400
    for path in (temp / "a.tmp", temp / "velha" / "b.log", temp / "claude" / "sessao.json"):
        path.write_text("x" * 100)
        os.utime(path, (old, old))
    (temp / "nova.tmp").write_text("recente")

    action = actions.propose_clean_temp(store, 1, "liberar espaço", temp=temp)
    assert "2 arquivos" in action.descricao
    done = actions.decide(store, action.id, approve=True, temp=temp)
    assert done.status == "executada"
    assert sorted(p.name for p in temp.iterdir()) == ["claude", "nova.tmp"]
    assert (temp / "claude" / "sessao.json").exists()


def test_store_rejects_path_traversal_ids(store):
    with pytest.raises(ValueError):
        store.get("..\\..\\config")


def test_pending_since_filters_by_time_and_status(store):
    old = store.save(actions.Action("limpar_temporarios", {"dias": 1}, "a", "m", criada_em=1.0))
    new = store.save(actions.Action("limpar_temporarios", {"dias": 1}, "b", "m"))
    assert [a.id for a in store.pending_since(100.0)] == [new.id]
    assert old.id not in [a.id for a in store.pending_since(100.0)]


# ── janela e cérebro ─────────────────────────────────────────────────────

class ProposingBrain:
    name = "claude"

    def __init__(self, store):
        self.store = store

    def ask(self, messages, system):
        self.store.save(actions.Action("limpar_temporarios", {"dias": 1}, "Apagar temporários", "lento"))
        return Answer("Sugiro limpar os temporários.", "claude")


def test_api_returns_new_proposals_and_records_decision(store):
    pytest.importorskip("webview")
    from jarvis.ui.app import Api

    conv = Conversation(Router([ProposingBrain(store)]), "sys")
    api = Api(Config(), conv, store)
    res = api.send("está lento")
    assert [a["descricao"] for a in res["actions"]] == ["Apagar temporários"]

    out = api.decide(res["actions"][0]["id"], False)
    assert out["status"] == "recusada"
    assert "recusada" in conv.history[-1]["content"]


def test_claude_command_enables_only_jarvis_mcp_tools(tmp_path):
    cmd = ClaudeCLI(ClaudeConfig(executable="x"), mcp_config=tmp_path / "mcp.json").command("s")
    assert cmd[cmd.index("--mcp-config") + 1].endswith("mcp.json")
    assert cmd[cmd.index("--allowedTools") + 1] == "mcp__jarvis"
    assert cmd[cmd.index("--tools") + 1] == ""


def test_system_readings_have_expected_shape():
    info = system.overview()
    assert 0 <= info["ram_em_uso_percent"] <= 100 and info["disco_c_livre_gb"] > 0
    top = system.top_processes("memoria", 3)
    assert len(top) == 3 and top[0]["memoria_mb"] >= top[-1]["memoria_mb"]
