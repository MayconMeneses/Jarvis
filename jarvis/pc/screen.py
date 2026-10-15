"""Captura de tela para a Jarvis "olhar" (erros, telas, layouts).

A janela da Jarvis é minimizada por um instante para não sair na foto e depois volta.
Só deve ser usada quando o usuário pede; a imagem vai para o Claude, como um anexo.
"""

from __future__ import annotations

import ctypes
import io
import time

SW_MINIMIZE, SW_RESTORE = 6, 9


def _jarvis_windows(title: str = "Jarvis") -> list[int]:
    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visit(hwnd, _):
        length = user32.GetWindowTextLengthW(hwnd)
        if length and user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if buffer.value == title:
                found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    return found


def capture(max_side: int = 1568, grab=None, hide=True) -> bytes:
    """PNG da tela (todos os monitores), reduzido ao tamanho que o modelo aproveita."""
    from PIL import ImageGrab

    grab = grab or (lambda: ImageGrab.grab(all_screens=True))
    hidden = _jarvis_windows() if hide else []
    user32 = ctypes.windll.user32
    for hwnd in hidden:
        user32.ShowWindow(hwnd, SW_MINIMIZE)
    try:
        if hidden:
            time.sleep(0.45)  # tempo da animação de minimizar
        image = grab()
    finally:
        for hwnd in hidden:
            user32.ShowWindow(hwnd, SW_RESTORE)
    image = image.convert("RGB")
    image.thumbnail((max_side, max_side))
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()
