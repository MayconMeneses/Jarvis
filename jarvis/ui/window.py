"""Janela do Windows: posição na tela e instância única."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import time

_ERROR_ALREADY_EXISTS = 183
_SPI_GETWORKAREA = 0x0030


def window_geometry(width: int = 440, height: int = 720, margin: int = 12) -> tuple[int, int, int, int]:
    """Canto inferior direito da área útil do monitor (sem cobrir a barra de tarefas)."""
    area = wt.RECT()
    if not ctypes.windll.user32.SystemParametersInfoW(_SPI_GETWORKAREA, 0, ctypes.byref(area), 0):
        return 100, 60, width, min(height, 680)
    usable = area.bottom - area.top - 2 * margin
    height = max(480, min(height, usable))
    return area.right - width - margin, area.bottom - height - margin, width, height


def claim_single_instance(name: str = "Local\\SuperJarvis", wait_seconds: float = 0.0):
    """Mutex nomeado do Windows. Retorna o handle, ou None se outra Jarvis já está aberta.

    No reinício, a Jarvis nova espera (wait_seconds) a antiga terminar e liberar o mutex.
    """
    kernel32 = ctypes.windll.kernel32
    deadline = time.time() + wait_seconds
    while True:
        handle = kernel32.CreateMutexW(None, False, name)
        if kernel32.GetLastError() != _ERROR_ALREADY_EXISTS:
            return handle
        kernel32.CloseHandle(handle)
        if time.time() >= deadline:
            return None
        time.sleep(0.25)


def show_already_open() -> None:
    ctypes.windll.user32.MessageBoxW(
        None, "A Jarvis já está aberta. Procure o ícone dela na bandeja, perto do relógio.", "Jarvis", 0x40)
