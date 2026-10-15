"""Tokens de acesso (OAuth) criptografados com o DPAPI do Windows.

Só a conta do Windows que gravou consegue ler. Fica em
%LOCALAPPDATA%\\SuperJarvis\\tokens\\<nome>.bin. É usado em vez do Gerenciador
de Credenciais porque tokens OAuth passam do limite de 2,5 KB dele.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from pathlib import Path

from jarvis.config import data_dir


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


_UI_FORBIDDEN = 0x01  # nunca abrir diálogo do Windows


def _call(func, data: bytes) -> bytes:
    """CryptProtectData e CryptUnprotectData têm a mesma assinatura de 7 argumentos."""
    buffer = ctypes.create_string_buffer(data, len(data))
    blob_in = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob_out = _Blob()
    if not func(ctypes.byref(blob_in), None, None, None, None, _UI_FORBIDDEN, ctypes.byref(blob_out)):
        raise OSError("falha no DPAPI do Windows")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def protect(data: bytes) -> bytes:
    return _call(ctypes.windll.crypt32.CryptProtectData, data)


def unprotect(data: bytes) -> bytes:
    return _call(ctypes.windll.crypt32.CryptUnprotectData, data)


def _path(name: str, folder: Path | None) -> Path:
    if not name.replace("_", "").isalnum():
        raise ValueError("nome de token inválido")
    return (folder or data_dir() / "tokens") / f"{name}.bin"


def save(name: str, text: str, folder: Path | None = None) -> None:
    path = _path(name, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(protect(text.encode("utf-8")))


def load(name: str, folder: Path | None = None) -> str | None:
    path = _path(name, folder)
    if not path.exists():
        return None
    try:
        return unprotect(path.read_bytes()).decode("utf-8")
    except OSError:
        return None


def delete(name: str, folder: Path | None = None) -> None:
    _path(name, folder).unlink(missing_ok=True)
