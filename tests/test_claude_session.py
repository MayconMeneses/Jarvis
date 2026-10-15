import json
import queue
import threading

import pytest

from jarvis.brains.base import BrainUnavailable
from jarvis.brains.claude_session import ClaudeSession, render_new
from jarvis.config import ClaudeConfig


class FakeStdin:
    def __init__(self, proc):
        self.proc = proc

    def write(self, text):
        self.proc.received.append(json.loads(text)["message"]["content"])

    def flush(self):
        reply = self.proc.replies.pop(0)
        if reply is None:  # simula o processo morrendo
            self.proc.dead = True
            self.proc.stdout.put(None)
            return
        self.proc.stdout.put(json.dumps({"type": "system", "subtype": "init"}) + "\n")
        self.proc.stdout.put(json.dumps(reply) + "\n")

    def close(self):
        self.proc.dead = True
        self.proc.stdout.put(None)


class FakeStdout:
    def __init__(self):
        self.q = queue.Queue()

    def put(self, item):
        self.q.put(item)

    def __iter__(self):
        while True:
            item = self.q.get()
            if item is None:
                return
            yield item


class FakeProc:
    instances = []

    def __init__(self, cmd, **kw):
        self.cmd, self.kw = cmd, kw
        self.received, self.replies, self.dead = [], list(FakeProc.next_replies), False
        self.stdout = FakeStdout()
        self.stdin = FakeStdin(self)
        self.stderr = iter(())
        FakeProc.instances.append(self)

    def poll(self):
        return 0 if self.dead else None

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.dead = True


def ok(text):
    return {"type": "result", "is_error": False, "result": text}


@pytest.fixture
def session(tmp_path):
    FakeProc.instances = []
    FakeProc.next_replies = [ok("Oi!"), ok("Você pediu oi."), ok("Feito.")]
    return ClaudeSession(ClaudeConfig(executable="x", timeout_seconds=5), workdir=tmp_path, popen=FakeProc)


def user(text):
    return {"role": "user", "content": text}


def bot(text):
    return {"role": "assistant", "content": text}


def test_one_process_serves_many_turns_sending_only_new_messages(session):
    a1 = session.ask([user("diga oi")], "sys")
    a2 = session.ask([user("diga oi"), bot(a1.text), user("o que pedi?")], "sys")
    assert (a1.text, a2.text) == ("Oi!", "Você pediu oi.")
    assert len(FakeProc.instances) == 1
    proc = FakeProc.instances[0]
    assert proc.received[0].endswith("diga oi")
    assert proc.received[1].endswith("o que pedi?") and "diga oi" not in proc.received[1]
    assert "--input-format" in proc.cmd and "ANTHROPIC_API_KEY" not in proc.kw["env"]


def test_notes_since_last_answer_are_sent_with_the_question(session):
    a1 = session.ask([user("limpe o temp")], "sys")
    history = [user("limpe o temp"), bot(a1.text), bot("[Registro do sistema] Ação executada."), user("e agora?")]
    session.ask(history, "sys")
    sent = FakeProc.instances[0].received[1]
    assert "Jarvis: [Registro do sistema] Ação executada." in sent and sent.endswith("e agora?")


def test_reset_conversation_restarts_session_and_replays_nothing(session):
    session.ask([user("primeira")], "sys")
    session.ask([user("conversa nova")], "sys")  # histórico zerado: última resposta não está mais lá
    assert len(FakeProc.instances) == 2
    assert FakeProc.instances[1].received[0].endswith("conversa nova")


def test_changed_instructions_restart_with_transcript(session):
    a1 = session.ask([user("meu nome é Ana")], "sys v1")
    session.ask([user("meu nome é Ana"), bot(a1.text), user("qual meu nome?")], "sys v2 (memória nova)")
    assert len(FakeProc.instances) == 2
    replay = FakeProc.instances[1].received[0]
    assert "Usuário: meu nome é Ana" in replay and replay.endswith("qual meu nome?")
    assert FakeProc.instances[1].cmd[FakeProc.instances[1].cmd.index("--system-prompt") + 1] == "sys v2 (memória nova)"


def test_warm_up_starts_process_once_and_first_question_reuses_it(session):
    FakeProc.next_replies = [ok("ok"), ok("Oi!")]
    session.warm_up("sys")
    session.warm_up("sys")
    answer = session.ask([bot("Bom dia! Como você está?"), user("estou bem")], "sys")
    assert answer.text == "Oi!" and len(FakeProc.instances) == 1
    received = FakeProc.instances[0].received
    assert "inicialização" in received[0]
    assert "Jarvis: Bom dia! Como você está?" in received[1] and received[1].endswith("estou bem")


def test_error_result_is_brain_unavailable_and_session_survives(session):
    FakeProc.next_replies = [{"type": "result", "is_error": True, "result": "You've hit your session limit"}, ok("voltei")]
    with pytest.raises(BrainUnavailable, match="session limit"):
        session.ask([user("oi")], "sys")
    assert session.ask([user("oi de novo")], "sys").text == "voltei"


def test_dead_process_is_reported_then_restarted(session):
    FakeProc.next_replies = [None]
    with pytest.raises(BrainUnavailable, match="encerrada"):
        session.ask([user("oi")], "sys")
    FakeProc.next_replies = [ok("de volta")]
    assert session.ask([user("oi")], "sys").text == "de volta"
    assert len(FakeProc.instances) == 2


def test_render_new_has_time_and_roles():
    text = render_new([user("a"), bot("b"), user("c")])
    assert text.startswith("[Agora: ") and "- Usuário: a" in text and "- Jarvis: b" in text
