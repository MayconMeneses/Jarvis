import json
import os

import pytest

from jarvis.dev import sessions

NOW = 1_800_000_000.0
CWD = r"C:\Users\eu\Projetos\Loja"


def assistant(*blocks, stop="tool_use", uuid="a1"):
    return {"type": "assistant", "uuid": uuid, "cwd": CWD, "entrypoint": "cli",
            "message": {"role": "assistant", "stop_reason": stop, "content": list(blocks)}}


def user(*blocks, uuid="u1"):
    return {"type": "user", "uuid": uuid, "cwd": CWD, "message": {"role": "user", "content": list(blocks)}}


def text(t):
    return {"type": "text", "text": t}


def tool(name, tid="t1"):
    return {"type": "tool_use", "id": tid, "name": name, "input": {}}


def result(tid="t1"):
    return {"type": "tool_result", "tool_use_id": tid, "content": "ok"}


@pytest.fixture
def home(tmp_path):
    (tmp_path / "projects" / "C--Users-eu-Projetos-Loja").mkdir(parents=True)
    (tmp_path / "sessions").mkdir()
    return tmp_path


def write_transcript(home, sid, objs, age=0.0, partial=False):
    path = home / "projects" / "C--Users-eu-Projetos-Loja" / f"{sid}.jsonl"
    body = "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in objs)
    if partial:
        body += '{"type":"assistant","mess'  # linha sendo escrita
    path.write_text(body, encoding="utf-8")
    os.utime(path, (NOW - age, NOW - age))
    return path


def write_roster(home, sid, pid=100, status="busy", waiting_for=None, updated=1):
    data = {"pid": pid, "sessionId": sid, "cwd": CWD, "name": "Loja nova", "status": status,
            "statusUpdatedAt": updated}
    if waiting_for:
        data["waitingFor"] = waiting_for
    (home / "sessions" / f"{pid}.json").write_text(json.dumps(data), encoding="utf-8")


def reader(home, alive=(100,)):
    return sessions.SessionReader(home, alive=lambda pid: pid in alive, clock=lambda: NOW)


def only(home, **kw):
    found = reader(home, **kw).sessions()
    assert len(found) == 1
    return found[0]


# ── estados a partir da ficha do processo (CONFIRMADO) ───────────────────

def test_roster_waiting_permission_prompt(home):
    write_transcript(home, "s1", [assistant(tool("Bash"))])
    write_roster(home, "s1", status="waiting", waiting_for="permission prompt")
    s = only(home)
    assert (s.estado, s.motivo, s.fonte, s.nome, s.projeto) == (
        "permissao", "permission prompt", "ficha", "Loja nova", "Loja")
    assert s.esperando


def test_roster_waiting_input_needed_is_question(home):
    write_transcript(home, "s1", [assistant(text("oi"), stop="end_turn")])
    write_roster(home, "s1", status="waiting", waiting_for="input needed")
    assert only(home).estado == "pergunta"


def test_roster_busy_is_working(home):
    write_transcript(home, "s1", [user(text("faça X")), assistant(tool("Read"))], age=5)
    write_roster(home, "s1", status="busy")
    assert only(home).estado == "trabalhando"


def test_roster_idle_after_end_turn_is_waiting(home):
    write_transcript(home, "s1", [user(text("oi")), assistant(text("Pronto, terminei."), stop="end_turn")])
    write_roster(home, "s1", status="idle")
    assert only(home).estado == "aguardando"


def test_dead_process_roster_is_ignored(home):
    write_transcript(home, "s1", [assistant(text("Pronto."), stop="end_turn")], age=3600)
    write_roster(home, "s1", pid=999, status="waiting", waiting_for="dialog open")
    assert reader(home).sessions() == []


def test_live_process_without_transcript_is_new(home):
    write_roster(home, "s9", status="idle")
    s = only(home)
    assert (s.session_id, s.estado, s.esperando) == ("s9", "nova", False)


# ── estados a partir do transcrito (HEURÍSTICA) ──────────────────────────

def test_pending_question_tool(home):
    write_transcript(home, "s1", [assistant(text("Antes"), tool("AskUserQuestion"))])
    write_roster(home, "s1", status="busy")
    s = only(home)
    assert (s.estado, s.motivo) == ("pergunta", "AskUserQuestion")


def test_stale_pending_tool_is_probable_permission(home):
    write_transcript(home, "s1", [assistant(tool("Bash"))], age=120)
    write_roster(home, "s1", status="busy")
    s = only(home)
    assert s.estado == "permissao" and s.motivo.startswith("talvez")


def test_fresh_pending_tool_and_subagents_are_working(home):
    write_transcript(home, "s1", [assistant(tool("Bash"))], age=5)
    write_transcript(home, "s2", [assistant(tool("Agent"))], age=600)
    states = {s.session_id: s.estado for s in reader(home).sessions()}
    assert states == {"s1": "trabalhando", "s2": "trabalhando"}


def test_resolved_tool_is_not_pending(home):
    write_transcript(home, "s1", [assistant(tool("Bash")), user(result())], age=120)
    write_roster(home, "s1", status="busy")
    assert only(home).estado == "trabalhando"


def test_end_turn_question_without_roster(home):
    write_transcript(home, "s1", [assistant(text("Prefere Postgres ou SQLite?\n1. Postgres\n2. SQLite"),
                                            stop="end_turn")], age=60)
    s = only(home, alive=())
    assert (s.estado, s.fonte) == ("pergunta", "transcrito")


def test_url_query_string_is_not_a_question(home):
    write_transcript(home, "s1", [assistant(text("Veja https://x.com/a?b=1"), stop="end_turn")], age=60)
    assert only(home, alive=()).estado == "aguardando"


def test_interrupted_by_user_is_waiting(home):
    write_transcript(home, "s1", [assistant(tool("Bash")), user(result()),
                                  user(text("[Request interrupted by user]"), uuid="u2")])
    write_roster(home, "s1", status="idle")
    assert only(home).estado == "aguardando"


def test_old_transcript_without_process_is_skipped(home):
    write_transcript(home, "s1", [assistant(text("ok?"), stop="end_turn")], age=sessions.RECENT_SECONDS + 10)
    assert reader(home, alive=()).sessions() == []


def test_sdk_runs_are_skipped(home):
    obj = assistant(text("Resultado"), stop="end_turn")
    obj["entrypoint"] = "sdk-cli"
    write_transcript(home, "s1", [obj])
    assert reader(home, alive=()).sessions() == []


def test_titles_partial_lines_and_sidechains(home):
    side = assistant(tool("AskUserQuestion"))
    side["isSidechain"] = True
    write_transcript(home, "s1", [{"type": "ai-title", "aiTitle": "Título IA"},
                                  {"type": "agent-name", "agentName": "Nome dado"},
                                  assistant(text("Feito."), stop="end_turn"), side], partial=True)
    s = only(home, alive=())
    assert (s.nome, s.estado) == ("Nome dado", "aguardando")


def test_tail_reads_only_the_end_of_big_files(home):
    filler = [user(text("x" * 1000), uuid=f"f{i}") for i in range(200)]
    write_transcript(home, "s1", filler + [assistant(tool("ExitPlanMode"))])
    objs = sessions.read_tail(home / "projects" / "C--Users-eu-Projetos-Loja" / "s1.jsonl", nbytes=8 * 1024)
    assert len(objs) < 10
    assert only(home, alive=()).estado == "pergunta"


def test_worktree_counts_as_parent_project(home):
    assert sessions._project_name(r"C:\x\Jarvis\.claude\worktrees\abc") == "Jarvis"
    assert sessions._project_name("") == "desconhecido"


def test_reader_never_writes(home):
    path = write_transcript(home, "s1", [assistant(text("ok"), stop="end_turn")])
    write_roster(home, "s1", status="idle")
    before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in home.rglob("*") if p.is_file()}
    reader(home).sessions()
    after = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in home.rglob("*") if p.is_file()}
    assert before == after and path.exists()


# ── monitor: avisa uma única vez ─────────────────────────────────────────

def test_watcher_notifies_once_per_waiting_episode(home):
    told = []
    write_transcript(home, "s1", [assistant(tool("Bash"))], age=5)
    write_roster(home, "s1", status="busy")
    watcher = sessions.SessionWatcher(told.append, reader(home))
    assert watcher.tick() == []

    write_roster(home, "s1", status="waiting", waiting_for="permission prompt", updated=2)
    watcher.tick()
    watcher.tick()
    assert [s.estado for s in told] == ["permissao"]
    assert "Loja nova" in told[0].frase() and "permissão" in told[0].frase()

    write_roster(home, "s1", status="busy", updated=3)  # aprovou: voltou a trabalhar
    watcher.tick()
    write_roster(home, "s1", status="waiting", waiting_for="permission prompt", updated=4)
    watcher.tick()
    assert len(told) == 2


def test_watcher_first_scan_skips_idle_but_not_permission(home):
    told = []
    write_transcript(home, "s1", [assistant(text("Pronto."), stop="end_turn")])
    write_transcript(home, "s2", [assistant(tool("Bash"))])
    write_roster(home, "s1", pid=100, status="idle")
    write_roster(home, "s2", pid=101, status="waiting", waiting_for="permission prompt")
    watcher = sessions.SessionWatcher(told.append, reader(home, alive=(100, 101)))
    watcher.tick()
    assert [s.session_id for s in told] == ["s2"]

    write_transcript(home, "s1", [assistant(text("Pronto."), stop="end_turn"), user(text("e agora")),
                                  assistant(text("Feito de novo."), stop="end_turn", uuid="a2")])
    watcher.tick()  # novo turno encerrado: este é avisado
    assert [s.session_id for s in told] == ["s2", "s1"]


def test_watcher_survives_notify_errors(home):
    write_transcript(home, "s1", [assistant(tool("Bash"))])
    write_roster(home, "s1", status="waiting", waiting_for="dialog open")

    def boom(_):
        raise RuntimeError("janela fechada")

    assert len(sessions.SessionWatcher(boom, reader(home)).tick()) == 1


def test_mcp_tool_lists_sessions(home, monkeypatch):
    pytest.importorskip("mcp")
    from jarvis.mcp_tools import project_tools as mcp_server

    write_transcript(home, "s1", [assistant(tool("Bash"))])
    write_roster(home, "s1", status="waiting", waiting_for="permission prompt")
    fixed = reader(home)
    monkeypatch.setattr(sessions, "SessionReader", lambda: fixed)
    out = mcp_server.sessoes_claude_code(apenas_esperando=True)
    assert out["esperando"] == 1 and out["sessoes"][0]["estado"] == "permissao"

