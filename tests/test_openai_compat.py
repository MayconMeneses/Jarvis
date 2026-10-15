import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from jarvis import keys
from jarvis.brains.base import BrainUnavailable
from jarvis.brains.openai_compat import OpenAICompat
from jarvis.config import ProviderConfig


class FakeAPI(BaseHTTPRequestHandler):
    status = 200
    reply = {"choices": [{"message": {"content": " Olá do servidor "}}]}
    seen: dict = {}

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        FakeAPI.seen = {
            "path": self.path,
            "auth": self.headers["Authorization"],
            "body": json.loads(self.rfile.read(length)),
        }
        payload = json.dumps(FakeAPI.reply).encode()
        self.send_response(FakeAPI.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    httpd = HTTPServer(("127.0.0.1", 0), FakeAPI)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    FakeAPI.status = 200
    FakeAPI.reply = {"choices": [{"message": {"content": " Olá do servidor "}}]}
    yield f"http://127.0.0.1:{httpd.server_port}/v1"
    httpd.shutdown()


def brain(url, key="chave-teste"):
    cfg = ProviderConfig(base_url=url, model="modelo-x", timeout_seconds=5)
    return OpenAICompat("gemini", cfg, lambda name: key)


MSG = [{"role": "user", "content": "oi"}]


def test_sends_system_history_and_bearer_key(server):
    answer = brain(server).ask(MSG, "seja breve")
    assert answer.text == "Olá do servidor"
    assert answer.brain == "gemini"
    assert FakeAPI.seen["path"] == "/v1/chat/completions"
    assert FakeAPI.seen["auth"] == "Bearer chave-teste"
    assert FakeAPI.seen["body"]["model"] == "modelo-x"
    assert FakeAPI.seen["body"]["messages"] == [
        {"role": "system", "content": "seja breve"},
        {"role": "user", "content": "oi"},
    ]


@pytest.mark.parametrize("status,reason", [(429, "limite"), (401, "chave inválida"), (500, "HTTP 500")])
def test_http_errors_become_brain_unavailable(server, status, reason):
    FakeAPI.status = status
    with pytest.raises(BrainUnavailable, match=reason):
        brain(server).ask(MSG, "sys")


def test_missing_key_is_unavailable_without_network():
    with pytest.raises(BrainUnavailable, match="sem chave"):
        brain("http://127.0.0.1:9", key=None).ask(MSG, "sys")


def test_unreachable_server_is_unavailable():
    with pytest.raises(BrainUnavailable, match="sem conexão"):
        brain("http://127.0.0.1:9").ask(MSG, "sys")


def test_malformed_reply_is_unavailable(server):
    FakeAPI.reply = {"choices": []}
    with pytest.raises(BrainUnavailable):
        brain(server).ask(MSG, "sys")


def test_env_variable_takes_precedence_over_vault(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "da-variavel")
    monkeypatch.setattr(keys.keyring, "get_password", lambda *a: "do-cofre")
    assert keys.get_key("gemini") == "da-variavel"
    monkeypatch.delenv("GEMINI_API_KEY")
    assert keys.get_key("gemini") == "do-cofre"
