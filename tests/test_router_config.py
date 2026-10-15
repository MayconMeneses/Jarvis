import json

import pytest

from jarvis import config
from jarvis.brains.base import Answer, BrainUnavailable
from jarvis.brains.router import NoBrainAvailable, Router
from jarvis.chat import MAX_HISTORY, Conversation


class Fake:
    def __init__(self, name, fail=False):
        self.name, self.fail, self.calls = name, fail, 0

    def ask(self, messages, system):
        self.calls += 1
        self.last = messages
        if self.fail:
            raise BrainUnavailable("fora do ar")
        return Answer(text=f"{self.name}:{messages[-1]['content']}", brain=self.name)


MSG = [{"role": "user", "content": "oi"}]


def test_router_falls_back_to_next_brain():
    first, second = Fake("claude", fail=True), Fake("gemini")
    answer = Router([first, second]).ask(MSG, "sys")
    assert answer.brain == "gemini"
    assert first.calls == 1


def test_router_stops_at_first_success():
    first, second = Fake("claude"), Fake("gemini")
    Router([first, second]).ask(MSG, "sys")
    assert second.calls == 0


def test_router_reports_all_failures():
    with pytest.raises(NoBrainAvailable, match="claude.*gemini"):
        Router([Fake("claude", True), Fake("gemini", True)]).ask(MSG, "sys")


def test_conversation_keeps_history_and_reset_clears_it():
    brain = Fake("claude")
    conv = Conversation(Router([brain]), "sys")
    conv.ask("primeira")
    conv.ask("segunda")
    assert [m["content"] for m in brain.last] == ["primeira", "claude:primeira", "segunda"]
    conv.reset()
    conv.ask("terceira")
    assert len(brain.last) == 1


def test_conversation_failed_question_is_not_stored():
    conv = Conversation(Router([Fake("claude", fail=True)]), "sys")
    with pytest.raises(NoBrainAvailable):
        conv.ask("oi")
    assert conv.history == []


def test_conversation_history_is_capped():
    conv = Conversation(Router([Fake("claude")]), "sys")
    for i in range(30):
        conv.ask(str(i))
    assert len(conv.history) == MAX_HISTORY


def test_config_created_with_defaults_and_ignores_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    cfg = config.load(path)
    assert path.exists() and cfg.brains == ["claude", "gemini", "nvidia"]

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["city"] = "Croatá"
    raw["chave_antiga"] = 1
    raw["claude"]["model"] = "sonnet"
    path.write_text(json.dumps(raw), encoding="utf-8")

    cfg = config.load(path)
    assert cfg.city == "Croatá"
    assert cfg.claude.model == "sonnet"


def test_config_fills_new_provider_fields_in_old_files(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"brains": ["claude"], "gemini": {"model": "x"}}), encoding="utf-8")
    cfg = config.load(path)
    assert cfg.gemini.model == "x"
    assert cfg.gemini.base_url.startswith("https://generativelanguage")
    assert "nvidia" in json.loads(path.read_text(encoding="utf-8"))
