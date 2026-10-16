"""Onde fica o modelo de transcrição (Whisper) e como a Jarvis o consegue.

Ordem de busca, da mais "dentro do instalador" para a menos:

1. `<pasta do app>\\modelos\\whisper-<tamanho>`: vai no instalador quando ele é gerado com o
   modelo (packaging\\baixar_modelo.py). Funciona offline desde a primeira abertura.
2. `%LOCALAPPDATA%\\SuperJarvis\\modelos\\whisper-<tamanho>`: pasta própria da Jarvis, onde o
   modelo é baixado uma única vez se o instalador não o trouxe.
3. O cache do Hugging Face do usuário, só se o modelo já estiver lá (PC de desenvolvimento).
   Nunca é criado nem alterado.

Só se nada disso existir, o modelo é baixado para a pasta própria (2).
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from jarvis.config import data_dir

# Tamanho aproximado dos arquivos (MB), só para avisar o usuário antes do download.
SIZES_MB = {"tiny": 75, "base": 145, "small": 465, "medium": 1500}
REQUIRED = ("model.bin", "config.json")


def bundled_root() -> Path:
    """Pasta `modelos` ao lado do programa instalado (ou em packaging/ no código-fonte)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "modelos"
    return Path(__file__).resolve().parents[2] / "packaging" / "modelos"


def own_root() -> Path:
    return data_dir() / "modelos"


def folder_name(size: str) -> str:
    return f"whisper-{size}"


def has_model(folder: Path) -> bool:
    return all((folder / name).is_file() for name in REQUIRED)


def _hub_download(size: str, **kwargs) -> str:
    from faster_whisper.utils import download_model

    return download_model(size, **kwargs)


def resolve_whisper(size: str, on_status: Callable[[str], None] | None = None,
                    download: Callable[..., str] = _hub_download) -> str:
    """Pasta do modelo `size`, baixando só se for preciso. Levanta RuntimeError com orientação."""
    if Path(size).is_dir():  # o config.json pode apontar direto para uma pasta
        return size
    for root in (bundled_root(), own_root()):
        folder = root / folder_name(size)
        if has_model(folder):
            return str(folder)
    try:
        return download(size, local_files_only=True)
    except Exception:  # noqa: BLE001 - não está no cache do usuário: segue para o download
        pass
    target = own_root() / folder_name(size)
    if on_status:
        on_status(f"Baixando o modelo de voz (~{SIZES_MB.get(size, '?')} MB), só nesta primeira vez…")
    try:
        return download(size, output_dir=str(target))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"não consegui baixar o modelo de voz ({exc}). Conecte à internet e abra a Jarvis de novo; "
            f"ou copie o modelo para {target}") from exc
