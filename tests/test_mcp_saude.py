"""Teste de saúde do servidor MCP e comandos de chat do catálogo de ferramentas externas."""

import sys

import pytest

from jarvis.local.engine import LocalEngine
from jarvis.mcp_catalogo import integridade, saude
from jarvis.pc import actions

# ── teste de saúde (servidor MCP de mentira) ─────────────────────────────
SERVIDOR = r"""
import json, sys, os
for linha in sys.stdin:
    m = json.loads(linha)
    if m.get("method") == "initialize":
        print(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": {"protocolVersion": "2025-06-18", "capabilities": {}, "serverInfo": {"name": "f", "version": "1"}}}), flush=True)
    elif m.get("method") == "tools/list":
        print("ruído que não é json", flush=True)
        print(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": {"tools": [{"name": "ferramenta_a"}, {"name": "ferramenta_b"}]}}), flush=True)
"""


def test_health_check_lists_tools_and_does_not_leak_api_keys(tmp_path, monkeypatch):
    script = tmp_path / "servidor.py"
    script.write_text(SERVIDOR, encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "segredo-nao-pode-vazar")
    r = saude.testar(sys.executable, [str(script)], {"UMA": "x"}, tempo=20)
    assert r.ok and r.ferramentas == ["ferramenta_a", "ferramenta_b"]
    assert "GEMINI_API_KEY" not in saude.ambiente_minimo({}) and saude.ambiente_minimo({"UMA": "x"})["UMA"] == "x"


def test_health_check_fails_cleanly_for_silent_or_broken_servers(tmp_path):
    mudo = tmp_path / "mudo.py"
    mudo.write_text("import sys, time\ntime.sleep(30)\n", encoding="utf-8")
    assert not saude.testar(sys.executable, [str(mudo)], {}, tempo=1.5).ok
    assert not saude.testar(str(tmp_path / "nao-existe.exe"), [], {}, tempo=1).ok
    sai = tmp_path / "sai.py"
    sai.write_text("print('oi')\n", encoding="utf-8")
    assert not saude.testar(sys.executable, [str(sai)], {}, tempo=5).ok


# ── comandos de chat ─────────────────────────────────────────────────────
from tests.test_mcp_catalogo import ambiente  # noqa: E402,F401


def test_chat_commands_list_install_and_remove(ambiente):
    from jarvis.config import Config

    motor = LocalEngine(load_config=lambda: Config())
    assert motor.classify("que ferramentas posso instalar")[0] == "ferramentas_catalogo"
    assert "Hora e fusos" in motor.handle("que ferramentas posso instalar") and "Pensamento" in motor.handle("catálogo de ferramentas")
    assert "@playwright/mcp" in motor.handle("ferramentas recusadas")
    resposta = motor.handle("instalar a ferramenta pensamento")
    assert "Preparei o cartão" in resposta and [a.kind for a in actions.ActionStore().pending_since(0)] == ["instalar_mcp"]
    assert "Nenhuma ferramenta externa instalada" in motor.handle("ferramentas instaladas")
    assert "não está instalada" in motor.handle("remover a ferramenta tempo")
