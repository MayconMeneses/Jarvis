import json

import pytest

from jarvis import config
from jarvis.brains.base import Answer, BrainUnavailable
from jarvis.brains.router import NoBrainAvailable, Router


class Fake:
    def __init__(self, name, fail=False):
        self.name, self.fail, self.calls = name, fail, 0

    def ask(self, prompt, system):
        self.calls += 1
        if self.fail:
            raise BrainUnavailable("fora do ar")
        return Answer(text=f"{self.name}:{prompt}", brain=self.name)


def test_router_falls_back_to_next_brain():
    first, second = Fake("claude", fail=True), Fake("gemini")
    answer = Router([first, second]).ask("oi", "sys")
    assert answer.brain == "gemini"
    assert first.calls == 1


def test_router_stops_at_first_success():
    first, second = Fake("claude"), Fake("gemini")
    Router([first, second]).ask("oi", "sys")
    assert second.calls == 0


def test_router_reports_all_failures():
    with pytest.raises(NoBrainAvailable, match="claude.*gemini"):
        Router([Fake("claude", True), Fake("gemini", True)]).ask("oi", "sys")


def test_config_created_with_defaults_and_ignores_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    cfg = config.load(path)
    assert path.exists() and cfg.brains == ["claude"]

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["city"] = "Croatá"
    raw["chave_antiga"] = 1
    raw["claude"]["model"] = "sonnet"
    path.write_text(json.dumps(raw), encoding="utf-8")

    cfg = config.load(path)
    assert cfg.city == "Croatá"
    assert cfg.claude.model == "sonnet"
