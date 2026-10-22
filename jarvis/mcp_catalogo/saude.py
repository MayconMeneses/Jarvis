"""Pré-requisitos (Node/uv) e teste de saúde de um servidor MCP: abre o processo, faz o aperto de mão e lista as ferramentas.

O processo roda com ambiente MÍNIMO (sem chaves de API nem variáveis do usuário), nasce oculto (jarvis/proc.py) e é
encerrado no fim, com tempo máximo. Só a resposta `tools/list` é lida: nenhuma ferramenta do servidor é chamada.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
from dataclasses import dataclass, field

from jarvis import proc as processos

TEMPO_TESTE = 90  # a primeira execução do npx/uvx baixa o pacote
COMO_INSTALAR = {
    "npx": "Instale o Node.js LTS em https://nodejs.org (ou, no terminal: winget install OpenJS.NodeJS.LTS) e abra a Jarvis de novo.",
    "uvx": "Instale o uv (gerenciador do Python) com: winget install --id=astral-sh.uv -e  (ou veja https://docs.astral.sh/uv/) e abra a Jarvis de novo.",
}
_VARIAVEIS_SEGURAS = ("PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA",
                      "TEMP", "TMP", "HOMEDRIVE", "HOMEPATH", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA", "NUMBER_OF_PROCESSORS")


@dataclass
class Saude:
    ok: bool
    mensagem: str
    ferramentas: list[str] = field(default_factory=list)


def prerequisito(gerenciador: str) -> tuple[str | None, str]:
    """(caminho do npx/uvx, mensagem). Caminho None = não instalado, e a mensagem diz como instalar."""
    achado = shutil.which(gerenciador)
    if achado:
        return achado, f"{gerenciador} encontrado."
    return None, f"Falta o {gerenciador} neste PC. {COMO_INSTALAR.get(gerenciador, '')}"


def ambiente_minimo(extra: dict[str, str]) -> dict[str, str]:
    base = {k: v for k, v in os.environ.items() if k.upper() in _VARIAVEIS_SEGURAS}
    return {**base, **extra}


def _mensagem(id_: int, metodo: str, params: dict | None = None) -> str:
    corpo = {"jsonrpc": "2.0", "id": id_, "method": metodo}
    if params is not None:
        corpo["params"] = params
    return json.dumps(corpo) + "\n"


def _encerrar(processo) -> None:
    try:
        if os.name == "nt":  # cmd /c npx cria netos (node): derruba a árvore inteira
            processos.executar(["taskkill", "/T", "/F", "/PID", str(processo.pid)], capture_output=True, timeout=10)
        else:
            processo.kill()
    except (OSError, subprocess.SubprocessError):
        pass


def testar(programa: str, argumentos: list[str], env: dict[str, str], tempo: float = TEMPO_TESTE) -> Saude:
    """Aperto de mão MCP (initialize + tools/list). Nunca levanta."""
    try:
        p = processos.abrir([programa, *argumentos], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, encoding="utf-8", errors="replace", env=ambiente_minimo(env), bufsize=1)
    except (OSError, ValueError) as exc:
        return Saude(False, f"não consegui iniciar o servidor ({type(exc).__name__})")
    linhas: queue.Queue = queue.Queue()

    def ler() -> None:
        for linha in p.stdout:
            linhas.put(linha)
        linhas.put(None)

    threading.Thread(target=ler, daemon=True).start()

    def esperar(id_: int) -> dict | None:
        while True:
            try:
                linha = linhas.get(timeout=tempo)
            except queue.Empty:
                return None
            if linha is None:
                return None
            try:
                dado = json.loads(linha)
            except ValueError:
                continue  # ruído que não é JSON-RPC
            if isinstance(dado, dict) and dado.get("id") == id_:
                return dado

    try:
        p.stdin.write(_mensagem(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                                  "clientInfo": {"name": "super-jarvis", "version": "1"}}))
        p.stdin.flush()
        if not esperar(1):
            return Saude(False, "o servidor não respondeu ao cumprimento (tempo esgotado ou fechou sozinho)")
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n" + _mensagem(2, "tools/list", {}))
        p.stdin.flush()
        resposta = esperar(2)
        nomes = [str(t.get("name"))[:60] for t in ((resposta or {}).get("result") or {}).get("tools", []) if isinstance(t, dict)]
        if not nomes:
            return Saude(False, "o servidor respondeu, mas não listou ferramentas")
        return Saude(True, f"o servidor respondeu e listou {len(nomes)} ferramenta(s)", nomes[:30])
    except (OSError, ValueError):
        return Saude(False, "a conversa com o servidor foi interrompida")
    finally:
        _encerrar(p)
