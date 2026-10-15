"""Logs em %LOCALAPPDATA%\\SuperJarvis\\logs\\jarvis.log.

Vários processos escrevem no mesmo arquivo (janela, servidor MCP, terminal). A rotação
automática do Python quebra nesse caso no Windows (renomear um arquivo aberto falha e
os registros se perdem). Por isso: anexar sempre, e arquivar só ao abrir a janela,
quando o arquivo passa de 5 MB.
"""

from __future__ import annotations

import logging

from jarvis.config import data_dir

MAX_BYTES = 5_000_000


def setup(level: int = logging.INFO, archive: bool = False) -> None:
    log_dir = data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "jarvis.log"
    if archive:
        try:
            if path.exists() and path.stat().st_size > MAX_BYTES:
                path.replace(log_dir / "jarvis.old.log")
        except OSError:
            pass  # outro processo está com o arquivo aberto: arquiva na próxima vez
    handler = logging.FileHandler(path, encoding="utf-8", delay=True)
    handler.setFormatter(logging.Formatter("%(asctime)s %(process)d %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
