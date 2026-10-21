"""Única porta de entrada para criar processos (subprocess) no Super Jarvis.

Por quê: o Jarvis.exe é um aplicativo de janela (sem console). No Windows, todo programa de console que ele
inicia (git, node, powershell, cmd, taskkill...) sem a flag CREATE_NO_WINDOW abre uma janelinha preta que
pisca e fecha. Aqui tudo nasce oculto: CREATE_NO_WINDOW + STARTUPINFO(SW_HIDE). Fora do Windows nada muda.

- `executar(...)`  = subprocess.run, oculto.
- `abrir(...)`     = subprocess.Popen, oculto.
- `abrir_visivel(...)` = para abrir programas que o usuário pediu para ver (Explorer, VS Code, cmd, PowerShell):
  sem SW_HIDE, para a janela do programa aparecer.
- `ocultar_consoles()` = rede de segurança: faz até o código de terceiros (platform, keyring...) criar processos ocultos.

Quem tiver uma exceção legítima passa `creationflags` explícito com DETACHED_PROCESS ou CREATE_NEW_CONSOLE: o helper respeita.
O teste tests/test_proc.py reprova qualquer chamada a subprocess/os.system fora deste arquivo.
"""

from __future__ import annotations

import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_CONSOLE = 0x00000010
_SW_HIDE = 0
_STARTF_USESHOWWINDOW = 0x00000001
_ja_ocultou = False


def _windows() -> bool:
    return sys.platform == "win32"


def _startupinfo_oculto(existente=None):
    info = existente if existente is not None else subprocess.STARTUPINFO()
    info.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", _STARTF_USESHOWWINDOW)
    info.wShowWindow = getattr(subprocess, "SW_HIDE", _SW_HIDE)
    return info


def _sem_janela(opcoes: dict, esconder: bool) -> dict:
    """Cópia das opções de Popen/run com as flags que impedem janela de console (só no Windows)."""
    if not _windows():
        return dict(opcoes)
    novas = dict(opcoes)
    flags = int(novas.get("creationflags") or 0)
    if not flags & (DETACHED_PROCESS | CREATE_NEW_CONSOLE):  # esses dois já decidem sozinhos sobre o console
        novas["creationflags"] = flags | CREATE_NO_WINDOW
    if esconder and not flags & CREATE_NEW_CONSOLE:
        novas["startupinfo"] = _startupinfo_oculto(novas.get("startupinfo"))
    return novas


def executar(*args, **opcoes) -> subprocess.CompletedProcess:
    """subprocess.run sem janela (timeout, capture_output, text, encoding... iguais)."""
    return subprocess.run(*args, **_sem_janela(opcoes, esconder=True))


def abrir(*args, **opcoes) -> subprocess.Popen:
    """subprocess.Popen sem janela."""
    return subprocess.Popen(*args, **_sem_janela(opcoes, esconder=True))


def abrir_visivel(*args, **opcoes) -> subprocess.Popen:
    """Abre um programa que o usuário quer ver: bloqueia só o console, nunca a janela do próprio programa."""
    return subprocess.Popen(*args, **_sem_janela(opcoes, esconder=False))


def ocultar_consoles() -> None:
    """Rede de segurança no Windows: todo Popen do processo (inclusive de bibliotecas) nasce sem console."""
    global _ja_ocultou
    if not _windows() or _ja_ocultou:
        return
    original = subprocess.Popen.__init__

    def iniciar(self, *args, **opcoes):
        original(self, *args, **_sem_janela(opcoes, esconder=False))

    subprocess.Popen.__init__ = iniciar
    _ja_ocultou = True
