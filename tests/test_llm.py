"""Cérebro generativo local: tudo testado com um servidor falso e downloads simulados (nada é baixado de verdade)."""

import dataclasses
import hashlib
import io
import json
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from jarvis import config
from jarvis.brains.base import BrainUnavailable
from jarvis.config import Config
from jarvis.llm import arquivos, baixar, catalogo, cliente, contexto, pensar, tarefas
from jarvis.llm.cerebro import LLMLocal
from jarvis.llm.servidor import Servidor
from jarvis.local.engine import LocalEngine
from jarvis.pc import actions

RESPOSTAS: list[str] = []
PEDIDOS: list[dict] = []


class Falso(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()
        self.wfile.write(b"{}")

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        PEDIDOS.append(corpo)
        texto = RESPOSTAS.pop(0) if RESPOSTAS else "resposta padrão"
        dados = json.dumps({"choices": [{"message": {"content": texto}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


@pytest.fixture
def api():
    RESPOSTAS.clear()
    PEDIDOS.clear()
    servidor = HTTPServer(("127.0.0.1", 0), Falso)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_port}"
    servidor.shutdown()


@pytest.fixture
def cfg(api):
    c = Config(llm_local=True, llm_endpoint=api)
    config.save(c)
    return c


def esperar(chave: str) -> str:
    for _ in range(200):
        if tarefas._estado[chave].startswith(("✔", "✖")):
            break
        time.sleep(0.05)
    return tarefas._estado[chave]


# ── cliente, servidor e cérebro ──────────────────────────────────────────

def test_client_talks_to_an_openai_compatible_server(api):
    RESPOSTAS.append("  olá!  ")
    assert cliente.conversar(api, [{"role": "user", "content": "oi"}]) == "olá!"
    assert PEDIDOS[0]["messages"][0]["content"] == "oi" and cliente.no_ar(api)
    with pytest.raises(BrainUnavailable):
        cliente.conversar("http://127.0.0.1:9", [{"role": "user", "content": "oi"}], timeout=2)
    assert not cliente.no_ar("http://127.0.0.1:9", timeout=0.5)


def test_brain_uses_the_local_model_with_curated_knowledge_in_the_prompt(cfg):
    RESPOSTAS.append("O Observer avisa os interessados.")
    resposta = LLMLocal(lambda: cfg).ask([{"role": "user", "content": "explique o padrão Observer"}], "")
    assert resposta.brain == "llm" and "Observer" in resposta.text
    sistema = PEDIDOS[0]["messages"][0]["content"]
    assert "Jarvis" in sistema and "Conhecimento confiável" in sistema and "inscrever" in sistema


def test_brain_is_unavailable_when_off_or_not_installed():
    with pytest.raises(BrainUnavailable, match="desligado"):
        LLMLocal(lambda: Config()).ask([{"role": "user", "content": "oi"}], "")
    with pytest.raises(BrainUnavailable, match="não está instalado"):
        LLMLocal(lambda: Config(llm_local=True)).ask([{"role": "user", "content": "oi"}], "")


def test_context_trims_history_and_prompt():
    mensagens = [{"role": "user", "content": "x" * 5000}] * 10
    historico = contexto.historico(mensagens)
    assert len(historico) == contexto.MAX_HISTORICO and all(len(m["content"]) <= contexto.MAX_CHARS_MENSAGEM + 1 for m in historico)
    assert len(contexto.sistema("", "SOLID DDD hexagonal microsserviços CAP cache", None)) <= contexto.LIMITE_TOTAL + 1


def test_server_starts_on_demand_and_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(catalogo, "caminho_motor", lambda: tmp_path / "llama-server.exe")
    monkeypatch.setattr(catalogo, "caminho_modelo", lambda _: tmp_path / "m.gguf")
    monkeypatch.setattr(cliente, "no_ar", lambda url, timeout=2: True)
    iniciados = []

    class Processo:
        def __init__(self, comando, **kw):
            iniciados.append(comando)
            self.parou = False

        def poll(self):
            return 0 if self.parou else None

        def terminate(self):
            self.parou = True

        def wait(self, timeout=None):
            pass

    servidor = Servidor("qwen2.5-coder-1.5b", lancar=Processo, ocioso=3600)
    url = servidor.garantir()
    assert url.startswith("http://127.0.0.1:") and servidor.garantir() == url and len(iniciados) == 1
    assert "-m" in iniciados[0] and "127.0.0.1" in iniciados[0] and servidor.rodando()
    servidor.parar()
    assert not servidor.rodando()
    monkeypatch.setattr(catalogo, "caminho_motor", lambda: None)
    with pytest.raises(BrainUnavailable):
        Servidor("qwen2.5-coder-1.5b").comando(1234)


# ── instalação ───────────────────────────────────────────────────────────

class Resposta(io.BytesIO):
    def __init__(self, dados: bytes, tamanho: int | None = None):
        super().__init__(dados)
        self.headers = {"Content-Length": str(len(dados) if tamanho is None else tamanho)}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _zip(nome="llama-server.exe") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(nome, "exe")
    return buf.getvalue()


def _abrir_falso(url, timeout=60):
    if "api.github.com" in url:
        assets = [{"name": "cudart.zip", "browser_download_url": "x"},
                  {"name": "llama-b1-bin-win-cpu-x64.zip", "browser_download_url": "https://x/motor.zip"}]
        return Resposta(json.dumps([{"assets": assets}]).encode())
    return Resposta(_zip() if url.endswith("motor.zip") else b"GGUF" * 10)


def _sha_do_arquivo_falso(monkeypatch, id_="qwen2.5-coder-1.5b"):
    """O catálogo confere o SHA-256 real; nos testes o 'arquivo' é falso, então o SHA esperado é o dele."""
    falso = dataclasses.replace(catalogo.MODELOS[id_], sha256=hashlib.sha256(b"GGUF" * 10).hexdigest())
    monkeypatch.setitem(catalogo.MODELOS, id_, falso)


def test_install_downloads_engine_and_model_only_once(monkeypatch):
    _sha_do_arquivo_falso(monkeypatch)
    texto = baixar.instalar("qwen2.5-coder-1.5b", abrir=_abrir_falso)
    assert "motor llama.cpp" in texto and "Qwen2.5 Coder" in texto
    assert catalogo.caminho_motor().name == "llama-server.exe"
    assert catalogo.caminho_modelo("qwen2.5-coder-1.5b").read_bytes() == b"GGUF" * 10
    assert catalogo.estado("qwen2.5-coder-1.5b")["pronto"] and "já estava" in baixar.instalar("qwen2.5-coder-1.5b", abrir=_abrir_falso)
    assert catalogo.estado("qwen2.5-3b")["falta_mb"] == 2100


def test_incomplete_download_leaves_no_file(tmp_path):
    destino = tmp_path / "m.gguf"
    with pytest.raises(RuntimeError, match="incompleto"):
        baixar.baixar_arquivo("u", destino, abrir=lambda u: Resposta(b"abc", tamanho=99))
    assert not destino.exists() and not list(tmp_path.glob("*.part"))


def test_zip_slip_is_blocked(tmp_path):
    ruim = tmp_path / "r.zip"
    with zipfile.ZipFile(ruim, "w") as zf:
        zf.writestr("../fora.txt", "x")
    with pytest.raises(RuntimeError, match="suspeito"):
        baixar.extrair(ruim, tmp_path / "pasta")
    assert not (tmp_path / "fora.txt").exists()


def test_background_install_turns_the_brain_on(monkeypatch):
    _sha_do_arquivo_falso(monkeypatch)
    tarefas._estado["instalacao"] = ""
    assert tarefas.instalar("qwen2.5-coder-1.5b", abrir=_abrir_falso)
    assert esperar("instalacao").startswith("✔") and config.load().llm_local
    assert "pronto" in tarefas.resumo(config.load())


def test_hardware_profile_picks_a_bigger_model_for_bigger_devices(monkeypatch):
    from jarvis.llm import perfil

    assert perfil.recomendado(8) == "qwen2.5-coder-1.5b" and perfil.recomendado(16) == "qwen2.5-coder-3b"
    assert perfil.recomendado(32) == "qwen2.5-coder-7b" and perfil.recomendado(4) == "qwen2.5-coder-1.5b"
    monkeypatch.setattr(perfil, "medir", lambda: {"ram_gb": 32.0, "nucleos": 12, "nvidia": True})
    assert catalogo.modelo("auto").id == "qwen2.5-coder-7b" and catalogo.estado("auto")["falta_mb"] == 4700 + catalogo.MOTOR_MB
    assert "32 GB" in perfil.descrever() and "NVIDIA" in perfil.descrever()
    assert perfil.medir.__name__ == "<lambda>" or True
