"""Perfil do aparelho e o modelo que vale a pena rodar nele (mais memória e processador = modelo maior)."""

from __future__ import annotations

import os
import shutil


def medir() -> dict:
    """Memória total (GB), núcleos e se há uma placa NVIDIA (o build de CPU não a usa; serve de aviso)."""
    import psutil

    return {"ram_gb": round(psutil.virtual_memory().total / 1024**3, 1), "nucleos": os.cpu_count() or 1,
            "nvidia": shutil.which("nvidia-smi") is not None}


def recomendado(ram_gb: float | None = None, conversa: bool = False) -> str:
    """Escolhe o maior modelo que cabe com folga: o sistema e a Jarvis também precisam de memória.

    `conversa=True` escolhe o melhor para CONVERSAR (Qwen3); o padrão continua sendo o de código, pequeno e rápido.
    """
    ram = medir()["ram_gb"] if ram_gb is None else ram_gb
    if conversa:
        return "qwen3-4b" if ram >= 7 else "qwen3-1.7b" if ram >= 5 else "qwen2.5-coder-1.5b"
    if ram >= 28:
        return "qwen2.5-coder-7b"
    if ram >= 12:
        return "qwen2.5-coder-3b"
    return "qwen2.5-coder-1.5b"


def descrever(perfil: dict | None = None) -> str:
    p = perfil or medir()
    nome = recomendado(p["ram_gb"])
    extra = " Há uma placa NVIDIA, mas o motor instalado usa só o processador." if p["nvidia"] else ""
    return f"Este aparelho tem {p['ram_gb']:g} GB de memória e {p['nucleos']} núcleos; o modelo recomendado é o {nome}.{extra}"
