"""Jarvis no celular: pareamento seguro, servidor com autenticação e o app (PWA) servido de verdade."""

import json
import shutil
import struct
import subprocess
import urllib.error
import urllib.request
import zlib
from pathlib import Path

import pytest

from jarvis import config
from jarvis.config import Config
from jarvis.mobile import icones
from jarvis.mobile.pareamento import MAX_ERROS, Pareamento
from jarvis.mobile.servidor import WEB, ServidorCelular

NODE = shutil.which("node")


class Relogio:
    t = 1000.0

    def __call__(self):
        return self.t


# ── pareamento ───────────────────────────────────────────────────────────

def test_pairing_code_is_single_use_and_the_token_is_stored_only_as_a_hash(tmp_path):
    p = Pareamento(tmp_path / "c.json")
    codigo = p.novo_codigo()
    assert len(codigo) == 6 and codigo.isdigit()
    token = p.trocar(codigo, "iPhone 13 Pro Max")
    assert token and p.validar(token) == {"id": p.listar()[0]["id"], "nome": "iPhone 13 Pro Max"}
    assert token not in (tmp_path / "c.json").read_text() and p.trocar(codigo, "outro") is None  # uso único
    assert p.validar("invalido") is None and p.validar("") is None


def test_pairing_code_expires_and_wrong_guesses_lock_it():
    relogio = Relogio()
    p = Pareamento(Path("nunca-usado.json"), relogio)
    codigo = p.novo_codigo()
    relogio.t += 301
    assert p.trocar(codigo, "x") is None  # venceu
    codigo = p.novo_codigo()
    for _ in range(MAX_ERROS):
        assert p.trocar("000000" if codigo != "000000" else "111111", "x") is None
    assert p.trocar(codigo, "x") is None  # bloqueado, mesmo com o código certo
    relogio.t += 301
    assert p.trocar(p.novo_codigo(), "x") is not None  # passado o bloqueio, um código novo funciona


def test_devices_can_be_revoked(tmp_path):
    p = Pareamento(tmp_path / "c.json")
    token = p.trocar(p.novo_codigo(), "celular")
    assert p.revogar(p.listar()[0]["id"]) and p.validar(token) is None and not p.revogar("nada")


# ── servidor ─────────────────────────────────────────────────────────────

@pytest.fixture
def app(tmp_path):
    pareamento = Pareamento(tmp_path / "c.json")
    chamadas = []

    def responder(texto):
        chamadas.append(texto)
        return {"text": f"eco: {texto}", "brain": "local"}

    servidor = ServidorCelular(pareamento, responder, lambda: 2, "Maycon")
    servidor.iniciar(porta=0, rede=False)
    yield servidor, pareamento, chamadas
    servidor.parar()


def chamar(servidor, caminho, corpo=None, token=None, bruto=None):
    cabecalhos = {"Content-Type": "application/json"}
    if token:
        cabecalhos["Authorization"] = "Bearer " + token
    dados = bruto if bruto is not None else (json.dumps(corpo).encode() if corpo is not None else None)
    pedido = urllib.request.Request(servidor.url + caminho, data=dados, headers=cabecalhos, method="POST" if dados is not None else "GET")
    try:
        with urllib.request.urlopen(pedido, timeout=10) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def test_full_flow_pair_then_chat(app):
    servidor, pareamento, chamadas = app
    assert chamar(servidor, "/api/estado")[0] == 401 and chamar(servidor, "/api/chat", {"texto": "oi"})[0] == 401
    assert chamar(servidor, "/api/parear", {"codigo": "123456", "nome": "x"})[0] == 403
    status, corpo, _ = chamar(servidor, "/api/parear", {"codigo": pareamento.novo_codigo(), "nome": "iPhone"})
    token = json.loads(corpo)["token"]
    assert status == 200
    status, corpo, _ = chamar(servidor, "/api/estado", token=token)
    assert json.loads(corpo) == {"aparelho": "iPhone", "usuario": "Maycon", "pendentes": 2}
    status, corpo, _ = chamar(servidor, "/api/chat", {"texto": "  que horas são?  "}, token)
    dados = json.loads(corpo)
    assert dados["texto"] == "eco: que horas são?" and dados["cerebro"] == "local" and dados["pendentes"] == 2 and chamadas == ["que horas são?"]
    pareamento.revogar(pareamento.listar()[0]["id"])
    assert chamar(servidor, "/api/chat", {"texto": "oi"}, token)[0] == 401  # aparelho removido perde o acesso na hora


def test_invalid_requests_are_rejected(app):
    servidor, pareamento, _ = app
    token = pareamento.trocar(pareamento.novo_codigo(), "x")
    assert chamar(servidor, "/api/chat", {"texto": "   "}, token)[0] == 400
    assert chamar(servidor, "/api/chat", token=token, bruto=b"nao e json")[0] == 400
    assert chamar(servidor, "/api/chat", token=token, bruto=b"x" * 9000)[0] == 400
    assert chamar(servidor, "/api/desconhecido", {"a": 1}, token)[0] == 404


def test_serves_the_app_files_with_security_headers_and_blocks_path_tricks(app):
    servidor, _, _ = app
    status, corpo, cab = chamar(servidor, "/")
    assert status == 200 and b"<title>Jarvis</title>" in corpo and "default-src 'self'" in cab["Content-Security-Policy"]
    assert cab["X-Content-Type-Options"] == "nosniff"
    for caminho, tipo in (("/app.js", "javascript"), ("/app.css", "css"), ("/sw.js", "javascript"), ("/manifest.webmanifest", "manifest")):
        assert tipo in chamar(servidor, caminho)[2]["Content-Type"], caminho
    for ruim in ("/../servidor.py", "/%2e%2e/servidor.py", "/..%5cservidor.py", "/icone-abc.png", "/web/../__init__.py", "/app.py"):
        assert chamar(servidor, ruim)[0] == 404, ruim
    corpo_icone = chamar(servidor, "/icone-180.png")[1]
    assert corpo_icone.startswith(b"\x89PNG")


def test_icons_are_valid_pngs():
    dados = icones.png(64)
    assert dados.startswith(b"\x89PNG\r\n\x1a\n") and dados.endswith(b"IEND\xaeB`\x82")
    largura, altura = struct.unpack(">II", dados[16:24])
    assert (largura, altura) == (64, 64)
    idat = dados[dados.index(b"IDAT") + 4:dados.index(b"IEND") - 8]
    assert len(zlib.decompress(idat)) == 64 * (1 + 64 * 3)


def test_pwa_is_installable_on_iphone():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for exigido in ("apple-mobile-web-app-capable", "apple-touch-icon", 'rel="manifest"', "viewport-fit=cover", 'lang="pt-BR"'):
        assert exigido in html, exigido
    manifesto = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifesto["display"] == "standalone" and manifesto["start_url"] == "/" and manifesto["lang"] == "pt-BR"
    assert "16px" in (WEB / "app.css").read_text(encoding="utf-8")  # input de 16px: o iPhone não dá zoom
    for arquivo in WEB.iterdir():
        assert len(arquivo.read_text(encoding="utf-8").splitlines()) <= 300, arquivo.name


@pytest.mark.skipif(NODE is None, reason="node não está instalado")
@pytest.mark.parametrize("nome", ["app.js", "sw.js"])
def test_mobile_scripts_have_valid_syntax(nome):
    assert subprocess.run([NODE, "--check", str(WEB / nome)], capture_output=True, text=True).returncode == 0


# ── janela do PC ─────────────────────────────────────────────────────────

def test_window_panel_turns_the_server_on_and_off(tmp_path):
    from jarvis.ui.api_mobile import MobileMixin

    class Ponte(MobileMixin):
        def __init__(self):
            self._store = type("S", (), {"pending_since": lambda s, t: []})()

        def send(self, texto):
            return {"text": "ok", "brain": "local"}

    config.save(Config(celular_porta=0, celular_rede=False))
    ponte = Ponte()
    ponte._pareamento = Pareamento(tmp_path / "c.json")
    assert ponte.mobile_code()["ok"] is False  # desligado: não gera código
    ligado = ponte.mobile_set(True)
    assert ligado["ok"] and ligado["ligado"] and ligado["url"].startswith("http://127.0.0.1:") and config.load().celular_ativo
    codigo = ponte.mobile_code()["codigo"]
    status, corpo, _ = chamar(ponte._mobile, "/api/parear", {"codigo": codigo, "nome": "iPhone"})
    assert status == 200 and ponte.mobile_status()["aparelhos"][0]["nome"] == "iPhone"
    assert ponte.mobile_revoke(ponte.mobile_status()["aparelhos"][0]["id"])["aparelhos"] == []
    assert ponte.mobile_set(False)["ligado"] is False and not config.load().celular_ativo
